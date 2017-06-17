#-*- coding: utf-8 -*- 

from polltask.task import Task


class TaskExecuteOpenstackOpt(Task):
    def __init__(self, status_queue):
        super(TaskExecuteOpenstackOpt, self).__init__(status_queue,
                                                   'TaskExecuteOpenstackOpt',
                                                   'subwsgi',
                                                   task_desc="Execute openstack command")

    def register(self, mapper, loader):
        mapper.connect('openstack_common_opt', 
                        '/openstack_opt/common/{action}', 
                        controller=loader.load_app('openstack_common_opt'))
        mapper.connect('openstack_setup_install_env', 
                        '/openstack_opt/setup_install_env/{action}', 
                        controller=loader.load_app('openstack_setup_install_env'))
