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

from django.conf.urls import url

from openstack_dashboard.dashboards.admin.projects import views


urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^create$', views.CreateProjectView.as_view(), name='create'),
    url(r'^(?P<tenant_id>[^/]+)/update/$',
        views.UpdateProjectView.as_view(), name='update'),
    url(r'^(?P<project_id>[^/]+)/belongs/$',
        views.BelongsInstanceView.as_view(), name='belongs'),
    url(r'^(?P<project_id>[^/]+)/usage/$',
        views.ProjectUsageView.as_view(), name='usage'),
    url(r'^(?P<tenant_id>[^/]+)/dedicated_binding$',
        views.DedicatedBindingView.as_view(), name='binding'),
    url(r'^(?P<tenant_id>[^/]+)/float_binding$',
        views.FloatBindingView.as_view(), name='binding'),
        #views.DedicatedBindingView.as_view(), name='dedicated_binding'),
    url(r'^(?P<tenant_id>[^/]+)/check_instances/$', 
        views.CheckDedicatedInstanceView.as_view(), name='check_instance'),
    url(r'^(?P<tenant_id>[^/]+)/batch_binding/$', 
        views.BatchBindingInstanceView.as_view(), name='batch_binding'),
    url(r'^(?P<tenant_id>[^/]+)/add_instance/$', 
        views.UserAddInstanceView.as_view(), name='add_instance'),
    url(r'^(?P<tenant_id>[^/]+)/instance_ajax/$', 
        views.SelectInstanceView.as_view(), name='instance_ajax'),
    url(r'^(?P<tenant_id>[^/]+)/user_remove/$', 
        views.UserRemoveInstanceView.as_view(), name='user_remove'),
    url(r'^(?P<tenant_id>[^/]+)/remove_all/$', 
        views.RemoveAllInstanceView.as_view(), name='remove_all'),
    url(r'^(?P<tenant_id>[^/]+)/check_instances_float/$', 
        views.CheckFloatInstanceView.as_view(), name='check_instances_float'),
    url(r'^(?P<tenant_id>[^/]+)/pool_ajax/$', 
        views.PoolAjaxView.as_view(), name='pool_ajax'),
    url(r'^(?P<tenant_id>[^/]+)/pool_add_instance/$', 
        views.PoolAddInstanceView.as_view(), name='pool_add_instance'),
    url(r'^(?P<tenant_id>[^/]+)/pool_remove_instance/$', 
        views.PoolRemoveInstanceView.as_view(), name='pool_remove_instance'),
    url(r'^(?P<tenant_id>[^/]+)/pool_bindvm_ajax/$', 
        views.PoolBindvmAjaxView.as_view(), name='pool_bindvm_ajax'),
    url(r'^(?P<tenant_id>[^/]+)/pool_remove_ajax/$', 
        views.PoolRemoveAjaxView.as_view(), name='pool_remove_ajax'),
    url(r'^(?P<project_id>[^/]+)/detail/$',
        views.DetailProjectView.as_view(), name='detail'),
]
