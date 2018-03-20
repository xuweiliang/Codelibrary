import requests
import threading
import time
import ethtool
import platform
import subprocess
import StringIO
import re

from time import sleep
from datetime import datetime

import Setting
import Logger
import havclient
from Version import string as versioninfo
from Setting import FirstUser,threadddd

class DeviceInfo(dict):
    def __init__(self):
        self.params = {}
        self.params["url"] = self.get_url()
        self.params["mac"] = self.get_addrinfo('mac')
        self.params["addr"] = self.get_addrinfo('ip')
        self.params["cpu"] = self.get_cpuinfo()
        self.params["memory"] = self.get_meminfo()
        self.params["version"] = self.get_version()
        self.params["system"] = self.get_sysinfo()
        self.params["hostname"] = self.get_sysnode()
        self.params["gateway"] = self.get_gateway()
        self.params["user"] = self.get_user()
        self.params["token"] = self.get_token()
        self.params["instance"] = self.get_desktop()

    def get_url(self):
        return "http://%s:10002/device/status" % (Setting.getServer())

    def get_addrinfo(self,param):
        addr={}
        try:
            act_device = ethtool.get_active_devices()
            if "lo" in act_device:
                act_device.remove("lo")
            for i in act_device:
                mac = ethtool.get_hwaddr(i)
                addr[mac] = ethtool.get_ipaddr(i)
        except OSError , e:
            Logger.error("Get addr information failed: %s" % str(e))
            return

        if param == "mac":
            return addr.keys()[0]
        elif param == "ip":
            return addr.values()[0]

    def get_cpuinfo(self):
        try:
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if len(line.split(':')) == 2:
                        if line.split(':')[0].strip() == "model name":
                            cpu = line.split(':')[1].strip()
                            break
                        else:
                            continue
                    else:
                        continue 
        except OSError , e:
            cpu = ""
            Logger.error("Get cpu information failed: %s" % str(e))
        return cpu

    def get_meminfo(self):
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    if len(line.split(':')) == 2:
                        if line.split(':')[0].strip() == "MemTotal":
                            mem_kb = int(line.split(':')[1].strip().split(" ")[0])/1024
                            mem = "".join([str(mem_kb), "MB"])
                            break
                        else:
                            continue
                    else:
                        continue
        except OSError , e:
            mem = ""
            Logger.error("Get mem infomation failed: %s" % str(e))
        return mem

    def get_gateway(self):
        gateway = ""
        try:
            ip_r_l=subprocess.Popen("ip r l",shell=True,stdout=subprocess.PIPE).communicate()[0]
            f = StringIO.StringIO(ip_r_l)

            for line in f:
                if "default" in line:
                    gateway = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',line).group(0)
        except OSError , e:
            Logger.error("Get gateway information failed: %s" % str(e))
            return
        return gateway

    def get_version(self):
        return versioninfo('python-hav-gclient', 3)

    def get_user(self):
        try:
            if FirstUser.get('firstuser').username:
                return FirstUser.get('firstuser').username
            else:
                return
        except:
            Logger.error("Get username information failed!")
            return

    def get_token(self):
        try:
            if FirstUser.get('firstuser').token.id:
                return FirstUser.get('firstuser').token.id
            else:
                return u"8eaff179174c49979d3435caccc0ecf3"
        except:
            return u"8eaff179174c49979d3435caccc0ecf3"

    def get_desktop(self):
        return Setting.getDesktop()

    def get_sysinfo(self):
        return "".join([platform.system(), platform.release()])

    def get_sysnode(self):
        return platform.node()

class DeviceRequests(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self) 
        self.exit = False

    def get_info(self):
        self.info = DeviceInfo()
        self.params = self.info.params
        self.params['user']=None
        self.session = requests.Session()
        self.session.headers["User-Agent"] = self.params["user"]
        self.session.headers["X-Auth-Token"] = self.params["token"]
        self.session.headers["Customer-Ip-Address"] = self.params["addr"]

    def post_request(self):
        self.get_info()
        
        try:
            req = self.session.post(self.params["url"], self.params)
        except:
            pass

    def run(self):
        #while (len(Setting.getServer().split("."))==2 or len(Setting.getServer().split("."))==3):
        #    sleep(1)
        #else:
        #    pass
        while self.exit != True:
            self.post_request()
            sleep(20)

    def stop(self):
        self.exit=True

def RestartDeviceRequests():
    try:
        if threadddd.get("devicerequest", DeviceRequests()).is_alive():
            threadddd.get("devicerequest", DeviceRequests()).stop()
        threadddd['devicerequest'] = DeviceRequests()
        threadddd.get("devicerequest", DeviceRequests()).start()
    except:
        Logger.error("DeviceThreading restart failed!")

def StopDeviceRequests():
    try:
        if threadddd.get("devicerequest", DeviceRequests()).is_alive():
            threadddd.get("devicerequest", DeviceRequests()).stop()
        Logger.info("DeviceThreading is stopped")
    except:
        Logger.error("DeviceThreading restart failed!")

def SpicePorxyRequests():
    try:
        session = requests.Session()
        session.headers["X-Auth-Token"] = FirstUser.get('firstuser').token.id
        resp = session.get("http://%s:10002/device/get_spice_proxy" % Setting.getServer())
        proxy_status = resp.json()[0].get("spice_proxy_flug",None)
        proxy_port = resp.json()[0].get("http_port",None)

        return (proxy_status, proxy_port)
    except:
        Logger.error("Send proxy requests failed!")
        return

def LoginInforRequests():
    info = {}
    info["time"] = datetime.now()

    try:
        act_device = ethtool.get_active_devices()
        if "lo" in act_device:
            act_device.remove("lo")
        for i in act_device:
            info["ip"] = ethtool.get_ipaddr(i)
    except OSError , e:
        Logger.error("Get addr ip failed: %s" % str(e))

    url = "http://%s:10002/device/status" % (Setting.getServer())
    try:
        req = requests.post(url, info)
    except:
        Logger.error("Send vmLoginInformation failed!")

def SaveVmLoginInfo():
    nowtime = datetime.now()
    vmlogintime = nowtime.strftime("%Y-%m-%d %H:%M")
    try:
        act_device = ethtool.get_active_devices()
        if "lo" in act_device:
            act_device.remove("lo")
        for i in act_device:
            clientip = ethtool.get_ipaddr(i)
    except OSError , e:
        Logger.error("Get addr ip failed: %s" % str(e))
    Setting.setClientIP(clientip)
    Setting.setVMLoginTime(vmlogintime)
    Setting.save()

if __name__ == "__main__":
    #testthread = Requests() 
    #testthread.start()
    LoginInforRequests()
