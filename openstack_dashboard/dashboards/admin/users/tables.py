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

from django.template import defaultfilters
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import forms
from horizon import tables
from openstack_dashboard import api
from openstack_dashboard import policy
from openstack_dashboard import record_action
ENABLE = 0
DISABLE = 1
KEYSTONE_V2_ENABLED = api.keystone.VERSIONS.active < 3


class CreateUserLink(tables.LinkAction):
    name = "create"
    verbose_name = _("Create User")
    url = "horizon:admin:users:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (('admin', 'admin:create_grant'),
                    ("admin", "admin:create_user"),
                    ("admin", "admin:list_roles"),
                    ("admin", "admin:list_projects"),)

    def allowed(self, request, user):
        return api.keystone.keystone_can_edit_user()


class EditUserLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit")
    url = "horizon:admin:users:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("admin", "admin:update_user"),
                    ("admin", "admin:list_projects"),)
    policy_target_attrs = (("user_id", "id"),)

    def allowed(self, request, user):
        return api.keystone.keystone_can_edit_user()


class ToggleEnabled(policy.PolicyTargetMixin, tables.BatchAction):
    name = "toggle"

    @staticmethod
    def action_present(count):
        return (
            ungettext_lazy(
                u"Enable User",
                u"Enable Users",
                count
            ),
            ungettext_lazy(
                u"Disable User",
                u"Disable Users",
                count
            ),
        )

    @staticmethod
    def action_past(count):
        return (
            ungettext_lazy(
                u"Enabled User",
                u"Enabled Users",
                count
            ),
            ungettext_lazy(
                u"Disabled User",
                u"Disabled Users",
                count
            ),
        )
    classes = ("btn-toggle",)
    policy_rules = (("admin", "admin:update_user"),)
    policy_target_attrs = (("user_id", "id"),)

    def allowed(self, request, user=None):
        if not api.keystone.keystone_can_edit_user():
            return False

        self.enabled = True
        if not user:
            return self.enabled
        self.enabled = user.enabled
        if self.enabled:
            self.current_present_action = DISABLE
        else:
            self.current_present_action = ENABLE
        return True

    def update(self, request, user=None):
        super(ToggleEnabled, self).update(request, user)
        if user and user.id == request.user.id:
            self.attrs["disabled"] = "disabled"

    def action(self, request, obj_id):
        user_data = api.keystone.user_get(request, obj_id)
        if obj_id == request.user.id:
            msg =  _('You cannot disable the user you are '
                     'currently logged in as.')
            messages.info(request, msg)
            api.nova.systemlogs_create(request, user_data.name, 
                record_action.TOGGLEUSER, result=False, detail=msg)
            return
        if self.enabled:
            api.keystone.user_update_enabled(request, obj_id, False)
            self.current_past_action = DISABLE
            flag = 'Disable '
        else:
            api.keystone.user_update_enabled(request, obj_id, True)
            self.current_past_action = ENABLE
            flag = 'Enable '
        objectname = flag + 'User'
        api.nova.systemlogs_create(request, user_data.name, 
                        objectname, result=True, detail='-')


class DeleteUsersAction(policy.PolicyTargetMixin, tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete User",
            u"Delete Users",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted User",
            u"Deleted Users",
            count
        )
    policy_rules = (("admin", "admin:delete_user"),)

    def allowed(self, request, datum):
        SystemName=['glance', 'cinder', 'neutron', 'nova', 'admin', request.user.username]
        self.result = True
        self.detail = '-'
        if datum is not None and datum.name in SystemName:
            self.result = False
            self.detail = _("Cannot allowed to delete user")
            #if not api.keystone.keystone_can_edit_user() or \
            #        (datum and datum.id == request.user.id):
            #    return False
            return False
        return True

    def delete(self, request, obj_id):
        user_data = api.keystone.user_get(request, obj_id)
        api.keystone.user_delete(request, obj_id)


class UserFilterAction(tables.FilterAction):
    def filter(self, table, users, filter_string):
        """Naive case-insensitive search."""
        q = filter_string.lower()
        return [user for user in users
                if q in user.name.lower()]
#    if api.keystone.VERSIONS.active < 3:
#        filter_type = "query"
#    else:
#        filter_type = "server"
#        filter_choices = (("name", _("User Name ="), True),
#                          ("id", _("User ID ="), True),
#                          ("enabled", _("Enabled ="), True, _('e.g. Yes/No')))


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, user_id):
        user_info = api.keystone.user_get(request, user_id, admin=True)
        return user_info


class UsersTable(tables.DataTable):
    STATUS_CHOICES = (
        ("true", True),
        ("false", False)
    )
    name = tables.Column('name', verbose_name=_('User Name'))
    email = tables.Column('email', verbose_name=_('Email'),
                          filters=(lambda v: defaultfilters
                                   .default_if_none(v, ""),
                                   defaultfilters.escape,
                                   defaultfilters.urlize)
                          )
    # Default tenant is not returned from Keystone currently.
    # default_tenant = tables.Column('default_tenant',
    #                               verbose_name=_('Default Project'))
    #id = tables.Column('id', verbose_name=_('User ID'))
    enabled = tables.Column('enabled', verbose_name=_('Enabled'),
                            status=True,
                            status_choices=STATUS_CHOICES,
                            filters=(defaultfilters.yesno,
                                     defaultfilters.capfirst),
                            empty_value="False")

    if api.keystone.VERSIONS.active >= 3:
        domain_name = tables.Column('domain_name',
                                    verbose_name=_('Domain Name'),
                                    attrs={'data-type': 'uuid'})

    class Meta(object):
        name = "users"
        verbose_name = _("Users")
        row_actions = (EditUserLink, ToggleEnabled, DeleteUsersAction)
        table_actions = (UserFilterAction, CreateUserLink, DeleteUsersAction)
        row_class = UpdateRow
