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


import pytz
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import workflows
from datetime import datetime

from openstack_dashboard import api

import logging
LOG=logging.getLogger(__name__)

class SetSingleTimingAction(workflows.Action):
    single = forms.CharField(label=_("Time"),
                           widget=forms.TextInput(attrs={'type':'datetime-local'}),
                           required=False)

    def clean(self):
        cleaned_data = super(SetSingleTimingAction, self).clean()
        single = cleaned_data.get("single", None)
        if not single:
            msg = _("Must fill time")
            self._errors['single']=self.error_class([msg])
        tz = pytz.timezone(pytz.country_timezones('cn')[0])
        now = datetime.now(tz)
        localtime = datetime(now.year, now.month,\
                              now.day, now.hour, now.minute)
        if single:
            singletime = datetime.strptime(single, "%Y-%m-%dT%H:%M")
            if singletime < localtime:
                msg = _("input time Invalid should not be less than the current time")
                self.errors['single']=self.error_class([msg])
        return cleaned_data


    class Meta:
        name = _("Set Timing")
        slug = 'single_set'
        help_text = _("The time you need to enter is not empty.")

    def __init__(self, request, context, *args, **kwargs):
        super(SetSingleTimingAction, self).__init__(request, context, *args, **kwargs)

    def handle(self, request, data):
        try:
            api.nova.update_timing_time(request, data)
            return True
        except Exception:
            exceptions.handle(request, ignore=True)
            return False


class SetSingleTiming(workflows.Step):
    action_class = SetSingleTimingAction
    depends_on = ("instance_id",)
    contributes = ("single")
    def contribute(self, data, context):
        if data:
            context['checkboxlist']=context.get('instance_id', None)
            context[self.workflow.slug]=self.workflow.slug
            if data.get('single', None):
                context['timing_time']=data['single']
        return context


class SingleTimingBoot(workflows.Workflow):
    slug = "timing_boot"
    name = _("Timing Boot")
    finalize_button_name = _("Save")
    success_message = _("Save instance timing boot time '%s'.")
    failure_message = _("Unable save instance timing boot time '%s'.")
    success_url = "horizon:admin:instances:index"
    default_steps = (SetSingleTiming,)

    def format_status_message(self, message):
        return message % self.context.get('timing_time', 'unknown time')

class SingleTimingShutdown(workflows.Workflow):
    slug = "timing_shutdown"
    name = _("Timing Shutdown")
    finalize_button_name = _("Save")
    success_message = _("Save instance timing shutdown time '%s'.")
    failure_message = _("Unable save instance timing showdown time '%s'.")
    success_url = "horizon:admin:instances:index"
    default_steps = (SetSingleTiming,)

    def format_status_message(self, message):
        return message % self.context.get('timing_time', 'unknown time')


