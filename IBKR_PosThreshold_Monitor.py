import sys, getopt, os
import subprocess
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import pytz

import websocket
import time
import ssl
import json

import m_logger

from ibw.client import IBClient
from functions import _create_session
from functions import import_credentials
import threading

# J. Jones
# Setting up a logging service for the bot to be able to retrieve
# runtime messages from a log file
est_tz = pytz.timezone('US/Eastern')
now = datetime.now(est_tz).strftime("%Y_%m_%d-%H%M%S")
logfilename = "{}_logfile_{}".format("RT_Stream", now)
logfilename = logfilename + ".txt"
logger = m_logger.getlogger(logfilename)
conids = []
PriceDict = {}
earliest_order = None
latest_order = None
second_earlier_order = None
second_latest_order = None

def PriceDict_Mgmt(ibcsession, underlying : str, conid: int, bidprice: float, askprice: float, lastprice: float, incoming_purchasePrc: float, stop_loss, gain_limit) -> bool :

    if conid not in PriceDict:
        #print("reseting PriceDict")
        if underlying != '' :
            PriceDict[conid] = {'Underlying' : underlying , 'bidprice': 0, 'askprice': 0.0, 'lastprice': 0.0, 'purchPrc': 0}
        else :
            PriceDict[conid] = {'Underlying' : "Undefined" , 'bidprice': 0, 'askprice': 0.0, 'lastprice': 0.0, 'purchPrc': 0}
        PriceDict[conid]['bidprice'] = bidprice
        PriceDict[conid]['askprice'] = askprice
        PriceDict[conid]['lastprice'] = lastprice
        if incoming_purchasePrc == 0.0:
            print("Purchase price should not be zero for {cid}".format(cid=str(conid)))
            # PriceDict[conid]['purchPrc'] = purchasePrc
        PriceDict[conid]['purchPrc'] = incoming_purchasePrc
        #print("Length of dictionary {lenPrc}".format(lenPrc=str(len(PriceDict))))
        #print(PriceDict)
    else:
        if bidprice != 0.0:
            PriceDict[conid]['bidprice'] = bidprice
        if askprice != 0.0:
            PriceDict[conid]['askprice'] = askprice
        if lastprice != 0.0:
            PriceDict[conid]['lastprice'] = lastprice
        if incoming_purchasePrc != 0.0:
            PriceDict[conid]['purchPrc'] = incoming_purchasePrc

    # we may not receive an underlying_symbol, bid, ask and last with every message.
    # we need to accommodate this partial information
    PrcMovePerc = 0.0
    bd = PriceDict[conid]['bidprice']
    ak = PriceDict[conid]['askprice']
    lp = PriceDict[conid]['lastprice']
    lpur = PriceDict[conid]['purchPrc']
    #print(" Msg : ConID {id} Purchase {Purch} Bid {bid} Ask {ask} Last {last} Perc Move {move} ".format(id=str(conid), Purch=str(PriceDict[conid]['purchPrc']), bid=str(PriceDict[conid]['bidprice']), ask=str(PriceDict[conid]['askprice']), last=str(PriceDict[conid]['lastprice']), move=str(PrcMovePerc)))

    if (bd == 0.0) or (ak == 0.0):
        #logger.info("either bid or ask is zero")
        #print(PriceDict)
        # We can't take any action without a bid/ask spread
        return True
    else :
        if (lp > ak) or (lp < bd):
            # set the last as the midpoint between bid/ask, if the security hasn't traded recently
            #print("last not between bid and ask")
            lp = PriceDict[conid]['lastprice'] = (bd + ak) / 2
    if underlying == '' :
        undSym = PriceDict[conid]['Underlying']
    else:
        undSym = underlying
    #print(" Msg 2 : ConID {id} Purchase {Purch} Bid {bid} Ask {ask} Last {last} Perc Move {move} ".format(id=str(conid), Purch=str(PriceDict[conid]['purchPrc']), bid=str(PriceDict[conid]['bidprice']), ask=str(PriceDict[conid]['askprice']), last=str(PriceDict[conid]['lastprice']), move=str(PrcMovePerc)))

    if lpur > 0.0 and lp > 0.0:
        PrcDiff = lp - lpur
        PrcMovePerc = (PrcDiff / lpur) * 100

    #print(PrcMovePerc, stop_loss, gain_limit)

    logger.info("Underlying {und} ConID {id} Purchase {Purch} Bid {bid} Ask {ask} Last {last} Perc Move {move} ".format(und=undSym, id=str(conid), Purch=str(lpur), bid=str(bd), ask=str(ak), last=str(lp), move=str(PrcMovePerc)))
    # Need to wrap the sell in a thread to avoid more market data updates interrupting the sell requests
    if (PrcMovePerc < stop_loss) or (PrcMovePerc > gain_limit) :
        Sell_Thread = threading.Thread(target=sell_stock, args=[ibcsession, PriceDict[conid]['Underlying'], conid, 'SELL', 1])
        Sell_Thread.start()
        Sell_Thread.join()
        return False
    else :
        return True

def on_message(ws, message):
    #logger.info('Incoming Msg : {dfbq}'.format(dfbq=str(message)))
    LastPrice = BidPrice = AskPrice = 0
    messageInfo = json.loads(message)
    # if 'topic' in messageInfo.keys() :
    # topic = messageInfo['topic']
    # logger.info('Topic : {}'.format(topic))
    Underlying_Symbol = ''
    if 'conid' in messageInfo.keys():
        conid_int = int(messageInfo['conid'])
        if '31' in messageInfo.keys():
            LastPrice = float(messageInfo['31'])
        if '84' in messageInfo.keys():
            BidPrice = float(messageInfo['84'])
        if '86' in messageInfo.keys():
            AskPrice = float(messageInfo['86'])
        if '55' in messageInfo.keys():
            Underlying_Symbol = messageInfo['55']
        if (not PriceDict_Mgmt(ws.ibcsession, Underlying_Symbol, conid_int, BidPrice, AskPrice, LastPrice, 0.0, ws.stop_loss, ws.gain_limit)) :
            ws.close() #PriceDict_Mgmt will return False if a position was sold, we need to close the socket and reload positions

    current_time = time.time()
    if (current_time - ws.timer_tracker) > 120:
        logger.info('over 120 secs, reloading positions')
        ws.timer_tracker = current_time
        ws.close()


def on_error(ws, error):
    logger.info('Error Msg : {dfbq}'.format(dfbq=str(error)))


def on_close(ws):
    logger.info('## CLOSED! ##')
    time.sleep(2)


def on_open(ws):
    logger.info('Opened Connection')
    time.sleep(3)
    # Note : PriceDict is a global variable of prices for each positions
    # We reset it every time we reload positions
    # THe list of available fields and their keys  is on the IBKR Website
    # 55=underlying Ticker, 31=Last, 84=Bid, 86=Ask
    for conid in conids:
        ws.send('smd+' + conid + '+{"fields":["55","31","84","86"]}')


def Load_Positions(Session, account) -> int:
    # Retrieve all ConID's we have positions in

    # Note : conids is a global list which is reset every time we reload positions
    conids.clear()
    conids.append('756733')
    PriceDict.clear()
    positions_response = Session.portfolio_account_positions(account_id=account, page_id=0)
    position_count = 0
    for position in positions_response:
        if 'acctId' not in position.keys():
            logger.info("Received Error While Requesting Positions : {pos}".format(pos=position))
            logger.info("Positions response {ord}".format(ord=json.dumps(positions_response, indent=4)))
            sys.exit(2)

        if 'conid' in position.keys():
            Underlying_Symbol = position['contractDesc'].split(" ")[0]
            position_symbol = position['conid']
            if position['position'] > 0:
                logger.info(
                    "ConID {cid} Quantity {qty} Purch Prc {purch}".format(cid=position_symbol, qty=position['position'],
                                                                          purch=position['avgPrice']))
                conids.append(str(position_symbol))
                if position_symbol not in PriceDict:
                    # print("reseting PriceDict")
                    PriceDict[position_symbol] = {'Underlying' : Underlying_Symbol, 'bidprice': 0, 'askprice': 0.0, 'lastprice': 0.0, 'purchPrc': position['avgPrice']}
                #PriceDict_Mgmt(Session, position_symbol, 0.0, 0.0, 0.0, position['avgPrice'])
                position_count += 1

    return position_count

def sell_stock(session, symbol, option_symbol, instruction: str, quant : int):
    """
    Portfolio format
        {
            'asset_type': 'equity',
            'quantity': 2,
            'purchase_price': 4.00,
            'symbol': 'MSFT',
            'purchase_date': '2020-01-31'
        }
    """

    bidPrice = 0.0
    account = "U7949765"


    order_response = {}
    if quant == 0 :
        default_quantity = 1
    else :
        default_quantity = quant

    orderType = 'MKT'
    if orderType == 'MKT':
        order_template = {
            'acctid': account,
            'conid': int(option_symbol),
            'ticker' : symbol,
            'secType': str(option_symbol) + ':' + 'OPT',
            'orderType': orderType,
            'quantity': default_quantity,
            'side': instruction,
            'tif': 'DAY'
            }
    else:
        logger.info("Invalid Order Type %s", orderType)
        order_template = {}
        return order_template, order_response

    try:
        # J. Jones - added dump of order template
        logger.info("Order Template {ord}".format(ord=json.dumps(order_template, indent=4)))

        order_response = session.place_order(
            account_id=account,
            order=order_template
        )

        if 'order_id' in order_response[0].keys() :
            logger.info("Order Submitted, OrderID = {id}".format(id=order_response[0]['order_id']))
            return order_template, order_response
        else : # We have messages to respond to, we by default just respond 'true' to all of them
            if 'messageIds' in order_response[0].keys() :
                logger.info("Message received on order : {msg}".format(msg=order_response[0]['message']))
                order_response_question = session.place_order_reply(reply_id = order_response[0]['id'])
                if 'messageIds' in order_response_question[0].keys() :
                    logger.info("Message received on order : {msg}".format(msg=order_response_question[0]['message']))
                    order_response_question2 = session.place_order_reply(reply_id = order_response_question[0]['id'])
                elif 'order_id' in order_response_question[0].keys() :
                    return order_template, order_response_question
                if 'order_id' in order_response_question2[0].keys() :
                    return order_template, order_response_question2
            elif 'order_id' in order_response[0].keys() :
                return order_template, order_response

        logger.info("{inst} order unsuccessfully placed for {sy}".format(inst=instruction, sy=option_symbol))

        logger.info("Order response {ord}".format(ord=json.dumps(order_response_question, indent=4)))

        return order_template, order_response

    except Exception as e:
        logger.info(
            "Error trying to place {inst} for {sy} with error code {er}".format(inst=instruction, sy=option_symbol,
                                                                                er=str(e)))

        return order_template, order_response


def main(argv):
    defQuant = 1
    try:
        opts, args = getopt.getopt(argv, "h")
    except getopt.GetoptError:
        print('Unrecognized command line arguments RT_Mon ')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('RT_Mon <no command line arguments, reads config.ini')
            sys.exit()

    CLIENT_ID, REDIRECT_URI, ACCOUNT_NUMBER, ACCOUNT_ID, \
        START_TRADING_TIME, END_TRADING_TIME, SECOND_START_TRADING_TIME, SECOND_END_TRADING_TIME, LIQUIDATE_DAY_TRADES_TIME, \
        DEFAULT_ORDER_TYPE, NO_TRADING_LOSS, DEFAULT_BUY_QUANTITY, Stop_Loss_Perc, Gain_Cap_Perc = import_credentials(
        log_hndl=logger)

    est_tz = pytz.timezone('US/Eastern')
    nw = datetime.now(est_tz)
    earliest_order = datetime.combine(nw, datetime.strptime(START_TRADING_TIME, '%H:%M:%S EST').time())
    earliest_order = est_tz.localize(earliest_order)
    latest_order = datetime.combine(nw, datetime.strptime(END_TRADING_TIME, '%H:%M:%S EST').time())
    latest_order = est_tz.localize(latest_order)

    IBC_Session = _create_session(CLIENT_ID, ACCOUNT_ID)
    Stop_Loss_Perc = Stop_Loss_Perc * -1.0
    logger.info(("Max Loss Limit = {mloss}, Max Gain Limit = {mgain}".format(mloss=str(Stop_Loss_Perc), mgain=str(Gain_Cap_Perc))))
    while (True):
        pos_count = Load_Positions(IBC_Session, ACCOUNT_ID)
        if pos_count >= 0:
            ws = websocket.WebSocketApp(
                url="wss://localhost:5000/v1/api/ws",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            # Reloading positions every 60 seconds
            ws.timer_tracker = time.time()
            ws.stop_loss = Stop_Loss_Perc
            ws.gain_limit = Gain_Cap_Perc
            ws.earliest_order = earliest_order
            ws.latest_order = latest_order
            ws.ibcsession = IBC_Session
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=60, ping_timeout=5)
        else:
            # wait 1 minutes for position update
            logger.info("No Positions Available")
            time.sleep(60)

    #    order_template, order_response = sell_stock(logger, IBC_Session, underlying_symbol, option_symbol_number, "SELL")

    return True


if __name__ == "__main__":
    main(sys.argv[1:])
