__author__ = 'Zero'

from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.admin.systemlogs import views

VIEW_MOD = 'openstack_dashboard.dashboards.admin.systemlogs.views'

urlpatterns = patterns(VIEW_MOD,
    url(r'^$', views.SystemLogsView.as_view(), name='index'),
    url(r'^logFilter/$', 'filter_view', name='logFilter'),
)
