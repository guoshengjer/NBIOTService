__author__ = 'Eric2'
#!/usr/bin/env python
# -*- coding:utf8 -*-

class DoorLock:
    def __init__(self):
        '''
        初始化门锁类
        door_name：      门锁名称
        door_code:      门锁编码
        door_battery:   门锁电量
        door_csq:       门锁信号强度
        door_fault:     门锁故障状态
        door_firmware:  门锁固件版本
        door_hdware:    门锁硬件版本
        door_status:    门锁开锁状态
        door_temp:      门锁温度
        door_event:     门锁事件
        :return:
        '''
        self.door_name = ''
        self.door_code = ''
        self.door_battery = -1
        self.door_CSQ = -1
        self.door_fault = -1
        self.door_firmware = -1
        self.door_hdware = -1
        self.door_status = -1
        self.door_temp = -1
        self.door_event = -1


    def updateDoorInfo(self, door_info):
        return True

    def updateSqlDoorinfo(self):
        return True
