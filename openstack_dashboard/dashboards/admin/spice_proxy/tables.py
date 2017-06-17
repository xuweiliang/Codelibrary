from django.core.urlresolvers import reverse  # noqa
from django.utils.http import urlencode  # noqa
from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import tables

from openstack_dashboard import api

import logging

LOG = logging.getLogger(__name__)

class ProxyPattern(tables.LinkAction):
    name = "setting"
    verbose_name = _("Spice Proxy Setting")
    url = "horizon:admin:spice_proxy:update"
    classes = ("ajax-modal",)
    icon = "pencil"

class ModifyPort(tables.LinkAction):
    name = "modifyport"
    verbose_name = _("Modify Http Port")
    url = "horizon:admin:spice_proxy:modifyport"
    classes = ("ajax-modal",)
    icon = "pencil"
    def allowed(self, request, spice_proxy):
        if spice_proxy.spice_proxy_flug:
            return True
        else:
            return False

class DisplayTable(tables.DataTable):
    id_proxy = tables.Column('id', verbose_name=_('Id'))
    spice_proxy_flug  = tables.Column('enabled_spice_proxy', verbose_name=_('Enable Spice Proxy'))
    http_port = tables.Column('http_port', verbose_name=_('Http Port'))
    update_time = tables.Column('updated_at', verbose_name=_('Updated Time'))
    class Meta:
        name = "spice proxy"
        verbose_name = _("Spice Proxy")
        row_actions = (ProxyPattern, ModifyPort,)

