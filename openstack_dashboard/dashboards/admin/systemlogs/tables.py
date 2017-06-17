__author__ = 'Zero'

from django.utils.translation import ugettext_lazy as _
from horizon import tables
from django.utils.translation import pgettext_lazy
from django import template
from openstack_dashboard.dashboards.admin.systemlogs import trans
import logging
LOG = logging.getLogger(__name__)

class DownloadLogs(tables.LinkAction):
    name = "Logs"
    verbose_name = _("Download")
    icon = "download"

    def get_link_url(self):
        return "?format=csv"

class LogsFilterAction(tables.FilterAction):
    def filter(self, table, logs, filter_string):
        q = filter_string.lower()
        def comp(tenant):
            if q in logs.name.lower():
                return True
            return False
        return filter(comp, logs)


def get_loginfo(db_log_data):
    template_name = 'admin/systemlogs/_loginfo.html'
    context = {
        "event_subject": db_log_data.event_subject,
        "id": db_log_data.id,
        "event_object": db_log_data.event_object,
        "user_name": db_log_data.user_name,
        "project_name": db_log_data.project_name,
	"time" :db_log_data.event_time,
        "result": db_log_data.result,
	"detail": db_log_data.message
    }
    return template.loader.render_to_string(template_name, context)

class LogsTable(tables.DataTable):
    STATUS_CHOICES = (
        ("createinstance", True),
        ("delete", True),
	)

    event_subject = tables.Column('event_subject', verbose_name=_('Subject'),
				status=True,
                                display_choices=trans.STATUS_DISPLAY_CHOICES)
    event_object = tables.Column(get_loginfo, verbose_name=_('Name'), attrs={'data-type': 'event_object'},)
    user_id = tables.Column('user_name', verbose_name=_('User'),)
    project_id = tables.Column('project_name', verbose_name=_('Tenant'),)
    visit_ip = tables.Column('visit_ip', verbose_name=_('Visit IP'),)
    event_time = tables.Column('event_time', verbose_name=_('Time'),)
    result = tables.Column('result', verbose_name=_('Result'),status=True,
                                display_choices=trans.RESULT_DISPLAY_CHOICES)

    class Meta:
        name = "Logs"
        verbose_name = _("System Logs")
        table_actions = (DownloadLogs, )
        multi_select = False
