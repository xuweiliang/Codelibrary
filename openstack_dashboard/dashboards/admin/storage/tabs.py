from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from openstack_dashboard import api
from oslo_log import log as logging
from openstack_dashboard.dashboards.admin.storage.storage\
    import tables as storage_tables

LOG = logging.getLogger(__name__)

class StorageTab(tabs.TableTab):
    table_classes = (storage_tables.StorageTable,)
    name = _("Add Local Storage")
    slug = "storage_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = True

    def get_storage_data(self):
        storage = api.storage.storage_list(self.request)
        return storage

class TabGroups(tabs.TabGroup):
    slug = "tab_groups"
    tabs = (StorageTab,)
    sticky = True

