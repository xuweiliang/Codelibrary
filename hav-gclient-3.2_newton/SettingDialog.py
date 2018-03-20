#!/usr/bin/env python
# coding=utf-8
'''
Created on Jun 12, 2012

@author: gf
'''
import os
import re
import wx
import ethtool
import Setting
import Resource
import Util
import About
import Advance
import Network
import DisplayPanel
import RDPSettingDialog
import ProgressDialog
import ResolutionDialog
import Main
import Update
import hashlib
import threading
import VPNDialog
from  SendRequests import RestartDeviceRequests

LAN = ["10","172","192"]

class AboutPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        text = wx.TextCtrl(self, style = wx.TE_MULTILINE | wx.TE_READONLY)
        text.AppendText(u'系统信息：\n\n')
        text.AppendText(u'网络信息：\n')
        text.AppendText(Network.GetInfoString());
        text.Bind(wx.EVT_CHAR, self.OnChar)
        sizer.Add(text, 1, wx.EXPAND)
        sizer.AddSpacer(20)
        button = wx.Button(self, -1, u'关于...')
        sizer.Add(button, 0, flag = wx.ALIGN_RIGHT)
        
        self.SetSizer(Util.CreateCenterSizer(sizer, 20))
        
        self.Bind(wx.EVT_BUTTON, self.OnAbout, button)
        
        self.keybuf = ''
        
    def OnChar(self, event):
        self.keybuf = self.keybuf + chr(event.GetKeyCode())
        if len(self.keybuf) > 32:
            self.keybuf = ''
            
        if self.keybuf == 'JUNSHI INFORMATION!' :
            os.system("xterm")
        
    def OnSave(self):
        pass
        
    def OnAbout(self, event):
        dlg = About.AboutDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

class DateTimePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

    def OnSave(self):
        pass

class MultiScreenPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.screen = "%s" % (Main.get_device()[0])

        sizer = wx.BoxSizer(wx.VERTICAL)

        btn_same = wx.Button(self, -1, u'复制屏')
        btn_VGA = wx.Button(self, -1, u'扩展屏(VGA主屏)')
        btn_HDMI = wx.Button(self, -1, u'HDMI主屏')

        self.Bind(wx.EVT_BUTTON, self.onSame, btn_same)
        self.Bind(wx.EVT_BUTTON, self.onVGA, btn_VGA)
        self.Bind(wx.EVT_BUTTON, self.onHDMI, btn_HDMI)

        sizer.AddSpacer(60)
        sizer.Add(btn_same, 0, flag = wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddSpacer(40)
        sizer.Add(btn_VGA, 0, flag = wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddSpacer(40)
        sizer.Add(btn_HDMI, 0, flag = wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddSpacer(40)

        self.SetSizer(Util.CreateCenterSizer(sizer, 10))

    def onSame(self, event):
        if len(Main.get_device_connected()) == 2:
            os.system('xrandr --output %s%s' % (Main.get_device()[2], " --off"))
            os.system('xrandr --output %s%s' % (Main.get_device()[1], " --auto --same-as %s%s") % (Main.get_device()[0], " --auto"))
        else:
            Util.MessageBox(self, '第二屏幕未找到!', u'错误', wx.OK | wx.ICON_ERROR)

    def onVGA(self, event):
        #if len(Main.get_device_connected()) == 2:
        os.system('xrandr --output %s%s' % (Main.get_device()[2], " --off"))
        os.system('xrandr --output %s%s' % (Main.get_device()[1], " --auto --right-of %s%s") % (Main.get_device()[0], " --auto"))
        self.screen = "%s" % (Main.get_device()[0])
        #else:
        #    Util.MessageBox(self, 'VGA设备未插入!', u'错误', wx.OK | wx.ICON_ERROR)

    def onHDMI(self, event):
        if len(Main.get_device_connected()) == 2:
            os.system('xrandr --output %s%s' % (Main.get_device()[2], " --off"))
            os.system('xrandr --output %s%s' % (Main.get_device()[1], " --auto --left-of %s%s") % (Main.get_device()[0], " --auto"))
            self.screen = "%s" % (Main.get_device()[1])
        else:
            Util.MessageBox(self, 'HDMI设备未插入!', u'错误', wx.OK | wx.ICON_ERROR)

    def OnSave(self):
        Setting.setMainScreen(self.screen)

class NetworkPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        midSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        midSizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u"网络接口：")
        midSizer.Add(label, 0, flag = wx.ALIGN_CENTER_VERTICAL)
        self.interChoice = wx.Choice(self, -1, choices = Network.GetInterfaceList())
        self.Bind(wx.EVT_CHOICE, self.OnChoice, self.interChoice)
        midSizer.Add(self.interChoice, 1, flag = wx.ALIGN_CENTER_HORIZONTAL)
        mainSizer.Add(midSizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(10)
        
        self.dhcp = wx.RadioButton(self, -1, u"使用DHCP自动分配")
        self.static = wx.RadioButton(self, -1, u"使用静态地址")
        
        staticbox = wx.StaticBox(self, -1, u"静态地址设置")
        midSizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
        sizer = wx.FlexGridSizer(cols = 2, hgap = 10, vgap = 15)
        sizer.AddGrowableCol(1)
        sizer.Add(wx.StaticText(self, -1, u"IP地址:"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        self.ipaddr = wx.TextCtrl(self)
        sizer.Add(self.ipaddr, 0, wx.EXPAND)
        
        sizer.Add(wx.StaticText(self, -1, u"网络掩码:"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        self.netmask = wx.TextCtrl(self)
        sizer.Add(self.netmask, 0, wx.EXPAND)
        
        sizer.Add(wx.StaticText(self, -1, u"网关:"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        self.gateway = wx.TextCtrl(self)
        sizer.Add(self.gateway, 0, wx.EXPAND)
        
        sizer.Add(wx.StaticText(self, -1, u"DNS:"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        self.dns = wx.TextCtrl(self)
        sizer.Add(self.dns, 0, wx.EXPAND)

        midSizer.Add(Util.CreateCenterSizer(sizer, 10), 1, wx.EXPAND)        
        
        mainSizer.Add(self.dhcp, 0, wx.EXPAND)
        mainSizer.Add(self.static, 0, wx.EXPAND)
        mainSizer.AddSpacer(5)
        mainSizer.Add(midSizer, 0, wx.EXPAND)
        
        #advance = wx.Button(self, -1, u'高级...');
        #self.Bind(wx.EVT_BUTTON, self.OnAdvance, advance)
        #mainSizer.AddSpacer(15)
        #mainSizer.Add(advance, 0, wx.ALIGN_RIGHT);

        vpn = wx.Button(self, -1, u'VPN连接')
        #self.Bind(wx.EVT_BUTTON, self.OnVPN, vpn)
        self.Bind(wx.EVT_BUTTON, self.OnVPN, vpn)
        mainSizer.AddSpacer(15)
        mainSizer.Add(vpn, 1, wx.ALIGN_RIGHT)
        
        self.Bind(wx.EVT_RADIOBUTTON, self.OnDHCP, self.dhcp)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnDHCP, self.static)
        
        self.OnDHCP(None)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))
        
        self.OnChoice(None)

    def OnAdvance(self, event):
        dlg = Advance.AdvanceDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            dlg.save()
        dlg.Destroy()

    def OnVPN(self, event):
        f = open("/etc/ppp/options.pptp")
        bufs = f.readlines()
        f.close()
        if bufs[-1] == "require-mppe-128\n":
            pass
        else:
            f = open("/etc/ppp/options.pptp", 'a') 
            f.write("require-mppe-128\n")  
            f.close()

        active_devices = ethtool.get_active_devices()

        if 'lo' in active_devices:
            active_devices.remove('lo')

        #if Setting.getVPNStatus().lower() == 'true':
        if len(active_devices) < 2:
            Setting.setVPNStatus('%s' % False)
            Setting.save()
        else:
            for i in active_devices:
                if ethtool.get_flags('%s' % i) & ethtool.IFF_POINTOPOINT:
                    Setting.setVPNStatus('%s' % True)
                    Setting.save()
                    break
                elif i == active_devices[-1]:
                    Setting.setVPNStatus('%s' % False)
                    Setting.save()

        dlg = VPNDialog.VPNDialog(self)

        if Setting.getVPNAuto().lower() == 'true' and Setting.getVPNStatus().lower() == 'false':
            dlg.AutoLogin(event)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.save()

        dlg.Destroy()
        
    def OnSave(self):
        interface = self.interChoice.GetStringSelection()
        old_dhcp = Network.IsInterfaceDHCP(interface)
        if self.dns.GetValue():
            Network.SetDNS(self.dns.GetValue())
        if self.dhcp.GetValue() and old_dhcp :
            return
        
        ip, mask, gw, dns = Network.GetInterfaceConf(interface)
        
        if self.static.GetValue() and (not old_dhcp) and \
            self.ipaddr.GetValue() == ip and \
            self.netmask.GetValue() == mask and \
            self.gateway.GetValue() == gw and \
            self.dns.GetValue() == dns :
            return

        try:
            if self.dhcp.GetValue():
                Network.SetDHCP(interface)
            else:
                Network.SetStatic(interface, 
                              self.ipaddr.GetValue(), 
                              self.netmask.GetValue(), 
                              self.gateway.GetValue(), 
                              self.dns.GetValue())
        except IOError, err:
            Util.MessageBox(self, u'更改网络配置出错：\n\n%s' % err, u'错误', wx.OK | wx.ICON_ERROR)
        RestartDeviceRequests()

    def OnDHCP(self, event):
        if self.dhcp.GetValue():
            self.ipaddr.Disable()
            self.netmask.Disable()
            self.gateway.Disable()
            self.dns.Disable()
        else:
            self.ipaddr.Enable()
            self.netmask.Enable()
            self.gateway.Enable()
            self.dns.Enable()

    def OnChoice(self, event):
        interface = self.interChoice.GetStringSelection()
        if Network.IsInterfaceDHCP(interface):
            self.dhcp.SetValue(True)
            self.OnDHCP(None)
        else:
            self.static.SetValue(True)
            self.OnDHCP(None)
            ip, mask, gw, dns = Network.GetInterfaceConf(interface)
            self.ipaddr.SetValue(ip)
            self.netmask.SetValue(mask)
            self.gateway.SetValue(gw)
            self.dns.SetValue(dns)
        
class USBPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
     
        self.hidusb = wx.CheckBox(self, -1, u'挂载HID设备')
        if Setting.getHIDUSB().lower() == 'true':
            self.hidusb.SetValue(True)
        else:
            self.hidusb.SetValue(False)
            
        sizer.Add(self.hidusb, 0, flag = wx.EXPAND)
        sizer.AddSpacer(3)
        label = wx.StaticText(self, -1, u'一些特殊的USB设备，例如：U盾，网银USB KEY\
等，是通过HID接口实现的。如果需要使用这些设备，请复选此单选框。如果没有使用这些设备请不要选中。')
        sizer.Add(label, 0, flag = wx.EXPAND)
        
        self.SetSizer(Util.CreateCenterSizer(sizer, 10))
        
    def OnSave(self):
        Setting.setHIDUSB('%s' % self.hidusb.GetValue())

class ServerPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        sizer = wx.FlexGridSizer(cols = 2, hgap = 10, vgap = 15)
        sizer.AddGrowableCol(1)
        sizer.Add(wx.StaticText(self, -1, u'服务器地址:'),
                  0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.server = wx.TextCtrl(self, -1, 
                             Setting.getServer())
        sizer.Add(self.server, 0, wx.EXPAND )

        self.public = wx.CheckBox(self, -1, u'公网连接')
        if Setting.getPublic().lower() == 'true':
            self.public.SetValue(True)
        else:
            self.public.SetValue(False)
        sizer.Add(self.public, 0, wx.EXPAND)

        box = wx.StaticBox(self, -1, u'虚拟化服务器设置')
        midSizer = wx.StaticBoxSizer(box, wx.VERTICAL)


        midSizer.Add(Util.CreateCenterSizer(sizer, 10), 
                     1, wx.EXPAND)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        help = wx.StaticText(self, -1, u'在首次使用之前请正确设置服务器地址和端口。如果你\
不了解这些设置，请联系你的网络管理员。')
        mainSizer.Add(help, 0, wx.EXPAND)
        mainSizer.AddSpacer((20, 20))
        mainSizer.Add(midSizer, 0, wx.EXPAND)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))

    def OnSave(self):
        Setting.setServer(self.server.GetValue())
        Setting.setPublic('%s' % self.public.GetValue())

        #sp = self.server.GetValue().split(".") 
        #if len(sp) == 4:
        #    if sp[0] in LAN:
        #        Setting.setPublic("False") 
        #    else:
        #        Setting.setPublic("True") 
        #elif len(sp) == 2 or len(sp) == 3:
        #    Setting.setPublic("True")
        #elif len(sp) == 1:
        #    Setting.setPublic("False") 

        RestartDeviceRequests()

#Add by wangderan start
class SetScreen(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        #Get current resolution
        currentRe = self.GetCurrentResolution()

        if len(Main.get_device_connected()) == 1:
            sampleList = ['1920x1080', "1280x1024", '1152x864', '1024x768']  
        elif len(Main.get_device_connected()) == 2:
            sampleList = self.GetSameResolution()
        label = wx.StaticText(self, -1, "分辨率：", (80, 68))  
        if '1920x1080' in str(currentRe):
            self.combo = wx.ComboBox(self, -1, '1920x1080', (150, 60), wx.DefaultSize, sampleList, wx.CB_READONLY)  
            self.current = '1920x1080'
            self.data = '1920x1080'
        elif '1280x1024' in str(currentRe):
            self.combo = wx.ComboBox(self, -1, '1280x1024', (150, 60), wx.DefaultSize, sampleList, wx.CB_READONLY)  
            self.current = '1280x1024'
            self.data = '1280x1024'
        elif '1152x864' in str(currentRe):
            self.combo = wx.ComboBox(self, -1, '1152x864', (150, 60), wx.DefaultSize, sampleList, wx.CB_READONLY)  
            self.current = '1152x864'
            self.data = '1152x864'
        elif '1024x768' in str(currentRe):
            self.combo = wx.ComboBox(self, -1, '1024x768', (150, 60), wx.DefaultSize, sampleList, wx.CB_READONLY)  
            self.current = '1024x768'
            self.data = '1024x768'
        else :
            self.combo = wx.ComboBox(self, -1, '', (150, 60), wx.DefaultSize, sampleList, wx.CB_READONLY)  
            self.current = 'null'
            self.data = 'null'

        self.combo.Bind(wx.EVT_COMBOBOX, self.OnCombo)
        #self.data = 'null'

        #Add by wangderan start
        self.localres = wx.CheckBox(self, -1, u'使用最佳分辨率', (80, 30))
        self.orig =Setting.getLocalResolution().lower()
        if Setting.getLocalResolution().lower() == 'true':
            self.localres.SetValue(True)
            self.combo.Enable(False)
        else:
            self.localres.SetValue(False)
            self.combo.Enable(True)
        self.Bind(wx.EVT_CHECKBOX, self.OnLocal, self.localres)
        
    def OnLocal(self, event):
        Setting.setLocalResolution("%s" % self.localres.GetValue())
        Setting.save()
        if self.localres.GetValue() == True:
            self.combo.Enable(False)
        else:
            self.combo.Enable(True)
#Add by wangderan end
            
    def OnCombo(self, event):
        self.data = event.GetString()

    def OnSave(self):
        if self.orig == Setting.getLocalResolution().lower():
            if self.orig == 'true':
                return 
            else:
                if str(self.current) == str(self.data):
                    return 

        dlg = ResolutionDialog.ResolutionDialog(None, u'系统将在5秒钟后重启...',self.data, self.localres.GetValue())
        dlg.CenterOnScreen()
        dlg.Update(0, u"系统将在5秒钟后重启...")
        ret = dlg.ShowModal()
        dlg.Destroy()

    def GetCurrentResolution(self):
        fp = os.popen('xrandr' , 'r')
        content = fp.read()
        fp.close()

        ttt = re.findall(r'current (.*),', content)
        t = ttt[0].replace(' ','')
        return t

    def GetSameResolution(self):
        result=[]
        samelist=[]
        solution=[]
        command = os.popen("xrandr -q", "r")
        content = command.readlines()
        for line in content:
            result.append(line.split()[0])
        
        result.remove(result[0])
        result.remove(result[-1])
        
        for line in result:
            if result.count(line) == 2:
                samelist.append(line)
        same=set(samelist)
        for line in same:
            flag = line.split("x")[0]
            if int(flag) >= 1000:
                solution.append(line)
        return solution
        
    #def OnSave(self):
    #    if self.data == 'null':
    #        return
    #    if str(self.current) != str(self.data):

    #        dlg = ResolutionDialog.ResolutionDialog(None, u'系统将在5秒钟后重启...',self.data)
    #        dlg.CenterOnScreen()
    #        dlg.Update(0, u"系统将在5秒钟后重启...")
    #        ret = dlg.ShowModal()
    #        dlg.Destroy()
    #def GetCurrentResolution(self):
    #    f = file(r'/etc/X11/xorg.conf', 'rb') 
    #    content = f.read() 
    #    f.close() 

    #    text = re.findall('PreferredMode"\s+"\d{3,4}x\d{3,4}',content) 
    #    currentRe = re.findall('\d{3,4}x\d{3,4}', str(text)) 
    #    return  currentRe

#Add by wangderan end



class ZopleNoteBook(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, -1,
                    size = (21,21), style = wx.BK_DEFAULT)
        
        serverPanel = ServerPanel(self)
        #displayPanel = DisplayPanel.DisplaySetting(self)
        rdpsetting = RDPSettingDialog.RDPSettingPanel(self)
        #usbPanel = USBPanel(self)
        networkPanel = NetworkPanel(self)
        multiScreenPanel = MultiScreenPanel(self)
        #datetimePanel = DateTimePanel(self)
        aboutPanel = AboutPanel(self)
        #Add by wangderan start
        setScreen = SetScreen(self)
        #Add by wangderan end
        
        
        self.AddPage(serverPanel, u'服务器')
        #self.AddPage(displayPanel, u'显示')
        self.AddPage(rdpsetting, u'RDP选项')
        #self.AddPage(usbPanel, u'USB设置')
        self.AddPage(networkPanel, u'网络')
        self.AddPage(multiScreenPanel, u'多屏幕')
        #self.AddPage(datetimePanel, 'Date/Time')
        #Add by wangderan start
        self.AddPage(setScreen, u'终端分辨率')
        #Add by wangderan end
        self.AddPage(aboutPanel, u'本机信息')

class SettingDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"系统设置",
                           style = wx.BORDER_DOUBLE, size = (520, 520)
                           )
        
        Setting.load()
        
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        panel = wx.Panel(self)
        panel.SetBackgroundColour('#B3B2B3')
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(bmp, 0)
        sizer.Add(panel, 1, flag = wx.EXPAND)
        
        nb = ZopleNoteBook(self)
        self.noteBook = nb
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(10)
        mainSizer.Add(nb, 1, flag = wx.EXPAND)

        sizer = wx.FlexGridSizer(cols = 2, hgap = 15, vgap = 20)
        btn_ok = wx.Button(self, wx.ID_OK, u'确定')
        btn_ok.SetDefault()
        btn_cancel = wx.Button(self, wx.ID_CANCEL, u'取消')
        sizer.Add(btn_ok, 0)
        sizer.Add(btn_cancel, 0)
        
        mainSizer.AddSpacer(10)
        mainSizer.Add(sizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))

    def SaveSetting(self):
        for page in self.noteBook.GetChildren():
            page.OnSave()
        Setting.save()

if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load()
    frame = SettingDialog(None)
    ret = frame.ShowModal()
    if (ret == wx.ID_OK):
        frame.SaveSetting()
