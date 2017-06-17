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
Views for managing volumes.
"""
import json
import re

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard import api
from openstack_dashboard.api import cinder
from openstack_dashboard.usage import quotas

from openstack_dashboard.dashboards.admin.volumes \
    .volumes import forms as project_forms
from openstack_dashboard.dashboards.admin.volumes \
    .volumes import tables as project_tables
from openstack_dashboard.dashboards.admin.volumes \
    .volumes import tabs as project_tabs


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.VolumeDetailTabs
    template_name = 'admin/volumes/volumes/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        volume = self.get_data()
        table = project_tables.VolumesTable(self.request)
        context["volume"] = volume
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(volume)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)
            for att in volume.attachments:
                att['instance'] = api.nova.server_get(self.request,
                                                      att['server_id'])
        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=redirect)
        return volume

    def get_redirect_url(self):
        return reverse('horizon:admin:volumes:index')

    def get_tabs(self, request, *args, **kwargs):
        volume = self.get_data()
        return self.tab_group_class(request, volume=volume, **kwargs)


class CreateView(forms.ModalFormView):
    form_class = project_forms.CreateForm
    template_name = 'admin/volumes/volumes/create.html'
    success_url = reverse_lazy('horizon:admin:volumes:volumes_tab')

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)
        try:
            context['usages'] = quotas.tenant_limit_usages(self.request)
        except Exception:
            exceptions.handle(self.request)
        return context

class IncreaseVolumeView(forms.ModalFormView):
    form_class = project_forms.IncreaseForm
    template_name = 'admin/volumes/volumes/increase.html'
    success_url = reverse_lazy('horizon:admin:volumes:index')

    def get_object(self):
        #try:
        endpoints = api.base.url_for(self.request, 'volume')
        expression = r'https?://(.+?):.+?'
        host = re.match(expression,endpoints).groups()
        cloud_size = api.device.get_colud_disk_size(self.request, host=host)
        loads_data = json.loads(cloud_size.text)
        content = eval(loads_data.get('content'))
        volumes = filter(lambda x: x["vg_tags"] == "cinder_volume", content)
        if volumes:
            volumes = volumes.pop()
            vg_size = re.findall(r"[a-zA-Z]{1}", volumes['vg_size'])
            return volumes['vg_size'][:-len(vg_size)]
        #except Exception:
        #    exceptions.handle(self.request, _("Unable request the size of current volume group."))

    def get_context_data(self, **kwargs):
        context = super(IncreaseVolumeView, self).get_context_data(**kwargs)
        context['usages'] = quotas.tenant_limit_usages(self.request)
        return context


    def get_initial(self):
        orig_size = self.get_object()
        return {'orig_size': orig_size}

class ExtendView(forms.ModalFormView):
    form_class = project_forms.ExtendForm
    template_name = 'admin/volumes/volumes/extend.html'
    success_url = reverse_lazy("horizon:admin:volumes:index")

    def get_object(self):
        if not hasattr(self, "_object"):
            volume_id = self.kwargs['volume_id']
            try:
                self._object = cinder.volume_get(self.request, volume_id)
            except Exception:
                self._object = None
                exceptions.handle(self.request,
                                  _('Unable to retrieve volume information.'))
        return self._object

    def get_context_data(self, **kwargs):
        context = super(ExtendView, self).get_context_data(**kwargs)
        context['volume'] = self.get_object()
        try:
            usages = quotas.tenant_limit_usages(self.request)
            usages['gigabytesUsed'] = (usages['gigabytesUsed']
                                       - context['volume'].size)
            context['usages'] = usages
        except Exception:
            exceptions.handle(self.request)
        return context

    def get_initial(self):
        volume = self.get_object()
        return {'id': self.kwargs['volume_id'],
                'name': volume.name,
                'orig_size': volume.size}


class CreateSnapshotView(forms.ModalFormView):
    form_class = project_forms.CreateSnapshotForm
    template_name = 'admin/volumes/volumes/create_snapshot.html'
    success_url = reverse_lazy('horizon:admin:volumes:snapshots_tab')

    def get_context_data(self, **kwargs):
        context = super(CreateSnapshotView, self).get_context_data(**kwargs)
        context['volume_id'] = self.kwargs['volume_id']
        try:
            volume = cinder.volume_get(self.request, context['volume_id'])
            if (volume.status == 'in-use'):
                context['attached'] = True
                context['form'].set_warning(_("This volume is currently "
                                              "attached to an instance. "
                                              "In some cases, creating a "
                                              "snapshot from an attached "
                                              "volume can result in a "
                                              "corrupted snapshot."))
            context['usages'] = quotas.tenant_limit_usages(self.request)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve volume information.'))
        return context

    def get_initial(self):
        return {'volume_id': self.kwargs["volume_id"]}


class UploadToImageView(forms.ModalFormView):
    form_class = project_forms.UploadToImageForm
    template_name = 'admin/volumes/volumes/upload_to_image.html'
    success_url = reverse_lazy("horizon:admin:volumes:index")

    @memoized.memoized_method
    def get_data(self):
        try:
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)
        except Exception:
            error_message = _(
                'Unable to retrieve volume information for volume: "%s"') \
                % volume_id
            exceptions.handle(self.request,
                              error_message,
                              redirect=self.success_url)

        return volume

    def get_context_data(self, **kwargs):
        context = super(UploadToImageView, self).get_context_data(**kwargs)
        context['volume'] = self.get_data()

        return context

    def get_initial(self):
        volume = self.get_data()

        return {'id': self.kwargs['volume_id'],
                'name': volume.name,
                'status': volume.status}


class UpdateView(forms.ModalFormView):
    form_class = project_forms.UpdateForm
    template_name = 'admin/volumes/volumes/update.html'
    success_url = reverse_lazy("horizon:admin:volumes:index")

    def get_object(self):
        if not hasattr(self, "_object"):
            vol_id = self.kwargs['volume_id']
            try:
                self._object = cinder.volume_get(self.request, vol_id)
            except Exception:
                msg = _('Unable to retrieve volume.')
                url = reverse('horizon:admin:volumes:index')
                exceptions.handle(self.request, msg, redirect=url)
        return self._object

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['volume'] = self.get_object()
        return context

    def get_initial(self):
        volume = self.get_object()
        return {'volume_id': self.kwargs["volume_id"],
                'name': volume.name,
                'description': volume.description}


class EditAttachmentsView(tables.DataTableView, forms.ModalFormView):
    table_class = project_tables.AttachmentsTable
    form_class = project_forms.AttachForm
    template_name = 'admin/volumes/volumes/attach.html'
    success_url = reverse_lazy("horizon:admin:volumes:index")

    @memoized.memoized_method
    def get_object(self):
        volume_id = self.kwargs['volume_id']
        try:
            return cinder.volume_get(self.request, volume_id)
        except Exception:
            self._object = None
            exceptions.handle(self.request,
                              _('Unable to retrieve volume information.'))

    def get_data(self):
        attachments = []
        volume = self.get_object()
        instance = self.get_initial()
        
        if volume is not None and instance is not None:
	    for ins in instance['instances']:
                for att in volume.attachments:
                    if att['server_id'] == ins.id and att['instance_name'] == ins.name:
                        att['volume_name'] = getattr(volume, 'name', att['device'])
                        att['status'] = ins.status
                        attachments.append(att)
 
        return attachments

    def get_initial(self):
        try:
            instances, has_more = api.nova.server_list(self.request)
        except Exception:
            instances = []
            exceptions.handle(self.request,
                              _("Unable to retrieve attachment information."))
        return {'volume': self.get_object(),
                'instances': instances}

    @memoized.memoized_method
    def get_form(self):
        form_class = self.get_form_class()
        return super(EditAttachmentsView, self).get_form(form_class)

    def get_context_data(self, **kwargs):
        context = super(EditAttachmentsView, self).get_context_data(**kwargs)
        context['form'] = self.get_form()
        volume = self.get_object()
        if volume and volume.status == 'available':
            context['show_attach'] = True
            del context['table']
        else:
            context['show_attach'] = False
        context['volume'] = volume
        if self.request.is_ajax():
            context['hide'] = True
        return context

    def get(self, request, *args, **kwargs):
        # Table action handling
        handled = self.construct_tables()
        if handled:
            return handled
        return self.render_to_response(self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.get(request, *args, **kwargs)


class RetypeView(forms.ModalFormView):
    form_class = project_forms.RetypeForm
    template_name = 'admin/volumes/volumes/retype.html'
    success_url = reverse_lazy("horizon:admin:volumes:index")

    @memoized.memoized_method
    def get_data(self):
        try:
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)
        except Exception:
            error_message = _(
                'Unable to retrieve volume information for volume: "%s"') \
                % volume_id
            exceptions.handle(self.request,
                              error_message,
                              redirect=self.success_url)

        return volume

    def get_context_data(self, **kwargs):
        context = super(RetypeView, self).get_context_data(**kwargs)
        context['volume'] = self.get_data()

        return context

    def get_initial(self):
        volume = self.get_data()

        return {'id': self.kwargs['volume_id'],
                'name': volume.name,
                'volume_type': volume.volume_type}

class UpdateStatusView(forms.ModalFormView):
    form_class = project_forms.UpdateStatus
    template_name = 'admin/volumes/volumes/update_status.html'
    success_url = reverse_lazy('horizon:admin:volumes:index')

    def get_context_data(self, **kwargs):
        context = super(UpdateStatusView, self).get_context_data(**kwargs)
        context["volume_id"] = self.kwargs['volume_id']
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            volume_id = self.kwargs['volume_id']
            volume = cinder.volume_get(self.request, volume_id)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve volume details.'),
                              redirect=self.success_url)
        return volume

    def get_initial(self):
        volume = self.get_data()
        return {'volume_id': self.kwargs["volume_id"],
                'status': volume.status}

