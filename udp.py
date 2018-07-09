#!/usr/bin/env python
# -*- coding:utf8 -*-

import sys
import time
import os
from time import sleep
reload(sys)
sys.setdefaultencoding('utf-8')
# make a copy of original stdout route
stdout_backup = sys.stdout
# define the log file that receives your log info
log_file = open("message_log.log", "a")
# redirect print output to log file
sys.stdout = log_file
log_file.close()

#wether it's from foward server
udp_foward = 1

import socket

def showHex(s):
    for c in s:
        print("%x"%(ord(c))),
    print("\ntotal length is:%d"%(len(s)))

def showAddr(s):
    port = ord(s[4])+ord(s[5])*256
    print("from:%3d.%3d.%3d.%3d"%(ord(s[0]),ord(s[1]),ord(s[2]),ord(s[3]))),
    print(":%4d"%(port))



class UdpServer(object):
    def tcpServer(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 12001))       # 绑定同一个域名下的所有机器

        while True:
            recvData, (remoteHost, remotePort) = sock.recvfrom(1024)
            log_file = open("message_log.log", "a")
            sys.stdout = log_file
            print "****************************"
            print time.strftime("%Y-%m-%d %X",time.localtime(time.time()))
            print("[%s:%s] connect" % (remoteHost, remotePort))     # 接收客户端的ip, port
            if udp_foward and len(recvData)> 6:
                showHex(recvData)
                print "recvData     :", recvData
                print "recvData(sub):", recvData[6:]
                showAddr(recvData)
                strsendData = "your address is %s" % remoteHost
                sendDataLen = sock.sendto(strsendData , (remoteHost, remotePort))
                #sendDataLen = sock.sendto(recvData[:7]+"this is echo data from server", (    remoteHost, remotePort))
                print("sendData(%3d):%s"%(sendDataLen,recvData))
                #print "sendDataLen: ", sendDataLen
            else:
                print "recvData: ", recvData
                sendDataLen = sock.sendto("Eric专属测试机器", (remoteHost, remotePort))
                print "sendDataLen: ", sendDataLen
                #print("sendData(%3d):%s"%(sendDataLen,recvData))
            print "****************************"
            print "\n"
            log_file.close()
            sys.stdout = stdout_backup
        sock.close()

if __name__ == "__main__":
    udpServer = UdpServer()
    udpServer.tcpServer()
