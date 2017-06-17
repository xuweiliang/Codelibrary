# Copyright 2013 Metacloud, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import logging
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.utils.http import urlencode
from horizon import tables
from horizon.utils import filters
LOG = logging.getLogger(__name__)


class AuditTable(tables.DataTable):
    ACTION_DISPLAY_CHOICES = (
        ("create", pgettext_lazy("Action log of an instance", u"Create")),
        ("pause", pgettext_lazy("Action log of an instance", u"Pause")),
        ("unpause", pgettext_lazy("Action log of an instance", u"Unpause")),
        ("rebuild", pgettext_lazy("Action log of an instance", u"Rebuild")),
        ("resize", pgettext_lazy("Action log of an instance", u"Resize")),
        ("confirmresize", pgettext_lazy("Action log of an instance",
                                        u"Confirm Resize")),
        ("suspend", pgettext_lazy("Action log of an instance", u"Suspend")),
        ("resume", pgettext_lazy("Action log of an instance", u"Resume")),
        ("reboot", pgettext_lazy("Action log of an instance", u"Reboot")),
        ("stop", pgettext_lazy("Action log of an instance", u"Stop")),
        ("start", pgettext_lazy("Action log of an instance", u"Start")),
    )

    request_id = tables.Column('request_id',
                               verbose_name=_('Request ID'))
    action = tables.Column('action', verbose_name=_('Action'),
                           display_choices=ACTION_DISPLAY_CHOICES)
    start_time = tables.Column('start_time', verbose_name=_('Start Time'),
                               filters=[filters.parse_isotime])
    user_id = tables.Column('user_id', verbose_name=_('User ID'))
    message = tables.Column('message', verbose_name=_('Message'))

    class Meta(object):
        name = 'audit'
        verbose_name = _('Instance Action List')

    def get_object_id(self, datum):
        return datum.request_id

class Createdevsnapshot(tables.LinkAction):
    name = "createdevsnapshot"
    verbose_name = _("Create Devsnapshot")
    classes = ("ajax-modal", "btn-migrate")

    def get_link_url(self):
        return self.name

class DeleteDevsnapshot(tables.LinkAction):
    name = "deletedevsnapshot"
    verbose_name = _("Delete Devsnapshot")
    classes = ("ajax-modal", "btn-migrate")

    def allowed(self, request, datum):
        return True

    def get_link_url(self, datum):
        param = urlencode({"name":datum['name']})
        next_url = '?'.join([self.name, param])
        return next_url

class SetDevsnapshot(tables.LinkAction):
    name = "setdevsnapshot"
    verbose_name = _("Set Plan Devsnapshot")
    classes = ("ajax-modal", "btn-migrate")

    def allowed(self, request, datum):
        return True

    def get_link_url(self, datum):
        param = urlencode({"name":datum['name']})
        next_url = '?'.join([self.name, param])
        return next_url

class RevertDevsnapshot(tables.LinkAction):
    name = "revertdevsnapshot"
    verbose_name = _("Revert Devsnapshot")
    classes = ("ajax-modal", "btn-migrate")

    def allowed(self, request, instance):
        return True
        #return instance.status in SNAPSHOT_READY_STATES \
        #    and not is_deleting(instance)

    def get_link_url(self, datum):
        param = urlencode({"name":datum['name']})
        next_url = '?'.join([self.name, param])
        return next_url




class DevsnapshotTable(tables.DataTable):
    dev_snapshot_name = tables.Column('name', verbose_name=_('Snapshot Name'))

    class Meta:
        name = 'dev_sanpshot'
        verbose_name = _('Devsnapshot List')
        table_actions = (Createdevsnapshot,)
        row_actions = (DeleteDevsnapshot, SetDevsnapshot, RevertDevsnapshot,)


    def get_object_id(self, datum):
        return datum['id']

