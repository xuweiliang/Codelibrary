
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

ALIAS = "os-cdrom"
LOG = logging.getLogger(__name__)

class CDromController(wsgi.Controller):
    """the Documents API Controller declearation"""
    def __init__(self):
        super(CDromController, self).__init__()
        self.compute_api = compute.API()

    #@wsgi.Controller.api_version("2.1", "2.5")
    @extensions.expected_errors(404)
    def index(self, req, server_id):
        context = req.environ['nova.context']
        instance = common.get_instance(self.compute_api, context, server_id) 
        try:
            cdroms = self.compute_api.cdrom_list(context, instance)
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())
        except NotImplementedError:
            msg = _("does not support this function.")
            raise webob.exc.HTTPNotImplemented(explanation=msg)

        LOG.info("cdroms ======================%s" % cdroms)
        return {'cdroms':cdroms}

    @extensions.expected_errors(404)
    def create(self, req, server_id, body):
        """Attach a cdrom to an instance."""
        context = req.environ['nova.context']
        #context.can(c_policies.BASE_POLICY_NAME)
        if not self.is_valid_body(body, 'cdromAttachment'):
            msg = _("cdromAttachment not specified")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            image_id = body['cdromAttachment']['imageId']
            dev = body['cdromAttachment']['dev']
            #server_id = body['cdromAttachment']['server_id']
        except KeyError:
            msg = _("volumeId must be specified.")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            instance = common.get_instance(self.compute_api, 
                                          context, server_id)

            cdrom = self.compute_api.attach_cdrom(
                                      context, instance, dev,
                                                    image_id)
        except exception.NotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except exception.InstanceIsLocked as e:
            raise exc.HTTPConflict(explanation=e.format_message())
        #except exception.InstanceInvalidState as state_error:
        #    common.raise_http_conflict_for_instance_invalid_state(state_error,
        #            'attach_cdrom')
        if cdrom is None:
            cdrom = {}

        return {'attachcdrom':cdrom}


class Cdrom(extensions.V21APIExtensionBase):
    """Documents ExtensionDescriptor implementation"""

    name = "CDrom"
    alias = ALIAS
    version = 1

    def get_resources(self):
        resource = extensions.ResourceExtension(ALIAS, CDromController(),
                   parent=dict(member_name='server', collection_name='servers'))
        return [resource]

    def get_controller_extensions(self):
        return []
