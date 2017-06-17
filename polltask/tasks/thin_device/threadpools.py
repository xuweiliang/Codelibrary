from polltask.tasks.thin_device.db.api import API
from xmlrpclib import ServerProxy
from oslo_config import cfg
from Queue import Queue
from polltask import logger
import subprocess
import threading
import socket
LOG = logger.get_default_logger(__name__)

CONF = cfg.CONF
CONF.import_opt('addrip', 'polltask.tasks.thin_device.device_manager')

class ConnectClient(object):
    def __init__(self, queue=None, db=None, IP=None):
        self.id = 0
        self.IP = IP
        self.mac = None
        self.status="off-line"
        self.db = db or API()
        self.queue = queue

    def get_client_ip(self, id):
        try:
            data = self.db.get_by_id(id)[0] 
            self.id = data.get('id', 0)
            self.mac = data.get("MAC", None)
            #if data and data['status'] == "on-line":
            self.IP = data.get("ip", None)
        except AttributeError, ValueError:
            raise "Query less than this ID or no this device."


    def start_dev(self):
        try:
            cmd = "wol -i {ip} {mac}".format(ip=self.IP, mac=self.mac)
            result = subprocess.call(cmd.split(), shell=False)
            #socket.setdefaulttimeout(10)
            self.queue.put(result)
            data = self.db.get_by_id(self.id)
            status = data[0]['status'] if data else None
            if status == self.status:
                self.db.status(self.id, "waiting")
            #self.db.status(self.id, self.status)
        except Exception:
            self.db.status(self.id, self.status)
            self.queue.put(1)
        
    def reboot(self):
        try:
            obj_instance=ServerProxy(CONF.addrip % self.IP)
            socket.setdefaulttimeout(5)
            result = obj_instance.reboot()
            socket.setdefaulttimeout(None)
            self.queue.put(result)
            self.db.status(self.id, "waiting")
        except Exception: 
            self.db.status(self.id, self.status)
            self.queue.put(1)


    def shutdown(self):
        try:
            obj_instance=ServerProxy(CONF.addrip % self.IP)
            socket.setdefaulttimeout(5)
            result = obj_instance.shutdown()
            socket.setdefaulttimeout(None)
            self.queue.put(result)
            self.db.status(self.id, "waiting")
        except Exception:
            self.db.status(self.id, self.status)
            self.queue.put(1)

class ConnectThread(object):
    def __init__(self, device=[]):
        self.device=device
        self.threadpool = []
        self.data = None

    def start_threadpools(self):
        queue = Queue(200)
        for id in self.device:
            conn = ConnectClient(queue=queue)
            IP = conn.get_client_ip(id)
            th = threading.Thread(target=conn.start_dev)
            self.threadpool.append(th)
        for th in self.threadpool:
            th.start()
            threading.Thread.join(th)

        for i in xrange(len(self.device)):
            LOG.info("start_device execute result %s" % queue.get())
        self.data=queue
        return queue
        

    def reboot_threadpools(self):
        queue = Queue(200)
        for id in self.device:
            conn = ConnectClient(queue=queue)
            IP = conn.get_client_ip(id)
            th = threading.Thread(target=conn.reboot)
            self.threadpool.append(th)
        for th in self.threadpool:
            th.start()
            threading.Thread.join(th)

        for i in xrange(len(self.device)):
            LOG.info("reboot execute result %s" % queue.get())
        self.data=queue 
        return queue

    def stop_threadpools(self):
        queue = Queue(200)
        for id in self.device:
            conn = ConnectClient(queue=queue)
            IP = conn.get_client_ip(id)
            th = threading.Thread(target=conn.shutdown)
            self.threadpool.append(th)
        for th in self.threadpool:
            th.start()
            threading.Thread.join(th)

        for i in xrange(len(self.device)):
            LOG.info("stop execute result %s" % queue.get())
        self.data=queue 
        return queue

if __name__=="__main__":
    device = [6,7, 8,9,10,11,12,13,14,15]
    m = ConnectThread(device)
    #m.reboot_threadpools()
    m.stop_threadpools()
    for i in xrange(len(device)):
        print m.data.get()
