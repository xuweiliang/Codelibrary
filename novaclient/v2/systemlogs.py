from novaclient import base
from novaclient.v2 import encoding
import logging
LOG = logging.getLogger(__name__)

class Systemlog(base.Resource):

    def __repr___(self):
        return "<Systemlog>"

class SystemlogManager(base.ManagerWithFind):
    resource_class = Systemlog

    def create(self, name, event_subject, result, details):
        """Create action logs."""
        details = encoding.force_text(details)
        body = {'systemlog': {'name': name,
                              'event_subject': event_subject,
                              'result': result,
                              'details': details}}
        return self._create('/os-systemlogs', body, 'systemlog')

    def list(self,filters=None):
        '''Get list of system logs.'''
        if filters:
            url = "/os-systemlogs?filters=%s" % filters
        else:
            url = "/os-systemlogs"
        LOG.info("list =======================%s" % filters)
        return self._list(url, "systemlogs")

