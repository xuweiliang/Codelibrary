
from nova import db
from nova.objects import base
from nova.objects import fields
from nova import objects
from oslo_utils import timeutils, importutils

import logging
LOG = logging.getLogger(__name__)

@base.NovaObjectRegistry.register
#class Systemlogs(base.NovaPersistentObject, base.NovaObjectA):
class Systemlogs(base.NovaObjectDictCompat, base.NovaObject):

    VERSION = '1.16'

    fields = {
        'id': fields.StringField(),
        'event_subject': fields.StringField(),
        'event_object': fields.StringField(),
        'created_at': fields.DateTimeField(),
        'user_name': fields.StringField(),
        'project_name': fields.StringField(),
        #'visit_ip': fields.IPAddressField(nullable=True),
        'visit_ip': fields.StringField(nullable=True),
        'result': fields.StringField(),
        'message': fields.StringField(),
    }

    @staticmethod
    def _from_db_object(context, action, db_logsinfo):
        for field in action.fields:
            action[field] = db_logsinfo[field]
        action._context = context
        action.obj_reset_changes()
        return action

    @staticmethod
    #@base.remotable_classmethod
    def get_session(context):
        alchemy = importutils.import_module('sqlalchemy.orm')
        Session = alchemy.sessionmaker()
        engine = db.get_engine(context)
        Session.configure(bind=engine)
        return Session()

    @base.remotable
    #@base.remotable_classmethod
    #@staticmethod
    def systemlogs_create(self, context):
        message = self.message.split(':')[-1]
        logsinfo = {'event_subject': self.event_subject,
                    'event_object': self.event_object,
                    #'action': self.action,
                    'visit_ip': self.visit_ip,
                    'result': self.result,
                    'message': message,
                    'user_name': self.user_name,
                    'project_name': self.project_name}

        #pdb.set_trace()
        setattr(context, 'Session', self.get_session(context))
        db_logsinfo = db.systemlogs_create(context, logsinfo)
        return self._from_db_object(context, self, db_logsinfo)

@base.NovaObjectRegistry.register
class SystemlogsList(base.ObjectListBase, base.NovaObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Systemlogs'),
        }
    child_versions = {
        '1.0': '1.0',
        }


    @base.remotable_classmethod
    def systemlogs_list(cls, context, session, filters=None):
        db_logsinfo = db.systemlogs_list(context,session, filters=filters)
        return base.obj_make_list(context, cls(context), objects.Systemlogs,
                                  db_logsinfo)
