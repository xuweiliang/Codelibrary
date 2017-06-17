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


from django.utils.translation import ugettext_lazy as _

from horizon import tables


class CreateStorage(tables.LinkAction):
    name = "create"
    verbose_name = _("Add Local Storage")
    url = "horizon:admin:storage:storage:create"
    classes = ("ajax-modal",)
    icon = "plus"

class ClearLocalStorage(tables.LinkAction):
    name = 'clear'
    verbose_name = _("Clear Local Storage")
    url = "horizon:admin:storage:storage:clearstorage"
    classes = ("ajax-modal",)


class StorageTable(tables.DataTable):
    STATUS_CHOICES = (
        ("active", True),
        ("saving", None),
        ("queued", None),
        ("pending_delete", None),
        ("killed", False),
        ("deleted", False),
    )
    name = tables.Column("storage_name",
                         verbose_name=_("Host Name"))

    storage_type = tables.Column("storage_type",
                         verbose_name=_("Storage Type"))

    status = tables.Column("accelerate_status",
                           classes=["storage_css"],
                           verbose_name=_("Boot cache acceleration"))

    path = tables.Column("mount_path",
                         verbose_name=_("Mount Path"))

    accelerate = tables.Column("accelerate_disk",
                         verbose_name=_("SSD Accelerate Disk"))

    memor_chache = tables.Column("memory_cache",
                         verbose_name=_("Memory Cache"))

    data_disk = tables.Column("data_disk",
                         verbose_name=_("Data Disk"))

    class Meta:
        name = "storage"
        verbose_name = _("Storage")
        table_actions = (CreateStorage, ClearLocalStorage )

