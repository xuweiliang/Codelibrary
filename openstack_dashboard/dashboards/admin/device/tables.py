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
from django.core.urlresolvers import reverse
from django import shortcuts

from horizon import exceptions
from horizon import messages
from horizon import tables

from openstack_dashboard import api
from openstack_dashboard import policy
LOG = logging.getLogger(__name__)


def is_status(device):
    status = getattr(device, "status", None)
    if not status:
        return False
    return status.lower() == "on-line"

class AllReboot(tables.LinkAction):
    name = "allreboot"
    verbose_name = _("All Reboot")
    url = "horizon:admin:device:allreboot"
    classes = ("ajax-modal", "btn-migrate")

    def allowed(self, request, datum):
        return True

#    def get_link_url(self, datum):
#        id = self.table.get_object_id(datum)
#        url = reverse(self.url)
#        base_url = '?'.join([url, urlencode({'id':id})])
#        return base_url

class UpdateDevice(tables.LinkAction):
    name = "edit"
    verbose_name = _("Update Device")
    url = "horizon:admin:device:update"
    classes = ("ajax-modal", "btn-migrate")

    def allowed(self, request, datum):
        if datum and datum.status == 'off-line':
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        return True


class DeleteDevice(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Device",
            u"Delete Devices",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Device",
            u"Deleted Devices",
            count
        )
    policy_rules = (("admin", "admin:delete"),)

    def allowed(self, request, datum):
        return True

    def delete(self, request, obj_id):
        api.device.delete(request, obj_id)

class StartDevice(policy.PolicyTargetMixin, tables.BatchAction):
    name = "start"
    policy_rules = (("admin","admin:start"),)
    policy_target_attrs = (("device_id", "id"),)
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Start Device",
            u"Start Devices",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Start Device",
            u"Start Devices",
            count
        )

    def allowed(self, request, datum):
        if datum and datum.status == 'on-line':
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        return True

    def handle(self, data_table, request, obj_id):
        response = shortcuts.redirect(request.build_absolute_uri())
        result=api.device.start_device(request, obj_id)
        if result == 0:
            msg=_('Wake up device boot.')
            messages.success(request, msg)
        elif result == 3:
            msg=_('All devices have been sent to restart the command.')
            messages.success(request, msg)
        else:
            msg=_('Fail to wake up device boot.')
            messages.error(request, msg)
        return response

class SendMessage(tables.LinkAction):
    name='message'
    verbose_name = _("Send Message")
    url = "horizon:admin:device:message"
    classes = ("ajax-modal", "btn-migrate")

    def allowed(self, request, datum):
        if datum and datum.status == 'off-line':
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        return True

class RebootDevice(policy.PolicyTargetMixin, tables.BatchAction):
    name='reboot'
    policy_rules = (("admin","admin:reboot"),)
    policy_target_attrs = (("device_id", "id"),)
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Reboot Device",
            u"Reboot Devices",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Reboot Device",
            u"Reboot Devices",
            count
        )

    def allowed(self, request, datum):
        if datum and datum.status == 'off-line':
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        return True

    def handle(self, data_table, request, obj_id):
        response = shortcuts.redirect(request.build_absolute_uri())
        result = api.device.reboot_device(request, obj_id)
        if result == 0:
            msg=_('This device has been successfully restarted.')
            messages.success(request, msg)
        elif result == 3:
            msg=_('Restart command has been sent.')
            messages.success(request, msg)
        else:
            msg=_('Failed to restart, Connection refused')
            messages.error(request, msg)
        return response

class StopDevice(policy.PolicyTargetMixin, tables.BatchAction):
    name='dev_stop'
    policy_rules = (("admin","admin:dev_stop"),)
    policy_target_attrs = (("device_id", "id"),)
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Stop Device",
            u"Stop Devices",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Stop Device",
            u"Stop Devices",
            count
        )

    def allowed(self, request, datum):
        if datum and datum.status == 'off-line':
            if "disabled" not in self.classes:
                self.classes = [c for c in self.classes] + ['disabled']
        return True

    def handle(self, data_table, request, obj_id):
        response = shortcuts.redirect(request.build_absolute_uri())
        result = api.device.poweroff_device(request, obj_id)
        if result == 0:
            msg=_('The device has been successfully closed.')
            messages.success(request, msg)
        elif result == 3:
            msg=_('Shutdown command has been sent.')
            messages.success(request, msg)
        else:
            msg=_('Unable to close, connection denied')
            messages.error(request, msg)
        return response

class DeviceTable(tables.DataTable):

    dev_id = tables.Column("id",
                           verbose_name=_("Number"))

    host = tables.Column("hostname",
                           classes=["host"],
                           verbose_name=_("Host Name"))

    ip = tables.Column('ip',
                       classes=["ip"],
                       verbose_name=_("IP Address"),
                       attrs={'data-type': "ip"})
    mac = tables.Column('MAC',
                         verbose_name=_("MAC Address"),
                         attrs={'id': 'size'})

    gateway = tables.Column("gateway",
                               verbose_name=_("Gateway"))

    status = tables.Column("status",
                           classes=["status"],
                           verbose_name=_("Connect Status"))

    created = tables.Column("created_at",
                            verbose_name=_("Register Time"))

    system = tables.Column("system",
                           verbose_name=_("Operating System"))
   
    cpu = tables.Column("cpu",
                        verbose_name=_("CPU"))

    memory = tables.Column("memory",
                           verbose_name=_("Memory"))

    version = tables.Column("version",
                            verbose_name=_("Version Number"))
    
    user = tables.Column("user", verbose_name=_("Login User"))

    name = tables.Column("binding_instance",
                         verbose_name=_("Relation Instance"))

    class Meta:
        name = "device"
        verbose_name = _("Device Manage")
        table_actions = (DeleteDevice, StartDevice, StopDevice, RebootDevice)
        row_actions =(DeleteDevice, StartDevice, RebootDevice, StopDevice, SendMessage, UpdateDevice)
