# Copyright 2013 Nebula, Inc.
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
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs
from horizon.utils import functions as utils
from openstack_dashboard import api
from openstack_dashboard.api import keystone
from openstack_dashboard.api import cinder
from openstack_dashboard.dashboards.admin.volumes.backups \
    import tables as backups_tables
from openstack_dashboard.dashboards.admin.volumes.snapshots \
    import tables as vol_snapshot_tables
from openstack_dashboard.dashboards.admin.volumes.volumes \
    import tables as volume_tables
from openstack_dashboard.dashboards.admin.volumes.volume_types \
    import tables as volume_types_tables

LOG = logging.getLogger(__name__)

class VolumeTableMixIn(object):

    def page_size(self, request):
        page_size = utils.get_page_size(request)
        return page_size

    def _get_pagination_param(self, _tables):
        self._more = False
        self._prev = False
        prev_marker = self.request.GET.get(
            _tables.VolumesTable._meta.prev_pagination_param, None)
        marker = self.request.GET.get(
            _tables.VolumesTable._meta.pagination_param, None)
        if prev_marker:
            paginate=int(str(prev_marker).split('=')[1])
            prev_marker=str(prev_marker).split('&')[0].decode()
        if marker:
            paginate=int(str(marker).split('=')[1])
            marker=str(marker).split('&')[0].decode()
        return prev_marker, marker


    def _get_volumes_pagedata(self, volume_list,
                              page_size, prev_marker, marker):
        id_index =[v.id for v in volume_list]
        has_more = False
        has_prev = False
        if marker and marker in id_index:
            index = int(id_index.index(marker))+1
            size = int(index + page_size)
            volumes_data = volume_list[index : size]
            has_prev = True
            if len(volume_list) != size:
                if len(volumes_data) < page_size:
                    has_more = False
                else:
                    has_more = True
            return has_more, has_prev, volumes_data
        elif prev_marker and prev_marker in id_index:
            index = int(id_index.index(prev_marker))
            size = int(index - page_size)
            if size != 0:
                has_prev = True
            has_more = True
            return has_more, has_prev, volume_list[size : index]
        elif marker is None and prev_marker is None:
            index = 0
            size = page_size
            has_more = True
            if len(volume_list) <= page_size:
                has_more = False
            return has_more, has_prev, volume_list[index : size]

    def _get_volumes(self, search_opts=None):
        try:
            return api.cinder.volume_list(self.request,
                                          search_opts=search_opts)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve volume list.'))
            return []

    def _get_instances(self, search_opts=None):
        try:
            instances, has_more = api.nova.server_list(self.request,
                                                       search_opts=search_opts)
            return instances
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve volume/instance "
                                "attachment information"))
            return []

    def _set_attachments_string(self, volumes, instances):
        instances = SortedDict([(inst.id, inst) for inst in instances])
        for volume in volumes:
            for att in volume.attachments:
                server_id = att.get('server_id', None)
                att['instance'] = instances.get(server_id, None)


class VolumeTab(tabs.TableTab, VolumeTableMixIn):
    table_classes = (volume_tables.VolumesTable,)
    name = _("Volumes")
    slug = "volumes_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def has_more_data(self, table):
        return self._more

    def has_prev_data(self, table):
        return self._prev

    def get_volumes_total(self):
        self._prev = False
        volumes = self._get_volumes()
        instances = self._get_instances()
        self._set_attachments_string(volumes, instances)

        try:
            tenants, has_more = keystone.tenant_list(self.request)
        except Exception:
            tenants = []
            msg = _('Unable to retrieve volume project information.')
            exceptions.handle(self.request, msg)

        tenant_dict = SortedDict([(t.id, t) for t in tenants])
        for volume in volumes:
            tenant_id = getattr(volume, "os-vol-tenant-attr:tenant_id", None)
            tenant = tenant_dict.get(tenant_id, None)
            volume.tenant_name = getattr(tenant, "name", None)

        return volumes

    def get_volumes_data(self):
        try:
            prev_marker, marker = self._get_pagination_param(volume_tables)
            page_size = self.page_size(self.request)
            volume_list = self.get_volumes_total()
            self._more, self._prev, volumes = self._get_volumes_pagedata(volume_list, page_size,
                                                  prev_marker, marker)
            return volumes
        except:
            self._more = False
            self._prev = False
            return []

class SnapshotTab(tabs.TableTab):
    table_classes = (vol_snapshot_tables.VolumeSnapshotsTable,)
    name = _("Volume Snapshots")
    slug = "snapshots_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def get_volume_snapshots_data(self):
        if api.base.is_service_enabled(self.request, 'volume'):
            try:
                snapshots = cinder.volume_snapshot_list(self.request,)
                volumes = cinder.volume_list(self.request,)
                volumes = dict((v.id, v) for v in volumes)
            except Exception:
                snapshots = []
                volumes = {}
                exceptions.handle(self.request, _("Unable to retrieve "
                                                  "volume snapshots."))

            try:
                tenants, has_more = keystone.tenant_list(self.request)
            except Exception:
                tenants = []
                msg = _('Unable to retrieve volume project information.')
                exceptions.handle(self.request, msg)

            tenant_dict = dict([(t.id, t) for t in tenants])
            for snapshot in snapshots:
                volume = volumes.get(snapshot.volume_id)
                tenant_id = getattr(volume,
                    'os-vol-tenant-attr:tenant_id', None)
                tenant = tenant_dict.get(tenant_id, None)
                snapshot._volume = volume
                snapshot.tenant_name = getattr(tenant, "name", None)
                snapshot.host_name = getattr(
                    volume, 'os-vol-host-attr:host', None)

        else:
            snapshots = []
        return snapshots


class BackupsTab(tabs.TableTab, VolumeTableMixIn):
    table_classes = (backups_tables.BackupsTable,)
    name = _("Volume Backups")
    slug = "backups_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def allowed(self, request):
        return api.cinder.volume_backup_supported(self.request)

    def get_volume_backups_data(self):
        try:
            backups = api.cinder.volume_backup_list(self.request)
            volumes = api.cinder.volume_list(self.request)
            volumes = dict((v.id, v) for v in volumes)
            for backup in backups:
                backup.volume = volumes.get(backup.volume_id)
        except Exception:
            backups = []
            exceptions.handle(self.request, _("Unable to retrieve "
                                              "volume backups."))
        return backups

class VolumeTypesTab(tabs.TableTab, VolumeTableMixIn):
    table_classes = (volume_types_tables.VolumeTypesTable,
                     volume_types_tables.QosSpecsTable)
    name = _("Volume Types")
    slug = "volume_types_tab"
    template_name = "admin/volumes/volume_types/volume_types_tables.html"
    preload = False

    def get_volume_types_data(self):
        try:
            volume_types = \
                cinder.volume_type_list_with_qos_associations(self.request)
        except Exception:
            volume_types = []
            exceptions.handle(self.request,
                              _("Unable to retrieve volume types"))

        return volume_types

    def get_qos_specs_data(self):
        try:
            qos_specs = cinder.qos_spec_list(self.request)
        except Exception:
            qos_specs = []
            exceptions.handle(self.request,
                              _("Unable to retrieve QOS specs"))
        return qos_specs



class VolumeAndSnapshotTabs(tabs.TabGroup):
    slug = "volumes_and_snapshots"
    #tabs = (VolumeTab, SnapshotTab, BackupsTab, VolumeTypesTab)
    tabs = (VolumeTab, SnapshotTab, BackupsTab)
    sticky = True
