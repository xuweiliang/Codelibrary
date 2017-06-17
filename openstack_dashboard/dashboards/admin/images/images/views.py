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

"""
Views for managing images.
"""
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard import api

from openstack_dashboard.dashboards.admin.images.images \
    import forms as project_forms
from openstack_dashboard.dashboards.admin.images.images \
    import tables as project_tables
from openstack_dashboard.dashboards.admin.images.images \
    import tabs as project_tabs

from django.http import HttpResponse
import json
class CreateView(forms.ModalFormView):
    form_class = project_forms.CreateImageForm
    template_name = 'admin/images/images/create.html'
    context_object_name = 'image'
    success_url = reverse_lazy("horizon:admin:images:index")

class UploadView(forms.ModalFormView):
    form_class = project_forms.UploadFileForm
    template_name = 'admin/images/images/upload.html'
    success_url = reverse_lazy("horizon:admin:images:index")

class UpdateView(forms.ModalFormView):
    form_class = project_forms.UpdateImageForm
    template_name = 'admin/images/images/update.html'
    success_url = reverse_lazy("horizon:admin:images:index")

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.glance.image_get(self.request, self.kwargs['image_id'])
        except Exception:
            msg = _('Unable to retrieve image.')
            url = reverse('horizon:admin:images:index')
            exceptions.handle(self.request, msg, redirect=url)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['image'] = self.get_object()
        return context

    def get_initial(self):
        image = self.get_object()
        properties = getattr(image, 'properties', {})
        return {'image_id': self.kwargs['image_id'],
                'name': getattr(image, 'name', None) or image.id,
                'description': properties.get('description', ''),
                'kernel': properties.get('kernel_id', ''),
                'ramdisk': properties.get('ramdisk_id', ''),
                'architecture': properties.get('architecture', ''),
                'disk_format': getattr(image, 'disk_format', None),
                'minimum_ram': getattr(image, 'min_ram', None),
                'minimum_disk': getattr(image, 'min_disk', None),
                'public': getattr(image, 'is_public', None),
                'protected': getattr(image, 'protected', None)}


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.ImageDetailTabs
    template_name = 'admin/images/images/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        image = self.get_data()
	
	if getattr(image, "properties", {}).get("image_type", '') == 'snapshot':
            table = project_tables.TemplatesTable(self.request)
	else:
	    table = project_tables.ImagesTable(self.request)
        context["image"] = image
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(image)
	return context

    @staticmethod
    def get_redirect_url():
        return reverse_lazy('horizon:admin:images:index')

    @memoized.memoized_method
    def get_data(self):
        try:
	    return api.glance.image_get(self.request, self.kwargs['image_id'])
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve image details.'),
                              redirect=self.get_redirect_url())

    def get_tabs(self, request, *args, **kwargs):
        image = self.get_data()
        return self.tab_group_class(request, image=image, **kwargs)

def download_image(request):
    try: 
        data = request.GET['data']
        data_loads = json.loads(data)
        image_id = data_loads[0]
        encode_name = data_loads[1].encode('UTF-8')
        encode_format = data_loads[2].encode('UTF-8')
        filename = '.'.join([encode_name, encode_format])
        #data_loads = json.loads(data)
        body = api.glance.download_image(request, image_id, True)
        #response = HttpResponse(body,mimetype='application/octet-stream')
        response = HttpResponse(body,content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
    except Exception:
        url = reverse('horizon:admin:images:index')
        msg = _('Unable to retrieve image.')
        exceptions.handle(request, msg, redirect=url)
    return response

class DownloadImageView(forms.ModalFormView):
    form_class = project_forms.DownloadImageForm
    template_name = 'admin/images/images/download.html'
    success_url = reverse_lazy("horizon:admin:images:index")


    @memoized.memoized_method
    def get_object(self):
        try:
            return api.glance.image_get(self.request, self.kwargs['image_id'])
        except Exception:
            msg = _('Unable to retrieve image.')
            url = reverse('horizon:admin:images:index')
            exceptions.handle(self.request, msg, redirect=url)


    def get_context_data(self, **kwargs):
        context = super(DownloadImageView, self).get_context_data(**kwargs)
        context['image'] = self.get_object()
        return context

    def get_initial(self):
        image = self.get_object()
        return {'image':image}
