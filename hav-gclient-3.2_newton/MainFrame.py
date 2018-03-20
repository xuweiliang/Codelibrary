#!/usr/bin/env python
# coding: utf-8
'''
Created on Jun 11, 2012

@author: gf
'''

import wx
import time
import wx.lib.buttons  as buttons
import wx.lib.agw.pygauge as PG

import Console
import Resource
import Session
import SettingDialog
import backend
import ProgressDialog
import threading
#Add by wangderan 20150525 start
import thread
#Add by wangderan 20150525 end
import Setting
import Util
import Logger
import About
import ChangePw
import VM
import havclient
import LoginFrame
import RDPLoginDialog
import consoleInfo
import user
from Setting import AdminShadow,FirstUser

LBVM = LBCPU = LBRAM = LBDISK = LBDISPLAY = LBSTATUS = LBUSB = LBCOUNT = 0
vms_len = 0
vms_dict = {}

def Analy(vms):
    for i in vms:
        try:
            vm_flavor = havclient.flavor_get(i.tenant_id, FirstUser['firstuser'], i.flavor['id'])
        except Exception,e:
            Logger.info('Time out: %s in flavor_get', e)

        try:
            usb = havclient.get_control(AdminShadow['admins'], i, i.tenant_id).get('usb', None)
            if usb:
                vm_usb = u'允许'
            else:
                vm_usb = u'不允许'
        except:
            vm_usb = u'不允许'
            Logger.info('The usb_policy has not been provided!')

        try:
            vm_vcpu = i.vcpus
        except:
            try:
                vm_vcpu = vm_flavor.vcpus
            except:
                vm_vcpu = u'UNKNOWN' 

        try:
            vm_ram = i.rams
        except:
            try:
                vm_ram = vm_flavor.ram
            except:
                vm_ram = u'UNKNOWN'

        vm_name = i.name 
        try:
            vm_type = havclient.get_vm_type(AdminShadow['admins'], i.tenant_id, i)
        except:
            vm_type = u'UNKNOWN'

        try:
            vm_disk = vm_flavor.disk + vm_flavor.ephemeral
        except:
            vm_disk = u'UNKNOWN'

        if i.status == u'ACTIVE':
            vm_status = 'RUNNING'
        else:
            vm_status = VM.get_power_state(i) 
        vms_total= vms_len

        vminfo = {}
        vminfo[u'vmname'] = vm_name
        vminfo[u'vmvcpu'] = vm_vcpu
        vminfo[u'vmram'] = vm_ram
        vminfo[u'vmdisk'] = vm_disk
        vminfo[u'vmstatus'] = vm_status
        vminfo[u'vmusb'] = vm_usb
        vminfo[u'vmtype'] = vm_type
        vminfo[u'vmslen'] = vms_total

        vms_dict[i.name] = vminfo

class BannerPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1,
                          pos = wx.DefaultPosition,
                          size = (200, 100))
        self.SetBackgroundColour('#B3B2B3')
        
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        mainSizer.Add(bmp, 1)
        
        info = wx.StaticText(self, -1, u"当前登录用户: %s" % FirstUser['firstuser'].username)
        font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.BOLD, wx.NORMAL)
        info.SetFont(font)

        area = wx.Display().GetGeometry()
        width = area.GetWidth()
        version = wx.StaticText(self, -1, u'vClient客户端', pos=wx.Point((width-361)/2, 9))

        versionfont = wx.Font(24, wx.FONTFAMILY_SWISS, wx.BOLD, wx.NORMAL)
        version.SetFont(versionfont)

        #settingBtn = wx.Button(self, -1, u"设置", style=wx.NO_BORDER)
        logoutBtn = wx.Button(self, -1, u"退出账号", style=wx.NO_BORDER)
        changepwBtn = wx.Button(self, -1, u"修改密码", style=wx.NO_BORDER)
        
        self.Bind(wx.EVT_BUTTON, self.OnLogOut, logoutBtn)
        #self.Bind(wx.EVT_BUTTON, self.OnSetting, settingBtn)
        self.Bind(wx.EVT_BUTTON, self.OnChangePw, changepwBtn)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(Util.CreateCenterSizer(info, 5), 1, flag = wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM)
        
        linesizer = wx.BoxSizer(wx.HORIZONTAL)
        #linesizer.Add(settingBtn, 0, flag = wx.EXPAND)
        linesizer.AddSpacer(3)
        linesizer.Add(logoutBtn, 0, flag = wx.EXPAND)
        linesizer.AddSpacer(3)
        linesizer.Add(changepwBtn, 0, flag = wx.EXPAND)
        
        sizer.Add(linesizer, 0, flag = wx.EXPAND)
        
        mainSizer.Add(sizer, 0, wx.EXPAND)
        
        self.SetSizer(mainSizer)
    
    def OnAbout(self, event):
        dlg = About.AboutDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
        event.Skip()

    def OnChangePw(self, event):
        if FirstUser['firstuser'].username == u'admin' or FirstUser['firstuser'].username == u'AdminShadow':
            Util.MessageBox(self, '操作失败！\n\n管理员用户不能在客户端修改密码！', u'错误', wx.OK | wx.ICON_ERROR)
            return

        dlg = ChangePw.ChangePwDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

        if dlg.Flag:
            FirstUser['firstuser'] = user.User()
            self.GetParent().Close()
            Util.RunShellWithLog('pkill remote-viewer')
            event.Skip()
    
    def OnLogOut(self, event):
        self.GetParent().Close()
        Util.RunShellWithLog('pkill remote-viewer')
        event.Skip()
        
    def OnSetting(self, event):
        dlg = SettingDialog.SettingDialog(self)
        dlg.CenterOnScreen()
        ret = dlg.ShowModal()
        if ret == wx.ID_OK:
            dlg.SaveSetting()
        dlg.Destroy()
        event.Skip()
        
class RefreshThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window
        self.cancel = False
        self.all = False
        self.autoConsole = True
        self.refresh = 0
        self.tenRefresh = 900
        # Add by wangderan 20150525 start
        self.lock = thread.allocate_lock()
        # Add by wangderan 20150525 end

    def stop(self):
        self.cancel = True
        
    def refresh_all(self):
        # Add by wangderan 20150525 start 
        self.lock.acquire()
        # Add by wangderan 20150525 end
        self.all = True
        # Add by wangderan 20150525 start 
        self.lock.release()
        # Add by wangderan 20150525 end
        self.refresh = 1
        self.vminfo = True
        
    def refresh_all_stop(self):
        self.all = False

    def setRefresh(self):
	    self.refresh = 20

    def refreshVM(self):
        if self.all:
            dialog = self.window.dlg
            Logger.info("Refresh VMs List:")

        try:
            if (not isinstance(AdminShadow['admins'], user.User) or 
                AdminShadow['admins'].is_token_expired() or 
                AdminShadow['admins'].endpoint is None or
                AdminShadow['admins'].endpoint != FirstUser['firstuser'].endpoint):
                url = 'http://%s%s' % (Setting.getServer(), ":5000/v2.0")
                backends = backend.KeystoneBackend()
                AdminS, test = backends.authenticate(username = u'AdminShadow',
                            password = u'adminshadow123', tenant=None,
                            auth_url=url, otp=None)
                AdminShadow['admins'] = AdminS
        except:
            AdminShadow['admins'] = user.User()
            Logger.error("AdminShadow logins failed!!!")
            if self.all:
                wx.CallAfter(dialog.Error, u'认证失败，请检查网络后再试！')
            return

        import pdb
        pdb.set_trace()
        global vms
        vms = [] 
        floatpool = []
        dedicated = []
        #import pdb
        #pdb.set_trace()
        try:

            tenants = havclient.tenant_list(AdminShadow['admins'], FirstUser['firstuser'].id)
            for i in tenants[0]:
                if getattr(i, u'pool_type', 'pool_type') == u'float':
                    floatpool.append(i)
                else:
                    if i.name == u'services':
                        pass
                    else:
                        dedicated.append(i)
        except:
            Logger.info("Failed to get all of the pool!")
            if self.all:
                wx.CallAfter(dialog.Error, u'获取池信息失败，请检查网络后再试！')
            Logger.info("Refresh ststus:Refresh failed！")
            return 

        try:
            authorized_tenants = FirstUser['firstuser']._authorized_tenants.keys()
            for i in tenants[0]:
                if i.id not in authorized_tenants:
                    Logger.info("Discover the new pool,now relogin.")
                    backends = backend.KeystoneBackend()
                    Fuser, Flag = backends.authenticate(username=FirstUser['firstuser'].username, 
                            password=FirstUser['firstuser'].password, tenant=None,
                            auth_url=FirstUser['firstuser'].endpoint, otp=None)
                    FirstUser['firstuser'] = Fuser
                    Logger.info("Discover the new pool,and relogin successfully.")
        except Exception as e:
            FirstUser['firstuser'] = user.User()
            Logger.error("Discover the new pool,but relogin failed.")
            if self.all:
                wx.CallAfter(dialog.Error, u'获取新填的池信息失败，请退出重新登录！')
            return 

        vmlist = self.window.vmlist

        if self.all:
            try:
                wx.CallAfter(vmlist.DeleteAllItems)
            except: 
                pass
        try:
            for i in dedicated:
                try:
                    vms = vms + havclient.vm_list(FirstUser['firstuser'], True, i.id)
                except:
                    pass
        except Exception as e:
            Logger.info("Time out: %s in vm_list" , e)
            if self.all:
                wx.CallAfter(dialog.Error, u'获取专有虚拟机失败，请检查网络后再试！')
            Logger.info("Refresh status:Refresh failed！")
            return
        global vms_len,vms_dict
        vms_len = len(vms)
        for i in range(0, vms_len):
            vm = vms[i]

            if self.all:
                try:
                    wx.CallAfter(self.window.InsertVMItem, i, vm)
                    wx.CallAfter(dialog.Update, 1, u'读取专有虚拟机信息...(%d/%d)' % (i+1, vms_len))
                except:
                    pass
            else :
                try:
                    wx.CallAfter(self.window.UpdateVMStatus, i, vm)
                except:
                    pass

        floatpool_len = len(floatpool)
        for j in range(0, floatpool_len):
            floats = floatpool[j]
            if self.all:
                try:
                    wx.CallAfter(self.window.InsertFloatItem, j, floats)
                    if self.all:
                        wx.CallAfter(dialog.Update, 1, u'读取浮动池信息...(%d/%d)' % (j+1, floatpool_len))
                except:
                    pass
            else :
                try:
                    wx.CallAfter(self.window.UpdateFloatStatus, j)
                except:
                    pass

        if self.all:
            try:
                wx.CallAfter(dialog.WorkFinished, u'读取虚拟机信息...完成')
                wx.CallAfter(dialog.Finish)
            except:
                pass

        self.window.vms = vms
        self.window.fps = floatpool 

        if self.vminfo:
            thread = threading.Thread(target=Analy(vms))
            thread.start()

        self.vminfo = False
        self.all = False
        if not vms:
            return 

        if Setting.getAuto() == 'True' and self.autoConsole and vms_len == 1 :
            self.autoConsole = False 
            try:
                wx.CallAfter(self.window.AutoConsole)
            except:
                pass

    def run(self):                
        while not self.cancel:
            if self.refresh > 0:
                self.lock.acquire()
                self.refreshVM()
                self.lock.release()
                self.refresh = self.refresh - 1
            else:
                if self.tenRefresh == 0:
                    # Del by wangderan 20150525 start 
                    #Session.logout()
                    # Del by wangderan 20150525 end

                    url = 'http://%s%s' % (Setting.getServer(), ":5000/v2.0")
                    _auth_url = url
                    
                    username = Setting.getLastLogin()
                    _user = username
                    
                    _password = LoginFrame.PassWord()
                    
                    ret, reason, detail = Session.login(_auth_url, _user, _password)
                    Logger.info("ReLogin Status: Result: %s", ret)
                    
                    self.lock.acquire()
                    self.refreshVM()
                    self.lock.release()
                    self.tenRefresh = 900
                else:
                    self.tenRefresh = self.tenRefresh - 1
                    wx.Sleep(2)

class FocusThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window
        
    def run(self):
        while True:
            #self.window.vmlist.SetFocus()
	    #wx.CallAfter(self.window.vmlist.SetFocus)
            time.sleep(1)
            
class VMListPanel(wx.Panel):
    def __init__(self, parent, info_panel):
        wx.Panel.__init__(self, parent, -1)
        
        self.info_panel = info_panel
        self.btn_start = buttons.GenBitmapTextButton(self, -1, Resource.play, u'启动', style = wx.NO_BORDER)
        self.btn_pause = buttons.GenBitmapTextButton(self, -1, Resource.pause, u'暂停', style = wx.NO_BORDER)
        self.btn_resume = buttons.GenBitmapTextButton(self, -1, Resource.resume, u'恢复', style = wx.NO_BORDER)
        self.btn_shutdown = buttons.GenBitmapTextButton(self, -1, Resource.shutdown, u'关闭',  style = wx.NO_BORDER)
        self.btn_reboot = buttons.GenBitmapTextButton(self, -1, Resource.reboot, u'重启', style = wx.NO_BORDER)
        self.btn_console = buttons.GenBitmapTextButton(self, -1, Resource.console, u'连接桌面',  style = wx.NO_BORDER)
        self.btn_refresh = buttons.GenBitmapTextButton(self, -1, Resource.refresh, u'全部刷新',  style = wx.NO_BORDER)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.btn_start, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.AddSpacer(5)
        sizer.Add(self.btn_pause, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.AddSpacer(5)
        sizer.Add(self.btn_resume, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.AddSpacer(5)
        sizer.Add(self.btn_shutdown, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.AddSpacer(5)
        sizer.Add(self.btn_reboot, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.AddSpacer(5)
        sizer.AddSpacer(5)
        sizer.Add(self.btn_console, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(self.btn_refresh, 0, wx.ALIGN_CENTER_VERTICAL)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sizer, 0, wx.EXPAND)
        
        self.vmlist = wx.ListCtrl(self, style = 
                             wx.LC_REPORT |
                             wx.BORDER_SUNKEN |
                             wx.LC_SINGLE_SEL )
        
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.btn_refresh)
        mainSizer.AddSpacer(3)
        mainSizer.Add(self.vmlist, 1, wx.EXPAND)
        box = wx.StaticBox(self, -1, u"虚拟机视图")
        outSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        outSizer.Add(Util.CreateCenterSizer(mainSizer, 10), 1, flag = wx.EXPAND)
        self.SetSizer(outSizer)
        
        self.vmlist.AssignImageList(VM.GetStatusIconList(), wx.IMAGE_LIST_SMALL)
        self.vmlist.InsertColumn(0, u'', width = 50)
        self.vmlist.InsertColumn(1, u'名称', width = 300)
        self.vmlist.InsertColumn(2, u'状态',width = 800)
        self.vms = None
        self.fps= None
        self.SetButtonStatus()
        self.refreshthread = None
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.vmlist)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onDCLICK, self.vmlist)
        self.Bind(wx.EVT_LIST_KEY_DOWN, self.OnKeyDown,self.vmlist)
        self.Bind(wx.EVT_BUTTON, self.OnStart, self.btn_start)
        self.Bind(wx.EVT_BUTTON, self.OnPause, self.btn_pause)
        self.Bind(wx.EVT_BUTTON, self.OnResume, self.btn_resume)
        self.Bind(wx.EVT_BUTTON, self.OnShutdown, self.btn_shutdown)
        self.Bind(wx.EVT_BUTTON, self.OnReboot, self.btn_reboot)
        #self.Bind(wx.EVT_BUTTON, self.OnStop, self.btn_stop)
        self.Bind(wx.EVT_BUTTON, self.OnConsole, self.btn_console)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnWindowDestroy)
        
        # Now send refresh message
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.btn_refresh.GetId())
        #self.refreshthread.refresh_all()
        #self.vmlist.Bind(wx.EVT_COMMAND_RIGHT_DCLICK, handler, source, id, id2)
        wx.PostEvent(self, evt)
        focusThread = FocusThread(self)
        focusThread.start()

    def OnKeyDown(self,event):
        if event.GetKeyCode() == wx.WXK_F4 :
            dlg = SettingDialog.SettingDialog(self)
            #dlg.CenterOnScreen()
            ret = dlg.ShowModal()
            if ret == wx.ID_OK:
                dlg.SaveSetting()
            dlg.Destroy()
        event.Skip()

    def ConnectVM(self, p_id, vm):
        key = vm.name
        try:
            vmtype = vms_dict[key]
            Type = vmtype['vmtype']
        except:
            Type = "UNKNOWN"
        Logger.info("VM is a %s type", Type)

        if Type == 'JSP' or Type == 'UNKNOWN': 
            dlg = ProgressDialog.ProgressDialog(self, u'连接服务器...')
            thread = Console.LaunchThread(p_id, vm, Type, dlg) 
            thread.start()
            if dlg.ShowModal() == wx.ID_CANCEL:
                thread.stop()
            else:
                thread.join()
        elif Type == 'RDP':
            RDP = RDPLoginDialog.RDPLoginDialog(vm,Type)
            RDP.ShowModal()

    def onDCLICK(self,event):
        select = self.vmlist.GetFirstSelected()

        if select < len(self.fps):
            vm = None
            fp = self.fps[select]
            try:
                vms_fp = havclient.vm_list(FirstUser['firstuser'], "is_simply", fp.id)
            except:
                Logger.error("Failed to get floating pool vms")
                return

            if len(vms_fp) == 0:
                Util.MessageBox(self, '该池无可用虚拟机资源,请联系系统管理员！', u'提示', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE)
                return

            for j in vms_fp:
                if j.status == u'ACTIVE':
                    try:
                        conn_status = havclient.connect_status(AdminShadow['admins'], fp.id, j) 
                    except:
                        Logger.error("Failed to get connecting status of vm")
                        return
                    conn = conn_status.get(u'connect_status', None)
                    if conn == u'free':
                        vm = j
                        break
                    else:
                        continue 
                else:
                    continue

            if vm == None:
                for j in vms_fp:
                    if j.status == u'SHUTOFF':
                        vm = j
                        try:
                            Logger.info("VM Status: %s is opening!",vm.name)
                            havclient.server_start(AdminShadow['admins'], vm, fp.id)
                            time.sleep(2)
                        except:
                            Logger.info("VM Status: %s is opening failure!",vm.name)
                            pass
                        break
                    else:
                        continue

            if vm == None:
                Util.MessageBox(self, '该池无空闲虚拟机资源,请联系系统管理员！', u'提示', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE) 
                return
                        
            self.ConnectVM(fp.id, vm)
            self.GetParent().SetFocus()
            self.TrackVMStatus(vm)
        else:
            vm = self.vms[select - len(self.fps)]
            if vm.status == 'ACTIVE':
                self.ConnectVM(vm.tenant_id, vm)
                self.GetParent().SetFocus()
                self.TrackVMStatus(vm)
            try:
                Logger.info("CMD: Start - %s", vm.name)
                self.TrackVMStatus(vm)
            except :
                pass
        event.Skip()

    def OnWindowDestroy(self, event):
        self.refreshthread.stop()
        event.Skip()
        
    def OnRefresh(self, event):
        try:
            LBVM.SetLabel(u"虚拟机：")
            LBCPU.SetLabel(u"虚拟CPU：")
            LBRAM.SetLabel(u"内存：")
            LBDISK.SetLabel(u"存储：")
            LBDISPLAY.SetLabel(u"显示接口：")
            LBSTATUS.SetLabel(u"状态：")
            LBCOUNT.SetLabel(u"虚拟机总数：")
            LBUSB.SetLabel(u"USB策略：")
        except:
            pass

        self.dlg = ProgressDialog.ProgressDialog(self, u'获取当前用户的虚拟机信息...')
        wx.CallAfter(self.dlg.Update, 1, u'获取当前用户的虚拟机信息...')
        if self.refreshthread:
            self.refreshthread.stop()
        self.refreshthread = RefreshThread(self)
        self.refreshthread.start()
        #orig = -1 
        orig = self.vmlist.GetFirstSelected()
        self.refreshthread.refresh_all()
        ret = self.dlg.ShowModal()
        if ret == wx.ID_CANCEL:
            self.refreshthread.refresh_all_stop()
            self.dlg.EndModal(ret)
        if self.dlg:
            self.dlg.Destroy()
        # add start
        if orig != -1:
        # add end
            self.vmlist.Select(orig, True)
            self.vmlist.SetFocus()
            event.Skip()
        
    def ConnectionError(self):
        Util.MessageBox(self, u"连接错误。\n请检查网络情况，然后重试！", u"错误",
                                   style=wx.OK|wx.ICON_ERROR)
        self.GetParent().Close()
        
    def float_status(self, floats):
        vm = None
        try:
            vms_fp = havclient.vm_list(FirstUser['firstuser'], "is_simply", floats.id)
        except:
            Logger.error("Failed to get floating pool vms")
            return
        if len(vms_fp) == 0:
            return u'none'

        for j in vms_fp:
            if j.status == u'ACTIVE':
                try:
                    conn_status = havclient.connect_status(AdminShadow['admins'], floats.id, j) 
                except:
                    Logger.error("Failed to get connecting status of vm")
                    return
                conn = conn_status.get(u'connect_status', None)
                if conn == u'free':
                    vm = j
                    break
                else:
                    continue
            else:
                continue

        if vm is not None:
            return u'enabling'
        else:
            for j in vms_fp:
                if j.status == u'SHUTOFF':
                    vm = j
                    return u'enabling'

        if vm is None:
            return u'disabling'

    def InsertFloatItem(self, j, floats):
        vmlist = self.vmlist 
        #status = self.float_status(floats)
        status = u'RUNNING' 

        vmlist.InsertImageItem(j, VM.GetStatusImage(status))
        vmlist.SetStringItem(j, 1, floats.name) 
        vmlist.SetStringItem(j, 2, status) 

    def InsertVMItem(self, i, vm):
        status = vm.status

        self.vmlist.InsertImageItem(i, VM.GetStatusImage(status))
        self.vmlist.SetStringItem(i, 1, vm.name)
        if status == u'ACTIVE':
            self.vmlist.SetStringItem(i, 2, u'RUNNING')
        else:
            self.vmlist.SetStringItem(i, 2, VM.get_power_state(vm))

    def SetButtonStatus(self):
        select = self.vmlist.GetFirstSelected()

        if select == -1:
            status = 'UnSelected'
        elif select < len(self.fps):
            #floats = self.fps[select]
            #status = self.float_status(floats)
            status = u'RUNNING'
        else:
            vm = self.vms[select - len(self.fps)]
            status = vm.status

        self.btn_start.Enable(status in VM.START_ENABLED_STATUS)
        self.btn_pause.Enable(status in VM.PAUSE_ENABLED_STATUS)
        self.btn_resume.Enable(status in VM.RESUME_ENABLED_STATUS)
        self.btn_shutdown.Enable(status in VM.SHUTDOWN_ENABLED_STATUS)
        self.btn_reboot.Enable(status in VM.REBOOT_ENABLED_STATUS)
        #self.btn_stop.Enable(status in VM.STOP_ENABLED_STATUS)
        self.btn_console.Enable(status in VM.CONSOLE_ENABLED_STATUS)
        
    # modi by wangderan start

    def OnItemSelected(self, event):
        select = self.vmlist.GetFirstSelected()

        if select < len(self.fps):
            self.info_panel.Hide()
        else:
            self.info_panel.Show(True)
            vm = self.vms[select - len(self.fps)]
            key = vm.name

            try:
                vminf = vms_dict[key]
                LBVM.SetLabel(u"虚拟机：%s" % vminf[u'vmname'])
                LBCPU.SetLabel(u"虚拟CPU：%s " % vminf[u'vmvcpu'])
                LBRAM.SetLabel(u"内存：%s MB" % vminf[u'vmram'])
                LBDISK.SetLabel(u"存储：%s GB" % vminf[u'vmdisk'])
                LBDISPLAY.SetLabel(u"显示接口：%s" % vminf[u'vmtype'])
                LBSTATUS.SetLabel(u"状态：%s" % vminf[u'vmstatus'])
                LBCOUNT.SetLabel(u"虚拟机总数：%s台" % vminf[u'vmslen'])
                LBUSB.SetLabel(u"USB策略：%s" % vminf[u'vmusb'])
            except:
                pass

        self.SetButtonStatus()
        event.Skip()
    # modi by wangderan end
        
    def TrackVMStatus(self, vm):
        self.refreshthread.setRefresh()
        
    def UpdateFloatStatus(self, j):
        #status = self.float_status(floats)
        status = u'RUNNING'

        self.vmlist.SetItemColumnImage(j, 0, VM.GetStatusImage(status))
        self.vmlist.SetStringItem(j, 2, status)

        self.SetButtonStatus()

    def UpdateVMStatus(self, i, vm):
        status = vm.status

        self.vmlist.SetItemColumnImage(i+len(self.fps), 0, VM.GetStatusImage(status))
        if status == u'ACTIVE':
            self.vmlist.SetStringItem(i, 2, u'RUNNING')
        else:
            self.vmlist.SetStringItem(i+len(self.fps), 2, VM.get_power_state(vm))
        
        self.SetButtonStatus()
        
    def OnStart(self, event):
        select = self.vmlist.GetFirstSelected()

        if select < len(self.fps):
        #            fp = self.fps[select]
        #            vms_fp = havclient.vm_list(FirstUser['firstuser'], "is_simply", fp.id)
        #            for j in range(0, len(vms_fp)):
        #                if vms_fp[j].status == u'ACTIVE':
        #                    conn_status = havclient.connect_status(fp.id, vms_fp[j]) 
        #                    conn = conn_status.get(u'connect_status', None)
        #                    if conn == u'free':
        #                        self.ConnectVM(fp.id, vms_fp[j])
        #                        self.GetParent().SetFocus()
        #                        self.TrackVMStatus(vms_fp[j])
        #                        break
        #                    else:
        #                        continue 
        #                else:
        #                    continue
            pass
        else:
            vm = self.vms[select - len(self.fps)]
            try:
                Logger.info("CMD: Start - %s", vm.name)
                havclient.server_start(AdminShadow['admins'], vm, vm.tenant_id) 
                self.TrackVMStatus(vm)
            except :
                pass
        #event.Skip()
            
    def OnShutdown(self, event):
        select = self.vmlist.GetFirstSelected()

        vm = self.vms[select - len(self.fps)]
        try:
            Logger.info("CMD: Shutdown - %s", vm.name)
            try:
                flag = havclient.get_control(AdminShadow['admins'], vm, vm.tenant_id).get('jostle', None)
            except:
                return
            if flag:
                Util.MessageBox(self, '此虚拟机不可抢断，操作失败！', u'提示', wx.OK | wx.ICON_ERROR)
                Logger.info("Shutdown %s failed!", vm.name) 
            else:
                try:
                    havclient.server_stop(AdminShadow['admins'], vm, vm.tenant_id)
                except:
                    Logger.error("Filed to shutdown vm")
                    return
                self.TrackVMStatus(vm)
        except :
            pass
            #wx.MessageBox(res.detail[1:-1], res.reason, wx.ID_OK|wx.ICON_ERROR)
        #event.Skip()
        
    def OnReboot(self, event):
        select = self.vmlist.GetFirstSelected()
        
        vm = self.vms[select - len(self.fps)]
        try:
            Logger.info("CMD: Reboot - %s", vm.name)
            try:
                havclient.server_reboot(AdminShadow['admins'], vm, vm.tenant_id)
            except Exception as e:
                Logger.error("Reboot instance failed: %s" % str(e))
                return
            self.TrackVMStatus(vm)
        except:
            Logger.error("Failed to reboot vm")

    def OnStop(self, event):
        select = self.vmlist.GetFirstSelected()

        vm = self.vms[select - len(self.fps)]
        try:
            Logger.info("CMD: Stop - %s", vm.name)
            havclient.server_stop(AdminShadow['admins'], vm, vm.tenant_id)
            self.TrackVMStatus(vm)
        except :
            pass
            #wx.MessageBox(res.detail[1:-1], res.reason, wx.ID_OK|wx.ICON_ERROR)
        #event.Skip()
    def OnPause(self, event):   
        select = self.vmlist.GetFirstSelected()

        vm = self.vms[select - len(self.fps)]
        try:
            Logger.info("CMD: Pause - %s", vm.name)
            try:
                flag = havclient.get_control(AdminShadow['admins'], vm, vm.tenant_id).get('jostle', None)
            except:
                return
            if flag:
                Util.MessageBox(self, '此虚拟机不可抢断，操作失败！', u'提示', wx.OK | wx.ICON_ERROR)
                Logger.info("Shutdown %s failed!", vm.name) 
            else:
                try:
                    havclient.server_pause(AdminShadow['admins'], vm, vm.tenant_id)
                except:
                    Logger.error("Failed to pause vm") 
                    return
                self.TrackVMStatus(vm)
        except Exception, res:
            Logger.warn(res)
            #wx.MessageBox(res.detail[1:-1], res.reason, wx.ID_OK|wx.ICON_ERROR)
    def OnResume(self, event): 
        select = self.vmlist.GetFirstSelected()

        vm = self.vms[select - len(self.fps)]
        try:
            Logger.info("CMD: Resume - %s", vm.name)
            havclient.server_unpause(AdminShadow['admins'], vm, vm.tenant_id)
            self.TrackVMStatus(vm)
        except Exception, res:
            Logger.warn(res)
            #wx.MessageBox(res.detail[1:-1], res.reason, wx.ID_OK|wx.ICON_ERROR)
    def AutoConsole(self):
        vm = self.vms[0]
        if vm.status in VM.CONSOLE_ENABLED_STATUS :
            pass
        else :
            return
        if vm.status == 'ACTIVE':
            Logger.info("AutoConsole - %s", vm)
            self.ConnectVM(vm.tenant_id, vm)
            self.GetParent().SetFocus()
            self.TrackVMStatus(vm)

    def OnConsole(self, event):
        select = self.vmlist.GetFirstSelected()

        if select < len(self.fps):
            vm = None
            fp = self.fps[select]
            try:
                vms_fp = havclient.vm_list(FirstUser['firstuser'], "is_simply", fp.id)
            except:
                Logger.error("Failed to get floating pool vms")
                return

            if len(vms_fp) == 0:
                Util.MessageBox(self, '该池无可用虚拟机资源,请联系系统管理员！', u'提示', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE)
                return

            for j in vms_fp:
                if j.status == u'ACTIVE':
                    try:
                        conn_status = havclient.connect_status(AdminShadow['admins'], fp.id, j)
                    except:
                        Logger.error("Failed to get connecting status of vm")
                        return
                    conn = conn_status.get(u'connect_status', None)
                    if conn == u'free':
                        vm = j
                        break
                    else:
                        continue
                else:
                    continue

            if vm == None:
                for j in vms_fp:
                    if j.status == u'SHUTOFF':
                        vm = j
                        try:
                            Logger.info("VM Status: %s is opening!",vm.name)
                            havclient.server_start(AdminShadow['admins'], vm, fp.id)
                            time.sleep(2)
                        except:
                            Logger.info("VM Status: %s is opening failure!",vm.name)
                            pass
                        break
                    else:
                        continue

            if vm == None:
                Util.MessageBox(self, '该池无空闲虚拟机资源,请联系系统管理员！', u'提示', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE) 
                return

            self.ConnectVM(fp.id, vm)
            self.GetParent().SetFocus()
            self.TrackVMStatus(vm)
        else:
            vm = self.vms[select - len(self.fps)]
            if vm.status == 'ACTIVE':
                self.ConnectVM(vm.tenant_id, vm)
                self.GetParent().SetFocus()
                self.TrackVMStatus(vm)
            try:
                Logger.info("CMD: Start - %s", vm.name)
                self.TrackVMStatus(vm)
            except :
                pass
        event.Skip()

class VMInfoPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.BOLD, wx.NORMAL)

        box = wx.StaticBox(self, -1, u'资源视图')
        outSizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.AddSpacer(10)
        
        global LBVM, LBCPU, LBRAM, LBDISK, LBDISPLAY, LBSTATUS, LBUSB, LBCOUNT
        # Add VM
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticBitmap(self, -1, Resource.vm_icon), 0, flag = wx.ALIGN_TOP)
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBVM = wx.StaticText(self, -1, u"虚拟机：")
        
        #iLBVM.SetFont(font)
        innerSizer.Add(LBVM, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        innerSizer.AddSpacer(2)

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)
        
        # Add CPU
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticBitmap(self, -1, Resource.cpu_icon), 0, flag = wx.ALIGN_TOP)
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBCPU = wx.StaticText(self, -1, u"虚拟CPU： ")
        #LBCPU.SetFont(font)
        innerSizer.Add(LBCPU, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        innerSizer.AddSpacer(2)

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)
        
        # Add Memory
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticBitmap(self, -1, Resource.memory_icon), 0, flag = wx.ALIGN_TOP)
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBRAM = wx.StaticText(self, -1, u"内存：")
        #lb.SetFont(font)
        innerSizer.Add(LBRAM, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        innerSizer.AddSpacer(2)

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)
        
        # Add Storage
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticBitmap(self, -1, Resource.storage_icon), 0, flag = wx.ALIGN_TOP)
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBDISK = wx.StaticText(self, -1, u"存储：")
        innerSizer.Add(LBDISK, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        innerSizer.AddSpacer(2)

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)

        # Add Display
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticBitmap(self, -1, Resource.spice_icon), 0, flag = wx.ALIGN_TOP)
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBDISPLAY = wx.StaticText(self, -1, u"显示接口：")
        innerSizer.Add(LBDISPLAY, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        innerSizer.AddSpacer(2)

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)

        # Add STATUS
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticBitmap(self, -1, Resource.status_icon), 0, flag = wx.ALIGN_TOP)
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBSTATUS = wx.StaticText(self, -1, u"状态：")
        innerSizer.Add(LBSTATUS, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        innerSizer.AddSpacer(2)

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)

        # Add USB
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticBitmap(self, -1, Resource.usb_icon), 0, flag = wx.ALIGN_TOP)
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBUSB = wx.StaticText(self, -1, u"USB策略：")
        innerSizer.Add(LBUSB, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        innerSizer.AddSpacer(2)


        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)                                             
        mainSizer.AddSpacer(20)

        #Add count
        sizer = wx.BoxSizer(wx.HORIZONTAL)                                                    
        sizer.Add(wx.StaticBitmap(self, -1, Resource.Count), 0, flag = wx.ALIGN_TOP)    
        innerSizer = wx.BoxSizer(wx.VERTICAL)
        LBCOUNT = wx.StaticText(self, -1, u"虚拟机总数：")                                         
        innerSizer.Add(LBCOUNT, 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)          
        innerSizer.AddSpacer(2)                                                               

        sizer.AddSpacer(10)
        sizer.Add(innerSizer, 1)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(20)

        outSizer.Add(Util.CreateCenterSizer(mainSizer, 10), 1, flag = wx.EXPAND)
        self.SetSizer(outSizer)
        self.SetMinSize((300, 100))
   
    def update_vm(self, cur, total):
        self.vm_total.SetLabel(u"虚拟机配额： %d" % total)
        self.vm_current.SetLabel(u"已使用的虚拟机： %d" % cur)
        if total != 0 :
            self.vm_gauge.SetValue(cur * 100 / total)
        else :
            self.vm_gauge.SetValue(0)       
        self.vm_gauge.Refresh()
        
    def update_cpu(self, cur, total):
        self.cpu_total.SetLabel(u"已定义的虚拟CPU： %d" % total)
        self.cpu_current.SetLabel(u"正在使用的虚拟CPU： %d" % cur)
        if total != 0 :
            self.cpu_gauge.SetValue(cur * 100 / total)
        else :
            self.cpu_gauge.SetValue(0)
        self.cpu_gauge.Refresh()
    
    def update_memory(self, cur, total):
        self.memory_total.SetLabel(u"已定义的内存： %d MB" % total)
        
        self.memory_current.SetLabel(u"内存使用： %d MB" % cur)
        if total != 0 : 
            self.memory_gauge.SetValue(cur * 100 / total)
        else :
            self.memory_gauge.SetValue(0)
        self.memory_gauge.Refresh()

class MainFrame(wx.Frame):
    def __init__(self, parent, size):
        #wx.Frame.__init__(self, parent, -1, title= u'视聪客户端',size = size, style = wx.CLOSE_BOX)
        wx.Frame.__init__(self, parent, -1, title= u'君是客户端',size = size)
        #panel = wx.Panel(self, -1)
        #panel.Bind(wx.EVT_CHAR, self.OnKeyDown)
        #panel.SetFocus()
        bp = BannerPanel(self)  
        vip = VMInfoPanel(self)  
        self.vlp = VMListPanel(self, vip)

        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
        bottomSizer.Add(self.vlp, 1, flag = wx.EXPAND)
        bottomSizer.AddSpacer(20)
        bottomSizer.Add(vip, 0, flag = wx.EXPAND)
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(bp, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(10)
        mainSizer.Add(bottomSizer, 1, flag = wx.EXPAND)
        
        self.SetSizer(Util.CreateCenterSizer(mainSizer, 15))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
         
    def OnKeyDown(self, event):
        if event.GetKeyCode() == ord('f'):
            if self.GetPosition()==((0,0)):
                self.SetPosition((300,300))
                self.SetSize((500,300))
            else:
                self.SetPosition((0,0))
                self.SetSize(wx.DisplaySize())
        if event.GetKeyCode() == ord('q'):
            self.Close()
        else:
            event.Skip()

    def autOn(self):
        num = len( Session.getVMs())
        if num == 1 :
            self.vlp.AutoConsole()
        
    def OnClose(self, event):
        Session.logout()
        if self.GetParent():
            self.GetParent().Show()
            self.GetParent().ShowFullScreen(True)
        event.Skip()

if __name__ == '__main__':
    auth_url = 'http://192.168.8.93:5000/v2.0'  
    user = 'test'  
    password = 'wwwwww' 
    app = wx.PySimpleApp()
    Resource.load()
    cafile = '/tmp/ca-%s.crt' % (Setting.getServer())
            
    Session.login(auth_url, user, password, tenant=None, otp=None)
    frame = MainFrame(None, wx.ScreenDC().GetSize())
    frame.ShowFullScreen(True)
#    frame.autOn()
    app.MainLoop()
    Session.logout()
