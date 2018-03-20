#! /usr/bin/env python
#coding:UTF-8

import wx
import Util
import Logger
from PIL import Image
import Setting
import ProgressDialog
import Console
import havclient
import Session
import MainFrame
ui_login_user = "images/user.bmp"

[wxID_FRAME1, wxID_FRAME1BMPUSER, wxID_FRAME1BTNCANCEL, wxID_FRAME1BTNOK, 
 wxID_FRAME1INPUT_DOMAIN, wxID_FRAME1INPUT_PASSWORD, 
 wxID_FRAME1INPUT_USERNAME, wxID_FRAME1PANEL1, wxID_FRAME1RADIOISADMIN, 
 wxID_FRAME1STATICLINE1, wxID_FRAME1TXTDOMAIN, wxID_FRAME1TXTIPADDR, 
 wxID_FRAME1TXTPASSWORD, wxID_FRAME1TXTPROMPT1, wxID_FRAME1TXTPROMPT2, 
 wxID_FRAME1TXTUSERNAME, 
] = [wx.NewId() for _init_ctrls in range(16)]

class RDPLoginDialog(wx.Dialog):
    def _init_ctrls(self, vm, Type):
        wx.Dialog.__init__(self, id=wxID_FRAME1, name='', parent=None,
              pos=wx.Point(773, 309), size=wx.Size(550, 361),
              style=wx.BORDER_DOUBLE, title=u'Windows\u5b89\u5168')
        self.vm = vm
        self.Type = Type
        self.SetClientSize(wx.Size(465, 260))
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.Center(wx.BOTH)
        self.Enable(True)

        self.btnCancel = wx.Button(id=wxID_FRAME1BTNCANCEL,
              label=u'\u53d6\u6d88', name=u'btnCancel', parent=self,
              pos=wx.Point(285, 200), size=wx.Size(72, 30), style=0)
        self.btnCancel.Bind(wx.EVT_BUTTON, self.OnBtnCancelButton,
              id=wxID_FRAME1BTNCANCEL)

        self.btnOK = wx.Button(id=wxID_FRAME1BTNOK, label=u'\u786e\u5b9a',
              name=u'btnOK', parent=self, pos=wx.Point(175, 200),
              size=wx.Size(72, 30), style=0)
        self.btnOK.SetFocus()
        self.btnOK.Bind(wx.EVT_BUTTON, self.OnBtnOKButton, id=wxID_FRAME1BTNOK)

        self.staticLine1 = wx.StaticLine(id=wxID_FRAME1STATICLINE1,
              name='staticLine1', parent=self, pos=wx.Point(23, 80),
              size=wx.Size(424, 3), style=0)
        self.staticLine1.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.staticLine1.Center(wx.HORIZONTAL)

        self.txtPrompt1 = wx.StaticText(id=wxID_FRAME1TXTPROMPT1,
              label='请输入您的凭据', name=u'txtPrompt1', parent=self,
              pos=wx.Point(24, 16), size=wx.Size(400, 20), style=1)
        font=wx.Font(14,wx.DEFAULT,wx.NORMAL,wx.NORMAL)
        self.txtPrompt1.SetFont(font)
        self.txtPrompt1.SetForegroundColour(wx.Colour(0, 51, 153))
        self.txtPrompt1.Enable(True)

        ip = havclient.get_vm_ip(self.vm)
        self.txtIPaddr = wx.StaticText(id=wxID_FRAME1TXTIPADDR, label=u'这些凭据将用于连接：'+ ip,
        name=u'txtIPaddr', parent=self, pos=wx.Point(24, 50),
        size=wx.Size(300, 20), style=0)

        self.radioIsAdmin = wx.RadioButton(id=wxID_FRAME1RADIOISADMIN,
              label=u'\u7ba1\u7406\u5458', name=u'radioIsAdmin', parent=self,
              pos=wx.Point(366, 107), size=wx.Size(66, 17), style=0)
        self.radioIsAdmin.SetValue(False)
        self.radioIsAdmin.Bind(wx.EVT_RADIOBUTTON,
              self.OnRadioIsAdminRadiobutton, id=wxID_FRAME1RADIOISADMIN)

        self.txtUsername = wx.StaticText(id=wxID_FRAME1TXTUSERNAME,
              label=u'\u7528\u6237\u540d', name=u'txtUsername', parent=self,
              pos=wx.Point(134, 107), size=wx.Size(40, 24), style=0)
    
        self.txtPassword = wx.StaticText(id=wxID_FRAME1TXTPASSWORD,
              label=u'\u5bc6\u7801', name=u'txtPassword', parent=self,
              pos=wx.Point(134, 157), size=wx.Size(40, 24), style=0)


        self.Input_username = wx.TextCtrl(id=wxID_FRAME1INPUT_USERNAME,
              name=u'Input_username', parent=self, pos=wx.Point(175, 104),
              size=wx.Size(180, 26), style=0, value=u'')
        self.Input_username.SetInsertionPoint(0)

        self.Input_password = wx.TextCtrl(id=wxID_FRAME1INPUT_PASSWORD,
              name=u'Input_password', parent=self, pos=wx.Point(175, 152),
              size=wx.Size(180, 26), style=wx.PASSWORD, value=u'')

        self.bmpUser = wx.StaticBitmap(bitmap=wx.NullBitmap,
              id=wxID_FRAME1BMPUSER, name=u'bmpUser', parent=self,
              pos=wx.Point(28, 92), size=wx.Size(88, 96), style=0)

        btn_login = wx.Bitmap(ui_login_user)
        self.bmpUser.SetBitmap(btn_login)
        self.bmpUser.SetThemeEnabled(True)

    def __init__(self, vm, Type):
        self._init_ctrls(vm, Type)
 
    def OnBtnCancelButton(self, event):
        self.Destroy()
        event.Skip()

    def OnBtnOKButton(self, event):
        username = self.Input_username.GetValue()
        password = self.Input_password.GetValue()

        if Setting.getPublic().lower() == "true":
            try:
                image_lists = havclient.image_list(FirstUser['firstuser'])
                for i in image_lists:
                    if i.name == u'Port':
                        image_info = havclient.data(FirstUser['firstuser'], i.id)
                        break
                havclient.download_templet(image_info)
                Logger.info("Download status:Download hosts successful!")
            except:
                Logger.info("Download status:Download hosts unsuccessful!")
        else:
            pass

        if username == '' or password == '' :
            Util.MessageBox(self, u'缺少用户名或密码!', u'错误', wx.OK | wx.ICON_ERROR)
            return
        else:
            Setting.setUser(username)
            Setting.setCipher(password)
            Setting.save()
            dlg = ProgressDialog.ProgressDialog(self, u'连接服务器...')
            thread = Console.LaunchThread(self.vm.tenant_id, self.vm, self.Type, dlg)
            thread.start()
            if dlg.ShowModal() == wx.ID_CANCEL:
                thread.stop()
            else:
                thread.join()
            self.Destroy()
            event.Skip()

    def OnRadioIsAdminRadiobutton(self, event):
        self.Input_username.SetValue("Administrator")
        self.Input_password.SetFocus()
        event.Skip()
        
if __name__ == '__main__':
    app = wx.App()
    frame = RDPLoginFrame(vm)
    frame.Show()
    app.MainLoop()
