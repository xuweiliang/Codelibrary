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
from django.core.urlresolvers import reverse
from openstack_dashboard import api
from django import shortcuts
from django.utils.translation import ugettext_lazy as _  # noqa
from horizon import forms
from horizon import messages
from datetime import datetime as time
from horizon import exceptions
from horizon.utils import validators
from django.utils import encoding
from subprocess import PIPE,Popen
from django.http import HttpResponseRedirect
from openstack_dashboard import record_action
LOG = logging.getLogger(__name__)


class LicenseRegisterForm(forms.SelfHandlingForm):
    licence_heip=_("Please enter the serial number")
    cryptogram_help=_("If you need a new certificate,\
                      please send your service provider the Cryptogram")

    encrypted_license = forms.CharField(widget=forms.widgets.Textarea,
                            label=_("Input licence"),
                            help_text = licence_heip,
                            required=True)

    system_uuid = forms.CharField(label=_("Cryptogram"),
                                 widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                                 help_text = cryptogram_help)

    def __init__(self, request, *args, **kwargs):
        super(LicenseRegisterForm, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        try:
            licence = data.get('encrypted_license', None).strip()
            systemUUID = data.get('system_uuid')
            UUID, key = systemUUID.split(":")
            decoded_string = eval(api.authcode.AuthCode.decode(licence, UUID.strip()))
            during = decoded_string.get('during', None) 
            num = decoded_string.get('num', None)
            authcode = decoded_string.get('uuid')
            uuid, pwd = authcode.split(":")
            licenceTime = decoded_string.get('time', None)
            if uuid != UUID:
                messages.error(request,
                encoding.force_unicode(_("Serial number can only activate\
                                          the specified server")))
                api.nova.systemlogs_create(request, '-',\
                                   record_action.REGISTERLICENSE,
                                    result=False, detail=_("Licence Register Fail"))
                return HttpResponseRedirect('/dashboard/admin/license')
            date  = time.strptime(licenceTime, '%Y-%m-%dT%H:%M:%S.%f')
            starttime = time.strftime(date, '%Y-%m-%d %H:%M:%S')
            apartDays =(time.now()- date).days
            if during > 0 and apartDays < 3 and num > 0:
                kwargs={'licence':{'starttime':starttime, 
                                   'system_uuid':authcode,
                                   'encrypted_license':licence,
                                   'disabled':False}} 
                try:
                    api.nova.update_licence(request, **kwargs)
                    msg = _("Serial number authentication success")
                    messages.success(request, 
                    encoding.force_unicode(msg)) 
                    api.nova.systemlogs_create(request, '-',\
                                   record_action.REGISTERLICENSE, 
                                    result=True, detail=msg)
                    return True
                except Exception as e:
                    exceptions.handle(request, 
                        encoding.force_unicode(_("%s", e)))
                    api.nova.systemlogs_create(request, '-',\
                                   record_action.REGISTERLICENSE,
                                    result=False, detail=_("Licence Register Fail"))
                    return False 
            else:
                messages.error(request,
                encoding.force_unicode(_("Serial number expired or invalid")))
                api.nova.systemlogs_create(request, '-',\
                                   record_action.REGISTERLICENSE,
                                    result=False, detail=_("Licence invalid"))
                return HttpResponseRedirect('/dashboard/admin/license')
        except Exception as e:
            exceptions.handle(request, 
                encoding.force_unicode(_("Invalid serial number \
                                               or registration error %s" % e)))
        api.nova.systemlogs_create(request, '-',\
                                   record_action.REGISTERLICENSE, 
                                    result=True, detail=_("Licence Register Success"))
        return True
