#!/usr/bin/env python
# coding=utf8
'''
Created on Jul 20, 2012

@author: gf
'''

import wx
import Setting
import Util

class DisplaySetting(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        sizer = wx.BoxSizer(wx.VERTICAL)

        '''
        sizer.Add(wx.StaticText(self, -1, u'    用户基于不同的场景，可以选择不同的体验模式。在硬件支持的条件下，可选择视频加速模式。\
若用户在办公模式下（例如：浏览PPT），请选择图形模式。'), 0, wx.EXPAND)
        '''
        sizer.Add(wx.StaticText(self, -1, u'若用户在办公模式下（例如：浏览PPT），请选择图形模式。'), 0, wx.EXPAND)
        sizer.AddSpacer(10)

        #self.hard_acc = wx.CheckBox(self, -1, u'视频加速')
        #self.radio_mjpeg = wx.RadioButton(self, -1, u"MJPEG加速")
        #self.radio_h264 = wx.RadioButton(self, -1, u"H264加速") 
        self.stream = wx.CheckBox(self, -1, u'图形模式')

        #sizer.Add(self.hard_acc, 0, wx.EXPAND)
        #sizer.AddSpacer(5)
        #sizer.Add(self.radio_mjpeg, 0, wx.EXPAND | wx.LEFT, 20)
        #sizer.AddSpacer(5)
        #sizer.Add(self.radio_h264, 0, wx.EXPAND | wx.LEFT, 20)
        #sizer.AddSpacer(5)
        sizer.Add(self.stream, 0, flag = wx.EXPAND)
        sizer.AddSpacer(10)

        #self.Bind(wx.EVT_CHECKBOX, self.Hard_acc, self.hard_acc)
        #self.Bind(wx.EVT_CHECKBOX, self.Stream, self.stream)

        #if Setting.getHARD_ACC().lower() == 'true':
        #    self.hard_acc.SetValue(True)
        #else:
        #    self.hard_acc.SetValue(False)
        #    self.radio_mjpeg.Enable(False)
        #    self.radio_h264.Enable(False)

        #if Setting.getMJPEG().lower() == 'true':
        #    self.radio_mjpeg.SetValue(True)
        #else:
        #    self.radio_mjpeg.SetValue(False)

        #if Setting.getH264().lower() == 'true':
        #    self.radio_h264.SetValue(True)
        #else:
        #    self.radio_h264.SetValue(False)

        if Setting.getStream().lower() == 'true':
            self.stream.SetValue(True)
        else:
            self.stream.SetValue(False)

        self.SetSizer(Util.CreateCenterSizer(sizer, 10))
        
    def Hard_acc(self, event):
        if self.hard_acc.GetValue() != True:
            self.radio_mjpeg.Enable(False)
            self.radio_h264.Enable(False)
            self.stream.Enable(True)
        else:
            self.radio_mjpeg.Enable(True)
            self.radio_h264.Enable(True)
            self.stream.Enable(False)

    def Stream(self, event):
        if self.stream.GetValue() != True:
            self.hard_acc.Enable(True)
        else:
            self.hard_acc.Enable(False)

    def OnSave(self):
        #Setting.setHARD_ACC('%s' % self.hard_acc.GetValue())
        #Setting.setH264('%s' % self.radio_h264.GetValue())
        #Setting.setMJPEG('%s' % self.radio_mjpeg.GetValue())
        Setting.setStream('%s' % self.stream.GetValue())

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = wx.Frame(None)
    ds = DisplaySetting(frame)
    frame.Show()
    app.MainLoop()
