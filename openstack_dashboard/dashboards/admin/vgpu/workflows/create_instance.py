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
import logging
import operator
import re

from oslo_utils import units
import six
import datetime

from django.template.defaultfilters import filesizeformat  # noqa
from django.utils.text import normalize_newlines  # noqa
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.views.decorators.debug import sensitive_variables  # noqa

from horizon import exceptions
from horizon import messages
from horizon import forms
from horizon.utils import functions
from horizon.utils import memoized
from horizon.utils import validators
from horizon import workflows

from openstack_dashboard import api
from openstack_dashboard.api import base
from openstack_dashboard.api import cinder
from openstack_dashboard.api import nova
from openstack_dashboard.usage import quotas

from openstack_dashboard.dashboards.admin.images \
    import utils as image_utils
from openstack_dashboard.dashboards.admin.vgpu \
    import utils as instance_utils


LOG = logging.getLogger(__name__)


class SelectProjectUserAction(workflows.Action):
    project_id = forms.ThemableChoiceField(label=_("Project"))
    user_id = forms.ThemableChoiceField(label=_("User"))

    def __init__(self, request, *args, **kwargs):
        super(SelectProjectUserAction, self).__init__(request, *args, **kwargs)
        # Set our project choices
        projects = [(tenant.id, tenant.name)
                    for tenant in request.user.authorized_tenants]
        self.fields['project_id'].choices = projects

        # Set our user options
        users = [(request.user.id, request.user.username)]
        self.fields['user_id'].choices = users

    class Meta(object):
        name = _("Project & User")
        # Unusable permission so this is always hidden. However, we
        # keep this step in the workflow for validation/verification purposes.
        permissions = ("!",)


class SelectProjectUser(workflows.Step):
    action_class = SelectProjectUserAction
    contributes = ("project_id", "user_id")

class TerminalControlAction(workflows.Action):
    TIME_ZONE_CHOICES = (
        ("utc", _("UTC")),
        ("localtime", _("Localtime")))
    time_zone = forms.ChoiceField(label=_("Instance Time Zone"),
                                  required=False,
                                  initial="localtime",
                                  choices=TIME_ZONE_CHOICES,
                                  help_text=_("Choose Instance Time Zone"))

    screen = forms.ChoiceField(label=_("Instance Screen"),
                               initial=1,
                               required=False,
                               choices=[(1, _('1')),
                                        (2, _('2')),
                                        (4, _('4'))])
    image_format = forms.ChoiceField(label =_("Disk Mode"),
                                   initial="",
                                   required=False,
                                   choices=[("", _("Thin Provision")),("raw", _("RAW"))],
                                   help_text=_("The default disk mode of virtual machine is thin provision,"
                                                "if you want to create a real-mode,please change the drop-down box."))

    disk_type  = forms.ChoiceField(label=_("Disk Interface"),
                               initial="virtio",
                               required=False,
                               choices=[("ide", _('Ide')),
                                        ("virtio", _('Virtio'))])

    usb_control = forms.BooleanField(label=_("USB"),
                                     required=False,
                                     initial=True)

    clipboard_control = forms.BooleanField(label=_("Whether to allow access Clipboard"),
                                     required=False,
                                     initial=True)

    quatity_control = forms.ChoiceField(label=_("Quatity"),
                                        initial="low",
                                        required=False,
                                        choices=[("low", _('Low')),
                                        ("high", _('High'))])

    jostle = forms.ChoiceField(label=_("Desktop Mode"),
                               required=False,
                               initial="shared",
                               help_text=_("Choose a desktop model"),
                               choices=[("single", _('Desktop Not snatch')),
                                        ("shared", _('Desktop snatch'))])

    multi_user= forms.ChoiceField(label=_('Multi user connection'),
                                                required=False,
                                                initial = "off",
                                                choices=[("on", _("Yes")),("off",_("No"))])

    broadcast = forms.BooleanField(label=_("Allow Screen Broadcast"),
                                            required=False,
                                            initial = False)

    shutdown_restore = forms.ChoiceField(label=_('Shutdown Restore'),
                                                required=False,
                                                initial = "no",
                                                choices=[("yes", _("Yes")),("no",_("No"))])


    during = forms.ChoiceField(label=_("Persistent Mode"),
                               initial="immobilization",
                               required=False,
                               help_text=_("Choose a persistent mode"),
                               choices=[("immobilization", _('Permanent')),
                                        ("variable", _('Non Durable'))])

    per = forms.ChoiceField(label=_("Per"),
                            required=False)

    month_id = forms.CharField(label=_("Month"),
                               required=False,
                               max_length=255)

    day_id = forms.ChoiceField(label=_("Day"),
                               required=False)

    week_id = forms.ChoiceField(label=_("Week"),
                                required=False)

    class Meta:
        name = _("TerminalControl")
        help_text_template= ("admin/vgpu/_launch_instance_terminal_help.html")

    def __init__(self, request, context, *args, **kwargs):
        self.request = request
        self.context = context
        super(TerminalControlAction, self).__init__(
            request, context, *args, **kwargs)

        per_choices= [('None', _("Select source")),
                      ("day_id", _('Day')),
                      ("week_id", _('Week')),
                      ("month_id", _('Month'))]

        day_id_choices = [('1:00', _("1:00")),
                          ("2:00", _('2:00')),
                          ("3:00", _('3:00')),
                          ("4:00", _('4:00')),
                          ("5:00", _('5:00'))]
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

    def clean(self):
        cleaned_data = super(TerminalControlAction, self).clean()

        month_id = cleaned_data.get('month_id', 1)
        p = re.compile('^([1-9]|[12]\d|3[01])$',re.S)
        if month_id:
            if p.match(month_id):
                pass
            else:
                error_message = _('Set the maximum reduction date than the date of each month, please reset')
                raise forms.ValidationError(error_message)

        return cleaned_data

class TerminalControl(workflows.Step):
    action_class = TerminalControlAction
    contributes = ("time_zone","screen","image_format", "disk_type",
                   "usb_control","clipboard_control", "quatity_control", 
                   "shutdown_restore","multi_user", "broadcast", 
                   "jostle", "during","spice_secure","per","dev_time",
                   "day_id","week_id","month_id",)
    def contribute(self, data, context):
        if data:

            param = dict()
            param['time_zone']=data.get("time_zone", None)
            param['screen']=data.get("screen", None)
            param['image_format']=data.get("image_format", None)
            param['disk_type']=data.get("disk_type", None)
            param['usb_control']=data.get("usb_control", None)
            param['clipboard_control']=data.get("clipboard_control", None)
            if data.get("quatity_control") == "low":
                param['quatity_control'] = True
            else:
                param['quatity_control'] = False
            param['shutdown_restore']=data.get("shutdown_restore", None)
            param['multi_user']=data.get("multi_user", None)

            allow_screen_broadcast = data.get("broadcast", "") 
            if param['multi_user'] != "on":
                allow_screen_broadcast = False
            param['allow_screen_broadcast']=allow_screen_broadcast
            control = data.get("jostle","")
            if control == "single":
                param['jostle'] = True
            else:
                param['jostle'] = False
            param['during']=data.get("during", None)
            param['spice_secure']=False
            param['per']=data.get("per", "")
            param['dev_time']=None
            if param['shutdown_restore'] == "yes":
                param['during'] = "immobilization"
            if param['during'] == "immobilization":
               param['per']=None
            a = param['per']
            if a == None:
                param['dev_time'] = None
            else:
                if a == "day_id":
                    param['dev_time'] = None
                elif a == "week_id":
                    param['dev_time'] = data.get("week_id", "")
                elif a == "month_id":
                    param['dev_time'] = data.get("month_id", "")
                    if param['dev_time'] == "":
                        param['dev_time'] = 1
                    

            context['terminal']=[param]
        return context

class SetInstanceDetailsAction(workflows.Action):

    availability_zone = forms.ThemableChoiceField(label=_("Availability Zone"),
                                                  required=False)

    name = forms.CharField(label=_("Instance Name"),
                           required=False,
                           max_length=255)

    pool = forms.ChoiceField(label=_("Pool"),
                             required=False,
                             help_text=_("Choose a pool for the instance to launch."))

    flavor = forms.ThemableChoiceField(label=_("Flavor"),
                                       help_text=_("Size of image to launch."))

    count = forms.IntegerField(label=_("Number of Instances"),
                               min_value=1,
                               initial=1)

    source_type = forms.ThemableChoiceField(
        label=_("Instance Boot Source"),
        help_text=_("Choose Your Boot Source "
                    "Type."))

    instance_snapshot_id = forms.ThemableChoiceField(
        label=_("Instance Snapshot"),
        required=False)

    volume_id = forms.ThemableChoiceField(label=_("Volume"), required=False)

    volume_snapshot_id = forms.ThemableChoiceField(label=_("Volume Snapshot"),
                                                   required=False)

    image_id = forms.ChoiceField(
        label=_("Image Name"),
        required=False,
        widget=forms.ThemableSelectWidget(
            data_attrs=('volume_size',),
            transform=lambda x: ("%s (%s)" % (x.name,
                                              filesizeformat(x.bytes)))))

    image_or_snapshot = forms.ChoiceField(
        label=_("Image Snapshot"),
        required=False,
        widget=forms.SelectWidget(
            data_attrs=('volume_size',),
            transform=lambda x: ("%s (%s)" % (x.name,
                                              filesizeformat(x.bytes)))))

    templet_id = forms.ChoiceField(label=_("templet Name"),
                                  required=False,
                                  widget=forms.SelectWidget(
                                      data_attrs=('volume_size',),
                                      transform=lambda x: ("%s (%s)" % (x.name,
                                              filesizeformat(x.bytes)))))

    custom_id = forms.ChoiceField(label=_("Custom"), required=False)

    volume_size = forms.IntegerField(label=_("Device size (GB)"),
                                     initial=1,
                                     min_value=0,
                                     required=False,
                                     help_text=_("Volume size in gigabytes "
                                                 "(integer value)."))

    device_name = forms.CharField(label=_("Device Name"),
                                  required=False,
                                  initial="vda",
                                  help_text=_("Volume mount point (e.g. 'vda' "
                                              "mounts at '/dev/vda'). Leave "
                                              "this field blank to let the "
                                              "system choose a device name "
                                              "for you."))

    vol_delete_on_instance_delete = forms.BooleanField(
        label=_("Delete Volume on Instance Delete"),
        initial=False,
        required=False,
        help_text=_("Delete volume when the instance is deleted"))

    class Meta(object):
        name = _("Details")
        help_text_template = ("admin/vgpu/"
                              "_launch_details_help.html")

    def __init__(self, request, context, *args, **kwargs):
        self._init_images_cache()
        self.request = request
        self.context = context
        super(SetInstanceDetailsAction, self).__init__(
            request, context, *args, **kwargs)

        # Hide the device field if the hypervisor doesn't support it.
        if not nova.can_set_mount_point():
            self.fields['device_name'].widget = forms.widgets.HiddenInput()

        source_type_choices = [
            ('', _("Select source")),
            ("image_id", _("Boot from image")),
            ("templet_id",_("Boot from templet")),
            #("custom_id", _("Boot from custom")),
            ("instance_snapshot_id", _("Boot from snapshot")),
        ]
        if cinder.is_volume_service_enabled(request):
            source_type_choices.append(("volume_id", _("Boot from volume")))

            try:
                if api.nova.extension_supported("BlockDeviceMappingV2Boot",
                                                request):
                    source_type_choices.append(
                        ("volume_image_id",
                         _("Boot from image (creates a new volume)")))
            except Exception:
                exceptions.handle(request, _('Unable to retrieve extensions '
                                             'information.'))

            source_type_choices.append(
                ("volume_snapshot_id",
                 _("Boot from volume snapshot (creates a new volume)")))
        self.fields['source_type'].choices = source_type_choices

    @memoized.memoized_method
    def _get_flavor(self, flavor_id):
        try:
            # We want to retrieve details for a given flavor,
            # however flavor_list uses a memoized decorator
            # so it is used instead of flavor_get to reduce the number
            # of API calls.
            flavors = instance_utils.flavor_list(self.request)
            flavor = [x for x in flavors if x.id == flavor_id][0]
        except IndexError:
            flavor = None
        return flavor

    @memoized.memoized_method
    def _get_image(self, image_id):
        try:
            # We want to retrieve details for a given image,
            # however get_available_images uses a cache of image list,
            # so it is used instead of image_get to reduce the number
            # of API calls.
            images = image_utils.get_available_images(
                self.request,
                self.context.get('project_id'),
                self._images_cache)
            image = [x for x in images if x.id == image_id][0]
        except IndexError:
            image = None
        return image

    def _check_licence(self, cleaned_data):

        try:
            licence = api.nova.get_licence(self.request)
            decoded_string = api.authcode.AuthCode.code_init(licence)
            probation = getattr(licence, 'probation', False)
            if not probation:
                startTime = datetime.datetime.strptime(\
                            decoded_string['time'],'%Y-%m-%dT%H:%M:%S.%f')     
                rtf = datetime.datetime.strptime(licence.starttime,\
                                                 '%Y-%m-%dT%H:%M:%S.%f')
                endTime = datetime.timedelta(days=decoded_string['during'])
                runTime = datetime.datetime(rtf.year, rtf.month, rtf.day)
                ef = (startTime + endTime)
                expiretime =datetime.datetime(ef.year, ef.month, ef.day)
                num = decoded_string['num']
                used = licence.used
                if used >= num or runTime >= expiretime or licence.disabled is True:
                    msg = _("Sequence number has %(expiretime)s expired or exceeds\
                                          the maximum number %(num)s of virtual machine") 
                    params = {'expiretime':expiretime, 'num':num }
                    raise forms.ValidationError(msg % params)
                cleaned_data.update({'num':num})
        except Exception:      
            raise forms.ValidationError(_("License Expired"))
                

    def _check_quotas(self, cleaned_data):
        pool_id = cleaned_data.get('pool',None)
        count = cleaned_data.get('count', 1)

        # Prevent launching more instances than the quota allows
        usages = quotas.tenant_quota_usages(self.request, pool_id)
        #LOG.info("usages ============================%s" % usages)
        available_count = usages['instances']['available']
        if available_count < count:
            error_message = ungettext_lazy(
                'The requested instance cannot be launched as you only '
                'have %(avail)i of your quota available. ',
                'The requested %(req)i instances cannot be launched as you '
                'only have %(avail)i of your quota available.',
                count)
            params = {'req': count,
                      'avail': available_count}
            raise forms.ValidationError(error_message % params)

        source_type = cleaned_data.get('source_type')
        if source_type in ('volume_image_id', 'volume_snapshot_id'):
            available_volume = usages['volumes']['available']
            if available_volume < count:
                msg = (_('The requested instance cannot be launched. '
                         'Requested volume exceeds quota: Available: '
                         '%(avail)s, Requested: %(req)s.')
                       % {'avail': available_volume, 'req': count})
                raise forms.ValidationError(msg)

        flavor_id = cleaned_data.get('flavor')
        flavor = self._get_flavor(flavor_id)

        count_error = []
        # Validate cores and ram.
        available_cores = usages['cores']['available']
        if flavor and available_cores < count * flavor.vcpus:
            count_error.append(_("Cores(Available: %(avail)s, "
                                 "Requested: %(req)s)")
                               % {'avail': available_cores,
                                  'req': count * flavor.vcpus})

        available_ram = usages['ram']['available']
        if flavor and available_ram < count * flavor.ram:
            count_error.append(_("RAM(Available: %(avail)s, "
                                 "Requested: %(req)s)")
                               % {'avail': available_ram,
                                  'req': count * flavor.ram})

        if count_error:
            value_str = ", ".join(count_error)
            msg = (_('The requested instance cannot be launched. '
                     'The following requested resource(s) exceed '
                     'quota(s): %s.') % value_str)
            if count == 1:
                self._errors['flavor'] = self.error_class([msg])
            else:
                self._errors['count'] = self.error_class([msg])

    def _check_flavor_for_image(self, cleaned_data):
        # Prevents trying to launch an image needing more resources.
        image_id = cleaned_data.get('image_id')
        image = self._get_image(image_id)
        flavor_id = cleaned_data.get('flavor')
        flavor = self._get_flavor(flavor_id)
        if not image or not flavor:
            return
        props_mapping = (("min_ram", "ram"), ("min_disk", "disk"))
        for iprop, fprop in props_mapping:
            if getattr(image, iprop) > 0 and \
                    getattr(image, iprop) > getattr(flavor, fprop):
                msg = (_("The flavor '%(flavor)s' is too small "
                         "for requested image.\n"
                         "Minimum requirements: "
                         "%(min_ram)s MB of RAM and "
                         "%(min_disk)s GB of Root Disk.") %
                       {'flavor': flavor.name,
                        'min_ram': image.min_ram,
                        'min_disk': image.min_disk})
                self._errors['image_id'] = self.error_class([msg])
                break  # Not necessary to continue the tests.

    def _check_volume_for_image(self, cleaned_data):
        image_id = cleaned_data.get('image_id')
        image = self._get_image(image_id)
        volume_size = cleaned_data.get('volume_size')
        if not image or not volume_size:
            return
        volume_size = int(volume_size)
        img_gigs = functions.bytes_to_gigabytes(image.size)
        smallest_size = max(img_gigs, image.min_disk)
        if volume_size < smallest_size:
            msg = (_("The Volume size is too small for the"
                     " '%(image_name)s' image and has to be"
                     " greater than or equal to "
                     "'%(smallest_size)d' GB.") %
                   {'image_name': image.name,
                    'smallest_size': smallest_size})
            self._errors['volume_size'] = self.error_class([msg])

    def _check_source_image(self, cleaned_data):
        if not cleaned_data.get('image_id'):
            msg = _("You must select an image.")
            self._errors['image_id'] = self.error_class([msg])
        else:
            self._check_flavor_for_image(cleaned_data)

    def _check_source_templet(self, cleaned_data):
        if not cleaned_data.get('templet_id'):
            msg =_("You must select an templet")
            self._errors['templet_id'] = self.error_class([msg])
        elif not cleaned_data.get('image_or_snapshot'):
            msg =_("You must select an image or snapshot")
            self._errors['image_or_snapshot'] = self.error_class([msg])
        else:
            templet_id = cleaned_data.get('templet_id', None)
            try:
                image_templet = api.glance.image_get(self.request, templet_id)
                templet = api.glance.templet_download(self.request, image_templet, True)
                users = api.keystone.user_list(self.request)
                count =0
                for info in templet:
                    if info['count']:
                        count+=int(info['count'], 10)
                    else:
                        count+=1
                if count >= cleaned_data.get('num', 0):
                    msg =_("The largest number is greater than the \
                           authorized permission to create instance")
                    self._errors['templet_id'] = self.error_class([msg])
                cleaned_data.update({'templet':templet, 'users':users}) 
            except Exception:
                msg =_("Batch to create Excel file(%s) content format is not correct" % templet_id)
                self._errors['templet_id'] = self.error_class([msg])
            #LOG.info("_check_source_templet ===============%s" % cleaned_data)

    def _check_source_volume_image(self, cleaned_data):
        volume_size = self.data.get('volume_size', None)
        if not volume_size:
            msg = _("You must set volume size")
            self._errors['volume_size'] = self.error_class([msg])
        if float(volume_size) <= 0:
            msg = _("Volume size must be greater than 0")
            self._errors['volume_size'] = self.error_class([msg])
        if not cleaned_data.get('image_id'):
            msg = _("You must select an image.")
            self._errors['image_id'] = self.error_class([msg])
            return
        else:
            self._check_flavor_for_image(cleaned_data)
            self._check_volume_for_image(cleaned_data)

    def _check_source_instance_snapshot(self, cleaned_data):
        # using the array form of get blows up with KeyError
        # if instance_snapshot_id is nil
        if not cleaned_data.get('instance_snapshot_id'):
            msg = _("You must select a snapshot.")
            self._errors['instance_snapshot_id'] = self.error_class([msg])

    def _check_source_volume(self, cleaned_data):
        if not cleaned_data.get('volume_id'):
            msg = _("You must select a volume.")
            self._errors['volume_id'] = self.error_class([msg])
        # Prevent launching multiple instances with the same volume.
        # TODO(gabriel): is it safe to launch multiple instances with
        # a snapshot since it should be cloned to new volumes?
        count = cleaned_data.get('count', 1)
        if count > 1:
            msg = _('Launching multiple instances is only supported for '
                    'images and instance snapshots.')
            raise forms.ValidationError(msg)

    def _check_source_volume_snapshot(self, cleaned_data):
        if not cleaned_data.get('volume_snapshot_id'):
            msg = _("You must select a snapshot.")
            self._errors['volume_snapshot_id'] = self.error_class([msg])

    def _check_source(self, cleaned_data):
        # Validate our instance source.
        source_type = self.data.get('source_type', None)
        source_check_methods = {
            'templet_id': self._check_source_templet,
            'image_id': self._check_source_image,
            'volume_image_id': self._check_source_volume_image,
            'instance_snapshot_id': self._check_source_instance_snapshot,
            'volume_id': self._check_source_volume,
            'volume_snapshot_id': self._check_source_volume_snapshot
        }
        check_method = source_check_methods.get(source_type)
        if check_method:
            check_method(cleaned_data)

    def clean(self):
        cleaned_data = super(SetInstanceDetailsAction, self).clean()
        self._check_licence(cleaned_data)
        LOG.info("clean =========================%s" % cleaned_data)
        self._check_quotas(cleaned_data)
        self._check_source(cleaned_data)
        return cleaned_data

    def populate_templet_id_choices(self, request, context):
        choices = []
        images = image_utils.get_filter_properties(request)
        #images = image_utils.get_available_images(request,
        #                                    context.get('project_id'),
        #                                    self._images_cache)
        for image in images:
            image.bytes = image.size
            image.volume_size = max(
                image.min_disk, functions.bytes_to_gigabytes(image.bytes))
            if image.properties.get('image_type'):
                if image.properties.get('image_type') != 'snapshot':
                    choices.append((image.id, image))
            if context.get('image_id') == image.id and \
                    'volume_size' not in context:
                context['volume_size'] = image.volume_size
        if choices:
            choices.sort(key=lambda c: c[1].name)
        else:
            choices.insert(0, ("", _("No templet available")))
        return choices



    def populate_image_or_snapshot_choices(self, request, context):
        choices = []
        images = image_utils.get_available_images(request,
                                            context.get('project_id'),
                                            self._images_cache)
        for image in images:
            image.bytes = image.size
            image.volume_size = max(
                image.min_disk, functions.bytes_to_gigabytes(image.bytes))
            if image.properties.get('image_type'):
                if image.properties.get('image_type') == 'snapshot':
                    choices.append((image.id, image))
            if not image.properties.get('image_type'):
                choices.append((image.id, image))
            if context.get('image_id') == image.id and \
                    'volume_size' not in context:
                context['volume_size'] = image.volume_size
        if choices:
            choices.sort(key=lambda c: c[1].name)
            choices.insert(0, ("", _("Select Image or Snapshot")))
        else:
            choices.insert(0, ("", _("No images available")))
        return choices


    def populate_pool_choices(self, request, context):
        tenants, has_more = api.keystone.tenant_list(self.request)
        choices = [(choice.id, _('Default Pool') if choice.name == 'admin' else choice.name) 
                 for choice in tenants if choice.name != 'services']
        adminPool = [default for default in choices if type(default[1]) != unicode][0]
        if adminPool in choices:
            choices.remove(adminPool)
            choices.insert(0, adminPool)
        #LOG.info('choices================%s' % choices) 
        return choices
            
    def populate_flavor_choices(self, request, context):
        return instance_utils.flavor_field_data(request, False)

    def populate_availability_zone_choices(self, request, context):
        try:
            zones = api.nova.availability_zone_list(request)
        except Exception:
            zones = []
            exceptions.handle(request,
                              _('Unable to retrieve availability zones.'))

        zone_list = [(zone.zoneName, zone.zoneName)
                     for zone in zones if zone.zoneState['available']]
        zone_list.sort()
        if not zone_list:
            zone_list.insert(0, ("", _("No availability zones found")))
        elif len(zone_list) > 1:
            zone_list.insert(0, ("", _("Any Availability Zone")))
        return zone_list

    def get_help_text(self, extra_context=None):
        extra = {} if extra_context is None else dict(extra_context)
        try:
            extra['usages'] = api.nova.tenant_absolute_limits(self.request,
                                                              reserved=True)
            extra['usages_json'] = json.dumps(extra['usages'])
            flavors = json.dumps([f._info for f in
                                  instance_utils.flavor_list(self.request)])
            extra['flavors'] = flavors
            images = image_utils.get_available_images(
                self.request, self.initial['project_id'], self._images_cache)
            if images is not None:
                attrs = [{'id': i.id,
                          'min_disk': getattr(i, 'min_disk', 0),
                          'min_ram': getattr(i, 'min_ram', 0),
                          'size': functions.bytes_to_gigabytes(i.size)}
                         for i in images]
                extra['images'] = json.dumps(attrs)

        except Exception:
            exceptions.handle(self.request,
                              _("Unable to retrieve quota information."))
        return super(SetInstanceDetailsAction, self).get_help_text(extra)

    def _init_images_cache(self):
        if not hasattr(self, '_images_cache'):
            self._images_cache = {}

    def _get_volume_display_name(self, volume):
        if hasattr(volume, "volume_id"):
            vol_type = "snap"
            visible_label = _("Snapshot")
        else:
            vol_type = "vol"
            visible_label = _("Volume")
        return (("%s:%s" % (volume.id, vol_type)),
                (_("%(name)s - %(size)s GB (%(label)s)") %
                 {'name': volume.name,
                  'size': volume.size,
                  'label': visible_label}))

    def populate_image_id_choices(self, request, context):
        choices = []
        images = image_utils.get_available_images(request,
                                                  context.get('project_id'),
                                                  self._images_cache)
        for image in images:
            image.bytes = getattr(image, 'virtual_size', None) or image.size
            image.volume_size = max(
                image.min_disk, functions.bytes_to_gigabytes(image.bytes))
            choices.append((image.id, image))
            if context.get('image_id') == image.id and \
                    'volume_size' not in context:
                context['volume_size'] = image.volume_size
        if choices:
            choices.sort(key=lambda c: c[1].name or '')
            choices.insert(0, ("", _("Select Image")))
        else:
            choices.insert(0, ("", _("No images available")))
        return choices

    def populate_instance_snapshot_id_choices(self, request, context):
        images = image_utils.get_available_images(request,
                                                  context.get('project_id'),
                                                  self._images_cache)
        choices = [(image.id, image.name)
                   for image in images
                   if image.properties.get("image_type", '') == "snapshot"]
        if choices:
            choices.sort(key=operator.itemgetter(1))
            choices.insert(0, ("", _("Select Instance Snapshot")))
        else:
            choices.insert(0, ("", _("No snapshots available")))
        return choices

    def populate_volume_id_choices(self, request, context):
        volumes = []
        try:
            if cinder.is_volume_service_enabled(request):
                available = api.cinder.VOLUME_STATE_AVAILABLE
                volumes = [self._get_volume_display_name(v)
                           for v in cinder.volume_list(self.request,
                           search_opts=dict(status=available, bootable=True))]
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve list of volumes.'))
        if volumes:
            volumes.insert(0, ("", _("Select Volume")))
        else:
            volumes.insert(0, ("", _("No volumes available")))
        return volumes

    def populate_volume_snapshot_id_choices(self, request, context):
        snapshots = []
        try:
            if cinder.is_volume_service_enabled(request):
                available = api.cinder.VOLUME_STATE_AVAILABLE
                snapshots = [self._get_volume_display_name(s)
                             for s in cinder.volume_snapshot_list(
                             self.request, search_opts=dict(status=available))]
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve list of volume '
                                'snapshots.'))
        if snapshots:
            snapshots.insert(0, ("", _("Select Volume Snapshot")))
        else:
            snapshots.insert(0, ("", _("No volume snapshots available")))
        return snapshots


class SetInstanceDetails(workflows.Step):
    action_class = SetInstanceDetailsAction
    depends_on = ("project_id", "user_id")
    contributes = ("source_type", "source_id",
                   "availability_zone", "name", "count", "flavor",
                   "device_name", "pool", # Can be None for an image.
                   "vol_delete_on_instance_delete")

    def prepare_action_context(self, request, context):
        if 'source_type' in context and 'source_id' in context:
            context[context['source_type']] = context['source_id']
        return context

    def contribute(self, data, context):
        context = super(SetInstanceDetails, self).contribute(data, context)
        # Allow setting the source dynamically.
        if ("source_type" in context and "source_id" in context
                and context["source_type"] not in context):
            context[context["source_type"]] = context["source_id"]

        # Translate form input to context for source values.
        if "source_type" in data:
            if data["source_type"] in ["image_id", "templet_id", "custom_id","volume_image_id"]:
                if data['image_id']:
                    context["source_id"] = data.get("image_id", None)
                else:
                    context['source_id'] = data.get("image_or_snapshot", None)
                if 'templet_id' in context:
                    context['templet_id'] = data.get("templet_id", None)
                    context['templet'] = data.get("templet", None)
                    context['users'] = data.get("users", None)
            else:
                context["source_id"] = data.get(data["source_type"], None)

        if "volume_size" in data:
            context["volume_size"] = data["volume_size"]

        LOG.info("data ============================%s" % data)
        return context


KEYPAIR_IMPORT_URL = "horizon:admin:access_and_security:keypairs:import"


class SetAccessControlsAction(workflows.Action):
    keypair = forms.ThemableDynamicChoiceField(
        label=_("Key Pair"),
        help_text=_("Key pair to use for "
                    "authentication."),
        add_item_link=KEYPAIR_IMPORT_URL)
    admin_pass = forms.RegexField(
        label=_("Admin Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False),
        regex=validators.password_validator(),
        error_messages={'invalid': validators.password_validator_msg()})
    confirm_admin_pass = forms.CharField(
        label=_("Confirm Admin Password"),
        required=False,
        widget=forms.PasswordInput(render_value=False))
    groups = forms.MultipleChoiceField(
        label=_("Security Groups"),
        required=False,
        initial=["default"],
        widget=forms.ThemableCheckboxSelectMultiple(),
        help_text=_("Launch instance in these "
                    "security groups."))

    class Meta(object):
        name = _("Access & Security")
        help_text = _("Control access to your instance via key pairs, "
                      "security groups, and other mechanisms.")

    def __init__(self, request, *args, **kwargs):
        super(SetAccessControlsAction, self).__init__(request, *args, **kwargs)
        if not api.nova.can_set_server_password():
            del self.fields['admin_pass']
            del self.fields['confirm_admin_pass']
        self.fields['keypair'].required = api.nova.requires_keypair()

    def populate_keypair_choices(self, request, context):
        keypairs = instance_utils.keypair_field_data(request, True)
        if len(keypairs) == 2:
            self.fields['keypair'].initial = keypairs[1][0]
        return keypairs

    def populate_groups_choices(self, request, context):
        try:
            groups = api.network.security_group_list(request)
            if base.is_service_enabled(request, 'network'):
                security_group_list = [(sg.id, sg.name) for sg in groups]
            else:
                # Nova-Network requires the groups to be listed by name
                security_group_list = [(sg.name, sg.name) for sg in groups]
        except Exception:
            exceptions.handle(request,
                              _('Unable to retrieve list of security groups'))
            security_group_list = []
        return security_group_list

    def clean(self):
        '''Check to make sure password fields match.'''
        cleaned_data = super(SetAccessControlsAction, self).clean()
        if 'admin_pass' in cleaned_data:
            if cleaned_data['admin_pass'] != cleaned_data.get(
                    'confirm_admin_pass', None):
                raise forms.ValidationError(_('Passwords do not match.'))
        return cleaned_data


class SetAccessControls(workflows.Step):
    action_class = SetAccessControlsAction
    depends_on = ("project_id", "user_id")
    contributes = ("keypair_id", "security_group_ids",
                   "admin_pass", "confirm_admin_pass")

    def contribute(self, data, context):
        if data:
            post = self.workflow.request.POST
            context['security_group_ids'] = post.getlist("groups")
            context['keypair_id'] = data.get("keypair", "")
            context['admin_pass'] = data.get("admin_pass", "")
            context['confirm_admin_pass'] = data.get("confirm_admin_pass", "")
        return context


class CustomizeAction(workflows.Action):
    class Meta(object):
        name = _("Post-Creation")
        help_text_template = ("admin/vgpu/"
                              "_launch_customize_help.html")

    source_choices = [('', _('Select Script Source')),
                      ('raw', _('Direct Input')),
                      ('file', _('File'))]

    attributes = {'class': 'switchable', 'data-slug': 'scriptsource'}
    script_source = forms.ChoiceField(
        label=_('Customization Script Source'),
        choices=source_choices,
        widget=forms.ThemableSelectWidget(attrs=attributes),
        required=False)

    script_help = _("A script or set of commands to be executed after the "
                    "instance has been built (max 16kb).")

    script_upload = forms.FileField(
        label=_('Script File'),
        help_text=script_help,
        widget=forms.FileInput(attrs={
            'class': 'switched',
            'data-switch-on': 'scriptsource',
            'data-scriptsource-file': _('Script File')}),
        required=False)

    script_data = forms.CharField(
        label=_('Script Data'),
        help_text=script_help,
        widget=forms.widgets.Textarea(attrs={
            'class': 'switched',
            'data-switch-on': 'scriptsource',
            'data-scriptsource-raw': _('Script Data')}),
        required=False)

    def __init__(self, *args):
        super(CustomizeAction, self).__init__(*args)

    def clean(self):
        cleaned = super(CustomizeAction, self).clean()

        files = self.request.FILES
        script = self.clean_uploaded_files('script', files)

        if script is not None:
            cleaned['script_data'] = script

        return cleaned

    def clean_uploaded_files(self, prefix, files):
        upload_str = prefix + "_upload"

        has_upload = upload_str in files
        if has_upload:
            upload_file = files[upload_str]
            log_script_name = upload_file.name
            LOG.info('got upload %s' % log_script_name)

            if upload_file._size > 16 * units.Ki:  # 16kb
                msg = _('File exceeds maximum size (16kb)')
                raise forms.ValidationError(msg)
            else:
                script = upload_file.read()
                if script != "":
                    try:
                        normalize_newlines(script)
                    except Exception as e:
                        msg = _('There was a problem parsing the'
                                ' %(prefix)s: %(error)s')
                        msg = msg % {'prefix': prefix,
                                     'error': six.text_type(e)}
                        raise forms.ValidationError(msg)
                return script
        else:
            return None


class PostCreationStep(workflows.Step):
    action_class = CustomizeAction
    contributes = ("script_data",)


class SetNetworkAction(workflows.Action):
    network = forms.MultipleChoiceField(
        label=_("Networks"),
        widget=forms.ThemableCheckboxSelectMultiple(),
        error_messages={
            'required': _(
                "At least one network must"
                " be specified.")},
        help_text=_("Launch instance with"
                    " these networks"))
    if api.neutron.is_port_profiles_supported():
        widget = None
    else:
        widget = forms.HiddenInput()
    profile = forms.ChoiceField(label=_("Policy Profiles"),
                                required=False,
                                widget=widget,
                                help_text=_("Launch instance with "
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


class SetNetwork(workflows.Step):
    action_class = SetNetworkAction
    # Disabling the template drag/drop only in the case port profiles
    # are used till the issue with the drag/drop affecting the
    # profile_id detection is fixed.
    if api.neutron.is_port_profiles_supported():
        contributes = ("network_id", "profile_id",)
    else:
        template_name = "admin/vgpu/_update_networks.html"
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


class SetNetworkPortsAction(workflows.Action):
    ports = forms.MultipleChoiceField(label=_("Ports"),
                                      widget=forms.CheckboxSelectMultiple(),
                                      required=False,
                                      help_text=_("Launch instance with"
                                                  " these ports"))

    class Meta(object):
        name = _("Network Ports")
        permissions = ('openstack.services.network',)
        help_text_template = ("admin/vgpu/"
                              "_launch_network_ports_help.html")

    def populate_ports_choices(self, request, context):
        ports = instance_utils.port_field_data(request)
        if not ports:
            self.fields['ports'].label = _("No ports available")
            self.fields['ports'].help_text = _("No ports available")
        return ports


class SetNetworkPorts(workflows.Step):
    action_class = SetNetworkPortsAction
    contributes = ("ports",)

    def contribute(self, data, context):
        if data:
            ports = self.workflow.request.POST.getlist("ports")
            if ports:
                context['ports'] = ports
        return context


class SetAdvancedAction(workflows.Action):
    disk_config = forms.ThemableChoiceField(
        label=_("Disk Partition"), required=False,
        help_text=_("Automatic: The entire disk is a single partition and "
                    "automatically resizes. Manual: Results in faster build "
                    "times but requires manual partitioning."))
    config_drive = forms.BooleanField(
        label=_("Configuration Drive"),
        required=False, help_text=_("Configure OpenStack to write metadata to "
                                    "a special configuration drive that "
                                    "attaches to the instance when it boots."))
    server_group = forms.ThemableChoiceField(
        label=_("Server Group"), required=False,
        help_text=_("Server group to associate with this instance."))

    def __init__(self, request, context, *args, **kwargs):
        super(SetAdvancedAction, self).__init__(request, context,
                                                *args, **kwargs)
        try:
            if not api.nova.extension_supported("DiskConfig", request):
                del self.fields['disk_config']
            else:
                # Set our disk_config choices
                config_choices = [("AUTO", _("Automatic")),
                                  ("MANUAL", _("Manual"))]
                self.fields['disk_config'].choices = config_choices
            # Only show the Config Drive option for the Launch Instance
            # workflow (not Resize Instance) and only if the extension
            # is supported.
            if context.get('workflow_slug') != 'launch_instance' or (
                    not api.nova.extension_supported("ConfigDrive", request)):
                del self.fields['config_drive']

            if not api.nova.extension_supported("ServerGroups", request):
                del self.fields['server_group']
            else:
                server_group_choices = instance_utils.server_group_field_data(
                    request)
                self.fields['server_group'].choices = server_group_choices
        except Exception:
            exceptions.handle(request, _('Unable to retrieve extensions '
                                         'information.'))

    class Meta(object):
        name = _("Advanced Options")
        help_text_template = ("admin/vgpu/"
                              "_launch_advanced_help.html")


class SetAdvanced(workflows.Step):
    action_class = SetAdvancedAction
    contributes = ("disk_config", "config_drive", "server_group",)

    def prepare_action_context(self, request, context):
        context = super(SetAdvanced, self).prepare_action_context(request,
                                                                  context)
        # Add the workflow slug to the context so that we can tell which
        # workflow is being used when creating the action. This step is
        # used by both the Launch Instance and Resize Instance workflows.
        context['workflow_slug'] = self.workflow.slug
        return context


class LaunchInstance(workflows.Workflow):
    slug = "launch_instance"
    name = _("Launch VGPUInstance")
    finalize_button_name = _("Launch")
    success_message = _('Request for launching %(count)s named "%(name)s" '
                        'has been submitted.')
    failure_message = _('Unable to launch %(count)s named "%(name)s".')
    success_url = "horizon:admin:vgpu:index"
    multipart = True
    default_steps = (SelectProjectUser,
                     SetInstanceDetails,
                     SetAccessControls,
                     SetNetwork,
                     #SetNetworkPorts,
                     TerminalControl,
                     PostCreationStep,
                     SetAdvanced)

    def format_status_message(self, message):
        name = self.context.get('name', 'unknown instance')
        count = self.context.get('count', 1)
        templet_id = self.context.get('source_type')
        if int(count) > 1:
            return message % {"count": _("%s instances") % count,
                              "name": name}
        elif templet_id == 'templet_id':
            return message % {"count": _("instance"), 
                              "name":'Batch create'}
        else:
            return message % {"count": _("instance"), "name": name}

    def batch_handle(self, request, context, image_id, templet, users, 
                           custom_script, block_device_mapping=None, 
                           block_device_mapping_v2=None, nics=None, 
                           availability_zone=None, scheduler_hints=None):
        terminal = context.get('terminal', list())
        if terminal:
           param = terminal[0]
        else:
           param = dict() 
           
        try:
            for info in templet:
                if info['count']:
                    instance_count=int(info['count'], 10)
                else:
                    instance_count=1
                _user = info.get('user')
                if not _user:
                    param.update({'vm_user':request.user.id})
                else: 
                    username = [u.id for u in users if u.name ==_user]
                    if username:
                        param.update({'vm_user':username.pop()}) 
                    else:
                        try:
                            domain = api.keystone.get_default_domain(self.request)
                            new_user=api.keystone.user_create(request, name=info['user'], 
                                     email=None, password=info['user'], 
                                     project=context['pool'], 
                                     enabled=True, domain=domain.id)
                            param.update({'vm_user':new_user.id})
                        except Exception:
                            messages.error(request, _('Unable to update the user.'))
                context['terminal']=[param]
                context.update({'name':info['name']}) 
                api.nova.server_create(request,
                                   context['name'],
                                   image_id,
                                   context['pool'],
                                   context['flavor'],
                                   context['keypair_id'],
                                   normalize_newlines(custom_script),
                                   context['security_group_ids'],
                                   terminal = context['terminal'],
                                   block_device_mapping=block_device_mapping,
                                   block_device_mapping_v2=block_device_mapping_v2,
                                   nics=nics,
                                   availability_zone=availability_zone,
                                   instance_count=instance_count,
                                   admin_pass=context['admin_pass'],
                                   disk_config=context.get('disk_config'),
                                   config_drive=context.get('config_drive'),
                                   scheduler_hints=scheduler_hints)
            return True
        except Exception: 
            exceptions.handle(request)
            return False


    @sensitive_variables('context')
    def handle(self, request, context):
        custom_script = context.get('script_data', '')
        users = context.get('users', None)
        templet = context.get('templet', None)

        dev_mapping_1 = None
        dev_mapping_2 = None

        image_id = ''

        # Determine volume mapping options
        source_type = context.get('source_type', None)
        if source_type in ['image_id', 'instance_snapshot_id', 'templet_id']:
            image_id = context['source_id']
            if context.get('templet_id', '') == 'No_templet' or 'custom_id' in context:
                if int(context['count']) > 1:
                    for i in range(int(context['count'])):
                        user_number = context['input_user']
                        userjoin = '_'.join([user_number, str(i+1)])
                        try:
                            if user_number:
                                domain = api.keystone.get_default_domain(self.request)
                                new_user=api.keystone.user_create(request,
                                                          name=userjoin,
                                                          email=None,
                                                          password=userjoin,
                                                          project=context['pool'],
                                                          enabled=True,
                                                          domain=domain.id)
                        except Exception:
                            username = [u.name for u in users if u.name == userjoin][0]
                            user_id = [u.id for u in users if u.name == userjoin][0]
                            user_info.append(user_id)
                            messages.warning(request, _('Users already exist.'))
                else:
                    username = [u.name for u in users if u.name == context['input_user']]
                    if username:
                        user_id = [u.id for u in users if u.name == context['input_user']][0]
                        api.keystone.user_update_tenant(self.request, user_id, context['pool'])
                        templet_info=user_id
                    else:
                        try:
                            if context.get('input_user', None):
                                domain = api.keystone.get_default_domain(self.request)
                                new_user=api.keystone.user_create(request,
                                               name=context['input_user'],
                                               email=None,
                                               password=context['input_user'],
                                               project=context['pool'],
                                               enabled=True,
                                               domain=domain.id)
                                api.keystone.user_update_tenant(self.request, new_user.id, context['pool'])
                                templet_info=new_user.id
                        except Exception:
                            messages.error(request, _('Unable to update the user.'))
                            templet_info=None

        elif source_type in ['volume_id', 'volume_snapshot_id']:
            try:
                if api.nova.extension_supported("BlockDeviceMappingV2Boot",
                                                request):
                    # Volume source id is extracted from the source
                    volume_source_id = context['source_id'].split(':')[0]
                    device_name = context.get('device_name', '') \
                        .strip() or None
                    dev_source_type_mapping = {
                        'volume_id': 'volume',
                        'volume_snapshot_id': 'snapshot'
                    }
                    dev_mapping_2 = [
                        {'device_name': device_name,
                         'source_type': dev_source_type_mapping[source_type],
                         'destination_type': 'volume',
                         'delete_on_termination':
                             bool(context['vol_delete_on_instance_delete']),
                         'uuid': volume_source_id,
                         'boot_index': '0',
                         'volume_size': context['volume_size']
                         }
                    ]
                else:
                    dev_mapping_1 = {
                        context['device_name']: '%s::%s' %
                        (context['source_id'],
                         bool(context['vol_delete_on_instance_delete']))
                    }
            except Exception:
                msg = _('Unable to retrieve extensions information')
                exceptions.handle(request, msg)

        elif source_type == 'volume_image_id':
            device_name = context.get('device_name', '').strip() or None
            dev_mapping_2 = [
                {'device_name': device_name,  # None auto-selects device
                 'source_type': 'image',
                 'destination_type': 'volume',
                 'delete_on_termination':
                     bool(context['vol_delete_on_instance_delete']),
                 'uuid': context['source_id'],
                 'boot_index': '0',
                 'volume_size': context['volume_size']
                 }
            ]

        netids = context.get('network_id', None)
        if netids:
            nics = [{"net-id": netid, "v4-fixed-ip": ""}
                    for netid in netids]
        else:
            nics = None

        avail_zone = context.get('availability_zone', None)

        scheduler_hints = {}
        server_group = context.get('server_group', None)
        if server_group:
            scheduler_hints['group'] = server_group

        port_profiles_supported = api.neutron.is_port_profiles_supported()

        if port_profiles_supported:
            nics = self.set_network_port_profiles(request,
                                                  context['network_id'],
                                                  context['profile_id'])

        ports = context.get('ports')
        if ports:
            if nics is None:
                nics = []
            nics.extend([{'port-id': port} for port in ports])

        if 'templet_id' in context and context.get('templet_id') != 'No_templet':
            if templet and users: 
                result= self.batch_handle(request, context, image_id, templet, users,
                                         custom_script, block_device_mapping=dev_mapping_1,
                                         block_device_mapping_v2=dev_mapping_2, nics=nics,
                                         availability_zone=avail_zone, 
                                         scheduler_hints=scheduler_hints)
            return result
            

        try:
            api.nova.server_create(request,
                                   context['name'],
                                   image_id,
                                   context['pool'],
                                   context['flavor'],
                                   context['keypair_id'],
                                   normalize_newlines(custom_script),
                                   context['security_group_ids'],
                                   terminal = context['terminal'], 
                                   block_device_mapping=dev_mapping_1,
                                   block_device_mapping_v2=dev_mapping_2,
                                   nics=nics,
                                   availability_zone=avail_zone,
                                   instance_count=int(context['count']),
                                   admin_pass=context['admin_pass'],
                                   disk_config=context.get('disk_config'),
                                   config_drive=context.get('config_drive'),
                                   scheduler_hints=scheduler_hints)
            return True
        except Exception:
            if port_profiles_supported:
                ports_failing_deletes = _cleanup_ports_on_failed_vm_launch(
                    request, nics)
                if ports_failing_deletes:
                    ports_str = ', '.join(ports_failing_deletes)
                    msg = (_('Port cleanup failed for these port-ids (%s).')
                           % ports_str)
                    exceptions.handle(request, msg)
            exceptions.handle(request)
        return False

    def set_network_port_profiles(self, request, net_ids, profile_id):
        # Create port with Network ID and Port Profile
        # for the use with the plugin supporting port profiles.
        nics = []
        for net_id in net_ids:
            try:
                port = api.neutron.port_create(
                    request,
                    net_id,
                    policy_profile_id=profile_id,
                )
            except Exception as e:
                msg = (_('Unable to create port for profile '
                         '"%(profile_id)s": %(reason)s'),
                       {'profile_id': profile_id,
                        'reason': e})
                for nic in nics:
                    try:
                        port_id = nic['port-id']
                        api.neutron.port_delete(request, port_id)
                    except Exception:
                        msg = (msg +
                               _(' Also failed to delete port %s') % port_id)
                redirect = self.success_url
                exceptions.handle(request, msg, redirect=redirect)

            if port:
                nics.append({"port-id": port.id})
                LOG.debug("Created Port %(portid)s with "
                          "network %(netid)s "
                          "policy profile %(profile_id)s",
                          {'portid': port.id,
                           'netid': net_id,
                           'profile_id': profile_id})

        return nics


def _cleanup_ports_on_failed_vm_launch(request, nics):
    ports_failing_deletes = []
    LOG.debug('Cleaning up stale VM ports.')
    for nic in nics:
        try:
            LOG.debug('Deleting port with id: %s' % nic['port-id'])
            api.neutron.port_delete(request, nic['port-id'])
        except Exception:
            ports_failing_deletes.append(nic['port-id'])
    return ports_failing_deletes
