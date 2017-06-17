# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Nebula, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import logging
import pytz
import random, string
import re
import sys
import operator
from openstack_dashboard import api
from django import shortcuts
from django.utils.translation import ugettext_lazy as _  # noqa
from horizon import forms
from horizon import messages
from datetime import datetime as time
from horizon import exceptions
from horizon.utils import validators
from django.utils import encoding
from openstack_dashboard.dashboards.project.instances.gfgq import AuthCode as code
from openstack_dashboard.openstack.common import jsonutils
from subprocess import PIPE,Popen
from openstack_dashboard import record_action
from django.http import HttpResponseRedirect
LOG = logging.getLogger(__name__)


class LicenseRegisterForm(forms.SelfHandlingForm):
    licence_heip=_("Please enter the serial number")

    cryptogram_help=_("If you need a new certificate, please send your service provider the Cryptogram")

    guofu = forms.CharField(widget=forms.widgets.Textarea,
                            label=_("Input licence"),
                            help_text = licence_heip,
                            required=True)

    cryptogram = forms.CharField(label=_("Cryptogram"),
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                                 help_text = cryptogram_help)

    def __init__(self, request, *args, **kwargs):
        super(LicenseRegisterForm, self).__init__(request, *args, **kwargs)

        old_licence = api.nova.get_licence(self.request)
        mima = old_licence.password
        connect = ":"
        computer_di = old_licence.compute_uuid
        cryptogram = computer_di + connect + mima
        self.fields['cryptogram'].initial = cryptogram

    def handle(self, request, data):
        response = shortcuts.redirect(request.build_absolute_uri())

        #update bufei by ggy
        new_password = self.GenPassword(8)

        #compare bufei by ggy
        a = api.nova.get_licence(self.request)
        mima = a.password
        old_compute_uuids = a.compute_uuid
        old_compute_uuid = old_compute_uuids.rstrip()
        try:
            guofu = data['guofu']
            LOG.info("type(%s)",type(guofu))
            decoded_string = eval(code.decode(guofu, 'fr1e54b8t4n4m47'))
            licence_num = decoded_string['num']
            during = decoded_string['during']

        #licence 9-2 add by ggy
            old_uuid = decoded_string['uuid']
            number = old_uuid.split(':')
            password = number[1]
            hardware_id = number[0]

            licence_day = time.strptime(decoded_string['time'], '%Y-%m-%dT%H:%M:%S.%f')
            plantime = time.strftime(licence_day, '%Y-%m-%d %H:%M:%S')
            registrationtime = plantime
            days = (time.now() - licence_day).days
            count = during
            if during > 0 and days < 3 and licence_num > 0 and password == str(mima) and hardware_id == str(old_compute_uuid):
                try:
                    api.nova.licence_update(request, count, plantime, registrationtime, new_password, guofu=data['guofu'])
                    messages.success(request, encoding.force_unicode(_("The input of success")))
                    result = True
                    message = "-"
                except Exception:
                    result = False
                    message = _("Input failure")
                    exceptions.handle(request, encoding.force_unicode(_("Input failure")))
            else:
                result = False
                message = _("The serial number is invalid")
                messages.error(request, encoding.force_unicode(message))
        except Exception:
            result = False
            message = _("Sequence number input error")
            messages.error(request, encoding.force_unicode(message))
        api.nova.systemlogs_create(request, '-', record_action.REGISTERLICENSE, result=result, detail=message)
        return HttpResponseRedirect('/dashboard/admin/licensedisplay')
        #return response

    def GenPassword(self, length):
        numOfNum = random.randint(1,length-1)
        numOfLetter = length - numOfNum
        slcNum = [random.choice(string.digits) for i in range(numOfNum)]
        slcLetter = [random.choice(string.ascii_letters) for i in range(numOfLetter)]
        slcChar = slcNum + slcLetter
        random.shuffle(slcChar)
        genPwd = ''.join([i for i in slcChar])
        return genPwd

