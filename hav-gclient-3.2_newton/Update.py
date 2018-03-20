#!/usr/bin/env python
# coding = uf8

'''
Created on Jul 15, 2012

@author: gf
'''
import os
import urllib2
import Setting
import Logger
import hashlib
import Version
import exceptions
import commands

CLIENT_INFO = ':5009/version.info'

def GetUrl():
    url = Setting.getServer()
    if Setting.getSecure() == 'True':
        url = 'https://' + url
    else:
        url = 'http://' + url
        
    return url

def DownloadFileTo(url, localname):
    try:
        m = hashlib.md5()
        remote = urllib2.urlopen(url)
        local = open(localname, 'w')

        while True:
            buf = remote.read(4096)
            m.update(buf)
            local.write(buf)
            if buf == '':
                break
            
        return m.hexdigest()
    finally:
        remote.close()
        local.close()

def CheckNow():
    if Setting.getServer() == '':
        return None
    
    info = None
    try:
        uri = GetUrl() + CLIENT_INFO
        info = urllib2.urlopen(uri, timeout = 1)
    
        version = ''
        filename = ''
        md5 = ''
   
        Logger.debug('Check System update')  
        for line in info.readlines():
            if line == '':
                continue
            if line[-1] == '\n':
                line = line[0:-1]
                split = line.split('=')
            if split[0].lower() == 'version':
                version = split[1]
            if split[0].lower() == 'filename':
                filename = split[1]
            if split[0].lower() == 'md5':
                md5 = split[1]
            if split[0].lower() == 'hav-gclient':
                hav_gclient = split[1]
            if split[0].lower() == 'spice-gtk':
                spice_gtk= split[1]
            if split[0].lower() == 'spice-glib':
                spice_glib = split[1]
            if split[0].lower() == 'spice-gtk-tools':
                spice_gtk_tools = split[1]
            if split[0].lower() == 'virt-viewer':
                virt_viewer = split[1]
            if split[0].lower() == 'add':
                add = split[1]
            Logger.debug(line)
        return {'version':version, 'filename':filename, 'md5':md5, 'hav_gclient':hav_gclient, 'spice_gtk':spice_gtk, 'spice_glib':spice_glib, 'spice_gtk_tools':spice_gtk_tools,'virt_viewer':virt_viewer,'add':add}
    finally:
        if info is not None:
            info.close()
        

def DownloadPackage(filename, md5):
    localname = '/tmp/' + filename
    
    ret = DownloadFileTo(GetUrl() + ':5009/' + filename, localname)
    
    if ret != md5:
        raise exceptions.Exception('MD5 not match!')
    return localname

def InstallPackage(filename, hav_gclient, spice_glib, spice_gtk, spice_gtk_tools, virt_viewer,add):
    installPath = '/tmp/'
    localname = installPath + filename
    #Save current path
    savePath = os.getcwd()
    #Change dir
    os.chdir(installPath)
    #Decompress package
    os.system('tar xvf %s' % localname)

    #Install hav-gclient
    os.system("rpm -e python-hav-gclient")
    os.system("rpm -ivh %s" % hav_gclient)
    #Install spice-gtk virt-viewer
    os.system("yum -y remove spice-glib")
    os.system("rpm -ivh %s %s %s %s" %(spice_glib, spice_gtk_tools, spice_gtk, virt_viewer))
    os.system("bash %s" % add)
    os.chdir(savePath)
    
if __name__ == '__main__' :
    ret = CheckNow()
    
    if ret is not None:
        print 'Latest version : ' + ret['version']
        print 'Current version : ' + Version.string()
        
        line = commands.getstatusoutput("rpm -qa | grep python-gclient")
