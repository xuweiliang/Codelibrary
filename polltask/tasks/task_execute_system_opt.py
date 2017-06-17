#-*- coding: utf-8 -*- 

from polltask.task import Task


class TaskExecuteSystemOpt(Task):
    def __init__(self, status_queue):
        super(TaskExecuteSystemOpt, self).__init__(status_queue,
                                                   'TaskExecuteSystemOpt',
                                                   'subwsgi',
                                                   task_desc="Execute system command")


    def register(self, mapper, loader):
        mapper.connect('system_opt', '/system_opt/{action}', controller=loader.load_app('system_opt'))
    
