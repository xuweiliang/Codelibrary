import polltaskclient as polltask_client
from django.conf import settings
from openstack_dashboard.api import base
from openstack_dashboard.api import templet_info as tmp 
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

def spice_proxy_list(request):
    spice_proxy = polltaskclient(request).device.detail_spice_proxy()
    return spice_proxy

def get_spice_proxy_by_id(request,id):
    spice_proxy = polltaskclient(request).device.get_spice_proxy(id)
    return spice_proxy

def update_spice_proxy_pattern(request, spice_proxy):
    spice_proxy_pattern = polltaskclient(request).device.update_spice_proxy(spice_proxy)
    return spice_proxy_pattern

def get(request, device): 
    return polltaskclient(request).device.get(device)

def status(request, device):
    return polltaskclient(request).device.status(device)

def device_list(request):
    return polltaskclient(request).device.list()

def delete(request, device):
    return polltaskclient(request).device.delete(device)

def reboot_device(request, device):
    return polltaskclient(request).device.reboot_device(device)

def start_device(request, device):
    return polltaskclient(request).device.start(device)

def poweroff_device(request, device):
    return polltaskclient(request).device.poweroff_device(device)

def device_ipaddr(request, ip):
    return polltaskclient(request).device.check_ipaddr(ip)

def sendmessage(request, data):
    return polltaskclient(request).device.sendmessage(data)

def update_devive(request, data):
    return polltaskclient(request).device.update(data)

def add_compute_node(request, data):
    return polltaskclient(request).device.add_compute_node(data)

def poweroff_host(request, host=None):
    return polltaskclient(request).device.poweroff_host(host=host)

def get_colud_disk_size(request, host=None):
    return polltaskclient(request).device.cloud_disk_total(host=host)

def update_cloud_disk_size(request, host=None, volume_size=None):
    return polltaskclient(request).device.update_cloud_disk_size(host=host, volume_size=volume_size)
