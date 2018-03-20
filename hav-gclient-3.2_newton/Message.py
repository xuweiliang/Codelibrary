#!coding=utf-8
import wx
import sys

def message(data):
    app = wx.PySimpleApp()
    dlg = wx.MessageDialog(None, "系统管理员向您发送了一条信息，请查看：\n\n%s" % data, "新的信息", wx.OK | wx.STAY_ON_TOP)
    dlg.ShowModal()
    dlg.Destroy()

if __name__=="__main__":
    message(sys.argv[1])
