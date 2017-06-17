from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tabs
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tabs
from openstack_dashboard import api
from openstack_dashboard.dashboards.admin.aggregates.compute \
    import tabs as cmp_tabs
from openstack_dashboard.dashboards.admin.aggregates import tables

class AggregatesTab(tabs.TableTab):
    table_classes = (tables.HostAggregatesTable,)
    name = _("Host Aggregates")
    slug = "aggregates_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def get_host_aggregates_data(self):
        request = self.request
        aggregates = []
        try:
            aggregates = api.nova.aggregate_details_list(self.request)
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve host aggregates list.'))
        aggregates.sort(key=lambda aggregate: aggregate.name.lower())
        return aggregates

class AvailabilitysTab(tabs.TableTab):
    table_classes = (tables.AvailabilityZonesTable,)
    name = _("Availability Zones")
    slug = "availabilitys_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = False

    def get_availability_zones_data(self):
        request = self.request
        availability_zones = []
        try:
            availability_zones = \
                api.nova.availability_zone_list(self.request, detailed=True)
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve availability zone list.'))
        availability_zones.sort(key=lambda az: az.zoneName.lower())
        return availability_zones

class TabGroups(tabs.TabGroup):
    slug = "tab_groups"
    tabs = (AggregatesTab, AvailabilitysTab, cmp_tabs.ComputeHostTab)
    sticky = True

