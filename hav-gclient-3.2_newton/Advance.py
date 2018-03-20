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
import Network

class EditDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u'编辑主机',
                           size = (400, 140))
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.FlexGridSizer(cols = 2, hgap = 10, vgap = 15)
        sizer.AddGrowableCol(1)
        sizer.Add(wx.StaticText(self, -1, u'IP地址：'), 0, wx.EXPAND)
        self.ip = wx.TextCtrl(self, -1, '')
        sizer.Add(self.ip, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, -1, u'主机名(空格分开)：'), 0, wx.EXPAND)
        self.hostname = wx.TextCtrl(self, -1, '')
        sizer.Add(self.hostname, 0, wx.EXPAND)

        mainSizer.Add(sizer, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, u'确定')
        btn_cancel = wx.Button(self, wx.ID_CANCEL, u'取消')
        sizer.Add(btn_ok, 0, wx.EXPAND)
        sizer.AddSpacer(15)
        sizer.Add(btn_cancel, 0, wx.EXPAND)
        
        mainSizer.Add(sizer, 0, wx.ALIGN_RIGHT)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))

class AddDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u'添加主机',
                           size = (400, 140))
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.FlexGridSizer(cols = 2, hgap = 10, vgap = 15)
        sizer.AddGrowableCol(1)
        sizer.Add(wx.StaticText(self, -1, u'IP地址：'), 0, wx.EXPAND)
        self.ip = wx.TextCtrl(self, -1, '')
        sizer.Add(self.ip, 0, wx.EXPAND)
        sizer.Add(wx.StaticText(self, -1, u'主机名(空格分开)：'), 0, wx.EXPAND)
        self.hostname = wx.TextCtrl(self, -1, '')
        sizer.Add(self.hostname, 0, wx.EXPAND)
        
        mainSizer.Add(sizer, 1, wx.EXPAND)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, u'确定')
        btn_cancel = wx.Button(self, wx.ID_CANCEL, u'取消')
        sizer.Add(btn_ok, 0, wx.EXPAND)
        sizer.AddSpacer(15)
        sizer.Add(btn_cancel, 0, wx.EXPAND)
        
        mainSizer.Add(sizer, 0, wx.ALIGN_RIGHT)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))

class AdvanceDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"高级设置...",
                           style = wx.BORDER_DOUBLE, size = (500, 400)
                           )
        
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        panel = wx.Panel(self)
        panel.SetBackgroundColour('#B3B2B3')
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(bmp, 0)
        sizer.Add(panel, 1, flag = wx.EXPAND)
        
        # Add Banner
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)
        
        self.hosts = Network.GetHostList()
        
        # Add DNS Setting
        staticbox = wx.StaticBox(self, -1, u"主机信息")
        midSizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.hostlist = wx.ListCtrl(self, style = 
                             wx.LC_REPORT |
                             wx.BORDER_SUNKEN |
                             wx.LC_SINGLE_SEL )

        self.hostlist.InsertColumn(0, u'IP地址', width = 130)
        self.hostlist.InsertColumn(1, u'主机名（空格分开）', width = 300)
        
        for ip in self.hosts.keys():
            self.hostlist.Append((ip, self.hosts[ip]))
        
        sizer.Add(self.hostlist, 1, wx.EXPAND)
        
        innerSizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_add = wx.Button(self, -1, u'添加')
        btn_edit = wx.Button(self, -1, u'编辑')
        btn_remove = wx.Button(self, -1, u'删除')
        innerSizer.Add(btn_add, 0, wx.EXPAND)
        innerSizer.AddSpacer(15)
        innerSizer.Add(btn_edit, 0, wx.EXPAND)
        innerSizer.AddSpacer(15)
        innerSizer.Add(btn_remove, 0, wx.EXPAND)

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 0, wx.EXPAND)

        midSizer.Add(Util.CreateCenterSizer(sizer, 10), 1, wx.EXPAND)
        mainSizer.Add(midSizer, 1, wx.EXPAND)

        # Add Bottom Button
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, u'确定')
        btn_cancel = wx.Button(self, wx.ID_CANCEL, u'取消')
        
        sizer.Add(btn_ok, 0, wx.ALIGN_CENTER)
        sizer.AddSpacer(20)
        sizer.Add(btn_cancel, 0, wx.ALIGN_CENTER)
        
        self.Bind(wx.EVT_BUTTON, self.OnAdd, btn_add)
        self.Bind(wx.EVT_BUTTON, self.OnEdit, btn_edit)
        self.Bind(wx.EVT_BUTTON, self.OnRemove, btn_remove)

        mainSizer.AddSpacer(10)
        mainSizer.Add(sizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))
    
    def OnAdd(self, event):
        dlg = AddDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            ip = dlg.ip.GetValue().strip()
            hostname = dlg.hostname.GetValue().strip()
            if ip == '' or hostname =='':
                return
            self.hostlist.Append((ip, hostname))
        dlg.Destroy()
        
    def OnEdit(self, event):
        index = self.hostlist.GetFirstSelected()
        if index >= 0:
            dlg = EditDialog(self)
            i_ip = self.hostlist.GetItem(index, 0)
            i_hostname = self.hostlist.GetItem(index, 1)        
            dlg.ip.SetValue(i_ip.GetText())
            dlg.hostname.SetValue(i_hostname.GetText())
            if dlg.ShowModal() == wx.ID_OK:
                i_ip.SetText(dlg.ip.GetValue())
                i_hostname.SetText(dlg.hostname.GetValue())
                self.hostlist.SetItem(i_ip)
                self.hostlist.SetItem(i_hostname)
            dlg.Destroy()
        
    def OnRemove(self, event):
        index = self.hostlist.GetFirstSelected()
        if index >= 0:
            self.hostlist.DeleteItem(index)
        
    def save(self):
        list = {}
        
        for i in range(0, self.hostlist.GetItemCount()):
            ip = self.hostlist.GetItem(i, 0).GetText()
            hostname = self.hostlist.GetItem(i, 1).GetText()
            list[ip] = hostname
        
        Network.SaveHostList(list)

if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load()
    dlg = AdvanceDialog(None)
    if dlg.ShowModal() == wx.ID_OK:
        dlg.save()
    dlg.Destroy()
    app.MainLoop()
