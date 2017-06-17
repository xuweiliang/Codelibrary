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
from openstack_dashboard.dashboards.admin.licensedisplay import tables as project_tables
from django.utils.datastructures import SortedDict
from horizon import forms
import datetime
from django.core.urlresolvers import reverse_lazy
from openstack_dashboard.dashboards.admin.licensedisplay.gfgq import AuthCode as code
from openstack_dashboard.dashboards.admin.licensedisplay import forms as register_forms
LOG = logging.getLogger(__name__)


class CreateLicenseView(forms.ModalFormView):
    form_class = register_forms.LicenseRegisterForm 
    template_name = 'admin/licensedisplay/settings.html' 
    success_url = reverse_lazy('horizon:admin:licensedisplay:index')


class LicenseDisplayView(tables.DataTableView):
    table_class = project_tables.DisplayTable
    template_name = 'admin/licensedisplay/index.html'

#    def get_context_data(self, **kwargs):
#        context = super(LicenseDisplayView, self).get_context_data(**kwargs)
#        return context

    def get_data(self):
	#licences = {}
        marker = self.request.GET.get(
            project_tables.DisplayTable._meta.pagination_param, None)
        try:
#           
            licences = api.nova.get_licence(self.request) 
            licences.bb = 'aaaaaaaaaa'
            LOG.info("licences ======================%s" % licences.__dict__)
            decoded_string = eval(code.decode(licences.guofudata, 'fr1e54b8t4n4m47'))
            #licencesa=decoded_string
	    number = decoded_string['num']
	    during = decoded_string['during']
	    available = number - licences.used
            licences.number = number
	    licences.available = available
            #licences.time = decoded_string['time']
	    licences.time = time.strptime(decoded_string['time'], '%Y-%m-%dT%H:%M:%S.%f')
	    licences.time = time.strptime(licences.registrationtime, '%Y-%m-%dT%H:%M:%S.%f')
	    d1 = licences.time
            licences.during = d1 + datetime.timedelta(days = during)
        except Exception:
            self._more = False
        return [licences]

