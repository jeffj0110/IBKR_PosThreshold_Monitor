import platform
import logging
import glob
import os
import pandas as pd
from os.path import exists

from datetime import datetime
import pytz
from pytz import timezone
from configparser import ConfigParser

from ibw.client import IBClient


#def setup_func(logger_hndl=None):
    # Get credentials

#    CLIENT_ID, REDIRECT_URI, ACCOUNT_NUMBER, ACCOUNT_ID, \
#    START_TRADING_TIME, END_TRADING_TIME, SECOND_START_TRADING_TIME, SECOND_END_TRADING_TIME, LIQUIDATE_DAY_TRADES_TIME, \
#    DEFAULT_ORDER_TYPE, NO_TRADING_LOSS, DEFAULT_BUY_QUANTITY, Stop_Loss_Perc, Gain_Cap_Perc  = import_credentials(log_hndl=logger_hndl)

    # J. Jones - setting bots default timezone to EST.
#    est_tz = pytz.timezone('US/Eastern')
#    dt = datetime.now(est_tz).strftime("%Y_%m_%d-%I%M%S_%p")
#    logmsg = "Session created at " + dt + " EST"
#    logger_hndl.info(logmsg)

#    return CLIENT_ID, REDIRECT_URI, ACCOUNT_NUMBER, ACCOUNT_ID, \
#    START_TRADING_TIME, END_TRADING_TIME, SECOND_START_TRADING_TIME, SECOND_END_TRADING_TIME, LIQUIDATE_DAY_TRADES_TIME, \
#    DEFAULT_ORDER_TYPE, NO_TRADING_LOSS, DEFAULT_BUY_QUANTITY, Stop_Loss_Perc, Gain_Cap_Perc


def import_credentials(log_hndl=None):
    system = platform.system()
    config = ConfigParser()
    currWorkingDirectory = os.getcwd()
    log_hndl.info("Working from default directory %s ", currWorkingDirectory)
    if exists('./config/config.ini') :
        config_str = config.read(r'./config/config.ini')
        log_hndl.info("Reading ./config/config.ini file ")
    else :
        log_hndl.info("No ./config/config.ini file found in %s", currWorkingDirectory)
        exit(-1)

    if config.has_option('main', 'CLIENT_ID') :
        CLIENT_ID = config.get('main', 'CLIENT_ID')
    else:
        log_hndl.info("No CLIENT_ID Found in config.ini file")
        exit(-1)
    REDIRECT_URI = config.get('main', 'REDIRECT_URI')
    ACCOUNT_NUMBER = config.get('main', 'ACCOUNT_NUMBER')
    ACCOUNT_ID = config.get('main', 'ACCOUNT_ID')
    #CREDENTIALS_PATH = config.get('main', 'CREDENTIALS_PATH')
    START_TRADING_TIME = config.get('main', 'START_TRADING_TIME')
    END_TRADING_TIME = config.get('main', 'END_TRADING_TIME')
    if config.has_option('main', '2ND_START_TRADING_TIME') :
        SECOND_START_TRADING_TIME = config.get('main', '2ND_START_TRADING_TIME')
    else:
        SECOND_START_TRADING_TIME = ''
    if config.has_option('main', '2ND_START_TRADING_TIME'):
        SECOND_END_TRADING_TIME = config.get('main', '2ND_END_TRADING_TIME')
    else:
        SECOND_END_TRADING_TIME = ''
    LIQUIDATE_DAY_TRADES_TIME = config.get('main', 'LIQUIDATE_ALL_POSITIONS_TIME')
    DEFAULT_ORDER_TYPE = config.get('main', 'DEFAULT_ORDER_TYPE')
    No_Trading_Loss = "FALSE"

    if config.has_option('main', 'STOP_LOSS_PERCENTAGE') :
        Stop_Loss_Perc = float(config.get('main', 'STOP_LOSS_PERCENTAGE'))
    else:
        Stop_Loss_Perc = float(0.0)

    if config.has_option('main', 'GAIN_CAP_PERCENTAGE') :
        Gain_Cap_Perc = float(config.get('main', 'GAIN_CAP_PERCENTAGE'))
    else:
        Gain_Cap_Perc = float(0.0)

    DEFAULT_BUY_QUANTITY = config.get('main', 'DEFAULT_BUY_QUANTITY')

    return CLIENT_ID, REDIRECT_URI, ACCOUNT_NUMBER, ACCOUNT_ID, \
           START_TRADING_TIME, END_TRADING_TIME, SECOND_START_TRADING_TIME, SECOND_END_TRADING_TIME,\
           LIQUIDATE_DAY_TRADES_TIME, \
           DEFAULT_ORDER_TYPE, No_Trading_Loss, DEFAULT_BUY_QUANTITY, Stop_Loss_Perc, Gain_Cap_Perc



def _create_session(CLIENT_ID, ACCOUNT_ID) -> IBClient:
#        """Start a new session.
#        Creates a new session with the Interactive Brokers API and logs the user into
#        the new session.

#        Returns:
#        ----
#        IBClient -- An IBClient object with an authenticated sessions.

#        """

    # Create a new instance of the client
    ib_client = IBClient(
        username=CLIENT_ID,
        account=ACCOUNT_ID,
        is_server_running=True
        #            client_id=self.client_id,
        #            account_number=self.trading_account,
        #            redirect_uri=self.redirect_uri,
        #            credentials_path=self.credentials_path
    )

    # log the client into the new session
    # td_client.login()

    return ib_client
