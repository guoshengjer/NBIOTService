# -*- coding:utf8 -*-
__author__ = 'Eric2'
__date__ = '2018/7/5'


import threading
import Queue
import time
import socket
import DoorLock
import crctest
import LogHelper

g_dictDeviceId2DoorLock = {}
g_logger = None

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
        g_logger.info("监听端口：%d", bindPort)
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

                g_logger.debug("UDP服务端接收消息")
                recvBuff, (remoteHost, remotePort) = self.sock.recvfrom(1024)
                g_logger.info("UDP客户端IP：%s,端口：%s,接收到报文：%s", remoteHost, remotePort, recvBuff.encode('hex'))
                self.totalBuff += recvBuff.encode('hex')
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
                            g_logger.debug("报文：%s", buff)
                            # 解析报文
                            sendBuff = self.decodeBuff(buff)
                            g_logger.debug("即将发送的报文：%s", sendBuff)
                            # 发送回复报文
                            hexBuff = sendBuff.decode('hex')
                            sendBuffLen = self.sock.sendto(hexBuff, (remoteHost, remotePort))
                            g_logger.info("发送报文字节：%s", sendBuffLen)
                        else:
                            break
                    elif iPos == -1:

                        self.totalBuff = ''
                        break
                    else:
                        self.totalBuff = self.totalBuff[iPos:]
            except socket.timeout:
                # 接收超时，继续运行
                g_logger.debug("UDP服务端接收超时")
                continue
            except Exception, ex:
                g_logger.error(ex.message)

    def decodeBuff(self, buff):
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
            g_logger.debug("服务器通用回复报文：%s", sendBuff)
            # 确认是否有该点的其他报文发送
            if dictDoorLock["DeviceID"] in g_dictDeviceId2DoorLock:
                # if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].
                # 密码推送包（无回复的情况下，发送后，立即清理已有报文）
                if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage != "":
                    sendBuff += g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage
                    g_logger.debug("合并密码修改包：%s", g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage)
                    g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_passwordmodifypackage = ""
                # 配置推送包（无回复的情况下，发送后，立即清理已有报文）
                if g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_configmodifypackage != "":
                    sendBuff += g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_configmodifypackage
                    g_logger.debug("合并配置修改包：%s", g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].door_configmodifypackage)
                    g_dictDeviceId2DoorLock[dictDoorLock["DeviceID"]].configmodifypackage = ""
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
            g_logger.info("收到锁通用回复：%s", dictDoorLock)
            # 更新门锁的发送信息状态
        elif iType == '33':
            #异常状态报告（锁端发起）
            dictDoorLock["Version"] = buff[6:8]
            # dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            dictDoorLock["Event"] = buff[40:42]
            dictDoorLock["AbnormalValue"] = buff[42:46]
            dictDoorLock["Firmware"] = buff[48:52]
            dictDoorLock["Hdware"] = buff[60:62]
            g_logger.info("收到锁异常状态报告：%s", dictDoorLock)
            # 更新锁的故障信息
            # 回复服务器端接收到该信息
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文：%s", sendBuff)
            return sendBuff
        elif iType == '32':
            # 多条开门记录合并上报
            dictDoorLock["Version"] = buff[6:8]
            # dictDoorLock["Type"] = buff[8:10]
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
            g_logger.info("收到多条开门记录：%s", dictDoorLock)
            #更新开门记录
            #回复锁信息
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文：%s", sendBuff)
            return sendBuff
        elif iType == '71':
            # 密码推送回复包
            dictDoorLock["Version"] = buff[6:8]
            # dictDoorLock["Type"] = buff[8:10]
            dictDoorLock["MessageID"] = buff[10:14]
            dictDoorLock["DeviceID"] = buff[16:32]
            dictDoorLock["Timestamp"] = buff[32:40]
            g_logger.info("收到密码推送回复包：%s", dictDoorLock)
            # 更新锁的故障信息
            # 回复服务器端接收到该信息
            sendBuff = ''.join(['ab', '00', '21', dictDoorLock["Version"], '88',
                               dictDoorLock["MessageID"], '00', dictDoorLock["DeviceID"],
                               dictDoorLock["Timestamp"], '00', dictDoorLock["Type"], '00',
                               '0000000000000000', dictDoorLock["MessageID"][2:]])
            strcrc8 = crctest.crc8(sendBuff)
            sendBuff += strcrc8
            g_logger.debug("服务器通用回复报文：%s", sendBuff)
            return sendBuff
        else:
            g_logger.warning("未找到指令类型的报文：%s", buff)
        return ""

if __name__ == "__main__":
    g_logger = LogHelper.LogHelper().logHelper
    evtWaitStop = threading.Event()

    qCommands = Queue.Queue()
    bindPort = 12001
    thdReceiveTcp = ReceiveUDPThread("ReceiveUDPThread", evtWaitStop, bindPort)
    thdReceiveTcp.setDaemon(True)
    thdReceiveTcp.start()

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

    if thdReceiveTcp.isAlive():
        thdReceiveTcp.join()

    # if log:
    #     log = None


