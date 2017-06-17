from polltask.tasks.thin_device.db import api
from polltask import logger
from datetime import datetime
import threading
import time
LOG = logger.get_default_logger("-checktime-")

class HeartBeat(threading.Thread):
    def __init__(self):
        self.db = api.API()
        super(HeartBeat, self).__init__()
        self.cancel = False
        

    def run(self):
        while not self.cancel:
            time.sleep(30)
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
                        LOG.info("device update time %s" % endtime)
                        if endtime > 60 :
                            print endtime
                            self.db.status(dev['id'], status='off-line')
 
    def stop(self):
        self.cancel=True



if __name__=="__main__":
#    devices = api.API()
#    print devices.list()
    heart1 = HeartBeat()
    heart1.start()
#    time.sleep(20)
#    heart1.stop()
