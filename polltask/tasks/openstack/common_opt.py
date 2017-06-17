#-*- coding: utf-8 -*- 

import os
import json
import socket
import re
import time

import eventlet
from eventlet import wsgi
import webob.dec

from polltask.wsgi import Application, Request
from polltask.logger import get_default_logger
from polltask.ssh_connection import SSHConnection
from polltask.utils import (hostname_to_ip, 
                            get_nic_name_by_ip, 
                            get_local_host, 
                            get_host_nics, 
                            get_nic_info,
                            get_domain_name,
                            get_host_disk_info,
                            format_host_disk_clean,
                            format_host_disk_part,
                            transfer_unit_to_byte)
from polltask.utils import get_bond_slaves as local_get_bond_slaves
from polltask.ovs_db import add_interface_to_port, remove_interface_to_port
from polltask.exception import NICNotFound, ConfigNotFound, TimeoutException
from polltask.config import Config


class CommonOpt(Application):
    # node will restart after the delay time
    # the time unit is minute 
    CONTROL_NODE_RESTART_DELAY = 1
    COMPUTE_NODE_RESTART_DELAY = 6
    def __init__(self):
        super(CommonOpt, self).__init__()
        self.logger = get_default_logger('OpenstackCommonOpt') 

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

    def reset_ip_config(self, **kwargs):
        for key in ['host', 'user', 'password', 'new_ip', 'other_nodes']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
            if key == 'other_nodes':
                other_nodes = json.loads(kwargs['other_nodes'])
                for node_info in other_nodes:
                    if not isinstance(node_info, dict):
                        continue
                    for sub_key in ['host', 'user', 'password']:
                        if sub_key not in node_info.keys():
                            return webob.exc.HTTPBadRequest
                
        self.logger.info("Reset ip relating to the host of {0}".format(kwargs['host']))
        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        new_ip = kwargs['new_ip']
        old_ip = hostname_to_ip(ssh)
        
        self._tmp_config_path = "/tmp/config_bak"
        self._all_sshs = set()
        self._ssh_config_pair = []

        try:
            netmask = kwargs.get('netmask', None)
            gateway = kwargs.get('gateway', None)
            dns = kwargs.get('dns', None)
            ret = self._reset_nic_config(ssh, old_ip, new_ip, netmask, gateway, dns)
        except ConfigNotFound:
            return "NOT found NIC configure"
        if int(ret) != 0:
            for ssh_config in self._ssh_config_pair:
                self._restore_original_config(ssh_config['ssh'], 
                                               ssh_config['config'], 
                                               self._tmp_config_path)
                ssh_config['ssh'].close()
            return webob.exc.HTTPExpectationFailed("Configure IPADDR for NIC failed")

        ret = self._reset_all_hosts_config(ssh, old_ip, new_ip, json.loads(kwargs['other_nodes'])) 
        if int(ret) != 0:
            for ssh_config in self._ssh_config_pair:
                self._restore_original_config(ssh_config['ssh'],
                                                ssh_config['config'],
                                                self._tmp_config_path)
                ssh_config['ssh'].close()
            return webob.exc.HTTPExpectationFailed("Configure IPADDR for /etc/hosts failed")

        ret = self._reset_neutron_config(ssh, new_ip)
        if int(ret) != 0:
            for ssh_config in self._ssh_config_pair:
                self._restore_original_config(ssh_config['ssh'],
                                                ssh_config['config'],
                                                self._tmp_config_path)
                ssh_config['ssh'].close()
            return webob.exc.HTTPExpectationFailed("Configure IPADDR for neutorn local ip failed")

        service_bind_ip = socket.gethostbyname(socket.gethostname())
        self._stop_nfs(ssh, service_bind_ip)
        self._operate_openstack_services_by_ip(ssh, 'stop', service_bind_ip)

        self._close_conn()
        return "reset_ip_config"

    def restart_openstack_services(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
            if key == 'other_nodes':
                other_nodes = json.loads(kwargs['other_nodes'])
                for node_info in other_nodes:
                    if not isinstance(node_info, dict):
                        continue
                    for sub_key in ['host', 'user', 'password']:
                        if sub_key not in node_info.keys():
                            return webob.exc.HTTPBadRequest
        self._all_sshs = set()

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        self._all_sshs.add(ssh)

        if 'other_nodes' in kwargs.keys():
            other_nodes = json.loads(kwargs['other_nodes'])
            for node in other_nodes:
                other_ssh = SSHConnection(node['host'], node['user'], node['password'])
                self._all_sshs.add(other_ssh)
         
        service_bind_ip = socket.gethostbyname(socket.gethostname())

        self._stop_nfs(ssh, service_bind_ip)
        self._operate_openstack_services_by_ip(ssh, 'restart', service_bind_ip)
        self._start_nfs(ssh, service_bind_ip)

        self._close_conn()

        return "restart_openstack_services"

    def _store_original_config(self, ssh, config, tmp_path):
        ssh.send_expect('mkdir -p {0}'.format(tmp_path), '# ')
        dest_path = os.path.join(tmp_path, os.path.basename(config))
        ssh.send_expect('rm -f {0}'.format(dest_path), '# ')
        ssh.send_expect('cp -f {0} {1}'.format(config, tmp_path), '# ')

    def _restore_original_config(self, ssh, config, tmp_path):
        config_name = os.path.basename(config)
        config_original_path = os.path.dirname(config)
        tmp_config = os.path.join(tmp_path, config_name) 
        ssh.send_expect("rm -f {0}".format(config), '# ')
        cmd = "cp -f {0} {1}".format(tmp_config, config_original_path)
        ssh.send_expect(cmd, '# ') 

    def _reset_nic_config(self, ssh, old_ip, new_ip, netmask=None, gateway=None, dns=None):
        old_ip = str(old_ip)
        new_ip = str(new_ip)
        nic = get_nic_name_by_ip(ssh, old_ip)
        if nic is None:
            return NICNotFound(ip=old_ip)
        nic = str(nic)
        cmd = "egrep --color=never '^(NAME|DEVICE) *= *(\")?%s(\")? *$' /etc/sysconfig/network-scripts/ifcfg-* \
               | awk -F ':' '{print $1}'" % nic
        config = ssh.send_expect(cmd, '# ')
        if not config:
            return ConfigNotFound(path='/etc/sysconfig/network-scripts/ifcfg-{0}'.format(nic))

        self._store_original_config(ssh, config, self._tmp_config_path)

        cmd = "sed -i 's/^\(IPADDR.*= *\).*/\\1{new}/g' {path}".format(
                                                new=new_ip,
                                                path=config)
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)

        if not retcode and netmask:
            cmd = "sed -i '/^PREFIX.*=/d' {path}".format(path=config)
            ssh.send_expect(cmd, '# ')
            cmd = "sed -i '/^NETMASK.*=/d' {path}".format(path=config)
            ssh.send_expect(cmd, '# ')
            #cmd = "sed -i 's/^\(NETMASK *= *\).*/\\1{new}/g' {path}".format(
            #                                        new=netmask,
            #                                        path=config)
            cmd = "echo 'NETMASK={mask}' >> {path}".format(mask=netmask, path=config)
            retcode, ret = ssh.send_expect(cmd, '# ', verify=True)

        if not retcode and gateway:
            cmd = "sed -i 's/^\(GATEWAY.*= *\).*/\\1{new}/g' {path}".format(
                                                    new=gateway,
                                                    path=config)
            retcode, ret = ssh.send_expect(cmd, '# ', verify=True)

        if not retcode and dns:
            cmd = "sed -n '/^DNS.* *=/=' {path}".format(path=config)
            ret = ssh.send_expect(cmd, '# ')
            line = 0
            if ret:
                try:
                    line = int(ret.split('\r\n')[0])
                except:
                    line = 0
            if line:
                cmd = "sed -i '1,{end}s/^\(DNS.* *= *\).*/\\1{new}/' {path}".format(
                                                        end=line,
                                                        new=dns,
                                                        path=config)
                retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
            else:
                cmd = "echo 'DNS1={new}' >> {path}".format(new=dns, path=config)
                retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
         
        self._ssh_config_pair.append({'ssh':ssh, 'config':config})
        return retcode

    def _reset_all_hosts_config(self, ssh, old_ip, new_ip, other_nodes):
        hostname = ssh.send_expect('hostname', '# ')
        hostname = hostname.strip(' ')
        domainname = get_domain_name(ssh)
        ret = self._reset_hosts_config(ssh, hostname, domainname, old_ip, new_ip)
        if int(ret) != 0:
            return ret
        self._all_sshs.add(ssh)

        for node in other_nodes:
            other_ssh = SSHConnection(node['host'], node['user'], node['password'])
            ret = self._reset_hosts_config(other_ssh, hostname, domainname, old_ip, new_ip) 
            if int(ret) != 0:
                return ret
            self._all_sshs.add(other_ssh)

        return ret

    def _reset_hosts_config(self, ssh, hostname, domainname, old_ip, new_ip):
        self._store_original_config(ssh, '/etc/hosts', self._tmp_config_path)
        #cmd = "sed -i 's/.*  *\({host}  *{host}.argos.com\)/{new} \\1/g' /etc/hosts".format(
        #                            new=new_ip,
        #                            host=hostname)
        cmd = "sed -i '/^ *%s .*/d' /etc/hosts" % old_ip
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)

        cmd = "sed -i '/^$/d' /etc/hosts"
        ssh.send_expect(cmd, '# ')

        #hostline = "{ip} {hostname} {hostname}.{domainname}".format(ip=new_ip, 
        hostline = "{ip} {hostname}.{domainname} {hostname}".format(ip=new_ip, 
                                                                    hostname=hostname, 
                                                                    domainname=domainname)
        cmd = "echo -e '{0}' >> /etc/hosts".format(hostline)
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)

        config = '/etc/hosts'
        self._ssh_config_pair.append({'ssh':ssh, 'config':config})
        return retcode

    def _reset_neutron_config(self, ssh, new_ip):
        neutron_config = '/etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini'
        cmd = "openstack-config --set {config} {section} {param} {value}".format(
                       config=neutron_config,
                       section='ovs',
                       param='local_ip',
                       value=new_ip)
        
        self._store_original_config(ssh, neutron_config, self._tmp_config_path)
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        self._ssh_config_pair.append({'ssh':ssh, 'config':neutron_config})
        return retcode 

    def _restart_all_hosts(self, ssh):
        cmd = "shutdown -r +{0}".format(self.CONTROL_NODE_RESTART_DELAY)
        ssh.send_expect(cmd, '#')
        cmd = "shutdown -r +{0}".format(self.COMPUTE_NODE_RESTART_DELAY)
        for pair in self._ssh_config_pair:
            conn = pair['ssh']
            if conn is ssh:
                continue
            conn.send_expect(cmd, '# ')

    def _operate_openstack_services_by_ip(self, ssh, action, service_bind_ip):
        ssh_ip = ssh.send_expect("hostname -i", '# ')
        if ssh_ip in service_bind_ip:
            # this service of polltask just runs on control node,
            # so if old_ip is included in local ips, then make sure
            # reset the ip on the control node
            if action in ['start', 'restart']:
                self._operate_rabbitmq(ssh, action)
                eventlet.sleep(2)
                self._operate_all_openstack_services(ssh, action)
                eventlet.sleep(30)
            else:
                self._operate_all_openstack_services(ssh, action)
                eventlet.sleep(30)
                self._operate_rabbitmq(ssh, action)
                eventlet.sleep(2)
            try:
                for other_ssh in self._all_sshs:
                    if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', other_ssh.host):
                        other_ssh_ip = other_ssh.host
                    else:
                        other_ssh_ip = other_ssh.send_expect("hostname -i", '# ')
                    if other_ssh_ip == ssh_ip:
                        continue
                    self._operate_all_openstack_services(other_ssh, action) 
            except Exception as e:
                self.logger.error(str(e))
        else:
            self._operate_all_openstack_services(ssh, action)

    def _restart_network(self, ssh, new_ip):
        host = new_ip
        username = ssh.username
        password = ssh.password

        try:
            cmd = "systemctl restart network"
            ssh.send_expect(cmd, '# ')
        except TimeoutException as e:
            pass
        eventlet.sleep(3)
        try:
            ssh = SSHConnection(host, username, password, 60)
        except Exception as e:
            self.logger.error(str(e))    
        return ssh

    def _stop_nfs(self, ssh, service_bind_ip):
        ssh_ip = ssh.send_expect("hostname -i", '# ')
        _all_sshs = self._all_sshs
        _all_sshs.add(ssh)

        if ssh_ip in service_bind_ip:
            for conn in _all_sshs:
                self._operate_nfs_mount_point(conn, 'umount')
            self._operate_nfs(ssh, 'stop') 
        else:
            self._operate_nfs_mount_point(ssh, 'umount')

    def _start_nfs(self, ssh, service_bind_ip):
        ssh_ip = ssh.send_expect("hostname -i", "# ")
        _all_sshs = self._all_sshs
        _all_sshs.add(ssh)

        if ssh_ip in service_bind_ip:
            self._operate_nfs(ssh, 'restart')
            for conn in _all_sshs:
                self._operate_nfs_mount_point(conn, 'mount')
        else:
            self._operate_nfs_mount_point(ssh, 'mount')

    def _operate_nfs(self, ssh, action):
        if action not in ['start', 'stop', 'restart']:
            raise Exception("Not support the action [{0}] to nfs".format(action))
        cmd = "systemctl {0} nfs.service".format(action)
        ssh.send_expect(cmd, '# ')

    def _operate_nfs_mount_point(self, ssh, action):
        def _mount_point_exists(ssh, mount_point):
            try:
                cmd = "df -h | grep --color=never {0}".format(mount_point)
                out = ssh.send_expect(cmd, '# ', timeout=60)
                if mount_point in out.split():
                    return True
                else:
                    return False
            except TimeoutException as e:
                self.logger.error(str(e))
                time.sleep(3)
                ssh.reconnect()
                return False

        if action not in ['mount', 'umount']:
            raise Exception("Not support the action [{0}] to nfs mount point!".format(action))
        mount_point = "/argos/isos"
        if action == "mount":
            try:
                cmd = "mount -a"
                ssh.send_expect(cmd, '# ', timeout=60)
            except:
                time.sleep(10)
            if not _mount_point_exists(ssh, mount_point):
                self.logger.info("Mount nfs mount point failed!") 
                #raise Exception("Mount nfs mount point failed!")
        elif action == 'umount':
            if _mount_point_exists(ssh, mount_point):
                cmd = "umount -l {0}".format(mount_point)
                ssh.send_expect(cmd, '# ', timeout=60)
                time.sleep(20)
                #if not _mount_point_exists(ssh, mount_point):
                #   self.logger.info("Umount nfs mount point failed!") 

    def _operate_rabbitmq(self, ssh, action):
        if action not in ['start', 'stop', 'restart']:
            raise Exception("Not support the action [{0}] to rabbitmq".format(action))
        cmd = "systemctl {0} rabbitmq-server.service".format(action)
        ssh.send_expect(cmd, '# ', timeout=60)

    def _operate_all_openstack_services(self, ssh, action):
        if action not in ['start', 'stop', 'restart']:
            raise Exception("Not support the action [{0}]".format(action))

        cmd = "killall dnsmasq"
        ssh.send_expect(cmd, '# ')
        
        cmd = "openstack-service list"
        services = ssh.send_expect(cmd, '# ', timeout=120)
        services = services.replace("\r\n", ' ')

        eventlet.sleep(1) 
        cmd = "openstack-service {0} {1}".format(action, services)
        retcode, out = ssh.send_expect(cmd , '# ', timeout=300, verify=True)
        return retcode 

    def _close_conn(self):
        for conn in self._all_sshs:
            if conn is not None and conn.isalive():
                conn.close()
            
    def create_bond_device(self, **kwargs):
        for key in ['host', 'user', 'password', 'bond_opts', 'nics']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)

        ip_info = kwargs.get('ip_info', None)
        if ip_info:
            ip_info = json.loads(kwargs['ip_info'])
            for key in ['IPADDR', 'NETMASK', 'GATEWAY', 'DNS']:
                if not ip_info.has_key(key):
                    if key == 'NETMASK':
                        if ip_info.has_key('PREFIX'):
                            continue
                    return "Bad request: need param [0]".format(key)

        nics = json.loads(kwargs['nics'])
        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        bond_device = kwargs.get('bond_device', '')
        bond_driver = kwargs.get('bond_driver', 'openvswitch')
        bond_opts = kwargs.get('bond_opts', '')
        ovs_opts = kwargs.get('ovs_opts', '')
        _configure_bond_device = getattr(self, "_configure_bond_device_{0}".format(bond_driver))
        if bond_driver == 'openvswitch':
            ovs_bridge = kwargs.get('ovs_bridge', '')
            if not ovs_bridge:
                return "Bad request: need param [0]".format(key) 
            bond_name = _configure_bond_device(ssh,
                                                ovs_bridge,
                                                bond_device,
                                                ovs_opts,
                                                bond_opts,
                                                *nics)

        else:
            bond_name = _configure_bond_device(ssh, bond_opts, bond_device)

        _configure_bond_slaves = getattr(self, "_configure_bond_slaves_{0}".format(bond_driver))
        _configure_bond_slaves(ssh, "add", bond_name, *nics)

        if ip_info:
            self._configure_nic_ip(ssh, 
                                   bond_name, 
                                    ip_info['IPADDR'], 
                                    ip_info.get('NETMASK', ''), 
                                    ip_info['GATEWAY'], 
                                    ip_info['DNS'],
                                    ip_info.get('PREFIX', ''))        


        ret = {'action':'add_bond_port',
                'bond': bond_name}

        return json.dumps(ret)

    def add_bond_slave(self, **kwargs):
        for key in ['host', 'user', 'password', 'bond_device', 'nics']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)

        nics = json.loads(kwargs['nics'])
        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        bond_dev = kwargs['bond_device']
        bond_driver = kwargs.get('bond_driver', 'openvswitch')
        _configure_bond_slaves = getattr(self, "_configure_bond_slaves_{0}".format(bond_driver))
        _configure_bond_slaves(ssh, "add", bond_dev, *nics)

        if bond_driver == 'kernel':
            for nic in nics:
                cmd= "ifenslave {bond_dev} {slave}".format(bond_dev=bond_dev, slave=nic)
                ssh.send_expect(cmd, '# ')
        else:
            for nic in nics:
                cmd = "ifup {0}".format(nic)
                ssh.send_expect(cmd, '# ')
            #add_interface_to_port(ssh, bond_dev, *nics)

        return 'ok'

    def remove_bond_slave(self, **kwargs):
        for key in ['host', 'user', 'password', 'bond_device', 'nics']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)

        nics = json.loads(kwargs['nics'])
        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        bond_dev = kwargs['bond_device']
        bond_driver = kwargs.get('bond_driver', 'openvswitch')
        _configure_bond_slaves = getattr(self, "_configure_bond_slaves_{0}".format(bond_driver))
        _configure_bond_slaves(ssh, "remove", bond_dev, *nics)

        if bond_driver == 'kernel':
            for nic in nics:
                cmd = "ifenslave -d {bond_dev} {slave}".format(bond_dev=kwargs['bond_device'], slave=nic)
                ssh.send_expect(cmd, '# ')
        else:
            #remove_interface_to_port(ssh, bond_dev, *nics)
            pass

        return 'ok'
 
    def add_ovs_bridge(self, **kwargs):
        for key in ['host', 'user', 'password', 'ovs_bridge']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                return "Bad request: key [0] value is null".format(key)

        ip_info = kwargs.get('ip_info', None)
        if ip_info:
            ip_info = json.loads(kwargs['ip_info'])
            for key in ['IPADDR', 'NETMASK', 'GATEWAY', 'DNS']:
                if not ip_info.has_key(key):
                    if key == 'NETMASK':
                        if ip_info.has_key('PREFIX'):
                            continue
                    return "Bad request: need param [0]".format(key)

        nics = json.loads(kwargs['nics'], None)
        if nics is not None and nics:
            port_type = kwargs.get('port_type', None)
            if port_type is None:
                return "Bad request: need param [port_type] when set bridge port"
            if  port_type not in ['normal', 'bond']:
                return "Bad request: param [port_type] just can be 'normal' or 'bond'"

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])
        ovs_bridge = kwargs.get('ovs_bridge', None) 
        if ovs_bridge:
            self._configure_ovs_bridge(ssh, ovs_bridge)
        
        bond_name = '' 
        if nics:
            _configure_ovs_port = getattr(self, "_configure_ovs_port_{0}".format(port_type))
            if port_type == 'normal':
                bond_name = _configure_ovs_port(ssh, ovs_bridge, *nics)
            else:
                bond_dev = kwargs.get('bond_dev', '')
                ovs_opts = kwargs.get('ovs_opts', '')
                bond_opts = kwargs.get('bond_opts', '')
                bond_name = _configure_ovs_port(ssh, ovs_bridge, bond_dev, ovs_opts, bond_opts, *nics)

        if ip_info:
            self._configure_nic_ip(ssh, 
                                   ovs_bridge, 
                                    ip_info['IPADDR'], 
                                    ip_info.get('NETMASK', ''), 
                                    ip_info['GATEWAY'], 
                                    ip_info['DNS'],
                                    ip_info.get('PREFIX', ''))        

        ret = {'action': 'add_ovs_bridge',
                'bridge': ovs_bridge,
                'bond': bond_name}

        return json.dumps(ret)

    def _configure_ovs_bridge(self, ssh, bridge):
        cmd = "ovs-vsctl br-exists {0}".format(bridge)
        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            cmd = "ovs-vsctl add-br {0}".format(bridge)
            ssh.send_expect(cmd, '# ')
        cmd = "echo 'DEVICE={bridge}\nBOOTPROTO=none\nONBOOT=yes\nDEVICETYPE=ovs\nTYPE=OVSBridge' \
                > /etc/sysconfig/network-scripts/ifcfg-{bridge}".format(bridge=bridge)
        ssh.send_expect(cmd, '# ')

    def _configure_ovs_port_normal(self, ssh, ovs_bridge, *net_devs):
        cmd = "ovs-vsctl list-ports {0}".format(ovs_bridge)
        out = ssh.send_expect(cmd, '# ')
        bridge_ports = out.split('\r\n')
        for net_dev in net_devs:
            #if net_dev not in bridge_ports:
            #    cmd = "ovs-vsctl add-port {bridge} {port}".format(bridge=ovs_bridge, port=net_dev)
            #    ssh.send_expect(cmd, '# ')
            #for prefix in ['NAME', 'DEVICE', 'BOOTPROTO', 'ONBOOT', 'OVS_BRIDGE', 'DEVICETYPE', 'TYPE', 'HOTPLUG']:
            #    cmd = "sed -i '/^{0}=/d' /etc/sysconfig/network-scripts/ifcfg-{1}".format(prefix, net_dev)
            #    ssh.send_expect(cmd, '# ')
            hwaddr = ''
            if os.path.isfile('/etc/sysconfig/network-scripts/ifcfg-{0}'.format(net_dev)):
                cmd = ' | '.join(["cat /etc/sysconfig/network-scripts/ifcfg-{0}".format(net_dev),
                                    "grep 'HWADDR='",
                                    "awk -F '=' '{print $2}'"])
                hwaddr = ssh.send_expect(cmd, '# ')
            if not hwaddr:
                cmd = "echo 'DEVICE={nic}\nBOOTPROTO=none\nONBOOT=yes\nHOTPLUG=no\nDEVICETYPE=ovs\nOVS_BRIDGE={bridge}\nTYPE=OVSPort' \
                    > /etc/sysconfig/network-scripts/ifcfg-{nic}".format(bridge=ovs_bridge,nic=net_dev,hw=hwaddr)
            else:
                cmd = "echo 'DEVICE={nic}\nHWADDR={hw}\nBOOTPROTO=none\nONBOOT=yes\nHOTPLUG=no\nDEVICETYPE=ovs\nOVS_BRIDGE={bridge}\nTYPE=OVSPort' \
                    > /etc/sysconfig/network-scripts/ifcfg-{nic}".format(bridge=ovs_bridge,nic=net_dev,hw=hwaddr)
            ssh.send_expect(cmd, '# ')

    def _configure_ovs_port_bond(self, ssh, ovs_bridge, bond_device, ovs_opts, bond_opts, *net_devs):
        cmd = "ovs-vsctl list-ports {0}".format(ovs_bridge)
        out = ssh.send_expect(cmd, '# ')
        bridge_ports = out.split('\r\n')
        if not bond_device or bond_device not in bridge_ports:
            #phy_ifaces = ' '.join(net_devs)
            #cmd = "ovs-vsctl add-bond {bridge} {port} {ifaces}".format(bridge=ovs_bridge, port=bond, ifaces=phy_ifaces)
            #ssh.send_expect(cmd, '# ')

            # Create ovs bond config
            #bond_dev_conf = ("DEVICE={name}\nBOOTPROTO=none\nHOTPLUG=no\n"
            #                "NM_CONTROLLED=no\nONBOOT=yes\nDELAY=0\n"
            #                "DEVICETYPE=ovs\nTYPE=OVSBond\nOVS_BRIDGE={bridge}\n")
            #bond_dev_conf = bond_dev_conf.format(name=bond, bridge=ovs_bridge)
            #if ovs_bond_opts.get('ovs_options', ''):
            #    bond_dev_conf += "OVS_OPTIONS=\"{ovs_opt}\"".format(ovs_bond_opts['ovs_options'])
            #if ovs_bond_opts.get('bond_opts', ''):
            #    bond_dev_conf += "\nBONDING_OPTS=\"{bond_opt}\"".format(bond_opt=ovs_bond_opts['bond_opts'])
            #bond_ifaces = "\"BOND_IFACES={0}\"".format(phy_ifaces)
            #bond_dev_conf += '\n' + bond_ifaces
            #cmd = "echo {ovs_bond_conf} > /etc/sysconfig/network-scripts/ifcfg-{bond}".format(ovs_bond_conf=bond_dev_conf,
            #                                                                                 bond=bond)
            #ssh.send_expect(cmd, '# ')

            #for net in net_devs:
            #    cmd = ("echo 'DEVICE={nic}\nUSERCTL=no\nBOOTPROTO=none\nONBOOT=yes' > "
            #            "/etc/sysconfig/network-scripts/ifcfg-{nic}")
            #    ssh.send_expect(cmd.format(nic=net), '# ')

            bond_name = self._configure_bond_device_openvswitch(
                                                        ssh,
                                                        ovs_bridge,
                                                        bond_device,
                                                        ovs_opts,
                                                        bond_opts,
                                                        *net_devs)


            self._configure_bond_slaves_openvswitch(ssh, 'add', bond_name, *net_devs)
            return bond_name
        else:
            self._configure_bond_slaves_openvswitch(ssh, 'add', bond_device, *net_devs)
            return bond_device
            
    def _nic_name_exist(self, ssh, nic_name):
        out = ssh.send_expect("ls -1 --color=never -d /sys/class/net/*", '# ')
        out += '\r\n'

        nic_names = re.findall(r'/sys/class/net/(.*?)\r\n', out)

        if nic_name in nic_names:
            return True
        else:
            return False 
 
    def _configure_bond_device_kernel(self, ssh, bond_opts, bond_device=''):
        out = ssh.send_expect("ls /etc/modprobe.d/*", '# ')
        if not re.search(r'/etc/modprobe.d/bonding.conf', out):
            ssh.send_expect("touch /etc/modprobe.d/bonding.conf", '# ')
        out = ssh.send_expect("cat /etc/modprobe.d/bonding.conf", '# ')
        if not re.search(r"alias bond\* bonding", out):
            ssh.send_expect("echo 'alias bond* bonding' > /etc/modprobe.d/bonding.conf", '# ')
        
        out = ssh.send_expect("ls --color=never -d /sys/class/net/*", '# ')
        bond_nums = re.findall(r'/sys/class/net/bond([0-9]+)', out)
        if len(bond_nums) != 0:
            bond_nums = [int(bond_num) for bond_num in bond_nums]
            bond_nums.sort()
            if bond_device:
                specify_bond_num = bond_device.replace('bond','')
                if specify_bond_num in bond_nums:
                    raise Exception('Bond device [{0}] has existed!!!'.format(bond_device))
                bond_new_num = specify_bond_num
            else:
                bond_new_num = bond_nums[-1] + 1
        else:
            bond_new_num = 0

        cmd = "touch /etc/sysconfig/network-scripts/ifcfg-bond{0}".format(bond_new_num)
        ssh.send_expect(cmd, '# ')
        cmd = "echo 'DEVICE=bond{num}\nONBOOT=yes\nBOOTPROTO=none\nUSERCTL=no\nBONDING_OPTS=\"{bond_opts}\"' \
                > /etc/sysconfig/network-scripts/ifcfg-bond{num}".format(num=bond_new_num, bond_opts=bond_opts)
        ssh.send_expect(cmd, '# ')

        return 'bond{0}'.format(bond_new_num)

    def _configure_bond_device_openvswitch(self, 
                                                ssh, 
                                                ovs_bridge, 
                                                bond_device, 
                                                ovs_opts, 
                                                bond_opts, 
                                                *bond_ifaces):
        if bond_device:
            if self._nic_name_exist(ssh, bond_device):
                raise Exception("Openvwtich bond device name [{0}] has existed!!!".format(bond_device))
            bond_name = bond_device
        else:
            #out = ssh.send_expect("ls --color=never -d /sys/class/net/*", '# ')
            #bond_nums = re.findall(r'/sys/class/net/bond([0-9]+)', out)
            bond_devs = get_host_nics(ssh, 'ovs_bond')
            bond_nums = []
            for dev in bond_devs:
                try:
                    num = re.match(r'bond([0-9]+)', dev).groups()[0]
                    bond_nums.append(num)
                except AttributeError:
                    pass
            if len(bond_nums) == 0:
                bond_num = 0
            else:
                bond_nums.sort()
                bond_num = int(bond_nums[-1]) + 1
            bond_name = 'bond{0}'.format(bond_num)

        conf_path = "/etc/sysconfig/network-scripts/ifcfg-{0}".format(bond_name)
        cmd = "touch {0}".format(conf_path)
        ssh.send_expect(cmd, '# ')

        bond_dev_conf = ("DEVICE={name}\nBOOTPROTO=none\nHOTPLUG=no\n"
                        "NM_CONTROLLED=no\nONBOOT=yes\nDELAY=0\n"
                        "DEVICETYPE=ovs\nTYPE=OVSBond\nOVS_BRIDGE={bridge}")
        bond_dev_conf = bond_dev_conf.format(name=bond_name, bridge=ovs_bridge)
        if ovs_opts:
            bond_dev_conf += "\nOVS_OPTIONS=\"{ovs_opt}\"".format(ovs_opt=ovs_opts)
        if bond_opts:
            bond_dev_conf += "\nBONDING_OPTS=\"{bond_opt}\"".format(bond_opt=bond_opts)
        if bond_ifaces:
            bond_dev_conf +="\nBOND_IFACES=" + '\"' + ' '.join(bond_ifaces) + '\"'

        cmd = "echo '{conf}' > {path}".format(conf=bond_dev_conf, path=conf_path)
        ssh.send_expect(cmd, '# ')

        return bond_name

    def _configure_bond_slaves_kernel(self, ssh, action, bond_name, *nics):
        """
        action: 'add', 'remove'
        """
        out = ssh.send_expect("ls --color=never -d /sys/class/net/* | awk -F '/' '{print $5}'", '# ')
        #out = out + ' '
        #NICs = re.findall(r"/sys/class/net/(.+?)[ +| *\r\n *]", out)
        NICs = out.split('\r\n')
        not_exist_nics = ''
        for nic in nics:
            if nic not in NICs:
                not_exist_nics += nic + ' '
        if not_exist_nics:
            raise Exception("NICs [{0}] did not exist!".format(not_exist_nics))
      
        if action == 'add': 
            for nic in nics:
                #cmd = "ip -f link addr show %s | grep --color=never link/ether | awk '{print $2}'" % nic
                #MAC = ssh.send_expect(cmd, '# ')
                conf_nic_info = get_nic_info(ssh, nic)
                if conf_nic_info and conf_nic_info.has_key('HWADDR'):
                    MAC = conf_nic_info['HWADDR']
                else:
                    MAC = ''
                if MAC:
                    cmd = "echo 'DEVICE={nic}\nHWADDR={mac}\nUSERCTL=no\nBOOTPROTO=none\nONBOOT=yes\nMASTER={bond}\nSLAVE=yes'\
                        > /etc/sysconfig/network-scripts/ifcfg-{nic}".format(nic=nic, mac=MAC, bond=bond_name)
                else:
                    cmd = "echo 'DEVICE={nic}\nUSERCTL=no\nBOOTPROTO=none\nONBOOT=yes\nMASTER={bond}\nSLAVE=yes'\
                        > /etc/sysconfig/network-scripts/ifcfg-{nic}".format(nic=nic, bond=bond_name)
                ssh.send_expect(cmd , '# ')
                #cmd= "ifenslave {bond_dev} {slave}".format(bond_dev=bond_name, slave=nic)
                #ssh.send_expect(cmd, '# ')
        elif action == 'remove':
            for nic in nics:
                cmd = "egrep --color=never '^(DEVICE|NAME) *= *(\")?%s(\")? *$' /etc/sysconfig/network-scripts/ifcfg-* \
                      | awk -F ':' '{print $1}'" % nic
                config_path = ssh.send_expect(cmd, '# ')
                if not config_path:
                    self.logger.info("Not find the configure of NIC [{0}].".format(nic))
                else:
                    cmd = "sed -i '/^MASTER={bond}/d' {path}".format(bond=bond_name, path=config_path)
                    ssh.send_expect(cmd, '# ')
                    cmd = "sed -i '/^SLAVE=/d' {0}".format(config_path)
                    ssh.send_expect(cmd, '# ')
                    #cmd = "ifenslave -d {bond_dev} {slave}".format(bond_dev=bond_name, slave=nic)
                    #ssh.send_expect(cmd, '# ')
                    #cmd = "sed -i 's/^DEVICE *=\(.*\)/NAME=\\1/g' {0}".format(config_path)
                    #ssh.send_expect(cmd, '# ')
        else:
            self.logger.info("Not support action [{0}] when configuring kernel bond slave.".format(action))
            return False

        return True

    def _configure_bond_slaves_openvswitch(self, ssh, action, bond_name, *nics):
        all_nics = get_host_nics(ssh, 'all')
        not_exist_nics = ''
        for nic in nics:
            if nic not in all_nics:
                not_exist_nics += nic + ' '
        if not_exist_nics:
            raise Exception("NICs [{0}] did not exist!".format(not_exist_nics))

        conf_prefix = "/etc/sysconfig/network-scripts/ifcfg-"

        #cmd = ("cat %(prefix)s%(name)s |"
        #        "grep BOND_IFACES | awk -F '=' '{print $2}'") % {'prefix':conf_prefix, 'name':bond_name}
        #out = ssh.send_expect(cmd, '# ')
        #ifaces = out.replace('"', '').split()
        ifaces = local_get_bond_slaves(ssh, bond_name)

        if action == 'add':
            ifaces.extend(nics)
            ifaces = list(set(ifaces))

            for nic in nics:
                conf_nic_info = get_nic_info(ssh, nic)
                if conf_nic_info and conf_nic_info.has_key('HWADDR'):
                    MAC = conf_nic_info['HWADDR']
                else:
                    MAC = ''
                if MAC:
                    cmd = "echo 'DEVICE={nic}\nHWADDR={mac}\nUSERCTL=no\nBOOTPROTO=none\nONBOOT=yes'\
                         > {prefix}{nic}".format(prefix=conf_prefix, nic=nic, mac=MAC)
                else:
                    cmd = "echo 'DEVICE={nic}\nUSERCTL=no\nBOOTPROTO=none\nONBOOT=yes'\
                         > {prefix}{nic}".format(prefix=conf_prefix, nic=nic)
                ssh.send_expect(cmd, '# ')
        elif action == 'remove':
            for nic in nics:
                try:
                    ifaces.remove(nic)
                except ValueError:
                    self.logger.warn('Iface [{0}] not exist in openvswitch bond device [{1}]!'.format(nic, bond_name))
        else:
            self.logger.info("Not support action [{0}] when configuring openvswitch bond ifaces.".format(action)) 
            return False

        cmd = "sed -i '/^BOND_IFACES *=/d' {prefix}{name}".format(prefix=conf_prefix, name=bond_name)
        ssh.send_expect(cmd, '# ')

        ifaces_str = "\"" + " ".join(ifaces) + "\""
        cmd = "echo 'BOND_IFACES={ifaces}' >> {prefix}{name}".format(ifaces=ifaces_str, prefix=conf_prefix, name=bond_name)
        ssh.send_expect(cmd, '# ')

        return True

    def _configure_nic_ip(self, ssh, nic, ip_addr, netmask, gateway, dns, prefix=''):
        for key in ['PREFIX', 'IPADDR', 'NETMASK', 'GATEWAY', 'DNS1']:
            cmd = "sed -i '/^{0}=/d' /etc/sysconfig/network-scripts/ifcfg-{1}".format(key, nic)
            ssh.send_expect(cmd, '# ')
        if netmask:
            cmd = "echo 'IPADDR={ip}\nNETMASK={mask}\nGATEWAY={gate}\nDNS1={dns}' \
                >> /etc/sysconfig/network-scripts/ifcfg-{nic}".format(ip=ip_addr, mask=netmask, gate=gateway, dns=dns, nic=nic)
        else:
            cmd = "echo 'IPADDR={ip}\nPREFIX={prefix}\nGATEWAY={gate}\nDNS1={dns}' \
                >> /etc/sysconfig/network-scripts/ifcfg-{nic}".format(ip=ip_addr, prefix=prefix, gate=gateway, dns=dns, nic=nic)
        ssh.send_expect(cmd, '# ')

    def _configure_openstack_ini(self, ssh, action, config_path, section='', param='', value='', option=''): 
        if action not in ['set', 'get', 'del', 'merge']:
            raise Exception('Action [{0}] is not supported!!!'.format(action))

        cmd = "openstack-config --{0}".format(action)
        if option:
            cmd += ' ' + option
        if os.path.isfile(config_path):
            cmd = cmd + ' ' + config_path
        else:
            raise Exception('Openstack configure [{0}] NOT exist!!!')
        if section:
            cmd += ' ' + section
        if param:
            cmd += ' ' + param
        if value:
            cmd += ' ' + value
        
        out = ssh.send_expect(cmd, '# ')
        return out
       
    def _configure_l3_agent_ini(self, ssh, action, section='', param='', value='', option=''): 
        config_path = '/etc/neutron/l3_agent.ini'
        return self._configure_openstack_ini(ssh, action, config_path, section, param, value, option)

    def _configure_ml2_plugin_ini(self, ssh, action, section='', param='', value='', option=''): 
        config_path = '/etc/neutron/plugins/ml2/ml2_conf.ini'
        return self._configure_openstack_ini(ssh, action, config_path, section, param, value, option)

    def _configure_openvswitch_plugin_ini(self, ssh, action, section='', param='', value='', option=''): 
        config_path = '/etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini'
        return self._configure_openstack_ini(ssh, action, config_path, section, param, value, option)

    def add_multiple_external_networks_with_one_l3_agent(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                return "Bad request: key [0] value is null".format(key)

        bridge_mappings = kwargs.get('bridge_mappings', None)
        if bridge_mappings:
            bridge_mapping_list = bridge_mappings.split(',')
            for bridge_mapping in bridge_mapping_list:
                if ':' not in bridge_mapping:
                    return "Bad request: key [bridge_mappings] format is wrong,\
                             need the format is like 'nic:bridge,nic:bridge'"
        else:
            bridge_mapping_list = []

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password']) 

        neutron_host_set = self._get_all_neutron_hosts(ssh)

        neutron_host_sshs = []
        for host in neutron_host_set:
            host_ssh = SSHConnection(host, 'root', '')
            neutron_host_sshs.append(host_ssh)

        if bridge_mapping_list:
            nics = []
            for bridge_mapping in bridge_mapping_list:
                nics.append(bridge_mapping.split(':')[0])
            ssh_nic_dict = {'SSHS': neutron_host_sshs, 'NICS': nics}
            host_map_not_exist_nics = self._result_not_exist_nics_on_host(**ssh_nic_dict)
            if host_map_not_exist_nics:
                return json.dumps({'NIC_NOT_EXIST':host_map_not_exist_nics}) 

        for host_ssh in neutron_host_sshs:
            self._enable_multiple_external_networks_with_one_l3_agent(host_ssh, *bridge_mapping_list) 

        return json.dumps({'SUCCESS': list(neutron_host_set)})

    def _get_all_nova_hosts(self, ssh):
        out = ssh.send_expect("nova-manage host list", '# ') 
        out = out.replace(' ', '')
        nova_hosts = out.split('\r\n')[1:]
        nova_host_set = set()
        for nova_host in nova_hosts:
            host = nova_host.split('\t')[0]
            if host:
                nova_host_set.add(host)

        return nova_host_set

    def _get_all_neutron_hosts(self, ssh):
        """
        Assume this service will run on the openstack controller node allways!
        So the neutron hosts will allways include local host.
        """
        nova_host_set = self._get_all_nova_hosts(ssh)

        neutron_host_set = nova_host_set

        local_host_ip = get_local_host()
        local_host_name = get_local_host('NAME')
        if (local_host_ip not in neutron_host_set and 
            local_host_name not in neutron_host_set):
            neutron_host_set.add(local_host_ip)

        return neutron_host_set

    def _not_exist_nics_on_host(self, ssh, *nics):     
        host_nics = get_host_nics(ssh, 'all')
        
        not_exist_nics = []
        for nic in nics:
            if nic not in host_nics:
                not_exist_nics.append(nic) 
        
        return not_exist_nics 

    def _result_not_exist_nics_on_host(self, **kwargs):
        """
        kwargs has two keys, one is 'NICS', the other is 'SSHS'.
        """
        nics = kwargs['NICS']
        SSHs = kwargs['SSHS']

        host_map_nics = {}
        for ssh in SSHs:
            not_exist_nics = self._not_exist_nics_on_host(ssh, *nics) 
            if not_exist_nics:
                host_map_nics[ssh.host] = not_exist_nics

        return host_map_nics

    def _enable_multiple_external_networks_with_one_l3_agent(self, ssh, *bridge_mapping_list):
        nics = ''
        for bridge_mapping in bridge_mapping_list:
            nic = bridge_mapping.splist(':')[0] + ','
        nics = nics.rstrip(',')

        self._configure_l3_agent_ini(ssh, 'del', 'DEFAULT', 'gateway_external_network_id') 
        self._configure_l3_agent_ini(ssh, 'del', 'DEFAULT', 'external_network_bridge') 

        # ML2 network setting
        # Check the flat network        
        ml2_type_drivers = self._configure_ml2_plugin_ini(ssh, 'get', 'ml2', 'type_drivers')
        if 'flat' not in ml2_type_drivers.split(','):
            ml2_type_drivers += ',flat'
            self._configure_ml2_plugin_ini(ssh, 'set', 'ml2', 'type_drivers', ml2_type_drivers)
        self._configure_ml2_plugin_ini(ssh, 'set', 'ml2_type_flat', 'flat_networks', '*')

        # Check the vlan network
        #ml2_network_types = self._configure_ml2_plugin_ini(ssh, 'get', 'ml2', 'tenant_network_types')
        #if 'vlan' not in ml2_network_types.split(','):
        #    ml2_network_types += ',vlan'
        #    self._configure_ml2_plugin_ini(ssh, 'set', 'ml2', 'tenant_network_types', ml2_network_types)
        #ml2_vlan_network = self._configure_ml2_plugins_ini(ssh, 'get', 'ml2_type_vlan', 'network_vlan_rnages')

        #for nic in nics:
        #    if nic not in ml2_vlan_network.split(','):
        #        ml2_vlan_network += ',' + nic
        #self._configure_ml2_plugin_ini(ssh, 'set', 'ml2_type_vlan', 'network_vlan_ranges', ml2_vlan_network)

        # openvswitch setting
        self._add_openvswitch_bridge_mappings(ssh, *bridge_mapping_list)

        cmd = "openstack-service restart neutron"
        ssh.send_expect(cmd, '# ')

    def _add_openvswitch_bridge_mappings(self, ssh, *bridge_mapping_list):
        #tenant_network_type = self._configure_openvswitch_plugin_ini(ssh, 'get', 'ovs', 'tenant_network_type')
        #if 'vlan' not in tenant_network_type.split(','):
        #    tenant_network_type += ',vlan'
        #    self._configure_openvswitch_plugin_ini(ssh, 'set', 'ovs', 'tenant_network_type')

        if bridge_mapping_list:
            #network_vlan_ranges = self._configure_openvswitch_plugin_ini(ssh, 'get', 'ovs', 'network_vlan_ranges')
            orig_bridge_mapping = self._configure_openvswitch_plugin_ini(ssh, 'get', 'ovs', 'bridge_mappings')

            #nets = ''
            bridge_mappings = ''
            for bridge_mapping in bridge_mapping_list:
                if bridge_mapping not in orig_bridge_mapping.split(','):
                    bridge_mappings += bridge_mapping + ','
                #net = bridge_mapping.split(':')[0]
                #if net not in network_vlan_ranges:
                #    nets += net + ','
            bridge_mappings = bridge_mappings.rstrip(',')
            #nets = nets.rstrip(',')

            #self._configure_openvswitch_plugin_ini(ssh, 'set', 'ovs', 'network_vlan_ranges', nets)

            self._configure_openvswitch_plugin_ini(ssh, 'set', 'ovs', 'bridge_mappings', bridge_mappings)

    def _add_openswitch_bridge_mapping_and_ml2_network(self, ssh, *bridge_mapping_list):
        if bridge_mapping_list:
            ml2_flat_networks = self._configure_ml2_plugin_ini(ssh, 'get', 'ml2_type_flat', 'flat_networks')
            orig_bridge_mapping = self._configure_openvswitch_plugin_ini(ssh, 'get', 'ovs', 'bridge_mappings')

            nets = ''
            bridge_mappings = ''
            for bridge_mapping in bridge_mapping_list:
                if bridge_mapping not in orig_bridge_mapping.split(','):
                    bridge_mappings += bridge_mapping + ','
                net = bridge_mapping.split(':')[0]
                if net not in ml2_flat_networks:
                    nets += net + ','
            if orig_bridge_mapping:
                bridge_mappings = bridge_mappings + orig_bridge_mapping
            else:
                bridge_mappings = bridge_mappings.rstrip(',')
            if ml2_flat_networks:
                nets = nets + ml2_flat_networks
            else:
                nets = nets.rstrip(',')

            ml2_type_drivers = self._configure_ml2_plugin_ini(ssh, 'get', 'ml2', 'type_drivers')
            if 'flat' not in ml2_type_drivers.split(','):
                ml2_type_drivers += ',flat'
                self._configure_ml2_plugin_ini(ssh, 'set', 'ml2', 'type_drivers', ml2_type_drivers)
            self._configure_ml2_plugin_ini(ssh, 'set', 'ml2_type_flat', 'flat_networks', nets)

            self._configure_openvswitch_plugin_ini(ssh, 'set', 'ovs', 'bridge_mappings', bridge_mappings)


    def set_all_neutron_hosts_openvswitch_bridge_mapping(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                return "Bad request: key [0] value is null".format(key)

        bridge_mappings = kwargs.get('bridge_mappings', None)
        if bridge_mappings:
            bridge_mapping_list = bridge_mappings.split(',')
            for bridge_mapping in bridge_mapping_list:
                if ':' not in bridge_mapping:
                    return "Bad request: key [bridge_mappings] format is wrong,\
                             need the format is like 'nic:bridge,nic:bridge'"
        else:
            bridge_mapping_list = []

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        neutron_host_set = self._get_all_neutron_hosts(ssh)

        neutron_host_sshs = []
        for host in neutron_host_set:
            host_ssh = SSHConnection(host, 'root', '')
            neutron_host_sshs.append(host_ssh)

        if bridge_mapping_list:
            nics = []
            for bridge_mapping in bridge_mapping_list:
                nics.append(bridge_mapping.split(':')[0])
            ssh_nic_dict = {'SSHS': neutron_host_sshs, 'NICS': nics}
            host_map_not_exist_nics = self._result_not_exist_nics_on_host(**ssh_nic_dict)
            if host_map_not_exist_nics:
                return json.dumps({'NIC_NOT_EXIST':host_map_not_exist_nics})

        for host_ssh in neutron_host_sshs:
            self._add_openswitch_bridge_mapping_and_ml2_network(host_ssh, *bridge_mapping_list)

        return json.dumps({'SUCCESS': list(neutron_host_set)})

    def set_neutron_host_openvswitch_bridge_mapping(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                return "Bad request: key [0] value is null".format(key)

        bridge_mappings = kwargs.get('bridge_mappings', None)
        if bridge_mappings:
            bridge_mapping_list = bridge_mappings.split(',')
            for bridge_mapping in bridge_mapping_list:
                if ':' not in bridge_mapping:
                    return "Bad request: key [bridge_mappings] format is wrong,\
                             need the format is like 'nic:bridge,nic:bridge'"
        else:
            bridge_mapping_list = []

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        if bridge_mapping_list:
            nics = []
            for bridge_mapping in bridge_mapping_list:
                nics.append(bridge_mapping.split(':')[0])
            ssh_nic_dict = {'SSHS': [ssh], 'NICS': nics}
            host_map_not_exist_nics = self._result_not_exist_nics_on_host(**ssh_nic_dict)
            if host_map_not_exist_nics:
                return json.dumps({'NIC_NOT_EXIST':host_map_not_exist_nics})

        self._add_openswitch_bridge_mapping_and_ml2_network(ssh, *bridge_mapping_list)

        return json.dumps({'SUCCESS': kwargs['host']})

    def get_all_neutron_hosts_map_free_nics(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                return "Bad request: key [0] value is null".format(key)

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        neutron_hosts = self._get_all_neutron_hosts(ssh)  

        neutron_host_map_free_nics = {}
        for host in set(neutron_hosts):
            host_ssh = SSHConnection(host, 'root', '')
            free_nics = get_host_nics(host_ssh, 'free')
            neutron_host_map_free_nics[host] = free_nics

        return json.dumps(neutron_host_map_free_nics)

    def get_all_neutron_hosts_map_ip_nics(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                return "Bad request: key [0] value is null".format(key)

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        neutron_hosts = self._get_all_neutron_hosts(ssh)

        neutron_host_map_ip_nics = {}
        for host in set(neutron_hosts):
            host_ssh = SSHConnection(host, 'root', '')
            if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d',host):
                ip = host
            else:
                ip = hostname_to_ip(host_ssh)
            nic = get_nic_name_by_ip(host_ssh, ip)
            neutron_host_map_ip_nics[host] = nic

        return json.dumps(neutron_host_map_ip_nics)

    def get_maximum_bond_device_num_on_all_neutron_hosts(self, **kwargs):
        for key in ['host', 'user', 'password']:
            if not kwargs.has_key(key):
                return "Bad request: need param [0]".format(key)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                return "Bad request: key [0] value is null".format(key)

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        neutron_hosts = self._get_all_neutron_hosts(ssh)  

        all_bond_devices = []
        for host in set(neutron_hosts):
            host_ssh = SSHConnection(host, 'root', '')
            bond_devices = get_host_nics(host_ssh, 'kernel_bond')
            all_bond_devices.extend(bond_devices)
            bond_devices = get_host_nics(host_ssh, 'ovs_bond')
            all_bond_devices.extend(bond_devices)
        all_bond_devices = set(all_bond_devices)
        if len(all_bond_devices) == 0:
            return '0'

        all_bond_nums = []
        bond_regx = re.compile(r'bond(\d+)')
        for bond_dev in all_bond_devices:
            try:
                dev_num = bond_regx.match(bond_dev).groups()[0] 
                all_bond_nums.append(int(dev_num))
            except:
                self.logger.error("Not standed bond device name [{0}].".format(bond_dev))
        if len(all_bond_nums) == 0:
            return '0'
        else:
            all_bond_nums.sort()
            return str(all_bond_nums[-1])

    def make_no_auth_login(self, **kwargs):
        pass

    def get_all_vgs(self, **kwargs):
        ret_dict = {}
        for key in ['host', 'user', 'password']:
            if not kwargs.has_key(key):
                ret_dict['status'] = 'failed'
                ret_dict['content'] = "Bad request: need param [0]".format(key)
                return json.dumps(ret_dict)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                ret_dict['status'] = 'failed'
                ret_dict['content'] = "Bad request: key [0] value is null".format(key)
                return json.dumps(ret_dict)

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        # Get the cinder volume name
        cinder_config_path = "/etc/cinder/cinder.conf"
        try:
            cinder_config = Config(cinder_config_path)
            cinder_backends = cinder_config.get_option_value('DEFAULT', 
                                                            'enabled_backends')
            backends = cinder_backends.split(',')
            if len(backends) < 1:
                raise Exception("Cannot find cinder backends in the config %s" % \
                                cinder_config_path)
            cinder_vg_names = []
            for backend in backends:
                backend = backend.strip()
                cinder_vg_name = cinder_config.get_option_value(backend, 
                                                                'volume_group') 
                if cinder_vg_name:
                    cinder_vg_names.append(cinder_vg_name.strip())
        except Exception as e:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = str(e)
            return json.dumps(ret_dict)

        # Get root volume name
        cmd = "df -h | egrep --color=never '/$' | awk '{print $1}'"
        ret = ssh.send_expect(cmd, '# ')
        if ret.endswith('root'):
            ret = ret.split('/')[-1]
            root_volume_bytes = ret.strip().replace('_', '').replace('-', '')
        else:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = "Get root volume failed on host!"
            return json.dumps(ret_dict)

        cmd = "vgs --noheadings -o vg_name"
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode == 0:
            vg_lines = ret.split('\r\n')
            vg_lines = [vg.strip() for vg in vg_lines if len(vg.split()) == 1]
        else:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = "Get volume group names failed: %s" % ret
            return json.dumps(ret_dict)

        vgs_list = []
        # if the volume group is belonged to the cinder, it will be set the tag 
        # of 'vg_tags' to 'cinder_volume', if the volume is belonged to the root
        # volume group, it will be set the tag of 'vg_tags' to 'root_volume'.
        fields = "vg_name,vg_fmt,pv_count,lv_count,vg_attr,vg_size,vg_free"
        vg_fields = fields.split(',')
        vg_fields_len = len(vg_fields)
        vg_unit = kwargs.get('vg_unit', 'g')
        cmd_prefix = "vgs --units %s --noheadings -o %s" % (vg_unit, fields)
        for vg_name in vg_lines:
            cmd = cmd_prefix + " %s" % vg_name.strip()
            retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
            if retcode == 0:
                vg_dict = {}

                if '\r\n' in ret:
                    ret_vg_lines = ret.split('\r\n')
                    for ret_vg_line in ret_vg_lines:
                        vg_values = ret_vg_line.split()
                        if (vg_name in vg_values and 
                            len(vg_values) == vg_fields_len):
                            break
                else:
                    vg_values = ret.split()

                if len(vg_values) != vg_fields_len:
                    msg = "Get the volume [%s] info failed: fields count not right!" % \
                            vg_name
                    self.logger.error(msg)
                    ret_dict['status'] = 'failed'
                    ret_dict['content'] = msg
                    return json.dumps(ret_dict)

                for i in range(vg_fields_len):
                    vg_dict[vg_fields[i]] = vg_values[i].strip()

                vg_name_bytes = vg_name.replace('_', '').replace('-', '') + 'root'
                if vg_name in cinder_vg_names:
                    vg_dict['vg_tags'] = 'cinder_volume'
                elif vg_name_bytes == root_volume_bytes:
                    vg_dict['vg_tags'] = 'root_volume'
                else:
                    vg_dict['vg_tags'] = '' 
                         
                vgs_list.append(vg_dict)
            else:
                msg = "Get the volume [%s] info failed: %s" % (vg_name, ret)
                self.logger.error(msg)
                ret_dict['status'] = 'failed'
                ret_dict['content'] = msg
                return json.dumps(ret_dict)
                
        ret_dict['status'] = 'success'
        ret_dict['content'] = json.dumps(vgs_list)
        return json.dumps(ret_dict) 

    def extend_cinder_volume(self, **kwargs):
        ret_dict = {}
        for key in ['host', 'user', 'password', 'extend_volume_size']:
            if not kwargs.has_key(key):
                ret_dict['status'] = 'failed'
                ret_dict['content'] = "Bad request: need param [0]".format(key)
                return json.dumps(ret_dict)
            if key == 'password':
                continue
            value = kwargs.get(key, None)
            if not value and value is None:
                ret_dict['status'] = 'failed'
                ret_dict['content'] = "Bad request: key [0] value is null".format(key) 
                return json.dumps(ret_dict)
            if key == 'extend_volume_size':
                extend_vg_size_str = kwargs['extend_volume_size']
                try:
                    # the default unit is Gigabyte
                    extend_vg_size = float(extend_vg_size_str)
                except:
                    extend_vg_byte_size = transfer_unit_to_byte(extend_vg_size_str[:-1], 
                                                            extend_vg_size_str[-1])
                    if extend_vg_byte_size is None:
                        ret_dict['status'] = 'failed'
                        ret_dict['content'] = ("extend_volume_size type is not right, must be"
                                                " like this: 20m or 20g or 20t")
                        return json.dumps(ret_dict)
                        
                    try:
                        extend_vg_size = extend_vg_byte_size / 1024 / 1024 / 1024
                    except Exception as e:
                        ret_dict['status'] = 'failed'
                        ret_dict['content'] = str(e) 
                        return json.dumps(ret_dict)

        ssh = SSHConnection(kwargs['host'], kwargs['user'], kwargs['password'])

        cinder_vg_name = kwargs.get('cinder_vg_name', "cinder-volumes")
        cmd = "vgs | grep --color=never %s" % cinder_vg_name
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)        
        if retcode == 0:
            cinder_vg_exists = True
        else:
            cinder_vg_exists = False

        if cinder_vg_exists:
            cmd = "vgs --units g | grep --color=never %s" % cinder_vg_name + " | awk '{print $6}'"
            cinder_vg_size = ssh.send_expect(cmd, '# ')
            cinder_vg_size = cinder_vg_size.strip('g')
        else:
            #cinder_vg_size = 0 
            ret_dict['status'] = 'failed'
            ret_dict['content'] = "Cinder volume [%s] does not exist!" % cinder_vg_name
            return json.dumps(ret_dict)

        #cmd = "hostname"
        #cinder_host_name = ssh.send_expect(cmd, '# ')
        #host_root_vg_prefix = 'vdesk'
        #cinder_host_root_vg = '_'.join([host_root_vg_prefix, cinder_host_name])
        #cmd = "vgs | grep --color=never %s" % cinder_host_root_vg
        #retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        #if retcode != 0:
        #    cinder_host_root_vg = host_root_vg_prefix
        #    cmd = "vgs | grep --color=never %s" % cinder_host_root_vg 
        #    retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        #    if retcode != 0:
        #        ret_dict['status'] = 'failed'
        #        ret_dict['content'] = "Cannot find the root LVS volume!"
        #        return json.dumps(ret_dict)
        #
        #cmd = "vgs --units g | grep --color=never %s" % cinder_host_root_vg + " | awk '{print $6}'"
        #ret = ssh.send_expect(cmd, '# ')
        #root_vg_size = ret.lower().strip('g')
        #try:
        #    if '.' in root_vg_size:
        #        root_vg_size = float(root_vg_size)
        #    else:
        #        root_vg_size = int(root_vg_size)
        #except Exception as e:
        #    ret_dict['status'] = 'failed'
        #    ret_dict['content'] = str(e)
        #    return json.dumps(ret_dict)

        #try:
        #    all_logical_parts = get_host_disk_info(ssh, 'part_logical')
        #except Exception as e:
        #    ret_dict['status'] = 'failed'
        #    ret_dict['content'] = str(e)
        #    return json.dumps(ret_dict)
        #root_vg_size = ''
        #for _, v in all_logical_parts:
        #    if v.has_key('mountpoint') and v['mountpoint'] == '/':    
        #        root_vg_size = v['size']
        #if root_vg_size:
        #    size_unit = root_vg_size[-1]
        #    root_vg_byte_size = transfer_unit_to_byte(root_vg_size[:-1], size_unit)
        #    try:
        #        root_vg_size = root_vg_byte_size / 1024 / 1024 / 1024
        #    except Exception as e:
        #        ret_dict['status'] = 'failed'
        #        ret_dict['content'] = str(e)
        #        return json.dumps(ret_dict)
        #else:
        #    ret_dict['status'] = 'failed'
        #    ret_dict['content'] = "Get host root volume size failed!"
        #    return json.dumps(ret_dict)
        cmd = "df -h | egrep --color=never '/$' | awk '{print $4}'"
        ret = ssh.send_expect(cmd, '# ')
        if ret:
            root_free_vg_byte_size = transfer_unit_to_byte(ret[:-1], ret[-1])
            try:
                root_free_vg_size = root_free_vg_byte_size / 1024 / 1024 / 1024
            except Exception as e:
                ret_dict['status'] = 'failed'
                ret_dict['content'] = str(e)
                return json.dumps(ret_dict)
        else:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = "Get host root volume size failed!"
            return json.dumps(ret_dict)

        if extend_vg_size > root_free_vg_size:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = ("Extend volume size [%s] is bigger " 
                                    "then cinder host root free volume size [%s]") % \
                                    (extend_vg_size, root_free_vg_size)
            return json.dumps(ret_dict)
        
        extend_vg_name_prefix = cinder_vg_name + '-' + 'extend-'
        cinder_vg_path = "/var/lib/cinder"
        extend_vg_regx = os.path.join(cinder_vg_path, extend_vg_name_prefix)
        cmd = "ls %s* | egrep -o --color=never '[[:digit:]]+'" % extend_vg_regx
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode == 0:
            try:
                max_num = int(ret.split('\n')[-1]) + 1
            except Exception as e:
                ret_dict['status'] = 'failed'
                ret_dict['content'] = str(e)
                return json.dumps(ret_dict)
        else:
            max_num = 0
        extend_vg_name = extend_vg_name_prefix + str(max_num)
        extend_vg_path = os.path.join(cinder_vg_path, extend_vg_name)

        cmd = "dd if=/dev/zero of=%s bs=1 count=0 seek=%dG" % (extend_vg_path, int(extend_vg_size))
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True, timeout=None)
        if retcode != 0:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = ret
            return json.dumps(ret_dict)
            
        #cmd = "ls /dev/loop* | egrep -o --color=never '[[:digit:]]+'"
        cmd = "ls --color=never -1 /dev/loop*"
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            loop_num = 0
        else:
            try:
                nums = []
                loops = [loop.strip() for loop in ret.split('\r\n')]
                for loop in loops:
                    loop_num_regx = re.match(r'/dev/loop(\d+$)', loop)
                    if loop_num_regx:
                        nums.append(loop_num_regx.groups()[0]) 
                nums = [int(i.strip()) for i in nums]
                nums.sort()
                loop_num = nums[-1] + 1
            except Exception as e:
                self.logger.error(str(e))
                ret_dict['status'] = 'failed'
                ret_dict['content'] = str(e)
                return json.dumps(ret_dict)

        loop_dev = "loop" + str(loop_num) 
        loop_path = os.path.join('/dev', loop_dev)
        cmd = "losetup %s %s" % (loop_path, extend_vg_path) 
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = ret
            return json.dumps(ret_dict)

        format_host_disk_clean(ssh, loop_dev) 
        format_host_disk_part(ssh, loop_dev, 'primary', '', 0, kwargs['extend_volume_size'])

        cmd = "pvcreate -y %s" % loop_path
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = ret
            return json.dumps(ret_dict)

        cmd = "vgextend %s %s" % (cinder_vg_name, loop_path)
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = ret
            return json.dumps(ret_dict)

        setup_vg_cmd = "losetup %s %s" % (loop_path, extend_vg_path) 
        cmd =  "echo '%s' >> /etc/rc.local" % setup_vg_cmd
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = ret
            return json.dumps(ret_dict)
        
        cmd = "systemctl restart openstack-cinder-volume"    
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            ret_dict['status'] = 'failed'
            ret_dict['content'] = ret
            return json.dumps(ret_dict)
        
        ret_dict['status'] = 'success'
        ret_dict['content'] = "You have extended cinder volume successfully!"
        return json.dumps(ret_dict)
