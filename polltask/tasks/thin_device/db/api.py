from polltask.tasks.thin_device.db.execute_data import ExecuteData as exdata 
from polltask import logger
import six
LOG = logger.get_default_logger(__name__)

class Module(exdata):
    def __init__(self, request=None):
        #context['query_string'] = dict(six.iteritems(request.params))
        #context['headers'] = dict(six.iteritems(request.headers))
        #context['path'] = request.environ['PATH_INFO']
        #context['host_url'] = request.host_url
        #params = request.environ.get('params', {})
        #context['environment'] = request.environ
        #context['accept_header'] = request.accept
        super(exdata, self).__init__()
        self.request=request
            

class API(object):
    _DEFAULT=None
    def __init__(self, request=None):
        self.request=request
 
    def get_storage_by_uuid(self, uuid):
        return Module(self.request).get_storage_by_uuid(uuid)

    def insert_storage_data(self, storage_uuid=None, storage_name=None,
                   storage_type=None,mount_path=None, 
                   accelerate_status=None,accelerate_disk=None,
                   data_disk=None, memory_cache=4):
        return Module(self.request).insert_storage_data(
               storage_uuid = storage_uuid,
               storage_name=storage_name,storage_type=storage_type,
               mount_path=mount_path,accelerate_status=accelerate_status,
               accelerate_disk=accelerate_disk,data_disk=data_disk,
               memory_cache=memory_cache)

    def storage_update(self, uuid, key, value):
        return Module(self.request).storage_update(uuid, key, value)

    def storage_list(self):
        return Module(self.request).storage_list()

    def spice_proxy_detail(self):
        return Module(self.request).spice_proxy_detail() 

    def get_spice_proxy(self, id):
        return Module(self.request).get_spice_proxy(id)

    def update_spice_proxy(self, flug, http_port):
        return Module(self.request).update_spice_proxy(flug, http_port)

    #def create_table(self, request):
    def create_table(self):
        """create table"""
        #Module(self.context, self.request).create_table() 
        Module(self.request).create_table() 
        #Module(request).create_table() 

    #def get_by_id(self, request, id): 
    def get_by_id(self, id): 
        """Through by ID query device"""
        #LOG.info("get_by_id===============%s" % id)
        #return Module(self.context, self.request).get_by_id(id)
        return Module(self.request).get_by_id(id)
        #return Module(request).get_by_id(id)

    #def get_by_mac(self, request, instance): 
    def get_by_mac(self, MAC): 
        """Query device by mac"""
        #return Module(self.context, self.request).get_by_mac(MAC)
        return Module(self.request).get_by_mac(MAC)
        #return Module(request).get_by_mac(MAC)

    #def list(self, request): 
    def list(self): 
        """Query so the all device"""
        return Module(self.request).list() 
        #return Module(self.context, self.request).list() 
        #return Module(request).list() 

    #def update(self, request, id, location):
    def update(self, id=None, ip=None, system=None,
                     memory=None, gateway=None,
                     version=None, hostname=None, cpu=None,
                     Terminal_location=None, status=None, 
                        user=None, binding_instance=None):
        if not user:
            user=self._DEFAULT
        if not binding_instance:
            binding_instance=self._DEFAULT
        """Update device information"""
        #Module(request).add_device(ip=ip, MAC=MAC,
        #return Module(self.context, self.request).update(id=id, ip=ip, MAC=MAC,
        return Module(self.request).update(id=id, ip=ip, location=Terminal_location,
                                 status=status, user=user, instance=binding_instance,
                                                system=system, cpu=cpu, memory=memory, 
                         gateway=gateway, version = version, hostname=hostname)

    def status(self, id, status='on-line'):
        #return Module(self.context, self.request).status(id, status=status)
        return Module(self.request).status(id, status=status)

    #def add_device(self, request, ip=None, MAC=None,
    def add_device(self, ip=None, MAC=None,Terminal_location=None,
                   system=None, status=None, user=None, binding_instance=None,
                   hostname=None, version=None, cpu=None, memory=None,
                   gateway=None): 
        if not user:
            user=self._DEFAULT
        if not binding_instance:
            binding_instance=self._DEFAULT
        """Adds a device that does not specify a value by default."""
        #Module(request).add_device(ip=ip, MAC=MAC,
        return Module(self.request).add_device(ip=ip, MAC=MAC, hostname=hostname,
                                   Terminal_location=Terminal_location, system=system,
                                   version=version, status=status, user=user,
                                   cpu=cpu, memory=memory, gateway=gateway,
                                   binding_instance=binding_instance)

    #def delete_table(self, request, id):
    def delete_table(self, id):
        """Must be based on ID to remove a device"""
        return Module(self.request).delete_table(id)
        #return Module(self.context, self.request).delete_table(id)
        #Module(request).delete_table(id)


if __name__=='__main__':
    m=API()
    import uuid
    kwargs = {"storage_uuid":uuid.uuid4().hex,
              "storage_name":"local-ssd",
              "storage_type":"localstorage",
              "mount_path":"jsdata",
              "accelerate_status":"yes",
              "accelerate_disk":"sdc",
              "data_disk":"[sda, sdb, sdd, sdf]",
              "memory_cache":4}
    g = m.storage_update('f197e58b62c445fe8e3de0e85e1a6fb1', "accelerate_status", "success")
#    g = m.insert_storage_data(storage_uuid=uuid.uuid4().hex, storage_name="local-ssd",
#         storage_type="localstorage", 
#         mount_path="jsdata",accelerate_status="yes",accelerate_disk="sdc",data_disk="[sda, sdb, sdd, sdf]", memory_cache=5)
#    g=m.get_by_id(77)
    #g=m.get_by_mac('f8:0j:41:dd:86:d2')
#    g=m.list()
    #g=m.status(24)
    #g=m.create_table()
#    g=m.add_device('192.168.10.57')
    #g = m.update(id=74, ip='http://192.168.5.13', MAC='f8:0j:41:dd:86:d2', Terminal_location=30, status='off-line', user=None, binding_instance='win8')
    print g
