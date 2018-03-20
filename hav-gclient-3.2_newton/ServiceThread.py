#!/usr/bin/env python
# coding: utf-8
import wx
import os
import time
import threading
import subprocess
import multiprocessing
from SimpleXMLRPCServer import SimpleXMLRPCServer as sxr

import Message
import Network
import Logger
import Util
import havclient
import MainFrame
import Setting
from Setting import AdminShadow,FirstUser
from SendRequests import StopDeviceRequests,RestartDeviceRequests

kwargs = ['reboot', 'shutdown', 'status', 'receive', 'update', 'ApplyRemote', 'CancelRemote', 'UsbConnect', 'UsbDisconnect', 'FlowSize']

class Controller(object):
    def __init__(self, method=[]):
        self.method=method
        self.simpleRPC = sxr(('0.0.0.0', 8099), allow_none=True)

    def server(self):
        for key in kwargs:
            self.simpleRPC.register_function(getattr(self, key))
        self.simpleRPC.serve_forever()

    def execute(self, *cmd):
        os.system(cmd[0])

    def reboot(self):
        Logger.info("Order from server,vClient will reboot.")
        threads = threading.Timer(3, self.execute, ["reboot"])
        threads.start()
        StopDeviceRequests()
        return 'success'

    def shutdown(self):
        Logger.info("Order from server,vClient will poweroff.")
        threads = threading.Timer(3, self.execute, ["poweroff"])
        threads.start()
        StopDeviceRequests()
        return 'success'

    def update(self, info):
        try:
            try:
                if info['hostname'] is not '':
                    with open("/etc/hostname", "w") as f:
                        f.write("%s\n" % info['hostname'])
                    os.system("sysctl kernel.hostname=%s" % info['hostname'])
                    Logger.info("Change the hostname succeeded")
            except:
                Logger.info("Change the hostname failed.")

            try:
                interface = Network.GetInterfaceList()[0] 
                if info ['network_type'] == "remain":
                    Logger.info("The IP address unchanged.")
                elif info['network_type'] == "static":
                    Network.SetStatic(interface, info['ipaddr'], info['mask'], info['gateway'], info['dns']) 
                    Logger.info("Set the static ipaddr")
                elif info['network_type'] == "dhcp":
                    Network.SetDHCP(interface)
                    Logger.info("Set the dhcp ipaddr")
            except:
                Logger.info("Change the ipaddr failed")

            try:
                if info['dns'] is not '':
                    Network.SetDNS(info['dns'])
                    Logger.info("Change the dns succeeded")
            except:
                Logger.info("Change the dns failed")
            RestartDeviceRequests()

        except:
            Logger.info("Set the device information failed")
        return "success"

    def status(self):
        return "on-line"

    def receive(self,data):
        Logger.info("Message from the server:%s" % data)
        if data == 'c9748aad-4e82-499a-b8aa-2c74358457fc':
            datas = u"远程协助已完成！"
        else:
        #wx.CallAfter(self.Message, data)
            datas = "\"%s\"" % data
        www = "python ./Message.pyc " + datas 
        subprocess.Popen(www, shell=True)

        return 'success'

    def UsbConnect(self, instance_id, descriptor):
        usb_audit = {}
        usb_audit['usbconnect'] = descriptor 
        vm = self.SeekVM(instance_id)
        havclient.usb_audit(FirstUser['firstuser'], vm.tenant_id, instance_id, usb_audit)

    def UsbDisconnect(self, instance_id, descriptor):
        usb_audit = {}
        usb_audit['usbdisconnect'] = descriptor 
        vm = self.SeekVM(instance_id)
        havclient.usb_audit(FirstUser['firstuser'], vm.tenant_id, instance_id, usb_audit)

    def FlowSize(self, instance_id, descriptor):
        usb_audit = {}
        usb_audit['usbflowsize'] = descriptor 
        vm = self.SeekVM(instance_id)
        havclient.usb_audit(FirstUser['firstuser'], vm.tenant_id, instance_id, usb_audit)

    def ApplyRemote(self, instance_id):
        status = "applyremote"
        self.Remote(instance_id, status)

    def CancelRemote(self, instance_id):
        status = "cancelremote"
        self.Remote(instance_id, status)

    def Remote(self, instance_id, status):
        try:
            data = {}
            vm = self.SeekVM(instance_id)
            if status == "applyremote":
                vmcipher = havclient.get_cipher(FirstUser['firstuser'], vm.tenant_id, vm)
                if isinstance(vmcipher, int):
                    password = vmcipher
                else:
                    password = vmcipher.cipher
                data['instance_id'] = instance_id
                #data['token_id'] = FirstUser['firstuser'].token.id
                data['client_ip'] = Setting.getClientIP()
                data['instance_name'] = vm.name
                data['status'] = status
                data['password'] = password
                havclient.create_remote_assistance(AdminShadow['admins'], vm.tenant_id, data) 
            elif status == "cancelremote":
                havclient.cancel_remote_assistance(AdminShadow['admins'], vm.tenant_id, instance_id)
        except:
            Logger.error("Remote failed!")

    def SeekVM(self, instance_id):
        try:
            vms = MainFrame.vms
            for i in vms:
                if i.id == instance_id:
                    return i
        except:
            Logger.error("Seeked failed!")

    def Message(self, data):
        p = MessageDlg(data)
        p.start()

    def status(self):
        return "on-line"

    def stop(self):
        self.simpleRPC.shutdown()

class MessageDlg(multiprocessing.Process):
    def __init__(self, data):
        multiprocessing.Process.__init__(self)
        self.data = data

    def run(self):

        dlg = wx.MessageDialog(None, "%s\n\n%s" % (u"系统管理员向您发送了一条信息，请查看：".encode("utf-8") , self.data.encode("utf-8")), "新的信息", wx.OK | wx.STAY_ON_TOP)
        dlg.ShowModal()
        dlg.Destroy()

class Service(threading.Thread):
    def __init__(self, params=None):
        super(Service, self).__init__()
        self.contr = Controller()

    def run(self):
        self.contr.server()

    def exit(self):
        self.contr.stop()

if __name__=="__main__":
    s = Service()
    s.start()
