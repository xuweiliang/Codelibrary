#!/usr/bin/env python

import Setting
import os
import re

if Setting.getLocalResolution().lower() == 'true':
    print 'auto'
    fp = os.popen('monitor-edid', 'r')
    content = fp.read()
    fp.close()

    reso = re.findall(r'ModeLine (\S+)', content)
    #print reso
    if reso:
        #print 'xrandr -s %s' % reso[0]
        os.system('xrandr -s %s' % reso[0])

else:
    pass
    print 'sign'
