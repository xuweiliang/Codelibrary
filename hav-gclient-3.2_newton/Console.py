#!/usr/bin/env python
# coding=utf-8
'''
Created on Jun 18, 2012

@author: gf
'''
import wx
import os
import subprocess
import threading
import base64
import urllib2
import Setting
import Session
import Util
import VM
import Logger
import consoleInfo
import havclient
import MainFrame
import Wfile
import Main 
from SendRequests import SpicePorxyRequests,RestartDeviceRequests,SaveVmLoginInfo
from Setting import AdminShadow,FirstUser

#from ovirtsdk.xml.params import Action, Ticket

#IP_TRANSLATE_FILE = os.curdir + '/ip.conf'
IP_TRANSLATE_TABLE = {}
SPICE_ERR_TABLE = (
                   u"成功",
                   u"错误",
                   u"获取服务器地址失败",
                   u"连接失败\n\n可能的原因：\n1.网络故障，请检查网络。\n2.其他用户登录到这台桌面云。\n3.桌面云出现错误。",
                   u"套接字失败",
                   u"发送失败",
                   u"接收失败",
                   u"SSL过程失败",
                   u"内存不足",
                   u"代理超时",
                   u"代理错误",
                   u"版本匹配失败",
                   u"权限不足",
                   u"无效的参数",
                   u"命令行错误",
                   )

CA_DOWNLOAD_CACHE = []
RDP_PORT = 3389

def loadIPConfig():
    if not os.access(IP_TRANSLATE_FILE, os.F_OK):
        with open(IP_TRANSLATE_FILE, "w") as file:
            file.write('# IP Translate File\n')
            file.write('# Source IP     Destination IP\n')
            file.write('# \n')
            file.write('# eg.\n')
            file.write('# 10.10.10.1 100.10.10.1\n')
            return

    with open(IP_TRANSLATE_FILE, "r") as file:
        lines = file.readlines()
        for line in lines:
            # skip comment line
            if line.startswith('#') :
                continue
            splits = line.strip().split()
            if len(splits) >= 2:
                IP_TRANSLATE_TABLE[splits[0]] = splits[1]

class LaunchThread(threading.Thread):
    def __init__(self, p_id, vm, Type, window):
        threading.Thread.__init__(self)
        self.window = window
        self.p_id = p_id
        self.vm = vm
        self.Type = Type 
        self.cancel = False
        self.ret = -1
        self.msg = ""

    def get_argument(self):
        try:
            control = havclient.get_control(AdminShadow['admins'], self.vm, self.p_id)
        except :
            Logger.error("Get control failed!")

        try:
            usb = control.get('usb', None)
            Logger.info("The %s USB_policy was allowde by server." , self.vm.name)
        except :
            usb = False
            Logger.error('The usb_policy has not been provided!')

        try:
            broadcast = control.get("allow_screen_broadcast", None)
            Logger.info("The %s was allowed screen_broadcast by server", self.vm.name)
        except:
            Logger.error("The %s was not allowed screen_broadcast by server", self.vm.name)

        if usb:
            arg_usb = " --spice-usbredir-auto-redirect-filter='-1,-1,-1-1,1' --spice-usbredir-redirect-on-connect='-1,-1,-1,-1,1' "
        else:
            arg_usb = "--spice-disable-usbredir"
    
        if broadcast:
            arg_bro = " --teacher "
        else:
            arg_bro = ""

        try:
            if len(Main.get_device_connected()) == 1:
                arg_screen = ""
            else :
                w = os.popen("ps -ef | grep remote*", 'r')
                ww = w.readlines()
                w.close()
                if len(ww) == 2:
                    arg_screen = "--extend"
                else:
                    arg_screen = ""
        except Exception as e:
            Logger.error("extend screen failed: %s",e)
        '''
        try:
            spice_secure = havclient.get_spice_secure(AdminShadow['admins'], self.vm, self.p_id)
            if spice_secure:
                try:
                    filename = '/tmp/ca-cert.pem'
                    addrip= Setting.getServer()
                    url = ''.join(["http://", addrip, ":5009/ca-cert.pem"])
                    info = urllib2.urlopen(url, timeout = 1) 
                    f = open(filename, 'w')
                    while True:
                        buf = info.read(4096)
                        f.write(buf)
                        if buf == '':
                            break
                    Logger.info("Download ca-cert.pem succeed.") 
                finally:
                    info.close()
                    f.close()
                arg_sec = '--spice-ca-file=/tmp/ca-cert.pem --spice-secure-channels=main,inputs --spice-host-subject="C=IL, L=Raanana, O=Red Hat, CN=my server"'
            else:
                arg_sec = ""
        except Exception as e:
            Logger.error('Get spice secure failed: %s' % str(e))
        '''
        arg = ' '.join([arg_usb, arg_bro, arg_screen])
        return arg

    def get_rdpsetting(self):
        if Setting.getAllow_device().lower() == 'true':
            arg_device = '/drive:USB,/run/media/root '
        else:
            arg_device = ''

        #if Setting.getAuto_connect().lower() == 'true':
        #    arg_auto = '+auto-reconnect '
        #else:
        #    arg_auto = ''

        #if Setting.getHeadset_micro().lower() == 'true':
        #    arg_head_mic = '/sound:sys:pulse /microphone:sys:pulse '
        #else:
        #    arg_head_mic = ''

        if Setting.getRemotefx().lower() == 'true':
            arg_rem = '/codec-cache:jpeg /gfx '
        else:
            arg_rem = ''

        if Setting.getPublic().lower() == 'true':
            arg_net = '/network:wan '
        else:
            arg_net = '/network:lan '

        arg = ' '.join([arg_device, arg_rem, arg_net])
        return arg
        
    def stop(self):
        self.cancel = True
        
    def run(self):
        import pdb
        #pdb.set_trace()
        try:    
            count = 0
            win = self.window
            
            wx.CallAfter(win.Update, 1, u'更新桌面云状态...')
            if self.cancel:
                return

            if self.Type == 'JSP' or self.Type == 'UNKNOWN':
                #import pdb
                #pdb.set_trace()
                vminfo = havclient.server_port(AdminShadow['admins'], self.p_id, self.vm, search_opts=None, all_tenants=None)
                passwd = havclient.get_cipher(FirstUser['firstuser'], self.p_id, self.vm)
                #vmcipher = havclient.get_cipher(FirstUser['firstuser'], self.p_id, self.vm)
                #passwd = vmcipher.cipher
                vmconsole = consoleInfo.ConsoleInfo(vminfo['console'])
                host = vmconsole.host
                port = vmconsole.port
                dsport = vmconsole.tlsport

                public_ip = Setting.getPublic().lower()
                Logger.info("The public_ip status is %s", public_ip)
                dport=port
                if public_ip == "false":
                    dhost=Wfile.Parsing_hosts(host)
                    try:
                        os.environ["SPICE_PROXY"] = ""
                    except:
                        Logger.error("Configure the environment variables failed!")
                        pass
                elif public_ip == "true":
                    dhost=host
                    proxy_status, proxy_port = SpicePorxyRequests() 
                    if proxy_status:
                        try:
                            os.environ["SPICE_PROXY"] = "http://%s:%s" % (Setting.getServer(),proxy_port)
                        except:
                            Logger.error("Configure the environment variables failed!")
                    else:
                        Util.MessageBox(self, '连接失败！\n\n系统管理员未设置公网代理！', u'错误', wx.OK | wx.ICON_ERROR)
                        return

                wx.CallAfter(win.WorkFinished, u'获取桌面云信息... 成功')
          
                wx.CallAfter(win.Update, 1, u'打开桌面云...')

      
                argument = self.get_argument()
                #cmdline = 'scdaemon spice://%s/?port=%s\&tls-port=%s\&password=%s --hotkeys=exit-app=shift+f12,release-cursor=shift+f11 -f --title="%s"' % (dhost,dport,dsport,passwd,self.vm.name) + argument
                cmdline = 'scdaemon spice://%s/?port=%s\&password=%s --hotkeys=exit-app=shift+f12,release-cursor=shift+f11 -f --title="%s"' % (dhost,dport,passwd,self.vm.name) + argument
                Logger.info("Spice Cmd:%s",cmdline)
            elif self.Type == 'RDP':
                user = Setting.getUser()
                Logger.info("The user of VM is %s",user)
                password = Setting.getCipher()
                Logger.info("The password of user is %s",password)

                ip = havclient.get_vm_ip(self.vm) 

                public_ip = Setting.getPublic().lower()
                Logger.info("The public_ip status is %s" , public_ip)

                argu = self.get_rdpsetting()
                if public_ip == 'false':
                    ipaddress = ip
                    Logger.info("The ipaddress of user is %s", ipaddress)
                    cmdline = 'xfreerdp /u:%s /p:%s /v:%s /cert-ignore -sec-tls /bpp:32 /gdi:hw /multimedia:decoder:gstreamer +auto-reconnect /sound:sys:pulse /microphone:sys:pulse -f ' % (user, password, ipaddress) + argu 
                elif public_ip == 'true':
                    ip, port = Wfile.getmapping_prot(ip, '3389')
                    ipaddress = ip + ':' + port
                    Logger.info("The ipaddress of user is %s", ipaddress)
                    cmdline = 'xfreerdp /u:%s /p:%s /v:%s /cert-ignore -sec-tls /bpp:32 /gdi:hw /multimedia:decoder:gstreamer +auto-reconnect /sound:sys:pulse /microphone:sys:pulse -f ' % (user, password, ipaddress) + argu

                Logger.info("Rdp Cmd:%s",cmdline)

            body={}
            vmlogintime = Setting.getVMLoginTime()
            clientip = Setting.getClientIP()
            body['client_time'] = vmlogintime
            body['client_ip'] = clientip

           # try:
           #     havclient.connect_client_info(AdminShadow['admins'], self.p_id, self.vm.id, body)
           # except:
           #     Logger.error("Send vmlogininfo failed!")

            Logger.debug(cmdline)

            ret = Util.RunConnectGuestWithLog(cmdline)

            if self.cancel:
                return
            wx.CallAfter(win.WorkFinished, u'打开桌面云... 成功')
            wx.CallAfter(win.Finish)

            name=self.vm.name
            desktop=name.encode('utf-8')
            Setting.setDesktop(desktop)
            Setting.save()

            RestartDeviceRequests()

            SaveVmLoginInfo()

            self.stop()

            self.ret = ret
        except Exception, e:
            self.ret = 1
            self.msg = "%s : %s" %(SPICE_ERR_TABLE[1], e)
                
        Logger.debug("Console Thread Ended!")
        
#loadIPConfig()

if __name__ == '__main__':
    app = wx.PySimpleApp()
    auth_url = 'http://192.168.8.150:5000/v2.0'  
    user = 'admin'  
    password = '123' 
    
    
            
    Session.login(auth_url, user, password, tenant=None, otp=None)
    
    vms = havclient.vm_list(Session.User, search_opts=None, all_tenants=None)
    vm = havclient.server_port(Session.User, vms[0], search_opts=None, all_tenants=None)
    print '**************8 %s ' % vms
    class Test(object):
        def Update(self, value, msg):
            print value, msg
            
        def WorkFinished(self, msg):
            print msg
            
        def Finish(self):
            pass
    
    dlg = Test()
    thread = LaunchThread(vm, dlg)
    thread.start()
    app.MainLoop()
    thread.join()
    
    for key in IP_TRANSLATE_TABLE.keys():
        print key, '->', IP_TRANSLATE_TABLE[key]
