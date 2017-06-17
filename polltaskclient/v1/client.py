from polltaskclient.http import HTTPClient
from polltaskclient.openstack.common import utils
from polltaskclient.v1.device import DeviceManager
from polltaskclient.v1.storage import StorageManager
from polltaskclient import Logger as LOG

class Client(object):
    
    def __init__(self, endpoint, *args, **kwargs):
        self.http_client = HTTPClient(utils.strip_version(endpoint), *args, **kwargs)
        self.device = DeviceManager(self.http_client)
        self.storage = StorageManager(self.http_client) 
#        self.session = self.http_client.session
#        url = '/'.join([endpoint, 'device/poweroff'])
#        data = self.session.request('get', url)

