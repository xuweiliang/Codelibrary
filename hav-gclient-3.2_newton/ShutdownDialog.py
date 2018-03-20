#!/usr/bin/env python
# coding=utf-8
'''
Created on Jun 15, 2012

@author: gf
'''

import wx
import Resource
import Util
import threading
import os

class TimeoutThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window
        self.cancel = False
        
    def stop(self):
        self.cancel = True
        
    def run(self):
        
        while not self.cancel:
            p = self.window.GetProgress() + 20
            wx.CallAfter(self.window.Update, p)
            if p >= 100:
                wx.CallAfter(self.window.TimedOut)
                break
            wx.Sleep(1)

class ShutdownDialog(wx.Dialog):
    def __init__(self, parent, msg):
        wx.Dialog.__init__(self, parent, -1, "Progress",
                           style = wx.BORDER_DOUBLE, size = (450, 230)
                           )
        
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        panel = wx.Panel(self)
        panel.SetBackgroundColour('#B3B2B3')
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(bmp, 0)
        sizer.Add(panel, 1, flag = wx.EXPAND)
        
        self.text = wx.StaticText(self, -1, msg)
        
        self.progress = wx.Gauge(self)
        self.color = self.progress.GetBackgroundColour()
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(15)
        mainSizer.Add(self.text, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(15)
        mainSizer.Add(self.progress, 0, flag = wx.EXPAND)
        
        sizer = wx.FlexGridSizer(cols = 1, hgap = 15, vgap = 20)
        btn_cancel = wx.Button(self, wx.ID_CANCEL, u'取消')
        self.cancel = False
        self.Bind(wx.EVT_BUTTON, self.OnCancel, btn_cancel)
        sizer.Add(btn_cancel, 0)
        
        mainSizer.AddSpacer(20)
        mainSizer.Add(sizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))
        self.timeoutthread = None

    def Update(self, value, msg = None):
        self.progress.SetValue(value)
        time = 5
        if value == 20:
            time =5
        elif value == 40:
            time = 4
        elif value == 60:
            time = 3
        elif value == 80:
            time = 2
        elif value == 100:
            time = 1
        text = u'系统将在%d秒钟后关机...' %(time)
        self.text.SetLabel(text)
        
        if msg and value == 0:
            if self.timeoutthread is not None:
                self.timeoutthread.stop()
                self.timeoutthread = None
            self.timeoutthread = TimeoutThread(self)
            self.timeoutthread.start()
            self.progress.SetBackgroundColour(self.color)
    
    def TimedOut(self):
        os.system("init 0")

        
    def Error(self, msg):
        self.Update(0, msg)
        self.progress.SetBackgroundColour('RED')
    
    def WorkFinished(self, msg):
        if self.timeoutthread:
            self.timeoutthread.stop()
        self.timeoutthread = None
        self.Update(5, msg)
        
    def Finish(self):
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        wx.PostEvent(self, evt)
        
    def OnCancel(self, event):
        if self.timeoutthread is not None:
            self.timeoutthread.stop()
        event.Skip()
    
    def GetProgress(self):
        return self.progress.GetValue()

        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load()
    dlg = ShutdownDialog(None, 'wewe')

    dlg.Update(0, u"系统将在5秒钟后重启")
    print dlg.ShowModal()

    dlg.Destroy()
    app.MainLoop()
