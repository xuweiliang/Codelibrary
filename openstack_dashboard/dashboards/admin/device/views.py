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
Views for managing device.
"""
import json
import logging
import subprocess

from django.core.urlresolvers import reverse_lazy
from django import http
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import messages

from openstack_dashboard import api

from openstack_dashboard.dashboards.admin.device \
    import forms as project_forms
from openstack_dashboard.dashboards.admin.device \
    import tables as project_tables

LOG = logging.getLogger(__name__)

def ajax_status_view(request):
    status = [] 
    dicts = {}
    id_number = request.GET.get('id_number', None)
    id_list = json.loads(id_number)   
    devices=api.device.device_list(request)
    status = []
    for dev in devices:
        if dev.id in id_list:
            data = {'status':dev.status,
                    'hostname':dev.hostname,
                    'ip':dev.ip,
                    'id':dev.id}
            status.append(data)
    try:
        status =[{
                  'status': [dev.status for dev in devices if dev.id==id][-1],
                  'hostname': [dev.hostname for dev in devices if dev.id==id][-1],
                  'id': id} for id in id_list]
    except:
        status =[]
    data = request.GET['callback']+'({"success":'+json.dumps(status)+'})'
    response = http.HttpResponse(content_type='text/plain')
    response.write(data)
    response.flush()
    return response


def check_ipaddr_view(request):
    ipaddr= request.GET.get("ipaddr", None)
    source_id = request.GET.get("source_id", None)
    device = api.device.get(request, source_id)
    source_ip = device.ip if device else None
    device_list = api.device.device_list(request)
    list_ip = [dev.ip for dev in device_list if dev.ip != source_ip]
    result = api.device.device_ipaddr(request, ipaddr)
    if ipaddr in list_ip:
        result = 0
    elif ipaddr == source_ip:
        result = 1
    data = request.GET['callback']+'({"valid":'+str(result)+'})'
    response = http.HttpResponse(content_type='text/plain')
    response.write(data)
    response.flush()
    return response

class DeleteView(forms.ModalFormView):
    form_class = project_forms.DeleteForm
    template_name = 'admin/device/delete.html'
    success_url = reverse_lazy('horizon:admin:device:index')

    def get_context_data(self, **kwargs):
        context = super(DeleteView, self).get_context_data(**kwargs)
        context['device_id'] = self.kwargs['id']
        return context

    def get_initial(self):
        return {'device_id': self.kwargs}

class UpdateView(forms.ModalFormView):
    form_class = project_forms.UpdateForm
    template_name = 'admin/device/update.html'
    success_url = reverse_lazy('horizon:admin:device:index')

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['id'] = self.kwargs['id']
        return context

    def get_initial(self):
        return {'device_id': self.kwargs['id']}

class RebootView(forms.ModalFormView):
    form_class = project_forms.RebootForm
    template_name = 'admin/device/reboot.html'
    success_url = reverse_lazy('horizon:admin:device:index')
    def get_context_data(self, **kwargs):
        context = super(RebootView, self).get_context_data(**kwargs)
        context['device_id'] = self.kwargs['device_id']
        return context

    def get_initial(self):
        return {'device_id': self.kwargs['device_id']}

class SendMessageView(forms.ModalFormView):
    form_class = project_forms.MessageForm
    template_name = 'admin/device/send.html'
    success_url = reverse_lazy('horizon:admin:device:index')

    def get_context_data(self, **kwargs):
        context = super(SendMessageView, self).get_context_data(**kwargs)
        context['id'] = self.kwargs['id']
        return context

    def get_initial(self):
        return {'device_id': self.kwargs['id']}

class IndexView(tables.DataTableView):
    table_class = project_tables.DeviceTable
    template_name = 'admin/device/index.html'

    def get_data(self):
        device = api.device.device_list(self.request)
        #context = self.get_context_data()
#        dev = api.device.get(self.request, 77)
        return device

