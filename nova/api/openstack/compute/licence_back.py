
from oslo_utils import strutils
import webob
#import datetime
#from nova.policies import licence as li_policies
#from nova.api.openstack.api_version_request \
#    import MAX_PROXY_API_SUPPORT_VERSION
from nova.api.openstack import common
from nova import compute
from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from oslo_log import log as logging
from nova import exception
from nova.i18n import _
from nova import utils

ALIAS = "os-licence"
LOG = logging.getLogger(__name__)

class LicenceController(wsgi.Controller):
    """the Documents API Controller declearation"""
    def __init__(self):
        super(LicenceController, self).__init__()
        self.licence_api = compute.LicenceAPI()

    @extensions.expected_errors(404)
    #@wsgi.response(200)
    @wsgi.Controller.api_version("2.1", MAX_PROXY_API_SUPPORT_VERSION)
    def show(self, req, id):
        context = req.environ['nova.context']
        #context.can(li_policies.BASE_POLICY_NAME)
        #import pdb
        #pdb.set_trace()
        try:
            licence = self.licence_api.get_licence_by_id(context)
        #ct = getattr(licence, 'created_at')
        #rt = getattr(licence, 'starttime')
#        ct = licence.created_at
#        rt = licence.starttime
#        setattr(licence, 'probation', False)
#        if ct and rt:
#            created_time = datetime.datetime(ct.year, ct.month,\
#                                             ct.day, ct.hour, ct.minute)
#            run_time = datetime.datetime(rt.year, rt.month,\
#                                             rt.day, rt.hour, rt.minute)
#            probation_at = created_time + datetime.timedelta(days = 30)
#            if run_time <= probation_at:
#                setattr(licence, 'probation', True)
        except:
            raise webob.exc.HTTPNotFound(explanation="Licence not found")
        return {'licence':licence}

    @extensions.expected_errors(404)
    def update(self, req, id, body):
        context = req.environ['nova.context']
        kwargs = body.pop('licence')
        try:
            self.licence_api.update_licence(context, **kwargs)
        except:
            raise webob.exc.HTTPNotFound(explanation="Licence can not update")


class Licence(extensions.V21APIExtensionBase):
    """Documents ExtensionDescriptor implementation"""

    name = "Licence"
    alias = ALIAS
    version = 1

    def get_resources(self):
        resource = extensions.ResourceExtension(ALIAS, LicenceController())
        return [resource]

    def get_controller_extensions(self):
        return []
