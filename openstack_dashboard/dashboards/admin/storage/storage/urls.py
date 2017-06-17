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

from openstack_dashboard.dashboards.admin.storage.storage import views


VIEWS_MOD = 'openstack_dashboard.dashboards.admin.storage.storage.views'


urlpatterns = patterns(VIEWS_MOD,
    url(r'^create/$', views.CreateView.as_view(), name='create'),
    url(r'^clearstorage/$', views.ClearStorageView.as_view(), name='clearstorage'),
    url(r'^select_disk/$', 'select_disk', name='select_disk'),
    url(r'^select_zfs_pools/$', 'select_zfs_pools', name='select_zfs_pools'),
    url(r'^storage_status/$', 'storage_status', name='storage_status'),
    url(r'^cache_partition/$', 'cache_partition', name='cache_partition'),
)
