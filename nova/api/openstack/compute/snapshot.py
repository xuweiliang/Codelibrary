
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

ALIAS = "os-snapshot"
LOG = logging.getLogger(__name__)

class SnapshotController(wsgi.Controller):
    """the Documents API Controller declearation"""

    def __init__(self):
        super(SnapshotController, self).__init__()
        self.compute_api = compute.API()

    def _get_params(self, req, key):
        if key:
            return req.params.get(key, None)
        return

    @extensions.expected_errors((400, 404, 501))
    def revert_dev_snapshot(self, req, id):
        context = req.environ['nova.context']
        name = self._get_params(req, "name")
        try:
            instance = common.get_instance(self.compute_api,
                                                context, id)
            self.compute_api.dev_snapshot_revert(context, instance, name)
        except exception.NotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except NotImplementedError:
            msg = _("set recovery function error.")
            raise webob.exc.HTTPNotImplemented(explanation=msg)
        return {"snapshot":{"execute":True}}

    @extensions.expected_errors((400, 404, 501))
    def set_dev_snapshot(self, req, id):

        context = req.environ['nova.context']
        name = self._get_params(req, "name")
        try:
            instance = common.get_instance(self.compute_api,
                                        context, id)
            if name:
                instance.dev_snapshot = name
                instance.save()
        except exception.NotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except NotImplementedError:
            msg = _("set recovery function error.")
            raise webob.exc.HTTPNotImplemented(explanation=msg)
        return {"snapshot":{"execute":True}}

    @extensions.expected_errors(404)
    def index(self, req):
        context = req.environ['nova.context']
        instance_id = self._get_params(req, "instance_id")
        instance = common.get_instance(self.compute_api,
                                     context, instance_id)
        try:
            snapshot = self.compute_api.dev_snapshot_list(context, instance)
        except exception.NotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except NotImplementedError:
            msg = _("does not support this function.")
            raise webob.exc.HTTPNotImplemented(explanation=msg)
        return {'snapshot':snapshot}


    @extensions.expected_errors(400)
    def create(self, req, body):
        context = req.environ['nova.context']
        if 'instance_id' not in body['snapshot'] \
            and 'name' not in body['snapshot']:
            return
        instance_id = body['snapshot']['instance_id']
        snapshot_name = body['snapshot']['name']
        try:
            instance = common.get_instance(self.compute_api,
                                            context, instance_id)
            self.compute_api.dev_snapshot_create(context, instance, snapshot_name)
        except exception.NotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except NotImplementedError:
            msg = _("create dev snapshot function error.")
            raise webob.exc.HTTPNotImplemented(explanation=msg)
        return {"snapshot":{"execute":True}}

    @extensions.expected_errors(400)
    def delete(self, req, id):
        context = req.environ['nova.context']
        name = self._get_params(req, 'name')
        try:
            instance = common.get_instance(self.compute_api,
                                            context, id)
            self.compute_api.dev_snapshot_delete(context, instance, name)
        except exception.NotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except NotImplementedError:
            msg = _("delete dev snapshot function error.")
            raise webob.exc.HTTPNotImplemented(explanation=msg)




class DevSnapshot(extensions.V21APIExtensionBase):
    """Documents ExtensionDescriptor implementation"""

    name = "DevSnapshot"
    alias = ALIAS
    version = 1

    def get_resources(self):
        resource = extensions.ResourceExtension(ALIAS, SnapshotController(),
                   member_actions={'set_dev_snapshot':'GET',
                                   'revert_dev_snapshot':'GET'})
        return [resource]

    def get_controller_extensions(self):
        return []
