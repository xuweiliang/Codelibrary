#-*- coding: utf-8 -*-

from eventlet import GreenPool
from eventlet import event
from eventlet import backdoor
import eventlet

from polltask.task import Task, WSGITask
from polltask.utils import import_utils, get_subclass
from polltask.logger import get_default_logger
from polltask.config import get_default_config

DEBUG = False

class Service(object):
    def __init__(self, check_task_internal='', *task_info):
        """
        task_info should include the dictionary which have the keys of 'task_name' and 'task_desc'.
        """
        global DEBUG
        if DEBUG:
            self.logger = get_debug_logger("Service")
        else:
            self.logger = get_default_logger("Service")
        self.config = get_default_config()
        
        if check_task_internal and int(check_task_internal):
            self.check_task_internal = int(check_task_internal)
        else:
            self.check_task_internal = int(self.config.get_option_value('default', 'check_task_internal'))
        self.enable_backdoor = self.config.get_option_value('eventlet_backdoor', 'enable')
        self.backdoor_port = self.config.get_option_value('eventlet_backdoor', 'port')
        self.task_info = task_info

        self.pool = GreenPool()

        self.control = None
        self.task_queue_list = []
        self.task_status = {}
        self.task_thread_list = []

        self._done = event.Event()
    
    def _get_task_status(self, queue):
        task_status = {}
        status = queue.get()
        if status:
            for item in status.split(','):
                key, value = item.split(':')
                task_status[key.strip()] = value.strip()
 
        return task_status
    
    def launch_control_task(self, *queue_list, **task_status):
        while True:
            eventlet.sleep(self.check_task_internal)
            for queue in queue_list:
                status = self._get_task_status(queue)
                if status:
                    task_status[status['task_name']] = status
    
    def _get_task_obj(self, task_name):
        task_module = import_utils(task_name)
        for task_subclass_name, task_subclass in get_subclass(task_module, Task):
            if task_subclass:
                return task_subclass
        return None
        
    def start(self):

        if len(self.task_info) == 0:
            self.logger.info("No task is here for executing!!!")
            self.stop()
        wsgi_tasks = WSGITask()
        wsgi_task_names = []
        #wsgi_url_map_app = {}
        for task_info in self.task_info:
            task_name = task_info['task_name']
            task_obj = self._get_task_obj(task_name)
            task_queue = eventlet.queue.LifoQueue()
            self.task_queue_list.append(task_queue)
            task = task_obj(task_queue)
            if task.task_type == 'standalone':
                task_thread = self.pool.spawn(task.start)
                self.task_thread_list.append(task_thread)
            elif task.task_type == 'subwsgi':
                #if task.url_map_app:
                    #
                    # If there is the same url mapping to the different apps,
                    # then the url will direct to the last app 
                    #
                #    wsgi_url_map_app.update(task.url_map_app)
                task.register(wsgi_tasks.mapper, wsgi_tasks.loader)
                wsgi_task_names.append(task.task_name)

        # Start the wsgi tasks binding to the whole port
        #for url, app in url_map_app.items():
        #    wsgi_tasks.register(url, app)
        if len(wsgi_task_names) >= 1:
            self.logger.info("Will run WSGI tasks:%s in a singal thread..." % wsgi_task_names)
            task_thread = self.pool.spawn(wsgi_tasks.start)
            self.task_thread_list.append(task_thread)

        # launch the control task
        task_thread = self.pool.spawn(self.launch_control_task, 
                                      *self.task_queue_list, 
                                      **self.task_status)
        self.task_thread_list.append(task_thread)

        if self.enable_backdoor.lower() == 'true':
            self.open_backdoor()
            
    def wait(self):
        self._done.wait()
    
    def stop(self):
        for task_thread in self.task_thread_list:
            task_thread.kill()
        if not self._done.ready():
            self._done.send()
    
    def restart(self):
        pass

    def list_task_threads(self):
        print self.task_thread_list

    def list_task_queues(self):
        print self.task_queue_list

    def list_task_status(self):
        print self.task_status
    
    def open_backdoor(self):
        backdoor_locals = {'list_task_threads': self.list_task_threads,
                            'list_task_queues': self.list_task_queues,
                            'list_task_status': self.list_task_status,
                            'stop': self.stop}
        self.backdoor_port = self.config.get_option_value('eventlet_backdoor', 'port')
        self.pool.spawn(backdoor.backdoor_server, eventlet.listen(('localhost', int(self.backdoor_port))), locals=backdoor_locals) 


class WSGIService(object):
    pass

def get_task_obj(task_name):
    task_module = import_utils(task_name)
    for task_subclass_name, task_subclass in get_subclass(task_module, Task):
        if task_subclass:
            return task_subclass
    return None

if __name__ == "__main__":
    import pdb
    pdb.set_trace()
    #task = get_task_obj("task_revert_snapshot")
    task = get_task_obj("task_execute_system_opt")
    print "members: ", dir(task)
