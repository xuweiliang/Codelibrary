#!/usr/bin/env python
# coding=utf8

import wx
import Resource
'''
Created on Jul 12, 2012

@author: gf
'''

ST_UNASSIGNED = 'unassigned'
ST_DOWN = 'SHUTOFF'
ST_UP = 'ACTIVE'
ST_POWERING_UP = 'powering_up'
ST_POWEREDDOEN = 'powered_down'
ST_PAUSED = 'PAUSED'
ST_MIGRATING_FROM = 'migrating_from'
ST_MIGRATING_TO = 'migrating_to'
ST_UNKNOWN = 'ERROR'
ST_NOT_RESPONDING = 'not_responding'
ST_WAIT_FOR_LAUNCH = 'wait_for_launch'
ST_REBOOT_IN_PROGRESS = 'reboot_in_progress'
ST_SAVING_STATE = 'saving_state'
ST_RESTORING_STATE= 'restoring_state'
ST_SUSPENDED = 'SUSPENDED'
ST_IMAGE_ILLEGAL = 'image_illegal'
ST_IMAGE_LOCKED = 'image_locked'
ST_POWERING_DOWN = 'powering_down'
ST_FLOAT = 'RUNNING'

STATUS_LIST = (
            ST_UNASSIGNED,
            ST_DOWN,
            ST_UP,
            ST_POWERING_UP,
            ST_POWEREDDOEN,
            ST_PAUSED,
            ST_MIGRATING_FROM,
            ST_MIGRATING_TO,
            ST_UNKNOWN,
            ST_NOT_RESPONDING,
            ST_WAIT_FOR_LAUNCH,
            ST_REBOOT_IN_PROGRESS,
            ST_SAVING_STATE,
            ST_RESTORING_STATE,
            ST_SUSPENDED,
            ST_IMAGE_ILLEGAL,
            ST_IMAGE_LOCKED,
            ST_POWERING_DOWN,
            ST_FLOAT
    )

START_ENABLED_STATUS = (
                        ST_DOWN,
                        ST_SUSPENDED
    )

PAUSE_ENABLED_STATUS = (
                        ST_UP
    )

RESUME_ENABLED_STATUS = (
                        ST_PAUSED
    )

SHUTDOWN_ENABLED_STATUS = (
                        ST_UP,
                        ST_POWERING_UP,
                        ST_SUSPENDED,
                        ST_POWERING_DOWN
    )

STOP_ENABLED_STATUS = (
                       ST_UP,
                       ST_POWERING_UP,
                       ST_PAUSED,
                       ST_SUSPENDED,
                       ST_POWERING_DOWN
    )

REBOOT_ENABLED_STATUS = (
                       ST_UP
    )

CONSOLE_ENABLED_STATUS = (
                        ST_FLOAT,
                        ST_UP,
                        ST_POWERING_UP,
                        ST_REBOOT_IN_PROGRESS,
                        ST_POWERING_DOWN
    )

STATUS_STRING = {
                 ST_UNASSIGNED : u'未指定',
                 ST_DOWN : u'关闭',
                 ST_UP : u'运行',
                 ST_POWERING_UP : u'正在启动',
                 ST_POWEREDDOEN : u'已关闭',
                 ST_PAUSED : u'暂停',
                 ST_MIGRATING_FROM : u'迁移来',
                 ST_MIGRATING_TO : u'迁移到',
                 ST_UNKNOWN : u'未知',
                 ST_NOT_RESPONDING : u'无响应',
                 ST_WAIT_FOR_LAUNCH : u'等待启动',
                 ST_REBOOT_IN_PROGRESS : u'重启中',
                 ST_SAVING_STATE : u'保存状态',
                 ST_RESTORING_STATE : u'恢复状态',
                 ST_SUSPENDED : u'休眠',
                 ST_IMAGE_ILLEGAL : u'镜像无效',
                 ST_IMAGE_LOCKED : u'镜像锁定',
                 ST_POWERING_DOWN : u'正在关闭'
    }

STATUS_IMAGE = {
            ST_UNASSIGNED : 6,
            ST_DOWN : 2,
            ST_UP : 0,
            ST_POWERING_UP : 4,
            ST_POWEREDDOEN : 2,
            ST_PAUSED : 1,
            ST_MIGRATING_FROM : 3,
            ST_MIGRATING_TO : 3,
            ST_UNKNOWN : 6,
            ST_NOT_RESPONDING : 6,
            ST_WAIT_FOR_LAUNCH : 3,
            ST_REBOOT_IN_PROGRESS : 3,
            ST_SAVING_STATE : 5,
            ST_RESTORING_STATE : 4,
            ST_SUSPENDED : 1,
            ST_IMAGE_ILLEGAL : 6,
            ST_IMAGE_LOCKED : 3,
            ST_POWERING_DOWN : 5,
            ST_FLOAT : 7
        }

POWER_STATES = {
    0: "NO STATE",
    1: "RUNNING",
    2: "BLOCKED",
    3: "PAUSED",
    4: "SHUTDOWN",
    5: "SHUTOFF",
    6: "CRASHED",
    7: "SUSPENDED",
    8: "FAILED",
    9: "BUILDING",
}

def get_power_state(instance):
    return POWER_STATES.get(getattr(instance, "OS-EXT-STS:power_state", 0), '')

def GetStatusString(status):
    if status in STATUS_LIST:
        return STATUS_STRING[status]
    return STATUS_STRING[ST_UNKNOWN]

def GetStatusIconList():
    list = wx.ImageList(43, 43, True)
    list.Add(Resource.running)     #0
    list.Add(Resource.paused)      #1
    list.Add(Resource.stopped)     #2
    list.Add(Resource.waiting)     #3
    list.Add(Resource.starting)    #4
    list.Add(Resource.stopping)    #5
    list.Add(Resource.questionmark)#6
    list.Add(Resource.floats)      #7
    
    return list

def GetStatusImage(status):
    if status in STATUS_LIST:
        return STATUS_IMAGE[status]
    return STATUS_IMAGE[ST_UNASSIGNED]   


if __name__ == '__main__':
    pass
