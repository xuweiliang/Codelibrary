#!/usr/bin/env python
# coding=utf-8

'''
Created on Jun 12, 2012

@author: gf
'''
import wx
import threading
import subprocess
import Logger

def MessageBox(parent, msg, title, style):
    dlg = wx.MessageDialog(parent, msg, title, style)
    ret = dlg.ShowModal()
    dlg.Destroy()

    return ret

def CreateCenterSizer(win, gap):
    marginSizer = wx.FlexGridSizer(rows = 3, cols = 3)
    marginSizer.AddGrowableCol(1)
    marginSizer.AddGrowableRow(1)
    
    for i in range(0,4):
        marginSizer.AddSpacer(gap)

    marginSizer.Add(win, 0, wx.EXPAND)
    
    for i in range(0,4):
        marginSizer.AddSpacer(gap)
        
    return marginSizer

def RunConnectGuestWithLog(command):
    subprocess.Popen(command, shell=True)
    Logger.info("Connect success")


def RunShellWithLog(command):
    Logger.info("Launch Command:")  
    Logger.info(command)
    
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  
                         shell=True, universal_newlines=False)
    
    def LogStream(prefix, stream):
        while True:
            line = stream.readline()
            if not line:
                break
            Logger.info(prefix + line.strip())
            
    readout = threading.Thread(target=LogStream, args=("[OUT] ", p.stdout,))
    readerr = threading.Thread(target=LogStream, args=("[ERR] ", p.stderr,))

    readout.start()
    readerr.start()
    
    readout.join()
    readerr.join()
    p.wait()

    p.stdout.close()  
    p.stderr.close()
    
    Logger.info('Return Value : %d', p.returncode) 
  
    return p.returncode  

if __name__ == '__main__':
    RunShellWithLog('ls -l /')
