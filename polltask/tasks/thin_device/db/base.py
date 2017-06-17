from polltask import config
from oslo_config import cfg
from polltask.tasks.tools import utils
from polltask.i18n import _, _LE
import MySQLdb


config = config.get_default_config()
_DB_USER = config.get_option_value('database','db_user')
_DB_PW= config.get_option_value('database','db_pw')
_DB_PORT = config.get_option_value('database','db_port')
_DB_HOST = config.get_option_value('database','db_host')
_CONNECT= cfg.StrOpt('db_module', 
                 default='MySQLdb',
                 help='The to connet database module')
_DB = cfg.StrOpt('database',
                 default='device',
                 help='The to connet databse')
CONF = cfg.CONF
CONF.register_opt(_DB)
CONF.register_opt(_CONNECT)


def _connect(db_module=None, *args, **kwargs):
    if not db_module:
        db = utils.import_module(CONF.db_module)
    else:
        db = utils.import_module(db_module)
    return db.connect(*args, **kwargs)

class Base(object):
    def __init__(self, db_module=None):
        self.db_module = CONF.db_module

    def create_database(self):
        try:
            conn =  _connect(host=_DB_HOST,user=_DB_USER, passwd=_DB_PW)
            cur=conn.cursor() 
            cur.execute('create database if not exists device') 
            cur.execute('alter database device default character set utf8 collate utf8_unicode_ci;')
            conn.commit()
            conn.close()
        except Exception as e:
            pass

    def connect(self, db_module):
        try:
            return _connect(
                    db_module=db_module,
                    host=_DB_HOST,
                    user=_DB_USER,
                    passwd=_DB_PW,
                    db=CONF.database,
                    port=int(_DB_PORT),
                    charset='utf8')
        except:
            pass

class DeviceBase(object):        
    def __init__(self):
        pass


if __name__=='__main__':
    base=Base()
#    db =connect(host='loaclhos', user='root', passwd='admin_openstack', db=CONF.database, port=3306)
    base.create_database()
