# Copyright 2013 NTT Innovation Institute Inc.
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


from django.utils.translation import ugettext_lazy as _

from openstack_dashboard.dashboards.admin.routers.ports import tables


class RemoveInterface(tables.RemoveInterface):
    failure_url = 'horizon:admin:network_topology:router'


class PortsTable(tables.PortsTable):
    class Meta(object):
        name = "interfaces"
        verbose_name = _("Interfaces")
        row_actions = (RemoveInterface, )