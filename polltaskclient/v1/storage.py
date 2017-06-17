from polltaskclient import Logger as LOG
from polltaskclient.v1 import base
import json


class Storage(base.Resource):
    def __repr__(self):
        return "<Storage : %s>" % getattr(self, 'info', None)


class StorageManager(base.BassManager):
    resource_class = Storage

    def storage_create(self, **kwargs):

        body={"storage_uuid":kwargs['storage_uuid'],
              "storage_name":kwargs['storage_name'],
              "accelerate_disk":kwargs['accelerate_disk'],
              "data_disk":json.dumps(kwargs['data_disk']),
              "memory_cache":kwargs['memory_cache']}
        return self._post('/device/storage_insert', body)

    def storage_list(self):
        return self._list('/device/storage_list')

    def get_free_disk(self, hostname):
        return self.client.post("/system_opt/get_disks", 
               params={"host": hostname, 
                       "user": "root", 
                       "password": "111111",
                       "disk_type": "free",
                       #"disk_type": "all",
                       "only_whole_disk":"yes"})

    def storage_start_thread(self, **kwargs):
        #LOG.info("kwargs =========================%s" % kwargs)
        return self.client.post('/system_opt/create_zfs_pool',
               params={"host":kwargs['host'],
                       "user":kwargs['user'],
                       "password":"",
                       "use_zfs_in_openstack":"yes",
                       "storage_uuid":kwargs['storage_uuid'],
                       "accelerator":kwargs['accelerator'],
                       "disks":json.dumps(kwargs['disks']),
                       "memory_cache":kwargs['memory_cache']})


    def get_zfs_pools(self, **kwargs):
        return self.client.post('/system_opt/get_zfs_pools',
               params={"host":kwargs['host'],
                       "user":"root",
                       "password":""})

    def destroy_zfs_pools(self, **kwargs):
        return self.client.post('/system_opt/destroy_zfs_pools',
               params={"host":kwargs['host'],
                       "user":"root",
                       "password":"",
                       "pool_names":kwargs['pool_names']
                       })
