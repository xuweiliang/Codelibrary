from horizon import forms
from horizon import tables
import logging
from horizon import exceptions
from datetime import datetime
from horizon.utils import memoized

from openstack_dashboard.dashboards.admin.spice_proxy import forms as proxy_forms
from openstack_dashboard.dashboards.admin.spice_proxy import tables as proxy_tables
from openstack_dashboard import api
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

LOG=logging.getLogger(__name__)

class DisplayView(tables.DataTableView):
    table_class =  proxy_tables.DisplayTable
    template_name = 'admin/spice_proxy/index.html'

    def get_data(self):
        try:
            spice_proxy = api.device.spice_proxy_list(self.request)
            for spice in spice_proxy:
                if spice.spice_proxy_flug:
                    spice.enabled_spice_proxy = "True"
                else:
                    spice.enabled_spice_proxy = "False"
        except Exception:
            spice_proxy = []
        return spice_proxy


class ProxyPatternView(forms.ModalFormView):
    form_class = proxy_forms.ProxyPatternForm
    template_name = 'admin/spice_proxy/update.html'
    success_url = reverse_lazy("horizon:admin:spice_proxy:index")

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.device.get_spice_proxy_by_id(self.request, self.kwargs['id'])
        except Exception:
            msg = _('Unable to retrieve spice proxy.')
            url = reverse('horizon:admin:spice_proxy:index')
            exceptions.handle(self.request, msg, redirect=url)

    def get_context_data(self, **kwargs):
        context = super(ProxyPatternView, self).get_context_data(**kwargs)
        context['id'] = self.kwargs['id']
        return context

    def get_initial(self):
        spice_proxy = self.get_object()
        return {'id':spice_proxy.id,'spice_proxy_flug':spice_proxy.spice_proxy_flug, 'http_port':spice_proxy.http_port}


class ModifyPortView(forms.ModalFormView):
    form_class = proxy_forms.ModifyPortForm
    template_name = 'admin/spice_proxy/modify_port.html'
    success_url = reverse_lazy("horizon:admin:spice_proxy:index")

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.device.get_spice_proxy_by_id(self.request, self.kwargs['id'])
        except Exception:
            msg = _('Unable to retrieve spice proxy.')
            url = reverse('horizon:admin:spice_proxy:index')
            exceptions.handle(self.request, msg, redirect=url)

    def get_context_data(self, **kwargs):
        context = super(ModifyPortView, self).get_context_data(**kwargs)
        context['id'] = self.kwargs['id']
        return context

    def get_initial(self):
        spice_proxy = self.get_object()
        return {'id':spice_proxy.id,'spice_proxy_flug':spice_proxy.spice_proxy_flug, 'http_port':
spice_proxy.http_port}

