#-*- coding: utf-8 -*-

#SELF_TEST = True
#if SELF_TEST:
#    import sys
#    sys.path.insert(0, '../')

from datetime import datetime

from polltask.tasks.thin_device.db import api
from polltask.task import Task
from polltask.timer import wakeup_every_time

HEARTBEAT_INTERNAL = 30

class TaskDeviceHeartbeat(Task):

    def __init__(self, status_queue):
        super(TaskDeviceHeartbeat, self).__init__(status_queue,
                                                'TaskDeviceHeartbeat',
                                                'standalone',
                                                task_desc='It is a task thread to update device info')
	self.db = api.API()

    def start(self):
        self.logger.info("start device heartbeat...")
        global HEARTBEAT_INTERNAL
        while True:
            wakeup_every_time(0, 0, HEARTBEAT_INTERNAL)
            devices = self.db.list()
            if devices:
                for dev in devices:
                    createtime=datetime.strptime(dev['created_at'], "%Y-%m-%d %H:%M:%S")
                    starttime = (datetime.now()-createtime).seconds
                    updated_at = dev.get("updated_at", None)
                    if not updated_at:
                        if starttime > 120:
                            self.db.status(dev['id'], status='off-line')
                    else:
                        updatetime=datetime.strptime(dev['updated_at'], "%Y-%m-%d %H:%M:%S")
                        endtime = (datetime.now()-updatetime).seconds
                        self.logger.info("device update time %s" % endtime)
                        if endtime > 60 :
                            self.db.status(dev['id'], status='off-line')

if __name__ == "__main__":
    import eventlet

    task_queue = eventlet.queue.LifoQueue()
    task = TaskDeviceHeartbeat(task_queue)
    task.start()

