import base64
import uuid
import urllib
from datetime import datetime
from polltask.tasks.thin_device.db import base
from oslo_config import cfg
from polltask import logger
LOG = logger.get_default_logger(__name__)
CONF = cfg.CONF
CONF.import_opt('db_module', 'polltask.tasks.thin_device.db.base')
CONF.import_opt('list', 'polltask.tasks.thin_device.db.base')
CONF.import_opt('create_sql', 'polltask.tasks.tools.utils')
CONF.import_opt('by_id', 'polltask.tasks.tools.utils')
CONF.import_opt('mac', 'polltask.tasks.tools.utils')
CONF.import_opt('update', 'polltask.tasks.tools.utils')
CONF.import_opt('status', 'polltask.tasks.tools.utils')
CONF.import_opt('add', 'polltask.tasks.tools.utils')
CONF.import_opt('delete', 'polltask.tasks.tools.utils')
CONF.import_opt('fields', 'polltask.tasks.tools.utils')
CONF.import_opt('spice_proxy', 'polltask.tasks.tools.utils')
CONF.import_opt('insert_spice_proxy', 'polltask.tasks.tools.utils')
CONF.import_opt('update_spice_proxy', 'polltask.tasks.tools.utils')
spice_proxy_fields = ('id', 'spice_proxy_flug', 
'created_at','updated_at','deleted_at','deleted','http_port')

class ExecuteData(base.Base):
    fields=eval(base64.decodestring(CONF.fields)) 
    def __init__(self, context=None, request=None): 
        super(ExecuteData, self).__init__()
        self.context=context
        self.request=request

    def connect(self):
        return super(ExecuteData, self).connect(self.db_module)

    def create_local_storage(self):
        try:
            db = self.connect()
            cur = db.cursor()
            cur.execute("""create table storage(\
                              id int(11) not null auto_increment primary key,\
                              created_at varchar(36),\
                              updated_at varchar(36),\
                              deleted_at varchar(36),\
                              storage_uuid varchar(36),\
                              storage_name varchar(36),\
                              storage_type varchar(36),\
                              mount_path varchar(225),\
                              accelerate_status char(64),\
                              accelerate_disk varchar(36),\
                              data_disk text,\
                              memory_cache int(11));""")
            db.commit()
            db.close()
            return True
        except:
            db.commit()
            db.close()
            return False

    def insert_storage_data(self, **kwargs):
        try:
            db = self.connect()
            cur = db.cursor()
            cur.execute("""insert into storage(storage_uuid,
                           storage_name, storage_type, 
                           mount_path, accelerate_status, 
                           accelerate_disk, data_disk, 
                           memory_cache)
                           values('{storage_uuid}','{storage_name}', 
                           '{storage_type}', '/{mount_path}',
                           '{accelerate_status}', '{accelerate_disk}', 
                           '{data_disk}', {memory_cache});""".format(
                           storage_uuid=kwargs.get('storage_uuid', None),
                           storage_name=kwargs.get('storage_name', None),
                           storage_type=kwargs.get('storage_type' , None), 
                           mount_path=kwargs.get('mount_path', None), 
                           accelerate_status=kwargs.get('accelerate_status', None),
                           accelerate_disk=kwargs.get('accelerate_disk', None),
                           data_disk=kwargs.get('data_disk', None),
                           memory_cache=kwargs.get('memory_cache', None)))
            db.commit()
            db.close()
            return True
        except:
            db.commit()
            db.close()
            return False

    def storage_list(self):
        fields = ["id","created_at","updated_at",
                  "deleted_at", "storage_uuid",
                  "storage_name","storage_type",
                  "mount_path","accelerate_status",
                  "accelerate_disk","data_disk",
                  "memory_cache"]
        try:
            db = self.connect()
            cur = db.cursor()
            cur.execute("""select * from storage;""")
            results = cur.fetchall()
            db.close()
            storage = [dict(map(None, fields, row)) for row in results]
            return storage
        except Exception as e:
            db.close()
            return []

    def get_storage_by_uuid(self, uuid):
        fields = ["id","created_at","updated_at",
                  "deleted_at", "storage_uuid",
                  "storage_name","storage_type",
                  "mount_path","accelerate_status",
                  "accelerate_disk","data_disk",
                  "memory_cache"]
        try:
            db = self.connect()
            cur = db.cursor()
            cur.execute("""select * from storage where storage_uuid='{0}';""".format(uuid))
            results = cur.fetchall()
            db.close()
            storage = [dict(map(None, fields, row)) for row in results]
            return storage
        except Exception as e:
            db.close()
            return []

    def storage_update(self, uuid, key, value):
        try:
            db = self.connect()
            cur = db.cursor()
            cur.execute("""update storage set {key}='{value}' where storage_uuid='{uuid}';"""\
                        .format(key=key, value=value, uuid=uuid))
            db.commit() 
            db.close()
            return True
        except Exception:
            db.close()
            return False
 
    def create_spice_proxy(self):
        try:
            now = datetime.now()
            update_time = str(now.strftime("%Y-%m-%d %H:%M:%S"))
            create_sql = base64.decodestring(CONF.spice_proxy)
            insert_sql = base64.decodestring(CONF.insert_spice_proxy)
            db = self.connect()
            cur = db.cursor()
            cur.execute(create_sql)
            cur.execute(insert_sql.format(update_time=update_time))
            db.commit()
            db.close()
        except: 
            pass

    def create_table(self):
        try:
            sql = base64.decodestring(CONF.create_sql)
            db = self.connect()
            cur = db.cursor()
            cur.execute(sql)
            cur.execute("alter table devices convert to character set utf8 collate utf8_unicode_ci;")
            db.close()
        except: 
            pass

    def spice_proxy_detail(self): 
        db = self.connect()
        try:
            cur = db.cursor()
            cur.execute('select * from spice_proxy')
            results = cur.fetchall()
            db.close()
            spice_proxy = [dict(map(None, spice_proxy_fields, row)) for row in results]
            return spice_proxy
        except Exception as e:
            db.close()
            return []

    def update_spice_proxy(self, spice_proxy_flug, http_port):
        db = self.connect()
        try:
            now = datetime.now()
            update_time = str(now.strftime("%Y-%m-%d %H:%M:%S"))
            cur = db.cursor()
            cur.execute(base64.decodestring(CONF.update_spice_proxy).format(
                                    spice_proxy_flug=int(spice_proxy_flug), 
                          http_port=int(http_port), update_time=update_time))
            db.commit()
            db.close()
            return True
        except Exception as e:
            db.rollback()
            db.close
            return False

    def get_spice_proxy(self, id):
        db = self.connect()
        sql = 'select * from spice_proxy where id = %s' % id
        cur = db.cursor()
        cur.execute(sql)
        results = cur.fetchall()
        spice_proxy = [dict(map(None, spice_proxy_fields, row)) for row in results]
        db.close()
        return spice_proxy

    def get_by_id(self, id):
        db = self.connect()
        cur = db.cursor()
        try:
            cur.execute(base64.decodestring(CONF.by_id).format(id))
            results = cur.fetchall()
            db.close()
            device = [dict(map(None, self.fields, row)) for row in results]
            return device
        except Exception as e:
            db.close()
            return []
 
    def get_by_mac(self, MAC):
        db = self.connect()
        cur = db.cursor()
        sql=base64.decodestring(CONF.mac)
        try:
            cur.execute(base64.decodestring(CONF.mac).format(MAC))
            results = cur.fetchall()
            db.close()
            device = [dict(map(None, self.fields, row)) for row in results]
            return device
        except Exception as e:
            db.close()
            return []
        
    def list(self):
        db = self.connect()
        cur = db.cursor()
        #print 'fields', self.fields
        try:
            cur.execute(base64.decodestring(CONF.list))
            results = cur.fetchall()
            db.close()
            device = [dict(map(None, self.fields, row)) for row in results]
            return device
        except Exception as e:
            db.close()
            return [] 

    def update(self, id=None, ip=None, location=0,
                    status='on-line', user=None,
                    instance=None, system=None,
                    cpu=None, memory=None,
                    gateway=None, version = None, 
                    hostname=None):
        now = datetime.now()
        localtime = str(now.strftime("%Y-%m-%d %H:%M:%S"))
        sql = base64.decodestring(CONF.add)
        db=self.connect()
        cur = db.cursor()
        #print sql
        try:
            sql = base64.decodestring(CONF.update).decode('latin1')
            #sql = base64.decodestring(CONF.update)
            cur.execute(sql.format(localtime=localtime,
                                   id=id, ip=ip, 
                                   location=location,
                                   status=status, user=user,
                                   instance=instance,
                                   system=system, cpu=cpu,
                                   memory=memory, 
                                   gateway=gateway,
                                   version = version, 
                                   hostname=hostname))
            db.commit()
            db.close()
            return True
        except Exception as e:
            self.status(id, 'off-line')
            db.rollback()
            db.close()
            return False

    def status(self, id, status=None):
        sql = base64.decodestring(CONF.status)
        print sql 
        now =datetime.now()
        localtime = str(now.strftime("%Y-%m-%d %H:%M:%S"))
        db=self.connect()
        cur = db.cursor()
        try:
            cur.execute(sql.format(id=id,
                        localtime=localtime,
                        status=status))
            db.commit()
            db.close()
            return True
        except Exception as e:
            db.rollback()
            db.close()
            return False

    def add_device(self, ip=None, MAC=None, hostname=None,
                    Terminal_location=0, system=None, version=None,
                    status=None, user=None, cpu=None, memory=None,
                    gateway=None, binding_instance=None):
        now = datetime.now()
        localtime = str(now.strftime("%Y-%m-%d %H:%M:%S"))
        sql = base64.decodestring(CONF.add)
        device_id = uuid.uuid4().hex
        db=self.connect()
        cur = db.cursor()

        try:
            sql = base64.decodestring(CONF.add).decode('latin1')
            #sql = base64.decodestring(CONF.add)
            cur.execute(sql.format(localtime=localtime, 
                                   device_id=device_id,
                                   ip=ip, MAC=MAC, hostname=hostname, 
                                   Terminal_location=Terminal_location, 
                                   status=status, user=user, 
                                   system=system, cpu=cpu, memory=memory,
                                   gateway=gateway, version = version,
                                   binding_instance=binding_instance))
            db.commit()
            db.close()
            return True
        except Exception as e:
            db.rollback()
            db.close()
            return False

    def delete_table(self, id):
        sql = base64.decodestring(CONF.delete)
        db = self.connect()
        cur = db.cursor()
        try:
            cur.execute(sql.format(id))
            db.commit()
            db.close()
            return True
        except Exception as e:
            db.rollback()
            db.close()
            return False
        

if __name__=='__main__':
    ex = ExecuteData()
#    data = ex.create_local_storage()
    #data = ex.get_storage_by_uuid("9d6778aaa27b49deaa7cc55534762e8b")
    kwargs = {"storage_name":"local-ssd",
              "storage_type":"localstorage",
              "mount_path":"jsdata",
              "accelerate_status":"yes",
              "accelerate_disk":"sdc",
#              "data_disk":"[sda, sdb, sdd, sdf]",
              "memory_cache":4}
#    data = ex.insert_storage_data(**kwargs)
    #print ex.storage_list()
    data = ex.storage_update('f197e58b62c445fe8e3de0e85e1a6fb1', 'accelerate_status', 'success')
    print data 
