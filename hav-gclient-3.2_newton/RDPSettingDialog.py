#!/usr/bin/env python
#coding=utf-8

import wx
import os
import re
import Logger
import commands
import subprocess
from subprocess import *
import threading
import time
import Resource

import Setting
import Util

class CheckHotplugDevice(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.onlineList = None
        self.usbip = '/usr/sbin/'+'usbip'

    def get_vid_and_pid(self, path, id):
        vidFile = '/sys'+path+'/'+id

        try:
            fp = open(vidFile)
        except IOError, e:
            print e
            return None
        else:
            #print 'success'
            pass
    
        id = fp.read().strip("\n")
        fp.close()
        return id

    def is_input_device(self, vid, pid):
        command = "lsusb -d %s:%s" % (vid, pid)
        bp = os.popen(command, 'r')
        content = bp.read().strip("\n")
        print content
        bp.close()

        m1 = re.search('Mouse', content)
        m2 = re.search('Keyboard', content)
        m3 = re.search('Intel Corp', content)
        m4 = re.search(r':\w{4}\s{1}\w+', content)
        if m1 or m2 or m3 or (m4 == None):
            return True
        return False

    def bind_device(self, port):
        #if Setting.getRdpUsbip().lower() == 'true':
            #return
        time.sleep(0.1)
        command = 'usbip bind -b %s' % port
        Logger.info("Add: %s", command)
        ret = os.system(command)
        if ret == 0:
            print 'bind device success: %s' % port
            Logger.info("bind device success")
        else:
            print 'bind device fail: %s' % port
            Logger.info("bind device fail") 

    def mount_device(self, port):
        os.system('usbip attach --remote 127.0.0.1 --busid=%s' % port)
        time.sleep(0.7)
        os.system('usbip port')
        os.system('usbip detach --port=0')    

    def unbind_device(self, port):
        if Setting.getRdpUsbip().lower() == 'true':
            return

        command = '%s unbind --busid=%s' % (self.usbip, port)
        print command
        Logger.info("Remove: %s", command)

        ret = os.system(command)
        if ret == 0:
            print 'unbind device success'
            Logger.info("unbind device success")
        else:
            print 'unbind device fail'
            Logger.info("unbind device fail")

    def scan_device(self):
        os.system('modprobe usbip-host')
        os.system('modprobe vhci-hcd')
        os.system('usbipd -D')
        bp = os.popen('%s list -l' % self.usbip, 'r')
        content = bp.read()
        bp.close()
        print content
        port = re.findall(r' - busid (.*) ', content)
        print port
        l1 = re.findall(r'\(((?:[a-z]|\d)*):', content) 
        vid = sorted(set(l1),key=l1.index)
        print vid
        l2 = re.findall(r'(?:[a-zA-Z]|[0-9])+:(.*?)\)', content)
        pid = sorted(set(l2),key=l2.index)
        print pid

        device = []
        for (item1, item2, item3) in zip(vid, pid, port):
            if (self.is_input_device(item1, item2)):
                continue
            vp = '%s:%s' % (item1, item2)
            temp = [vp, item3] #[vid:pid, port]
            device.append(temp)
        return device

    def unshare_all_device(self):
        global usbip
        bp = os.popen('%s list -l' % self.usbip, 'r')
        content = bp.read()
        bp.close()

        port = re.findall(r'Port: (\S+)', content)

        flag = re.findall(r'Status: (.*?)\n', content)
        for (item3, item4) in zip(port, flag):
            if 'shared' in item4:
                self.unshare_device(item3)

    def check_device_is_bind(self, port):
        command = 'usbip list -r 127.0.0.1'
        fp = os.popen(command, 'r')
        content = fp.read()
        fp.close()

        if port in content:
            return True
        else:
            return False
     
    def run(self):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)

        for action, device in monitor:
            if 'BUSNUM' in device.keys():
                if device['ACTION'] == 'add':
                    port = device['DEVPATH'].split("/")[5]

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
                    self.bind_device(port)


                if device['ACTION'] == 'remove':
                    port = device['DEVPATH'].split("/")[5]
                    #self.unbind_device(port)

class RDPSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)       

        sizer = wx.BoxSizer(wx.VERTICAL)

#        sizer.Add(wx.StaticText(self, -1, u'    xxxxxxxxxxx'), 0, wx.EXPAND)
#        sizer.AddSpacer(10)

        self.allow_device = wx.CheckBox(self, -1, u"允许映射本地USB设备")
        #self.auto_connect = wx.CheckBox(self, -1, u"断开连接后重新连接")
        #self.headset_micro = wx.CheckBox(self, -1, u"允许映射本地耳机、麦克风设备")
        self.remotefx = wx.CheckBox(self, -1, u"启用RemoteFX显示特性")

        sizer.Add(self.allow_device, 0, wx.EXPAND)
        sizer.AddSpacer(5)
        #sizer.Add(self.auto_connect, 0, wx.EXPAND)
        #sizer.AddSpacer(5)
        #sizer.Add(self.headset_micro, 0, wx.EXPAND)
        #sizer.AddSpacer(5)
        sizer.Add(self.remotefx, 0, wx.EXPAND)
        sizer.AddSpacer(20)

        if Setting.getAllow_device().lower() == 'true':
            self.allow_device.SetValue(True)
        else:
            self.allow_device.SetValue(False)

        #if Setting.getAuto_connect().lower() == 'true':
        #    self.auto_connect.SetValue(True)
        #else:
        #    self.auto_connect.SetValue(False)

        #if Setting.getHeadset_micro().lower() == 'true':
        #    self.headset_micro.SetValue(True)
        #else:
        #    self.headset_micro.SetValue(False)

        if Setting.getRemotefx().lower() == 'true':
            self.remotefx.SetValue(True)
        else:
            self.remotefx.SetValue(False)
        
        self.mainSizer.Add(sizer, 0, wx.EXPAND)

        label = wx.StaticText(self, -1, u'RDP设置：')
        self.mainSizer.Add(label, 0, flag = wx.EXPAND | wx.ALL) 
        
        self.autoCheckBox = wx.CheckBox(self, -1, u'自动(将自动重定向除鼠标键盘之外的设备)')
        self.Bind(wx.EVT_CHECKBOX, self.OnAutoCheckBox, self.autoCheckBox)
        self.mainSizer.Add(self.autoCheckBox, 0, flag = wx.EXPAND)
        self.mainSizer.AddSpacer(3)
        label = wx.StaticText(self, -1, u'    点击检测按钮，进行设备检测，手动勾选进行重定向')
        self.mainSizer.Add(label, 0, flag = wx.EXPAND)

        self.refresh = wx.Button(self, -1, u'刷新')
        self.mainSizer.Add(self.refresh, 0)

        self.midSizer = wx.BoxSizer(wx.VERTICAL)

        self.topSizer.Add(self.mainSizer, 0, wx.EXPAND)
        self.topSizer.Add(self.midSizer, 0, wx.EXPAND)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.refresh)

        if Setting.getRdpUsbip().lower() == 'true':
            #auto
            self.refresh.Enable(False)
            self.autoCheckBox.SetValue(True)
        else:
            #sign
            self.refresh.Enable(True)
            self.autoCheckBox.SetValue(False)


        self.usb_list = []
        self.SetSizerAndFit(self.topSizer)

        
        #self.SetSizer(Util.CreateCenterSizer(sizer, 10))
    
    def OnAutoCheckBox(self, event):
        if self.autoCheckBox.GetValue() == True:
            #auto
            self.refresh.Enable(False)
            for device in self.usb_list:
                device.Enable(False)
        else:
            #sign
            self.refresh.Enable(True)
            for device in self.usb_list:
                device.Enable(True)

    def OnRefresh(self, event):
        self.midSizer = wx.BoxSizer(wx.VERTICAL)
        self.usbipdialog = CheckHotplugDevice()
        self.device = self.usbipdialog.scan_device()
        for usb in self.usb_list:
             usb.Destroy()
        self.usb_list = []

        value = 0
        for i in self.device:

            iManufacturer, iProduct = self.get_manufacturer_and_product(i[1])

            usb = wx.CheckBox(self, value, iManufacturer + ' ' + iProduct)
            self.Bind(wx.EVT_CHECKBOX, self.OnCheckBox, usb)
            self.usb_list.append(usb)
            self.midSizer.Add(usb, 3, wx.EXPAND)
            value = value + 1

            if self.usbipdialog.check_device_is_bind(i[1]):
                usb.SetValue(True)
            else:
                usb.SetValue(False)


        self.topSizer.Add(self.midSizer, 0, wx.EXPAND)
        self.SetSizerAndFit(self.topSizer)

    def OnCheckBox(self, event):
        id = event.GetId()
        #print self.usb_list[id].GetValue()
        #print self.device[id]

    def get_manufacturer_and_product(self, port):
        path = '/sys/bus/usb/devices/' + port

        manufacturerPath = path + '/manufacturer'
        if os.path.exists(manufacturerPath):
            manufacturer = self.open_and_read_file(manufacturerPath)
        else:
            manufacturer = 'None'

        productPath = path + '/product'
        product = self.open_and_read_file(productPath)

        return manufacturer, product

    def open_and_read_file(self, name):
        fp = open(name)
        content = fp.read().strip('\n')
        fp.close()
        return content



    def OnSave(self):
        Setting.setAllow_device('%s' % self.allow_device.GetValue())
        #Setting.setAuto_connect('%s' % self.auto_connect.GetValue())
        #Setting.setHeadset_micro('%s' % self.headset_micro.GetValue())
        Setting.setRemotefx('%s' % self.remotefx.GetValue())
        Setting.setRdpUsbip('%s' % self.autoCheckBox.GetValue())
        Setting.save()
        if self.autoCheckBox.GetValue() == True:
            self.OnRefresh(-1)
            for device in self.usb_list:
                self.usbipdialog.bind_device(self.device[device.GetId()][1])
                self.usbipdialog.mount_device(self.device[device.GetId()][1])
        else:
            for device in self.usb_list:
                if True == device.GetValue():
                    print self.device[device.GetId()]
                    #if self.usbipdialog.check_device_is_bind(self.device[device.GetId()][1]) == False:
                    self.usbipdialog.bind_device(self.device[device.GetId()][1])
                    self.usbipdialog.mount_device(self.device[device.GetId()][1])
                else:
                    print self.device[device.GetId()]
                    if self.usbipdialog.check_device_is_bind(self.device[device.GetId()][1]) == True:
                        self.usbipdialog.unbind_device(self.device[device.GetId()][1])

if __name__ == '__main__':
    thread = CheckHotplugDevice()
    thread.start()
    app = wx.PySimpleApp()
    frame = wx.Frame(None)
    ds = RDPSettingPanel(frame)
    frame.Show()
    app.MainLoop()
