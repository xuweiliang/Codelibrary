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
import json
import time

from django.conf import settings
from django.forms import ValidationError  # noqa
from django.forms.widgets import HiddenInput  # noqa
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api
from openstack_dashboard import policy
import logging
LOG = logging.getLogger(__name__)

IMAGE_BACKEND_SETTINGS = getattr(settings, 'OPENSTACK_IMAGE_BACKEND', {})
IMAGE_FORMAT_CHOICES = IMAGE_BACKEND_SETTINGS.get('image_formats', [])
NAME_CHOICES = [("", _("Select Name")),
                ("Port", _("Port")),
                ("Txt", _("Txt"))]


def create_image_metadata(data):
    """Use the given dict of image form data to generate the metadata used for
    creating the image in glance.
    """
    # Glance does not really do anything with container_format at the
    # moment. It requires it is set to the same disk_format for the three
    # Amazon image types, otherwise it just treats them as 'bare.' As such
    # we will just set that to be that here instead of bothering the user
    # with asking them for information we can already determine.
    disk_format = data['disk_format']
    if disk_format in ('ami', 'aki', 'ari',):
        container_format = disk_format
    elif disk_format == 'docker':
        # To support docker containers we allow the user to specify
        # 'docker' as the format. In that case we really want to use
        # 'raw' as the disk format and 'docker' as the container format.
        disk_format = 'raw'
        container_format = 'docker'
    else:
        container_format = 'bare'

    meta = {'protected': False,
            'disk_format': disk_format,
            'container_format': container_format,
            'min_disk': (data['minimum_disk'] or 0),
            'min_ram': (data['minimum_ram'] or 0),
            'name': data['name']}

    is_public = data.get('is_public', data.get('public', False))
    properties = {}
    # NOTE(tsufiev): in V2 the way how empty non-base attributes (AKA metadata)
    # are handled has changed: in V2 empty metadata is kept in image
    # properties, while in V1 they were omitted. Skip empty description (which
    # is metadata) to keep the same behavior between V1 and V2
    if data.get('description'):
        properties['description'] = data['description']
    if data.get('kernel'):
        properties['kernel_id'] = data['kernel']
    if data.get('ramdisk'):
        properties['ramdisk_id'] = data['ramdisk']
    if data.get('architecture'):
        properties['architecture'] = data['architecture']
    if api.glance.VERSIONS.active < 2:
        meta.update({'is_public': is_public, 'properties': properties})
    else:
        meta['visibility'] = 'public' if is_public else 'private'
        meta.update(properties)

    return meta

class CreateImageForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255, label=_("Name"))
    description = forms.CharField(widget=forms.widgets.Textarea(
        attrs={'class': 'modal-body-fixed-width', 'rows': 2}),
        label=_("Description"),
        required=False)
    source_type = forms.ChoiceField(
                                     label=_('Image Source'),
                                     required=False,
                                     choices=[('url', _('Image Location')),
                                     ('file', _('Image File'))],
                                     widget=forms.Select(attrs={
            			     'class': 'switchable',
            			     'data-slug': 'source'}))

    copy_from = forms.CharField(max_length=255,
                                label=_("Image Location"),
                                help_text=_("An external (HTTP) URL to load "
                                            "the image from."),
                                widget=forms.TextInput(attrs={
                                    'class': 'switched',
                                    'data-switch-on': 'source',
                                    'data-source-url': _('Image Location'),
                                    'ng-model': 'copyFrom',
                                    'ng-change':
                                    'selectImageFormat(copyFrom)'}),
                                required=False)

    image_file = forms.FileField(label=_("Load File"),
                                 help_text=_("A local image to upload."),
                                 widget=forms.FileInput(attrs={
                                     'class': 'switched',
                                     'data-switch-on': 'source',
                                     'data-source-file': _('Load File'),
                                     'ng-model': 'imageFile',
                                     'ng-change':
                                     'selectImageFormat(imageFile.name)',
                                     'image-file-on-change': None}),
				required=False)

    disk_format = forms.ChoiceField(label=_('Format'),
                                    choices=[],
                                    widget=forms.Select(attrs={
                                        'class': 'switchable',
                                        'ng-model': 'diskFormat'}))

    architecture = forms.CharField(max_length=255, label=_("Architecture"),
                                   widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                                   required=False)

    minimum_disk = forms.IntegerField(label=_("Minimum Disk (GB)"),
                                    min_value=0,
                                    help_text=_('The minimum disk size'
                                            ' required to boot the'
                                            ' image. If unspecified, this'
                                            ' value defaults to 0'
                                            ' (no minimum).'),
                                    required=False)

    minimum_ram = forms.IntegerField(label=_("Minimum RAM (MB)"),
                                    min_value=0,
                                    help_text=_('The minimum memory size'
                                            ' required to boot the'
                                            ' image. If unspecified, this'
                                            ' value defaults to 0 (no'
                                            ' minimum).'),
                                    required=False)

#    is_public = forms.BooleanField(label=_("Public"), required=False)
#    protected = forms.BooleanField(label=_("Protected"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(CreateImageForm, self).__init__(request, *args, **kwargs)
        #if (not settings.HORIZON_IMAGES_ALLOW_UPLOAD or
        if (api.glance.get_image_upload_mode() == 'off' or
                not policy.check((("image", "upload_image"),), request)):
            self._hide_file_source_type()
        if not policy.check((("image", "set_image_location"),), request):
            self._hide_url_source_type()
        if not policy.check((("image", "publicize_image"),), request):
            self._hide_is_public()

	self.fields['disk_format'].choices = IMAGE_FORMAT_CHOICES

    def _hide_file_source_type(self):
        self.fields['image_file'].widget = HiddenInput()
        source_type = self.fields['source_type']
        source_type.choices = [choice for choice in source_type.choices
                               if choice[0] != 'file']
        if len(source_type.choices) == 1:
            source_type.widget = HiddenInput()
    def _hide_url_source_type(self):
        self.fields['copy_from'].widget = HiddenInput()
        source_type = self.fields['source_type']
        source_type.choices = [choice for choice in source_type.choices
                               if choice[0] != 'url']
        if len(source_type.choices) == 1:
            source_type.widget = HiddenInput()

    def _hide_is_public(self):
        self.fields['is_public'].widget = HiddenInput()
        self.fields['is_public'].initial = False
    
    def clean(self):
        data = super(CreateImageForm, self).clean()
        # The image_file key can be missing based on particular upload
        # conditions. Code defensively for it here...
        image_url = data.get('copy_from', None)
        image_file = data.get('image_file', None)
	if not image_url and not image_file:
            raise ValidationError(
                _("A image or external image location must be specified."))
        elif image_url and image_file:
            raise ValidationError(
                _("Can not specify both image and external image location."))
        else:
            return data

    def handle(self, request, data):
        # Glance does not really do anything with container_format at the
        # moment. It requires it is set to the same disk_format for the three
        # Amazon image types, otherwise it just treats them as 'bare.' As such
        # we will just set that to be that here instead of bothering the user
        # with asking them for information we can already determine.
	if data['disk_format'] in ('ami', 'aki', 'ari',):
            container_format = data['disk_format']
        else:
            container_format = 'bare'
        data['is_public'] = 'public'
        properties = {}
        if data.get('description'):
            properties['description'] = data['description']
        if data.get('kernel'):
            properties['kernel_id'] = data['kernel']
        if data.get('ramdisk'):
            properties['ramdisk_id'] = data['ramdisk']
        if data.get('architecture'):
            properties['architecture'] = data['architecture']

        meta = {'visibility': data['is_public'],
                'protected': False,
                'disk_format': data['disk_format'],
                'container_format': container_format,
                'min_disk': (data['minimum_disk'] or 0),
                'min_ram': (data['minimum_ram'] or 0),
                'name': data['name']}
        meta.update(properties)
        if (api.glance.get_image_upload_mode() != 'off' and
                policy.check((("image", "upload_image"),), request) and
                data.get('image_file', None)):
            meta['data'] = self.files['image_file']
        else:
            meta['copy_from'] = data['copy_from']

        try:
            image = api.glance.image_create(request, **meta)
            messages.success(request,
                _('Your image %s has been queued for creation.') %
                data['name'])
            if request.session.has_key('last_activity'):
                request.session['last_activity'] = int(time.time())
            return image
        except Exception:
            exceptions.handle(request, _('Unable to create new image.'))

class UpdateImageForm(forms.SelfHandlingForm):
    image_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(max_length=255, label=_("Name"))
    description = forms.CharField(
        widget=forms.widgets.Textarea(attrs={'class': 'modal-body-fixed-width', 'rows': 2}),
        label=_("Description"),
        required=False,
    )
    kernel = forms.CharField(
        max_length=36,
        label=_("Kernel ID"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
    )
    ramdisk = forms.CharField(
        max_length=36,
        label=_("Ramdisk ID"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
    )
    architecture = forms.CharField(
        label=_("Architecture"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
    )
    disk_format = forms.ChoiceField(
        label=_("Format"),
    )
    minimum_disk = forms.IntegerField(label=_("Minimum Disk (GB)"),
                                      min_value=0,
                                      help_text=_('The minimum disk size'
                                                  ' required to boot the'
                                                  ' image. If unspecified,'
                                                  ' this value defaults to'
                                                  ' 0 (no minimum).'),
                                      required=False)
    minimum_ram = forms.IntegerField(label=_("Minimum RAM (MB)"),
                                     min_value=0,
                                     help_text=_('The minimum memory size'
                                                 ' required to boot the'
                                                 ' image. If unspecified,'
                                                 ' this value defaults to'
                                                 ' 0 (no minimum).'),
                                     required=False)
    is_public = forms.BooleanField(label=_("Public"), required=False)
    #protected = forms.BooleanField(label=_("Protected"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(UpdateImageForm, self).__init__(request, *args, **kwargs)
        self.fields['disk_format'].choices = [(value, name) for value,
                                              name in IMAGE_FORMAT_CHOICES
                                              if value]
        if not policy.check((("image", "publicize_image"),), request):
            self.fields['public'].widget = forms.CheckboxInput(
                attrs={'readonly': 'readonly'})

    def handle(self, request, data):
        image_id = data['image_id']
        error_updating = _('Unable to update image "%s".')
        meta = create_image_metadata(data)

        try:
            image = api.glance.image_update(request, image_id, **meta)
            messages.success(request, _('Image was successfully updated.'))
            return image
        except Exception:
            exceptions.handle(request, error_updating % image_id)

class UploadFileForm(forms.SelfHandlingForm):
    name = forms.ChoiceField(label=_('Name'), choices=[])

    description = forms.CharField(widget=forms.widgets.Textarea(
        attrs={'class': 'modal-body-fixed-width', 'rows': 4}),
        label=_("Description"),
        required=False)
    image_file = forms.FileField(label=_("Load File"),
                                 help_text=_("A local file to upload."),
                                 widget=forms.FileInput(attrs={
                                     'class': 'switched',
                                     'data-switch-on': 'source',
                                     'data-source-file': _('Load File'),
                                     'ng-model': 'File',
                                     'ng-change':
                                     'selectImageFormat(File.name)',
                                     'image-file-on-change': None}),
                                 required=False)
    #is_public = forms.BooleanField(label=_("Public"), required=False)
    #protected = forms.BooleanField(label=_("Protected"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(UploadFileForm, self).__init__(request, *args, **kwargs)
        if (api.glance.get_image_upload_mode() == 'off' or
                not policy.check((("image", "upload_image"),), request)):
            self._hide_file_source_type()
        if not policy.check((("image", "publicize_image"),), request):
            self._hide_is_public()
	self.fields['name'].choices = NAME_CHOICES

    def _hide_file_source_type(self):
        self.fields['image_file'].widget = HiddenInput()

    def _hide_is_public(self):
        self.fields['is_public'].widget = HiddenInput()
        self.fields['is_public'].initial = False

    def clean(self):
        data = super(UploadFileForm, self).clean()
	image_file = data.get('image_file', None)
        if not image_file:
            raise ValidationError(
                _("A file location must be specified."))
        else:
            return data

    def handle(self, request, data):
        container_format = 'bare'
        data['is_public'] = True
        data['disk_format'] = 'raw'
        properties = {}
        if data.get('description'):
            properties['description'] = data['description']
        properties['image_type'] = 'file' 
        meta = {'public': 'public',
                'protected': False,
                'disk_format': data['disk_format'],
                'container_format': container_format,
                'min_disk': 0,
                'min_ram': 0,
                'name': data['name'],
                #'properties': {'image_type': 'file'},
                'data': self.files['image_file']}
        meta.update(properties)
        LOG.info("properties ========================%s" % meta)
        try:
            image = api.glance.image_create(request, **meta)
            messages.success(request,
                _('Your file %s has been queued for upload.') %
                data['name'])
            return image
        except Exception:
            exceptions.handle(request, _('Unable to upload the file.'))

class DownloadImageForm(forms.SelfHandlingForm):
    image_id = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(label =_('name'))
    disk_format = forms.CharField(label=_("Format"), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    def __init__(self, request, *args, **kwargs):
        super(DownloadImageForm, self).__init__(request, *args, **kwargs)
        self.fields['image_id'].initial = kwargs['initial']['image'].id
        self.fields['name'].initial = kwargs['initial']['image'].name
        self.fields['disk_format'].initial = kwargs['initial']['image'].disk_format

    def handle(self, request, data):
        filename = '.'.join([data['name'], data['disk_format']])
        request.session['filename'] = filename
        request.session['data'] = data
        Parameter = json.dumps([data['image_id'], data['name'], data['disk_format']])
        return HttpResponseRedirect('/dashboard/admin/images/downloadimage?data=%s' % Parameter)
