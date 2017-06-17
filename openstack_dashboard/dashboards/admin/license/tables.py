from django.core.urlresolvers import reverse  # noqa
from django.utils.http import urlencode  # noqa
from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import tables

from openstack_dashboard import api
from openstack_dashboard.api import keystone


class CreateLicense(tables.LinkAction):
    name = "create"
    verbose_name = _("Certificate of registration")
    url = "horizon:admin:license:create"
    classes = ("ajax-modal",)


class DisplayTable(tables.DataTable):
    time = tables.Column('time', verbose_name=_('Registration Time'))
    closing_data  = tables.Column('during', verbose_name=_('Closing Date'))
    number = tables.Column('number', verbose_name=_('Instances Number'))
    available = tables.Column('available', verbose_name=_('Available Number'), status=True)

    class Meta:
        name = "license"
        verbose_name = _("Display")
        table_actions = (CreateLicense,)
