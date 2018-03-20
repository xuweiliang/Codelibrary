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

class TimeoutThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window
        self.cancel = False
        
    def stop(self):
        self.cancel = True
        
    def run(self):
        while not self.cancel:
            try:
                p = self.window.GetProgress() + 1
                wx.CallAfter(self.window.Update, p)
                if p >= 100:
                    wx.CallAfter(self.window.TimedOut)
                    break
            except:
                return
            wx.Sleep(1)

class ProgressDialog(wx.Dialog):
    def __init__(self, parent, msg):
        wx.Dialog.__init__(self, parent, -1, "Progress",
                           style = wx.BORDER_DOUBLE, size = (450, 230)
                           )
        
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        panel = wx.Panel(self)
        panel.SetBackgroundColour('#B3B2B3')

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(bmp, 0)
        sizer.Add(panel, 1, flag=wx.EXPAND)

        #bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        #panel1 = wx.Panel(self)
        #panel1.SetBackgroundColour('#B3B2B3')
        #panel2 = wx.Panel(self)
        #panel2.SetBackgroundColour('#B3B2B3')
        #
        #sizer = wx.BoxSizer(wx.HORIZONTAL)
        #sizer.Add(panel1, 1, flag = wx.EXPAND)
        #sizer.Add(bmp, 0, flag = wx.ALIGN_CENTER)
        #sizer.Add(panel2, 1, flag = wx.EXPAND)
        
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
        btn_cancel = wx.Button(self, wx.ID_CANCEL, u'放弃')
        self.cancel = False
        self.Bind(wx.EVT_BUTTON, self.OnCancel, btn_cancel)
        sizer.Add(btn_cancel, 0)
        
        mainSizer.AddSpacer(20)
        mainSizer.Add(sizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))
        self.timeoutthread = None

    def Update(self, value, msg = None):
        self.progress.SetValue(value)
        if msg:
            self.text.SetLabel(msg)
        if msg and value == 1:
            if self.timeoutthread is not None:
                self.timeoutthread.stop()
                self.timeoutthread = None
            self.timeoutthread = TimeoutThread(self)
            self.timeoutthread.start()
            self.progress.SetBackgroundColour(self.color)
    
    def TimedOut(self):
        self.Update(0, u'超时! 请重试。')
        self.progress.SetBackgroundColour('RED')
        
    def Error(self, msg):
        if self.timeoutthread:
            self.timeoutthread.stop()
            self.tiemoutthread = None
        self.Update(0, msg)
        self.progress.SetBackgroundColour('RED')
    
    def WorkFinished(self, msg):
        if self.timeoutthread:
            self.timeoutthread.stop()
	    self.timeoutthread = None
        self.Update(100, msg)
        
    def Finish(self):
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        try:
            wx.PostEvent(self, evt)
        except:
            return
        
    def OnCancel(self, event):
        if self.timeoutthread is not None:
            self.timeoutthread.stop()
        event.Skip()
    
    def GetProgress(self):
        return self.progress.GetValue()

        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load()
    dlg = ProgressDialog(None, 'Connecting to Server ...')

    dlg.Update(1, 'Connecting...')
    print dlg.ShowModal()

    dlg.Destroy()
    app.MainLoop()
