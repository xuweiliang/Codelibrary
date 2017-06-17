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
from django.conf import settings  # noqa
from horizon import tables
from openstack_dashboard import api
from datetime import datetime as time
from openstack_dashboard.dashboards.admin.license import tables as project_tables
from django.utils.datastructures import SortedDict
from horizon import forms
import datetime
from django.core.urlresolvers import reverse_lazy
from openstack_dashboard.dashboards.admin.license import forms as register_forms
LOG = logging.getLogger(__name__)


class CreateLicenseView(forms.ModalFormView):
    form_class = register_forms.LicenseRegisterForm 
    template_name = 'admin/license/register.html' 
    success_url = reverse_lazy('horizon:admin:license:index')

    def get_initial(self):
        try:
            licence = api.nova.get_licence(self.request)
        except Exception:
            return {}
        return {'system_uuid': licence.system_uuid}


class LicenseView(tables.DataTableView):
    table_class = project_tables.DisplayTable
    template_name = 'admin/license/index.html'

    def get_context_data(self, **kwargs):
        context = super(LicenseView, self).get_context_data(**kwargs)
        return context

    def get_data(self):
        marker = self.request.GET.get(
            project_tables.DisplayTable._meta.pagination_param, None)
#        remote={"instance_id":"738d0981-523f-4185-9bd2-d496fb7b1807",
#                "instance_name":"win7","client_ip":"192.168.2.6","password":"31016", "status":"waitfor"}
#        remote = api.nova.create_remote(self.request, remote) 
        try:
            licence = api.nova.get_licence(self.request) 
            decoded_string = api.authcode.AuthCode.code_init(licence)
            licence.number = decoded_string['num']
            licence.available = decoded_string['num'] - licence.used
            licence.time = time.strptime(decoded_string['time'], '%Y-%m-%dT%H:%M:%S.%f')
            licence.during = licence.time + datetime.timedelta(days =decoded_string['during'])
        except Exception:
            self._more = False
            return []
        return [licence]

