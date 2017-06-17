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
import logging

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.views.decorators.debug import sensitive_variables  # noqa

from horizon import exceptions
from horizon import forms
from horizon import workflows
from horizon import messages

from openstack_dashboard import api
from openstack_dashboard.usage import quotas

from openstack_dashboard.dashboards.admin.instances \
    import utils as instance_utils
LOG = logging.getLogger(__name__)

class ResourceAction(workflows.Action):
    checkboxlist = forms.CharField(widget=forms.HiddenInput())

    flavor = forms.ChoiceField(label=_("New Flavor"),
                               help_text=_("Choose the flavor to resize."))

    class Meta:
        name = _("Flavor Choice")
        help_text_template = ("admin/instances/_update_instance_resource_help.html")

    def __init__(self, request, context, *args, **kwargs):
        self.request = request
        self.context = context
        super(ResourceAction, self).__init__(request, context, *args, **kwargs)

    def clean(self):
        cleaned_data = super(ResourceAction, self).clean()
        checkbox = cleaned_data.get("checkboxlist", None)
        if not checkbox:
            error_message=_("No instance option selected")
            raise forms.ValidationError(error_message)
        select_flavor_id = cleaned_data.get('flavor')
        select_flavor = api.nova.flavor_get(self.request, select_flavor_id)
        select_flavor_vcpus = select_flavor.vcpus
        select_flavor_ram = select_flavor.ram
        select_flavor_disk = select_flavor.disk
        select_flavor_ephemeral = select_flavor.ephemeral
        instance_ids = checkbox.split("_")
        resource_allocation_ratio = api.nova.get_resource_allocation_ratio(self.request)
        ram_allocation = resource_allocation_ratio.get('ram_allocation', 1.5)
        cpu_allocation = resource_allocation_ratio.get('cpu_allocation', 16.0)
        disk_allocation = resource_allocation_ratio.get('disk_allocation', 1.0)
        flug =0
        tenant_resources = {}
        server_hosts = {}
        for instance_id in instance_ids:
            instance = api.nova.server_get(self.request, instance_id)
            instance_host = getattr(instance, 'vm_node', None)
            flavor_id = instance.flavor['id']
            if flavor_id == select_flavor_id:
                flug =1
                break
            flavor = api.nova.flavor_get(self.request, flavor_id)
            if select_flavor_disk < flavor.disk or select_flavor_ephemeral < flavor.ephemeral:
                flug =2
                break

            if server_hosts.has_key(instance_host):
                server_hosts[instance_host]['vcpus'] += instance.vcpus
                server_hosts[instance_host]['rams'] += instance.rams
                instance_disk = flavor.disk + flavor.ephemeral
                server_hosts[instance_host]['disks'] += instance_disk
                server_hosts[instance_host]['count'] += 1
            else:
                server_hosts[instance_host] ={}
                server_hosts[instance_host]['vcpus'] = instance.vcpus
                server_hosts[instance_host]['rams'] = instance.rams
                server_hosts[instance_host]['disks'] = flavor.disk + flavor.ephemeral
                server_hosts[instance_host]['count'] = 1
            if tenant_resources.has_key(instance.tenant_id):
                tenant_resources[instance.tenant_id]['vcpus'] = tenant_resources[instance.tenant_id]['vcpus'] + instance.vcpus
                tenant_resources[instance.tenant_id]['rams'] = tenant_resources[instance.tenant_id]['rams'] + instance.rams
                tenant_resources[instance.tenant_id]['count'] = tenant_resources[instance.tenant_id]['count'] + 1
            else:
                tenant_resources[instance.tenant_id] ={}
                tenant_resources[instance.tenant_id]['vcpus']=instance.vcpus
                tenant_resources[instance.tenant_id]['rams']=instance.rams
                tenant_resources[instance.tenant_id]['count']=1

        server_error =[]
        hypervisors = api.nova.hypervisor_list(self.request)
        for hypervisor in hypervisors:
            hypervisor_hostname = hypervisor.hypervisor_hostname
            server_name = hypervisor_hostname.split('.')[0]
            if server_hosts.has_key(server_name):
                if hypervisor.hypervisor_type =="xen":
                    total_vcpus = hypervisor.vcpus
                    total_rams = hypervisor.memory_mb
                    total_disk = hypervisor.local_gb
                    avail_vcpus = total_vcpus - hypervisor.vcpus_used + server_hosts[instance_host]['vcpus']
                    avail_rams = total_rams - hypervisor.memory_mb_used + server_hosts[instance_host]['rams']
                    avail_disk = total_disk - hypervisor.local_gb_used + server_hosts[instance_host]['disks']
                else:
                    total_vcpus = hypervisor.vcpus * cpu_allocation
                    total_rams = hypervisor.memory_mb * ram_allocation
                    total_disk = hypervisor.local_gb * disk_allocation
                    avail_vcpus = total_vcpus - hypervisor.vcpus_used + server_hosts[instance_host]['vcpus']
                    avail_rams = total_rams - hypervisor.memory_mb_used + server_hosts[instance_host]['rams']
                    avail_disk = total_disk - hypervisor.local_gb_used + server_hosts[instance_host]['disks']
                request_vcpus = server_hosts[instance_host]['count'] * select_flavor_vcpus
                request_rams = server_hosts[instance_host]['count'] * select_flavor_ram
                request_disk = server_hosts[instance_host]['count'] * (select_flavor_disk + select_flavor_ephemeral)

                if avail_vcpus < request_vcpus:
                    flug = 3
                    server_error.append(_("Compute Node %(server_name)s:VCPU:(Available:%(avail)s, Requestd:%(req)s)") 
                                           % {'server_name': server_name, 'avail': avail_vcpus, 'req':request_vcpus})

                if avail_rams < request_rams:
                    flug = 3
                    server_error.append(_("Compute Node %(server_name)s:RAM:(Available:%(avail)s(MB), Requestd:%(req)s(MB))") 
                                          % {'server_name': server_name, 'avail': avail_rams, 'req':request_rams})

                if avail_disk < request_disk:
                    flug = 3
                    server_error.append(_("Compute Node %(server_name)s:Disk:(Available:%(avail)s(GB), Requestd:%(req)s(GB))") 
                                          % {'server_name': server_name, 'avail': avail_disk, 'req':request_disk})

        if flug !=3:
            count_error =[]
            for tenant_id in tenant_resources.keys():
                select_resource_vcpus = tenant_resources[tenant_id]['count'] * select_flavor_vcpus
                select_resource_rams = tenant_resources[tenant_id]['count'] * select_flavor_ram
                tenant = api.keystone.tenant_get(self.request, tenant_id)
                #wengshuhua TODO
                #usages = quotas.tenant_quota_usages(self.request, pool=tenant.name)
                usages = quotas.tenant_quota_usages(self.request)
                available_vcpus = usages['cores']['available'] + tenant_resources[tenant_id]['vcpus']
                available_ram = usages['ram']['available'] + tenant_resources[tenant_id]['rams']
                if available_vcpus < select_resource_vcpus:
                    flug = 4
                    count_error.append(_("Pool %(pool)s:VCPU(Available: %(avail)s(MB),"
                                     "Requested: %(req)s(MB))") % {'pool':tenant.name, 'avail': available_vcpus, 'req': select_resource_vcpus})
                if available_ram < select_resource_rams:
                    flug = 4
                    count_error.append(_("Pool(%(pool)s):RAM(Available: %(avail)s,"
                                     "Requested: %(req)s)") % {'pool':tenant.name, 'avail': available_ram, 'req': select_resource_rams})
        if flug ==1:
            msg = _("The flavor is same as the origin flavor of some instances you select.Please reselect.")
            self._errors['flavor'] = self.error_class([msg])
        elif flug ==2:
            msg = _("The disk of selected flavor is lower than the origin disk of some instances.Please reselect.")
            self._errors['flavor'] = self.error_class([msg])
        elif flug == 3:
            if server_error:
                value_str = ", ".join(server_error)
                msg = (_('The instance cannot be updated. '
                        'The following requested resource(s) exceed '
                        'quota(s): %s.') % value_str)
                self._errors['flavor'] = self.error_class([msg])
        elif flug == 4:
            if count_error:
                value_str = ", ".join(count_error)
                msg = (_('The instance cannot be updated. '
                        'The following requested resource(s) exceed '
                        'quota(s): %s.') % value_str)
                self._errors['flavor'] = self.error_class([msg])

        return cleaned_data

    def populate_flavor_choices(self, request, context):
         flavors = context.get("flavors").values()
         if len(flavors) > 1:
             flavors = instance_utils.sort_flavor_list(request, flavors)
         if flavors:
             flavors.insert(0, ("", _("Select a New Flavor")))
         else:
             flavors.insert(0, ("", _("No flavors available")))
         return flavors


class Resource(workflows.Step):
    action_class = ResourceAction
    contributes = ("flavors", "flavor", "checkboxlist")
    def contribute(self, data, context):
        if data:
            context['checkboxlist'] = data.get("checkboxlist", None)
            checkbox = data.get("checkboxlist", None)
            context['instance_ids'] = checkbox.split("_")
            context['flavor'] = data.get("flavor", None)
        return context

class UpdateInstanceResource(workflows.Workflow):
    slug = "update instance resource"
    name = _("Resize Instance")
    success_message = _('Update %(count)s.')
    failure_message = _('Unable to update %(count)s.')
    success_url = "horizon:admin:instances:index"
    multipart = True
    default_steps = (Resource,)

    def format_status_message(self, message):
        checkboxlist = self.context.get('checkboxlist', '')
        checkbox = checkboxlist.split("_")
        name = self.context.get('name', 'unknown instance')
        instance_ids = self.context['instance_ids']
        count = len(instance_ids)
        if int(count) > 1:
            return message % {"count": _("%s instances") % count}
        else:
            return message % {"count": _("%s instance") % count}

    @sensitive_variables('context')
    def handle(self, request, context):
        try:
            flavor = context['flavor']
            #wengshuhua TODO
            #for instance_id in context['instance_ids']:
            #    names = api.nova.dev_snapshot_list(request, instance_id)
            #    if names:
            #        for name in names:
            #            api.nova.dev_snapshot_delete(request, instance_id, name.snapshotname)
            LOG.info("========================= horizion -> horizon API:server_batch_resize=================")
            api.nova.server_batch_resize(request, context['instance_ids'], flavor, disk_config=None)

            return True
        except Exception:
            exceptions.handle(request)
            return False
