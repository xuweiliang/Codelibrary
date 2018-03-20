#!/usr/bin/env python
# coding=utf8
'''
Created on Jul 7, 2012

@author: gf
'''
import os
import Util
import ethtool

def GetInfoString():
    active_interfaces = ethtool.get_active_devices()
    all_interfaces = GetInterfaceList()

    for i in active_interfaces:
        if ethtool.get_flags('%s' % i) & ethtool.IFF_POINTOPOINT:
            active_interfaces.remove(i)

    ret = ''

    for inter in active_interfaces:
        if inter in all_interfaces:
            all_interfaces.remove(inter)
        else:
            continue
        t = 'Static'
        if IsInterfaceDHCP(inter):
            t = 'DHCP'
        ret = ret + '     %s - Active, %s\n' % (inter, t)
        ret = ret + '     IP: %s\n' % ethtool.get_ipaddr(inter)
        ret = ret + '     Netmask: %s\n' % ethtool.get_netmask(inter)
        ret = ret + '     HWAddr: %s\n' % ethtool.get_hwaddr(inter)
        
    for inter in all_interfaces:
        t = 'Static'
        if IsInterfaceDHCP(inter):
            t = 'DHCP'
        ret = ret + '     %s - Inactive, %s\n' % (inter, t)
        if t == 'Static':
            ip, mask, gw, dns = GetInterfaceConf(inter)
            ret = ret + '     IP: %s\n' % ip
            ret = ret + '     Netmask: %s\n' % mask
        ret = ret + '     HWAddr: %s\n' % ethtool.get_hwaddr(inter)
        
    return ret

def GetInterfaceList():
    all_interfaces = ethtool.get_devices()
    
    if 'lo' in all_interfaces:
        all_interfaces.remove('lo')
        
    for i in all_interfaces:
        filename = GetInterfaceConfigFileName(i)
        if not os.access(filename, os.R_OK):
            all_interfaces.remove(i)
        
    return all_interfaces
    
def GetInterfaceConfigFileName(interface):
    return '/etc/sysconfig/network-scripts/ifcfg-' + interface
    
def IsInterfaceDHCP(interface):    
    filename = GetInterfaceConfigFileName(interface)
    if not os.access(filename, os.R_OK):
        return False
    
    f = open(filename)
    bufs = f.readlines()
    f.close()
    for line in bufs:
        line = line.lower().strip()
        if line.startswith('bootproto'):
            if line.find('dhcp') > 0 :
                return True
            else:
                return False
    return False

def GetInterfaceConf(interface):
    ip = ""
    mask = ""
    gw = ""
    dns = ""
    
    filename = GetInterfaceConfigFileName(interface)
    if not os.access(filename, os.R_OK):
        return ip, mask, gw, dns
    
    f = open(filename)
    bufs = f.readlines()
    f.close()
    for line in bufs:
        line = line.lower().strip()
        if line.startswith('ipaddr'):
            splits = line.split('=')
            if len(splits) >= 2:
                ip = splits[1]
        if line.startswith('netmask'):
            splits = line.split('=')
            if len(splits) >= 2:
                mask = splits[1]
        if line.startswith('gateway'):
            splits = line.split('=')
            if len(splits) >= 2:
                gw = splits[1]
        if line.startswith('dns1'):
            splits = line.split('=')
            if len(splits) >= 2:
                dns = splits[1]
                                    
    return ip, mask, gw, dns

KEYWORD_LIST = ["bootproto", "ipaddr", "netmask", "gateway", "dns1", "dns2"]
DNS_KEYLIST = ["nameserver"]

def SetDNS(dns):
    filename = "/etc/resolv.conf"
    if not os.access(filename, os.R_OK):
        return
    f = open(filename)
    bufs = f.readlines()
    f.close()
    Util.RunShellWithLog("mv -f %s %s.bak" % (filename, filename))
    
    f = open(filename, "w")
    comstr = 'nameserver %s' % dns
    for line in bufs:
        skip = False
        low = line.lower().strip()
        
        for key in DNS_KEYLIST:
            if low == comstr:
                skip = True
                break
        if not skip:
            f.write(line)
    f.write('\n')
    f.write(comstr)
        
    f.flush()
    f.close()

def SetDHCP(interface):
    filename = GetInterfaceConfigFileName(interface)
    if not os.access(filename, os.R_OK):
        return
    
    f = open(filename)
    bufs = f.readlines()
    f.close()
    Util.RunShellWithLog("mv -f %s ~/%s.bak" % (filename, filename))
    
    f = open(filename, "w")
    for line in bufs:
        skip = False
        low = line.lower().strip()
        for key in KEYWORD_LIST:
            if low.startswith(key):
                skip = True
                break
        if not skip:
            f.write(line)
        
    f.write('BOOTPROTO=dhcp\n')
    f.flush()
    f.close()
    
    Util.RunShellWithLog('systemctl restart NetworkManager.service')
    
def SetStatic(interface, ip, mask, gw, dns):    
    filename = GetInterfaceConfigFileName(interface)
    if not os.access(filename, os.R_OK):
        return
    
    f = open(filename)
    bufs = f.readlines()
    f.close()
    Util.RunShellWithLog("mv -f %s ~/%s.bak" % (filename, filename))
    
    f = open(filename, "w")
    for line in bufs:
        skip = False
        low = line.lower().strip()
        for key in KEYWORD_LIST:
            if low.startswith(key):
                skip = True
                break
        if not skip:
            f.write(line)
    
    f.write('BOOTPROTO=static\n')
    f.write('IPADDR=%s\n' % ip)
    f.write('NETMASK=%s\n' % mask)
    f.write('GATEWAY=%s\n' % gw)
    f.write('DNS1=%s\n' % dns)
    
    f.flush()
    f.close()
    
    Util.RunShellWithLog('systemctl restart NetworkManager.service')
    
    
def GetHostList():
    '''
    Return Hosts List
    
    {'IP' : 'Host Name'}
    '''
    
    list = {}
    
    try:
        f = open('/etc/hosts')
        bufs = f.readlines()
        f.close()
        
        for line in bufs:
            if line.startswith('127.0.0.1') or \
                line.startswith('::1'):
                continue
            splits = line.split()
            if len(splits) >= 2:
                list[splits[0]] = ' '.join(splits[1:])

    except Exception, e:
        pass
        
    return list

def SaveHostList(list):
    try:
        f = open('/etc/hosts')
        bufs = f.readlines()
        f.close()
        
        f = open("/tmp/hosts", "w")
        for line in bufs:
            line = line.strip()
            if line == '':
                continue
            if line.startswith('127.0.0.1') or \
                line.startswith('::1') or \
                line.startswith('#'):
                f.write(line + '\n')
        
        for i in list.keys():
            f.write('%s %s\n' % (i, list[i]))
            
        f.close()
        
        Util.RunShellWithLog("cp -f /etc/hosts ~/hosts.bak")
        Util.RunShellWithLog("cp -f /tmp/hosts /etc/hosts")
        
    except Exception, e:
        pass
        

if __name__ == '__main__':
    list = {}
    SaveHostList(list)
