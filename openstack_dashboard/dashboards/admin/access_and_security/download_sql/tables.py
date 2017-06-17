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

from django.template.defaultfilters import title  # noqa
from django.utils.translation import ugettext_lazy as _

from openstack_auth import utils

from horizon import tables
from openstack_dashboard import api

from openstack_dashboard import policy

class DownloadDB(tables.LinkAction):
    name = "download_sql"
    verbose_name = _("Download vDesk DataBase")
    verbose_name_plural = _("Download vDesk DataBase")
    icon = "download"
    url = "horizon:admin:access_and_security:download_sql:download_db"

    def allowed(self, request, datum=None):
        return True



class DownloadSQLTable(tables.DataTable):

    class Meta(object):
        name = "download_sql"
        verbose_name = _("Download DataBase")
        table_actions = (DownloadDB,)
