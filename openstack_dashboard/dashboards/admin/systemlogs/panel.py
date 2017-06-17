__author__ = 'Zero'

from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.admin import dashboard


class SystemLogsPanel(horizon.Panel):
    name = _("System Logs")
    slug = 'systemlogs'

#dashboard.Admin.register(SystemLogsPanel)
