import logging

#
# Uses standard Python logging service to
# manage logging of the bot
#

def getlogger(lgfileName):
    # logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    ch = logging.FileHandler(lgfileName)
    ch.setLevel(logging.INFO)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(module)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    # create console handler and set level to debug
    stream_ch = logging.StreamHandler()
    stream_ch.setLevel(logging.INFO)
    stream_ch.setFormatter(formatter)
    logger.addHandler(stream_ch)
    return logger
