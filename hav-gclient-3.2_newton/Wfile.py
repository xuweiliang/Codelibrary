#!/usr/bin/env python
# coding=utf-8
import Logger
import Setting
import base64

def getmapping_prot(host, port):
    hostlist = {}
    getportlist=[]
    setportlist=[]
    f=open(base64.decodestring(Setting.getFilename()))
    bufs= f.readlines()
    f.close()
    for line in bufs:
        if line.startswith('127.0.0.1') or \
            line.startswith('::1') or \
            line.startswith("#"):
            continue
        splits = line.split()
        if len(splits) == 4:
            startport={'getport':splits[1]}
            getportvalue={splits[0]:startport}
            getportlist.append(getportvalue)

            mappingstart={'setport':splits[3]}
            setportvalue={splits[0]:mappingstart}
            setportlist.append(setportvalue) 

            hostlist.setdefault(splits[0], splits[2])

    for i in getportlist:
        hostname = i.get(host, None)
        if hostname:
            getport = hostname.get('getport', None).split('-')[0]
            break
    for i in setportlist:
        hostname = i.get(host, None)
        if hostname:
            setport = hostname.get('setport', None)
            break

    diff_value = int(getport) - int(setport)
    
    dhost = hostlist.get(host, None) 
    dport = u'%d' % (int(port) - diff_value)

    return dhost, dport

def Parsing_hosts(hostname):
    Logger.info("The original host is %s" % hostname)
    filename = "/etc/hosts"
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            for i in lines:
                splits = i.split()
                if hostname in splits:
                    return splits[0]
    except:
        Logger.info("Parsing the hostname failed!")
        return hostname

if __name__=='__main__':
    host = raw_input('input host:')
    port = raw_input('input port:')
    hp = getmapping_prot(host, port)
