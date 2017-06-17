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
import json

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from django.views import generic

from horizon import exceptions
from horizon import forms
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard import api

from openstack_dashboard.dashboards.admin.storage.storage \
    import forms as project_forms
from openstack_dashboard.dashboards.admin.storage.storage \
    import tables as project_tables

from oslo_log import log

LOG = log.getLogger(__name__)

def select_disk(request):
    response = HttpResponse(content_type='text/plain')
    hostname= request.GET.get('node', None)
    free_disk = api.storage.get_free_disk(request, hostname)
    disk_encode = json.loads(free_disk.text)
    disk_list = [{key:disk_encode[key]} for key in disk_encode]
    #LOG.info("key ====================%s" % disk_list)
    try:
        disk = ["sda","sdb","sdc", "sdd", "sde","sdf","sdg"]
        data = request.GET['callback']+'({"success":'+json.dumps(disk_list)+'})'
        response.write(data)
    except Exception:
        response.write("")
    response.flush()
    return response    

def select_zfs_pools(request):
    response = HttpResponse(content_type='text/plain')
    host = request.GET.get('host', None)
    zfs_pools =api.storage.get_zfs_pools(request, host)
    zfs_pools_encode = json.loads(zfs_pools.text)
    zfs_pools_list = zfs_pools_encode['pools']
    try:
       data = request.GET['callback']+'({"success":'+json.dumps(zfs_pools_list)+'})'
       response.write(data)
    except Exception:
       response.write("")
    response.flush()
    return response


def cache_partition(request):
    response = HttpResponse(content_type='text/plain')
    cache_disk = request.GET.get('cache_disk', None)
    try:
        data = request.GET['callback']+'({"success":"success"})'
        response.write(data)
    except Exception:
        response.write("")
    response.flush()
    return response

def storage_status(request):
    response = HttpResponse(content_type='text/plain')
    status_id = request.GET.get('id', None)
    status_list = json.loads(status_id)
    storage = api.storage.storage_list(request)
    status = []
    for s in storage:
        if s.id in status_list:
            status = [{"id":s.id, "_status":s.accelerate_status}]
    try:
        data = request.GET['callback']+'({"success":'+json.dumps(status)+'})'
        response.write(data)
    except Exception:
        response.write("")
    response.flush()
    return response

class CreateView(forms.ModalFormView):
    form_class = project_forms.CreateStorageForm
    template_name = 'admin/storage/storage/create.html'
    context_object_name = 'storage'
    success_url = reverse_lazy("horizon:admin:storage:index")

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)
        return context

    def get_initial(self):
        storage = [s.storage_name for s in api.storage.storage_list(self.request)]
        #storage = []
        return {'storage':storage}

class ClearStorageView(forms.ModalFormView):
    form_class = project_forms.ClearLocalStorageForm
    template_name = 'admin/storage/storage/clearstorage.html'
    context_object_name = 'storage'
    success_url = reverse_lazy("horizon:admin:storage:index")

    def get_context_data(self, **kwargs):
        context = super(ClearStorageView, self).get_context_data(**kwargs)
        return context

    def get_initial(self):
        storage = [s.storage_name for s in api.storage.storage_list(self.request) if s.accelerate_status != "error"]
        return {'storage':storage}
