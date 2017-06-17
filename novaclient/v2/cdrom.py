# Copyright 2013 Rackspace Hosting
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import six
from six.moves.urllib import parse
from novaclient import api_versions

from novaclient import base
import logging
LOG = logging.getLogger(__name__)

class CDrom(base.Resource):
    """
    A cdrom is an extra block level storage to the OpenStack instances.
    """
    NAME_ATTR = 'display_name'

    def __repr__(self):
        return '<Server: %s>' % getattr(self, '_info')
        #return '<Server: %s>' % getattr(self, 'name', 'unknown-name')

class CDromManager(base.ManagerWithFind):
    resource_class = CDrom
    def get(self, server):
        pass

    def update(self, guofu, id):
        pass
#        data = datetime.datetime.today()
#        time = data.strftime("%Y-%m-%d %H:%M:%S")
#        body = {'licence': {'guofudata':guofu}}
#        LOG.error("AABB %s" % guofudata)
#        return self._update("/os-cipher/%s" % id, body, "cipher")

    def delete(self):
        pass

    def list(self):
        pass
    #@api_versions.wraps('2.26')
    def cdrom_list(self, server):
        """
        List attached CDROM device

        :param server: The :class:`Server` (or its ID) to query.
        """
        #LOG.info("cdrom_list ==================%s" % server_id)
        cdroms =  self._list('/servers/%s/os-cdrom' %  base.getid(server), 'cdroms')
        #cdroms =  self._list('/os-cdrom?instance_id=%s' % base.getid(server), 'cdroms')
        return cdroms

    def attach_server_cdrom(self, server_id, dev, image_id):
        """
        Attach a volume identified by the image ID to the given server ID

        :param server_id: The ID of the server
        :param image_id: The ID of the image to attach.
        
        """
        LOG.info("attach_server_cdrom =======================%s" % dev)
        body = {'cdromAttachment': {'dev':dev,'imageId': image_id}}
        #cdrom = self._create("/os-cdrom",  body, "attachcdrom")
        cdrom = self._create("/servers/%s/os-cdrom" % server_id,  body, "attachcdrom")
	return cdrom

