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
import operator
import json, uuid
from django.http import HttpResponse
from django.views.generic import View as AjaxView
from django.conf import settings
from django.utils.datastructures import SortedDict
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from oslo_log import log as logging
from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon.utils import memoized
from horizon import views, forms
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.api import keystone
from openstack_dashboard import policy
from openstack_dashboard import usage
from openstack_dashboard.usage import quotas

from openstack_dashboard.dashboards.admin.projects \
    import tables as project_tables
from openstack_dashboard.dashboards.admin.projects \
    import workflows as project_workflows
from openstack_dashboard.dashboards.project.overview \
    import views as project_views
from openstack_dashboard.dashboards.admin.instances \
    import tables as instance_tables


LOG = logging.getLogger(__name__)

PROJECT_INFO_FIELDS = ("domain_id",
                       "domain_name",
                       "name",
                       "description",
                       "enabled")

INDEX_URL = "horizon:admin:projects:index"


class TenantContextMixin(object):
    @memoized.memoized_method
    def get_object(self):
        tenant_id = self.kwargs['tenant_id']
        try:
            return api.keystone.tenant_get(self.request, tenant_id, admin=True)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project information.'),
                              redirect=reverse(INDEX_URL))

    def get_context_data(self, **kwargs):
        context = super(TenantContextMixin, self).get_context_data(**kwargs)
        context['tenant'] = self.get_object()
        return context

class BelongsInstanceView(tables.DataTableView):
    table_class = instance_tables.InstancesTable
    template_name = 'admin/instances/index.html'
    page_title = _('Instance')

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        project_id = self.kwargs.get('project_id', None)
        search_opts={'project_id':project_id}
        instance, self._more= api.nova.server_list(
                  self.request, search_opts=search_opts)
        return instance 


class IndexView(tables.DataTableView):
    table_class = project_tables.TenantsTable
    template_name = 'admin/projects/index.html'
    page_title = _("Projects")

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        tenants = []
        marker = self.request.GET.get(
            project_tables.TenantsTable._meta.pagination_param, None)
        self._more = False
        filters = self.get_filters()
        if policy.check((("identity", "identity:list_projects"),),
                        self.request):
            domain_context = api.keystone.get_effective_domain_id(self.request)
            try:
                tenants, self._more = api.keystone.tenant_list(
                    self.request,
                    domain=domain_context,
                    paginate=True,
                    filters=filters,
                    marker=marker)
            except Exception:
                exceptions.handle(self.request,
                                  _("Unable to retrieve project list."))
        elif policy.check((("identity", "identity:list_user_projects"),),
                          self.request):
            try:
                tenants, self._more = api.keystone.tenant_list(
                    self.request,
                    user=self.request.user.id,
                    paginate=True,
                    marker=marker,
                    filters=filters,
                    admin=False)
            except Exception:
                exceptions.handle(self.request,
                                  _("Unable to retrieve project information."))
        else:
            msg = \
                _("Insufficient privilege level to view project information.")
            messages.info(self.request, msg)

        if api.keystone.VERSIONS.active >= 3:
            domain_lookup = api.keystone.domain_lookup(self.request)
            for t in tenants:
                t.domain_name = domain_lookup.get(t.domain_id)
        LOG.info("tenants ===========================%s" % tenants)
        return tenants


class ProjectUsageView(usage.UsageView):
    table_class = usage.ProjectUsageTable
    usage_class = usage.ProjectUsage
    template_name = 'admin/projects/usage.html'
    csv_response_class = project_views.ProjectUsageCsvRenderer
    csv_template_name = 'admin/overview/usage.csv'
    page_title = _("Project Usage")

    def get_data(self):
        super(ProjectUsageView, self).get_data()
        return self.usage.get_instances()


class CreateProjectView(workflows.WorkflowView):
    workflow_class = project_workflows.CreateProject

    def get_initial(self):

        if (api.keystone.is_multi_domain_enabled() and
                not api.keystone.is_cloud_admin(self.request)):
            self.workflow_class = project_workflows.CreateProjectNoQuota

        initial = super(CreateProjectView, self).get_initial()

        # Set the domain of the project
        domain = api.keystone.get_default_domain(self.request)
        initial["domain_id"] = domain.id
        initial["domain_name"] = domain.name

        # get initial quota defaults
        if api.keystone.is_cloud_admin(self.request):
            try:
                quota_defaults = quotas.get_default_quota_data(self.request)

                try:
                    if api.base.is_service_enabled(
                            self.request, 'network') and \
                            api.neutron.is_quotas_extension_supported(
                                self.request):
                        # TODO(jpichon): There is no API to access the Neutron
                        # default quotas (LP#1204956). For now, use the values
                        # from the current project.
                        project_id = self.request.user.project_id
                        quota_defaults += api.neutron.tenant_quota_get(
                            self.request,
                            tenant_id=project_id)
                except Exception:
                    error_msg = _('Unable to retrieve default Neutron quota '
                                  'values.')
                    self.add_error_to_step(error_msg, 'create_quotas')

                for field in quotas.QUOTA_FIELDS:
                    initial[field] = quota_defaults.get(field).limit

            except Exception:
                error_msg = _('Unable to retrieve default quota values.')
                self.add_error_to_step(error_msg, 'create_quotas')

        return initial


class UpdateProjectView(workflows.WorkflowView):
    workflow_class = project_workflows.UpdateProject

    def get_initial(self):

        if (api.keystone.is_multi_domain_enabled() and
                not api.keystone.is_cloud_admin(self.request)):
            self.workflow_class = project_workflows.UpdateProjectNoQuota

        initial = super(UpdateProjectView, self).get_initial()

        project_id = self.kwargs['tenant_id']
        initial['project_id'] = project_id

        try:
            # get initial project info
            project_info = api.keystone.tenant_get(self.request, project_id,
                                                   admin=True)
            for field in PROJECT_INFO_FIELDS:
                initial[field] = getattr(project_info, field, None)

            if keystone.VERSIONS.active >= 3:
                # get extra columns info
                ex_info = getattr(settings, 'PROJECT_TABLE_EXTRA_INFO', {})
                for ex_field in ex_info:
                    initial[ex_field] = getattr(project_info, ex_field, None)

                # Retrieve the domain name where the project belong
                try:
                    if policy.check((("identity", "identity:get_domain"),),
                                    self.request):
                        domain = api.keystone.domain_get(self.request,
                                                         initial["domain_id"])
                        initial["domain_name"] = domain.name

                    else:
                        domain = api.keystone.get_default_domain(self.request)
                        initial["domain_name"] = domain.name

                except Exception:
                    exceptions.handle(self.request,
                                      _('Unable to retrieve project domain.'),
                                      redirect=reverse(INDEX_URL))

            # get initial project quota
            if keystone.is_cloud_admin(self.request):
                quota_data = quotas.get_tenant_quota_data(self.request,
                                                          tenant_id=project_id)
                if api.base.is_service_enabled(self.request, 'network') and \
                        api.neutron.is_quotas_extension_supported(
                            self.request):
                    quota_data += api.neutron.tenant_quota_get(
                        self.request, tenant_id=project_id)
                for field in quotas.QUOTA_FIELDS:
                    initial[field] = quota_data.get(field).limit
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project details.'),
                              redirect=reverse(INDEX_URL))
        return initial


class DetailProjectView(views.HorizonTemplateView):
    template_name = 'admin/projects/detail.html'
    page_title = "{{ project.name }}"

    def get_context_data(self, **kwargs):
        context = super(DetailProjectView, self).get_context_data(**kwargs)
        project = self.get_data()
        table = project_tables.TenantsTable(self.request)
        context["project"] = project
        context["url"] = reverse(INDEX_URL)
        context["actions"] = table.render_row_actions(project)

        if keystone.VERSIONS.active >= 3:
            extra_info = getattr(settings, 'PROJECT_TABLE_EXTRA_INFO', {})
            context['extras'] = dict(
                (display_key, getattr(project, key, ''))
                for key, display_key in extra_info.items())
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            project_id = self.kwargs['project_id']
            project = api.keystone.tenant_get(self.request, project_id)
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve project details.'),
                              redirect=reverse(INDEX_URL))
        return project

class BindingInstanceForm(forms.SelfHandlingForm):

    tenant_id = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, request, *args, **kwargs):
        super(BindingInstanceForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})

    def handle(self, request, data):
        msg = _('The instance  is successful  reallocated.')
        messages.success(request, msg)
        return True


class DedicatedBindingView(forms.ModalFormView):
    form_class = BindingInstanceForm
    template_name = "admin/projects/binding.html"
    context_object_name = 'binding'
    success_url = reverse_lazy("horizon:admin:projects:index")

    def get_context_data(self, **kwargs):
        context = super(DedicatedBindingView, self).get_context_data(**kwargs)
        self.page_title=self.request.GET.get("page_title", None)
        context['pool_type']=self.request.GET.get("pool_type", None)
        context['tenant_id']=self.kwargs['tenant_id']
        context['instance'] = self.get_instance()
        tenant = SortedDict([(t.id, t.name)for t in self.tenant_list()])
        user_list = [us.id for us in api.keystone.user_list(self.request)]
        free_instance = list()
        for ins in self.get_instance():
            if not ins.tenant_id:
                free_instance.append(ins)
            elif ins.tenant_id not in tenant.keys():
                free_instance.append(ins)
            elif ins.user_id not in user_list and ins.tenant_id == self.kwargs['tenant_id']:
                free_instance.append(ins)
            elif ins.tenant_id in tenant.keys():
                _values = tenant.values()
                admin_index = _values.index(u'admin')
                _keys = tenant.keys()
                admin_keys_id = _keys.pop(admin_index)
                if ins.tenant_id == admin_keys_id:
                    free_instance.append(ins)
        context['free_instance']=sorted(free_instance, key=operator.attrgetter('name'))
        context['user']=sorted(self.get_user(tenant_id=self.kwargs['tenant_id']), 
                               key=operator.attrgetter('name'))
        return context

    def get_instance(self):
        instance, has = api.nova.server_list(self.request, 
                        search_opts=None, all_tenants=True)
        return instance

    def get_user(self, tenant_id=None):
        return api.keystone.user_list(self.request, 
                                     project=tenant_id)

    def tenant_list(self):
        tenant, has = api.keystone.tenant_list(self.request)
        return tenant

    def get_tenant(self, tenant_id=None):
        return api.keystone.tenant_get(self.request, 
                                       project=tenant_id)

    def get_initial(self):
        return {"tenant_id": self.kwargs['tenant_id']}
    
class AjaxIndexView(AjaxView): 

    @classmethod
    def response_method(self, req, content=None):
        if content:
            data = ''.join([req.GET['callback'],
                   '(%s)' % json.dumps(content)])
        return HttpResponse(data, content_type="text/plain")


class CheckDedicatedInstanceView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):
        data_list = request.GET.get('data', None)
        tenant_id = kwargs.get('tenant_id', None)
        user_list = list()
        if data_list and tenant_id:
            data_loads = json.loads(data_list)
            instances = [ins.user_id for ins in api.nova.server_list(request,
                         all_tenants=True)[0] if ins.tenant_id==tenant_id]
            for user in data_loads:
                if user in instances:
                    user_list.append(user) 
        if not user_list:
            result = {"success":"error"}
        else:
            result = {"success":"success"}
        return self.response_method(request, result)

class SelectInstanceView(AjaxIndexView):

    def get(self, request, *args, **kwargs):
       
        tenant_id = kwargs.get('tenant_id', None) 
        user_id = request.GET.get('user_id', None)
        user_instance=list()
        if tenant_id and user_id:
            try:
                instances, more=api.nova.server_list(request, all_tenants=True) 
                user_instance = [(ins.name, ins.id) for ins in instances\
                       if ins.tenant_id==tenant_id and ins.user_id==user_id]
                result = request.GET['callback']
                result +='({"success": '+json.dumps(user_instance)+'})'
            except Exception:
                result=request.GET['callback']+'({"error":"error"})'
        response = HttpResponse(content_type='text/plain')
        response.write(result)
        response.flush()
        return response

class UserAddInstanceView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):
        tenant_id=kwargs.get('tenant_id', None)
        instance_id = request.GET.get('vm_id', None)
        user_id = request.GET.get('user_id', None)
        if tenant_id and instance_id and user_id:
            try:
                instance = api.nova.reallocation(
                           request, instance_id, 
                           project=tenant_id , 
                           user=user_id)
                if instance:
                    result= request.GET['callback']+'({"success":"success"})'
            except Exception:
                result = request.GET['callback']+'({"error":"error"})'
            response = HttpResponse(content_type='text/plain')
            response.write(result)
            response.flush()
            return response


class UserRemoveInstanceView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):
        tenant_id = kwargs.get('tenant_id', None)
        instance_id = request.GET.get('instance_id', None)
        user_id = request.GET.get('user_id', str(uuid.uuid4()).replace('-',''))
        try:
            instance = api.nova.reallocation(
                        request, instance_id,
                        project=tenant_id,
                        user=user_id)
            result = {"success":"success"}
        except Exception:
            result = {"error":"error"}
        return self.response_method(request, result)

class RemoveAllInstanceView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):
        
        try:
            callback = []
            data = []
            instance, has = api.nova.server_list(request, all_tenants=True)
            user_list=json.loads(request.GET.get('data', None))
            instance_list = []
            tenant, has = api.keystone.tenant_list(request)
            admin_tenant = [t.id for t in tenant if t.name =='admin'][0]
            for ins in instance:
                if ins.user_id in user_list and \
                   ins.tenant_id == self.kwargs['tenant_id']:
                    instance_list.append(ins.id)
            for ins in instance_list:
                instance = api.nova.reallocation(request, ins, 
                             project=self.kwargs['tenant_id'], 
                             user=str(uuid.uuid4()).replace('-',''))
                callback.append(instance)
            if callback:
                ins = [(i.name, i.id) for i in callback]
                data = request.GET['callback']+'({"success":'\
                       +json.dumps(sorted(ins, key=operator.itemgetter(0)))+'})'
        except Exception:
            data = request.GET['callback']+'({"error":"error"})'
        response = HttpResponse(content_type='text/plain')
        response.write(data)
        response.flush()
        return response

class BatchBindingInstanceView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):

        try:
            callback = []
            data_list = request.GET.get('data', None)
            data_loads = json.loads(data_list)
            for i in data_loads:
                instance = api.nova.reallocation(request, i[1], \
                         project=self.kwargs['tenant_id'] , user=i[0])
                callback.append(instance)
            if callback:
                ins = [(i.name, i.id, i.user_id) for i in callback]
                data = request.GET['callback']
                data += '({"success": '+json.dumps(ins)+'})'
        except Exception:
            data = request.GET['callback']+'({"error":"error"})'
        response = HttpResponse(content_type='text/plain')
        response.write(data)
        response.flush()
        return response


class FloatBindingView(forms.ModalFormView): 
    form_class = BindingInstanceForm
    template_name = "admin/projects/binding.html"
    context_object_name = 'binding'
    success_url = reverse_lazy("horizon:admin:projects:index")

    def get_context_data(self, **kwargs):
        context = super(FloatBindingView, self).get_context_data(**kwargs)
        free_instance = []
        self.page_title=self.request.GET.get("page_title", None)
        context['pool_type']=self.request.GET.get("pool_type", None)
        admin_tenant = [us.id for us in self.tenant_list() if us.name == 'admin'][0]
        tenant_name = [t.id for t in self.tenant_list()]
        context['instance'] = self.get_instance()
        for ins in self.get_instance():
            if not ins.tenant_id:
                free_instance.append(ins)
            elif ins.tenant_id not in tenant_name:
                free_instance.append(ins)
            elif ins.tenant_id == admin_tenant:
                free_instance.append(ins)
        context['free_instance'] = sorted(free_instance, key=operator.attrgetter('name'))
        context['tenant'] = self.get_tenant(self.kwargs['tenant_id'])
        context['tenant_id'] = self.kwargs['tenant_id']
        return context

    def get_instance(self):
        instance, has = api.nova.server_list(self.request, search_opts=None, all_tenants=True)
        return instance

    def get_tenant(self, tenant_id=None):
        return api.keystone.tenant_get(self.request, project=tenant_id)

    def tenant_list(self):
        tenant, has = api.keystone.tenant_list(self.request)
        return tenant

    #def get_user(self, tenant_id=None):
    #    return api.keystone.user_list(self.request, project=tenant_id)

    def get_initial(self):
        return {'tenant_id': self.kwargs['tenant_id']}


class CheckFloatInstanceView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):
    
        user_list = []
        instance =[ins.name for ins in \
                   api.nova.server_list(request, all_tenants=True)[0] \
                   if ins.tenant_id==self.kwargs['tenant_id']]
        if not instance:
            result = {"success":"error"}
        else:
            result = {"success":"success"}
        return self.response_method(request, result)

class PoolAjaxView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):

        try:
            instance, has = api.nova.server_list(request, all_tenants=True)
            user_instance = [(i.name, i.id) for i in instance \
                             if i.tenant_id==self.kwargs['tenant_id']]
            data = request.GET['callback']
            data += '({"success": '+json.dumps(user_instance)+'})'
        except Exception:
            data = request.GET['callback']+'({"error":"error"})'
        response = HttpResponse(content_type='text/plain')
        response.write(data)
        response.flush()
        return response

class PoolAddInstanceView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):

        try:
            data = request.GET['callback'] or []
            instance_id = request.GET['add_instance_id']
            instance = api.nova.reallocation(request, instance_id, \
                                project=self.kwargs['tenant_id'] , \
                                user=str(uuid.uuid4()).replace('-',''))
            if instance:
                data +='({"success":"success"})'
        except Exception:
            data +='({"error":"error"})'
        response = HttpResponse(content_type='text/plain')
        response.write(data)
        response.flush()
        return response

class PoolRemoveInstanceView(AjaxIndexView):

    def get(self, request, *args, **kwargs):
    
        try:
            data = request.GET['callback'] or []
            instance_id = request.GET['remove_instance_id']
            tenant, has = api.keystone.tenant_list(request)
            admin_tenant = [t.id for t in tenant if t.name =='admin'][0]
            instance = api.nova.reallocation(request, instance_id, 
                           project=admin_tenant ,\
                           user=str(uuid.uuid4()).replace('-',''))
            if instance:
                data +='({"success":"success"})'
        except Exception:
            data += '({"error":"error"})'
        response = HttpResponse(content_type='text/plain')
        response.write(data)
        response.flush()
        return response

class PoolBindvmAjaxView(AjaxIndexView):

    def get(self, request, *args, **kwargs):

        try:
            callback = []
            data_list = request.GET.get('data', None)
            data_loads = json.loads(data_list)
            for i in data_loads:
                instance = api.nova.reallocation(request, i, \
                               project=self.kwargs['tenant_id'] ,\
                               user=str(uuid.uuid4()).replace('-',''))
                callback.append(instance)
            if callback:
                ins = [(i.name, i.id, i.user_id) for i in callback]
                data = request.GET['callback']+'({"success": '+json.dumps(ins)+'})'
        except Exception:
            data = request.GET['callback']+'({"error":"error"})' or []
        response = HttpResponse(content_type='text/plain')
        response.write(data)
        response.flush()
        return response

class PoolRemoveAjaxView(AjaxIndexView):
    
    def get(self, request, *args, **kwargs):
        
        callback = []
        instance, has = api.nova.server_list(request, all_tenants=True)
        tenant, has = api.keystone.tenant_list(request)
        instance_id = [ins.id for ins in instance if ins.tenant_id == self.kwargs['tenant_id']]
        admin_tenant = [t.id for t in tenant if t.name =='admin'][0]
        for i in instance_id:
            instance = api.nova.reallocation(request, i, \
                           project=admin_tenant, \
                           user=str(uuid.uuid4()).replace('-',''))
            callback.append(instance)
        if callback:
            ins = [(ins.name, ins.id) for ins in callback]
            data = request.GET['callback'] + '({"success": '+json.dumps(ins)+'})'
        response = HttpResponse(content_type='text/plain')
        response.write(data)
        response.flush()
        return response


