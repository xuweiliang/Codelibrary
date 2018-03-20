#!/usr/bin/env python
# coding=utf8
'''
Created on Jun 11, 2012

@author: gf
'''

import wx
import LoginFrame
import Logger
import Version
import Setting
import Session
import Util
import ProgressDialog
import Resource
import MainFrame
import user
import os 
import re 

#add by wangderan start
import threading
#import pyudev
import time
from time import sleep
from Setting import AdminShadow, FirstUser, threadddd
#add by wangderan end

import ServiceThread 
import SendRequests 

def autoLogin():
    if Setting.getSign().lower() == 'false':
        return False
    if Setting.getAuto().lower() == 'true' :
        pass
    else :
        return False
    username = Setting.getLastLogin()
    passwd = Setting.getPasswd()
    if username == '' or passwd == '' :
        Util.MessageBox(None, u'缺少用户名或密码!', u'错误', wx.OK | wx.ICON_ERROR)
        return
        
    dlg = ProgressDialog.ProgressDialog(
                        None, u'连接到服务器...')

    url = 'http://%s:5000/v2.0' % (Setting.getServer())    
    loginthread = LoginFrame.LoginThread(dlg, url, 
                               username, passwd)
    loginthread.start()

    dlg.CenterOnScreen()
    ret = dlg.ShowModal()
    dlg.Destroy()
    if ret == wx.ID_CANCEL:
        loginthread.stop()
        return

    Logger.info("Connect to %s", url)
    Logger.info("UserId: %s, Password: ******", username)
    ret, reason, detail = loginthread.getReturnValue()
    Logger.info("Result: %s, reason: %s, detail: %s", ret, reason, detail)
        
    if not ret:
        Session.logout()
        return False
    else:
        LoginFrame.PASSWORD = passwd
        return True

def get_device():
    command = 'xrandr -q'
    b = os.popen(command,'r')
    content =  b.read()
    b.close()

    text1 = re.findall(r'(\S+) connected',content)
    text2 = re.findall(r'(\S+) disconnected',content)
    text = text1 + text2

    return text

def get_device_connected():
    command = 'xrandr -q'
    b = os.popen(command,'r')
    content =  b.read()
    b.close()

    text1 = re.findall(r'(\S+) connected',content)

    return text1

class CheckHotplugDevice(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.onlineList = None
        self.usbsrv = '/usr/share/hav-gclient/'+'usbsrv'

    def get_vid_and_pid(self, path, id):
        vidFile = '/sys'+path+'/'+id

        try:
            fp = open(vidFile)
        except IOError, e:
            print e
            return None
        else:
            pass
        
        id = fp.read().strip("\n")
        fp.close()
        return id

    def is_input_device(self, vid, pid):
        command = "lsusb -d %s:%s" % (vid, pid)
        bp = os.popen(command, 'r')
        content = bp.read().strip("\n")
        bp.close()

        m1 = re.search('Mouse', content)
        m2 = re.search('Keyboard', content)

        if m1 or m2:
            return True
        return False

    def share_device(self, port):
        time.sleep(0.1)
        command = '%s -share -usbport %s' % (self.usbsrv, port)
        Logger.info("Add: %s", command)

        ret = os.system(command)
        if ret == 0:
            Logger.info("share device success")
        else:
            Logger.info("share device fail")

    def unshare_device(self, port):
        command = '%s -unshare -usbport %s' % (self.usbsrv, port)
        Logger.info("Remove: %s", command)

        ret = os.system(command)
        if ret == 0:
            Logger.info("unshare device success")
        else:
            Logger.info("unshare device fail")

    def scan_device(self):
        bp = os.popen('%s -l' % self.usbsrv, 'r')
        content = bp.read()
        bp.close()
        
        vid = re.findall(r'Vid: (\S+)', content)
        pid = re.findall(r'Pid: (\S+)', content)
        port = re.findall(r'Port: (\S+)', content)
        
        for (item1, item2, item3) in zip(vid, pid, port):
            if (self.is_input_device(item1, item2)):
                continue
            self.share_device(item3)

    def unshare_all_device(self):
        global usbsrv
        bp = os.popen('%s -l' % self.usbsrv, 'r')
        content = bp.read()
        bp.close()
    
        port = re.findall(r'Port: (\S+)', content)
    
        flag = re.findall(r'Status: (.*?)\n', content)
        for (item3, item4) in zip(port, flag):
            if 'shared' in item4:
                self.unshare_device(item3)

    def run(self):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)

        self.unshare_all_device()
        self.scan_device()
        for action, device in monitor:
            if 'BUSNUM' in device.keys():
                if device['ACTION'] == 'add':
                    str = device['DEVPATH'].split("/")[6]

                    vid = self.get_vid_and_pid(device['DEVPATH'], 'idVendor')
                    if vid == None:
                        Logger.info('open vid file error')
                        continue

                    pid = self.get_vid_and_pid(device['DEVPATH'], 'idProduct')
                    if pid == None:
                        Logger.info('open pid file error')
                        continue

                    if (self.is_input_device(vid, pid)):
                        continue
                    self.share_device(str)

        
                if device['ACTION'] == 'remove':
                    str = device['DEVPATH'].split("/")[6]
                    self.unshare_device(str)

def Main():
    f = None
    frame = None
    AdminShadow['admins'] = user.User() 
    FirstUser['firstuser'] = user.User()
    threadddd['devicerequest'] = SendRequests.DeviceRequests()

    server = ServiceThread.Service()
    server.start()

    #add by wangderan start
    #thread = CheckHotplugDevice()
    #thread.start()
    #add by wangderan end 
    #disaltl='xmodmap -e "keycode 64="'
    #disaltr='xmodmap -e "keycode 108="'
    os.system("service chronyd stop");
    os.system("chkconfig chronyd off");
    #os.system("%s"%disaltl)
    #os.system("%s"%disaltr)
    #Logger.info("Argbee Client start, version : %s", Version.string('python-hav-gclient', 3))
    #Logger.info("Get Video Device : %s", " ".join(get_device()))
    #sleep(2)
    #os.system("%s"%disaltl)
    #os.system("%s"%disaltr)

    app = wx.PySimpleApp()
    area = wx.Display().GetGeometry()
    width = area.GetWidth()
    height = area.GetHeight()
    Resource.load(width, height)

    frame = LoginFrame.LoginFrame(None)    
    frame.ShowFullScreen(True)

    '''
    if autoLogin() :
        #f = MainFrame.MainFrame(frame, wx.ScreenDC().GetSize())
        f = MainFrame.MainFrame(frame, (width, height))
        f.Show(True)
    else :
    #frame.autoLogin()
        frame.ShowFullScreen(True)
    #Setting.save()
    #Logger.info( Setting.getIP()
        app.SetTopWindow(frame)
    '''

    devicethread = threadddd.get("devicerequest", SendRequests.DeviceRequests())
    devicethread.start()
    threadddd['devicerequest'] = devicethread

    app.MainLoop()

    Logger.info("Normal Exit")

if __name__ == '__main__':
    Main()
