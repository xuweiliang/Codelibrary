# Copyright 2012,  Nachi Ueno,  NTT MCL,  Inc.
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

from django.conf.urls import url

from openstack_dashboard.dashboards.admin.routers.extensions.extraroutes\
    import views as er_views
from openstack_dashboard.dashboards.admin.routers.ports \
    import views as port_views
from openstack_dashboard.dashboards.admin.routers import views


ROUTER_URL = r'^(?P<router_id>[^/]+)/%s'


urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^create/$', views.CreateView.as_view(), name='create'),
    url(ROUTER_URL % '$',
        views.DetailView.as_view(),
        name='detail'),
    url(ROUTER_URL % 'update',
        views.UpdateView.as_view(),
        name='update'),
    url(ROUTER_URL % 'addinterface',
        port_views.AddInterfaceView.as_view(),
        name='addinterface'),
    url(ROUTER_URL % 'addrouterroute',
        er_views.AddRouterRouteView.as_view(),
        name='addrouterroute'),
    url(ROUTER_URL % 'setgateway',
        port_views.SetGatewayView.as_view(),
        name='setgateway'),
]
