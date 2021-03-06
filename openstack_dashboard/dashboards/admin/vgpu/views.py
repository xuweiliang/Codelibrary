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
Views for managing instances.
"""
import logging
from datetime import datetime
from collections import OrderedDict
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django import http
from django import shortcuts
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.utils.datastructures import SortedDict

from horizon.utils import functions as utils
from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import tables
from horizon import tabs
from horizon.utils import memoized
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.utils import filters

from openstack_dashboard.dashboards.admin.instances \
    import console as project_console
from openstack_dashboard.dashboards.admin.instances \
    import forms as project_forms
from openstack_dashboard.dashboards.admin.instances \
    import tables as project_tables
from openstack_dashboard.dashboards.admin.instances \
    import tabs as project_tabs
from openstack_dashboard.dashboards.admin.instances \
    import workflows as project_workflows

LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = project_tables.InstancesTable
    template_name = 'admin/vgpu/index.html'
    page_title = _("Instances")


    def has_more_data(self, table):
        return self._more

    def has_prve_data(self, table):
        return self._prev

    def get_data(self):
        marker = self.request.GET.get(
            project_tables.InstancesTable._meta.pagination_param, None)
        prev_marker = self.request.GET.get(
            project_tables.InstancesTable._meta.prev_pagination_param, None)
        page = self.request.GET.get("page", 1)
        search_opts = self.get_filters({'marker': marker, 'paginate': True})
        # Gather our instances
        try:
            instances, self._more, self._prev= api.nova.server_vgpu(
                    self.request,
                    search_opts=search_opts)
        except Exception:
            self._more = False
            instances = []
            exceptions.handle(self.request,
                              _('Unable to retrieve instances.'))

       
        if instances:
            try:
                api.network.servers_update_addresses(self.request, instances, all_tenants=True)
            except Exception:
                exceptions.handle(
                    self.request,
                    message=_('Unable to retrieve IP addresses from Neutron.'),
                    ignore=True)

            # Gather our flavors and images and correlate our instances to them
            try:
                flavors = api.nova.flavor_list(self.request)
            except Exception:
                flavors = []
                exceptions.handle(self.request, ignore=True)

            try:
                # TODO(gabriel): Handle pagination.
                images, more, prev = api.glance.image_list_detailed(
                    self.request)
            except Exception:
                images = []
                exceptions.handle(self.request, ignore=True)

            try:
                tenants, has_more = api.keystone.tenant_list(self.request)
                users = api.keystone.user_list(self.request)
            except Exception:
                tenants = []
                msg = _('Unable to retrieve instance project information.')
                exceptions.handle(self.request, msg)


            tenant_dict = OrderedDict([(t.id, t) for t in tenants])
            user_dict = OrderedDict([(t.id, t) for t in users])
            full_flavors = OrderedDict([(str(flavor.id), flavor)
                                       for flavor in flavors])
            image_map = OrderedDict([(str(image.id), image)
                                    for image in images])

            # Loop through instances to get flavor info.
            for instance in instances:
                if hasattr(instance, 'image'):
                    # Instance from image returns dict
                    if isinstance(instance.image, dict):
                        if instance.image.get('id') in image_map:
                            instance.image = image_map[instance.image['id']]

                try:
                    flavor_id = instance.flavor["id"]
                    if flavor_id in full_flavors:
                        instance.full_flavor = full_flavors[flavor_id]
                    else:
                        # If the flavor_id is not in full_flavors list,
                        # get it via nova api.
                        instance.full_flavor = api.nova.flavor_get(
                            self.request, flavor_id)
                except Exception:
                    msg = ('Unable to retrieve flavor "%s" for instance "%s".'
                           % (flavor_id, instance.id))
                    LOG.info(msg)
                tenant = tenant_dict.get(instance.tenant_id, None)
                user = user_dict.get(instance.user_id, None)
                instance.tenant_name = getattr(tenant, "name", None)
                instance.user_name = getattr(user, "name", None)
        return instances

    def get_filters(self, filters):
        filter_field = self.table.get_filter_field()
        filter_action = self.table._meta._filter_action
        if filter_action.is_api_filter(filter_field):
            filter_string = self.table.get_filter_string()
            if filter_field and filter_string:
                filters[filter_field] = filter_string
        return filters



class LaunchInstanceView(workflows.WorkflowView):
    workflow_class = project_workflows.LaunchInstance

    def get_initial(self):
        initial = super(LaunchInstanceView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        defaults = getattr(settings, 'LAUNCH_INSTANCE_DEFAULTS', {})
        initial['config_drive'] = defaults.get('config_drive', False)
        return initial


def console(request, instance_id):
    data = _('Unable to get log for instance "%s".') % instance_id
    tail = request.GET.get('length')
    if tail and not tail.isdigit():
        msg = _('Log length must be a nonnegative integer.')
        messages.warning(request, msg)
    else:
        try:
            data = api.nova.server_console_output(request,
                                                  instance_id,
                                                  tail_length=tail)
        except Exception:
            exceptions.handle(request, ignore=True)
    return http.HttpResponse(data.encode('utf-8'), content_type='text/plain')


def vnc(request, instance_id):
    try:
        instance = api.nova.server_get(request, instance_id)
        console_url = project_console.get_console(request, 'VNC', instance)[1]
        return shortcuts.redirect(console_url)
    except Exception:
        redirect = reverse("horizon:admin:vgpu:index")
        msg = _('Unable to get VNC console for instance "%s".') % instance_id
        exceptions.handle(request, msg, redirect=redirect)


def spice(request, instance_id):
    try:
        instance = api.nova.server_get(request, instance_id)
        console_url = project_console.get_console(request, 'SPICE',
                                                  instance)[1]
        return shortcuts.redirect(console_url)
    except Exception:
        redirect = reverse("horizon:admin:vgpu:index")
        msg = _('Unable to get SPICE console for instance "%s".') % instance_id
        exceptions.handle(request, msg, redirect=redirect)


def rdp(request, instance_id):
    try:
        instance = api.nova.server_get(request, instance_id)
        console_url = project_console.get_console(request, 'RDP', instance)[1]
        return shortcuts.redirect(console_url)
    except Exception:
        redirect = reverse("horizon:admin:vgpu:index")
        msg = _('Unable to get RDP console for instance "%s".') % instance_id
        exceptions.handle(request, msg, redirect=redirect)


class SerialConsoleView(generic.TemplateView):
    template_name = 'admin/vgpu/serial_console.html'

    def get_context_data(self, **kwargs):
        context = super(SerialConsoleView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        instance = None
        try:
            instance = api.nova.server_get(self.request,
                                           self.kwargs['instance_id'])
        except Exception:
            context["error_message"] = _(
                "Cannot find instance %s.") % self.kwargs['instance_id']
            # name is unknown, so leave it blank for the window title
            # in full-screen mode, so only the instance id is shown.
            context['instance_name'] = ''
            return context
        context['instance_name'] = instance.name
        try:
            console_url = project_console.get_console(self.request,
                                                      "SERIAL", instance)[1]
            context["console_url"] = console_url
        except exceptions.NotAvailable:
            context["error_message"] = _(
                "Cannot get console for instance %s.") % self.kwargs[
                'instance_id']
        return context


class UpdateView(workflows.WorkflowView):
    workflow_class = project_workflows.UpdateInstance
    success_url = reverse_lazy("horizon:admin:vgpu:index")

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()
        initial.update({'instance_id': self.kwargs['instance_id'],
                        'name': getattr(self.get_object(), 'name', '')})
        return initial


class RebuildView(forms.ModalFormView):
    form_class = project_forms.RebuildInstanceForm
    template_name = 'admin/vgpu/rebuild.html'
    success_url = reverse_lazy('horizon:admin:vgpu:index')
    page_title = _("Rebuild Instance")
    submit_label = page_title

    def get_context_data(self, **kwargs):
        context = super(RebuildView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        context['can_set_server_password'] = api.nova.can_set_server_password()
        return context

    def get_initial(self):
        return {'instance_id': self.kwargs['instance_id']}


class DecryptPasswordView(forms.ModalFormView):
    form_class = project_forms.DecryptPasswordInstanceForm
    template_name = 'admin/vgpu/decryptpassword.html'
    success_url = reverse_lazy('horizon:admin:vgpu:index')
    page_title = _("Retrieve Instance Password")

    def get_context_data(self, **kwargs):
        context = super(DecryptPasswordView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        context['keypair_name'] = self.kwargs['keypair_name']
        return context

    def get_initial(self):
        return {'instance_id': self.kwargs['instance_id'],
                'keypair_name': self.kwargs['keypair_name']}


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.InstanceDetailTabs
    template_name = 'horizon/vgpu/_detail.html'
    redirect_url = 'horizon:admin:vgpu:index'
    page_title = "{{ instance.name|default:instance.id }}"
    image_url = 'horizon:admin:images:images:detail'
    volume_url = 'horizon:admin:volumes:volumes:detail'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        instance = self.get_data()
        #LOG.info("instance ==================%s" %  instance)
#        if instance.image:
#            instance.image_url = reverse(self.image_url,
#                                         args=[instance.image['id']])
        instance.volume_url = self.volume_url
        context["instance"] = instance
        context["url"] = reverse(self.redirect_url)
        context["actions"] = self._get_actions(instance)
        return context

    def _get_actions(self, instance):
        table = project_tables.InstancesTable(self.request)
        return table.render_row_actions(instance)

    @memoized.memoized_method
    def get_data(self):
        instance_id = self.kwargs['instance_id']

        try:
            instance = api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse(self.redirect_url)
            exceptions.handle(self.request,
                              _('Unable to retrieve details for '
                                'instance "%s".') % instance_id,
                              redirect=redirect)
            # Not all exception types handled above will result in a redirect.
            # Need to raise here just in case.
            raise exceptions.Http302(redirect)

        choices = project_tables.STATUS_DISPLAY_CHOICES
        instance.status_label = (
            filters.get_display_label(choices, instance.status))

        try:
            instance.volumes = api.nova.instance_volumes_list(self.request,
                                                              instance_id)
            # Sort by device name
            instance.volumes.sort(key=lambda vol: vol.device)
        except Exception:
            msg = _('Unable to retrieve volume list for instance '
                    '"%(name)s" (%(id)s).') % {'name': instance.name,
                                               'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        try:
            instance.full_flavor = api.nova.flavor_get(
                self.request, instance.flavor["id"])
        except Exception:
            msg = _('Unable to retrieve flavor information for instance '
                    '"%(name)s" (%(id)s).') % {'name': instance.name,
                                               'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        try:
            instance.security_groups = api.network.server_security_groups(
                self.request, instance_id)
        except Exception:
            msg = _('Unable to retrieve security groups for instance '
                    '"%(name)s" (%(id)s).') % {'name': instance.name,
                                               'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        try:
            api.network.servers_update_addresses(self.request, [instance])
        except Exception:
            msg = _('Unable to retrieve IP addresses from Neutron for '
                    'instance "%(name)s" (%(id)s).') % {'name': instance.name,
                                                        'id': instance_id}
            exceptions.handle(self.request, msg, ignore=True)

        return instance

    def get_tabs(self, request, *args, **kwargs):
        instance = self.get_data()
        return self.tab_group_class(request, instance=instance, **kwargs)


class ResizeView(workflows.WorkflowView):
    workflow_class = project_workflows.ResizeInstance
    success_url = reverse_lazy("horizon:admin:vgpu:index")

    def get_context_data(self, **kwargs):
        context = super(ResizeView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            instance = api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)
        flavor_id = instance.flavor['id']
        flavors = self.get_flavors()
        if flavor_id in flavors:
            instance.flavor_name = flavors[flavor_id].name
        else:
            try:
                flavor = api.nova.flavor_get(self.request, flavor_id)
                instance.flavor_name = flavor.name
            except Exception:
                msg = _('Unable to retrieve flavor information for instance '
                        '"%s".') % instance_id
                exceptions.handle(self.request, msg, ignore=True)
                instance.flavor_name = _("Not available")
        return instance

    @memoized.memoized_method
    def get_flavors(self, *args, **kwargs):
        try:
            flavors = api.nova.flavor_list(self.request)
            return OrderedDict((str(flavor.id), flavor) for flavor in flavors)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve flavors.'),
                              redirect=redirect)

    def get_initial(self):
        initial = super(ResizeView, self).get_initial()
        _object = self.get_object()
        if _object:
            initial.update(
                {'instance_id': self.kwargs['instance_id'],
                 'name': getattr(_object, 'name', None),
                 'old_flavor_id': _object.flavor['id'],
                 'old_flavor_name': getattr(_object, 'flavor_name', ''),
                 'flavors': self.get_flavors()})
        return initial


class AttachInterfaceView(forms.ModalFormView):
    form_class = project_forms.AttachInterface
    template_name = 'admin/vgpu/attach_interface.html'
    modal_header = _("Attach Interface")
    form_id = "attach_interface_form"
    submit_label = _("Attach Interface")
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    def get_context_data(self, **kwargs):
        context = super(AttachInterfaceView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context

    def get_initial(self):
        args = {'instance_id': self.kwargs['instance_id']}
        submit_url = "horizon:admin:vgpu:attach_interface"
        self.submit_url = reverse(submit_url, kwargs=args)
        return args


class AttachVolumeView(forms.ModalFormView):
    form_class = project_forms.AttachVolume
    template_name = 'admin/vgpu/attach_volume.html'
    modal_header = _("Attach Volume")
    modal_id = "attach_volume_modal"
    submit_label = _("Attach Volume")
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.nova.server_get(self.request,
                                       self.kwargs["instance_id"])
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve instance."))

    def get_initial(self):
        args = {'instance_id': self.kwargs['instance_id']}
        submit_url = "horizon:admin:vgpu:attach_volume"
        self.submit_url = reverse(submit_url, kwargs=args)
        try:
            volume_list = api.cinder.volume_list(self.request)
        except Exception:
            volume_list = []
            exceptions.handle(self.request,
                              _("Unable to retrieve volume information."))
        return {"instance_id": self.kwargs["instance_id"],
                "volume_list": volume_list}

    def get_context_data(self, **kwargs):
        context = super(AttachVolumeView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context


class DetachVolumeView(forms.ModalFormView):
    form_class = project_forms.DetachVolume
    template_name = 'admin/vgpu/detach_volume.html'
    modal_header = _("Detach Volume")
    modal_id = "detach_volume_modal"
    submit_label = _("Detach Volume")
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    @memoized.memoized_method
    def get_object(self):
        try:
            return api.nova.server_get(self.request,
                                       self.kwargs['instance_id'])
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve instance."))

    def get_initial(self):
        args = {'instance_id': self.kwargs['instance_id']}
        submit_url = "horizon:admin:vgpu:detach_volume"
        self.submit_url = reverse(submit_url, kwargs=args)
        return {"instance_id": self.kwargs["instance_id"]}

    def get_context_data(self, **kwargs):
        context = super(DetachVolumeView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context


class DetachInterfaceView(forms.ModalFormView):
    form_class = project_forms.DetachInterface
    template_name = 'admin/vgpu/detach_interface.html'
    modal_header = _("Detach Interface")
    form_id = "detach_interface_form"
    submit_label = _("Detach Interface")
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    def get_context_data(self, **kwargs):
        context = super(DetachInterfaceView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context

    def get_initial(self):
        args = {"instance_id": self.kwargs["instance_id"]}
        submit_url = "horizon:admin:vgpu:detach_interface"
        self.submit_url = reverse(submit_url, kwargs=args)
        return args

class ReallocationView(forms.ModalFormView):
    form_class = project_forms.ReallocationInstanceForm
    template_name = 'admin/vgpu/reallocation.html'
    context_object_name = 'instance'
    submit_label = _("Allocate")
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    def get_context_data(self, **kwargs):
        context = super(ReallocationView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context

    def get_initial(self):
        return {'instance_id': self.kwargs['instance_id']}

class CreateDevsnapshotView(forms.ModalFormView):
    form_class = project_forms.CreateDevsnapshotForm
    template_name = 'admin/vgpu/create_dev_sanpshot.html'
    context_object_name = 'instance'
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    def get_context_data(self, **kwargs):
        context = super(CreateDevsnapshotView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context

    def get_initial(self):
        return {'instance_id': self.kwargs['instance_id']}

class DeleteDevsnapshotView(forms.ModalFormView):
    form_class = project_forms.DeleteDevsnapshotForm
    template_name = 'admin/vgpu/delete_dev_sanpshot.html'
    context_object_name = 'instance'
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    def get_context_data(self, **kwargs):
        context = super(DeleteDevsnapshotView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context

    def get_initial(self):
        name = self.request.GET.get('name', None)
        return {'instance_id': self.kwargs['instance_id'], 'name':name}

class SetDevsnapshotView(forms.ModalFormView):
    form_class = project_forms.SetDevsnapshotForm
    template_name = 'admin/vgpu/set_dev_sanpshot.html'
    context_object_name = 'instance'
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    def get_context_data(self, **kwargs):
        context = super(SetDevsnapshotView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context

    def get_initial(self):
        name = self.request.GET.get('name', None)
        return {'instance_id': self.kwargs['instance_id'], 
                'name':name}

class RevertDevsnapshotView(forms.ModalFormView):
    form_class = project_forms.RevertDevsnapshotForm
    template_name = 'admin/vgpu/revert_dev_sanpshot.html'
    context_object_name = 'instance'
    success_url = reverse_lazy('horizon:admin:vgpu:index')

    def get_context_data(self, **kwargs):
        context = super(RevertDevsnapshotView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        return context

    def get_initial(self):
        name = self.request.GET.get('name', None)
        return {'instance_id': self.kwargs['instance_id'],
                'name':name}

class LiveMigrateView(forms.ModalFormView):
    form_class = project_forms.LiveMigrateForm
    template_name = 'admin/vgpu/live_migrate.html'
    context_object_name = 'instance'
    success_url = reverse_lazy("horizon:admin:vgpu:index")

    def get_context_data(self, **kwargs):
        context = super(LiveMigrateView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_hosts(self, *args, **kwargs):
        try:
            return api.nova.host_list(self.request)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            msg = _('Unable to retrieve host information.')
            exceptions.handle(self.request, msg, redirect=redirect)

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        initial = super(LiveMigrateView, self).get_initial()
        _object = self.get_object()
        if _object:
            current_host = getattr(_object, 'OS-EXT-SRV-ATTR:host', '')
            initial.update({'instance_id': self.kwargs['instance_id'],
                            'current_host': current_host,
                            'hosts': self.get_hosts()})
        return initial


class UpdateInstanceResourceView(workflows.WorkflowView):
    workflow_class = project_workflows.UpdateInstanceResource

    def get_context_data(self, **kwargs):
        context = super(UpdateInstanceResourceView, self).get_context_data(**kwargs)
        context["flavors"] = self.get_flavors()
        return context

    @memoized.memoized_method
    def get_flavors(self, *args, **kwargs):
        try:
            flavors = api.nova.flavor_list(self.request)
            return SortedDict((str(flavor.id), flavor) for flavor in flavors)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            exceptions.handle(self.request,
                _('Unable to retrieve flavors.'), redirect=redirect)

    def get_initial(self):
        initial = super(UpdateInstanceResourceView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        initial['flavors'] = self.get_flavors()
        return initial


class TimingBootView(workflows.WorkflowView):
    workflow_class = project_workflows.TimingBoot

    def get_initial(self):
        initial = super(TimingBootView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class TimingShutdownView(workflows.WorkflowView):
    workflow_class = project_workflows.TimingShutdown

    def get_initial(self):
        initial = super(TimingShutdownView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class EditTimingBootView(workflows.WorkflowView):
    workflow_class = project_workflows.SingleTimingBoot
    success_url = reverse_lazy("horizon:admin:vgpu:index")

    def get_context_data(self, **kwargs):
        context = super(EditTimingBootView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            msg = _('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        initial = super(EditTimingBootView, self).get_initial()
        initial.update({'instance_id': self.kwargs['instance_id'],
                'name': getattr(self.get_object(), 'name', '')})
        return initial


class EditTimingShutdownView(workflows.WorkflowView):
    workflow_class = project_workflows.SingleTimingShutdown
    success_url = reverse_lazy("horizon:admin:vgpu:index")

    def get_context_data(self, **kwargs):
        context = super(EditTimingShutdownView, self).get_context_data(**kwargs)
        context["instance_id"] = self.kwargs['instance_id']
        return context

    @memoized.memoized_method
    def get_object(self, *args, **kwargs):
        instance_id = self.kwargs['instance_id']
        try:
            return api.nova.server_get(self.request, instance_id)
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            msg =_('Unable to retrieve instance details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        initial = super(EditTimingShutdownView, self).get_initial()
        initial.update({'instance_id':self.kwargs['instance_id'],
                       'name':getattr(self.get_object(), 'name', '')})
        return initial


class CDromView(forms.ModalFormView):
    form_class = project_forms.CDRomForm
    template_name = 'admin/vgpu/cdrom.html'
    success_url = reverse_lazy("horizon:admin:vgpu:index")

    @memoized.memoized_method
    def get_devices(self):
        try:
            cdroms = api.nova.cdrom_list(self.request,
                self.kwargs["instance_id"])
        except Exception:
            cdroms = []
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(self.request,
                              _("Unable to retrieve the devices of instance."),
                              redirect=redirect)
        return cdroms

    @memoized.memoized_method
    def get_isos(self):
        try:
            isos, _m, _p = api.glance.image_list_detailed(self.request)
        except Exception:
            isos = []
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(self.request,
                              _("Unable to retrieve the isos."),
                              redirect=redirect)

        return isos

    def get_initial(self):
        instance = api.nova.server_get(self.request, self.kwargs['instance_id'])
        return {"instance_id":self.kwargs['instance_id'], 
                "instance_name":getattr(instance, 'name', 'Error Not Name'),
                "isos":self.get_isos(),
                "devices":self.get_devices()}

    def get_context_data(self, **kwargs):
        context = super(CDromView, self).get_context_data(**kwargs)
        context['instance_id'] = self.kwargs['instance_id']
        #LOG.info("get_context_data ===============%s" % context)
        context['devices'] = self.get_devices()
        if not context['devices'] or len(context['devices']) == 0:
            context['show_attach'] = False
        else:
            context['show_attach'] = True
        return context



