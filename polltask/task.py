#-*- coding: utf-8 -*-

import time

import eventlet
from eventlet import wsgi
from routes import Mapper

from polltask.logger import get_default_logger, get_debug_logger
from polltask.wsgi import Router, Loader
from polltask.config import get_default_config
from exception import TaskTypeException

TASK_STATUS = {'normal': 'NORMAL',
              'exception': 'EXCEPTION'}

TASK_REPORT_FORMAT = ','.join(['time: {now}',
                               'task_type: {task_type}',
                               'task_name: {task_name}',
                               'task_desc: {task_desc}',
                               'created_time: {created_time}',
                               'now_state: {now_state}',
                               'state_info: {state_info}'])

DEBUG = False

class TaskMeta(object):

    def __init__(self, task_name, task_type, task_desc=''):
        """
        task_type: 'standalone' or 'subwsgi'
                    'standalone': this task will be executed in a standalone 
                                  green thread.
                    'subwsgi': this task will be registered into a whole green
                               thread which will execute all tasks communicating 
                               with http clients by a specified port.
        """
        global TASK_STATUS
        self.task_type = task_type
        self.task_name = task_name
        self.task_desc = task_desc
        self.created_time = time.time() 
        self.now_state = TASK_STATUS['normal']
        self.state_info = None
        if self.task_type not in ['standalone', 'subwsgi']:
            raise TaskTypeException(task_type=self.task_type)
        
class Task(TaskMeta):
    
    def __init__(self, status_queue, task_name, task_type, task_desc=''):
        global DEBUG
        super(Task, self).__init__(task_name, task_type, task_desc)
        self.status_queue = status_queue
        if DEBUG:
            self.logger = get_debug_logger(task_name)
        else:
            self.logger = get_default_logger(task_name)
        
    def start(self):
        if self.task_type == 'subwsgi':
            pass
        else:
            NotImplemented

    def register(self, mapper, loader):
        if self.task_type == 'subwsgi':
            NotImplemented
        else:
            pass

    def report_status(self):
        task_status = TASK_REPORT_FORMAT.format(now=time.time(),
                                                task_type=self.task_type,
                                                task_name=self.task_name,
                                                task_desc=self.task_desc,
                                                created_time=self.created_time,
                                                now_state=self.now_state,
                                                state_info=self.state_info)
        self.status_queue.put(task_status)

class WSGITask(object):
    def __init__(self):
	global DEBUG
        if DEBUG:
            self.logger = get_debug_logger('wsgi_task')
        else:
            self.logger = get_default_logger('wsgi_task')

        default_config = get_default_config()
        self.bind_port = default_config.get_option_value('WSGI', 'bind_port')

        self.loader = Loader()
        self.mapper = Mapper()

#    def register(self, url, contrl_app, action=None, conditions=None):
#        if conditions is None and action is None:
#            self.mapper.connect(None, url, controller=self.loader.load_app(app))
#        elif conditions is None and action is not None:
#            self.mapper.connect(url, 
#                                controller=self.loader.load_app(contrl_app),
#                                action=action)
#        else:
#            self.mapper.connect(url, 
#                                controller=self.loader.load_app(app), 
#                                action=action
#                                conditions=conditions)

    def start(self):
        self.logger.info("start wsgi task...")
        router = Router(self.mapper)
        wsgi.server(eventlet.listen(('', int(self.bind_port))), router)

