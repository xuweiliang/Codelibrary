# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
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

from django.core.urlresolvers import reverse
from django.template.defaultfilters import filesizeformat  # noqa
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa
from django.http import HttpResponseRedirect
from oslo_log import log as logging
import operator
import json
import hashlib
from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import validators

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.images \
    import utils as image_utils
from openstack_dashboard.dashboards.admin.vgpu \
    import utils as instance_utils

LOG = logging.getLogger(__name__)


def _image_choice_title(img):
    gb = filesizeformat(img.size)
    return '%s (%s)' % (img.name or img.id, gb)


class RebuildInstanceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())

    image = forms.ChoiceField(
        label=_("Select Image"),
        widget=forms.ThemableSelectWidget(
            attrs={'class': 'image-selector'},
            data_attrs=('size', 'display-name'),
            transform=_image_choice_title))
    password = forms.RegexField(
        label=_("Rebuild Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_password = forms.CharField(
        label=_("Confirm Rebuild Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))
    disk_config = forms.ThemableChoiceField(label=_("Disk Partition"),
                                            required=False)

    def __init__(self, request, *args, **kwargs):
        super(RebuildInstanceForm, self).__init__(request, *args, **kwargs)
        instance_id = kwargs.get('initial', {}).get('instance_id')
        self.fields['instance_id'].initial = instance_id

        images = image_utils.get_available_images(request,
                                                  request.user.tenant_id)
        choices = [(image.id, image) for image in images]
        if choices:
            choices.insert(0, ("", _("Select Image")))
        else:
            choices.insert(0, ("", _("No images available")))
        self.fields['image'].choices = choices

        if not api.nova.can_set_server_password():
            del self.fields['password']
            del self.fields['confirm_password']

        try:
            if not api.nova.extension_supported("DiskConfig", request):
                del self.fields['disk_config']
            else:
                # Set our disk_config choices
                config_choices = [("AUTO", _("Automatic")),
                                  ("MANUAL", _("Manual"))]
                self.fields['disk_config'].choices = config_choices
        except Exception:
            exceptions.handle(request, _('Unable to retrieve extensions '
                                         'information.'))

    def clean(self):
        cleaned_data = super(RebuildInstanceForm, self).clean()
        if 'password' in cleaned_data:
            passwd = cleaned_data.get('password')
            confirm = cleaned_data.get('confirm_password')
            if passwd is not None and confirm is not None:
                if passwd != confirm:
                    raise forms.ValidationError(_("Passwords do not match."))
        return cleaned_data

    # We have to protect the entire "data" dict because it contains the
    # password and confirm_password strings.
    @sensitive_variables('data', 'password')
    def handle(self, request, data):
        instance = data.get('instance_id')
        image = data.get('image')
        password = data.get('password') or None
        disk_config = data.get('disk_config', None)
        try:
            api.nova.server_rebuild(request, instance, image, password,
                                    disk_config)
            messages.info(request, _('Rebuilding instance %s.') % instance)
        except Exception:
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, _("Unable to rebuild instance."),
                              redirect=redirect)
        return True


class DecryptPasswordInstanceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    _keypair_name_label = _("Key Pair Name")
    _keypair_name_help = _("The Key Pair name that "
                           "was associated with the instance")
    _attrs = {'readonly': 'readonly', 'rows': 4}
    keypair_name = forms.CharField(widget=forms.widgets.TextInput(_attrs),
                                   label=_keypair_name_label,
                                   help_text=_keypair_name_help,
                                   required=False)
    _encrypted_pwd_help = _("The instance password encrypted "
                            "with your public key.")
    encrypted_password = forms.CharField(widget=forms.widgets.Textarea(_attrs),
                                         label=_("Encrypted Password"),
                                         help_text=_encrypted_pwd_help,
                                         required=False)

    def __init__(self, request, *args, **kwargs):
        super(DecryptPasswordInstanceForm, self).__init__(request,
                                                          *args,
                                                          **kwargs)
        instance_id = kwargs.get('initial', {}).get('instance_id')
        self.fields['instance_id'].initial = instance_id
        keypair_name = kwargs.get('initial', {}).get('keypair_name')
        self.fields['keypair_name'].initial = keypair_name
        try:
            result = api.nova.get_password(request, instance_id)
            if not result:
                _unavailable = _("Instance Password is not set"
                                 " or is not yet available")
                self.fields['encrypted_password'].initial = _unavailable
            else:
                self.fields['encrypted_password'].initial = result
                self.fields['private_key_file'] = forms.FileField(
                    label=_('Private Key File'),
                    widget=forms.FileInput())
                self.fields['private_key'] = forms.CharField(
                    widget=forms.widgets.Textarea(),
                    label=_("OR Copy/Paste your Private Key"))
                _attrs = {'readonly': 'readonly'}
                self.fields['decrypted_password'] = forms.CharField(
                    widget=forms.widgets.TextInput(_attrs),
                    label=_("Password"),
                    required=False)
        except Exception:
            redirect = reverse('horizon:admin:vgpu:index')
            _error = _("Unable to retrieve instance password.")
            exceptions.handle(request, _error, redirect=redirect)

    def handle(self, request, data):
        return True


class AttachVolume(forms.SelfHandlingForm):
    volume = forms.ChoiceField(label=_("Volume ID"),
                               help_text=_("Select a volume to attach "
                                           "to this instance."))
    device = forms.CharField(label=_("Device Name"),
                             widget=forms.HiddenInput(),
                             required=False,
                             help_text=_("Actual device name may differ due "
                                         "to hypervisor settings. If not "
                                         "specified, then hypervisor will "
                                         "select a device name."))
    instance_id = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(AttachVolume, self).__init__(*args, **kwargs)

        # Populate volume choices
        volume_list = kwargs.get('initial', {}).get("volume_list", [])
        volumes = []
        for volume in volume_list:
            # Only show volumes that aren't attached to an instance already
            if not volume.attachments:
                volumes.append(
                    (volume.id, '%(name)s (%(id)s)'
                     % {"name": volume.name, "id": volume.id}))
        if volumes:
            volumes.insert(0, ("", _("Select a volume")))
        else:
            volumes.insert(0, ("", _("No volumes available")))
        self.fields['volume'].choices = volumes

    def handle(self, request, data):
        instance_id = self.initial.get("instance_id", None)
        volume_choices = dict(self.fields['volume'].choices)
        volume = volume_choices.get(data['volume'],
                                    _("Unknown volume (None)"))
        volume_id = data.get('volume')

        device = data.get('device') or None

        try:
            attach = api.nova.instance_volume_attach(request,
                                                     volume_id,
                                                     instance_id,
                                                     device)

            message = _('Attaching volume %(vol)s to instance '
                        '%(inst)s on %(dev)s.') % {"vol": volume,
                                                   "inst": instance_id,
                                                   "dev": attach.device}
            messages.info(request, message)
        except Exception:
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request,
                              _('Unable to attach volume.'),
                              redirect=redirect)
        return True


class DetachVolume(forms.SelfHandlingForm):
    volume = forms.ChoiceField(label=_("Volume ID"),
                               help_text=_("Select a volume to detach "
                                           "from this instance."))
    instance_id = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(DetachVolume, self).__init__(*args, **kwargs)

        # Populate instance id
        instance_id = kwargs.get('initial', {}).get("instance_id", None)

        # Populate attached volumes
        try:
            volumes = []
            volume_list = api.nova.instance_volumes_list(self.request,
                                                         instance_id)
            for volume in volume_list:
                volumes.append((volume.id, '%s (%s)' % (volume.name,
                                                        volume.id)))
            if volume_list:
                volumes.insert(0, ("", _("Select a volume")))
            else:
                volumes.insert(0, ("", _("No volumes attached")))

            self.fields['volume'].choices = volumes
        except Exception:
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(self.request, _("Unable to detach volume."),
                              redirect=redirect)

    def handle(self, request, data):
        instance_id = self.initial.get("instance_id", None)
        volume_choices = dict(self.fields['volume'].choices)
        volume = volume_choices.get(data['volume'],
                                    _("Unknown volume (None)"))
        volume_id = data.get('volume')

        try:
            api.nova.instance_volume_detach(request,
                                            instance_id,
                                            volume_id)

            message = _('Detaching volume %(vol)s from instance '
                        '%(inst)s.') % {"vol": volume,
                                        "inst": instance_id}
            messages.info(request, message)
        except Exception:
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request,
                              _("Unable to detach volume."),
                              redirect=redirect)
        return True


class AttachInterface(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    network = forms.ThemableChoiceField(label=_("Network"))

    def __init__(self, request, *args, **kwargs):
        super(AttachInterface, self).__init__(request, *args, **kwargs)
        networks = instance_utils.network_field_data(request,
                                                     include_empty_option=True)
        self.fields['network'].choices = networks

    def handle(self, request, data):
        instance_id = data['instance_id']
        network = data.get('network')
        try:
            api.nova.interface_attach(request, instance_id, net_id=network)
            msg = _('Attaching interface for instance %s.') % instance_id
            messages.success(request, msg)
        except Exception:
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, _("Unable to attach interface."),
                              redirect=redirect)
        return True


class DetachInterface(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    port = forms.ThemableChoiceField(label=_("Port"))

    def __init__(self, request, *args, **kwargs):
        super(DetachInterface, self).__init__(request, *args, **kwargs)
        instance_id = self.initial.get("instance_id", None)

        ports = []
        try:
            ports = api.neutron.port_list(request, device_id=instance_id)
        except Exception:
            exceptions.handle(request, _('Unable to retrieve ports '
                                         'information.'))
        choices = []
        for port in ports:
            ips = []
            for ip in port.fixed_ips:
                ips.append(ip['ip_address'])
            choices.append((port.id, ','.join(ips) or port.id))
        if choices:
            choices.insert(0, ("", _("Select Port")))
        else:
            choices.insert(0, ("", _("No Ports available")))
        self.fields['port'].choices = choices

    def handle(self, request, data):
        instance_id = data['instance_id']
        port = data.get('port')
        try:
            api.nova.interface_detach(request, instance_id, port)
            msg = _('Detached interface %(port)s for instance '
                    '%(instance)s.') % {'port': port, 'instance': instance_id}
            messages.success(request, msg)
        except Exception:
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, _("Unable to detach interface."),
                              redirect=redirect)
        return True

class ReallocationInstanceForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    user_data = forms.CharField(widget=forms.HiddenInput())
    project = forms.ChoiceField(label=_("Project"))
    user = forms.ChoiceField(label=_("User"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(ReallocationInstanceForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        instance_id = initial.get('instance_id')
        data = self.get_user_text()
        #api.nova.cdrom_attach(request, instance_id, 'dev', 'image_id')
        #api.nova.cdrom_list(request, instance_id)
        #LOG.info("cipher =======================%s" % cipher)
        self.fields['instance_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=instance_id)
        self.fields['user_data'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=data)
        self.fields['project'].choices = self.populate_project_choices(request,
                                                                 initial)

        self.fields['user'].choices = self.populate_user_choices(request,
                                                                 initial)

    def populate_project_choices(self, request, initial):
        projects, has_more = api.keystone.tenant_list(self.request)
        choices = [(project.id, project.name) for project in projects if project.name !='services']
        if choices:
            choices.insert(0, ("", _("Select a project")))
        else:
            choices.insert(0, ("", _("No project available.")))
        return sorted(choices, key=operator.itemgetter(1))

    def populate_user_choices(self, request, initial):
        users = api.keystone.user_list(self.request)
        uname = ['nova', 'neutron', 'cinder', 'glance', 'AdminShadow']                 
        choices = [(user.id, user.name) for user in users if user.name not in uname]   
        if choices:
            choices.insert(0, ("", _("Select a user")))
        else:
            choices.insert(0, ("", _("No user available.")))
        return sorted(choices, key=operator.itemgetter(1)) 

    def get_user_text(self):
        list = {}
        json_list = {}
        try:
            projects, has_more = api.keystone.tenant_list(self.request)
            project_all = [(project.id, project.name) for project in projects]
            for p in project_all:
                user_list = [(u.id, u.name)for u in api.keystone.user_list(self.request, p[0])]
                user_list.sort()
                uname = ['nova', 'neutron', 'ceilometer','swift','cinder', 'glance', 'AdminShadow']    
                for u in sorted(user_list, key=operator.itemgetter(1)):         
                    if u[1] not in uname:                             
                        list.setdefault(p[0], [ ]).append(u)
        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve get user data."))
        json_list = json.dumps(list)
        return json_list


    def clean(self):
        cleaned_data = super(ReallocationInstanceForm, self).clean()
        if cleaned_data.get("user_data", None):
            del cleaned_data['user_data']
        return cleaned_data

    def handle(self, request, data):
        try:
            api.nova.reallocation(request,
                              data["instance_id"],
                              data['project'], 
                              data['user'])
            msg = _('Allocation intances .')
            messages.success(request, msg)
        except Exception:
           redirect = reverse('horizon:admin:vgpu:index') 
           exceptions.handle(self.request, _("Unable to allocate instance"))
        return True

class CreateDevsnapshotForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"), required=False)

    def clean(self):
        cleaned_data = super(CreateDevsnapshotForm, self).clean()
        instance_id =  cleaned_data.get('instance_id', None)
        return cleaned_data

    def __init__(self, request, *args, **kwargs):
        super(CreateDevsnapshotForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        instance_id = initial.get('instance_id')

        self.fields['instance_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=instance_id)

    def handle(self, request, data):
        kwargs = {'snapshot':{
                             'instance_id':data['instance_id'],
                             'name':data['name']}}
        try:
            api.nova.create_dev_snapshot(request, **kwargs)
            return HttpResponseRedirect('/dashboard/admin/%s' 
                   % data.get('instance_id', None))
        except Exception as error:
            msg = _('Failed to create dev_snapshot. ')
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, msg, redirect=redirect)

class DeleteDevsnapshotForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"), 
           widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, request, *args, **kwargs):
        super(DeleteDevsnapshotForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        instance_id = initial.get('instance_id')

        self.fields['instance_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=instance_id)
    def handle(self, request, data):

        try:
            api.nova.delete_dev_snapshot(request, data['instance_id'], data['name'])
            msg = _('The snapshot  is successful delete .')
            messages.success(request, msg)
            return HttpResponseRedirect('/dashboard/admin/%s' 
                               % data.get('instance_id', None))
        except Exception:
            msg = _('Failed to delete dev_snapshot. ')
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, msg, redirect=redirect)


class SetDevsnapshotForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"),
           widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, request, *args, **kwargs):
        super(SetDevsnapshotForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        instance_id = initial.get('instance_id')

        self.fields['instance_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=instance_id)
    def handle(self, request, data):

        try:
            api.nova.set_dev_snapshot(request, data['instance_id'], data['name'])
            msg = _('set this devsnapshot for plan devsnapshot .')
            messages.success(request, msg)
            return HttpResponseRedirect('/dashboard/admin/%s'
                               % data.get('instance_id', None))
        except Exception:
            msg = _('Failed to set dev_snapshot. ')
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, msg, redirect=redirect)

class RevertDevsnapshotForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"),
           widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, request, *args, **kwargs):
        super(RevertDevsnapshotForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        instance_id = initial.get('instance_id')

        self.fields['instance_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=instance_id)

    def handle(self, request, data):

        try:
            api.nova.revert_dev_snapshot(request, data['instance_id'], data['name'])
            msg = _('The snapshot  is successful revert.')
            messages.success(request, msg)
            return HttpResponseRedirect('/dashboard/admin/%s'
                               % data.get('instance_id', None))
        except Exception:
            msg = _('Failed to set revert snapshot. ')
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, msg, redirect=redirect)


class CDRomForm(forms.SelfHandlingForm):
    instance_id = forms.CharField(label=_("Instance ID"),
                                  widget=forms.HiddenInput(),
                                  required=False)

    instance_name = forms.CharField(
        label=_("Instance name:"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False,
    )
    devices = forms.ChoiceField(label=_("CDROM Device"),
                               help_text=_("Choose a Device."),required=False)

    images = forms.ChoiceField(label=_("Image name"),
                               help_text=_("Choose a Image to attach."),required=True)

    def __init__(self, *args, **kwargs):
        super(CDRomForm, self).__init__(*args, **kwargs)
        device_list = kwargs.get('initial', {}).get('devices', [])

        iso_list = kwargs.get('initial', {}).get('isos', [])

        isos = []
        isoMap = {}
        for iso in iso_list:
            if iso.disk_format == 'iso':
                isos.append((iso.id, '%s (%s)' % (iso.name,iso.id)))
                fake_iso_id = hashlib.sha1(iso.id).hexdigest()
                isoMap[fake_iso_id] = iso.name
        if isos:
            #isos.insert(len(isos), ("1", _("select the iso")))
            isos.insert(len(isos), ("0", _("Detach the iso")))
        else:
            isos = (("", _("No iso available")),)
        self.fields['images'].choices = isos

        devices = []
        for device in device_list:
            iso_name = device.image_id
            if isoMap.has_key(iso_name):
                iso_name = isoMap[device.image_id]
            devices.append((device.device_name, '%s (%s)' % (device.device_name,iso_name)))
        if devices:
            pass
        else:
            devices = (("", _("No devices available")),)
        self.fields['devices'].choices = devices


    def handle(self, request, data):
        try:
            #snapshot = api.nova.snapshot_create(request,
            #                                    data['instance_id'],
            #                                    data['name'])
            # NOTE(gabriel): This API call is only to display a pretty name.
            instance = api.nova.server_get(request, data['instance_id'])
            vals = {"inst": instance.name,"status":instance.status}
            image_id = data.get('images', '')
            dev = data.get('devices', '')
            if vals['status'] != 'SHUTOFF' and (not data['devices'] or len(data['devices']) == 0):

                messages.error(request, _('Attach ISO error,  '
                                        'instance "%(inst)s" status "%(status)s".It must Shutoff') % vals)
                return True
            else:
                api.nova.cdrom_attach(request, data['instance_id'], dev, image_id)
                if image_id == "0":
                    msg = _('ISO detach successfully.')
                else:
                    msg = _('ISO attach successfully.')
                messages.success(request, msg)
            return True
        except Exception:
            redirect = reverse("horizon:admin:vgpu:index")
            exceptions.handle(request,
                              _('Unable to attach ISO.'),
                              redirect=redirect)

class LiveMigrateForm(forms.SelfHandlingForm):
    current_host = forms.CharField(label=_("Current Host"),
                                   required=False,
                                   widget=forms.TextInput(
                                       attrs={'readonly': 'readonly'}))
    host = forms.ChoiceField(label=_("New Host"),
                             help_text=_("Choose a Host to migrate to."))
    disk_over_commit = forms.BooleanField(label=_("Disk Over Commit"),
                                          initial=False, required=False)
    block_migration = forms.BooleanField(label=_("Block Migration"),
                                         initial=False, required=False)

    def __init__(self, request, *args, **kwargs):
        super(LiveMigrateForm, self).__init__(request, *args, **kwargs)
        initial = kwargs.get('initial', {})
        instance_id = initial.get('instance_id')
        self.fields['instance_id'] = forms.CharField(widget=forms.HiddenInput,
                                                     initial=instance_id)
        self.fields['host'].choices = self.populate_host_choices(request,
                                                                 initial)

    def populate_host_choices(self, request, initial):
        hosts = initial.get('hosts')
        current_host = initial.get('current_host')
        host_list = [(host.host_name,
                      host.host_name)
                     for host in hosts
                     if host.service.startswith('compute') and
                         host.host_name != current_host]
        if host_list:
            host_list.insert(0, ("", _("Select a new host")))
        else:
            host_list.insert(0, ("", _("No other hosts available.")))
        return sorted(host_list)

    def handle(self, request, data):
        try:
            block_migration = data['block_migration']
            disk_over_commit = data['disk_over_commit']
            api.nova.server_live_migrate(request,
                                         data['instance_id'],
                                         data['host'],
                                         block_migration=block_migration,
                                         disk_over_commit=disk_over_commit)
            msg = _('The instance is preparing the live migration '
                    'to host "%s".') % data['host']
            messages.success(request, msg)
            return True
        except Exception:
            msg = _('Failed to live migrate instance to '
                    'host "%s".') % data['host']
            redirect = reverse('horizon:admin:vgpu:index')
            exceptions.handle(request, msg, redirect=redirect)
