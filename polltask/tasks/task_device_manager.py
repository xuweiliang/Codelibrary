from polltask.task import Task


class TaskDeviceManager(Task):
    def __init__(self, status_queue):
        super(TaskDeviceManager, self).__init__(status_queue, 
                                                'TaskDeviceManager', 
                                                'subwsgi', 
              task_desc='Manager devices linking with the openstack controller')

    def register(self, mapper, loader):
        func= getattr(mapper, 'connect')
	device_controller = loader.load_app('device_manager')
        func('/device/get_spice_proxy',
             controller=device_controller,
             action='get_spice_proxy',
             conditions=dict(method=['GET']))
        func('/device/update_spice_proxy',
             controller=device_controller,
             action='update_spice_proxy',
             conditions=dict(method=['POST']))
        func('/device/spice_proxy',
             controller=device_controller,
             action='spice_proxy_detail',
             conditions=dict(method=['GET']))
        func('/device/get',
             controller=device_controller,
             action='get_dev_by_id',
             conditions=dict(method=['GET']))
        func('/device/list', 
             controller=device_controller, 
             action='detail', 
             conditions=dict(method=['GET']))
        func('/device/reboot',
             controller=device_controller,
             action='dev_reboot',
             conditions=dict(method=['GET']))
        func('/device/dev_stop',
             controller=device_controller,
             action='dev_stop',
             conditions=dict(method=['GET']))
        func('/device/start',
             controller=device_controller,
             action='dev_start',
             conditions=dict(method=['GET']))
        func('/device/delete',
            controller=device_controller,
             action='dev_delete',
             conditions=dict(method=['DELETE']))
        func('/device/status',
             controller=device_controller,
             action='dev_status',
             conditions=dict(method=['POST']))
        func('/device/send',
             controller=device_controller,
             action='push_message',
             conditions=dict(method=['POST']))
        func('/device/update',
             controller=device_controller,
             action='update',
             conditions=dict(method=['POST']))
        func('/device/check_ip',
             controller=device_controller,
             action='device_check_ipaddr',
             conditions=dict(method=['GET']))
        func('/device/storage_list',
             controller=device_controller,
             action='storage_list',
             conditions=dict(method=['GET']))
        func('/device/storage_insert',
             controller=device_controller,
             action='storage_insert',
             conditions=dict(method=['POST']))
        func('/device/storage_update',
             controller=device_controller,
             action='storage_update',
             conditions=dict(method=['POST']))
        #func('/device/dump_db',
        #     controller=device_controller,
        #     action='dev_dumpdb',
        #     conditions=dict(method=['GET']))
