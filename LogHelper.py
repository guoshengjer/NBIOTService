# -*- coding:utf8 -*-
__author__ = 'Eric2'
__date__ = '2018/7/8'
import logging
import os
import datetime

class LogHelper:

    def __init__(self):
        self.logHelper = self.log()
        return

    def log(self):
        logger = logging.getLogger('NBIOTService')
        logger.setLevel(logging.DEBUG)
        LOGDIR = os.path.join(os.getcwd(), 'log')
        LOGFILE = datetime.datetime.now().strftime('%Y-%m-%d')+'.log'
        if not os.path.isdir(LOGDIR):
            os.makedirs(LOGDIR)
        # logging.basicConfig(level=logging.DEBUG,
        #                     format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        #                     pathname=LOGDIR,
        #                     datefmt='%Y-%m-%d %H:%M:%S',
        #                     #filename=os.path.join(LOGDIR, LOGFILE),
        #                     filemode='a')
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(filename)s[line:%(lineno)d]: %(message)s')

        cmdlog = logging.StreamHandler()
        cmdlog.setLevel(logging.DEBUG)
        cmdlog.setFormatter(formatter)
        fileLog = logging.FileHandler(os.path.join(LOGDIR, LOGFILE), 'a')
        fileLog.setLevel(logging.DEBUG)
        fileLog.setFormatter(formatter)
        logger.addHandler(fileLog)
        logger.addHandler(cmdlog)
        return logger




if __name__ == '__main__':
    #logHelper = LogHelper().log()
    #logHelper.info("123")
    st = 'abcd'
    print st[::]