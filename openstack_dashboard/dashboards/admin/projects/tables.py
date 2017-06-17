# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.core.urlresolvers import reverse
from django.template import defaultfilters as filters
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.utils.translation import pgettext_lazy
from horizon import forms
from horizon import tables

from openstack_dashboard import api
from openstack_dashboard import policy
from openstack_dashboard.usage import quotas
from oslo_log import log as logging
LOG = logging.getLogger(__name__)


class RescopeTokenToProject(tables.LinkAction):
    name = "rescope"
    verbose_name = _("Set as Active Project")
    url = "switch_tenants"

    def allowed(self, request, project):
        # allow rescoping token to any project the user has a role on,
        # authorized_tenants, and that they are not currently scoped to
        return next((True for proj in request.user.authorized_tenants
                     if proj.id == project.id and
                     project.id != request.user.project_id and
                     project.enabled), False)

    def get_link_url(self, project):
        # redirects to the switch_tenants url which then will redirect
        # back to this page
        dash_url = reverse("horizon:admin:projects:index")
        base_url = reverse(self.url, args=[project.id])
        param = urlencode({"next": dash_url})
        return "?".join([base_url, param])


class UpdateMembersLink(tables.LinkAction):
    name = "users"
    verbose_name = _("Manage Members")
    url = "horizon:admin:projects:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("identity", "identity:list_users"),
                    ("identity", "identity:list_roles"))

    def get_link_url(self, project):
        step = 'update_members'
        base_url = reverse(self.url, args=[project.id])
        param = urlencode({"step": step})
        return "?".join([base_url, param])

    def allowed(self, request, project):
        if api.keystone.is_multi_domain_enabled():
            # domain admin or cloud admin = True
            # project admin or member = False
            return api.keystone.is_domain_admin(request)
        else:
            return super(UpdateMembersLink, self).allowed(request, project)


class UpdateGroupsLink(tables.LinkAction):
    name = "groups"
    verbose_name = _("Modify Groups")
    url = "horizon:admin:projects:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("identity", "identity:list_groups"),)

    def allowed(self, request, project):
        if api.keystone.is_multi_domain_enabled():
            # domain admin or cloud admin = True
            # project admin or member = False
            return api.keystone.is_domain_admin(request)
        else:
            return super(UpdateGroupsLink, self).allowed(request, project)

    def get_link_url(self, project):
        step = 'update_group_members'
        base_url = reverse(self.url, args=[project.id])
        param = urlencode({"step": step})
        return "?".join([base_url, param])


class UsageLink(tables.LinkAction):
    name = "usage"
    verbose_name = _("View Usage")
    url = "horizon:admin:projects:usage"
    icon = "stats"
    policy_rules = (("compute", "compute_extension:simple_tenant_usage:show"),)

    def allowed(self, request, project):
        return (request.user.is_superuser and
                api.base.is_service_enabled(request, 'compute'))

class BindingInstance(tables.LinkAction):
    name = "binding"
    verbose_name = _("Binding Instance")
    classes = ("ajax-modal",)
    
    def allowed(self, request, project): 
        if hasattr(project, "pool_type"):
            pool_type = getattr(project, "pool_type")
            if pool_type== "float":
                self.verbose_name=_("Float Pool")
                return True
            elif pool_type == "dedicated":
                self.verbose_name=_("Dedicated Pool")
                return True
        if getattr(project, 'name') in ['admin','services']:
            return False
        return False

    def get_link_url(self, datum):
        pool_type = getattr(datum, "pool_type", None)
        path_name = '_'.join([pool_type, self.name])
        title = urlencode({"page_title":self.verbose_name})
        binding_type = urlencode({"pool_type": pool_type})
        param = '&'.join([title, binding_type])
        _request = '?'.join([path_name, param])
        next_url = '/'.join([self.table.get_object_id(datum), _request])
        LOG.info("project =====================%s", param)
        LOG.info("next_url =====================%s", next_url)
        return next_url


class CreateProject(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Project")
    url = "horizon:admin:projects:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (('identity', 'identity:create_project'),)

    def allowed(self, request, project):
        if api.keystone.is_multi_domain_enabled():
            # domain admin or cloud admin = True
            # project admin or member = False
            return api.keystone.is_domain_admin(request)
        else:
            return api.keystone.keystone_can_edit_project()


class UpdateProject(policy.PolicyTargetMixin, tables.LinkAction):
    name = "update"
    verbose_name = _("Edit Project")
    url = "horizon:admin:projects:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (('identity', 'identity:update_project'),)
    policy_target_attrs = (("target.project.domain_id", "domain_id"),)

    def allowed(self, request, project):
        if api.keystone.is_multi_domain_enabled():
            # domain admin or cloud admin = True
            # project admin or member = False
            return api.keystone.is_domain_admin(request)
        else:
            return api.keystone.keystone_can_edit_project()


class ModifyQuotas(tables.LinkAction):
    name = "quotas"
    verbose_name = _("Modify Quotas")
    url = "horizon:admin:projects:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (('compute', "compute_extension:quotas:update"),)

    def allowed(self, request, datum):
        if api.keystone.VERSIONS.active < 3:
            return True
        else:
            return (api.keystone.is_cloud_admin(request) and
                    quotas.enabled_quotas(request))

    def get_link_url(self, project):
        step = 'update_quotas'
        base_url = reverse(self.url, args=[project.id])
        param = urlencode({"step": step})
        return "?".join([base_url, param])


class DeleteTenantsAction(policy.PolicyTargetMixin, tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Project",
            u"Delete Projects",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Project",
            u"Deleted Projects",
            count
        )

    policy_rules = (("identity", "identity:delete_project"),)
    policy_target_attrs = ("target.project.domain_id", "domain_id"),

    def allowed(self, request, project):
        if api.keystone.is_multi_domain_enabled() \
                and not api.keystone.is_domain_admin(request):
            return False
        if project and project.name in ['services', 'admin']:
            return False
        return api.keystone.keystone_can_edit_project()

    def delete(self, request, obj_id):
        sysProject = [p.name for p in self.table.data if p.id == obj_id][-1]
        if sysProject in [u'services', u'admin']:
            return 
        api.keystone.tenant_delete(request, obj_id)

    def handle(self, table, request, obj_ids):
        response = \
            super(DeleteTenantsAction, self).handle(table, request, obj_ids)
        return response


class TenantFilterAction(tables.FilterAction):

    def filter(self, table, tenants, filter_string):
        """Really naive case-insensitive search."""
        q = filter_string.lower()

        def comp(tenant):
            if q in tenant.name.lower():
                return True
            return False

        return filter(comp, tenants)

#    if api.keystone.VERSIONS.active < 3:
#        filter_type = "query"
#    else:
#        filter_type = "server"
#        filter_choices = (('name', _("Project Name ="), True),
#                          ('id', _("Project ID ="), True),
#                          ('enabled', _("Enabled ="), True, _('e.g. Yes/No')))


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, project_id):
        project_info = api.keystone.tenant_get(request, project_id,
                                               admin=True)
        return project_info


class TenantsTable(tables.DataTable):
    POOL_TYPE_DISPLAY_CHOICES=(
        ("float", pgettext_lazy("Pool Type of an display", u"Float")),
        ("dedicated", pgettext_lazy("Pool Type of an display", u"Dedicated"))
    )
    name = tables.WrappingColumn('name', verbose_name=_('Name'),
                                 link=("horizon:admin:projects:belongs"),
                                 form_field=forms.CharField(max_length=64))
    description = tables.Column(lambda obj: getattr(obj, 'description', None),
                                verbose_name=_('Description'),
                                form_field=forms.CharField(
                                    widget=forms.Textarea(attrs={'rows': 4}),
                                    required=False))
    id = tables.Column('id', verbose_name=_('Project ID'))
    pool_type = tables.Column('pool_type', verbose_name=_('Pool Type'),
                              display_choices=POOL_TYPE_DISPLAY_CHOICES)
    #if api.keystone.VERSIONS.active >= 3:
    #    domain_name = tables.Column(
    #        'domain_name', verbose_name=_('Domain Name'))

    enabled = tables.Column('enabled', verbose_name=_('Enabled'), status=True,
                            filters=(filters.yesno, filters.capfirst),
                            form_field=forms.BooleanField(
                                label=_('Enabled'),
                                required=False))

#    def get_project_detail_link(self, project):
#        # this method is an ugly monkey patch, needed because
#        # the column link method does not provide access to the request
#        if policy.check((("identity", "identity:get_project"),),
#                        self.request, target={"project": project}):
#            #return reverse("horizon:admin:projects:detail",
#            return reverse("horizon:admin:instances:index",
#                           args=(project.id,))
#        return None
#
#    def __init__(self, request, data=None, needs_form_wrapper=None, **kwargs):
#        super(TenantsTable,
#              self).__init__(request, data=data,
#                             needs_form_wrapper=needs_form_wrapper,
#                             **kwargs)
#        # see the comment above about ugly monkey patches
#        #self.columns['name'].get_link_url = self.get_project_detail_link
#        self.columns['name'].get_link_url = reverse("horizon:admin:instances:index")

    class Meta(object):
        name = "tenants"
        verbose_name = _("Projects")
        row_class = UpdateRow
        row_actions = (UpdateMembersLink, UpdateGroupsLink, 
                       UpdateProject,ModifyQuotas, DeleteTenantsAction,
                       UsageLink, BindingInstance, #ModifyQuotas, DeleteTenantsAction,
                       RescopeTokenToProject)
        table_actions = (TenantFilterAction, CreateProject,
                         DeleteTenantsAction)
        pagination_param = "tenant_marker"
