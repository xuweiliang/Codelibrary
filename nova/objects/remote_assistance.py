#    Copyright 2013 IBM Corp.
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

from nova import db
from nova import objects
from nova.objects import base
from nova.objects import fields
from oslo_utils import timeutils, importutils
from oslo_log import log as logging
LOG = logging.getLogger(__name__)

# TODO(berrange): Remove NovaObjectDictCompat
@base.NovaObjectRegistry.register
class RemoteAssistance(base.NovaObject, base.NovaObjectDictCompat):


    VERSION = '1.1'
    
    fields = {
        'id':fields.IntegerField(),
        'instance_id': fields.UUIDField(),
        'created_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'client_ip': fields.IPAddressField(nullable=True),
        'instance_name': fields.StringField(nullable=True),
        'password':fields.IntegerField(nullable=True),
        'status': fields.StringField(nullable=True),
        }

    @staticmethod
    def _from_db_object(context, remote, db_remote):
        for field in remote.fields:
            remote[field] = db_remote[field]
        remote._context = context
        remote.obj_reset_changes()
        return remote


    @base.remotable_classmethod
    def create_remote_assistance(cls, context, *argws, **kwargs):
        db_remote = db.create_remote(context, *argws,  **kwargs)


    @base.remotable_classmethod
    def get_remote_assistance(cls, context, *argws):
        db_remote = db.get_remote_assistance(context, *argws)
        if not db_remote:
            return db_remote
        try:
            return cls._from_db_object(context, cls(), db_remote)
        except Exception:
            return db_remote


#    @base.remotable_classmethod
#    def delete_remote_assistance(cls, context, *args):
#        db_remote = db.delete_remote_assistance(context, *args)
#        if db_remote:
#            return db_remote


    @base.remotable_classmethod
    def update_remote_assistance(cls, context, *args, **kwargs):
        db_remote = db.update_remote_assistance(context, *args, **kwargs)


@base.NovaObjectRegistry.register
class RemoteAssistanceList(base.ObjectListBase, base.NovaObject):
    # Version 1.0: Initial version
    #              RemoteList <= version 1.1
    VERSION = '1.0'
    fields = {
        'objects': fields.ListOfObjectsField('RemoteAssistance'),
        }

    @base.remotable_classmethod
    def remote_assistance_list(cls, context, *args):
        db_remote = db.remote_assistance_list(context, *args)
        if db_remote:
            return base.obj_make_list(context, cls(),
                   RemoteAssistance, db_remote)
#        try:
#            return base.obj_make_list(context, cls(), 
#                   RemoteAssistance, db_remote)
#        except Exception:
#            return db_remote

