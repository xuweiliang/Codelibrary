import six
import json
import webob.dec
import webob.exc
import webob
import subprocess
import socket
import threading
from webob import Response
from xmlrpclib import ServerProxy
from oslo_config import cfg

from polltask.wsgi import Application, Request
#from polltask.tasks.tools import utils
#import routes
from polltask import logger
from polltask.tasks.thin_device.db.api import API
from polltask.tasks.thin_device import spice_proxy as sp
from polltask.tasks.thin_device import threadpools as tp
LOG = logger.get_default_logger(__name__)
_STATUS = "off-line"

CONF=cfg.CONF

CONF.import_opt('addrip', 'polltask.tasks.thin_device.device_manager')


LOG = logger.get_default_logger(__name__)

class BatchOperation(tp.ConnectThread):

    def start_threadpools(self):
        start_dev = super(BatchOperation, self)
        start_dev.start_threadpools()

    def reboot_threadpools(self):
        reboot = super(BatchOperation, self)
        reboot.reboot_threadpools()

    def stop_threadpools(self):
        stop = super(BatchOperation, self)
        stop.stop_threadpools()


class DeviceManager(Application):
    
    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, req):
        self.db = API(req)
        arg_dict = req.environ['wsgiorg.routing_args'][1]
        token = req.environ.get('HTTP_X_AUTH_TOKEN', None)
#        import pdb
#        pdb.set_trace()
        if not token:
            headers = []
            status=(204, 'No Token')
            headers.append(('Vary', 'X-Auth-Token'))
            return webob.Response(
                             body='', 
                             status='%s %s' % status,
                             headerlist=headers)
        del arg_dict['controller']
        action = arg_dict.get('action', None) 
        if action is None:
            return webob.exc.HTTPNotFound
        action = action.encode()
        if not hasattr(self, action):
            return webob.exc.HTTPNotImplemented()
        method = getattr(self, action)
        kwargs = dict(req.params.iteritems())
        context = req.environ.get('device', {})
        context['query_string'] = dict(six.iteritems(req.params))
        context['headers'] = dict(six.iteritems(req.headers))
        context['path'] = req.environ['PATH_INFO']
        context['host_url'] = req.host_url
        params = req.environ.get('params', {})
        context['environment'] = req.environ
        context['accept_header'] = req.accept
        req_method = req.environ['REQUEST_METHOD'].upper()
        return self._process_stack(req, method, context,  **kwargs)

    def _process_stack(self, req, method, context, headers=None, **kwargs):
        result = method(req, context, **kwargs)
        if headers is None:
            headers = []
        else:
            headers = list(headers)
        headers.append(('Vary', 'X-Auth-Token'))
        if result is None:
            status=(204, 'No Content')
            resp = webob.Response(body='',
                          status='%s %s' % status,
                          headerlist=headers)
            return resp
        elif isinstance(result, six.string_types):
            return result
        elif isinstance(result, webob.Response):
            return result
        elif isinstance(result, webob.exc.WSGIHTTPException):
            return result

    def _json(self, data, decoding=False):
        try:
            if decoding:
                return json.loads(data)
            return json.dumps(data) 
        except TypeError:
            raise 'Data Type Error'


    def get_spice_proxy(self, req, context, **kwargs):
        try:
            id = kwargs.get("id", 1)
            body = self.db.get_spice_proxy(id)
            return self._json(body)
        except Exception as e:
            return []

    def spice_proxy_detail(self, req, context, **kwargs):
        body = self.db.spice_proxy_detail()
        return self._json(body)

    def update_spice_proxy(self, req, context, **kwargs):
        try:
            execute = 1
            http_port = kwargs.get('http_port', None)
            flug = kwargs.get('spice_proxy_flug', None)
            if flug == '1':
                initsp = sp.SpiceProxy(kwargs['http_port'])
                initsp.save_file()
                execute = initsp.services(['service',' squid','restart'])
            else:
                initsp = sp.SpiceProxy(kwargs['http_port'])
                initsp.save_file()
                execute = initsp.services(['service',' squid','stop'])
            if execute == 0:
                body = self.db.update_spice_proxy(flug, http_port)
            return self._json(body)
        except Exception as e:
            raise e("Proxy service exception")

    def get_dev_by_id(self, req, context, **kwargs):
        try:
            id = kwargs.pop('id')
            body = self.db.get_by_id(id)
        except (AttributeError, ValueError):
            return []
        return self._json(body)

    def detail(self, req, context, **kwargs):
        #import pdb
        #pdb.set_trace()
        body = self.db.list()
        return self._json(body)

    def dev_delete(self, req, context, **kwargs):
        try:
            id = kwargs.pop('id')
            body = self.db.delete_table(id)
        except (AttributeError, ValueError):
            return self._json(False)
        return self._json(body)

    def dev_reboot(self, req, context, **kwargs):
        allreboot = self._json(kwargs.pop('id'), decoding=True)
        if len(allreboot) > 1:
            bo = BatchOperation(allreboot)
            delayed = threading.Timer(2, bo.reboot_threadpools)
            delayed.start()
            return self._json(3)
        try:
            id = allreboot[0]
            body = self.db.get_by_id(id)[0]
            if body["status"] == 'off-line':
                raise
            IP = body.pop("ip")
            obj_instance=ServerProxy(CONF.addrip % IP)
            socket.setdefaulttimeout(3)
            result=obj_instance.reboot()
            #socket.setdefaulttimeout(None)
            self.db.status(id, "waiting")
            return self._json(0)
        except Exception as e:
            self.db.status(id, _STATUS)
            return self._json(1)

    def dev_stop(self, req, context,  **kwargs):
        allstop = self._json(kwargs.pop('id'), decoding=True)
        if len(allstop) > 1:
            bo = BatchOperation(allstop)
            delayed = threading.Timer(2, bo.stop_threadpools)
            delayed.start()
            return self._json(3)
        try:
            id = allstop[0]
            body = self.db.get_by_id(id)[0]
            if body["status"] == 'off-line':
                raise
            IP = body.pop("ip")
            obj_instance=ServerProxy(CONF.addrip % IP)
            socket.setdefaulttimeout(3)
            result = obj_instance.shutdown()
            #socket.setdefaulttimeout(None)
            self.db.status(id, "waiting")
            #self.db.status(id, _STATUS)
            return self._json(0)
        except Exception:
            self.db.status(id, _STATUS)
            return self._json(1)

    def split_ip(self, ip):
        ip_split=ip.split('.')
        ip_split.pop(-1)
        ip_join=''.join(ip_split)
        return ip_join

    def check_ipaddr(self, host_ip, client_ip):
        if host_ip and client_ip:
            HostIPAddr = self.split_ip(host_ip)
            ClientIPAddr = self.split_ip(client_ip)
            if ClientIPAddr == HostIPAddr:
                return cmp(HostIPAddr, ClientIPAddr)
            return 1

    def dev_start(self, req, context, **kwargs):
        allstart = self._json(kwargs.pop('id'), decoding=True)
        if len(allstart) > 1:
            bo = BatchOperation(allstart)
            delayed = threading.Timer(2, bo.start_threadpools)
            delayed.start()
            return self._json(3)
        try:
            id = allstart[0]
            body = self.db.get_by_id(id)[0]
            mac = body.pop('MAC')
            client_ip = body.pop("ip")
            remote_addr = req.environ.get('REMOTE_ADDR', None)
            #check_ip = self.check_ipaddr(remote_addr, client_ip)
            #if check_ip == 0:
            cmd = "wol -i {ip} {mac}".format(ip=client_ip, mac=mac)
            result = subprocess.call(cmd.split(), shell= False)
            self.db.status(id, "waiting")
            return self._json(result)
            #return self._json(0)
        except Exception as e:
            return self._json(1)

    def update(self, req, context, **kwargs):
        try:
            id = kwargs.pop("id_update")
            body = self.db.get_by_id(id)[0]
            if body["status"] == 'off-line':
                raise
            data = kwargs.copy()
            IP = body.pop("ip")
            obj_instance=ServerProxy(CONF.addrip % IP)
            socket.setdefaulttimeout(5)
            result = obj_instance.update(data)
            socket.setdefaulttimeout(None)
            return self._json(0)
        except Exception as e:
            return Response(body='', status=451)

    def dev_status(self, req, context, **kwargs):
        device_mac=None
        hostname = kwargs.get("hostname", None)
        system = kwargs.get("system", None)
        version = kwargs.get("version", None)
        gateway= kwargs.get("gateway", None)
        memory= kwargs.get("memory", None)
        cpu= kwargs.get("cpu", None)
        ip = kwargs.get('addr', None)
        MAC = kwargs.get('mac', None)
        status = kwargs.get('status', 'on-line')
        user = kwargs.get('user', None)
        binding_instance = kwargs.get('instance', None)
        Terminal_location = kwargs.get('Terminal_location', 0)
        if MAC:
            device_mac =self.db.get_by_mac(MAC)
        if not device_mac:
            body = self.db.add_device(ip=ip, MAC=MAC, system=system,
                                 Terminal_location=Terminal_location,
                                 status=status, user=user,
                                 binding_instance=binding_instance,
                                 hostname=hostname, version=version,
                                 cpu=cpu, memory=memory,
                                 gateway=gateway)
        else:
            db = API()
            info = device_mac.pop()
            body = self.db.update(
                               id=info['id'], ip=ip, system=system,
                               memory=memory, gateway=gateway,
                               version=version, hostname=hostname,
                               Terminal_location=Terminal_location,
                               status=status, user=user, cpu=cpu,
                               binding_instance=binding_instance)

    def push_message(self, req, context, **kwargs):
        try:
            id = kwargs.pop('id_message')
            body = self.db.get_by_id(id)[0]
            if body["status"] == 'off-line':
                raise
            data = kwargs.pop('message')
            IP = body.pop("ip")
            obj_instance=ServerProxy(CONF.addrip % IP)
            socket.setdefaulttimeout(3)
            result = obj_instance.receive(data)
            socket.setdefaulttimeout(None)
            return self._json(0)
        except Exception as e:
            self.db.status(id, _STATUS)
            return self._json(1)

    def device_check_ipaddr(self, req, context, **kwargs):
        ipaddr = kwargs.get('id', '0.0.0.0')
        result = subprocess.call(['ping','-c','1','-W','1', eval(ipaddr)], shell= False)
        return self._json(result)

    def storage_insert(self, req, context, **kwargs):
        storage_uuid=kwargs.get("storage_uuid", None)
        storage_name=kwargs.get("storage_name",None)
        storage_type=kwargs.get("storage_type",None)
        mount_path=kwargs.get("mount_path",None)
        accelerate_status=kwargs.get("accelerate_status", 'creating')
        accelerate_disk=kwargs.get("accelerate_disk",None)
        data_disk=kwargs.get("data_disk",None)
        memory_cache=kwargs.get("memory_cache",None)
        try:
            self.db.insert_storage_data(storage_uuid=storage_uuid,
               storage_name=storage_name,storage_type=storage_type,
               mount_path=mount_path,accelerate_status=accelerate_status,
               accelerate_disk=accelerate_disk,data_disk=data_disk,
               memory_cache=memory_cache)
            return self._json(True)
        except Exception as e:
            return self._json(False)

    def storage_list(self, req, context, **kwargs):

        try:
            storage = self.db.storage_list() 
            return self._json(storage)
        except Exception:
            return self._json([]) 

    """def storage_update(self, req, context, **kwargs):
        
        try:
            self.db.storage_update()
            return _json(True)
        except Exception:
            return _json(False)"""
