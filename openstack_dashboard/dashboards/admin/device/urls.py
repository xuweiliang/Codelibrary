# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
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

from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.admin.device import views


DEVICE_ID = r'^(?P<id>[^/]+)/%s$'
INSTANCES_KEYPAIR = r'^(?P<device_id>[^/]+)/(?P<keypair_name>[^/]+)/%s$'
VIEW_MOD = 'openstack_dashboard.dashboards.admin.device.views'


urlpatterns = patterns(VIEW_MOD,
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(DEVICE_ID % 'update', views.UpdateView.as_view(), name='update'),
    url(DEVICE_ID % 'message', views.SendMessageView.as_view(), name='message'),
#    url(DEVICE_ID % 'allreboot', views.AllRebootView.as_view(), name='allreboot'),
#    url(r'allreboot$', views.AllRebootView.as_view(), name='allreboot'),
#    url(r'allreboot$', 'all_reboot', name='allreboot'),
    url(r'ajax_status$', 'ajax_status_view', name='status'),
    url(r'check_ipaddr$', 'check_ipaddr_view', name='check_ipaddr'),
)
