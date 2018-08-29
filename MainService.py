# -*- coding:utf8 -*-
__author__ = 'Eric2'
__date__ = '2018/7/5'


import threading
import Queue
import time
import socket
import random
import DoorLock
import crctest
import LogHelper
from SocketServer import ThreadingTCPServer, BaseRequestHandler

g_dictDeviceId2DoorLock = {}
g_logger = None
# 中国电信兼容包头
g_buffHead_CTCC = "0001"


class MainService():

    def __init__(self):
        return True

    def startservice(self):

        return True


class ReceiveUDPThread(threading.Thread):

    def __init__(self, threadname, evtWaitStop, bindPort):
        '''
            线程初始化
        :param threadname:线程名称
        :param evtWaitStop: 线程停止标志
        :param bindPort: 监听端口
        :return:
        '''
        threading.Thread.__init__(self, name=threadname)
        self.m_evtWaitStop = evtWaitStop
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        g_logger.info("建立UDP服务端")
        self.sock.bind(('', bindPort))
        g_logger.info("监听端口:%d", bindPort)
        self.sock.setblocking(0)
        # 非阻塞模式
        self.sock.settimeout(1)
        # 超时时间
        self.totalBuff = ''

    def run(self):
        '''
            UDP服务端进程
        :return:
        '''
        bThdRunFlag = True
        while bThdRunFlag:

            self.m_evtWaitStop.wait(0.3)
            if self.m_evtWaitStop.isSet():

                bThdRunFlag = False
                continue
            try:

                # g_logger.debug("UDP服务端接收消息")
                recvBuff, (remoteHost, remotePort) = self.sock.recvfrom(1024)
                g_logger.info("UDP客户端IP:%s,端口:%s,接收到报文:%s", remoteHost, remotePort, recvBuff.encode('hex'))
                self.totalBuff += recvBuff.encode('hex')
                # -----------------------修改 20180725 eric-----------------
                self.totalBuff = self.totalBuff[8:]
                # ----------------------截取电信包8个字符--------------------
                # arraybuff = self.totalBuff.split(0xab)
                # 将接收的字符串分成多条报文
                # 方式一：找到ab起始符，然后读取ab后两个字节的内容，得到字符长度，然后取相应的长度截断。如果字符不够，则保留到下次
                while 1:
                    iPos = self.totalBuff.find('ab')
                    if iPos != -1 and iPos < len(self.totalBuff)/2 - 2:
                        g_logger.debug("进入解析报文阶段")
                        # 找到ab了，且能判断这条报文的字节大小
                        iBuffLenth = int(self.totalBuff[iPos+2:iPos+6], 16) * 2
                        if iBuffLenth <= len(self.totalBuff):
                            # totalbuff里还有别的报文数据
                            buff = self.totalBuff[iPos:iBuffLenth]
                            self.totalBuff = self.totalBuff[iBuffLenth:]
                            g_logger.debug("报文:%s", buff)
                            # 解析报文
                            sendBuff = self.formatDoorLockBuff(buff)
                            if sendBuff != None:
                                sendBuff = g_buffHead_CTCC + hex(len(sendBuff)/2)[2:].zfill(4) + sendBuff

                                g_logger.debug("即将发送的报文:%s", sendBuff)
                                # 发送回复报文
                                hexBuff = sendBuff.decode('hex')
                                sendBuffLen = self.sock.sendto(hexBuff, (remoteHost, remotePort))
                                g_logger.info("发送报文字节:%s", sendBuffLen)
                        else:
                            break
                    elif iPos == -1:

                        self.totalBuff = ''
                        break
                    else:
                        self.totalBuff = self.totalBuff[iPos:]
                        g_logger.info(self.totalBuff)
                        time.sleep(0.05)
            except socket.timeout:
                # 接收超时，继续运行
                # g_logger.debug("UDP服务端接收超时")
                continue
            except Exception, ex:
                g_logger.error(ex.message)

    def formatDoorLockBuff(self, buff):
        '''
            解析已经分隔好的报文
        :param buff:报文（ab0031023100220086874403359155705b1fa5b300530d00010d0019100001223c00820b1984d105fc550000000000000f）
        :return:
        '''
        iType = buff[8:10]
        dictDoorLock = {}
        if iType == '31':
            # 设备状态上报
            dictDoorLock["Version"] = buff[6:8]
            dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            dictDoorLock["Option"] = buff[40:42]
            dictDoorLock["Battery"] = buff[42:44]
            dictDoorLock["CSQ"] = buff[44:46]
            dictDoorLock["Fault"] = buff[46:48]
            dictDoorLock["Firmware"] = buff[48:52]
            dictDoorLock["Status"] = buff[52:54]
            dictDoorLock["Temp"] = buff[54:56]
            dictDoorLock["Event"] = buff[56:58]
            dictDoorLock["Index"] = buff[58:60]
            dictDoorLock["Hdware"] = buff[60:62]
            dictDoorLock["Sign"] = buff[62:64]
            dictDoorLock["vBattery"] = buff[64:66]
            g_logger.info("收到锁设备上报:%s", dictDoorLock)
            # 打包服务器通用回复
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文:%s", sendBuff)
            # 确认是否有该点的其他报文发送
            if dictDoorLock["DeviceID"] in g_dictDeviceId2DoorLock:
                # if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].
                # 密码推送包（无回复的情况下，发送后，立即清理已有报文）
                if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage != "":
                    sendBuff += g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage
                    g_logger.debug("合并密码修改包:%s", g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage)
                    g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage = ""
                # 配置推送包（无回复的情况下，发送后，立即清理已有报文）
                if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_configmodifypackage != "":
                    sendBuff += g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_configmodifypackage
                    g_logger.debug("合并配置修改包:%s", g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_configmodifypackage)
                    g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_configmodifypackage = ""
                if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_remoteopenpackage != "":
                    sendBuff += g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_remoteopenpackage
                    g_logger.debug("合并远程开锁包:%s", g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_remoteopenpackage)
                    g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_remoteopenpackage = ""
                if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_getconfigpackage != "":
                    sendBuff += g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_getconfigpackage
                    g_logger.debug("合并获取配置包:%s", g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_getconfigpackage)
                    g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_getconfigpackage = ""
            return sendBuff
        elif iType == '08':
            # 锁通用回复
            dictDoorLock["Version"] = buff[6:8]
            # dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            dictDoorLock["Result"] = buff[40:42]
            dictDoorLock["AckType"] = buff[42:44]
            dictDoorLock["Firmware"] = buff[44:48]
            dictDoorLock["Hdware"] = buff[60:62]
            g_logger.info("收到锁通用回复:%s", dictDoorLock)
            # 更新门锁的发送信息状态
        elif iType == '33':
            #异常状态报告（锁端发起）
            dictDoorLock["Version"] = buff[6:8]
            dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            dictDoorLock["Event"] = buff[40:42]
            dictDoorLock["AbnormalValue"] = buff[42:46]
            dictDoorLock["Firmware"] = buff[48:52]
            dictDoorLock["Hdware"] = buff[60:62]
            g_logger.info("收到锁异常状态报告:%s", dictDoorLock)
            # 更新锁的故障信息
            # 回复服务器端接收到该信息
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文:%s", sendBuff)
            return sendBuff
        elif iType == '32':
            # 多条开门记录合并上报
            dictDoorLock["Version"] = buff[6:8]
            dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            dictDoorLock["Count"] = buff[40:42]
            listDoorOpenRecord = []
            for index in range(int(dictDoorLock["Count"], 16)):
                doorOpenRecord = {}
                doorOpenRecord["UnlockWay"] = buff[42+index*12: 44+index*12]
                doorOpenRecord["Passindex"] = buff[44+index*12: 46+index*12]
                doorOpenRecord["TimeStamp"] = buff[46+index*12: 54+index*12]
                listDoorOpenRecord.append(doorOpenRecord)
            dictDoorLock["OpenRecord"] = listDoorOpenRecord
            g_logger.info("收到多条开门记录:%s", dictDoorLock)
            #更新开门记录
            #回复锁信息
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文:%s", sendBuff)
            return sendBuff
        elif iType == '71':
            # 密码推送回复包
            dictDoorLock["Version"] = buff[6:8]
            dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            g_logger.info("收到密码推送回复包:%s", dictDoorLock)
            # 更新锁的故障信息
            # 回复服务器端接收到该信息
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文:%s", sendBuff)
            return sendBuff
        elif iType == '52':
            # 配置获取包
            dictDoorLock["Version"] = buff[6:8]
            dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            dictDoorLock["ConfigLength"] = buff[40:44]
            iconfigLength = int(dictDoorLock["ConfigLength"], 16)
            dictDoorLock["configstring"] = buff[44:44+iconfigLength]
            configString = dictDoorLock["configstring"].decode('hex')
            g_logger.info("获取configString:%s",configString)
            listConfigString = configString.split('&')
            for cs in listConfigString:
                configParam = cs.split('=')
                dictDoorLock[configParam[0]] = configParam[1]
            g_logger.info("收到配置获取包:%s", dictDoorLock)


            # 更新锁的故障信息
            # 回复服务器端接收到该信息
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文:%s", sendBuff)
            return sendBuff
        else:
            g_logger.warning("未找到指令类型的报文:%s", buff)
        return ""

    def updateDoorLockInfo(self,dictDoorLock):
        strDoorLockInfo = "版本号:"


        return strDoorLockInfo


class ReceiveCMDThread(threading.Thread):

    def __init__(self, threadname, evtWaitStop, bindPort):
        '''
            线程初始化
        :param threadname:线程名称
        :param evtWaitStop: 线程停止标志
        :param bindPort: 监听端口
        :return:
        '''
        threading.Thread.__init__(self, name=threadname)
        self.m_evtWaitStop = evtWaitStop
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        g_logger.info("建立UDP服务端")
        self.sock.bind(('', bindPort))
        g_logger.info("监听端口:%d", bindPort)
        self.sock.setblocking(0)
        # 非阻塞模式
        self.sock.settimeout(1)
        # 超时时间
        self.totalBuff = ''

    def run(self):
        '''
            UDP服务端进程
        :return:
        '''
        bThdRunFlag = True
        while bThdRunFlag:

            self.m_evtWaitStop.wait(0.3)
            if self.m_evtWaitStop.isSet():

                bThdRunFlag = False
                continue
            try:
                recvBuff, (remoteHost, remotePort) = self.sock.recvfrom(1024)
                g_logger.info("UDP客户端IP:%s,端口:%s,接收到报文:%s", remoteHost, remotePort, recvBuff.encode('hex'))
                sendBuff = self.formatDoorLockBuff(recvBuff)
                    # 发送回复报文
                sendBuffLen = self.sock.sendto(sendBuff, (remoteHost, remotePort))
            except socket.timeout:
                # 接收超时，继续运行
                # g_logger.debug("UDP服务端接收超时")
                continue
            except Exception, ex:
                g_logger.error(ex.message)

    def formatDoorLockBuff(self, buff):
        '''
            通过接收到的信息，向相应的设备发送指令
            属性：
            设备ID：DeviceID
            密码：Password(3-4byte)?直接是16进制数字算为密码
            密码属性：Prop(8bit)：
                新密码写入：IsNewPass(1bit)：1：新密码写入；0：不修改密码
                密码类型：PassType(2bit)：0b01:房东密码；0b10:租客密码
                密码组别：Pass Index（5bit）:0-31
            密码控制标识：OP（1byte）：
                0x00:停用;0x01:启用;0x10:清空密码；0xff:不做控制任何设置
            开始时间：StartTime
            结束时间：EndTime
        :param buff:
        :return:
        '''
        sendBuff =""
        if buff == "1":
            # 设置修改密码
            deviceID = "8694050300000390"
            password = "65432100"
            prop_isnewpass = 1
            prop_passtype = 0b10
            prop_pass_index = 01
            prop = hex((prop_isnewpass << 7)+(prop_passtype << 5)+prop_pass_index)[2:]
            OP = "01"
            startTime = "00000000"
            endTime = "00000000"
            lenth = hex(49)[2:].zfill(4)
            version = "02"
            messageID = "0001"
            timeStamp_Package = hex(int(time.time()))[2:]
            random_number = hex(random.randint(0, 2**31))[2:].zfill(8)
            # time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            sendBuff = "".join(["ab", lenth, version, "61", messageID, "00", deviceID, password,
                               "0000", prop, OP, startTime, endTime, timeStamp_Package, random_number,
                               "0000000000000000"])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("组成密码修改报文:%s", sendBuff)
            if deviceID in g_dictDeviceId2DoorLock:
                g_dictDeviceId2DoorLock[deviceID].door_passwordmodifypackage = sendBuff
                g_logger.info("门锁:%s，添加密码修改报文:%s", deviceID, sendBuff)
        if buff == "2":
            # 修改配置
            # 配置传输最好通过json格式
            messageID = "0002"
            deviceID = "8694050300000390"
            timeStamp = hex(int(time.time()))[2:]

            # sri = 300
            # tn = 8
            # sv = "106.14.13.157"
            # pt = "12001"
            # uc = 0
            # odt = 10
            # nw = 2
            # otpw = 2
            # configBuff = "SRI=%s&TN=%s&SV=%s&PT=%s&UC=%s&ODT=%s&NW=%s&OTPW=%s"% \
            #              (sri, tn, sv, pt, uc, odt, nw, otpw)

            uc = 5
            configBuff = "UC=%s"% (uc)
            g_logger.info(configBuff)
            i_insertBuff = 16 - len(configBuff) % 16
            insertBuff = ""
            for i in range(i_insertBuff):
                insertBuff += "00"
            configBuff = configBuff.encode('hex') + insertBuff
            configLength = hex(len(configBuff)/2)[2:].zfill(4)
            sign = messageID[2:]
            sendBuff = "".join(["ab", "FFFF", "02", "62", messageID, "00", deviceID,
                               timeStamp, configLength, configBuff, sign])
            length = hex(len(sendBuff)/2+1)[2:].zfill(4)

            sendBuff = sendBuff.replace("FFFF", length, 1)
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("组成配置修改报文:%s", sendBuff)
            if deviceID in g_dictDeviceId2DoorLock:
                g_dictDeviceId2DoorLock[deviceID].door_configmodifypackage = sendBuff
                g_logger.info("门锁:%s，添加配置修改报文:%s", deviceID, sendBuff)
        if buff == "3":
            # 远程开锁

            messageID = "0003"
            deviceID = "8694050300000390"
            timeStamp = hex(int(time.time()))[2:]

            sign = messageID[2:]
            sendBuff = "".join(["ab", "0021", "02", "41", messageID, "00", deviceID,
                               timeStamp, "00000000", "00000000", "000000", sign])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("组成远程开锁报文:%s", sendBuff)
            if deviceID in g_dictDeviceId2DoorLock:
                g_dictDeviceId2DoorLock[deviceID].door_remoteopenpackage = sendBuff
                g_logger.info("门锁:%s，添加远程开锁报文:%s", deviceID, sendBuff)
        if buff == "4":
            # 配置获取
            messageID = "0004"
            deviceID = "8694050300000390"
            timeStamp = hex(int(time.time()))[2:]

            sign = messageID[2:]
            sendBuff = "".join(["ab", "0021", "02", "42", messageID, "00", deviceID,
                                   timeStamp, "00000000", "00000000", "000000", sign])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("组成通知设备上报配置参数报文:%s", sendBuff)
            if deviceID in g_dictDeviceId2DoorLock:
                g_dictDeviceId2DoorLock[deviceID].door_getconfigpackage = sendBuff
                g_logger.info("门锁:%s，添加通知设备上报配置参数报文:%s", deviceID, sendBuff)
        return sendBuff


class ReceiveTCPThread(threading.Thread):

    def __init__(self, threadname, evtWaitStop, bindPort):
        '''
            线程初始化
        :param threadname:线程名称
        :param evtWaitStop: 线程停止标志
        :param bindPort: 监听端口
        :return:
        '''
        threading.Thread.__init__(self, name=threadname)
        self.m_evtWaitStop = evtWaitStop
        #self.tcpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        g_logger.info("建立TCP服务端")
        #self.tcpsock.bind(('', bindPort))
        g_logger.info("监听端口:%d", bindPort)
        #self.tcpsock.setblocking(0)
        self.addr = ("", bindPort)

    def run(self):
        '''
            UDP服务端进程
        :return:
        '''
        bThdRunFlag = True
        while bThdRunFlag:

            self.m_evtWaitStop.wait(0.3)
            if self.m_evtWaitStop.isSet():

                bThdRunFlag = False
                continue
            try:

                g_logger.debug("TCP服务端接收消息")
                 #购置TCPServer对象，
                server = ThreadingTCPServer(self.addr, MyBaseRequestHandlerr)

                #启动服务监听
                server.serve_forever()
            except Exception, e:
                print e.args[0], e.args[1]
                g_logger.error("接收出现异常，错误码为:%s，信息为:%s" % (e.args[0],e.args[1]))


class MyBaseRequestHandlerr(BaseRequestHandler):
    """
    #从BaseRequestHandler继承，并重写handle方法
    """
    def handle(self):
        # 循环监听（读取）来自客户端的数据
        while True:
            # 当客户端主动断开连接时，self.recv(1024)会抛出异常
            try:
                recvBuff = self.request.recv(1024)
                g_logger.debug("收到数据:%s" % recvBuff)
                if not recvBuff:
                    g_logger.debug("关闭TCP连接。")
                    break
                # print data
                # self.client_address是客户端的连接(host, port)的元组
                # print "receive from (%r):%r" % (self.client_address, data)
                sendBuff = self.formatDoorLockBuff(recvBuff)

                # sendBuff = g_buffHead_CTCC + hex(len(sendBuff)/2)[2:].zfill(4) + sendBuff
                self.request.sendall(sendBuff)
                # 转换成大写后写回(发生到)客户端
                # self.request.sendall(data.upper())
            except Exception, e:
                print e
                g_logger.error("接收出现异常，%s" % e)
                break

    def formatDoorLockBuff(self, buff):
        '''
            通过接收到的信息，向相应的设备发送指令
            属性：
            设备ID：DeviceID
            密码：Password(3-4byte)?直接是16进制数字算为密码
            密码属性：Prop(8bit)：
                新密码写入：IsNewPass(1bit)：1：新密码写入；0：不修改密码
                密码类型：PassType(2bit)：0b01:房东密码；0b10:租客密码
                密码组别：Pass Index（5bit）:0-31
            密码控制标识：OP（1byte）：
                0x00:停用;0x01:启用;0x10:清空密码；0xff:不做控制任何设置
            开始时间：StartTime
            结束时间：EndTime
        :param buff:
        :return:
        '''
        sendBuff =""
        if buff == "1":
            # 设置修改密码
            deviceID = "8694050300000390"
            password = "12345600"
            prop_isnewpass = 1
            prop_passtype = 0b10
            prop_pass_index = 01
            prop = hex((prop_isnewpass << 7)+(prop_passtype << 5)+prop_pass_index)[2:]
            OP = "01"
            startTime = "00000000"
            endTime = "00000000"
            lenth = hex(48)[2:]
            version = "02"
            messageID = "0001"
            timeStamp_Package = hex(int(time.time()))[2:]
            random_number = hex(random.randint(0, 2*32))[2:]
            # time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            sendBuff = "".join(["ab", lenth, version, "61", messageID, "00", deviceID, password,
                               "0000", prop, OP, startTime, endTime, random_number,
                               "0000000000000000"])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("组成密码修改报文:%s", sendBuff)
            if deviceID in g_dictDeviceId2DoorLock:
                g_dictDeviceId2DoorLock[deviceID].door_passwordmodifypackage = sendBuff
                g_logger.info("门锁:%s，添加密码修改报文:%s", deviceID, sendBuff)
        if buff == "2":
            # 修改配置

            messageID = "0002"
            deviceID = "8694050300000390"
            timeStamp = hex(int(time.time()))[2:]
            sri = 30
            tn = 8
            sv = "106.14.13.157"
            pt = "12001"
            uc = 0
            odt = 10
            nw = 1
            otpw = 1
            configBuff = "SRI=%s&TN=%s&SV=%s&PT=%s&UC=%s&ODT=%s&NW=%s&OTPW=%s"% \
                         (sri, tn, sv, pt, uc, odt, nw, otpw)
            i_insertBuff = len(configBuff) % 16
            insertBuff = ""
            for i in range(i_insertBuff):
                insertBuff += "00"
            configBuff = configBuff.encode('hex') + insertBuff
            configLength = hex(len(configBuff)/2)[2:]
            sign = "02"
            sendBuff = "".join("ab", "FFFF", "01", "62", messageID, "00", deviceID,
                               timeStamp, configLength, configBuff, sign)
            length = hex(len(sendBuff)/2)[2:]

            sendBuff = sendBuff.replace("FFFF", length, 1)
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("组成配置修改报文:%s", sendBuff)
            if deviceID in g_dictDeviceId2DoorLock:
                g_dictDeviceId2DoorLock[deviceID].door_configmodifypackage = sendBuff
                g_logger.info("门锁:%s，添加配置修改报文:%s", deviceID, sendBuff)
        return sendBuff

if __name__ == "__main__":
    g_logger = LogHelper.LogHelper().logHelper
    evtWaitStop = threading.Event()

    # 开启门锁读取进程
    g_dictDeviceId2DoorLock["8694050300000390"] = DoorLock.DoorLock()

    qCommands = Queue.Queue()
    # 开启门锁状态接收进程
    bindUDPPort = 12001
    thdReceiveUdp = ReceiveUDPThread("ReceiveUDPThread", evtWaitStop, bindUDPPort)
    thdReceiveUdp.setDaemon(True)
    thdReceiveUdp.start()

    #开启门锁设置进程
    # bindTCPPort = 13001
    # thdReceiveTcp = ReceiveTCPThread("ReceiveTCPThread", evtWaitStop, bindTCPPort)
    # thdReceiveTcp.setDaemon(True)
    # thdReceiveTcp.start()
    bindCMDPort = 12002
    thdReceiveCMD = ReceiveCMDThread("ReceiveCMDThread", evtWaitStop, bindCMDPort)
    thdReceiveCMD.setDaemon(True)
    thdReceiveCMD.start()


    # 主进程
    bRunFlag = True
    nLoadConfigTimer = 300
    try:
        while bRunFlag:
            if nLoadConfigTimer <= 0:
                g_logger.info("主进程心跳信息")
                nLoadConfigTimer = 300
            else:
                nLoadConfigTimer -= 1

            time.sleep(1)

    except KeyboardInterrupt:

        evtWaitStop.set()
    except:

        evtWaitStop.set()

    if thdReceiveUdp.isAlive():
        thdReceiveUdp.join()
    if thdReceiveCMD.isAlive():
        thdReceiveCMD.join()

    # if log:
    #     log = None


