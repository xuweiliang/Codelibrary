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
#"""class Licence(base.NovaPersistentObject,
#   base.NovaObject, base.NovaObjectDictCompat):"""
class Licence(base.NovaObject, base.NovaObjectDictCompat):


    VERSION = '1.1'
    
    fields = {
        'id':fields.IntegerField(),
        'starttime': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'created_at': fields.DateTimeField(nullable=True),
        'system_uuid': fields.StringField(nullable=True),
        'encrypted_license': fields.StringField(nullable=True),
        'disabled': fields.BooleanField(),
        'used':fields.IntegerField(nullable=True),
        }

    @staticmethod
    def _from_db_object(context, licence, db_licence):
        for field in licence.fields:
            licence[field] = db_licence[field]
        licence._context = context
        licence.obj_reset_changes()
        return licence

    @base.remotable_classmethod
    def get_by_licence_id(cls, context, session):
        db_licence = db.get_licence(context, 1, session=session)
        if db_licence:
            return cls._from_db_object(context, cls(), db_licence)


    @base.remotable_classmethod
    def session(cls, context):
        alchemy = importutils.import_module('sqlalchemy.orm')
        Session = alchemy.sessionmaker()
        engine = db.get_engine(context)
        Session.configure(bind=engine)
        return Session()

    @base.remotable_classmethod
    def save(cls, context, session, **kwargs):
        db_licence = db.update_licence(context, 1, session=session, **kwargs)
        if db_licence:
            return True
