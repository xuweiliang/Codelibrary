#-*- coding: utf-8 -*-

import time
import calendar
from datetime import datetime, timedelta

import eventlet

SECONDS_PER_DAY = 24 * 60 * 60
MAPPING_WEEKDAY = {
                0: 'monday',
                1: 'tuesday',
                2: 'wednesday',
                3: 'thursday',
                4: 'friday',
                5: 'saturday',
                6: 'sunday'
                }

# the range of hour is [0 ~ 23]
# the range of minute is [0 ~ 59]
# the range of second is [0 ~ 59]
# the range of microsecond is [0 ~ 999999]
def wakeup_on_time(hour, minute=0, second=0, microsecond=0):
    cur_time = datetime.now()
    des_time = cur_time.replace(hour=hour, minute=minute, second=second, microsecond=microsecond)
    if des_time > cur_time:
        delta = des_time - cur_time
    elif des_time < cur_time:
        day_end_time = cur_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        today_delta = day_end_time - cur_time
        day_start_time = cur_time.replace(hour=0, minute=0, second=0, microsecond=0)
        delta = des_time - day_start_time + today_delta
    
    skip_seconds = delta.total_seconds()
    eventlet.sleep(skip_seconds)

def wakeup_every_time(hour, minute=0, second=0):
    skip_seconds = (hour * 60 * 60 + 
                    minute * 60 +
                    second)

    eventlet.sleep(skip_seconds)
   
class NowTime(object):
    def __init__(self):
        self.time_struct = time.localtime()

    def year(self):
        return self.time_struct.tm_year

    def month(self):
        return self.time_struct.tm_mon
 
    def mday_of_month(self):
        return self.time_struct.tm_mday

    def weekday_of_today(self):
        return self.time_struct.tm_wday

    def weekday_string_of_today(self):
        return MAPPING_WEEKDAY[self.weekday_of_today()]

    def time_of_day(self):
        return (self.time_struct.tm_hour, 
                self.time_struct.tm_min, 
                self.time_struct.tm_sec)
    
    def total_days_this_month(self):
        monthRange = calendar.monthrange(self.time_struct.tm_year, 
                                        self.time_struct.tm_mon)
        return monthRange[1]

if __name__ == "__main__":
    """
    print "start: ", time.time()
    now = time.time()
    wakeup_on_time(10, 46, 0, 0)
    cur = time.time()
    print "end: ", cur
    print "during: ", (cur -now)
    """
    now_time = NowTime()
    print "weekday:", now_time.weekday_of_today()
    print "weekday string: ", now_time.weekday_string_of_today()
    print "year: ", now_time.year()
    print "month: ", now_time.month()
    print "date: ", now_time.mday_of_month()
    print "time: ", now_time.time_of_day()
    print "total days: ", now_time.total_days_this_month()
