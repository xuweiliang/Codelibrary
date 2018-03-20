#!/usr/bin/env python
# coding: utf-8

'''
Created on Jul 6, 2012

@author: gf
'''
import os
import sys
import logging

LEVEL_DEBUG = 0
LEVEL_INFO = 1
LEVEL_WARN = 2
LEVEL_ERROR = 3

LOG_FILE = os.environ['HOME'] + '/havclient.log'

g_logger = None
stdout = None
stderr = None

class StdRedir(object):
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
    
    def write(self, msg):
        if self.level == LEVEL_ERROR:
            self.logger.error(msg)
            stderr.write(msg)
        else:
            self.logger.info(msg)
            stdout.write(msg)
    
def initlog():
    logger = logging.getLogger()
    filehandler = logging.FileHandler(LOG_FILE)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    filehandler.setFormatter(formatter)
    logger.addHandler(filehandler)
    logger.setLevel(logging.NOTSET)
    
    global g_logger, stdout, stderr
    g_logger = logger
    stdout = sys.stdout
    stderr = sys.stderr
    
    out = StdRedir(logger, LEVEL_INFO)
    err = StdRedir(logger, LEVEL_WARN)
    
    sys.stdout = out
    sys.stderr = err
    
def info(msg, *args, **kwargs):
    g_logger.info(msg, *args, **kwargs)
    
def warn(msg, *args, **kwargs):
    g_logger.warn(msg, *args, **kwargs)
    
def error(msg, *args, **kwargs):
    g_logger.error(msg, *args, **kwargs)
    
def debug(msg, *args, **kwargs):
    g_logger.debug(msg, *args, **kwargs)
    
initlog()
    
if __name__ == '__main__':
    info("Testing %d, %s", 1, 'Hello')
    print 'Hello'
    print 'Error '>> sys.stderr
    
