#-*- coding: utf-8 -*-
import logging
from logging import StreamHandler, FileHandler
import os

from polltask.config import get_default_config

DEBUG_LOG_FILE = os.path.join(os.path.dirname(__file__), '../out', 'poll_task.log')

class Logger(object):
    def __init__(self, name, log_file, log_level='INFO'):
        """
        :param log_file: the path of log file
        :param log_level: the log level which can be "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        """
        # create logger
        self.logger = logging.getLogger(name)
        log_level = self._convert_log_level(log_level)
        self.logger.setLevel(log_level)
        
        # Remove the existed handlers belonging to the logger
        handlers = self.logger.handlers
        while len(handlers) != 0:
            self.logger.removeHandler(handlers[0])
                
        # create console and file handler and set log level  
        self.ch = None
        self.fh = None
        ch = StreamHandler()
        ch.setLevel(log_level)
        fh = FileHandler(log_file)
        fh.setLevel(log_level)     
        
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # add formatter to handlers
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        # add handlers to logger
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)
       
        self.ch = ch
        self.fh = fh
        
    def _convert_log_level(self, log_level):
        log_convert_dict = {'DEBUG': logging.DEBUG,
                            'INFO': logging.INFO,
                            'WARNING': logging.WARNING,
                            'ERROR': logging.ERROR,
                            'CRITICAL': logging.CRITICAL}
        return log_convert_dict[log_level]

    def debug(self, message):
        self.logger.debug(message)
        
    def info(self, message):
        self.logger.info(message)

    def warn(self, message):
        self.logger.warn(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    def exit(self):
        if self.ch is not None:
            self.logger.removeHandler(self.ch)
        if self.fh is not None:
            self.logger.removeHandler(self.fh)

def get_logger(name, log_file, log_level='INFO'):
    if os.path.isfile(log_file):
        pass
    else:
        log_dir = os.path.dirname(log_file)
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir) 
        with open(log_file, 'w'):
            pass
    logger = Logger(name, log_file, log_level=log_level)
    return logger

def get_default_logger(name):
    config = get_default_config()
    default_log_file = config.get_option_value('default', 'log_file')
    default_log_level = config.get_option_value('default', 'log_level')
    return get_logger(name, default_log_file, log_level=default_log_level)

def get_debug_logger(name):
    global DEBUG_LOG_FILE
    return get_logger(name, DEBUG_LOG_FILE, log_level='DEBUG')

if __name__ == "__main__":
    #logger = get_default_logger('test', log_level='DEBUG')
    for i in [1, 2, 3]:
        print "\nThe {0}th logger:".format(i)
        logger = get_debug_logger('test')
        logger.debug("test log function")
