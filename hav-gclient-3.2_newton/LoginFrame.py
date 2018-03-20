#!/usr/bin/env python
# coding=utf8
'''
Created on Jun 6, 2012

@author: gf
'''

import wx
import os
import threading
from time import sleep

import Setting
import SettingDialog
import Resource
import Session
import MainFrame
import Logger
import ProgressDialog
import ShutdownDialog
import Util
from Setting import FirstUser
from  SendRequests import RestartDeviceRequests

CA_DOWNLOAD_CACHE=[]
PASSWORD = 0

def PassWord():
    return PASSWORD

class LoginThread(threading.Thread):
    def __init__(self, window, url, username, password):
        threading.Thread.__init__(self)
        
        self.url = url
        self.username = username
        self.password = password
        self.window = window
        self.cancel = False
        self.ret = None
        
        
    def stop(self):
        self.cancel = True

    def run(self):
        if self.cancel:
            return
        #wx.CallAfter(self.window.WorkFinished, u'下载根证书... 成功')
        wx.CallAfter(self.window.Update, 1, u'正在连接服务器 ...')
        self.ret = Session.login(self.url, self.username, self.password)            
        wx.CallAfter(self.window.WorkFinished, u'认证成功')
        wx.CallAfter(self.window.Finish)

    def getReturnValue(self):
        return self.ret

class BackgroundPanel(wx.Panel):
    def __init__(self, parent, imagename):
        wx.Panel.__init__(self, parent, -1)
               
        self.width, self.height = wx.ScreenDC().GetSize()
        ##Resource.load(self.width, self.height)
        area = wx.Display().GetGeometry()
        self.width = area.GetWidth()
        self.height = area.GetHeight()

        self.bmp = Resource.ui_login

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        
        self.Bind(wx.EVT_KEY_UP, self.onKeyup)
        
        self.InitControls()

        # Modi by wdr 20150601 start
        '''
        if Setting.getAuto().lower() != 'true' :
            print 'not auto'
            pass
        else :
            print 'auto'
            evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self..GetId())
            #self.autoLogin()
            #self.InitControls()
            #self.password.SetValue('');
            #self.password.SetFocus();
        '''
        # Modi by wdr 20150601 end
        
    def InitControls(self):
        xradio = self.width / 1440.0
        yradio = self.height / 900.0
        
        username = wx.TextCtrl(self, -1, 
                               Setting.getLastLogin(), 
                               style = wx.BORDER_NONE)
        username.SetPosition((int(xradio * 776),
                              int(yradio * 404)))
        username.SetSize((int(xradio * 176),
                          int(yradio * 28)))
        password = wx.TextCtrl(self, -1, '', style = wx.BORDER_NONE|wx.PASSWORD)
        #if Setting.getSign().lower() == 'true' :
        #    password.SetValue(Setting.getPasswd())
        #password = wx.TextCtrl(self, -1, , style = wx.BORDER_NONE|wx.PASSWORD)
        password.SetPosition((int(xradio * 776),
                              int(yradio * 451)))
        password.SetSize((int(xradio * 178),
                          int(yradio * 28)))
        
        self.auto = wx.CheckBox(self, -1, u'自动登录')
        self.auto.SetValue(Setting.getAuto().lower() == 'true')
        self.sign = wx.CheckBox(self, -1, u'保存密码')
        self.sign.SetValue(Setting.getSign().lower() == 'true')
        self.sign.SetPosition((int(xradio * 731),
                              int(yradio * 500)))

        self.auto.SetPosition((int(xradio * 879),
                              int(yradio * 500)))
	
        #self.auto.Enable(False)
        
        self.Bind(wx.EVT_CHECKBOX, self.OnSign, self.sign)
        self.Bind(wx.EVT_CHECKBOX, self.OnAuto, self.auto)
        
        self.sign.SetValue(Setting.getSign().lower() == 'true')
        
        btn_login = wx.BitmapButton(self, -1, Resource.btn_login,None)
        btn_login.SetPosition((int(xradio * 880),
                              int(yradio * 530)))
        btn_login.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.OnLogin, btn_login)

     #   btn_shutdown = wx.BitmapButton(self, -1, Resource.btn_shutdown,None)
     #   btn_shutdown.SetPosition((int(xradio * 1405),
     #                         int(yradio * 865)))
     #   btn_shutdown.SetSize((int(xradio * 36), int(yradio * 36)))
     #   self.Bind(wx.EVT_BUTTON, self.OnShutdown, btn_shutdown)
        
        btn_shutdown = wx.Button(self, -1, u"关机", style=wx.NO_BORDER)
        btn_shutdown.SetPosition((int(xradio * 1385),
                              int(yradio * 865)))
        btn_shutdown.SetSize((int(xradio * 60), int(yradio * 40)))
        self.Bind(wx.EVT_BUTTON, self.OnShutdown, btn_shutdown)

        if username.GetValue() == '':
            username.SetFocus()
        else:
            password.SetFocus()

        self.username = username
        self.password = password
        if Setting.getSign().lower() == 'true':
            password.SetValue(Setting.getPasswd())
            self.auto.SetValue(Setting.getAuto().lower() == 'true')
        else:
            self.auto.SetValue(False)

        # Add by wdr 20150601 start
        if Setting.getAuto().lower() != 'true' :
            #print 'not auto'
            pass
        else :
            #print 'auto'
            evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn_login.GetId())
            wx.PostEvent(self, evt)
            #self.autoLogin()
        # Add by wdr 20150601 end

    def OnSign(self, evt):
        Setting.setSign("%s" % self.sign.GetValue())
        if self.sign.GetValue() != True:
            self.auto.SetValue(False)
            Setting.setAuto("%s" % self.auto.GetValue())
        Setting.setPasswd(self.password.GetValue())
        Setting.save()

    def OnAuto(self, evt):
        #if self.sign.GetValue() == 'True':    
        #    self.auto.Enable(True)
        #else :
        #    self.auto.Enable(False)
        if self.sign.GetValue() != True:
            self.sign.SetValue(True)
        Setting.setAuto("%s" % self.auto.GetValue())
        Setting.setSign("%s" % self.sign.GetValue())
        Setting.setPasswd(self.password.GetValue())
        Setting.save()
        #else:
        #    self.auto.SetValue( self.sign.GetValue() == True )
         
    def OnEraseBackground(self, evt):
        """
        Add a picture to the background
        """
        dc = evt.GetDC()
        
        if not dc:
            dc = wx.ClientDC(self)
            rect = self.GetUpdateRegion().GetBox()
            dc.SetClippingRect(rect)
            
        dc.Clear()

        dc.DrawBitmap(self.bmp, 0, 0)
    def autoLogin(self):
        if Setting.getSign().lower() == 'false':
            return False
        if Setting.getAuto().lower() == 'true' :
            pass
        else :
            return False

        username = Setting.getLastLogin()
        passwd = Setting.getPasswd()
        if username == '' or passwd == '' :
            Util.MessageBox(self, u'缺少用户名或密码!', u'错误', wx.OK | wx.ICON_ERROR)
            return
        
        dlg = ProgressDialog.ProgressDialog(
                        self, u'连接服务器...')
        dlg.CenterOnScreen()
        
        url = 'http://%s:5000/v2.0' % (Setting.getServer())

        RestartDeviceRequests()
        
        loginthread = LoginThread(dlg, url, 
                               username, passwd)
        loginthread.start()
        #dlg.SetPosition((100,100))
        #dlg.Move((Resource.screenX-dlg.))
        #dlg.CenterOnScreen()
        #ret = dlg.ShowModal()
        #dlg.Destroy()
        if dlg.ShowModal() == wx.ID_CANCEL:
            loginthread.stop()
            return
        if loginthread:
            loginthread.stop()
        dlg.Destroy()

        Logger.info("Connect to %s", url)
        Logger.info("UserId: %s, Password: ******", username)
        ret, reason, detail = loginthread.getReturnValue()
        Logger.info("Result: %s, reason: %s, detail: %s", ret, reason, detail)
        
        if not ret:
            Util.MessageBox(self, detail, reason, wx.OK | wx.ICON_ERROR)
            self.ShowFullScreen(True)
            Session.logout()
        else:
            f = MainFrame.MainFrame(self.GetParent(), wx.ScreenDC().GetSize())
            f.ShowFullScreen(True)
            self.GetParent().Hide()
            #f.autOn()
                
    def OnShutdown(self, event):
        dlg = ShutdownDialog.ShutdownDialog(None, u'系统将在5秒钟后关机...')
        dlg.CenterOnScreen()
        dlg.Update(0, u"系统将在5秒钟后关机...")
        ret = dlg.ShowModal()
        dlg.Destroy()
        #os.system("init 0")

    def OnLogin(self, event):
        global PASSWORD
        PASSWORD = self.password.GetValue()        
        # Valid Check
        if self.username.GetValue() == '' or self.password.GetValue() == '' :
            Util.MessageBox(self, u'缺少用户名或密码!', u'错误', wx.OK | wx.ICON_ERROR)
            return
        
        dlg = ProgressDialog.ProgressDialog(
                        self, u'连接服务器...')
        
        url = 'http://%s:5000/v2.0' % (Setting.getServer())

        RestartDeviceRequests()

        loginthread = LoginThread(dlg, url, 
                               self.username.GetValue(), self.password.GetValue())
        loginthread.start()
        #ret = dlg.ShowModal()
        #dlg.Destroy()
        if dlg.ShowModal() == wx.ID_CANCEL:
            loginthread.stop()
            return
        if loginthread:
            loginthread.stop()
        dlg.Destroy()

        Logger.info("Connect to %s", url)
        Logger.info("UserId: %s, Password: ******", self.username.GetValue())
        ret, reason, detail = loginthread.getReturnValue()
        Logger.info("Result: %s, reason: %s, detail: %s", ret, reason, detail)
        
        if Setting.getSign().lower() == 'false':
            self.password.SetValue('')
            
        self.password.SetFocus()

        if not ret:
            Util.MessageBox(self, detail, reason, wx.OK | wx.ICON_ERROR)
            Session.logout()
        else:
            Setting.setLastLogin(FirstUser['firstuser'].username)
            if self.sign.GetValue() == True:
                Setting.setPasswd(self.password.GetValue())
            else:
                Setting.setPasswd('1df#$!cd123~')
            Setting.save()
            area = wx.Display().GetGeometry()
    	    width = area.GetWidth()
            height = area.GetHeight()
            f = MainFrame.MainFrame(self.GetParent(), (width,height))

            f.ShowFullScreen(True)
            self.GetParent().Hide()

    def OnSetting(self, event):
        dlg = SettingDialog.SettingDialog(self)
        dlg.CenterOnScreen()
        ret = dlg.ShowModal()
        if ret == wx.ID_OK:
            dlg.SaveSetting()
        dlg.Destroy()

    def onKeyup(self,event):
        if event.GetKeyCode() == wx.WXK_F4 :
            dlg = SettingDialog.SettingDialog(self)
            #dlg.CenterOnScreen()
            ret = dlg.ShowModal()
            if ret == wx.ID_OK:
                dlg.SaveSetting()
            dlg.Destroy()

class LoginFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, None, -1, 'LoginBackgroundFrame')
        self.backPanel=BackgroundPanel(self, 'images/gf_login_ui.png')

    def autoLogin(self):
        self.backPanel.autoLogin()
            
if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load(1600, 900)
    frame = LoginFrame(None)
    
    frame.Show(True)
    #frame.autoLogin()
    app.MainLoop()
