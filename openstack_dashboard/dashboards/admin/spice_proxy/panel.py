#__author__ = "Zero"

from django.utils.translation import ugettext_lazy as _

import horizon

class SpiceProxyPanel(horizon.Panel):
    name = _("Spice Proxy")
    slug = 'spice_proxy'
    permissions = ('openstack.services.network',)

