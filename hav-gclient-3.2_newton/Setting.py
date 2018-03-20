#!/usr/bin/env python
# coding=utf-8
'''
Created on Jun 12, 2012

@author: gf
'''
import os
import ConfigParser
import Logger

SEC_BASIC = 'Basic'
SEC_NETWORK = 'Network'
SEC_ADVANCE = 'Advance'
SEC_RDP = 'RDPSetting'
SEC_VPN = 'VPNSetting'

__filename = os.environ["HOME"] + '/hav.conf'
__conf = None

AdminShadow = {}
FirstUser = {}
threadddd = {}

def load():
    global __filename, __conf
 
    try:
        __conf = ConfigParser.ConfigParser()
        __conf.read(__filename)
    except IOError:
        pass
    
def save():
    try:
        __conf.write(open(__filename, "w"))
    except IOError:
        pass
        
def setValue(section, option, value):
    if not __conf.has_section(section):
        __conf.add_section(section)
    __conf.set(section, option, value)

def getValue(section, option, default):  
    if not __conf.has_option(section, option):
        setValue(section, option, default)
        return default
    return __conf.get(section, option)
    
def getServer():
    return getValue(SEC_BASIC, "SERVER", "")
        
def getPort():
    return getValue(SEC_BASIC, "PORT", "80")

def getSecure():
    return getValue(SEC_BASIC, "SECURE", "False")

def getAuto():
    return getValue(SEC_BASIC, "AUTO", "False")

def getSign():
    return getValue(SEC_BASIC, "SIGN", "False")

def getSearch():
    return getValue(SEC_BASIC, "AUTOSEARCH", "True")
    
def getLastLogin():
    return getValue(SEC_BASIC, "LASTLOGIN", "admin")

def getUser():
    return getValue(SEC_RDP, "RDPUSER", "")

def getCipher():
    return getValue(SEC_RDP, "RDPPASSWORD", "")

def getAddrip():
    return getValue(SEC_BASIC, "HYPERVIP", "")

def getFilename():
    return getValue(SEC_BASIC, "FILENAME", "")

def getPasswd():
    return getValue(SEC_BASIC, "PASSWD", "111111")

def getMainScreen():
    return getValue(SEC_BASIC, "MAINSCREEN", "VGA")

def setMainScreen(mainscreen):
    setValue(SEC_BASIC, "MAINSCREEN", mainscreen)

def setServer(server):
    setValue(SEC_BASIC, "SERVER", server)
        
def setPort(port):
    setValue(SEC_BASIC, "PORT", port)
    
def setSecure(secure):
    setValue(SEC_BASIC, "SECURE", secure)
    
def setAuto(auto):
    setValue(SEC_BASIC, "AUTO", auto)
    
def setSign(ispass):
    setValue(SEC_BASIC, "SIGN", ispass)
    
def setSearch(search):
    setValue(SEC_BASIC, "AUTOSEARCH", search)
        
def setLastLogin(loginid):
    setValue(SEC_BASIC, "LASTLOGIN", loginid)

def setUser(username):
    setValue(SEC_RDP, "RDPUSER", username)

def setCipher(cipher):
    setValue(SEC_RDP, "RDPPASSWORD", cipher)

def setAddrip(addrip):
    setValue(SEC_BASIC, "HYPERVIP", addrip)

def setFilename(filename):
    setValue(SEC_BASIC, "FILENAME", filename)

def setPasswd(passwd):
    setValue(SEC_BASIC, "PASSWD", passwd)
    
def getProtocol():
    return getValue(SEC_NETWORK, "BOOTPROTO", "DHCP")
    
def getIP():
    return getValue(SEC_NETWORK, "IPADDR", "")
    
def getNetmask():
    return getValue(SEC_NETWORK, "NETMASK", "")
   
def getGateway():
    return getValue(SEC_NETWORK, "GATEWAY", "")
    
def getPrimaryDNS():
    return getValue(SEC_NETWORK, "DNS1", "")
    
def getSecondaryDNS():
    return getValue(SEC_NETWORK, "DNS2", "")
    
def setProtocol(proto):
    setValue(SEC_NETWORK, "BOOTPROTO", proto)  
        
def setIP(ip):
    setValue(SEC_NETWORK, "IPADDR", ip)

def getInterval():
    return getValue(SEC_BASIC, "RefreshInterval", "10")

def setInterval(val):
    setValue(SEC_BASIC, "RefreshInterval", val)
    
def setPreferClient(client):
    setValue(SEC_ADVANCE, "Prefer", client)
    
def getPreferClient():
    return getValue(SEC_ADVANCE, "Prefer", "Video")
    
def getHIDUSB():
    return getValue(SEC_ADVANCE, "HIDUSB", "True")

def getAutoResolution():
    return getValue(SEC_ADVANCE, "AutoResolution", "True")

def getH264():
    return getValue(SEC_ADVANCE, "H264", "False")

def getMJPEG():
    return getValue(SEC_ADVANCE, "MJPEG", "False")

def getHARD_ACC():
    return getValue(SEC_ADVANCE, "HARD_ACC", "False")

def getPublic():
    return getValue(SEC_ADVANCE, "Public", "False")

def getStream():
    return getValue(SEC_ADVANCE, "Stream", "False")

def getVPNStatus():
    return getValue(SEC_VPN, "VPNSTATUS", "False")

def getVPNServer():
    return getValue(SEC_VPN, "VPNSERVER", "")

def getVPNUser():
    return getValue(SEC_VPN, "VPNUSER", "")

def getVPNPass():
    return getValue(SEC_VPN, "VPNPASS", "")

def getVPNRem():
    return getValue(SEC_VPN, "VPNREM", "False")
    
def getVPNAuto():
    return getValue(SEC_VPN, "VPNAUTO", "False")

def getVPNDevice():
    return getValue(SEC_VPN, "VPNDEVICE", "")
    
def getAllow_device():
    return getValue(SEC_RDP, "ALLOW_DEVICE", "")
    
def getAuto_connect():
    return getValue(SEC_RDP, "AUTO_CONNECT", "True")
    
def getHeadset_micro():
    return getValue(SEC_RDP, "HEADSET_MICRO", "True")
    
def getRemotefx():
    return getValue(SEC_RDP, "REMOTEFX", "")

def getDesktop():
    return getValue(SEC_BASIC, "DESKTOP", "")
    
def getClientIP():
    return getValue(SEC_BASIC, "CLIENTIP", "")

def getVMLoginTime():
    return getValue(SEC_BASIC, "VMLOGINTIME", "")
    
#Add by wangderan start
def getLocalResolution():
    return getValue(SEC_ADVANCE, "LocalResolution", "True")

def setLocalResolution(res):
    setValue(SEC_ADVANCE, "LocalResolution", res)
#Add by wangderan end

def getRdpUsbip():
    return getValue(SEC_RDP, "RdpUsbip", "False")

def setRdpUsbip(res):
    return setValue(SEC_RDP, "RdpUsbip", res)

def setHIDUSB(flag):
    setValue(SEC_ADVANCE, "HIDUSB", flag)

def setAutoResolution(res):
    setValue(SEC_ADVANCE, "AutoResolution", res)

def setH264(res):
    setValue(SEC_ADVANCE, "H264", res)

def setMJPEG(res):
    setValue(SEC_ADVANCE, "MJPEG", res)

def setHARD_ACC(res):
    setValue(SEC_ADVANCE, "HARD_ACC", res)

def setPublic(res):
    setValue(SEC_ADVANCE, "Public", res)
    
def setStream(res):
    setValue(SEC_ADVANCE, "Stream", res)

def setVPNStatus(res):
    setValue(SEC_VPN, "VPNSTATUS", res)

def setVPNServer(server):
    setValue(SEC_VPN, "VPNSERVER", server)

def setVPNUser(user):
    setValue(SEC_VPN, "VPNUSER", user)

def setVPNPass(passwd):
    setValue(SEC_VPN, "VPNPASS", passwd)

def setVPNRem(res):
    setValue(SEC_VPN, "VPNREM", res)
    
def setVPNAuto(res):
    setValue(SEC_VPN, "VPNAUTO", res)

def setVPNDevice(res):
    setValue(SEC_VPN, "VPNDEVICE", res)

def setAllow_device(res):
    setValue(SEC_RDP, "ALLOW_DEVICE", res)
    
def setAuto_connect(res):
    setValue(SEC_RDP, "AUTO_CONNECT", res)
    
def setHeadset_micro(res):
    setValue(SEC_RDP, "HEADSET_MICRO", res)
    
def setRemotefx(res):
    setValue(SEC_RDP, "REMOTEFX", res)

def setDesktop(res):
    setValue(SEC_BASIC, "DESKTOP", res)

def setClientIP(res):
    setValue(SEC_BASIC, "CLIENTIP", res)

def setVMLoginTime(res):
    setValue(SEC_BASIC, "VMLOGINTIME", res)
    
def getAutoRDP():
    return getValue(SEC_ADVANCE, "AutoRDP", "False")

def setAutoRDP(enabled):
    setValue(SEC_ADVANCE, "AutoRDP", enabled)
    
def getOvirtIP():
    ip = None
    try :
        file = open("/etc/ovirt-engine","r")
        fileList = file.readlines()
        for ip in fileList :
            ip = ip.strip('\n')
        file.close()
    except :
        Logger.error("can't get engine IP")
    try:    
        ips = ip.split(' ')
    
        for ip in ips :
            setServer(ip)
    except:
        pass
    
load()


if __name__ == '__main__':
    load()
    #getOvirtIP()
    #print getServer()
    print getAutoResolution()
    
