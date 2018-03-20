#!/usr/bin/env python
# coding=utf8
'''
Created on Jun 20, 2012

@author: gf
'''
'''
Version    Note
1.0.0.0    Initial release
1.0.0.7    Fix bugs, and replace login image
1.0.0.8    Fix refresh bugs
1.0.0.9    Fix vm.update, this function must has root permission
1.0.1.0    Add secure port check box to support ICC2000
1.0.1.1    Fix auto refresh bugs
1.0.2.0    Add USB-HID mount support
1.0.2.1    Add usb disable support
1.0.2.2    Fix bugs
1.0.3.0    Add Video/USB client chooser
1.0.3.1    Update login image for baoshan
1.0.3.2    Add log system
1.0.3.3    set spicec debug level
1.0.3.4    Fix IP for internet
1.0.3.5    Fix refresh freq
1.1.0.0    add usb support
1.1.0.1    fix paused bug
1.1.0.2    fix bugs, refactor
1.1.0.3    remove pause button
1.1.0.4    fix network info bugs, and disable powersave in gf.sh
1.1.0.5    fix bugs, remove invalid ca download
1.1.1.0    Add update feature
1.1.1.1    fix bugs
1.1.1.2    fix segment fault bug
1.1.1.3    fix bugs
1.1.1.4    fix bugs
1.1.2.0    add log backup function
1.1.2.1    add auto update function
1.1.2.2    fix message title bugs
1.1.2.3    fix ticket expiry to 120 hours, 5 days
1.1.2.4    fix auto update bugs
1.1.2.5    Disable auto update for security reason
1.1.3.0    Add auto display res option
1.1.3.1    Add new entry to ip translate table
1.1.3.2    Fix console and ProgressDialog bugs
1.1.3.3    Fix pulseaudio
1.2.0.0    Add network support
1.2.0.1    Fix bugs
1.2.0.2    Fix huang up bugs
1.2.0.3    Add node7.zm.com
1.2.0.4    Fix status not update
1.2.0.5    Merge latest to PuDong
1.2.0.6    Standard Version
1.2.0.7    clear password after login
1.2.1.0    Add host setting
1.2.1.1    Fix some bugs
1.2.1.2    Fix process log system
1.2.2.0    Add IP.conf
1.3.0.0    Add RDP
2.0.0.0    havstack
2.1.1.0    admin permission
2.1.3.0    tickit
'''
import commands

major = 1
minor = 3
patch = 0
build = 0

def string(package, n):
    line = commands.getstatusoutput("rpm -qa | grep %s" %package)
    try:
        str = line[1].split("-", n)
        str = str[n].split(".fc")[0]
    except:
        str = 'unkown'
    return str

def GetOEMInfo():
    return u"标准版"

if __name__ == '__main__':
    print string('python-hav-gclient', 3)
    print string('spice-gtk', 2)
    print string('virt-viewer',2)
