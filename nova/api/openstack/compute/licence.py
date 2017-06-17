
from oslo_utils import strutils
import webob
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
    def show(self, req, id):
        context = req.environ['nova.context']
        try:
            licence = self.licence_api.get_licence_by_id(context)
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

