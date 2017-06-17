#-*- coding: utf-8 -*-

#SELF_TEST = True
#if SELF_TEST: 
#    import sys
#    sys.path.insert(0, '../../')
import time
import datetime

from keystoneclient.v2_0 import client as keystone_client
from novaclient import client as nova_client
import novaclient

from polltask.config import get_default_config, Config
from polltask.timer import NowTime
from polltask.logger import get_default_logger
from __builtin__ import isinstance

Logger = get_default_logger("openstack_utils")

def get_option_from_nova_host(section, option, host=None, password=None):
    if host is None:
        config = Config('/etc/nova/nova.conf')
        return config.get_option_value(section, option)
    else:
        # support to get the nova configure from the remote host
        pass

def get_auth_url_from_nova_host(host=None, password=None):
    if host is None:
        config = Config('/etc/nova/nova.conf')
        auth_uri = config.get_option_value('keystone_authtoken', 'auth_uri')
        auth_version = config.get_option_value('keystone_authtoken', 'auth_version')
        if auth_version is None:
            auth_version = 'v2.0'
        if auth_uri.endswith('/'):
            auth_url = auth_uri + auth_version
        else:
            auth_url = auth_uri + '/' + auth_version
        return auth_url
    else:
        # support to get the nova configure from the remote host
        pass

def get_auth_url():
    default_config = get_default_config()
    os_auth_url = default_config.get_option_value('openstack_auth', 'OS_AUTH_URL')
    if not os_auth_url:
        os_auth_url = get_auth_url_from_nova_host()
    return os_auth_url
    
def get_openstack_auth_info():
    default_config = get_default_config()
    os_username = default_config.get_option_value('openstack_auth', 'OS_USERNAME')
    os_password = default_config.get_option_value('openstack_auth', 'OS_PASSWORD')
    os_tenant = default_config.get_option_value('openstack_auth', 'OS_TENANT')
    os_auth_url = get_auth_url()
    return {'OS_USERNAME': os_username,
            'OS_PASSWORD': os_password,
            'OS_TENANT': os_tenant,
            'OS_AUTH_URL': os_auth_url}

def get_keystone_token():
    openstack_auth_info = get_openstack_auth_info()
    os_username = openstack_auth_info['OS_USERNAME']
    os_password = openstack_auth_info['OS_PASSWORD']
    os_tenant = openstack_auth_info['OS_TENANT']
    os_auth_url = openstack_auth_info['OS_AUTH_URL']

    KEYSTONE_CONN = keystone_client.Client(
                        auth_url=os_auth_url,
                        username=os_username,
                        password=os_password,
                        tenant=os_tenant)

    OS_TOKEN = KEYSTONE_CONN.get_token(KEYSTONE_CONN.session)
    RAW_TOKEN = KEYSTONE_CONN.get_raw_token_from_identity_service(
                auth_url=os_auth_url,
                username=os_username,
                password=os_password,
                tenant_name=os_tenant)
    return (OS_TOKEN, RAW_TOKEN)

def get_novaclient(version='1.1'):
    openstack_auth_info = get_openstack_auth_info()
    os_username = openstack_auth_info['OS_USERNAME']
    os_auth_url = openstack_auth_info['OS_AUTH_URL']
    
    os_token, os_raw_token = get_keystone_token()
    os_tenant_id = os_raw_token['token']['tenant']['id']
    
    NOVA_CONN = nova_client.Client('1.1',
                                auth_url=os_auth_url,
                                username=os_username,
                                auth_token=os_token,
                                tenant_id=os_tenant_id)
    
    return NOVA_CONN

def get_one_day_time():
    return 1 * 24 * 60 * 60

def get_current_time():
    d_time = time.strftime("%Y/%m/%d")
    y, m, d = d_time.split('/')[0:3]
    t_time = time.mktime(datetime.datetime(int(y), int(m), int(d)).timetuple())
    return t_time

def convert_datetime_to_time(d_time):
    """Just convert the time based on the number of days.
    """
    d_time = str(d_time)
    y, m, d = time.strptime(d_time, '%Y-%m-%dT%H:%M:%SZ')[0:3]
    t_time = time.mktime(datetime.datetime(y,m,d).timetuple())
    return t_time

def get_instance(nova_conn, instance_id):
    #if not isinstance(nova_conn, nova_client.Client):
    #    raise Exception("Not the novaclient.v1_1.client.Client instance, please check!")
    instance = nova_conn.servers.get(instance_id)
    return instance

def get_instance_created_time(instance):
    return instance._info['created']

def get_instance_created_timestamp(instance):
    u_created = get_instance_created_time(instance)
    created_time = convert_datetime_to_time(u_created)
    return created_time

def get_all_variable_instances(nova_conn):
    #PERMANET_FLAG = "immobilization"
    VARIABLE_FLAG = "variable"
    instances = nova_conn.servers.get_enduring_control()

    variable_instances = []
    instances = instances[1]
    for instance in instances.values()[0]:
        if instance['during'] == VARIABLE_FLAG:
            variable_instances.append(instance)
    
    return variable_instances

def _day_is_ready_to_revert(created_time, during):
    """
    now_time = get_current_time()
    created_time = convert_datetime_to_time(created_time)
    during_time = during * get_one_day_time()
    if (now_time - created_time) % during_time == 0:
        return True
    else:
        return False
    """
    return True

def _week_is_ready_to_revert(create_time, during):
    now_time = NowTime()
    weekday = now_time.weekday_string_of_today()
    if during.lower() == weekday:
        return True
    else:
        return False

def _month_is_ready_to_revert(create_time, during):
    during = int(during)
    now_time = NowTime()
    monthday = now_time.mday_of_month()
    total_days = now_time.total_days_this_month()
    if during > total_days:
        during = total_days
    if monthday == during:
        return True
    else:
        return False

def is_ready_to_revert(flag, created_time, during):
    if flag is None:
        return False
    elif flag == 'day_id':
        return _day_is_ready_to_revert(created_time, during)
    elif flag == 'week_id':
        return _week_is_ready_to_revert(created_time, during)
    elif flag == 'month_id':
        return _month_is_ready_to_revert(created_time, during)

   
def revert_specified_snapshot(nova_conn, instance_id, snapshot_name=None):
    #if not isinstance(nova_conn, nova_client.Client):
    #    raise Exception("Not the novaclient.v1_1.client.Client instance, please check!")
    instance = nova_conn.servers.get(instance_id)
    snapshots = instance.dev_snapshot_list()
    if len(snapshots) == 0:
        instance.dev_snapshot_create(dev_id=None)
        snapshots = instance.dev_snapshot_list()
        snapshot_name = snapshots[0].snapshotname
        Logger.info("The VM [{0}] does not have any snapshot, create a snapshot [{1}]!".format(instance_id, snapshot_name))
        return snapshot_name
        #raise Exception("The VM [{0}] does not have any snapshot!".format(instance_id))
    snapshot_names = [snapshot.snapshotname for snapshot in snapshots]
    if snapshot_name is None:
        # choose the latest snapshot to revert
        snapshot_name = snapshots[-1].snapshotname
    else:
        if snapshot_name not in snapshot_names:
            raise Exception("The specified snapshot [{0}] does not exist in the instance [{1}]".format(snapshot_name, instance_id))
    instance.dev_snapshot_revert(name=snapshot_name)
    return snapshot_name

def stop_specified_instance(nova_conn, instance_id):
    try:
        instance = nova_conn.servers.get(instance_id)
    except novaclient.exception.NotFound as e:
        raise e
    instance.stop()  
    
def start_specified_instance(nova_conn, instance_id):
    try:
        instance = nova_conn.servers.get(instance_id)
    except novaclient.exception.NotFound as e:
        raise e
    instance.start()  

if __name__ == "__main__":
    #import pdb
    #pdb.set_trace()
    client = get_novaclient() 
    client.servers.list()
    
    variable_instances = get_all_variable_instances(client)
    print "All variable instances: ", variable_instances

    cur_time = get_current_time()
    print "Current time: ", cur_time
