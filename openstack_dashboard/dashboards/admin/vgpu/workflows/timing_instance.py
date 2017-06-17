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
import logging
import pytz

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.views.decorators.debug import sensitive_variables  # noqa

from horizon import exceptions
from horizon import forms
from horizon.utils import validators
from horizon import workflows
from openstack_dashboard import api
from datetime import datetime as date_time

LOG = logging.getLogger(__name__)


class TimingControlAction(workflows.Action):
    checkboxlist = forms.CharField(widget=forms.HiddenInput()) 
    weeklist = forms.CharField(widget=forms.HiddenInput()) 
    timing_mode = forms.ChoiceField(label=_("Select mode"),
                               initial="",
                               required=True,
                               help_text=_("Choose a timing mode"),
                               choices=[("", _("Select a Timing Mode")),
                                        ("single", _('Set single time')),
                                        ("loop", _('Set loop time'))])

    single= forms.CharField(label=_("Single Time"), 
                              widget=forms.TextInput(attrs={'type':'datetime-local'}),
                              required=False)

    loop = forms.CharField(label=_("Loop time"),
                               required=False,
                               widget=forms.TextInput(attrs={'type':'time'}),
                               help_text=_("Time format 24 hour system"))


    class Meta:
        name = _("Set Timing")
        help_text = _("Please select the instance option,"
                      "and the time you need to enter is not empty.")

    def __init__(self, request, context, *args, **kwargs):
        self.request = request
        self.context = context
        super(TimingControlAction, self).__init__(
			request, context, *args, **kwargs)
        self.fields['weeklist'].initial = False


    def clean(self):
        cleaned_data = super(TimingControlAction, self).clean()
        timing_mode = cleaned_data.get("timing_mode", None)
        single = cleaned_data.get("single", None)
        loop = cleaned_data.get("loop", None)
        checkbox = cleaned_data.get("checkboxlist", None)
        tz = pytz.timezone(pytz.country_timezones('cn')[0])
        if not checkbox:
            error_message=_("No instance option selected")
            raise forms.ValidationError(error_message)

        if timing_mode == "single" and not single:
            msg = _("Must fill time")
            self._errors['single']=self.error_class([msg])
        elif timing_mode == "single" and single:
            singleformat = date_time.now(tz).strftime('%Y-%m-%d %H:%M')
            singletime = date_time.strptime(single, "%Y-%m-%dT%H:%M")
            localtime = date_time.strptime(singleformat, "%Y-%m-%d %H:%M")
            if singletime < localtime:
                msg = _("input time Invalid should not be less than the current time")
                self._errors['single']=self.error_class([msg])



        weeklist = cleaned_data.get("weeklist", 'False')
        if timing_mode =="loop" and not loop:
            self.fields['weeklist'].initial = False
            msg =_("Must fill time")
            self._errors['loop']=self.error_class([msg])
        elif timing_mode == "loop" and eval(weeklist) is False:
            error_message=_("No choice week")
            raise forms.ValidationError(error_message)

#        tz = pytz.timezone(pytz.country_timezones('cn')[0])
#        singleformat = date_time.now(tz).strftime('%Y-%m-%d %H:%M')
#        if not single:
#            singletime = date_time.strptime(single, "%Y-%m-%dT%H:%M")
#            localtime = date_time.strptime(singleformat, "%Y-%m-%d %H:%M")
#            if singletime < localtime:
#                msg = _("input time Invalid should not be less than the current time")
#                self._errors['single']=self.error_class([msg])
#
#        loopformat = date_time.now(tz).hour
#        if timing_mode == "loop" and loop:
#            self.fields['weeklist'].initial = False
#            looptime = date_time.strptime(loop, "%H:%M")
#            if looptime.hour < loopformat:
#                msg = _("input time Invalid should not be less than the current time")
#                self._errors['loop']=self.error_class([msg])
#
#        weeklist = cleaned_data.get("weeklist", 'False')
#        if timing_mode == "loop" and eval(weeklist) is False:
#            error_message=_("No choice week")
#            raise forms.ValidationError(error_message)

        return cleaned_data

class TimingControl(workflows.Step):
    action_class = TimingControlAction
    contributes = ("single", "loop", "checkboxlist","weeklist")
    def contribute(self, data, context):
        if data:
            context['checkboxlist'] = data.get('checkboxlist', None)
            context[self.workflow.slug] = self.workflow.slug
            if data.get('single', None):
                context['timing_time'] =data['single'] 
            if data.get('loop', None) and data.get('weeklist', None):
                context['timing_time'] = {'loop':data['loop'], 'weeklist':data['weeklist']}
        return context


class TimingBoot(workflows.Workflow):
    slug = "timing_boot"
    name = _("Timing Boot")
    success_message = _('Set timing boot successfully.')
    failure_message = _('Unable to set timing boot instance.')
    success_url = "horizon:admin:vgpu:index"
    multipart = True
    default_steps = (TimingControl,)

    def format_status_message(self, message):
        checkboxlist = self.context.get('checkboxlist', '')
        checkbox = checkboxlist.split("_")
        timing_time = self.context.get('timing_time', '0000-00-00 00:00')
        if timing_time == "single":
            return message % {"time": _("time %s") % timing_time,
                              "count": len(checkbox)}
        else:
            return message % {"time": _("time week"), "count": len(checkbox)}

    @sensitive_variables('context')
    def handle(self, request, context):
        try:
            api.nova.instance_timing(request, context)
            return True
        except Exception:
            exceptions.handle(request)
            return False


class TimingShutdown(workflows.Workflow):
    slug = "timing_shutdown"
    name = _("Timing Shutdown")
    success_message = _('Set timing shutdown successfully.')
    failure_message = _('Unable to set timing shutdown instance.')
    success_url = "horizon:admin:vgpu:index"
    multipart = True
    default_steps = (TimingControl,)


    def format_status_message(self, message):
        checkboxlist = self.context.get('checkboxlist', '')
        checkbox = checkboxlist.split("_")
        timing_time = self.context.get('timing_time', '0000-00-00 00:00')
        if timing_time == "single":
            return message % {"time": _("time %s") % timing_time,
                              "count": len(checkbox)}
        else:
            return message % {"time": _("time week"), "count": len(checkbox)}

    @sensitive_variables('context')
    def handle(self, request, context):
        try:
            api.nova.instance_timing(request, context)
            return True
        except Exception:
            exceptions.handle(request)
            return False

