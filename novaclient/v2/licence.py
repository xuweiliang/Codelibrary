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
licence interface
"""

from novaclient import base
from novaclient import api_versions
from oslo_log import log as logging
LOG = logging.getLogger(__name__)


class Licence(base.Resource):
    def __repr__(self):
        return "<licence>"


class LicenceManager(base.ManagerWithFind):
    resource_class = Licence

    def list(self):
        pass


    def update(self, id, **kwargs):
        """Update an existing agent build."""
        body = dict()
        body.update(kwargs)
        return self._update('/os-licence/%s' % id, body, 'licence')

    #@api_versions.wraps('2.0', '2.5')
    def get(self, id):
        """
        Deletes an existing agent build.

        :param id: The agent's id to delete
        :returns: An instance of novaclient.base.TupleWithMeta
        """
        return self._get('/os-licence/%s' % id, "licence")

