__author__ = 'Eric2'
#!/usr/bin/env python
# -*- coding:utf8 -*-

class DoorLock:
    def __init__(self):
        '''
        ��ʼ��������
        door_name��      ��������
        door_code:      ��������
        door_battery:   ��������
        door_csq:       �����ź�ǿ��
        door_fault:     ��������״̬
        door_firmware:  �����̼��汾
        door_hdware:    ����Ӳ���汾
        door_status:    ��������״̬
        door_temp:      �����¶�
        door_event:     �����¼�
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
