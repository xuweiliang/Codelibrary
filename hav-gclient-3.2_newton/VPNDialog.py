#!/usr/bin/env python
# coding=utf-8

import os
import ethtool
from time import sleep
import wx
import threading
import Setting
import Resource
import Util
import Logger

class VPNDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"VPN设置...",
                           style = wx.BORDER_DOUBLE, size = (290, 336))
    
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        panel = wx.Panel(self)
        panel.SetBackgroundColour('#B3B2B3')
    
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(bmp, 0)
        sizer.Add(panel, 1, flag = wx.EXPAND)
    
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(10)

        staticsizer = wx.BoxSizer(wx.HORIZONTAL)
        staticsizer.Add(wx.StaticText(self, -1, u'Welcome To VPN'), 0, wx.ALIGN_CENTER)

        mainSizer.AddSpacer(10)
        mainSizer.Add(staticsizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER)

        gbsizer=wx.BoxSizer(wx.VERTICAL)

        serverlabel=wx.StaticText(self,-1,label=u'服务器：')
        userlabel=wx.StaticText(self,-1,label=u'用户名：')
        passlabel=wx.StaticText(self,-1,label=u'密  码：')
        self.serverText=wx.TextCtrl(self,-1,Setting.getVPNServer(),size=(200,25))
        self.userText=wx.TextCtrl(self,-1,Setting.getVPNUser(),size=(200,25))

        if Setting.getVPNRem().lower() == "true":
            self.passText=wx.TextCtrl(self,-1,Setting.getVPNPass(),size=(200,25),style=wx.TE_PASSWORD)
        else:
            self.passText=wx.TextCtrl(self,-1,'',size=(200,25),style=wx.TE_PASSWORD)

        if self.passText.GetValue() == '':
            self.passText.SetFocus()
        if self.serverText.GetValue() == '':
            self.serverText.SetFocus()

        gbsizer.Add(serverlabel, 0, wx.EXPAND)
        gbsizer.Add(self.serverText, 0, wx.EXPAND)
        gbsizer.Add(userlabel, 0, wx.EXPAND)
        gbsizer.Add(self.userText, 0, wx.EXPAND)
        gbsizer.Add(passlabel, 0, wx.EXPAND)
        gbsizer.Add(self.passText, 0, wx.EXPAND)

        mainSizer.AddSpacer(10)
        mainSizer.Add(gbsizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER) 

        checksizer = wx.BoxSizer(wx.HORIZONTAL)

        self.rempassCheck=wx.CheckBox(self,-1,label=u'记住密码')
        self.autologCheck=wx.CheckBox(self,-1,label=u'自动登录')

        if Setting.getVPNRem().lower() == 'true':
            self.rempassCheck.SetValue(True)
        else:
            self.rempassCheck.SetValue(False)

        if Setting.getVPNAuto().lower() == 'true':
            self.autologCheck.SetValue(True)
        else:
            self.autologCheck.SetValue(False)

        if Setting.getVPNStatus().lower() == "false" :
            self.EnWidget()
        else:
            self.DisWidget()

        checksizer.Add(self.rempassCheck, 0, wx.ALIGN_LEFT)
        checksizer.AddSpacer(10)
        checksizer.Add(self.autologCheck, 0, wx.ALIGN_RIGHT)

        mainSizer.AddSpacer(10)
        mainSizer.Add(checksizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER) 

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        if Setting.getVPNStatus().lower() == "false" :
            self.btn_login = wx.Button(self, -1, u'登录')
        else:
            self.btn_login = wx.Button(self, -1, u'断开')
        self.btn_cancel = wx.Button(self, -1, u'退出')

        sizer.Add(self.btn_login, 0, wx.ALIGN_CENTER)
        sizer.AddSpacer(20)
        sizer.Add(self.btn_cancel, 0, wx.ALIGN_CENTER)

        self.Bind(wx.EVT_CHECKBOX, self.OnRempass, self.rempassCheck)
        self.Bind(wx.EVT_CHECKBOX, self.OnAutologin, self.autologCheck)
        self.Bind(wx.EVT_BUTTON, self.OnChoice, self.btn_login)
        self.Bind(wx.EVT_BUTTON, self.OnExit, self.btn_cancel)

        mainSizer.AddSpacer(10)
        mainSizer.Add(sizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER)

        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))

    def EnWidget(self):
        self.serverText.Enable()
        self.userText.Enable()
        self.passText.Enable()
        self.rempassCheck.Enable()
        self.autologCheck.Enable()

    def DisWidget(self):
        self.serverText.Disable()
        self.userText.Disable()
        self.passText.Disable()
        self.rempassCheck.Disable()
        self.autologCheck.Disable()

    def OnRempass(self, event):
        Setting.setVPNRem(self.rempassCheck.GetValue())
        Setting.setVPNPass(self.passText.GetValue())
        if self.rempassCheck.GetValue() != True:
            self.autologCheck.SetValue(False)
            Setting.setVPNAuto('%s' % self.autologCheck.GetValue())
        Setting.save()

    def OnAutologin(self, event):
        Setting.setVPNAuto(self.autologCheck.GetValue()) 
        Setting.setVPNPass(self.passText.GetValue())
        if self.autologCheck.GetValue() == True:
            self.rempassCheck.SetValue(True)
            Setting.setVPNRem(True)
        Setting.save()

    def LoginVPN(self, server, user, passwd):
        try:
            device = os.popen("pptpsetup --create Account --server %s --username %s --password %s --start" % (server, user, passwd)).readline()
            self.devices = device.split()[-1]

            Setting.setVPNDevice(self.devices)

            try:
                f = open('/etc/ppp/peers/Account', 'a')
                f.write("file /etc/ppp/options.pptp\n")
                f.close()
            except:
                Logger.info('Configuration VPN file failed!') 
        except:
            Util.MessageBox(self, u'VPN连接失败，请联系系统管理员！', u'错误', wx.OK | wx.ICON_ERROR)
            Logger.info('VPN was loginned unsuccessful!')

        os.system("pppd call Account")

        active_interface = []

        i = 0
        while self.devices not in active_interface:
            sleep(1)
            i = i + 1
            if i >= 16:
                Util.MessageBox(self, u'VPN连接失败，请联系系统管理员！', u'错误', wx.OK | wx.ICON_ERROR)
                Logger.info('VPN was loginned unsuccessful!')
                return
            else:
                active_interface = ethtool.get_active_devices()

        os.system("route add -net 0.0.0.0 dev %s" % self.devices)

        Setting.setVPNStatus('%s' % True)
        self.btn_login.SetLabel(u"断开")
        self.DisWidget()
        Setting.save()
        Logger.info('VPN was loginned successful!')

    def AutoLogin(self, event):
        Logger.info("VPN Status : Autologin VPN account!")
        Setting.setVPNAuto(self.autologCheck.GetValue())
        if self.autologCheck.GetValue() == True:
            self.rempassCheck.SetValue(True)
            Setting.setVPNRem(True)
        Setting.save()
        thread = threading.Thread(target=self.LoginVPN(Setting.getVPNServer(), Setting.getVPNUser(), Setting.getVPNPass()))
        thread.start()

    def OnChoice(self, event):
        if Setting.getVPNStatus().lower() == 'true':
            try:
                f = open('/var/run/%s' % ((Setting.getVPNDevice()) + '.pid'))
                pid = f.readline()
                f.close()
                os.system('kill -INT %s' % pid)
                Logger.info('VPN was logouted successful!')
            except:
                Logger.info('VPN was logouted unsuccessful!')

            self.btn_login.SetLabel(u"登录") 
            Setting.setVPNStatus('%s' % False)
            Setting.save()
            self.EnWidget()

            if self.rempassCheck.GetValue() != True:
                self.passText.SetValue('') 
        else:
            if self.serverText.GetValue()=='' or self.userText.GetValue()=='' or self.passText.GetValue()=='':
                Util.MessageBox(self, u'缺少用户名或密码!', u'错误', wx.OK | wx.ICON_ERROR)
                return

            Logger.info("VPN Status : ManualLogin VPN account!")
            thread = threading.Thread(target=self.LoginVPN(self.serverText.GetValue(),self.userText.GetValue(),self.passText.GetValue()))
            thread.start()

    def OnExit(self, event):
        Setting.setVPNServer(self.serverText.GetValue())
        Setting.setVPNUser(self.userText.GetValue())
        if self.rempassCheck.GetValue() == True:
            Setting.setVPNPass(self.passText.GetValue())
        else:
            Setting.setVPNPass('')
        Setting.setVPNRem('%s' % self.rempassCheck.GetValue())
        Setting.setVPNAuto('%s' % self.autologCheck.GetValue())
        Setting.save()
        Logger.info("")
        self.Destroy()

if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load()
    frame = VPNDialog(None)
    ret = frame.ShowModal()
