# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
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

import netaddr
import re
import logging
import subprocess

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from openstack_dashboard import api

LOG = logging.getLogger(__name__)

class MessageForm(forms.SelfHandlingForm):
    id_message = forms.CharField(widget=forms.HiddenInput())
    message = forms.CharField(widget=forms.widgets.Textarea,
                            max_length=100,
                            label=_("Message Box"),
                            required=True)

    def __init__(self, request, *args, **kwargs):
        super(MessageForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        message_id = initial.get('device_id')

        self.fields['id_message'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=message_id)
    def handle(self, request, data):
        result = api.device.sendmessage(request, data)
        redirect = reverse('horizon:admin:device:index')
        if result.text != unicode(1):
            msg = _('Message has been sent successfully.')
            messages.success(request, msg)
        else:
            msg=_('Message sent failed please check whether online.')
            messages.error(request, msg)
        return redirect

class DeleteForm(forms.SelfHandlingForm):
    id = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, request, *args, **kwargs):
        super(DeleteForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        device_id = initial.get('device_id')

        self.fields['id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=device_id)

    def handle(self, request, data):
        try:
            api.device.delete(request, data)
            msg = _('The device  is successful delete .')
            messages.success(request, msg)
        except Exception:
            msg=_('Failed to delete device')
            redirect = reverse('horizon:admin:device:index')
            exceptions.handle(request, msg, redirect=redirect)
        return True

class UpdateForm(forms.SelfHandlingForm):
    id_update = forms.CharField(widget=forms.HiddenInput())
    hostname = forms.CharField(label=_("Host Name"), required=False, max_length=20)
    network_type = forms.ChoiceField(label=_("Network Operate Type"),
        choices=[('remain', _('Remain')),('dhcp',_('DHCP')), ('static',_('Static'))],
                               initial="remain", required=False) 
    ipaddr = forms.CharField(label=_("IP Addr"), required=False)
    gateway = forms.CharField(label=_("Gateway"), required=False)
    mask = forms.CharField(label=_("Subnet Mask"), required=False, initial='255.255.255.0')
    dns = forms.CharField(label=_("DNS"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(UpdateForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        device_id = initial.get('device_id')
        device = api.device.get(request, device_id)
        self.fields['ipaddr'].initial=device.ip if device else None
        self.fields['gateway'].initial=device.gateway if device else None
        self.fields['id_update'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=device_id)

    def clean(self):
        cleaned_data = super(UpdateForm, self).clean()
        ip_update = cleaned_data.get("id_update", None)
        hostname =cleaned_data.get("hostname", None)
        network_type = cleaned_data.get("network_type", None)
        ipaddr =cleaned_data.get("ipaddr", None)
        gateway =cleaned_data.get("gateway", None)
        mask =cleaned_data.get("mask", None)
        dns =cleaned_data.get("dns", None)
        matching = re.compile('^[A-Za-z0-9]+$',re.S)

        if hostname and not matching.match(hostname):
            msg = _("Host name error.")
            self._errors['hostname'] = self.error_class([msg])

        try:
            if dns:
                value = netaddr.IPNetwork(dns)
        except Exception:
            msg = _("DNS format is not correct.")
            self._errors['dns'] = self.error_class([msg])

        if network_type != 'static':
            return cleaned_data

        if not ipaddr:
            msg =_("IP address must be specified.")
            self._errors['ipaddr']=self.error_class([msg])
        if not gateway:
            msg =_("Gateway must be specified.")
            self._errors['gateway']=self.error_class([msg])
        if not mask:
            msg =_("Subnet mask must be specified.")
            self._errors['mask']=self.error_class([msg])

        try:
            if ipaddr:
                value = netaddr.IPNetwork(ipaddr) 
        except Exception:
            msg = _("IP address format is incorrect.")
            self._errors['ipaddr'] = self.error_class([msg])
        try:
            if gateway:
                value = netaddr.IPNetwork(gateway) 
        except Exception:
            msg = _("Gateway format is not correct.")
            self._errors['gateway'] = self.error_class([msg])

        try:
            if mask:
                value = netaddr.IPNetwork(mask)
        except Exception:
            msg = _("Subnet mask format is not correct.")
            self._errors['mask'] = self.error_class([msg])

        return cleaned_data

            
    def handle(self, request, data):
        try:
            result = api.device.update_devive(request, data)
            msg = _('Client to modify the device information has been successfully sent.The name will be updated when client reboot.')
            messages.success(request, msg)
            return True
        except Exception:
            msg = _('Modified failure try again later.')
            messages.error(request, msg)
            redirect = reverse('horizon:admin:device:index')
            return redirect


class RebootForm(forms.SelfHandlingForm):
    device_id = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, request, *args, **kwargs):
        super(RebootForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        reboot_id = initial.get('device_id')
        self.fields['device_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=reboot_id)

    def handle(self, request, data):
        result=api.device.reboot(request, data)
        if result is True:
            msg = _('This device has been successfully restarted.')
            messages.success(request, msg)
            return result
        msg=_('Failed to restart, Connection refused') 
        messages.error(request, msg)
        redirect = reverse('horizon:admin:device:index')
        return redirect


