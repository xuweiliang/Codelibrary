# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
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

"""
Views for managing images.
"""
import uuid
import logging
import json

from django.core.urlresolvers import reverse
from django.forms import ValidationError  # noqa
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api

LOG = logging.getLogger(__name__)


class CreateStorageForm(forms.SelfHandlingForm):
    cache_disk = forms.CharField(widget=forms.HiddenInput())
    data_disk = forms.CharField(widget=forms.HiddenInput())
    node = forms.ChoiceField(label=_("Host Node"), initial="")
#    disk = forms.CharField(label=_("disk"), required=False)
#    format_disk = forms.BooleanField(label=_("Format Disk"))
    raid = forms.ChoiceField(label=_("Raid"), required=False)
    memory_cache = forms.IntegerField(label=_("Memory Cache"),
                               min_value=2,
                               max_value=128,
                               initial=4,
                               help_text=_("Memory cache defaults to 4G Max 128G."))

    def __init__(self, request, *args, **kwargs):
        super(CreateStorageForm, self).__init__(request, *args, **kwargs)
        storages = kwargs['initial']
        self.fields['node'].choices=self.populate_node_choices(request, storages)
        self.fields['raid'].choices=[("raid0",_("Raid0")),
                                     ("raid10",_("Raid10")),
                                     ("raidz",_("Raidz"))]

    def populate_node_choices(self, request, storages):
        stor=storages.get("storage")
        services = api.nova.service_list(request)
        choices = [(service.host, service.host) for service in services \
                          if service.binary == 'nova-compute' and service.host not in stor]
        if choices:
            choices.insert(0,("", _("Select a host node")))
        else:
            choices.insert(0,("",_("No free host node")))
        return choices

    def clean(self):
        cleand_data = super(CreateStorageForm, self).clean()
        host = cleand_data.get("node", None)
        cache = cleand_data.get("cache_disk", None)
        data = cleand_data.get("data_disk", None)
        raid = cleand_data.get("raid", None)
        checkdata = [] 
        if data:
            checkdata = data.split(',')
            cleand_data["data_disk"]=checkdata

        if host and not cache:
            raise ValidationError(_("no accelerator disk"))

        if host and not data:
            raise ValidationError(_("no data disk"))

        switch = {
            "raid0": True if len(checkdata) >= 2 else False,
            "raid10": True if len(checkdata) >= 4 and divmod(len(checkdata), 2)[-1] !=1 else False,
            "raidz": True if len(checkdata) >= 3 else False,
        }

        if switch[raid] == False:
            if raid == u'raid0':
                msg=_("%s mode requires at least 2 data disks.") % raid
            if raid == u'raid10':
                msg=_("%s mode requires at least 4 or more than 4 of "\
                      "the even number of data disks.") % raid
            if raid == u'raidz':
                msg=_("%s mode requires at least 3 data disks.") % raid
            self._errors['raid']=self.error_class([msg])
         
        return cleand_data

    def handle(self, request, data):
        storage_uuid=uuid.uuid4().hex
        api.storage.storage_create(request, 
                  storage_uuid=storage_uuid,
                  storage_name=data['node'],
             accelerate_disk=data['cache_disk'], 
                data_disk=data['data_disk'], 
          memory_cache=data['memory_cache'])
        return True

class ClearLocalStorageForm(forms.SelfHandlingForm):
    host = forms.ChoiceField(label=_("Host Node"), initial="")

    zfs_pool_select = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, request, *args, **kwargs):
        super(ClearLocalStorageForm, self).__init__(request, *args, **kwargs)
        storages = kwargs['initial']
        self.fields['host'].choices=self.populate_host_choices(request, storages)

    def populate_host_choices(self, request, storages):
        stor=storages.get("storage")
        services = api.nova.service_list(request)
        choices = [(service.host, service.host) for service in services \
                          if service.binary == 'nova-compute' and service.host not in stor]
        if choices:
            choices.insert(0,("",_("Select a host node")))
        else:
            choices.insert(0,("",_("No host needed clear")))
        return choices

    def clean(self):
        cleand_data = super(ClearLocalStorageForm, self).clean()
        host = cleand_data.get("host", None)
        zfs_pool_select = cleand_data.get("zfs_pool_select", None)
        if not zfs_pool_select:
            raise ValidationError(_('Please select a zfs pool that you need clear.'))
        return cleand_data

    def handle(self, request, data):
       try:
           result = api.storage.destroy_zfs_pools(request, data['host'], data['zfs_pool_select'])
           result_encode = json.loads(result.text)
           status = result_encode['status']
           if status == "ok":
               messages.success(request, _("Success to clear old zfs pool."))
           else:
               redirect = reverse('horizon:admin:storage:index')
               messages.error(request, _("The zfs pool is using and you cannot clear it."))
           return True
       except Exception:
           redirect = reverse('horizon:admin:storage:index')
           exceptions.handle(request, _("Fail to clear zfs pool."), redirect=redirect)

