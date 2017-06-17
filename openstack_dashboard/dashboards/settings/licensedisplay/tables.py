from django.core.urlresolvers import reverse  # noqa
from django.utils.http import urlencode  # noqa
from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import tables

from openstack_dashboard import api
from openstack_dashboard.api import keystone




#class TenantFilterAction(tables.FilterAction):
#    def filter(self, table, tenants, filter_string):
#        """ Really naive case-insensitive search. """
#        # FIXME(gabriel): This should be smarter. Written for demo purposes.
#        q = filter_string.lower()

#        def comp(tenant):
#            if q in tenant.name.lower():
#                return True
#            return False

#        return filter(comp, tenants)

class CreateLicense(tables.LinkAction):
    name = "create"
    verbose_name = _("Certificate of registration")
    url = "horizon:admin:licensedisplay:create"
    classes = ("ajax-modal",)


class DisplayTable(tables.DataTable):
    time = tables.Column('time', verbose_name=_('Registration Time'))
    closing_data  = tables.Column('during', verbose_name=_('Closing Date'))
    number = tables.Column('number', verbose_name=_('Instances Number'))
    available = tables.Column('available', verbose_name=_('Available Number'), status=True)

    class Meta:
        name = "license"
        verbose_name = _("Display")
       # row_actions = (UpdateProject,
       #                UsageLink, ModifyQuotas,)
        table_actions = (CreateLicense,)
       # pagination_param = "tenant_marker"
