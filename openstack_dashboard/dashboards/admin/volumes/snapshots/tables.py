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

from django.core.urlresolvers import reverse
from django.utils import html
from django.utils.http import urlencode
from django.utils import safestring
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.utils.datastructures import SortedDict

from horizon import tables

from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import cinder
from openstack_dashboard import policy

from openstack_dashboard.dashboards.admin.volumes \
    .volumes import tables as volume_tables
import logging

LOG = logging.getLogger(__name__)

class LaunchSnapshot(volume_tables.LaunchVolume):
    name = "launch_snapshot"

    def get_link_url(self, datum):
        base_url = reverse(self.url)

        vol_id = "%s:snap" % self.table.get_object_id(datum)
        params = urlencode({"source_type": "volume_snapshot_id",
                            "source_id": vol_id})
        return "?".join([base_url, params])

    def allowed(self, request, snapshot=None):
        if snapshot:
            if (snapshot._volume and
                    getattr(snapshot._volume, 'bootable', '') == 'true'):
                return snapshot.status == "available"
        return False


class DeleteVolumeSnapshot(policy.PolicyTargetMixin, tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Volume Snapshot",
            u"Delete Volume Snapshots",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of Volume Snapshot",
            u"Scheduled deletion of Volume Snapshots",
            count
        )

    policy_rules = (("volume", "volume:delete_snapshot"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    def delete(self, request, obj_id):
        api.cinder.volume_snapshot_delete(request, obj_id)


class EditVolumeSnapshot(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Snapshot")
    url = "horizon:admin:volumes:snapshots:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("volume", "volume:update_snapshot"),)
    policy_target_attrs = (("project_id",
                            'os-extended-snapshot-attributes:project_id'),)

    def allowed(self, request, snapshot=None):
        return snapshot.status == "available"


class CreateVolumeFromSnapshot(tables.LinkAction):
    name = "create_from_snapshot"
    verbose_name = _("Create Volume")
    url = "horizon:admin:volumes:volumes:create"
    classes = ("ajax-modal",)
    icon = "camera"
    policy_rules = (("volume", "volume:create"),)

    def get_link_url(self, datum):
        base_url = reverse(self.url)
        params = urlencode({"snapshot_id": self.table.get_object_id(datum)})
        return "?".join([base_url, params])

    def allowed(self, request, volume=None):
        if volume and base.is_service_enabled(request, 'volume'):
            return volume.status == "available"
        return False


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, snapshot_id):
        snapshot = cinder.volume_snapshot_get(request, snapshot_id)
        snapshot._volume = cinder.volume_get(request, snapshot.volume_id)
        try:
            tenants, has_more = api.keystone.tenant_list(request)
        except Exception:
            tenants = []
            msg = _('Unable to retrieve volume project information.')

        tenant_dict = SortedDict([(t.id, t) for t in tenants])
        tenant_id = getattr(snapshot, "os-extended-snapshot-attributes:project_id", None)
        tenant = tenant_dict.get(tenant_id, None)
        snapshot.tenant_name = getattr(tenant, "name", None)

        return snapshot


class SnapshotVolumeNameColumn(tables.Column):
    def get_raw_data(self, snapshot):
        volume = snapshot._volume
        if volume:
            volume_name = volume.name
            volume_name = html.escape(volume_name)
        else:
            volume_name = _("Unknown")
        return safestring.mark_safe(volume_name)

    def get_link_url(self, snapshot):
        volume = snapshot._volume
        if volume:
            volume_id = volume.id
            return reverse(self.link, args=(volume_id,))


class VolumeSnapshotsTable(volume_tables.VolumesTableBase):
    name = tables.Column("name",
                         verbose_name=_("Name"),
                         link="horizon:admin:volumes:snapshots:detail")
    volume_name = SnapshotVolumeNameColumn(
        "name",
        verbose_name=_("Volume Name"),
        link="horizon:admin:volumes:volumes:detail")

    class Meta:
        name = "volume_snapshots"
        verbose_name = _("Volume Snapshots")
        table_actions = (DeleteVolumeSnapshot,)
        row_actions = (CreateVolumeFromSnapshot, LaunchSnapshot,
                       EditVolumeSnapshot, DeleteVolumeSnapshot)
        row_class = UpdateRow
        status_columns = ("status",)
        permissions = ['openstack.services.volume']
