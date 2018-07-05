__author__ = 'Eric2'
__date__ = '2018/7/5'
# -*- coding:utf8 -*-

import threading
import Queue
import time

class MainService():

    def __init__(self):
        return True

    def startservice(self):

        return True

class ReceiveUDPThread(threading.Thread):
    def __init__(self, threadname, evtWaitStop):
        threading.Thread.__init__(self, name=threadname)
        self.m_evtWaitStop = evtWaitStop

    def run(self):
        bThdRunFlag = True

        while bThdRunFlag:

            self.m_evtWaitStop.wait(0.3)
            if self.m_evtWaitStop.isSet():

                bThdRunFlag = False
                continue
            print('udpServer is running')




if __name__ == "__main__":

    evtWaitStop = threading.Event()

    qCommands = Queue.Queue()

    thdReceiveTcp = ReceiveUDPThread("ReceiveUDPThread", evtWaitStop)
    thdReceiveTcp.setDaemon(True)
    thdReceiveTcp.start()

    bRunFlag = True
    nLoadConfigTimer = 300
    try:
        while bRunFlag:
            if nLoadConfigTimer <= 0:
                print("heart")
                nLoadConfigTimer = 300
            else:
                nLoadConfigTimer -= 1

            time.sleep(10)

    except KeyboardInterrupt:

        evtWaitStop.set()
    except:

        evtWaitStop.set()

    if thdReceiveTcp.isAlive():
        thdReceiveTcp.join()

    # if log:
    #     log = None


