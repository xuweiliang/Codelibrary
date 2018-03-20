#!/usr/bin/env python
# coding=utf-8
'''
Created on Jun 18, 2012

@author: gf
'''

import wx
import Resource
import Util
import Version
import Update

class AboutDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"关于...",
                           style = wx.BORDER_DOUBLE, size = (500, 260)
                           )
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        panel = wx.Panel(self)
        panel.SetBackgroundColour('#B3B2B3')
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(bmp, 0)
        sizer.Add(panel, 1, flag = wx.EXPAND)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        
        font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.BOLD, wx.NORMAL)

        #Get hav-gclient version
        version = Version.string('python-hav-gclient', 3)
        #label = wx.StaticText(self, -1, 'hav-gclient: %s' %(version))
        label = wx.StaticText(self, -1, '客户端: %s' %(version))
        label.SetFont(font)
        mainSizer.AddSpacer(30)
        mainSizer.Add(label, 0, flag = wx.ALIGN_CENTER_HORIZONTAL)
        mainSizer.AddSpacer(10)
        #label = wx.StaticText(self, -1, u'2014-01-08')

        #versionSpice = Version.string('spice-gtk', 2)
        versionVirtViewer = Version.string('virt-viewer', 2)
        
        #label = wx.StaticText(self, -1, 'SC-client: %s' %(versionVirtViewer))
        label = wx.StaticText(self, -1, '协议: %s' %(versionVirtViewer))
        mainSizer.Add(label, 0, flag = wx.ALIGN_CENTER_HORIZONTAL)
        
        mainSizer.AddSpacer(20)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_ok = wx.Button(self, wx.ID_OK, u'确定')
        
        sizer.Add(btn_ok, 0, flag = wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddSpacer(100)
        btn_update = wx.Button(self, -1, u'检查更新')
        self.Bind(wx.EVT_BUTTON, self.OnUpdate, btn_update)
        
        sizer.Add(btn_update, 0, flag = wx.ALIGN_CENTER_HORIZONTAL)

        mainSizer.AddSpacer(10)
        mainSizer.Add(sizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))
        
    def OnUpdate(self, event):
        try:
            ret = Update.CheckNow()

            '''
            if ret['version'] <= Version.string('python-hav-gclient', 3):
                Util.MessageBox(self, u'系统已经是最新，无需更新！', u'信息', wx.OK | wx.ICON_INFORMATION)
                return
            '''
            
            if Util.MessageBox(self, 
                                   '当前版本是： %s\n最新版本是： %s\n\n您确定要更新到最新版吗？' % (Version.string('python-hav-gclient', 3), ret['version']), 
                                   u'确认', wx.YES_NO | wx.ICON_QUESTION) == wx.ID_NO:
                return
            
            Update.DownloadPackage(ret['filename'], ret['md5'])
            Update.InstallPackage(ret['filename'], ret['hav_gclient'],ret['spice_glib'],ret['spice_gtk'],ret['spice_gtk_tools'],ret['virt_viewer'],ret['add'])
            #Update.InstallPackage(ret['filename'])

            Util.MessageBox(self, '更新成功！\n新版程序会在下次系统启动时生效。', u'成功', wx.OK | wx.ICON_INFORMATION)
        except:
            Util.MessageBox(self, '检查更新失败！如果需要更新系统，请联系系统管理员。', u'错误', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE)        
        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load()
    dlg = AboutDialog(None)
    dlg.ShowModal()
    dlg.Destroy()
    app.MainLoop()
