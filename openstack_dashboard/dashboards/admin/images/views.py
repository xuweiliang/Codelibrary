from horizon import tabs
from openstack_dashboard.dashboards.admin.images \
import tabs as project_tabs
class IndexView(tabs.TabbedTableView):
    tab_group_class = project_tabs.TabGroups
    template_name = 'admin/images/index.html'

