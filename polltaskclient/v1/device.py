from polltaskclient import Logger as LOG
from polltaskclient.v1 import base


class Device(base.Resource):
    def __repr__(self):
        return "<Device : %s>" % getattr(self, 'info', None)


class DeviceManager(base.BassManager):
    resource_class = Device

    def get(self, id):
        return self._get('/device/get', id)

    def detail_spice_proxy(self):
        return self._list('/device/spice_proxy')

    def get_spice_proxy(self, id):
        return self._get('/device/get_spice_proxy', id)

    def update_spice_proxy(self, body):
        return self._post('/device/update_spice_proxy', body)


    def list(self):
        return self._list('/device/list')


    def delete(self, id):
        return self._delete('/device/delete', id)


    def reboot_device(self, id):
        return self._action('/device/reboot', id)


    def poweroff_device(self, id):
        return self._action('/device/dev_stop', id)


    def sendmessage(self, body):
        return self._post('/device/send', body)


    def start(self, device):
        return self._action('/device/start', device)

    def check_ipaddr(self, ip):
        return self._action('/device/check_ip', ip)

    def update(self, body):
        return self._post('/device/update', body)

    def add_compute_node(self, body):
        return self._post('/openstack_opt/setup_install_env/add_compute_node', body)

    def reboot_host(self, host=None, user="root", password=""):
        """Restart server host"""
        return self.client.post('/system_opt/reboot',
               params={
                   "host":host,
                   "user":user,
                   "password":password
               })

    def poweroff_host(self, host=None, user="root", password=""):
        """poweroff server host"""
        return self.client.post('/system_opt/poweroff',
               params={
                   "host":host,
                   "user":user,
                   "password":password
               })

    def cloud_disk_total(self, host=None, user="root", password=""):
        return self.client.post('/openstack_opt/common/get_all_vgs',
               params={
                   "host":host,
                   "user":user,
                   "password":password
               })

    def update_cloud_disk_size(self, host=None, volume_size=None, user="root", password=""):
        return self.client.post('/openstack_opt/common/extend_cinder_volume',
               params={
                   "host":host,
                   "user":user,
                   "password":password,
                   "extend_volume_size":volume_size
               })
    def download_db(self):
        return self.client.post('/system_opt/dev_dumpdb')
