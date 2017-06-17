# Copyright 2012 IBM Corp.
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

"""
dev_snapshot interface
"""

from novaclient import base
from oslo_log import log as logging
LOG = logging.getLogger(__name__)


class Snapshot(base.Resource):
    def __repr__(self):
        return "<snapshot>"


class SnapshotManager(base.ManagerWithFind):
    resource_class = Snapshot

    def list(self, server):
        return self._list('/os-snapshot?instance_id=%s' 
                          % base.getid(server), 'snapshot')

    def create(self, **kwargs):
        """Create a dev snapshot."""
        body = dict()
        body.update(kwargs)
        return self._create('/os-snapshot', body, 'snapshot')

    def get(self, id):
        """
        Deletes an existing agent build.

        :param id: The agent's id to get
        :returns: An instance of novaclient.base.TupleWithMeta
        """
        return self._get('/os-snapshot/%s' % id, "snapshot")

    def delete(self, instance_id, name):
        """Delete a snapshot."""
        if not name:
            return 
        return self._delete("/os-snapshot/%s?name=%s" 
                            % (instance_id, name))


    def set_dev_snapshot(self, instance_id, name):
        return self._get("/os-snapshot/%s/set_dev_snapshot?name=%s" 
               % (instance_id, name), "snapshot")    

    def revert_dev_snapshot(self, instance_id, name):
        return self._get("/os-snapshot/%s/revert_dev_snapshot?name=%s"
               % (instance_id, name), "snapshot")
