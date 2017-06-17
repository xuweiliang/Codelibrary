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

import json
import re
from django.utils.translation import ugettext_lazy as _

from horizon import messages
from horizon import exceptions
from horizon import forms
from horizon import workflows
import logging
from openstack_dashboard import api
from openstack_dashboard.utils import filters

from openstack_dashboard.dashboards.admin.instances \
    import utils as instance_utils
LOG = logging.getLogger(__name__)

INDEX_URL = "horizon:admin:instances:index"
ADD_USER_URL = "horizon:admin:instances:create_user"
INSTANCE_SEC_GROUP_SLUG = "update_security_groups"


class UpdateInstanceSecurityGroupsAction(workflows.MembershipAction):
    def __init__(self, request, *args, **kwargs):
        super(UpdateInstanceSecurityGroupsAction, self).__init__(request,
                                                                 *args,
                                                                 **kwargs)
        err_msg = _('Unable to retrieve security group list. '
                    'Please try again later.')
        context = args[0]
        instance_id = context.get('instance_id', '')

        default_role_name = self.get_default_role_field_name()
        self.fields[default_role_name] = forms.CharField(required=False)
        self.fields[default_role_name].initial = 'member'

        # Get list of available security groups
        all_groups = []
        try:
            all_groups = api.network.security_group_list(request)
        except Exception:
            exceptions.handle(request, err_msg)
        groups_list = [(group.id, group.name) for group in all_groups]

        instance_groups = []
        try:
            instance_groups = api.network.server_security_groups(request,
                                                                 instance_id)
        except Exception:
            exceptions.handle(request, err_msg)
        field_name = self.get_member_field_name('member')
        self.fields[field_name] = forms.MultipleChoiceField(required=False)
        self.fields[field_name].choices = groups_list
        self.fields[field_name].initial = [group.id
                                           for group in instance_groups]

    def handle(self, request, data):
        instance_id = data['instance_id']
        wanted_groups = map(filters.get_int_or_uuid, data['wanted_groups'])
        try:
            api.network.server_update_security_groups(request, instance_id,
                                                      wanted_groups)
        except Exception as e:
            exceptions.handle(request, str(e))
            return False
        return True

    class Meta(object):
        name = _("Security Groups")
        slug = INSTANCE_SEC_GROUP_SLUG


class UpdateInstanceSecurityGroups(workflows.UpdateMembersStep):
    action_class = UpdateInstanceSecurityGroupsAction
    help_text = _("Add and remove security groups to this instance "
                  "from the list of available security groups.")
    available_list_title = _("All Security Groups")
    members_list_title = _("Instance Security Groups")
    no_available_text = _("No security groups found.")
    no_members_text = _("No security groups enabled.")
    show_roles = False
    depends_on = ("instance_id",)
    contributes = ("wanted_groups",)

    def contribute(self, data, context):
        request = self.workflow.request
        if data:
            field_name = self.get_member_field_name('member')
            context["wanted_groups"] = request.POST.getlist(field_name)
        return context


class UpdateInstanceInfoAction(workflows.Action):
    name = forms.CharField(label=_("Name"),
                           max_length=255)

    usb_control = forms.BooleanField(label=_("Whether to change the USB"), required=False)
    spice_secure = forms.BooleanField(label=_("Spice Secure"), required=False)
    clipboard_control = forms.BooleanField(label=_("Whether to allow access Clipboard"), required=False)
    screen = forms.ChoiceField(label=_("The number of the screen"), initial="populate_screen.num", 
                                required=False, choices=[(1, _('1')), (2, _('2')), (4, _('4'))])

    quatity_control = forms.ChoiceField(label=_("Quatity"),
                                        initial="populate_quatity_control",
                                        required=False,
                                        choices=[("low", _('Low')),
                                        ("high", _('High'))])

    multi_user= forms.ChoiceField(label=_('Multi user connection'),
                                                required=False,
                                                choices=[("on", _("Yes")),("off",_("No"))])

    broadcast = forms.BooleanField(label=_("Allow Screen Broadcast"), required=False)

    jostle = forms.ChoiceField(label=_("Desktop Mode"),
                       required=False,
                       help_text=_("Choose a desktop model"),
                       choices=[("single", _('Desktop Not snatch')),
                             ("shared", _('Desktop snatch'))])

    during = forms.ChoiceField(label=_("Persistent Mode"),
                       required=False,
                       help_text=_("Choose a persistent mode"),
                       choices=[("immobilization", _('Permanent')),
                             ("variable", _('Non Durable'))])

    per = forms.ChoiceField(label=_("Per"),
                    required=False)

    day_id = forms.ChoiceField(label=_("Day"),
                               required=False)

    week_id = forms.ChoiceField(label=_("Week"),
                                required=False)

    month_id = forms.CharField(label=_("Month"),
                               required=False,
                               max_length=255)

    def __init__(self, request, context, *args, **kwargs):
        super(UpdateInstanceInfoAction, self).__init__(request, context, *args, **kwargs)
        LOG.info("kwargs =====================%s" % kwargs)
        per_choices= [("day_id", _('Day')),
                      ("week_id", _('Week')),
                      ("month_id", _('Month'))]

        day_id_choices = [('None', _("None"))]
        week_id_choices = [('monday', _("Monday")),
                           ("tuesday", _('Tuesday')),
                           ("wednesday", _('Wednesday')),
                           ("thursday", _('Thursday')),
                           ("friday", _('Friday')),
                           ("saturday", _('Saturday')),
                           ("sunday", _('Sunday'))]
        self.fields['per'].choices = per_choices
        self.fields['day_id'].choices = day_id_choices
        self.fields['week_id'].choices = week_id_choices        
        try:
            control = api.nova.get_object_info(request, context.get('instance_id'))
            spice_secure = api.nova.get_spice_secure(request, context.get('instance_id'))
            self.fields['usb_control'].initial = control.get('usb')
            self.fields['spice_secure'].initial = spice_secure.get('spice_secure')
            self.fields['clipboard_control'].initial = control.get('clipboard')
            self.fields['screen'].initial = control.get('screen')
            if control.get('quatity_control')==True:
                self.fields['quatity_control'].initial = "low"
            else:
                self.fields['quatity_control'].initial = "high"
    
            self.fields['multi_user'].initial = control.get('multi_user')
            self.fields['broadcast'].initial = control.get('allow_screen_broadcast')
            if control.get('jostle') == True:
                self.fields['jostle'].initial = "single"
            else:
                self.fields['jostle'].initial = "shared"
            self.fields['during'].initial = control.get('during')
    
            #about the dev_time for the original value
            self.fields['per'].initial = control.get('per')
            b = control.get('dev_time')
            if control.get('per') == 'None':
                self.fields['day_id'].initial = 'None'
                self.fields['week_id'].initial = 'None'
                self.fields['month_id'].initial = 'None'
            elif control.get('per') == 'day_id':
                self.fields['day_id'].initial = control.get('dev_time')
                self.fields['week_id'].initial = 'None'
                self.fields['month_id'].initial = 'None'
            elif control.get('per') == 'week_id':
                self.fields['week_id'].initial = control.get('dev_time')
                self.fields['day_id'].initial = 'None'
                self.fields['month_id'].initial = 'None'
            else:
                self.fields['month_id'].initial = control.get('dev_time')
                self.fields['day_id'].initial = 'None'
                self.fields['week_id'].initial = 'None'

        except Exception:
            exceptions.handle(request, _('Unable to retrieve extensions'
                                         'information.'))
    class Meta(object):
        name = _("Information")
        slug = 'instance_info'
        help_text = _("Edit the instance details.")

    def clean(self):
        cleaned_data = super(UpdateInstanceInfoAction, self).clean()
        month_id = cleaned_data.get('month_id', 1)
        per = cleaned_data.get('per')
        if per == "month_id":
            p = re.compile('^([1-9]|[12]\d|3[01])$',re.S)
            if month_id:
                if p.match(month_id):
                    pass
                else:
                    error_message = _('Set the maximum reduction date\
                           than the date of each month, please reset')
                    raise forms.ValidationError(error_message)
        else:
            pass
        return cleaned_data

    def handle(self, request, data):
        LOG.info("data =====================%s" % data)
#        try:
#            api.nova.server_update(request,
#                                   data['instance_id'],
#                                   data['name'],
#                                   data['terminal'])
#        except Exception:
#            exceptions.handle(request, ignore=True)
#            return False
        return True


class UpdateInstanceResourceAction(workflows.Action):

    old_flavor_id = forms.CharField(required=False, widget=forms.HiddenInput())
    old_flavor_name = forms.CharField(
        label=_("Old Flavor"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False,
    )

    flavor = forms.ChoiceField(label=_("New Flavor"), required=False,
                               help_text=_("Choose the flavor to resize."))

    def __init__(self, request, context, *args, **kwargs):
        self.context=context
        super(UpdateInstanceResourceAction, self).__init__(request, context, *args, **kwargs)
        try:
            instance = api.nova.server_get(self.request, context['instance_id'])
            flavors = api.nova.flavor_get(self.request, instance.flavor['id'])
            self.fields['old_flavor_id'].initial = flavors.id
            self.fields['old_flavor_name'].initial = flavors.name
        except Exception:
            exceptions.handle(request, ignore=True)

    def populate_flavor_choices(self, request, context):
        flavors = api.nova.flavor_list(request)
        if len(flavors) > 1:
            flavors = instance_utils.sort_flavor_list(request, flavors)
        if flavors:
            flavors.insert(0, ("", _("Select a New Flavor")))
        else:
            flavors.insert(0, ("", _("No flavors available")))
        return flavors

    def get_help_text(self):
        extra = {}
        try:
            extra['usages'] = api.nova.tenant_absolute_limits(self.request)
            extra['usages_json'] = json.dumps(extra['usages'])
            flavors = json.dumps([f._info for f in
                                  instance_utils.flavor_list(self.request)])
            extra['flavors'] = flavors
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve quota information."))
        return super(UpdateInstanceResourceAction, self).get_help_text(extra)

    def clean(self):
        cleaned_data = super(UpdateInstanceResourceAction, self).clean()
        flavor = cleaned_data.get('flavor', None)
        if flavor is None or flavor == cleaned_data['old_flavor_id']:
            raise forms.ValidationError(_('Please choose a new flavor that '
                                          'is not the same as the old one.'))
        return cleaned_data

    def handle(self, request, data):
        try:
            if data['flavor']:
                #snapshot = api.nova.dev_snapshot_list(request, data['instance_id'])
                snapshot = None
                if not snapshot and data.get("flavor"):
                    api.nova.server_resize(request, data['instance_id'],
                         data['flavor'], data.get("disk_config", "AUTO"))
                else:
                    if snapshot:
                        raise
                    pass
            else:
                pass
        except Exception:
            messages.error(request, _("Can not resize the instance when the devsnapshot exist."))
            return False
        return True

    class Meta:
        name = _("Resource")
        slug = 'instance_resource'
        help_text_template = ("admin/instances/"
                              "_flavors_and_quotas.html")

class UpdateInstanceInfo(workflows.Step):
    action_class = UpdateInstanceInfoAction
    depends_on = ("instance_id",)
    contributes = ("name","usb_control","spice_secure",
                   "clipboard_control","screen", "quatity_control",
                   "multi_user", 'broadcast',"jostle", "during",
                   "per","dev_time","day_id","week_id","month_id",)
    LOG.info("sskkk ================================")

    def contribute(self, data, context):
        LOG.info("sskkk =================================%s" % data)
        if data:
            param = dict()
            param['usb_control']=data.get("usb_control", None)
            param['spice_secure']=data.get("spice_secure", None)
            param['clipboard_control']=data.get("clipboard_control", None)
            param['screen']=data.get("screen", None)
            if data.get("quatity_control") == "low":
                param['quatity_control'] = True
            else:
                param['quatity_control']= False

            param['multi_user']=data.get("multi_user", None)
            allow_screen_broadcast = data.get("broadcast", "")
            if param['multi_user'] != "on":
                allow_screen_broadcast = False
            param['allow_screen_broadcast']=allow_screen_broadcast

            desktop_mode = data.get("jostle","")
            if desktop_mode == "single":
                param['jostle'] = True
            else:
                param['jostle'] = False
            param['during']=data.get("during", None)
            param['per'] = data.get("per","")

            if param['during'] == "immobilization":
                param['per'] =  None;
            a = param['per']
            if a == 'day_id':
                param['dev_time'] = None
            elif a == "week_id":
                param['dev_time'] = data.get("week_id",None)
            elif a == "month_id":
                param['dev_time'] = data.get["month_id",None]
                if param['dev_time'] == "":
                    param['dev_time'] = 1
            context['terminal']=[param]
        return context



class UpdateInstanceResource(workflows.Step):
    action_class = UpdateInstanceResourceAction
    depends_on = ("instance_id",)
    contributes = ("old_flavor_id", "old_flavor_name", "flavors", "flavor", "disk_config")

class SetNetworkAction(workflows.Action):

    network = forms.MultipleChoiceField(
        label=_("Networks"),
        widget=forms.ThemableCheckboxSelectMultiple(),
        error_messages={
            'required': _(
                "At least one network must"
                " be specified.")},
        help_text=_("Update instance with"
                    " these networks"))
    if api.neutron.is_port_profiles_supported():
        widget = None
    else:
        widget = forms.HiddenInput()
    profile = forms.ChoiceField(label=_("Policy Profiles"),
                                required=False,
                                widget=widget,
                                help_text=_("Update instance with "
                                            "this policy profile"))

    def __init__(self, request, *args, **kwargs):
        super(SetNetworkAction, self).__init__(request, *args, **kwargs)
        network_list = self.fields["network"].choices
        if len(network_list) == 1:
            self.fields['network'].initial = [network_list[0][0]]
        if api.neutron.is_port_profiles_supported():
            self.fields['profile'].choices = (
                self.get_policy_profile_choices(request))

    class Meta(object):
        name = _("Networking")
        permissions = ('openstack.services.network',)
        help_text = _("Select networks for your instance.")

    def populate_network_choices(self, request, context):
        return instance_utils.network_field_data(request)

    def get_policy_profile_choices(self, request):
        profile_choices = [('', _("Select a profile"))]
        for profile in self._get_profiles(request, 'policy'):
            profile_choices.append((profile.id, profile.name))
        return profile_choices

    def _get_profiles(self, request, type_p):
        profiles = []
        try:
            profiles = api.neutron.profile_list(request, type_p)
        except Exception:
            msg = _('Network Profiles could not be retrieved.')
            exceptions.handle(request, msg)
        return profiles


    def handle(self, request, context):
        instance_id = context.get('instance_id','')
        netids = context.get('network_id', None)
        #net_ids = []
        #port_ids = []
        nets = []
        interfaces = api.nova.interfaces_list(request,instance_id)
        avi_nets = []
        LOG.info("interfaces ========================%s" % interfaces)
#        try:
#            for interface in interfaces:
#                port_id = getattr(interface, 'port_id')
#                net_id = getattr(interface, 'net_id')
#                nets.append((net_id,port_id))
#                if net_id not in netids:
#
#                    api.nova.interface_detach(request,instance_id,port_id=port_id)
#                else:
#                    avi_nets.append(net_id)
#            for net in netids:
#                if net not in avi_nets:
#                    api.nova.interfaces_attach(request,instance_id,port_id=None,net_id=net,fixed_ip=None)
#
#        except Exception:
#            msg = _('Network update error.')
#            exceptions.handle(request, msg)

class SetNetwork(workflows.Step):
    action_class = SetNetworkAction
    if api.neutron.is_port_profiles_supported():
        contributes = ("network_id", "profile_id",)
    else:
        template_name = "admin/instances/_update_networks.html"
        contributes = ("network_id",)

    def contribute(self, data, context):
        if data:
            networks = self.workflow.request.POST.getlist("network")
            # If no networks are explicitly specified, network list
            # contains an empty string, so remove it.
            networks = [n for n in networks if n != '']
            if networks:
                context['network_id'] = networks

            if api.neutron.is_port_profiles_supported():
                context['profile_id'] = data.get('profile', None)
        return context


class UpdateInstanceInfo(workflows.Step):
    action_class = UpdateInstanceInfoAction
    depends_on = ("instance_id",)
    contributes = ("name",)


class UpdateInstance(workflows.Workflow):
    slug = "update_instance"
    name = _("Edit Instance")
    finalize_button_name = _("Save")
    success_message = _('Modified instance "%s".')
    failure_message = _('Unable to modify instance "%s".')
    success_url = "horizon:admin:instances:index"
    default_steps = (UpdateInstanceInfo,\
                     UpdateInstanceSecurityGroups)
                     #SetNetwork)

    def format_status_message(self, message):
        return message % self.context.get('name', 'unknown instance')


# NOTE(kspear): nova doesn't support instance security group management
#               by an admin. This isn't really the place for this code,
#               but the other ways of special-casing this are even messier.
class AdminUpdateInstance(UpdateInstance):
    success_url = "horizon:admin:instances:index"
    default_steps = (UpdateInstanceInfo,)
