from django.utils.translation import ugettext_lazy as _
from horizon import forms
from horizon import messages
from openstack_dashboard import api
from horizon import exceptions
from django.core.urlresolvers import reverse
import logging
LOG=logging.getLogger(__name__)

class ProxyPatternForm(forms.SelfHandlingForm):
    id = forms.CharField(widget=forms.HiddenInput())
    flug_proxy  = forms.BooleanField(label=_("Spice Proxy Flug"),required=False)

    def __init__(self, request, *args, **kwargs):
        super(ProxyPatternForm, self).__init__(request, *args, **kwargs)
        id = kwargs.get('initial', {}).get('id', [])
        spice_proxy_flug = kwargs.get('initial', {}).get('spice_proxy_flug', [])
        self.port = kwargs.get('initial', {}).get('http_port', [])
        if spice_proxy_flug:
            self.fields['flug_proxy'].initial = True
        else:
            self.fields['flug_proxy'].initial = False
        self.fields['id'] = forms.CharField(widget=forms.HiddenInput,initial=id)

    def handle(self, request, data):
        try:
            if data['flug_proxy']:
                spice_proxy_flug = 1
            else:
                spice_proxy_flug = 0
            http_port = self.port
            api.device.update_spice_proxy_pattern(request, {'spice_proxy_flug':spice_proxy_flug, 'http_port':http_port})
            msg = _('The spice proxy is setted successfully.')
            messages.success(request, msg)
            return True
        except Exception:
            msg = _('Failed to set spice proxy.')
            redirect = reverse('horizon:admin:spice_proxy:index')
            exceptions.handle(request, msg, redirect=redirect)

class ModifyPortForm(forms.SelfHandlingForm):
    id = forms.CharField(widget=forms.HiddenInput())
    http_port = forms.IntegerField(label=_("Http Port"), required=False, min_value=1025, max_value=65535, widget=None)

    def __init__(self, request, *args, **kwargs):
        super(ModifyPortForm, self).__init__(request, *args, **kwargs)
        id = kwargs.get('initial', {}).get('id', [])
        self.spice_proxy_flug = kwargs.get('initial', {}).get('spice_proxy_flug', [])
        self.fields['id'] = forms.CharField(widget=forms.HiddenInput,initial=id)
            
    def handle(self, request, data):
        try:
            http_port = int(data['http_port'])
            if self.spice_proxy_flug:
                spice_proxy_flug=self.spice_proxy_flug
            else:
                spice_proxy_flug=1
            api.device.update_spice_proxy_pattern(request, {'spice_proxy_flug':spice_proxy_flug, 'http_port':http_port})
            msg = _('The http port is altered successfully.')
            messages.success(request, msg)
            return True
        except Exception:
            msg = _('Failed to alter http port.')
            redirect = reverse('horizon:admin:spice_proxy:index')
            exceptions.handle(request, msg, redirect=redirect)

