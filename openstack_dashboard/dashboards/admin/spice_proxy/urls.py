from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.admin.spice_proxy import views

urlpatterns = patterns('openstack_dashboard.dashboards.admin.spice_proxy.views',
    url(r'^$', views.DisplayView.as_view(), name='index'),
    url(r'^(?P<id>[^/]+)/update/$', views.ProxyPatternView.as_view(), name='update'),
    url(r'^(?P<id>[^/]+)/modifyport/$', views.ModifyPortView.as_view(), name='modifyport'))
