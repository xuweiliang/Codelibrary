from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.compute import api as compute_api
import time as datetime
from datetime import datetime as time
#from nova.objects import fields
from nova import exception
#from nova import db
import webob
from nova import objects
from webob import exc

from nova.objects import base

import datetime
import logging
LOG = logging.getLogger(__name__)


class SystemLogsController(wsgi.Controller):
    def __init__(self):
        self.systemlogs_api = compute_api.SystemLogsAPI()

    def create(self, req, body):
        context = req.environ['nova.context']
        #authorize(context)
        logsinfo = body['systemlog']
        event_subject = logsinfo['event_subject']
        name = logsinfo['name']
        result = logsinfo['result']
        detail = logsinfo['details']
        try:
            loginfo = self.systemlogs_api.systemlogs_create(context, name, event_subject, result, detail)
            return {'systemlog': loginfo}
        except:
            raise webob.exc.HTTPNotFound(explanation="fail to save system logs")

    @extensions.expected_errors(404)
    def index(self, req):
        context = req.environ['nova.context']
        filters = req.GET.get('filters',None)
        try:
            systemlogs = self.systemlogs_api.systemlogs_list(context, filters)
        except:
            raise webob.exc.HTTPNotFound(explanation="There are some errors")
        data_log = []
        if filters and systemlogs:
            flags = filters.split('-')[1]
            if flags == 'time':
                number = int(filters.split('-')[0])
                for systemlog in systemlogs:
                    createtime = time.strptime(systemlog['created_at'].strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                    day = (time.now() - createtime).days
                    if number >= day:
                        systemlog['event_time'] = systemlog['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                        data_log.append(systemlog)
                return {'systemlogs': data_log}
            else:
                for systemlog in systemlogs:
                    systemlog['event_time'] = systemlog['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                return {'systemlogs': systemlogs}
        elif systemlogs:
            for systemlog in systemlogs:
                systemlog['event_time'] = systemlog['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return {'systemlogs': systemlogs}

class Systemlogs(extensions.V21APIExtensionBase):
    """Documents ExtensionDescriptor implementation"""

    name = "Systemlogs"
    alias = "os-systemlogs"
    version = 1

    def get_resources(self):
        resources = []
        res = extensions.ResourceExtension('os-systemlogs', SystemLogsController())
        resources.append(res)
        return resources

    def get_controller_extensions(self):
        return []
