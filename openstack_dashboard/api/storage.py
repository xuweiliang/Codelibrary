import polltaskclient as polltask_client
from django.conf import settings
from openstack_dashboard.api import base
from openstack_dashboard.api import templet_info as tmp
import threading
import logging

LOG = logging.getLogger(__name__)


def polltaskclient(request, version='1'):
    path= tmp.Url(request)
    url = path.url_path()
    LOG.debug('polltaskclient connection created using token "%s" and url "%s"'
              % (request.user.token.id, url))
    insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
    cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
    token=request.user.token.id
    ip_address=request.META['REMOTE_ADDR'],
    return polltask_client.Client(version, url,
                               token=token,
                               ip_address=ip_address,
                               insecure=insecure,
                               cacert=cacert)

def storage_start_thread(request, uuid, **kwargs):
    return polltaskclient(request).storage.storage_start_thread(**kwargs) 

def storage_create(request, 
          storage_uuid=None, storage_name=None, 
          accelerate_disk=None, data_disk=None, 
                              memory_cache=None):

    st = threading.Timer(5, storage_start_thread,
                            (request, storage_uuid),
                            {"user":"root",
                             "password":"",
                             "storage_uuid":storage_uuid,
                             "host":storage_name,
                             "accelerator":accelerate_disk,
                             "disks":data_disk,
                             "memory_cache":memory_cache})
    st.start()
    return polltaskclient(request).storage.storage_create(
                                 storage_uuid=storage_uuid,
                                 storage_name=storage_name,
                            accelerate_disk=accelerate_disk,
                                        data_disk=data_disk,
                                  memory_cache=memory_cache)

def storage_list(request):
    storage = polltaskclient(request).storage.storage_list()
    return storage

def storage_insert(request):
    return polltaskclient(request).storage.storage_insert()

def get_free_disk(request, hostname):
    free_disk = polltaskclient(request).storage.get_free_disk(hostname)
    return free_disk

def get_zfs_pools(request, host):
    zfs_pools = polltaskclient(request).storage.get_zfs_pools(host=host)
    return zfs_pools

def destroy_zfs_pools(request, host, pool_names):
    result = polltaskclient(request).storage.destroy_zfs_pools(host=host, pool_names=pool_names)
    return result
