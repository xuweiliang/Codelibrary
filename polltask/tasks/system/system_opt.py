#-*- coding: utf-8 -*- 

import subprocess
from subprocess import Popen
import os
import json
import socket
import re
import time
import copy
import shutil
import uuid

import pexpect
import eventlet
from eventlet import wsgi
import routes
from routes import Mapper, route
import webob.dec

from polltask.task import Task
from polltask.config import get_default_config
from polltask.wsgi import Router, Application, Request, Loader
from polltask.logger import get_default_logger
from polltask.ssh_connection import SSHConnection
from polltask.utils import (kernel_module_is_loaded,
                            hostname_to_ip, 
                            get_nic_name_by_ip, 
                            get_local_host, 
                            get_host_nics, 
                            get_nic_info,
                            get_host_disks,
                            get_host_disk_info,
                            generate_uuid_str, 
                            translate_netmask_to_cidr_prefix,
                            generate_ssh_key,
                            copy_ssh_key_to,
                            get_domain_name,
                            format_host_disk_clean,
                            format_host_disk_part,
                            mkfs_disk_part,
                            get_zfs_pool_status,
                            get_path_size,
                            reset_zfs_mem_cache,
                            command_exists,
                            rebase_image)
from polltask.utils import get_bond_slaves as local_get_bond_slaves
from polltask.ovs_db import add_interface_to_port, remove_interface_to_port
from polltask.exception import NICNotFound, ConfigNotFound, TimeoutException
from polltask.setting import (ZFS_POOL_NAME_PREFIX, 
                                DEFAULT_ZFS_RAID_TYPE,
                                DEFAULT_ZFS_LOG_CACHE_RATE,
                                DEFAULT_ZFS_POOL_MOUNT_POINT,
                                ZFS_CREATE_STATE,
                                AUTO_GENERATE_POOL_NAME_NUMBER,
                                RC_LOCAL_PATH)
from polltask.tasks.thin_device.db.api import API

import tarfile
from io import BytesIO
import base64
import hashlib
BACKUP_PATH = '/opt/'

def store_original_config(ssh, config, tmp_path):
    ssh.send_expect('mkdir -p {0}'.format(tmp_path), '# ')
    dest_path = os.path.join(tmp_path, os.path.basename(config))
    ssh.send_expect('rm -f {0}'.format(dest_path), '# ')
    ssh.send_expect('cp -f {0} {1}'.format(config, tmp_path), '# ')

def restore_original_config(ssh, config, tmp_path):
    config_name = os.path.basename(config)
    config_original_path = os.path.dirname(config)
    tmp_config = os.path.join(tmp_path, config_name) 
    ssh.send_expect("rm -f {0}".format(config), '# ')
    cmd = "cp -f {0} {1}".format(tmp_config, config_original_path)
    ssh.send_expect(cmd, '# ') 

def get_remote_openstack_option(ssh, 
                                config,
                                section,
                                option):
    cmd = "openstack-config --get %s %s %s" % \
            (config, section, option)
    retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
    return (retcode, ret)

def set_remote_openstack_option(ssh,
                                config,
                                section,
                                option,
                                value):
    cmd = "openstack-config --set %s %s %s %s" % \
            (config, section, option, value)
    retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
    return (retcode, ret)

def get_remote_nova_home_path(ssh, 
                               default_nova_config='/etc/nova/nova.conf'):
    return get_remote_openstack_option(ssh, 
                                        default_nova_config, 
                                        'DEFAULT',
                                        'state_path')

def reset_remote_nova_home_path(ssh, 
                                new_home_path,
                                default_nova_config='/etc/nova/nova.conf'):
    retcode, ret = set_remote_openstack_option(ssh, 
                                        default_nova_config,
                                        'DEFAULT',
                                        'state_path',
                                        new_home_path)
    if retcode != 0:
        return (retcode, ret)

    retcode, ret = set_remote_openstack_option(ssh, 
                                        default_nova_config,
                                        'DEFAULT',
                                        'lock_path',
                                        os.path.join(new_home_path, 'tmp'))
    if retcode != 0:
        set_remote_openstack_option(ssh, 
                                        default_nova_config,
                                        'DEFAULT',
                                        'state_path',
                                        new_home_path)
    return (retcode, ret)
    

def get_remote_glance_home_path(ssh,
                      default_glance_config='/etc/glance/glance-api.conf'):
    retcode, ret = get_remote_openstack_option(ssh,
                                            default_glance_config,
                                            'DEFAULT',
                                            'image_cache_dir')
    if retcode == 0:
        image_cache_dir = ret.strip().rstrip('/')
        return (0, os.path.dirname(image_cache_dir)) 
    else:
        return retcode, ret

def reset_remote_glance_home_path(ssh,
                                new_home_path):
    reset_list = [{'config': '/etc/glance/glance-api.conf',
                    'section': 'DEFAULT',
                    'option': 'scrubber_datadir',
                    'value': os.path.join(new_home_path, 'scrubber')},
                  {'config': '/etc/glance/glance-api.conf',
                    'section': 'DEFAULT',
                    'option': 'image_cache_dir',
                    'value': os.path.join(new_home_path, 'image-cache')},
                  {'config': '/etc/glance/glance-api.conf',
                    'section': 'glance_store',
                    'option': 'filesystem_store_datadir',
                    'value': os.path.join(new_home_path, 'images/')},
                  #{'config': '/etc/glance/glance-api.conf',
                  #  'section': 'glance_store',
                  #  'option': 'filesystem_store_datadirs',
                  #  'value': os.path.join(new_home_path, 'images/:1')},
                  {'config': '/etc/glance/glance-cache.conf',
                    'section': 'DEFAULT',
                    'option': 'image_cache_dir',
                    'value': os.path.join(new_home_path, 'image-cache/')},
                  {'config': '/etc/glance/glance-cache.conf',
                    'section': 'DEFAULT',
                    'option': 'filesystem_store_datadir',
                    'value': os.path.join(new_home_path, 'images/')},
                  {'config': '/etc/glance/glance-scrubber.conf',
                    'section': 'DEFAULT',
                    'option': 'scrubber_datadir',
                    'value': os.path.join(new_home_path, 'scrubber')}]  

    retcode, old_home_path = get_remote_glance_home_path(ssh)
    if retcode != 0:
        return retcode, old_home_path

    has_reseted_list = []
    for reset_dict in reset_list:
        retcode, ret = set_remote_openstack_option(ssh,
                                        reset_dict['config'],
                                        reset_dict['section'],
                                        reset_dict['option'],
                                        reset_dict['value'])                        
        if retcode != 0:
            for d in has_reseted_list:
                set_remote_openstack_option(ssh,
                                        d['config'],
                                        d['section'],
                                        d['option'],
        os.path.join(old_home_path, os.path.basename(d['value'])))                        
            return retcode, ret
                
        has_reseted_list.append(reset_dict)
    return 0, ''


class SystemOpt(Application):
    def __init__(self):
        super(SystemOpt, self).__init__()
        self.logger = get_default_logger('SystemOpt')
        self._init_system_setting()

    def _init_system_setting(self):
        default_config = get_default_config()
        try:
            system_items = default_config.get_section_items('system_task')
        except Exception as e:
            self.logger.error(e)
            system_items = []

        system_setting = {} 
        for opt, val in system_items:
            system_setting[opt] = val

        if 'clean_orig_data_after_accelerating_disk' not in system_setting.keys():
            system_setting['clean_orig_data_after_accelerating_disk'] = 'True'

        self.system_setting = system_setting

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, req):
        match = req.environ['wsgiorg.routing_args'][1]
        action = match.get('action', None)
        if action is None:
            return webob.exc.HTTPNotFound
        action = action.encode()
        if not hasattr(self, action):
            return webob.exc.HTTPNotImplemented()
        func = getattr(self, action)
        kwargs = dict(req.params.iteritems())
        return func(**kwargs)

    def hello_world(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if key not in kwargs.keys():
                return "no correct params"
        self.logger.info("Hello world!!!")
        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        return "hello_world"

    def reboot(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
        cmd = 'shutdown -r +1'
        self.logger.info("Reboot system!!!")
        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        try:
            ssh.send_expect(cmd, '# ')
        except pexpect.EOF:
            pass
        return "reboot"

    def poweroff(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
        cmd = 'shutdown -P +1'
        self.logger.info("Power off system!!!")
        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        try:
            ssh.send_expect(cmd, '# ')
        except pexpect.EOF:
            pass
        return "poweroff"

    def restart_network(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Restart network!!!")
        try:
            # Restart network by subprocess when the host is the local host
            # or restart network by ssh when the host is the remote host
            cmd = "hostname"
            local_host_name = subprocess.check_output(cmd.split())
            local_host_name = local_host_name.split('\n')

            cmd = "ip addr show | grep 'inet ' | awk '{print $2}'"
            out = subprocess.check_output(cmd, shell=True)
            self.logger.info("CMD: {0}".format(cmd))
            local_ips = out.split('\n')
            local_host_ips = []
            for local_ip in local_ips:
                if '/' in local_ip:
                    local_host_ips.append(local_ip.split('/')[0])
                else:
                    local_host_ips.append(local_ip)

            local_hosts = copy.copy(local_host_name)
            local_hosts.extend(local_host_ips)

            puppet_ssh_know_hosts_path = "/etc/ssh/ssh_known_hosts"

            if kwargs['host'] in local_hosts:
                cmd = "systemctl restart network"
                subprocess.call(cmd.split())
                self.logger.info("CMD: {0}".format(cmd))

                host = subprocess.check_output("hostname -i".split())
                host = host.replace('\n', '')
                """ 
                if not re.match(r'(\d{1,3}\.){3}\d{1,3}', kwargs['host']):
                    for ip in local_host_ips:
                        cmd = "sed -i 's/{orig}/{new}/g' {path}".format(orig=ip, new=host, path=puppet_ssh_know_hosts_path)
                        subprocess.call(cmd, shell=True)
                        self.logger.info("CMD: {0}".format(cmd))
                else:
                    cmd = "sed -i 's/{orig}/{new}/g' {path}".format(orig=kwargs['host'], new=host, path=puppet_ssh_know_hosts_path)
                    subprocess.call(cmd, shell=True)
                    self.logger.info("CMD: {0}".format(cmd))
                """
            else:
                ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

                if not re.match(r'(\d{1,3}\.){3}\d{1,3}', kwargs['host']):
                    cmd = "ip addr show | grep 'inet ' | awk '{print $2}'"
                    out = ssh.send_expect(cmd, '# ')
                    self.logger.info("CMD: {0}".format(cmd))
                    remote_ips = out.split('\n')
                    remote_host_ips = []
                    for remote_ip in remote_ips:
                        if '/' in remote_ip:
                            remote_host_ips.append(remote_ip.split('/')[0])
                        else:
                            remote_host_ips.append(remote_ip)

                host = ssh.send_expect("hostname -i", '# ')

                try:
                    cmd = "systemctl restart network"
                    ssh.send_expect(cmd, '# ')
                except TimeoutException as e:
                    pass
                """
                if not re.match(r'(\d{1,3}\.){3}\d{1,3}', kwargs['host']):
                    for ip in remote_host_ips:
                        if ip == '127.0.0.1':
                            continue
                        cmd = "sed -i 's/{orig}/{new}/g' {path}".format(orig=ip, new=host, path=puppet_ssh_know_hosts_path)
                        subprocess.call(cmd, shell=True)
                        self.logger.info("CMD: {0}".format(cmd))
                else:
                    cmd = "sed -i 's/{orig}/{new}/g' {path}".format(orig=kwargs['host'], new=host, path=puppet_ssh_know_hosts_path)
                    subprocess.call(cmd, shell=True)
                    self.logger.info("CMD: {0}".format(cmd))
                """
        except Exception as e:
            self.logger.error(str(e))
            return "ssh connection error with ip [{0}]".format(kwargs['host'])

        username = kwargs['user']
        password = kwargs['password']

        eventlet.sleep(3)
        try:
            cmd = "ssh-keygen -R {0}".format(host)
            subprocess.call(cmd.split())
            cmd = "ssh-keygen -R {0}".format(kwargs['host'])
            subprocess.call(cmd.split())

            ssh = SSHConnection(host, username, password, 60)
            ssh.send_expect("ssh-keygen -R {0}".format(kwargs['host']), '# ')
            return "restart_network"
        except Exception as e:
            self.logger.error(str(e))    
            return "failed"

    def set_nic_configure(self, **kwargs):
        for key in ['host', 'user', 'password', 'nic', 'nic_param_dict']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
            if key == 'nic_param_dict':
                nic_param_dict = json.loads(kwargs['nic_param_dict'])
                if not isinstance(nic_param_dict, dict):
                    return webob.exc.HTTPBadRequest

        self.logger.info("Set NIC configure!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(str(e))
            return "ssh connection error with ip [{0}]".format(kwargs['host'])

        nic = str(kwargs['nic'])
        tmp_config_path = "/tmp/config_bak"

        cmd = "egrep --color=never '^(NAME|DEVICE) *= *(\")?%s(\")? *$' /etc/sysconfig/network-scripts/ifcfg-* \
               | awk -F ':' '{print $1}'" % nic
        config = ssh.send_expect(cmd, '# ')
        if not config:
            return ConfigNotFound(path='/etc/sysconfig/network-scripts/ifcfg-{0}'.format(nic))

        store_original_config(ssh, config, tmp_config_path)

        for option, value in nic_param_dict.items():
            cmd = "sed -i 's/^\({option} *= *\).*/\\1{new}/g' {path}".format(
                                                    option=option,
                                                    new=value,
                                                    path=config)
            retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
            if retcode:
                restore_original_config(ssh, config, tmp_config_path)
                return 'failed'
            cmd = "cat {path} | egrep --color=never '^{option} *='".format(path=config, option=option)
            retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
            if not retcode:
                if option not in ret:
                    cmd = "echo '{key}={value}' >> {path}".format(key=option, value=value, path=config)
                    retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
                    if not recode:
                        restore_original_config(ssh, config, tmp_config_path)
                        return 'failed'
            else:
                restore_original_config(ssh, config, tmp_config_path)
                return 'failed'

        return 'ok'
     
    def get_nic_configure(self, **kwargs):
        for key in ['host', 'user', 'password', 'nic']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Get NIC configure!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(str(e))
            return "ssh connection error with ip [{0}]".format(kwargs['host'])

        nic = kwargs['nic']
        cmd = "egrep --color=never '^(NAME|DEVICE) *= *(\")?%s(\")? *$' /etc/sysconfig/network-scripts/ifcfg-* \
               | awk -F ':' '{print $1}'" % nic
        config_path = ssh.send_expect(cmd, '# ')
        if not config_path:
            return ConfigNotFound(path='/etc/sysconfig/network-scripts/ifcfg-{0}'.format(nic))

        nic_param_dict = {}
        cmd = "cat {0}".format(config_path)
        config = ssh.send_expect(cmd, '# ')
        if config:
            line_list = config.split('\r\n')
            for line in line_list:
                line.replace(' ', '')
                line.replace('"', '')
                if line != '=' and '=' in line:
                    nic_param = line.split('=')
                    nic_param_dict[nic_param[0]] = nic_param[1]

        return json.dumps(nic_param_dict)

    def get_nic_ip_info_by_ip(self, **kwargs):
        for key in ['host', 'user', 'password', 'ip']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Get NIC IP info!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(str(e))
            return "ssh connection error with ip [{0}]".format(kwargs['host'])

        cmd = "ip addr show | grep 'inet ' | awk '{print $2}'"
        out = ssh.send_expect(cmd, '# ')
        all_nic_ip_info = out.split('\r\n')

        ip_map_prefix_dict = {}
        for ip_info in all_nic_ip_info:
            ip = ip_info.split('/')[0]
            prefix = ip_info.split('/')[1]
            ip_map_prefix_dict[ip] = prefix

        prefix = ip_map_prefix_dict.get(kwargs['ip'], None)
        if prefix is not None:
            ret = {'status': 'success', 'ip':kwargs['ip'], 'prefix': prefix }
        else:
            ret = {'status': 'failed', 'ip':'', 'prefix':''}

        return json.dumps(ret)

    def standardize_nic_configure(self, **kwargs):
        for key in ['host', 'user', 'password', 'nic']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
            #if key == 'old_field_map_new':
            #    old_field_map_new = json.dumps(kwargs['old_field_map_new'])
            #    if not isinstance(old_field_map_new, dict):
            #        return webob.exc.HTTPBadRequest

        self.logger.info("Clear NIC configure!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(str(e))
            return "ssh connection error with ip [{0}]".format(kwargs['host'])

        nic = kwargs['nic']
        cmd = "egrep --color=never '^(NAME|DEVICE) *= *(\")?%s(\")? *$' /etc/sysconfig/network-scripts/ifcfg-* \
               | awk -F ':' '{print $1}'" % nic
        config_path = ssh.send_expect(cmd, '# ')
        if not config_path:
            return ConfigNotFound(path='/etc/sysconfig/network-scripts/ifcfg-{0}'.format(nic))

        for key in ['PREFIX', 'GATEWAY', 'IPADDR', 'NETMASK']:
            cmd = "sed -i 's/^{opt}.*=\(.*\)/{opt}=\\1/g' {path}".format(opt=key, path=config_path)
            ssh.send_expect(cmd, '# ')

        return 'ok'

    def get_nics(self, **kwargs):
        """
        type: 'all', 'general', 'free', 'kernel_bond', 
                'ovs_bond', 'bridge', 'openvswitch'
        """
        for key in ['host', 'user', 'password', 'nic_type']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Get NICs on host!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with host [{0}]".format(kwargs['host'])

        nic_type = kwargs['nic_type']
        choosed_nics = get_host_nics(ssh, nic_type)

        return json.dumps(choosed_nics)

    def get_bond_slaves(self, **kwargs):
        for key in ['host', 'user', 'password', 'bond']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Get the slaves of bond device on host!!!")

        slaves = []
        if not kwargs['bond']:
            return json.dumps(slaves)    

        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with host [{0}]".format(kwargs['host'])

        #prefix = "/sys/class/net/{0}/slave_".format(kwargs['bond'])
        #cmd = "ls -d --color=never /sys/class/net/{0}/slave_*".format(kwargs['bond'])
        #out = ssh.send_expect(cmd, '# ')
        #for slave in out.split():
        #    slave = slave.replace(prefix, '') 
        #    slaves.append(slave)
        bond_driver = kwargs.get('bond_driver', 'openvswitch')
        slaves = local_get_bond_slaves(ssh, kwargs['bond'], bond_driver)
        return json.dumps(slaves)

    def copy_file_to(self, **kwargs):
        for key in ['remote_host', 'remote_user', 'remote_password', 'local_file_path', 'remote_file_path']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
            if key == 'local_file_path':
                local_file_path = kwargs['local_file_path']
                if not local_file_path:
                    return webob.exc.HTTPBadRequest
                else:
                    if local_file_path.endswith('*'):
                        real_local_file_path = local_file_path.rstrip('*') 
                    else:
                        real_local_file_path = local_file_path
                    if (not os.path.isfile(real_local_file_path) and 
                        not os.path.isdir(real_local_file_path)):
                        return "Local file [{0}] not exist!!!".format(real_local_file_path)

        no_auth_login = kwargs.get('no_auth_login', 'false')
        if no_auth_login not in ['true', 'false']:
            return "Not correct no_auth_login value [{0}], please set 'true' or 'false'!!!".format(no_auth_login)

        self.logger.info("Copy file to remote host!!!")
        try:
            ssh = SSHConnection(kwargs['remote_host'], kwargs['remote_user'], kwargs['remote_password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with remote host [{0}]".format(kwargs['remote_host'])

        if os.path.isdir(real_local_file_path):
            local_file_path = "-r {0}".format(kwargs['local_file_path'])            

        remote_file_path = kwargs.get('remote_file_path', '~/')

        if no_auth_login == 'false':
            ssh.copy_file_to(local_file_path, remote_file_path)
        else:
            cmd = "scp {local} {user}@{addr}:{path}".format(local=local_file_path, 
                                                            user=kwargs['remote_user'], 
                                                            addr=kwargs['remote_host'],
                                                            path=remote_file_path)
            self.logger.info("copy_file_to cmd: {0}".format(cmd))
            ret = subprocess.call(cmd.split())
            if ret != 0:
                return 'failed'

        return 'ok'

    def copy_ssh_id_to(self, **kwargs):
        for key in ['local_host', 'local_user', 'local_password', 'remote_host', 'remote_user', 'remote_password']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Copy ssh id from local host to remote host!!!")
        try:
            ssh = SSHConnection(kwargs['local_host'], kwargs['local_user'], kwargs['local_password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with local host [{0}]".format(kwargs['local_host'])

        key_path = generate_ssh_key(ssh)
        if key_path is not None:
            success = copy_ssh_key_to(ssh, kwargs['remote_host'], kwargs['remote_user'], kwargs['remote_password'])
            if success:
                self.logger.info("Copy ssh key successfully!")
                return 'ok'

        return 'failed'

    def get_disks(self, **kwargs):
        """
        disk_type: 'all', 'free'
        only_whole_disk: 'yes', 'no'
        """
        for key in ['host', 'user', 'password', 'disk_type']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
        only_whole_disk = kwargs.get('only_whole_disk', 'no')

        self.logger.info("Get disks on host!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with host [{0}]".format(kwargs['host'])

        disk_type = kwargs['disk_type']
        if only_whole_disk == 'no':
            whole_flag = False
        else:
            whole_flag = True
        choosed_disks = get_host_disks(ssh, disk_type, whole_flag)
        
        return json.dumps(choosed_disks)

    def get_disk_info(self, **kwargs):
        """
        disk_type: 'all', 'whole', 'part', 'part_logical'
        """
        for key in ['host', 'user', 'password', 'disk_type']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Get disk info on host!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with host [{0}]".format(kwargs['host'])

        disk_type = kwargs['disk_type']
        choosed_disk_info = get_host_disk_info(ssh, disk_type)
        
        return json.dumps(choosed_disk_info)

    def create_zfs_pool(self, **kwargs):
        storage_uuid = kwargs.get('storage_uuid', None)
        storage_status_key = 'accelerate_status'
        storage_mountpoint_key = 'mount_path'
        if storage_uuid is not None:
            db_api = API()
        else:
            db_api = None

        def _update_storage_db(key, 
                                value, 
                                db_api=db_api, 
                                storage_uuid=storage_uuid):
            if db_api:
                ret = db_api.storage_update(storage_uuid, 
                                        key, 
                                        value)
                if not ret:
                    self.logger.error("Update storage db key [%s] to [%s] failed"
                            % (key, value))
                    return False
            return True

        for key in ['host', 'user', 'password', 'disks']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
        disks = json.loads(kwargs.get('disks'))
        if len(disks) < 1:
            ret = _update_storage_db(storage_status_key, 
                                        ZFS_CREATE_STATE['create.error'])
            return webob.exc.HTTPBadRequest

        self.logger.info("Create zfs pool!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            _update_storage_db(storage_status_key, 
                                        ZFS_CREATE_STATE['create.error'])
            error_info = "SSH connetcion error with host [{0}]".format(kwargs['host'])
            return {'status': 'failed', 'error': error_info}

        if not kernel_module_is_loaded(ssh, 'zfs'):
            retcode, out = ssh.send_expect("modprobe zfs", "# ", verify=True)
            if retcode != 0:
                self.logger.error(out)
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.error'])
                ret = {'status':'failed', 'error': out}
                return json.dumps(ret)

        zfs_pools = self._get_zfs_pools(ssh)

        pool_name = kwargs.get('pool_name', None)
        if pool_name is None:
            count = 0
            while count < AUTO_GENERATE_POOL_NAME_NUMBER:
                pool_name = generate_uuid_str(ZFS_POOL_NAME_PREFIX) 
                count += 1 
                if pool_name not in zfs_pools:
                    break
            if pool_name in zfs_pools:
                error_info = 'Cannot generate a vaild zfs pool name automatically!!!'
                self.logger.error(error_info)
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.error'])
                ret = {'status':'failed', 'error': error_info}
                return json.dumps(ret)
        else:
            if pool_name in zfs_pools:
                error_info = 'Pool name [{0}] has existed!!!'.format(pool_name)
                self.logger.error(error_info)
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.error'])
                ret = {'status':'failed', 'error': error_info}
                return json.dumps(ret)

        raid_type = kwargs.get('raid_type', None)
        if raid_type is None:
            raid_type = DEFAULT_ZFS_RAID_TYPE

        mount_point = kwargs.get('mount_point', None)
        if mount_point is None:
            mount_point = DEFAULT_ZFS_POOL_MOUNT_POINT

        cmd = "dir -1 {0}".format(mount_point)
        is_dir_retcode, dir_files = ssh.send_expect(cmd, '# ', verify=True)
        if is_dir_retcode == 2:
            dir_files = ''
        if is_dir_retcode in [0, 2] and not dir_files:
            # Create ZFS storage pool with data disks
            _update_storage_db(storage_status_key, 
                                        ZFS_CREATE_STATE['create.storage'])
            retcode, out_storage = self._create_zfs_pool(ssh, pool_name, mount_point, raid_type, *disks)
            if retcode != 0:
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.error'])
                ret = {'status': 'faied', 'error': out_storage}
                return json.dumps(ret)

            # Get the accelerate disk and parted the disk for log and cache device
            accelerate_disk = kwargs.get('accelerator', None)
            if accelerate_disk is not None:
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.accelerate'])
                success, aclrt_log, aclrt_cache = self._mkpart_accelerating_disk(ssh,
                                                            accelerate_disk)
                if not success:
                    _update_storage_db(storage_status_key, 
                                                ZFS_CREATE_STATE['create.error'])
                    self._destroy_zfs_pool(ssh, pool_name)
                    ret = {'status':'failed', 'error': 'Make part accelerate failed!!!'}
                    return json.dumps(ret)
            else:
                aclrt_cache, aclrt_log = '', ''

            # If set accelerate disk, it will just use the accelerate disk to 
            # build cache and log disk.
            # Add cache device for ZFS pool
            out_cache = ''
            if aclrt_cache:
                caches = [aclrt_cache]
            else:
                caches = kwargs.get('cache', None)
                if caches is not None:
                    caches = json.loads(caches)
            if isinstance(caches, list) and caches:
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.cache'])
                retcode, out_cache = self._add_zfs_pool_cache(ssh, pool_name, False, *caches)
                if retcode != 0:
                    _update_storage_db(storage_status_key, 
                                                ZFS_CREATE_STATE['create.error'])
                    self._destroy_zfs_pool(ssh, pool_name)
                    ret = {'status': 'faied', 'error': out_cache}
                    return json.dumps(ret)

            # Add log device for ZFS pool
            out_log = ''
            if aclrt_log:
                log_devs = [aclrt_log]
            else:
                log_devs = kwargs.get('log_dev', None)
                if log_devs is not None:
                    log_devs = json.loads(log_devs)
            if isinstance(log_devs, list) and log_devs:
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.log'])
                retcode, out_log = self._add_zfs_pool_log(ssh, pool_name, False, *log_devs)
                if retcode != 0:
                    _update_storage_db(storage_status_key, 
                                                ZFS_CREATE_STATE['create.error'])
                    self._destroy_zfs_pool(ssh, pool_name)
                    ret = {'status': 'faied', 'error': out_log}
                    return json.dumps(ret)

            # Setup memory cache for ZFS storage
            out_arc_mem = ''
            zfs_arc_mem = kwargs.get('arc_mem', None)
            if zfs_arc_mem is not None:
                _update_storage_db(storage_status_key, 
                                            ZFS_CREATE_STATE['create.mem_cache'])
                retcode, out_arc_mem = reset_zfs_mem_cache(ssh, zfs_arc_mem)
                if retcode != 0:
                    _update_storage_db(storage_status_key, 
                                                ZFS_CREATE_STATE['create.error'])
                    self._destroy_zfs_pool(ssh, pool_name)
                    ret = {'status': 'faied', 'error': out_arc_mem}
                    return json.dumps(ret)

            _update_storage_db(storage_status_key, 
                                        ZFS_CREATE_STATE['create.end'])
            _update_storage_db(storage_mountpoint_key, 
                                        mount_point)

            use_zfs_in_openstack = kwargs.get('use_zfs_in_openstack', 'no')
            if use_zfs_in_openstack and use_zfs_in_openstack.lower() != 'no':
                _update_storage_db(storage_status_key,
                                    ZFS_CREATE_STATE['create.used_openstack'])

                pool_status = get_zfs_pool_status(ssh, pool_name)
                if pool_status is None:
                    _update_storage_db(storage_status_key, 
                                                ZFS_CREATE_STATE['create.error'])
                    ret = {'status': 'faied', 'error': "Get zfs storage size failed!"}
                mount_path_size = pool_status['free']
                retcode, out = self._use_zfs_pool_in_openstack(ssh, 
                                                mount_point, 
                                                mount_path_size)
                if retcode != 0:
                    _update_storage_db(storage_status_key, 
                                                ZFS_CREATE_STATE['create.error'])
                    ret = {'status': 'faied', 'error':out}
                    return json.dumps(ret)

            _update_storage_db(storage_status_key, 
                                        ZFS_CREATE_STATE['create.success'])

            ret = {'status': 'ok', 
                    'error': '', 
                    'need_copy_file_flag': '',
                    'mount_point_rename_path': ''}
        else:
            _update_storage_db(storage_status_key, 
                                        ZFS_CREATE_STATE['create.error'])
            err_info = "mountpoint [%s] exists and is not empty" % mount_point
            ret = {'status': 'failed', 'error': err_info} 

        return json.dumps(ret)

    def _mkpart_accelerating_disk(self, ssh, disk):
        cache_disk = ''
        log_disk = ''

        host_disk_info = get_host_disk_info(ssh, 'all')
        if disk in host_disk_info.keys():
            d_info = host_disk_info[disk]
            d_size = d_info['size']
            d_type = d_info['type']
            if d_type == 'disk':
                log_rate = int(DEFAULT_ZFS_LOG_CACHE_RATE.split(':')[0])
                cache_rate = int(DEFAULT_ZFS_LOG_CACHE_RATE.split(':')[1])
                d_size_num = d_size[:-1]
                d_size_unit = d_size[-1]
                log_size_num = float(d_size_num) * log_rate / (log_rate + cache_rate)
                log_size = str(log_size_num) + d_size_unit

                success, out = format_host_disk_clean(ssh, disk, 'gpt')
                if success != 0:
                    self.logger.error("Reformat disk [%s] failed" % disk)
                    return (False, cache_disk, log_disk)

                success, out = format_host_disk_part(ssh, disk, 'primary', 
                                                        'xfs', 0, log_size)
                if success != 0:
                    self.logger.error("Make part disk [%s] failed for cache" % disk)
                    return (False, cache_disk, log_disk)
                log_disk = disk.strip() + '1'
                retcode, ret = mkfs_disk_part(ssh, log_disk, 'xfs')
                if retcode != 0:
                    self.logger.error("Make log disk [%s] to filesystem \
                                         [%s] failed forcely" % (log_disk, 'xfs'))
                    return (False, cache_disk, log_disk)

                success, out = format_host_disk_part(ssh, disk, 'primary', 
                                                        'xfs', log_size, d_size)
                if success != 0:
                    self.logger.error("Make part disk [%s] failed for log" % disk)
                    return (False, cache_disk, log_disk)
                cache_disk = disk.strip() + '2'
                retcode, ret = mkfs_disk_part(ssh, cache_disk, 'xfs')
                if retcode != 0:
                    self.logger.error("Make cache disk [%s] to filesystem \
                                         [%s] failed forcely" % (cache_dis, 'xfs'))
                    return (False, cache_disk, log_disk)

                return (True, log_disk, cache_disk)
            elif d_type == 'part':
                return (True, disk, '')
            else:
                self.logger.error("Disk type is not appropriate for cahce and log!")
                return (False, '', '')
        else:
            self.logger.error("Disk [%s] does not exist on host!" % disk)
            return (False, '', '')

    def _create_zfs_pool(self, ssh, pool_name, mountpoint, raid_type, *disks, **opt_values):
        if raid_type.upper() == 'RAID0':
            storage_str = ' '.join(disks)
        elif raid_type.upper() == 'RAID10':
            storage_str = ' '
            for i in range(0, len(disks), 2):
                mirror_str = ' '.join(['mirror', disks[i], disks[i+1]])
                storage_str = storage_str + ' ' + mirror_str
        elif raid_type.upper() == 'RAIDZ':
            storage_str = 'raidz1 ' + ' '.join(disks)
        else:
            raise Exception("Not support ZFS raid type [%s]!" % raid_type)

        for disk in disks:
            success, out = format_host_disk_clean(ssh, disk, 'gpt')
            if success != 0:
                self.logger.error("Reformat disk [%s] failed" % disk)
                return (success, out)

        cmd = "zpool create -f -o ashift=12 {name} {storage} -m {point}".format(name=pool_name, 
                                                                    storage=storage_str,
                                                                    point=mountpoint)
        retcode, out = ssh.send_expect(cmd, '# ', verify=True)

        if retcode == 0:
            # Optimize the zfs storage
            #opt_values = {'compression': 'on',
            #                'dedup': 'on',
            #                'atime': 'off',
            #                'setuid': 'off'}
            for opt, value in opt_values.items():
                cmd = "zfs set {opt}={val} {pool}".format(opt=opt, val=value, pool=pool_name)
                retcode, out_set_storage = ssh.send_expect(cmd, '# ', verify=True)
                if retcode != 0:
                    error_info = "Set ZFS pool [{pool}] option [ {opt}={val} ] failed!!!"
                    self.logger.error(error_info.format(pool=pool_name, opt=opt, val=value))
                    return retcode, error_info

        return retcode, out

    def _use_zfs_pool_in_openstack(self, ssh, data_path, data_path_size):
        total_mv_storage_size = 0

        moved_project = []
        retcode, nova_home_dir = get_remote_nova_home_path(ssh)
        if retcode != 0:
            return retcode, nova_home_dir 
        nova_image_base_dir = os.path.join(nova_home_dir, "instances/_base")
        retcode, glance_home_dir = get_remote_glance_home_path(ssh)
        if retcode != 0:
            #return retcode, glance_home_dir
            self.logger.info("There is no glance home dir!")
            glance_home_dir = ''

        nova_dir_exist = False
        cmd = "dir -1 %s" % nova_home_dir
        is_nova_dir_retcode, dir_files = ssh.send_expect(cmd, '# ', verify=True)
        if is_nova_dir_retcode == 0:
            nova_dir_exist = True
            moved_project.append('Nova')
            nova_dir_size = get_path_size(ssh, nova_home_dir)
            total_mv_storage_size += int(nova_dir_size)

        glance_dir_exist = False
        if glance_home_dir:
            cmd = "dir -1 %s" % glance_home_dir
            is_glance_dir_retcode, dir_files = ssh.send_expect(cmd, '# ', verify=True)
            if is_glance_dir_retcode == 0:
                glance_dir_exist = True
                moved_project.append('Glance')
                glance_dir_size = get_path_size(ssh, glance_home_dir)
                total_mv_storage_size += int(glance_dir_size)

        if data_path_size <= total_mv_storage_size:
            projects = ' and '.join(moved_project)
            message = "The total size [%s] of " % total_mv_storage_size +\
                        projects +\
                        " is bigger than the total size [%s] " +\
                        "of data storage [%s]!" % data_path
            self.logger.error(message)
            return 1, message

        def _cp_cmd(ssh, src, dst):
            try:
                cmd = "cp -a %s %s" % (src, dst)
                retcode, out = ssh.send_expect(cmd, '# ', timeout=None, verify=True)
            except Exception as e:
                out = str(e)
                retcode = 1
            return retcode, out

        #def _rename_cmd(ssh, f_path, new_name):
        #    try:
        #        f_dirname = os.path.dirname(f_path) 
        #        new_path = os.path.join(f_dirname, new_name)
        #        cmd = "mv %s %s" % (f_path, new_path)
        #        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        #    except Exception as e:
        #        out = str(e)
        #        retcode = 1
        #        new_path = ''
        #    return retcode, out, new_path

        def _delete_cmd(ssh, f_path, option='-f'):
            try:
                cmd = "rm %s %s" % (option, f_path)
                retcode, out = ssh.send_expect(cmd, '# ', timeout=120, verify=True)
            except Exception as e:
                out = str(e)
                retcode = 1
            return retcode, out

        clean_orig_data = self.system_setting['clean_orig_data_after_accelerating_disk']
        clean_orig_data = clean_orig_data.lower()
        if clean_orig_data in ['false', 'true']:
            if clean_orig_data == 'true':
                clean_data = True
            else:
                clean_data = False
        else:
            clean_data = True

        if nova_dir_exist:
            cmd = "openstack-service stop openstack-nova-compute"
            retcode, out = ssh.send_expect(cmd, '# ', verify=True)
            if retcode != 0:
                self.logger.error(out)

            # If there are some vms, firstly stop them.
            cmd = "dir -1 {0}".format(nova_image_base_dir)
            is_dir_retcode, dir_files = ssh.send_expect(cmd, '# ', verify=True)
            if is_dir_retcode == 0 and dir_files:
                # Shutdown the VMs on host
                try:
                    cmd = "/usr/libexec/libvirt-guests.sh shutdown"
                    ssh.send_expect(cmd, '# ', timeout=None)
                except Exception as e:
                    self.logger.error(e)
                    cmd = "openstack-service start openstack-nova-compute"
                    ssh.send_expect(cmd, '# ')
                    return retcode_nova, out_nova

            retcode_nova, out_nova = _cp_cmd(ssh, nova_home_dir, data_path)
            if retcode_nova != 0:
                self.logger.error("Copy nova home directory failed!")
                cmd = "openstack-service start openstack-nova-compute"
                ssh.send_expect(cmd, '# ')
                return retcode_nova, out_nova

            #retcode_rename_nova, out, bak_nova_home = _rename_cmd(ssh, nova_home_dir, 'nova.bak')
            #if retcode_rename_nova != 0:
            #    self.logger.error("Rename nova home directory failed!")
            #    cmd = "openstack-service start openstack-nova-compute"
            #    ssh.send_expect(cmd, '# ')
            #    return retcode_rename_nova, out

            new_nova_home = os.path.join(data_path, os.path.basename(nova_home_dir))
            #cmd = "ln -s %s %s" % (new_nova_home, nova_home_dir)
            #retcode_ln_nova, out = ssh.send_expect(cmd, '# ', verify=True)
            #if retcode_ln_nova != 0:
            #    self.logger.error("Link the nova home directory failed")

            #cmd = "chown -R nova:nova %s" % nova_home_dir
            #retcode_chown_nova, out = ssh.send_expect(cmd, '# ', verify=True)
            #if retcode_chown_nova != 0:
            #    self.logger.error("Change the owner of the new nova home directory failed!")

            #cmd = "chcon -R -u system_u -r object_r -t nova_var_lib_t %s" % nova_home_dir
            #retcode_chcon_nova, out = ssh.send_expect(cmd, '# ', verify=True)
            #if retcode_chcon_nova != 0:
            #    self.logger.error("Change the selinux context of the new nova home directory failed!")            

            #if retcode_ln_nova != 0 or retcode_chown_nova != 0 or retcode_chcon_nova != 0:
            #    if retcode_ln_nova == 0:
            #        retcode, out = _delete_cmd(ssh, nova_home_dir)
            #        if retcode != 0:
            #            self.logger.error("Delete the nova link directory failed!")
            #            return retcode, out
            #    retcode, out = _rename_cmd(ssh, bak_nova_home, os.path.basename(nova_home_dir))
            #    if retcode != 0:
            #        self.logger.error("Recover nova home directory failed!")
            #        return retcode, out
            #    else:
            #        cmd = "openstack-service start openstack-nova-compute"
            #        ssh.send_expect(cmd, '# ', verify=True)
            #        return 1, 'Link or change nova directory failed'
            #else:
            #    recode, out = _delete_cmd(ssh, bak_nova_home, '-rf')
            #    if retcode != 0:
            #        self.logger.warn("Delete the nova bak home failed!")

            retcode, ret = reset_remote_nova_home_path(ssh, new_nova_home)
            if retcode == 0:
                retcode, ret = self._rebase_nova_disk(ssh, new_nova_home)
                if retcode != 0:
                    self.logger.warn("There is some errors when rebasing nova images!")

                if clean_data:
                    recode, out = _delete_cmd(ssh, nova_home_dir, '-rf')
                    if retcode != 0:
                        self.logger.warn("Delete the original nova home direcotry [%s] failed!" % nova_home_dir)
            else:
                cmd = "openstack-service start openstack-nova-compute"
                ssh.send_expect(cmd, '# ')
                return retcode, ret

            #cmd = "openstack-service start openstack-nova-compute"
            cmd = "openstack-service restart nova"
            retcode, out = ssh.send_expect(cmd, '# ', verify=True)
            if retcode != 0:
                self.logger.error(out)
                return retcode, out

        if glance_dir_exist:
            cmd = "openstack-service stop openstack-glance-registry"
            retcode, out = ssh.send_expect(cmd, '# ', verify=True)
            if retcode != 0:
                self.logger.error(out)

            retcode_glance, out_glance = _cp_cmd(ssh, glance_home_dir, data_path)
            if retcode_glance != 0:
                cmd = "openstack-service start openstack-glance-registry"
                ssh.send_expect(cmd, '# ')
                return retcode_glance, out_glance

            #retcode_rename_glance, out, bak_glance_home = _rename_cmd(ssh, glance_home_dir, 'glance.bak')
            #if retcode_rename_glance != 0:
            #    self.logger.error("Rename glance home directory failed!")
            #    cmd = "openstack-service start openstack-glance-registry"
            #    ssh.send_expect(cmd, '# ')
            #    return retcode_rename_glance, out

            new_glance_home = os.path.join(data_path, os.path.basename(glance_home_dir))
            #cmd = "ln -s %s %s" % (new_glance_home, glance_home_dir)
            #retcode_ln_glance, out = ssh.send_expect(cmd, '# ', verify=True)
            #if retcode_ln_glance != 0:
            #    self.logger.error("Link the glance home directory failed")

            #cmd = "chown -R glance:glance %s" % glance_home_dir
            #retcode_chown_glance, out = ssh.send_expect(cmd, '# ', verify=True)
            #if retcode_chown_glance != 0:
            #    self.logger.error("Change the owner of the new glance home directory failed!")

            #cmd = "chcon -R -u system_u -r object_r -t glance_var_lib_t %s" % glance_home_dir
            #retcode_chcon_glance, out = ssh.send_expect(cmd, '# ', verify=True)
            #if retcode_chcon_glance != 0:
            #    self.logger.error("Change the selinux context of the new glance home directory failed!")            

            #if retcode_ln_glance != 0 or retcode_chown_glance != 0 or retcode_chcon_glance != 0:
            #    if retcode_ln_glance == 0:
            #        retcode, out = _delete_cmd(ssh, glance_home_dir)
            #        if retcode != 0:
            #            self.logger.error("Delete the glance link directory failed!")
            #            return retcode, out
            #    retcode, out = _rename_cmd(ssh, bak_glance_home, os.path.basename(glance_home_dir))
            #    if retcode != 0:
            #        self.logger.error("Recover glance home directory failed!")
            #        return retcode, out
            #    else:
            #        cmd = "openstack-service start openstack-glance-registry"
            #        ssh.send_expect(cmd, '# ', verify=True)
            #        return 1, 'Link or change glance directory failed'
            #else:
            #    recode, out = _delete_cmd(ssh, bak_glance_home, '-rf')
            #    if retcode != 0:
            #        self.logger.warn("Delete the glance bak home failed!")

            retcode_reset, out_reset = reset_remote_glance_home_path(ssh, new_glance_home)
            if retcode_reset == 0:
                if clean_data:
                    recode, out = _delete_cmd(ssh, glance_home_dir, '-rf')
                    if retcode != 0:
                        self.logger.warn("Delete the glance home directory failed!")
            else:
                cmd = "openstack-service start openstack-glance-registry"
                ssh.send_expect(cmd, '# ')
                return retcode_reset, out_reset

            #cmd = "openstack-service start openstack-glance-registry"
            cmd = "openstack-service restart glance"
            retcode, out = ssh.send_expect(cmd, '# ', verify=True)
            if retcode != 0:
                self.logger.error(out)
                return retcode, out

        return (0, '')

    def _rebase_nova_disk(self, ssh, nova_home_dir, new_baking_file_dir=''):
        if not command_exists(ssh, 'qemu-img'):
            self.logger.warn("Not support qemu-img to rebase image on host!")
            return 1, ''

        instance_home_dir = os.path.join(nova_home_dir, 'instances') 
        if not new_baking_file_dir:
            new_baking_file_dir = os.path.join(nova_home_dir, 'instances/_base')

        cmd = "ls -d %s" % os.path.join(instance_home_dir, '*/')
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True) 
        if retcode != 0:
            self.logger.error("List nova instances directory failed: %s" % ret)
            return 2, ret
        instance_regx = r'(%s/([0-9a-f]+?\-){4}[0-9a-f]+?\/)' % instance_home_dir.rstrip('/')
        instance_dirs = re.findall(instance_regx, ret)
        if not instance_dirs:
            return 0, ''
        else:
            instance_dirs = [d[0] for d in instance_dirs]
        
        for d in instance_dirs:
            disk = os.path.join(d, 'disk')
            cmd = "test -f %s" % disk
            retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
            if retcode != 0:
                self.logger.warn("Nova instance directory [%s] not exist image disk file!" % d)
                continue

            cmd = ("qemu-img info %s | "
                    "grep --color=never 'backing file' | "
                    "awk -F ':' '{print $2}'") % disk
            retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
            if retcode != 0:
                self.logger.error("Get instance disk [%s] backing file failed!" % disk)
                continue

            backing_file = os.path.join(new_baking_file_dir, os.path.basename(ret.rstrip('/')))
            retcode, ret = rebase_image(ssh, backing_file, disk)            
            if retcode != 0:
                self.logger.error(ret)
                continue

        return 0, ''

    def _get_zfs_pools(self, ssh):
        cmd = "zpool list | grep -v NAME | awk '{print $1}'"
        out = ssh.send_expect(cmd, '# ')
        pools = out.split('\r\n')
        if len(pools) == 1 and pools[0] == 'no':
            pools = []

        return pools

    def _add_zfs_pool_cache(self, ssh, pool_name, enable_mirror, *caches):
        cache_str = ' '.join(caches)
        if not enable_mirror:
            cmd = "zpool add {name} cache {cache}".format(name=pool_name, 
                                                            cache=cache_str)
        else:
            cmd = "zpool add {name} cache mirror {cache}".format(name=pool_name, 
                                                                cache=cache_str)

        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            self.logger.error(out)

        return retcode, out

    def _add_zfs_pool_log(self, ssh, pool_name, enable_mirror, *log_devs):
        log_dev_str = ' '.join(log_devs)
        if not enable_mirror:
            cmd = "zpool add {name} log {log_dev}".format(name=pool_name,
                                                    log_dev=log_dev_str)
        else:
            cmd = "zpool add {name} log mirror {log_dev}".format(name=pool_name,
                                                    log_dev=log_dev_str)

        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            self.logger.error(out)

        return retcode, out

    def _add_zfs_pool_storage(self, ssh, pool_name, vdev='', *disks):
        disk_str = ' '.join(disks)
        cmd = "zpool add -f {name} {vdev} {disk}".format(name=pool_name, 
                                                                vdev=vdev, 
                                                                disk=disk_str)
        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            self.logger.error(out)

        return retcode, out

    def add_zfs_pool(self, **kwargs):
        for key in ['host', 'user', 'password', 'pool_name', 'pool_type', 'disks']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
            if key == 'pool_type':
                pool_type = kwargs['pool_type']
                if pool_type not in ['storage', 'cache', 'log']:
                    self.logger.error("Not correct pool type [{0}]".format(pool_type))
                    return webob.exc.HTTPBadRequest
            if key == 'disks':
                disks = json.loads(kwargs.get('disks'))
                if len(disks) < 1:
                    return webob.exc.HTTPBadRequest
            if key == 'pool_name':
                if not kwargs['pool_name']:
                    return webob.exc.HTTPBadRequest

        self.logger.info("Add zfs pool [{0}] disks!!!".format(pool_type))
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with host [{0}]".format(kwargs['host'])

        pool_name = kwargs['pool_name']
        disks = json.loads(kwargs['disks'])

        if pool_type == 'cache':
            enable_mirror = kwargs.get('enable_mirror', 'no')
            if enable_mirror == 'no':
                out = self._add_zfs_pool_cache(ssh, pool_name, False, *disks)
            else:
                out = self._add_zfs_pool_cache(ssh, pool_name, True, *disks)
        elif pool_type == 'log':
            enable_mirror = kwargs.get('enable_mirror', 'no')
            if enable_mirror == 'no':
                out = self._add_zfs_pool_log(ssh, pool_name, False, *disks)
            else:
                out = self._add_zfs_pool_log(ssh, pool_name, True, *disks)
        elif pool_type == 'storage':
            raid_type = kwargs.get('raid_type', None)
            if raid_type is None:
                raid_type = DEFAULT_ZFS_RAID_TYPE

            out = self._add_zfs_pool_storage(ssh, pool_name, raid_type, *disks)
        if not out:
            ret = {'status': 'ok', 'error': ''}
        else:
            ret = {'status': 'failed', 'error': out}

        return json.dumps(ret)

    def get_zfs_pools(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Get zfs pools!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with host [{0}]".format(kwargs['host'])

        if not kernel_module_is_loaded(ssh, 'zfs'):
            retcode, out = ssh.send_expect("modprobe zfs", "# ", verify=True)
            if retcode != 0:
                ret = {'status':'failed', 'error': out}
                return json.dumps(ret)

        zfs_pools = self._get_zfs_pools(ssh)

        ret = {'status': 'ok', 'error':'', 'pools': zfs_pools}
        return json.dumps(ret)

    def destroy_zfs_pools(self, **kwargs):
        POOL_NAME_SEPARATOR = ':'
        for key in ['host', 'user', 'password']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest

        self.logger.info("Destroy zfs pool!!!")
        try:
            ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        except Exception as e:
            self.logger.error(e)
            return "SSH connetcion error with host [{0}]".format(kwargs['host'])

        host_pool_names = self._get_zfs_pools(ssh)
        pool_names = kwargs.get('pool_names', '')
        if not pool_names: 
            pool_names = host_pool_names
        else:
            pool_names = pool_names.split(POOL_NAME_SEPARATOR)
            pool_names = [p_n.strip() for p_n in pool_names]
            not_exist_pools = []
            for p_n in pool_names:
                if p_n not in host_pool_names:
                    not_exist_pools.append(p_n)
            if not_exist_pools:
                msg = "Pool %s not exist on host!" % not_exist_pools
                ret = {'status': 'failed', 'error': msg}
            ret = {'status': 'ok', 'error': ''}
            return json.dumps(ret)

        for p_n in pool_names:
            retcode, out = self._destroy_zfs_pool(ssh, p_n)
            if retcode != 0:
                ret = {'status': 'failed', 'error': out}
                return json.dumps(ret)

        ret = {'status': 'ok', 'error': ''}
        return json.dumps(ret)

    def _destroy_zfs_pool(self, ssh, pool_name):
        #cmd = "zfs mount"
        #retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        #if retcode == 0:
        #    pool_mount_dict = {}
        #    zfs_mount_lines = out.split('\r\n')
        #    for line in zfs_mount_lines:
        #        p_m = line.split()
        #        pool_mount_dict[p_m[0]] = p_m[1]
        #    if pool_name in pool_mount_dict.keys():
        #        cmd = "zfs umount -f %s" % pool_mount_dict[pool_name] 
        #        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        #        if retcode == 0:
        #            cmd = "sed -i '/zfs mount/d' {0}".format(RC_LOCAL_PATH)
        #            ssh.send_expect(cmd, '# ')
        #        else:
        #            self.logger.error("ZFS umount mountpoint [%s] failed!" % pool_mount_dict[pool_name])
        #            return retcode, out
        #else:
        #    self.logger.error("zfs list mountpoint failed!")
        #    return retcode, out

        cmd = "zpool destroy -f {0}".format(pool_name)
        retcode, out = ssh.send_expect(cmd, '# ', verify=True) 
        if out:
            if 'no such pool' in out:
                retcode = 0
                out = ''
        return retcode, out

    def dev_dumpdb(self):
        import os
        self.logger.info("dev_dumpdb IN")
        
        file_dict = {} 
        time_name = time.strftime('%Y%m%d-%H%M%S')
        filename_sql = BACKUP_PATH + time_name + '.sql'
        #filename_out = time_name + '.sql'
        cmd = "mysqldump --opt --all-databases > %s" % filename_sql
        #print cmd
        subprocess.Popen(cmd,shell=True)
        time.sleep(1)
        #now generated *.sql file

        #out = BytesIO()
        #tar = tarfile.open(mode = "w:gz", fileobj = out)
        f = open(filename_sql, 'rb')
        sql_data = f.read()

        #sql_data_gbk = sql_data.decode('GBK')
        #data = sql_data_gbk.encode('utf-8')
        #file_in = BytesIO(data)
        #info = tarfile.TarInfo(name=filename_sql)
        #info.size = len(data)

        #tar.addfile(tarinfo=info, fileobj=file_in)
        #tar.close()
        #buf = base64.b64encode(out.getvalue()).decode()
        file_dict={'filename':time_name, 'buffer_out':sql_data}
        #file_dict["filename"] = json.dumps(filename_tgz)
        #file_dict["buffer_out"] = json.dumps(out)
        f.close()
        #os.remove(filename_sql)       
        self.logger.info("dev_dumpdb OUT")
        return json.dumps(file_dict)
