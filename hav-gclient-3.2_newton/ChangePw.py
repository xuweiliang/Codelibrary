#!/usr/bin/env python
# coding=utf-8

import re
import wx
import havclient
import Resource
import Util
import Logger
import Session
import Setting
from Setting import FirstUser

class ChangePwDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"修改密码",
                           style = wx.BORDER_DOUBLE, size = (260, 350))
    
        self.Flag = False
        bmp = wx.StaticBitmap(self, -1, Resource.ui_banner)
        panel = wx.Panel(self)
        panel.SetBackgroundColour('#B3B2B3')
    
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(bmp, 0)
        sizer.Add(panel, 1, flag = wx.EXPAND)
    
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sizer, 0, flag = wx.EXPAND)
        mainSizer.AddSpacer(10)

        staticsizer = wx.BoxSizer(wx.HORIZONTAL)
        staticsizer.Add(wx.StaticText(self, -1, u'请输入符合规则的密码，规则如下：\n1.请输入6-14位字符。\n2.必须包含数字和字母。\n3.不允许空格。'), 0, wx.ALIGN_CENTER)

        mainSizer.AddSpacer(10)
        mainSizer.Add(staticsizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER)

        gbsizer=wx.BoxSizer(wx.VERTICAL)

        currentpw=wx.StaticText(self,-1,label=u'请输入当前密码：')
        newpw=wx.StaticText(self,-1,label=u'请输入新的密码：')
        checknewpw=wx.StaticText(self,-1,label=u'请确认新的密码：')
        self.currentpwText=wx.TextCtrl(self,-1,'',size=(200,25),style=wx.TE_PASSWORD)
        self.newpwText=wx.TextCtrl(self,-1,'',size=(200,25),style=wx.TE_PASSWORD)
        self.checknewpwText=wx.TextCtrl(self,-1,'',size=(200,25),style=wx.TE_PASSWORD)

        if self.checknewpwText.GetValue() == '':
            self.checknewpwText.SetFocus()
        if self.currentpwText.GetValue() == '':
            self.currentpwText.SetFocus()

        gbsizer.Add(currentpw, 0, wx.EXPAND)
        gbsizer.Add(self.currentpwText, 0, wx.EXPAND)
        gbsizer.Add(newpw, 0, wx.EXPAND)
        gbsizer.Add(self.newpwText, 0, wx.EXPAND)
        gbsizer.Add(checknewpw, 0, wx.EXPAND)
        gbsizer.Add(self.checknewpwText, 0, wx.EXPAND)

        mainSizer.AddSpacer(10)
        mainSizer.Add(gbsizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER) 

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_login = wx.Button(self, -1, u'修改')
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL, u'退出')

        sizer.Add(self.btn_login, 0, wx.ALIGN_CENTER)
        sizer.AddSpacer(25)
        sizer.Add(self.btn_cancel, 0, wx.ALIGN_CENTER)

        self.Bind(wx.EVT_BUTTON, self.OnChange, self.btn_login)

        mainSizer.AddSpacer(10)
        mainSizer.Add(sizer, 0, flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER)

        self.SetSizer(Util.CreateCenterSizer(mainSizer, 10))

    def OnChange(self, event):

        Logger.info("Change password!")

        currentpw = self.currentpwText.GetValue()
        newpw = self.newpwText.GetValue()
        checknewpw = self.checknewpwText.GetValue()

        if currentpw == u'' or newpw == u'' or checknewpw == u'':
            Util.MessageBox(self, u'密码不能为空。', u'错误', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE)
            Logger.info("The password is None!")
            return
        elif currentpw != Session.Password:
            Util.MessageBox(self, u'当前密码输入错误。', u'错误', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE)
            Logger.info("The current password is wrong!")
            return
        elif len(newpw) < 6 or len(newpw) > 14 or re.search(r"\W", newpw) or newpw.isalpha() or newpw.isdigit():
            Util.MessageBox(self, u'您输入的新密码不符合规则，请重新输入。', u'错误', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE)
            Logger.info("The new password doesn't conform to the rules!")
            return
        elif newpw != checknewpw:
            Util.MessageBox(self, u'两次输入的新密码不一致。', u'错误', wx.OK | wx.ICON_ERROR | wx.BORDER_DOUBLE)
            Logger.info("New passwords is not equally!")
            return

        try:
            havclient.user_update_own_password(FirstUser['firstuser'], currentpw, checknewpw)
            self.Flag = True
            Logger.info("The password is update successful!")
            Util.MessageBox(self, u'修改成功！\n请输入新的密码重新登录！', u'成功', wx.OK | wx.ICON_INFORMATION)

            self.Destroy()
        except:
            Util.MessageBox(self, u'修改失败！', u'错误', wx.OK | wx.ICON_ERROR)
            Logger.info("The password is update failing!")

if __name__ == '__main__':
    app = wx.PySimpleApp()
    Resource.load()
    frame = ChangePwDialog(None)
    ret = frame.ShowModal()
