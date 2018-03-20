#!/usr/bin/env python
# coding=utf-8
'''
Created on Jun 11, 2012

@author: gf
'''
import time
import user
import backend
import thread
import Logger
import base64
import os
import urllib2
import Setting
import Update
import user
from Setting import FirstUser
"""
Connect to Engine
  
Return: result, reason
   
        True - Success
        False - Failed
"""
def Check_hosts():
    if Setting.getServer() == '':
        return None

    url = Update.GetUrl()
    try:
        remote = urllib2.urlopen(url + ':5009/hosts')
        Logger.info("Read the hosts file successful!")
    except:
        Logger.info("Read the hosts file unsuccessful!")
        return
    server_dict = {}

    while True:
        buf = remote.readline()
        if not buf:
            break
        if buf.startswith("#") or \
            buf.startswith("127.0.0.1") or \
            buf.startswith("::1"):
            pass
        else:
            splits = buf.split()
            if len(splits) >= 2:
                key = " ".join(splits[1:])
                server_dict[key] = splits[0]

    update_hosts(server_dict)

def analy_host():
    server_dict = {}
    f=open(base64.decodestring(Setting.getFilename()))
    bufs= f.readlines()
    f.close()
    for line in bufs:
        if line.startswith('127.0.0.1') or \
            line.startswith('::1'):
            continue
        splits = line.split()
        if len(splits) == 0:
            pass
        elif len(splits) <= 3:
            key = " ".join(splits[1:])
            server_dict[key] = splits[0]
        
    client_dict = {}
    localname = open('/etc/hosts')
    bufs = localname.readlines()
        
    for line in bufs:
        if line.startswith('127.0.0.1') or \
            line.startswith('::1') or \
            line.startswith('#') :
            continue
        splits = line.split()
        if len(splits) >= 2:
            key = " ".join(splits[1:])
            client_dict[key] = splits[0]
    localname.close()

    for key in server_dict:
        client_dict[key] = server_dict[key]
    update_hosts(client_dict)

def update_hosts(dict):
    localname = open('/etc/hosts')
    buffer = localname.readlines()
    localname.close()
    localname = open('/etc/hosts', 'w')
    for line in buffer:
        line = line.strip()
        if line == '':
            continue
        if line.startswith('#') or \
            line.startswith('127.0.0.1') or \
            line.startswith('::1'):
            localname.write(line + '\n')
    for i in dict.keys():
        localname.write('%s %s\n' % (dict[i], i))
    localname.close()

Password = None
_lock = thread.allocate_lock()

def login(url, username, password, tenant=None,otp=None):
    global Password, _lock
    _lock.acquire()
    try:
        if (not isinstance(FirstUser['firstuser'], user.User) 
            or FirstUser['firstuser'].is_token_expired()
            or FirstUser['firstuser'].password != password
            or FirstUser['firstuser'].endpoint != url 
            or FirstUser['firstuser'].username != username):
            backends = backend.KeystoneBackend()
            Fuser, Flag = backends.authenticate(username=username, password=password,
                tenant=None, auth_url=url, otp=otp)
            FirstUser['firstuser'] = Fuser
            FirstUser['loginflag'] = Flag
    except:
        FirstUser['firstuser'] = user.User()
        Logger.error("FirstUser logins failed!!!")
    try:
        if FirstUser['loginflag'] == u'Invalid':
            Logger.info("The username or password is error! Please try again!")
            return False, u'连接失败', u"用户名或密码错误.\n\n请重新登录."
        elif FirstUser['loginflag'] == u'IPError':
            Logger.info("The IP is Error!Please check it!")
            return False, u'连接失败', u"网络错误.\n\n请检查你的网络设置."
        elif FirstUser['loginflag'] == u'':
            pass
        if Setting.getPublic().lower() == 'false':
            #import pdb
            #pdb.set_trace()
            Check_hosts()
        else:
            pass

        Password = password

        return True, u'成功!', u'成功登录.'
    except:
        return False, u'连接错误', u"不能连接到服务器.\n\n请检查你的系统设置或联系网络管理员."
    finally:
        if _lock.locked():
            _lock.release()
        
    return False, u'错误', u'未知错误!'
    
def logout():
    global  _lock
    if _lock.locked():
        _lock.release()


if __name__ == '__main__':
    username = 'admin'
    passwd = '111111'
    url = 'http://go:5000/v2.0' 
    while True:
        print '%s %s %s' % (username, passwd, url)
        ret, reason, detail = login(url, username, passwd)
        print 'ReLogin Status:  %s , %s, %s' % (ret, reason, detail)
