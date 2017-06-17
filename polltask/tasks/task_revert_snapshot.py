#-*- coding: utf-8 -*-

#SELF_TEST = True
#if SELF_TEST:
#    import sys
#    sys.path.insert(0, '../')

from polltask.task import Task
from polltask.task import TASK_STATUS
from polltask.tasks.openstack import openstack_utils
from polltask.tasks.openstack.openstack_utils import (get_novaclient, 
                                                        get_instance,
                                                        get_all_variable_instances,
                                                        get_instance_created_time,
                                                        is_ready_to_revert,
                                                        revert_specified_snapshot)
from polltask.timer import wakeup_on_time
from polltask.timer import wakeup_every_time


# the range of hour is [0 ~ 23]
# the range of minute is [0 ~ 59]
# the range of second is [0 ~ 59]
# the range of microsecond is [0 ~ 999999]
TASK_EXECUTE_TIME_PER_DAY = {'hour': 0,
                             'minute': 1,
                             'second': 0,
                             'microsecond': 0}

DEBUG_INTERNAL_LOOP_TEST = False
DEBUG_READY_TO_REVERT = False

TASK_EXECUTE_TIME_INTERNAL_LOOP = {'hour': 0,
                                    'minute': 2,
                                    'second': 0}

class TaskRevertSnapshot(Task):
    
    def __init__(self, status_queue):
        super(TaskRevertSnapshot, self).__init__(status_queue, 
                                                'TaskRevertSnapshot', 
                                                'standalone',
                                                task_desc='It is a task thread to revert instance according to user`s need')
        
    
    def start(self):
        self.logger.info("start revert snapshot...")
        while True:
            hour = TASK_EXECUTE_TIME_PER_DAY['hour']
            minute = TASK_EXECUTE_TIME_PER_DAY['minute']
            second = TASK_EXECUTE_TIME_PER_DAY['second']
            microsecond = TASK_EXECUTE_TIME_PER_DAY['microsecond']
            if DEBUG_INTERNAL_LOOP_TEST:
                wakeup_every_time(TASK_EXECUTE_TIME_INTERNAL_LOOP['hour'],
                                    minute=TASK_EXECUTE_TIME_INTERNAL_LOOP['minute'],
                                    second=TASK_EXECUTE_TIME_INTERNAL_LOOP['second'])
            else:
                wakeup_on_time(hour, minute, second, microsecond)
            self.logger.info("Starting executing the task of reverting snapshots...")
            self.nova_conn = get_novaclient()
            variable_instances = get_all_variable_instances(self.nova_conn)
            for instance in variable_instances:
                self._revert_snapshot_and_update_status(instance)
            self.logger.info("Finish to execute the task of reverting snapshots today!")

    def _revert_snapshot_and_update_status(self, instance):
        vm_instance = get_instance(self.nova_conn, instance['uuid'])
        created_time = get_instance_created_time(vm_instance)
        if DEBUG_READY_TO_REVERT:
            ready_to_revert = True
        else:
            ready_to_revert = is_ready_to_revert(instance['per'], created_time, instance['dev_time'])
        if ready_to_revert:
            self.now_state = TASK_STATUS['normal']
            self.state_info = "Reverting instance [{uuid}] ...".format(uuid=instance['uuid'])
            try:
                if instance['dev_snapshot'] is None:
                    message = ("Not specify the snapshot for instance [{uuid}] to revert, "
                                "it will choose the latest snapshot of instance to revert".format(uuid=instance['uuid']))
                else:
                    message = "Reverting snapshot [{snapshot}] of instance [{uuid}]".format(snapshot=instance['dev_snapshot'],
                                                                                               uuid=instance['uuid'])
                self.logger.info(message)
                snapshot_name = revert_specified_snapshot(self.nova_conn, instance['uuid'], instance['dev_snapshot'])
            except Exception as e:
                self.logger.error("Reverting snapshot [{snapshot}] of instance [{uuid}] error: {error}".format(snapshot=instance['dev_snapshot'],
                                                                                                uuid=instance['uuid'],
                                                                                                error=str(e)))
                self.now_state = TASK_STATUS['exception']
                self.state_info = "Revert instance [{uuid}] failed. Error info: {error}".format(uuid=instance['uuid'],
                                                                                                error=str(e))
            if self.now_state == TASK_STATUS['normal']:
                self.logger.info("Revert snapshot [{snapshot}] of instance [{uuid}] successfully.".format(snapshot=snapshot_name,
                                                                                                              uuid=instance['uuid']))
                self.state_info = "Finish to revert instance [{uuid}] successfully.".format(uuid=instance['uuid'])

    def __str__(self):
        return "TaskReverSnapshot"

if __name__ == "__main__":
    import eventlet 

    task_queue = eventlet.queue.LifoQueue()
    task = TaskRevertSnapshot(task_queue)
    task.start()
