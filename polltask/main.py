#-*- coding: utf-8 -*-

from config import get_default_config
from service import Service

def main():
    default_config = get_default_config()
    task_names = default_config.get_option_value('task_list', 'task_names')
    task_names = task_names.replace(' ', '').split(',')
    task_info = []
    for name in task_names:
        task_info.append({'task_name':name})

    service_threads = Service(5, *task_info)
    service_threads.start()
    service_threads.wait()

if __name__ == "__main__":
    main()
