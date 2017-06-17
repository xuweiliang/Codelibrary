__author__ = 'Zero'

from horizon import tables
from openstack_dashboard.dashboards.admin.systemlogs \
    import tables as project_tables
from openstack_dashboard import api
from horizon import exceptions
from django.utils.translation import ugettext_lazy as _
from horizon.utils import functions as utils
import json
from django import http 
from horizon.utils import csvbase
from openstack_dashboard.dashboards.admin.systemlogs import trans
import logging 
LOG = logging.getLogger(__name__)

NOVA_USER_LIST = ['glance', 'cinder', 'neutron', 'nova', 'AdminShadow']

class LogCsvRender(csvbase.BaseCsvResponse):

    columns = [_("Subject"), _("Name"), _("User"),
               _("Tenant"), _("Visit IP"), _("Create Time"),
               _("Result"), _("Details")]

    def get_row_data(self):
        for log in self.context['logs']:
            display_value = [display for (value, display) in
                                trans.STATUS_DISPLAY_CHOICES
                                if value.lower() == log.event_subject.lower()]

            result_value = [display for (value, display) in
                                trans.RESULT_DISPLAY_CHOICES
                                if value.lower() == log.result.lower()]

            if list(display_value):
                display_name = display_value[0]
            else:
                display_name = log.event_subject

            if log.user_name == "AdminShadow":
                log.user_name = "admin"

            yield (display_name,
                   log.event_object,
                   log.user_name,
                   log.project_name,
                   log.visit_ip,
                   log.event_time,
                   result_value[0],
                   log.message)

class SystemLogsView(tables.DataTableView):
    table_class = project_tables.LogsTable
    template_name = 'admin/systemlogs/index.html'
    logs_response_class = LogCsvRender
    csv_template_name = 'admin/systemlogs/logs.csv'

    def has_more_data(self, table):
        return self._more

    def has_prev_data(self, table):
        return self._prev

    def page_index(self, table):
        return self.page

#    def skip_page(self, table):
#	return self._pages

    def get_data(self):
        db_log_data = []
        self._more = False
        self._prev = False
        self._pages = False
        self.page = 1
        try:
            filters_data = self.request.GET.get('filter_val',None)
            parent_data = self.request.GET.get('parent_val',None)
            if filters_data and parent_data:
                filters = filters_data + "-"+ parent_data
            else:
                filters = None
            self.logsinfo = api.nova.systemlogs_list(self.request, filters)
            for log in self.logsinfo:
                LOG.info("log ==============================%s" % log)
                if log.user_name == "AdminShadow":
                    log.user_name = "admin"
        except Exception:
            db_log_data = []
            self._more = False
            self._prev = False
            exceptions.handle(self.request,
                              _('Unable to show logs list.'))

        return self.logsinfo
    def get_context_data(self, **kwargs):
        context = super(SystemLogsView, self).get_context_data(**kwargs)
        context['logs'] = self.logsinfo or None
        return context

    def get_template_names(self):
        if self.request.GET.get('format', 'html') == 'csv':
            return self.csv_template_name
        return self.template_name

    def get_content_type(self):
        if self.request.GET.get('format', 'html') == 'csv':
            return "text/csv"
        return "text/html"

    def render_to_response(self, context):
        if self.request.GET.get('format', 'html') == 'csv':
            render_class = self.logs_response_class
        else:
            render_class = self.response_class
        resp = render_class(request=self.request,
                            template=self.get_template_names(),
                            context=context,
                            content_type=self.get_content_type())
        return resp 

def filter_view(request):
    user_list=[]
    tenant_list=[]
    visit_ip_data=[]
    success=[]
    try:
	visit_ip = api.nova.systemlogs_list(request)
	for ip in visit_ip:
	    visit_ip_data.append(ip.visit_ip)
            if ip.user_name != "AdminShadow":
                user_list.append(ip.user_name)
	    user_list.append(ip.user_name)
	    tenant_list.append(ip.project_name) 
        success.append(list(set(user_list)))
	success.append(list(set(tenant_list)))
	success.append(list(set(visit_ip_data)))
    except Exception:
        tenants = []
        msg = _('Unable to retrieve instance project information.')
        exceptions.handle(request, msg)
    data =  request.GET['callback']+'({"success":'+json.dumps(success)+ '})'
    response = http.HttpResponse(content_type='text/plain')
    response.write(data)
    response.flush()
    return response
 
