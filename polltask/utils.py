#-*- coding: utf-8 -*-

import os
import sys
import inspect
import subprocess
import uuid
import re
import copy

from exception import NetmaskErrorException, TimeoutException
from logger import get_default_logger

from setting import (DEFAULT_SSH_KEY_DIR, 
                        DEFAULT_SSH_KEY_NAME,
                        DEFAULT_SSH_KEY_TYPE,
                        DEFAULT_SSH_KEY_CONFIG_NAME,
                        DEFAULT_DOMAIN_NAME,
                        DEFAULT_DISK_LABEL,
                        ZFS_CONFIG)

TASK_DIR = os.path.join(os.path.dirname(__file__), 'tasks')
Logger = get_default_logger(__name__)

def import_utils(module_name, module_path=TASK_DIR):
    for dir_path, dir_names, files in os.walk(module_path):
        if '.'.join([module_name, 'py']) in files:
            if dir_path not in sys.path:
                sys.path.append(dir_path)
            return __import__(module_name)
    
    return None

def get_subclass(module, clazz):
    for subclazz_name, subclazz in inspect.getmembers(module):
        if hasattr(subclazz, '__bases__') and clazz in subclazz.__bases__:
            yield (subclazz_name, subclazz)

def kernel_module_is_loaded(ssh, module):
    cmd = "lsmod | grep --color=never {0}".format(module)
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode == 0:
        return True
    else:
        Logger.error("Kernel module [{0}] Not loaded!!!".format(module))
        return False

def execute(cmd, shell=True):
    try:
        result = None
        Logger.debug("Execute cmd [%s]..." % cmd)
        if shell:
            result = subprocess.check_output(cmd, shell=True)
        else:
            result = subprocess.check_output(cmd.split(), shell=False)
        err = None
    except subprocess.CalledProcessError as e:
        err = e
        Logger.error("Execute error: %s" % err)
    return (result, err)

def hostname_to_ip(ssh):
    """
    param: 
        ssh: the instance of SSHConnection
    """
    host = ssh.host
    if re.match(r'\d{1,3}(\.\d{1,3}){3}', host):
        ip = host
    else:
        ip_tmp = ssh.send_expect("hostname -i", '# ')
        if ip_tmp and address_can_be_linked(ip_tmp):
            ip = ip_tmp
        else:
            ip = None
            ip_list = get_all_ips(ssh)
            for ip_tmp in ip_list:
                if address_can_be_linked(ip_tmp):
                    ip = ip_tmp
                    break
    return ip

def get_all_ips(ssh, exclude_lo=True):
    regx = r'inet (\d{1,3}(\.\d{1,3}){3})\/\d+? '
    cmd = "ip addr show"
    if ssh:
        result = ssh.send_expect(cmd, '# ')
    else:
        result = execute(cmd)

    regx_ret = re.findall(regx, result)
    ip_list = []
    for ip, _ in regx_ret:
        if ip == '127.0.0.1' and exclude_lo:
            continue
        ip_list.append(ip)

    return ip_list

def address_can_be_linked(address):
    Logger.info("Verify if address can be linked!")
    cmd = "ping -c 3 -W 1 %s" % address
    _, err = execute(cmd)
    if err is not None:
        return False
    else:
        return True

def get_local_host(choice='IP'):
    """
    choice: 'IP' or 'NAME'
    """
    if choice == 'IP':
        cmd = 'hostname -i'
    else:
        cmd = 'hostname'
    out = subprocess.check_output(cmd.split())

    if choice == 'hostname':
        return out.strip('\n')
    else:
        ip_tmp = out.strip('\n').strip()
        if ip_tmp and address_can_be_linked(ip_tmp):
            ip = ip_tmp
        else:
            ip = None
            ip_list = get_all_ips(None)
            for ip_tmp in ip_list:
                if address_can_be_linked(ip_tmp):
                    ip = ip_tmp
                    break
        return ip

def get_nic_name_by_ip(ssh, ip):
    """
    param: 
        ssh: the instance of SSHConnection
    """
    nics = ssh.send_expect("ip neigh | awk '{print $3}'", '# ') 
    for nic in set(nics.split('\r\n')):
        nic_ip = ssh.send_expect("ip addr show dev %s | grep 'inet ' | awk '{print $2}'" % nic, '# ')
        nic_ip = nic_ip.split('/')[0]
        if nic_ip == ip:
            return nic
    return None

def get_domain_name(ssh, local=False):
    cmd = "cat /etc/resolv.conf | grep --color=never search | awk '{print $2}'"
    default_domainname = DEFAULT_DOMAIN_NAME
    if not local:
        result = ssh.send_expect(cmd, '# ')
    else:
        result = subprocess.check_output(cmd, shell=True)
    if result:
        if local:
            sep = '\n'
        else:
            sep = '\r\n'
        result = result.split(sep)[0]
        if "You have new mail in" in result:
            return default_domainname
        else:
            return result
    else:
        return default_domainname

def get_etc_hosts(ssh, ip):
    regx = r'%s[ ]+.*' % ip
    cmd = "cat /etc/hosts"
    if ssh:
        result = ssh.send_expect(cmd, '# ')
    else:
        result = subprocess.check_output(cmd.split())

    regx_ret = re.search(regx, result)
    if regx_ret:
        return regx_ret.group()
    else:
        return None

def add_etc_hosts(ssh, ip, short_hostname, domain, overlay=False):
    hostline = "%s %s.%s %s" % (ip, short_hostname, domain, short_hostname)
    cmd = "cat /etc/hosts"
    if ssh:
        result = ssh.send_expect(cmd, '# ')
    else:
        result = subprocess.check_output(cmd.split())

    del_cmd = "sed -i '/^ *%s .*/d' /etc/hosts" % ip
    add_cmd = "echo -e '%s' >> /etc/hosts" % hostline
    if overlay:
        if ssh:
            ssh.send_expect(del_cmd, '# ')
            ssh.send_expect(add_cmd, '# ')
        else:
            subprocess.check_output(del_cmd, shell=True)
            subprocess.check_output(add_cmd, shell=True)
        return hostline
    else:
        regx = r'%s[ ]+.*' % ip
        regx_ret = re.search(regx, result)
        if not regx_ret:
            if ssh:
                ssh.send_expect(add_cmd, '# ')
            else:
                subprocess.check_output(add_cmd, shell=True)
            return hostline
        return regx_ret.group()

def get_bond_slaves(ssh, bond_device, driver='openvswitch'):
    """driver: 'openvswitch' or 'kernel'
    """
    if driver == 'openvswitch':
        return _get_bond_slaves_openvswitch(ssh, bond_device)
    elif driver == 'kernel':
        return _get_bond_slaves_kernel(ssh, bond_device)
    else:
        return []

def _get_bond_slaves_kernel(ssh, bond_device):
    cmd = "cat /proc/net/bonding/%s | grep 'Slave Interface' | awk -F ':' '{print $2}'" % bond_device
    out = ssh.send_expect(cmd, '# ')
    if 'No such file' in out:
        return []
    slaves = out.replace(' ', '').split('\r\n')
    return slaves

def _get_bond_slaves_openvswitch(ssh, bond_device):
    slaves = []

    # if the service of openvswitch does not start,
    # then return []
    cmd = "systemctl status openvswitch"
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode != 0:
        Logger.warn("The service of openvswitch Not start on host [{0}].".format(ssh.host))
        return slaves

    cmd = ("ovs-appctl bond/list | grep -v '^bond.*type.*slaves$'"
            " | grep --color=never {0}")
    cmd = cmd.format(bond_device)
    out = ssh.send_expect(cmd, '# ')
    if out:
        slaves = out.split('\t')[-1]
        return slaves.replace(' ', '').split(',')
    return slaves

def get_ovs_ports(ssh, ovs_bridge):
    cmd = "ovs-vsctl list-ports {0}".format(ovs_bridge) 
    out = ssh.send_expect(cmd, '# ')
    if 'no bridge' in out:
        return []
    ports = out.replace(' ', '').split('\r\n')
    return ports

def get_host_nics(ssh, nic_type):
    """
    nic_type: ('all' or 
                'general' or 
                'kernel_bond' or 
                'ovs_bond' or
                'bridge' or 
                'openvswitch' or 
                'free')
    """
    cmd = "ip link show | grep --color=never mtu | awk -F ':' '{print $2}'"
    out = ssh.send_expect(cmd, '# ')
    orig_nics = out.split()
    nics = []
    for nic in orig_nics:
        nics.append(nic.replace(' ', ''))

    #cmd = "cat /etc/sysconfig/network-scripts/ifcfg-* | egrep '^DEVICE *=|^NAME *=' | awk -F '=' '{print $2}'"
    #out = ssh.send_expect(cmd, '# ')
    #orig_nics = out.split('\r\n')
    #for nic in orig_nics:
    #    if nic not in nics:
    #        nics.append(nic.replace(' ', ''))
    #if 'loopback' in nics:
    #    nics.remove('loopback')

    def build_nic_driver_map(ssh, nics):
        nic_driver_map = {}
        driver_cmd = "ethtool -i %s | grep --color=never ^driver | awk -F ':' '{print $2}'"
        for nic in nics:
            if nic == 'lo':
                continue
            cmd = driver_cmd % nic
            out = ssh.send_expect(cmd, '# ') 
            driver = out.replace(' ', '')
            nic_driver_map[nic] = driver
        return nic_driver_map

    def _get_general_nics(ssh, all_nics):
        general_nics = []
        nic_driver_map = build_nic_driver_map(ssh, all_nics)
        for nic, driver in nic_driver_map.items():
           if driver not in ['bonding', 'openvswitch', 'bridge', 'veth', 'tun']:
                general_nics.append(nic)

        return general_nics

    def _get_kernel_bond_nics(ssh, all_nics):
        bond_nics = []
        nic_driver_map = build_nic_driver_map(ssh, all_nics)
        for nic, driver in nic_driver_map.items():
           if driver == 'bonding':
                bond_nics.append(nic)
        return bond_nics

    def _get_ovs_bond_nics(ssh):
        bond_nics = []

        # if the service of openvswitch does not start,
        # then return []
        cmd = "systemctl status openvswitch"
        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            Logger.warn("The service of openvswitch Not start on host [{0}].".format(ssh.host))
            return bond_nics

        cmd = "ovs-appctl bond/list | grep -v '^bond.*type.*slaves$' | awk '{print $1}'"
        out = ssh.send_expect(cmd, '# ')
        bond_nics = out.split('\r\n')
        return bond_nics

    def _get_openvswitch_nics(ssh, all_nics):
        openvswitch_nics = []
        nic_driver_map = build_nic_driver_map(ssh, all_nics)
        for nic, driver in nic_driver_map.items():
           if driver == 'openvswitch':
                openvswitch_nics.append(nic)
        return openvswitch_nics

    def _get_bridge_nics(ssh, all_nics):
        bridge_nics = []
        nic_driver_map = build_nic_driver_map(ssh, all_nics)
        for nic, driver in nic_driver_map.items():
           if driver in 'bridge':
                bridge_nics.append(nic)
        return bridge_nics

    def _get_free_nics(ssh, all_nics):
        general_nics = _get_general_nics(ssh, all_nics)

        bond_slaves = []
        kernel_bond_nics = _get_kernel_bond_nics(ssh, all_nics)
        for bond_device in kernel_bond_nics:
            slaves = get_bond_slaves(ssh, bond_device, 'kernel') 
            bond_slaves.extend(slaves)
        openvswitch_bond_nics = _get_ovs_bond_nics(ssh)
        for bond_device in openvswitch_bond_nics:
            slaves = get_bond_slaves(ssh, bond_device)
            bond_slaves.extend(slaves)

        ovs_ports = []
        ovs_nics = _get_openvswitch_nics(ssh, all_nics)
        for ovs_nic in ovs_nics:
            ports = get_ovs_ports(ssh, ovs_nic)
            ovs_ports.extend(ports)

        all_used_nics = []
        all_used_nics.extend(bond_slaves)
        all_used_nics.extend(ovs_ports)

        free_nics = []
        for nic in general_nics:
            if nic not in all_used_nics:
                free_nics.append(nic)

        free_nics = set(free_nics)
        return list(free_nics)
 
    choosed_nics = []
    if nic_type == 'all':
        choosed_nics = nics
    elif nic_type == 'general':
        choosed_nics = _get_general_nics(ssh, nics)
    elif nic_type == 'free':
        choosed_nics = _get_free_nics(ssh, nics)
    elif nic_type == 'kernel_bond':
        choosed_nics = _get_kernel_bond_nics(ssh, nics)
    elif nic_type == 'ovs_bond':
        choosed_nics = _get_ovs_bond_nics(ssh)
    elif nic_type == 'openvswitch':
        choosed_nics = _get_openvswitch_nics(ssh, nics)
    elif nic_type == 'bridge':
        choosed_nics = _get_bridge_nics(ssh, nics)

    return choosed_nics

def get_nic_info(ssh, nic, conf=True):
    nic_param_dict = {}
    if conf:
        cmd = "egrep --color=never '^(NAME|DEVICE) *= *(\")?%s(\")? *$' /etc/sysconfig/network-scripts/ifcfg-* \
               | awk -F ':' '{print $1}'" % nic
        config_path = ssh.send_expect(cmd, '# ')
        if not config_path:
            #return ConfigNotFound(path='/etc/sysconfig/network-scripts/ifcfg-{0}'.format(nic))
            Logger.error("get_nic_info:Not find the config of nic [%s]!" % nic)
            return nic_param_dict

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
        return nic_param_dict
    else:
        Logger.warn("get_nic_info:Not support to get nic info by net tools 'ip'!")
        return nic_param_dict

def get_host_disk_info(ssh, disk_type):
    """paramer:
            disk_type: 'all', 'whole', 'part', 'part_logical'
       return:
           {'name': {'type', 'size', 'vendor', 'model', 'fstype',
                      'mountpoint'},
           }
    """
    disk_info_model = {'type': '',
                    'size': '',
                    'vendor': '',
                    'model': '',
                    'fstype': '',
                    'mountpoint': ''}
 
    def __probe_list(l, locate):
        if len(l) > locate:
            return l[locate]
        else:
            return ''

    def _get_whole_disk_info(ssh):
        top_blk_columns = "NAME,TYPE,SIZE,ROTA,VENDOR,MODEL"

        top_blk_cmd = "lsblk -nl -o %s | grep --color=never disk" % top_blk_columns
        out = ssh.send_expect(top_blk_cmd, '# ')
        top_blk_line_list = out.split('\r\n')
        top_blk_dict = {}
        for blk_line in top_blk_line_list:
            blk = blk_line.split()
            blk_name = blk[0].strip()
            if blk_name:
                blk_info_model = copy.deepcopy(disk_info_model)

                ## Get the block info to check if the disk is SSD or HDD
                #cmd = "cat /sys/block/%s/queue/rotational" % blk_name
                #retcode, out = ssh.send_expect(cmd, '# ', verify=True)
                #if retcode == 0 and out:
                #    rotational = out.strip().strip('\r').strip('\n') 
                #else:
                #    rotational = ''

                blk_info = {'type': blk[1],
                            'size': __probe_list(blk, 2),
                            'rotational': __probe_list(blk, 3),
                            'vendor': __probe_list(blk, 4),
                            'model': __probe_list(blk, 5)}
                blk_info_model.update(blk_info)
                top_blk_dict[blk_name] = blk_info_model

        return top_blk_dict

    def _get_part_disk_info(ssh):
        part_blk_columns = "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT"

        part_blk_cmd = "lsblk -nl -o %s | grep --color=never part" % part_blk_columns
        out = ssh.send_expect(part_blk_cmd, '# ')
        part_blk_line_list = out.split('\r\n')
        part_blk_dict = {}
        #name_regx = r'.*?([a-z0-9]+)'
        for blk_line in part_blk_line_list:
            blk = blk_line.split()
            #name = re.match(name_regx, blk[0]).groups()[0]
            name = blk[0]
            if name:
                part_info_model = copy.deepcopy(disk_info_model)
                part_info = {'type': blk[1],
                                        'size': blk[2],
                                        'fstype': __probe_list(blk, 3),
                                        'mountpoint': __probe_list(blk, 4)}
                part_info_model.update(part_info)
                part_blk_dict[name] = part_info_model
        return part_blk_dict

    def _get_part_logical_disk_info(ssh):
        part_logical_blk_columns = "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT"
        
        part_logical_disk_info = {}
        all_part_disk_info = _get_part_disk_info(ssh)
        for part_disk in all_part_disk_info.keys():
            part_logical_cmd = "lsblk -nl -o %s %s | grep -v '%s '" % (
                                                part_logical_blk_columns,
                                                '/dev/' + part_disk.strip(),
                                                part_disk)
            out = ssh.send_expect(part_logical_cmd, '# ')
            if not out:
                continue
            else:
                logical_head = part_disk.strip() + ':'
                part_logical_line_list = out.split('\r\n')
                for logical_line in part_logical_line_list:
                    blk = logical_line.split()
                    name = blk[0]
                    if name:
                        part_logical_info_model = copy.deepcopy(disk_info_model)
                        part_logical_info = {
                                'type': blk[1],
                                'size': blk[2],
                                'fstype': __probe_list(blk, 3),
                                'mountpoint': __probe_list(blk, 4)}
                        part_logical_info_model.update(part_logical_info)

                        fake_name = logical_head + name
                        part_logical_disk_info[fake_name] = part_logical_info_model
        return part_logical_disk_info

    def _get_all_disk_info(ssh):
        whole_disk_info = _get_whole_disk_info(ssh)
        part_disk_info = _get_part_disk_info(ssh)

        whole_disk_info.update(part_disk_info)
        return whole_disk_info

    if disk_type == 'all':
        return _get_all_disk_info(ssh)
    elif disk_type == 'whole':
        return _get_whole_disk_info(ssh)
    elif disk_type == 'part':
        return _get_part_disk_info(ssh)
    elif disk_type == 'part_logical':
        return _get_part_logical_disk_info(ssh)
    else:
        raise Exception("Not support disk type [%s]" % disk_type)

def get_host_disk_hierarchy(ssh, disk=None):
    """
    params:
        disk:    None or 'disk-identifier'.
                'disk-identifier' must be the block disk 
                identifier: 'sda' or 'sdb1' or ...
                if disk is None, this function will return
                all disk hierarchy.
       only_hard: Just show real physical partitions which type
                  is 'part' else can show some logical partitions. 
    return:
        example:
        {'sda':{'type':'disk', 
                'mountpoint': '',
                'sub-disks':{'sda1':{'type':'part', 'mountpoint':'/'},
                             'sda2':{'type':'part', 'mountpoint':'swap'},
                            }
               },
        }
    """
    def __probe_list(l, locate):
        if len(l) > locate:
            return l[locate]
        else:
            return ''

    def __format_disk_info(info):
        disk_info = {}
        disk_info['type'] = info[1]
        disk_info['mountpoint'] = __probe_list(info, 2)
        return disk_info

    def __get_disk_hierarchy(ssh, disk):
        """This will just probe only one floor.
        """
        cmd = "lsblk -nl -o NAME,TYPE,MOUNTPOINT %s" % '/dev/' + disk
        out = ssh.send_expect(cmd, '# ')
        parts = {}
        if out:
            parts['type'] = ''
            parts['mountpoint'] = ''
            parts['sub-disks'] = {}
            disk_type = ''
            for line in out.split('\r\n'):
                info = line.split()
                if info[0] == disk:
                    disk_type = info[1]
                    parts['type'] = disk_type
                    parts['mountpoint'] = __probe_list(info, 2)
                    continue
                if disk_type == 'disk':
                    if info[1] == 'part':
                        sub_disk_info = __format_disk_info(info)
                        parts['sub-disks'][info[0]] = sub_disk_info
                else:
                    sub_disk_info = __format_disk_info(info)
                    parts['sub-disks'][info[0]] = sub_disk_info

        return parts

    disk_hierarchy = {}
    all_block_disk_info = get_host_disk_info(ssh, 'all')
    all_block_disks = all_block_disk_info.keys()
    if disk is None:
        for blk in all_block_disks:
            disk_hierarchy[blk] = __get_disk_hierarchy(ssh, blk)
    else:
        if disk in all_block_disks:
            disk_hierarchy[disk] = __get_disk_hierarchy(ssh, disk)
        else:
            raise Exception("Disk [%s] is not a block device!" % disk)
    return disk_hierarchy

def get_host_disk_used_status(ssh, disk=None):
    """
    params:
        disk: None or some disk identifier
    return:
       status: 'free', 'used'
        example:
        {'sda':{'status': 'free',
                'sub-disks': {'sda1': {'type':'part', 'mountpoint':'/'},
                              'sda2': {'type':'part', 'mountpoint':'swap'},
                              }, 
                },
        }
    """
    def __disk_is_free(all_disk_hierarchy, disk):
        def __part_disk_is_free(all_disk_hierarchy, part_disk):
            part_disk_type = all_disk_hierarchy[part_disk]['type']
            part_mountpoint = all_disk_hierarchy[part_disk]['mountpoint']
            part_sub_disks = all_disk_hierarchy[part_disk]['sub-disks']

            if part_disk_type != 'part':
                raise Exception("Disk [%s] is not part disk!" % part_disk)

            is_free = True
            if disk_mountpoint:
                is_free = False
            else:
                for _, sub_disk_info in part_sub_disks.items():
                    if sub_disk_info['mountpoint']:
                        is_free = False
                        break
            
            return is_free

        disk_type = all_disk_hierarchy[disk]['type']
        disk_mountpoint = all_disk_hierarchy[disk]['mountpoint']
        sub_disks = all_disk_hierarchy[disk]['sub-disks']

        is_free = True
        if disk_mountpoint:
            is_free = False
        else:
            if disk_type == 'disk':
                for d, d_info in sub_disks.items():
                    if d_info['type'] == 'part':
                        is_free = __part_disk_is_free(all_disk_hierarchy, d)
                        if not is_free:
                            break
            else:
                is_free = __part_disk_is_free(all_disk_hierarchy, disk)
        return is_free
   
    def __disk_status(all_disk_hierarchy, d):
        sub_status = {}
        sub_status['status'] = ''
        sub_status['sub-disks'] = {}

        d_is_free = __disk_is_free(all_disk_hierarchy, d)
        if d_is_free:
            sub_status['status'] = 'free'
        else:
            sub_status['status'] = 'used'
        sub_status['sub-disks'] = all_disk_hierarchy[d]['sub-disks']

        return sub_status

    disk_status = {}
    all_disk_hierarchy = get_host_disk_hierarchy(ssh)
    
    disks = all_disk_hierarchy.keys()
    if disk is None:
        for d in disks:
            sub_status = __disk_status(all_disk_hierarchy, d)
            disk_status[d] = sub_status
    else:
        if disk in disks:
            sub_status = __disk_status(all_disk_hierarchy, disk)
            disk_status[disk] = sub_status
        else:
            raise Exception("Disk [%s] is not a block device!" % disk)

    return disk_status

def get_host_disks(ssh, disk_type, only_whole_disk=False):
    """
    disk_type: 'all', 'free'
    """
    ## 获取主机上所有的分区
    #cmd = "cat /proc/partitions | grep --color=never -v 'major minor' | awk '{print $4}'"
    #out = ssh.send_expect(cmd, '# ')
    #all_disks = out.split('\r\n')
    #if '' in all_disks:
    #    all_disks.remove('')
    #if ' ' in all_disks:
    #    all_disks.remove(' ')

    ## 去掉映射磁盘和loop设备，以及只读scsi设备
    #tmp_all_disks = copy.copy(all_disks)
    #for disk in tmp_all_disks:
    #    if disk.startswith('dm'):
    #        all_disks.remove(disk)
    #    if disk.startswith('loop'):
    #        all_disks.remove(disk)
    #    if disk.startswith('sr'):
    #        all_disks.remove(disk)
    #del tmp_all_disks

    ## 去掉已经有分区的硬盘名 
    #if not out.endswith('\r\n'):
    #    out = out + '\r\n'
    #top_disks = re.findall(r'([a-z]+)\r\n', out)
    #for disk in top_disks:
    #    regx = r'({0}[0-9]+)\r\n'.format(disk)
    #    if re.search(regx, out):
    #        all_disks.remove(disk)

    whole_disk_info = get_host_disk_info(ssh, 'whole')
    all_disk_info = get_host_disk_info(ssh, 'all')

    if only_whole_disk:
        type_disk_info = whole_disk_info
    else:
        type_disk_info = copy.deepcopy(all_disk_info)
        whole_disks = whole_disk_info.keys()
        all_disk_hierarchy = get_host_disk_hierarchy(ssh)
        for d in whole_disks:
            if all_disk_hierarchy[d]['sub-disks']:
                type_disk_info.pop(d, None)

    def _get_host_all_disks(type_disk_info):
        return type_disk_info

    def _get_host_free_disks(ssh, type_disk_info):
        #cmd = "pvscan | grep --color=never PV |  awk '{print $2}'"
        #out = ssh.send_expect(cmd, '# ')
        #pv_disks = out.split('\r\n')

        #cmd = "df -T | egrep ^/dev | awk '{print $1}'"
        #out = ssh.send_expect(cmd, '# ')
        #sys_used_disks = out.split('\r\n')

        #all_used_disks = copy.copy(sys_used_disks)
        #all_used_disks.extend(pv_disks)
        #for num in range(len(all_used_disks)):
        #    if all_used_disks[num].startswith('/dev/'):
        #        all_used_disks[num] = all_used_disks[num].replace('/dev/', '')

        #all_free_disks = copy.copy(all_disks)
        #for disk in all_used_disks:
        #    if disk in all_free_disks:
        #        all_free_disks.remove(disk)

        ## Remove system boot disk
        #for disk in all_free_disks:
        #    cmd = "fdisk -l | grep --color=never /dev/%s" % disk
        #    ret = ssh.send_expect(cmd, '# ')
        #    dev_line_list = ret.split('\r\n')
        #    for dev_line in dev_line_list:
        #        if dev_line.startswith('/dev/%s' % disk):
        #            dev_line_str = dev_line.replace(' ', '')
        #            boot_dev_str = "/dev/%s*" % disk
        #            if dev_line_str.startswith(boot_dev_str):
        #                all_free_disks.remove(disk)

        #all_free_disks = _remove_zfs_used_disks(ssh, all_free_disks)

        #all_mounted_part_disks = []
        #all_part_disk_info = get_host_disk_info(ssh, 'part')
        #for part_disk, disk_info in all_part_disk_info.items():
        #    if disk_info['mountpoint']:
        #        all_mounted_part_disks.append(part_disk)
        #all_part_logical_info = get_host_disk_info(ssh, 'part_logical')
        #for part_logical, logical_info in all_part_logical_info.items():
        #    if logical_info['mountpoint']:
        #        part_disk = part_logical.split(':')[0]
        #        if part_disk not in all_mounted_part_disks:
        #            all_mounted_part_disks.append(part_disk)

        #for disk in all_mounted_part_disks:
        #    if disk in all_disks:
        #        all_disks.remove(disk)

        #all_free_disks = _remove_zfs_used_disks(ssh, all_disks)

        #return all_free_disks

        all_disk_used_status = get_host_disk_used_status(ssh)

        tmp_free_disk_info = copy.deepcopy(type_disk_info)
        for disk in type_disk_info.keys():
            if all_disk_used_status[disk]['status'] == 'used':
                tmp_free_disk_info.pop(disk)

        free_disks = tmp_free_disk_info.keys()
        free_disks = _remove_zfs_used_disks(ssh, free_disks)

        free_disk_info = {}
        for d in free_disks:
            free_disk_info[d] = type_disk_info[d]
        return free_disk_info

    def _zfs_module_is_here(ssh):
        cmd = "lsmod | grep zfs"
        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode == 0:
            return True
        else:
            return False

    def _get_zfs_disks(ssh):
        if not _zfs_module_is_here(ssh):
            return []

        cmd = "zpool status | grep ONLINE | grep -v state | awk '{print $1}'"
        out = ssh.send_expect(cmd, '# ')
        if 'no pools available' in out:
            zfs_used_disks = []
        else:
            zfs_used_disks = out.split('\r\n')

        return zfs_used_disks

    def _remove_zfs_used_disks(ssh, all_free_disks):
        if not _zfs_module_is_here(ssh):
            return all_free_disks

        zfs_used_disks = _get_zfs_disks(ssh)

        for disk in zfs_used_disks:
            if disk in all_free_disks:
                all_free_disks.remove(disk)
            if re.match(r'^[a-zA-Z]+[0-9]+$', disk):
                disk_head = re.match(r'^([a-zA-Z]+)[0-9]+$', disk).groups()[0]
                if disk_head in all_free_disks:
                    all_free_disks.remove(disk_head)
            if re.match(r'^[a-zA-Z]+$', disk):
                tmp_free_disks = copy.deepcopy(all_free_disks)
                for f_d in tmp_free_disks:
                    if re.match(r'%s[0-9]+$' % disk, f_d):
                        all_free_disks.remove(f_d)

        #uuid_name = str(uuid.uuid1())

        # 去掉不存在的设备
        #def _get_not_exist_disks(ssh, pool_name, all_free_disks):
        #    free_disks = ' '.join(all_free_disks)
        #    cmd = "zpool create -f {name} {free}".format(name=pool_name, free=free_disks)
        #    out = ssh.send_expect(cmd, '# ')
        #    not_exist_regx = r"cannot open '(.+?)': no such device in /dev\r\n"
        #    not_exist_disks = re.findall(not_exist_regx, out)

        #    return not_exist_disks, out

        #not_exist_disks, out = _get_not_exist_disks(ssh, uuid_name, all_free_disks)
        #while not_exist_disks:
        #    for disk in not_exist_disks:
        #        if disk in all_free_disks:
        #            all_free_disks.remove(disk)

        #    not_exist_disks, out = _get_not_exist_disks(ssh, uuid_name, all_free_disks)

        # 去掉已经被用的设备
        #if not out:
        #    cmd = "zpool list | grep -v --color=never NAME | awk '{print $1}'"
        #    out = ssh.send_expect(cmd, '# ')
        #    zfs_pools = out.split('\r\n')
        #    if uuid_name in zfs_pools:
        #        cmd = "zpool destroy {name}".format(name=uuid_name)
        #        ssh.send_expect(cmd, '# ')
        #else:
        #    not_free_regx = r"cannot open '/dev/(.+?)': .*\r\n"
        #    not_free_disks = re.findall(not_free_regx, out)
        #    for disk in not_free_disks:
        #        all_free_disks.remove(disk)

        return all_free_disks

    if disk_type == 'all':
        return _get_host_all_disks(type_disk_info)
    elif disk_type == 'free':
        return _get_host_free_disks(ssh, type_disk_info)
    else:
        Logger.error("Not support the disk type [{0}] when getting host disks!".format(disk_type))
        return {}

def format_host_disk_clean(ssh, disk, disk_label=DEFAULT_DISK_LABEL):
    cmd = "parted -s /dev/%s mklabel %s" % (disk, disk_label)
    retcode, out = ssh.send_expect(cmd, '# ', verify=True) 
    if retcode == 0:
        return (retcode, out)
    else:
        Logger.error("Format host disk [%s] to clean failed!" % disk)
        return (retcode, out)

def format_host_disk_part(ssh, disk, part_type, fs_type, start, end):
    """
    Make a part-type partition for filesystem fs-type (if specified), 
    beginning at start and ending at end  (by  default  in  megabytes).
    part-type should be one of "primary", "logical", or "extended".
    params:
        disk: host disk identifier, examples: 'sda', 'sdb', ...
        part_type: 'primary', 'logical' or 'extended'
        fs_type: part disk filesystem, examples: 'ext3', 'ext4', 'xfs', ...
        start: part disk start location, default unit is megabytes, 
               examples: 0, 1G, 5G, ...
        end: same to the start.
    """
    cmd = "parted -s /dev/{d} mkpart {p_type} {fs_type} {s} {e}".format(
            d=disk, p_type=part_type, fs_type=fs_type, s=start, e=end)
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode == 0:
        return (retcode, out)
    else:
        Logger.error("Format host disk [%s] to new part failed!" % disk)
        return (retcode, out)

def mkfs_disk_part(ssh, disk_part, fs_type, force_mkfs=True):
    mkfs_cmd = '.'.join(['mkfs', fs_type])
    if force_mkfs:
        cmd = '%s -f /dev/%s' % (mkfs_cmd, disk_part)
    else:
        cmd = "%s /dev/%s" % (mkfs_cmd, disk_part)
    retcode, out = ssh.send_expect(cmd, '# ', verify=True, timeout=None)
    if retcode == 0:
        return (retcode, out)
    else:
        Logger.error("Make host disk [%s] to new filesystem failed!" % disk_part)
        return (retcode, out)

def get_zfs_pool_status(ssh, pool_name, unit_is_byte=True):
    pool_status = {}
    cmd = ("zpool list -H |"
            "grep --color=never %s |"
            "awk '{print $1,$2,$4,$9}'") % pool_name
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode == 0:
        status = out.split()
        if unit_is_byte:
            total_size = transfer_unit_to_byte(status[1][:-1], status[1][-1])
            free_size = transfer_unit_to_byte(status[2][:-1], status[2][-1])
        else:
            total_size = status[1]
            free_size = status[2]
        pool_status = {'name': status[0],
                        'size': total_size,
                        'free': free_size,
                        'health': status[3]}
    else:
        pool_status = None

    return pool_status

def get_path_size(ssh, f_path, unit='1'):
    """unit: '1' or 'k' or 'm' or 'g' or 't' ...
    """
    cmd = "du -B%s -s %s" % (unit, f_path)
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode == 0:
        return out.split()[0]
    else:
        Logger.error(out)
        return None

def transfer_unit_to_byte(num, unit):
    try:
        num = float(num)
    except Exception as e:
        Logger.error(e)
        return None

    unit = unit.lower()
    if unit in ['k','kb']:
        return num * 1024
    elif unit in ['m', 'mb']:
        return num * 1024 * 1024
    elif unit in ['g', 'gb']:
        return num * 1024 * 1024 * 1024
    elif unit in ['t', 'tb']:
        return num * 1024 * 1024 * 1024 * 1024
    elif unit in ['p', 'pb']:
        return num * 1024 * 1024 * 1024 * 1024 * 1024
    elif unit in ['e', 'eb']:
        return num * 1024 * 1024 * 1024 * 1024 * 1024 * 1024
    else:
        Logger.error("Not support storage unit [%s]!" % unit)
        return None

def reset_zfs_mem_cache(ssh, arc_max, no_cache_flush=True, now_effect=True):
    """arc_max: if arc_max is the int type or a string can be transfered to 
                be int type, then it will be get a default storage unit 'GB'.
    """
    try:
        arc_max_value = int(arc_max)
        arc_max_unit = 'g'
    except ValueError:
        arc_max_value = arc_max[:-1]
        arc_max_unit = arc_max[-1]
    zfs_arc_max = transfer_unit_to_byte(arc_max_value, arc_max_unit)

    cmd = "echo 'options zfs zfs_arc_max=%d' > %s" % (zfs_arc_max, ZFS_CONFIG)
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode != 0:
        return retcode, out
    if no_cache_flush:
        cmd = "echo 'options zfs zfs_nocacheflush=1' >> %s" % ZFS_CONFIG
        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            return retcode, out
    if now_effect:
        cmd = "echo %d > /sys/module/zfs/parameters/zfs_arc_max" % zfs_arc_max
        retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        if retcode != 0:
            return retcode, out

        if no_cache_flush:
            cmd = "echo 1 > /sys/module/zfs/parameters/zfs_nocacheflush"
            retcode, out = ssh.send_expect(cmd, '# ', verify=True)
            if retcode != 0:
                return retcode, out
    return (0, '')

def get_host_memory_status(ssh, unit=None):
    """unit: None or 'byte' or 'kilo' or 'mega' 
             or 'giga' or 'human'
    """
    mem_status = {}
    if unit is None:
        cmd = "free --kilo | grep -i --color=never mem"
    else:
        if unit in ['byte', 'kilo', 'mega', 'giga', 'human']:
            cmd = "free --%s | grep -i --color=never Mem"
        else:
            raise Exception("Not support memory unit!")
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode == 0:
        mem_line = out.split(':')[1].strip().strip('\n').strip('\r')
        mem_line_list = mem_line.split()
        mem_status['total'] = mem_line_list[0]
        mem_status['used'] = mem_line_list[1]
        mem_status['free'] = mem_line_list[2]
        mem_status['shared'] = mem_line_list[3]
        mem_status['buffers'] = mem_line_list[4]
        mem_status['cached'] = mem_line_list[5]

    return mem_status

def probe_list(l, locate):
    if len(l) > locate:
        return l[locate]
    else:
        return ''

def translate_cidr_prefix_to_netmask(self, prefix):
    number_map_mask = {0:'0', 
                        1:'128', 
                        2:'192', 
                        3:'224',
                        4:'240', 
                        5:'248', 
                        6:'252', 
                        7:'254', 
                        8:'255'}
    try:
        prefix = int(prefix)
    except Exception as e:
        raise e

    if prefix < 0 or prefix > 32:
        msg = "Netmask prefix must be less or equal than 32 and be equal or greater than 0"
        raise Exception(msg)

    netmask_list = []
    mask_num = prefix / 8
    remainder = prefix % 8

    for i in range(0, mask_num):
        netmask_list.append('255')
    netmask_list.append(number_map_Mask[remainder])
    for i in range(mask_num + 1, 4):
        netmask_list.append('0')

    return '.'.join(netmask_list)

def translate_netmask_to_cidr_prefix(self, netmask):
    mask_map_number = {'0': 0, 
                        '128': 1, 
                        '192': 2, 
                        '224': 3,
                        '240': 4, 
                        '248': 5, 
                        '252': 6, 
                        '254': 7, 
                        '255': 8}

    prefix = 0
    mask_list = netmask.split('.')
    for mask in mask_list:
        number = mask_map_number.get(mask, None)
        if number is None:
            raise NetmaskErrorException(netmask=netmask)
        prefix += number

    return prefix

def compute_network_address(self, ip_addr, subnet_mask):
    ip_addr_list = ip_addr.split('.')
    subnet_mask_list = subnet_mask.split('.')

    network_addr = []
    for num in range(len(ip_addr_list)):
        sub_id = str(int(ip_addr_list[num]) & int(subnet_mask_list[num]))
        network_addr.append(sub_id)

    return '.'.join(network_addr)

def generate_uuid_str(prefix=''):
    uuid_str = str(uuid.uuid1())
    uuid_str = uuid_str.replace('-', '_')
    if prefix:
        ret = prefix + uuid_str
    else:
        ret = uuid_str

    return ret

def generate_ssh_key(ssh, key_name='', key_dir='', key_type='', regen=False, key_phrase=''):
    if not key_name:
        key_name = DEFAULT_SSH_KEY_NAME 
    if not key_dir:
        key_dir = DEFAULT_SSH_KEY_DIR
    if not key_type:
        key_type = DEFAULT_SSH_KEY_TYPE

    ssh_key_config_path = os.path.join(key_dir, DEFAULT_SSH_KEY_CONFIG_NAME)
    key_path = os.path.join(key_dir, key_name) 
    if key_phrase:
        if len(key_phrase) < 5:
            Logger.error("SSH key phrase need > 4, now the length of phrase [{0}] <= 4.".format(key_phrase))
    else:
        key_phrase = "''"

    cmd = "mkdir -p {0}".format(key_dir)
    ssh.send_expect(cmd, '# ') 

    cmd = "touch {0}".format(ssh_key_config_path)
    ssh.send_expect(cmd, '# ')

    cmd = "ls {key_dir} | egrep --color=never {key_name}$".format(key_dir=key_dir,
                                                                 key_name=key_name)
    retcode_private, out = ssh.send_expect(cmd, '# ', verify=True)
    cmd = "ls {key_dir} | egrep --color=never {key_name}.pub$".format(key_dir=key_dir,
                                                                        key_name=key_name)
    retcode_pub, out = ssh.send_expect(cmd, '# ', verify=True)

    delete_cmd = "rm -rf {key} {key}.pub".format(key=key_path)
    if retcode_private !=0 and retcode_pub != 0:
        pass
    elif retcode_private !=0 or retcode_pub != 0:
        ssh.send_expect(delete_cmd, '# ')
    else:
        if regen:
            ssh.send_expect(delete_cmd, '# ')
        else:
            return key_path

    cmd = "ssh-keygen -t {key_type} -f {path} -P {phrase}".format(key_type=key_type ,path=key_path, phrase=key_phrase)
    retcode, out = ssh.send_expect(cmd, '# ', verify=True)
    if retcode != 0:
        Logger.error(out)
        return None
    else:
        add_ssh_identity_file(ssh)
        return key_path

def add_ssh_identity_file(ssh, key_name='', key_dir=''):
    if not key_dir:
        key_dir = DEFAULT_SSH_KEY_DIR

    ssh_key_config_path = os.path.join(key_dir, DEFAULT_SSH_KEY_CONFIG_NAME)
    cmd = "touch {0}".format(ssh_key_config_path)
    ssh.send_expect(cmd, '# ')
  
    key_files = []
    if not key_name:
        cmd = "ls -1 --color=never {0}".format(key_dir) 
        out = ssh.send_expect(cmd, '# ')
        key_file_names = out.split('\r\n')
        for name in key_file_names:
            if re.match(r".+\.pub$", name):
                continue
            if name in ['config', 'authorized_keys', 'known_hosts', 'known_hosts.old']:
                continue
            key_path = os.path.join(key_dir, name)
            cmd = "cat {0} | grep --color=never 'PRIVATE KEY'".format(key_path)
            retcode, out = ssh.send_expect(cmd, '# ', verify=True)
            if retcode == 0:
                key_files.append(key_path)
    else:
        key_path = os.path.join(key_dir, key_name)
        key_files = [key_path]

    cmd = 'cat {0}'.format(ssh_key_config_path)
    all_identity_files = ssh.send_expect(cmd, '# ')
    for key_file in key_files:
        key_file_regx = r'IdentityFile +' + key_file.replace('.', '\.')
        identity_file_list = re.findall(key_file_regx, all_identity_files)
        if not identity_file_list:
            cmd = "echo 'IdentityFile {key_file}' >> {conf}".format(key_file=key_file,
                                                                conf=ssh_key_config_path)
            ssh.send_expect(cmd, '# ')

def copy_ssh_key_to(ssh, remote_addr, remote_user, remote_pass, key_file=''):
    if not key_file:
        key_file = os.path.join(DEFAULT_SSH_KEY_DIR, DEFAULT_SSH_KEY_NAME)

    try:
        cmd = "ssh-copy-id -o StrictHostKeyChecking=no -i {key_file} {user}@{addr}".format(key_file=key_file,
                                                                user=remote_user,
                                                                addr=remote_addr)

        ssh.send_expect(cmd, 'password: *', 60)
        retcode, out = ssh.send_expect(remote_pass, '# ', 90, True)
        if "Permission denied, please try again" in out:
            Logger.error("Copy ssh key to remote host failed: {0}".format(out))
            ssh.send_expect("^c", '# ')
        else:
            if retcode == 0:
                return True
    except TimeoutException as e:
        if "All keys were skipped because they already exist on the remote system" in e.message:
            return True
        else:
            return False

    return False   

def reset_user_home(ssh, user, home_dir):
    cmd = "usermod -d %s %s" % (home_dir, user)
    retcode, ret = ssh.send_expect(cmd, '# ', verify=True)
    return (retcode, ret)

def command_exists(ssh, command):
    cmd = "command -v %s" % command
    if ssh is None:
        try:
            ret = subprocess.check_output(cmd.split())
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        retcode, ret = ssh.send_expect(cmd, '# ', verify=True) 
        if retcode == 0:
            return True
        else:
            return False

def rebase_image(ssh, baking_file, image, backend='qemu'):
    if backend == 'qemu':
        if command_exists(ssh, 'qemu-img'):
            pass
        else:
            raise Exception("Not support rebasing image with [qemu] backend!") 
    else:
        raise Exception("Not support rebasing image with [%s] backend!" % backend)

    cmd = "qemu-img rebase -b %s %s" % (baking_file, image)
    retcode, ret = ssh.send_expect(cmd, '# ', verify=True, timeout=None)
    return retcode, ret

if __name__ == "__main__":
    from ssh_connection import SSHConnection
    ssh = SSHConnection('192.168.10.16', 'root', '111111')
    import pdb
    pdb.set_trace()
    domainname = get_domain_name(ssh)
    ovs_bonds = get_bond_slaves(ssh, 'bond0') 
    print "OVS bond slaves: ", ovs_bonds
    host_bond_nics = get_host_nics(ssh, 'ovs_bond')
    print "OVS bonds: ", host_bond_nics
    host_free_nics = get_host_nics(ssh, 'free')
    print "OVS free nics: ", host_free_nics
    if kernel_module_is_loaded(ssh, 'zfs'):
        print "yes"
    else:
        print "no"
    free_disks = get_host_disks(ssh, 'free')
    print "Free Disks: ", free_disks
    key_path = generate_ssh_key(ssh, key_name='test', key_dir='', key_type='', regen=True, key_phrase='')
    if key_path is not None:
        success = copy_ssh_key_to(ssh, '192.168.8.103', 'root', '111111', '%s.pub' % key_path)
        if success:
            Logger.info("Copy ssh key successfully!")
