#!/usr/bin/env python
# coding=utf-8
'''
Created on Jun 12, 2012

@author: gf
'''
import wx
import Logger
from PIL import Image

ui_login = "images/gf_login_ui.png"
btn_login = "images/login.png"
btn_shutdown = "images/close.png"
ui_banner = "images/banner.png"
running = "images/RUNNING.png"
paused = "images/PAUSED.png"
stopped = "images/STOPPED.png"
waiting = "images/WAITING.png"
starting = "images/STARTING.png"
stopping = "images/STOPPING.png"
questionmark = "images/QUESTIONMARK.png"

floats = "images/enfloats.png"

play = "images/play.gif"
pause = "images/pause.gif"
shutdown = "images/stop.gif"
resume = "images/resume.gif"
stop = "images/shutdown.png"
reboot = "images/reboot.gif"
console = "images/console.png"
refresh = "images/refresh.png"

vm_icon = "images/vm_icon.png"
memory_icon = "images/memory_icon.png"
cpu_icon = "images/cpu_icon.png"
storage_icon = "images/storage_icon.png"
spice_icon = "images/spice_icon.png"
Count = "images/Count.png"
status_icon = "images/status_icon.png"
usb_icon = "images/usb_icon.png"

screenX = None
screenY = None

def load(width = 1440, height = 900):
    try:
        """
        Resize Login UI and Two buttons
        """
        Logger.info("Resource Load Size : %dx%d", width, height)
        
        global ui_login
        image = Image.open(ui_login)
        iw, ih = image.size
        xradio = float(width) / iw
        yradio = float(height) / ih
        screenX = width
        screenY = height
        Logger.debug("Login UI scale radio : %f x %f", xradio, yradio)
        
        nimage = image.resize((width, height), Image.BICUBIC)
        ui_login = '/tmp/ui_login_%d_%d.png' % (width, height)
        nimage.save(ui_login)
        ui_login = wx.Bitmap(ui_login)
        
        global btn_login
        image = Image.open(btn_login)
        iw, ih = image.size
        nimage = image.resize(
                    (int(xradio * iw), int(yradio * ih)), Image.BICUBIC)
        btn_login = '/tmp/btn_login_%d_%d.png' % (int(xradio * iw), int(yradio * ih))
        nimage.save(btn_login)
        btn_login = wx.Bitmap(btn_login)
        
        global btn_shutdown
        image = Image.open(btn_shutdown)
        iw, ih = image.size
        nimage = image.resize(
                    (int(xradio * iw), int(yradio * ih)), Image.BICUBIC)
        btn_shutdown = '/tmp/btn_shutdown_%d_%d.png' % (int(xradio * iw), int(yradio * ih))
        nimage.save(btn_shutdown)
        btn_shutdown = wx.Bitmap(btn_shutdown)
        
        # banner 
        global ui_banner, waiting, starting, stopping, stopped
        global paused, running, questionmark, floats
        ui_banner = wx.Bitmap(ui_banner)
        
        # VM Status
        waiting = wx.Bitmap(waiting)
        starting = wx.Bitmap(starting)
        stopping = wx.Bitmap(stopping)
        stopped = wx.Bitmap(stopped)
        paused = wx.Bitmap(paused)
        running = wx.Bitmap(running)
        questionmark = wx.Bitmap(questionmark)
        floats = wx.Bitmap(floats)

        # Button
        global play, pause, resume, shutdown, stop, reboot, console, refresh
        play = wx.Bitmap(play)
        pause = wx.Bitmap(pause)
        resume = wx.Bitmap(resume)
        shutdown = wx.Bitmap(shutdown)
        stop = wx.Bitmap(stop)
        reboot = wx.Bitmap(reboot)
        console = wx.Bitmap(console)
        refresh = wx.Bitmap(refresh)
        
        # Icon
        global vm_icon, memory_icon, cpu_icon, storage_icon, spice_icon, status_icon, usb_icon, Count
        vm_icon = wx.Bitmap(vm_icon)
        memory_icon = wx.Bitmap(memory_icon)
        cpu_icon = wx.Bitmap(cpu_icon)
        storage_icon = wx.Bitmap(storage_icon)
        spice_icon = wx.Bitmap(spice_icon)
        Count = wx.Bitmap(Count)
        status_icon = wx.Bitmap(status_icon)
        usb_icon = wx.Bitmap(usb_icon)
        
    except IOError:
        print 'Initialize resources failed!'
        


if __name__ == '__main__':
    import wx
    
    app = wx.PySimpleApp()
    width, height = wx.ScreenDC().GetSize()
    load(width, height)
    print ui_login
