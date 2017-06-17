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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard.api import cinder

from openstack_dashboard import api

from openstack_dashboard.dashboards.admin.volumes \
    .snapshots import forms as vol_snapshot_forms
from openstack_dashboard.dashboards.admin.volumes \
    .snapshots import tables as vol_snapshot_tables
from openstack_dashboard.dashboards.admin.volumes \
    .snapshots import tabs as vol_snapshot_tabs

class UpdateStatusView(forms.ModalFormView):
    form_class = vol_snapshot_forms.UpdateStatus
    modal_header = _("Update Volume Snapshot Status")
    modal_id = "update_volume_snapshot_status"
    template_name = 'admin/volumes/snapshots/update_status.html'
    submit_label = _("Update Status")
    submit_url = "horizon:admin:volumes:snapshots:update_status"
    success_url = reverse_lazy("horizon:admin:volumes:snapshots_tab")
    page_title = _("Update Volume Snapshot Status")

    @memoized.memoized_method
    def get_object(self):
        snap_id = self.kwargs['snapshot_id']
        try:
            self._object = cinder.volume_snapshot_get(self.request,
                                                      snap_id)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve volume snapshot.'),
                              redirect=self.success_url)
        return self._object

    def get_context_data(self, **kwargs):
        context = super(UpdateStatusView, self).get_context_data(**kwargs)
        context['snapshot_id'] = self.kwargs["snapshot_id"]
        args = (self.kwargs['snapshot_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        snapshot = self.get_object()
        return {'snapshot_id': self.kwargs["snapshot_id"],
                'status': snapshot.status}

class DetailView(tabs.TabView):
    tab_group_class = vol_snapshot_tabs.SnapshotDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ snapshot.name|default:snapshot.id }}"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        snapshot = self.get_data()
        table = vol_snapshot_tables.VolumeSnapshotsTable(self.request)
        context["snapshot"] = snapshot
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(snapshot)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            snapshot_id = self.kwargs['snapshot_id']
            snapshot = api.cinder.volume_snapshot_get(self.request,
                                                      snapshot_id)
        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve snapshot details.'),
                              redirect=redirect)
        return snapshot

    @staticmethod
    def get_redirect_url():
        return reverse('horizon:admin:volumes:index')

    def get_tabs(self, request, *args, **kwargs):
        snapshot = self.get_data()
        return self.tab_group_class(request, snapshot=snapshot, **kwargs)
