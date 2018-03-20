# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Openstack, LLC
# Copyright 2012 Nebula, Inc.
# Copyright (c) 2012 X.commerce, a business unit of eBay Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import absolute_import

import logging
import Session
import Logger
import Setting
import backend
import base

#import sys
#reload(sys)
#sys.setdefaultencoding("utf-8")
#sys.setdefaultencoding("gbk")


# Add by wangderan start
__all__ = ['timeout']

import ctypes
import functools
import threading
import consoleInfo
import socket
import base64

def _async_raise(tid, exception):
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exception))
    if ret == 0:
        raise ValueError('Invalid thread id')
    elif ret != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), 0)
        raise SystemError('PyThreadState_SetAsyncExc failed')


class ThreadTimeout(Exception):
    """ Thread Timeout Exception """
    pass
"""
class WorkThread(threading.Thread):
    def __init__(self, target, args, kwargs):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
        else:
            self.exception = None

    def get_tid(self):
        if self.ident is None:
            raise threading.ThreadError('The thread is not active')
        return self.ident

    def raise_exc(self, exception):
        _async_raise(self.get_tid(), exception)

    def terminate(self):
        self.raise_exc(SystemExit)
"""

class WorkThread(threading.Thread):
    """ WorkThread """

    def __init__(self, target, args, kwargs):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
        else:
            self.exception = None

    def get_tid(self):
        if self.ident is None:
            raise threading.ThreadError('The thread is not active')
        return self.ident

    def raise_exc(self, exception):
        _async_raise(self.get_tid(), exception)

    def terminate(self):
        self.raise_exc(SystemExit)
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
        else:
            self.exception = None

    def get_tid(self):
        if self.ident is None:
            raise threading.ThreadError('The thread is not active')
        return self.ident

    def raise_exc(self, exception):
        _async_raise(self.get_tid(), exception)

    def terminate(self):
        self.raise_exc(SystemExit)

__all__ = ['timeout']

import ctypes
import functools
import threading


def _async_raise(tid, exception):
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exception))
    if ret == 0:
        raise ValueError('Invalid thread id')
    elif ret != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), 0)
        raise SystemError('PyThreadState_SetAsyncExc failed')


class ThreadTimeout(Exception):
    """ Thread Timeout Exception """
    pass


class WorkThread(threading.Thread):
    """ WorkThread """

    def __init__(self, target, args, kwargs):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
        else:
            self.exception = None

    def get_tid(self):
        if self.ident is None:
            raise threading.ThreadError('The thread is not active')
        return self.ident

    def raise_exc(self, exception):
        return self.ident

    def raise_exc(self, exception):
        _async_raise(self.get_tid(), exception)

    def terminate(self):
        self.raise_exc(SystemExit)

def timeout(timeout):
    """ timeout decorator """
    def proxy(method):
        @functools.wraps(method)
        def func(*args, **kwargs):
            worker = WorkThread(method, args, kwargs)
            worker.join(timeout=timeout)
            if worker.is_alive():
                worker.terminate()
                raise ThreadTimeout('A call to %s() has timed out' % method.__name__)
            elif worker.exception is not None:
                raise worker.exception
            else:
                return worker.result
        return func
    return proxy
# Add by wangderan end

from glanceclient import client as glance_client
from novaclient.v1_1 import client as nova_client
from novaclient.v1_1.contrib.list_extensions import ListExtManager  # noqa
from novaclient.v1_1 import security_group_rules as nova_rules
from novaclient.v1_1.security_groups import SecurityGroup as NovaSecurityGroup  # noqa
from novaclient.v1_1.servers import REBOOT_HARD  # noqa
from novaclient.v1_1.servers import REBOOT_SOFT  # noqa

import base
import user

LOG = logging.getLogger(__name__)

#  glanceclient API
def glanceclient(User, version='1'):
    url = base.url_for(User, 'image')
    insecure = False
    LOG.debug('glanceclient connection created using token "%s" and url "%s"'
              % (User.token.id, url))
    return glance_client.Client(version, url, token=User.token.id, insecure=insecure, cacert=None)

def data(User, image, do_checksum=True):
    return glanceclient(User).images.data(image, do_checksum)

def download_templet(body):
    filename = base64.decodestring(Setting.getFilename())
    with open(filename, 'wb') as image:
        try:
            for info in body:
                image.write(info)
            image.flush()
            return filename
        except Exception:
            pass

def image_list(request, marker=None, sort_dir='desc',
                        sort_key='created_at', filters=None, paginate=False):
    page_size = 20
    kwargs = {'filters': filters or {}}
    if marker:
        kwargs['marker'] = marker
    kwargs['sort_dir'] = sort_dir
    kwargs['sort_key'] = sort_key

    images_iter = glanceclient(request).images.list(page_size=page_size,
                                                    **kwargs)
    images = list(images_iter)
    return images

# API static values
INSTANCE_ACTIVE_STATE = 'ACTIVE'
VOLUME_STATE_AVAILABLE = "available"

class VNCConsole(base.APIDictWrapper):
    """Wrapper for the "console" dictionary returned by the
    havclient.servers.get_vnc_console method.
    """
    _attrs = ['url', 'type']


class SPICEConsole(base.APIDictWrapper):
    """Wrapper for the "console" dictionary returned by the
    havclient.servers.get_spice_console method.
    """
    _attrs = ['url', 'type']


class Server(base.APIResourceWrapper):
    """Simple wrapper around havclient.server.Server

       Preserves the request info so image name can later be retrieved

    """
    _attrs = ['addresses', 'attrs', 'id', 'image', 'links', 'vcpus', 'rams',
             'metadata', 'name', 'private_ip', 'public_ip', 'status', 'uuid',
             'image_name', 'VirtualInterfaces', 'flavor', 'key_name',
             'tenant_id', 'user_id', 'OS-EXT-STS:power_state',
             'OS-EXT-STS:task_state', 'OS-EXT-SRV-ATTR:instance_name',
             'OS-EXT-SRV-ATTR:host', 'created']

    def __init__(self, apiresource, request):
        super(Server, self).__init__(apiresource)
        self.request = request


    @property
    def internal_name(self):
        return getattr(self, 'OS-EXT-SRV-ATTR:instance_name', "")

class Hypervisor(base.APIDictWrapper):
    """Simple wrapper around novaclient.hypervisors.Hypervisor."""

    _attrs = ['manager', '_loaded', '_info', 'hypervisor_hostname', 'id',
              'servers']

    @property
    def servers(self):
        # if hypervisor doesn't have servers, the attribute is not present
        servers = []
        try:
            servers = self._apidict.servers
        except Exception:
            pass

        return servers


class NovaUsage(base.APIResourceWrapper):
    """Simple wrapper around contrib/simple_usage.py."""
    _attrs = ['start', 'server_usages', 'stop', 'tenant_id',
             'total_local_gb_usage', 'total_memory_mb_usage',
             'total_vcpus_usage', 'total_hours']

    def get_summary(self):
        return {'instances': self.total_active_instances,
                'memory_mb': self.memory_mb,
                'vcpus': getattr(self, "total_vcpus_usage", 0),
                'vcpu_hours': self.vcpu_hours,
                'local_gb': self.local_gb,
                'disk_gb_hours': self.disk_gb_hours}

    @property
    def total_active_instances(self):
        return sum(1 for s in self.server_usages if s['ended_at'] is None)

    @property
    def vcpus(self):
        return sum(s['vcpus'] for s in self.server_usages
                   if s['ended_at'] is None)

    @property
    def vcpu_hours(self):
        return getattr(self, "total_hours", 0)

    @property
    def local_gb(self):
        return sum(s['local_gb'] for s in self.server_usages
                   if s['ended_at'] is None)

    @property
    def memory_mb(self):
        return sum(s['memory_mb'] for s in self.server_usages
                   if s['ended_at'] is None)

    @property
    def disk_gb_hours(self):
        return getattr(self, "total_local_gb_usage", 0)


class SecurityGroup(base.APIResourceWrapper):
    """Wrapper around havclient.security_groups.SecurityGroup which wraps its
    rules in SecurityGroupRule objects and allows access to them.
    """
    _attrs = ['id', 'name', 'description', 'tenant_id']

    @property
    def rules(self):
        """Wraps transmitted rule info in the havclient rule class."""
        if "_rules" not in self.__dict__:
            manager = nova_rules.SecurityGroupRuleManager(None)
            rule_objs = [nova_rules.SecurityGroupRule(manager, rule)
                         for rule in self._apiresource.rules]
            self._rules = [SecurityGroupRule(rule) for rule in rule_objs]
        return self.__dict__['_rules']


class SecurityGroupRule(base.APIResourceWrapper):
    """ Wrapper for individual rules in a SecurityGroup. """
    _attrs = ['id', 'ip_protocol', 'from_port', 'to_port', 'ip_range', 'group']

    def __unicode__(self):
        if 'name' in self.group:
            vals = {'from': self.from_port,
                    'to': self.to_port,
                    'group': self.group['name']}
            return _('ALLOW %(from)s:%(to)s from %(group)s') % vals
        else:
            vals = {'from': self.from_port,
                    'to': self.to_port,
                    'cidr': self.ip_range['cidr']}
            return _('ALLOW %(from)s:%(to)s from %(cidr)s') % vals

    # The following attributes are defined to keep compatibility with Neutron
    @property
    def ethertype(self):
        return None

    @property
    def direction(self):
        return 'ingress'


class FlavorExtraSpec(object):
    def __init__(self, flavor_id, key, val):
        self.flavor_id = flavor_id
        self.id = key
        self.key = key
        self.value = val


class FloatingIp(base.APIResourceWrapper):
    _attrs = ['id', 'ip', 'fixed_ip', 'port_id', 'instance_id', 'pool']

    def __init__(self, fip):
        fip.__setattr__('port_id', fip.instance_id)
        super(FloatingIp, self).__init__(fip)


class FloatingIpPool(base.APIDictWrapper):
    def __init__(self, pool):
        pool_dict = {'id': pool.name,
                     'name': pool.name}
        super(FloatingIpPool, self).__init__(pool_dict)


class FloatingIpTarget(base.APIDictWrapper):
    def __init__(self, server):
        server_dict = {'name': '%s (%s)' % (server.name, server.id),
                       'id': server.id}
        super(FloatingIpTarget, self).__init__(server_dict)

def havclient(User, p_id):
    insecure = False
    LOG.debug('havclient connection created using token "%s" and url "%s"' %
              (User.token.id, base.url_for(User, 'compute')))

    token=User._authorized_tenants[p_id]
    User.token = token
    c = nova_client.Client(User.username,
                           token.id,
                           project_id=p_id,
                           auth_url=base.url_for(User, 'compute'),
                           insecure=insecure)
    #c.client.auth_token = User.token.id
    c.client.auth_token = token.id
    c.client.management_url = base.url_for(User, 'compute')
    return c

def server_vnc_console(request, instance_id, console_type='novnc'):
    return VNCConsole(havclient(request).servers.get_vnc_console(instance_id,
                                                  console_type)['console'])


def server_spice_console(request, instance_id, console_type='spice-html5'):
    return SPICEConsole(havclient(request).servers.get_spice_console(
            instance_id, console_type)['console'])


def flavor_create(request, name, memory, vcpu, disk, flavorid='auto',
                  ephemeral=0, swap=0, metadata=None):
    flavor = havclient(request).flavors.create(name, memory, vcpu, disk,
                                                flavorid=flavorid,
                                                ephemeral=ephemeral,
                                                swap=swap)
    if (metadata):
        flavor_extra_set(request, flavor.id, metadata)
    return flavor

def flavor_list(user):
    return havclient(user).flavors.list(detailed=True)

def flavor_delete(request, flavor_id):
    havclient(request).flavors.delete(flavor_id)


@timeout(5)
def flavor_get(p_id, user, flavor_id):
    return havclient(user, p_id).flavors.get(flavor_id)


def flavor_get_extras(request, flavor_id, raw=False):
    """Get flavor extra specs."""
    flavor = havclient(request).flavors.get(flavor_id)
    extras = flavor.get_keys()
    if raw:
        return extras
    return [FlavorExtraSpec(flavor_id, key, value) for
            key, value in extras.items()]


def flavor_extra_delete(request, flavor_id, keys):
    """Unset the flavor extra spec keys."""
    flavor = havclient(request).flavors.get(flavor_id)
    return flavor.unset_keys(keys)


def flavor_extra_set(request, flavor_id, metadata):
    """Set the flavor extra spec keys."""
    flavor = havclient(request).flavors.get(flavor_id)
    if (not metadata):  # not a way to delete keys
        return None
    return flavor.set_keys(metadata)


def snapshot_create(request, instance_id, name):
    return havclient(request).servers.create_image(instance_id, name)


def keypair_create(request, name):
    return havclient(request).keypairs.create(name)


def keypair_import(request, name, public_key):
    return havclient(request).keypairs.create(name, public_key)


def keypair_delete(request, keypair_id):
    havclient(request).keypairs.delete(keypair_id)


def keypair_list(request):
    return havclient(request).keypairs.list()


def server_create(request, name, image, flavor, key_name, user_data,
                  security_groups, block_device_mapping, nics=None,
                  availability_zone=None, instance_count=1, admin_pass=None):
    return Server(havclient(request).servers.create(
            name, image, flavor, userdata=user_data,
            security_groups=security_groups,
            key_name=key_name, block_device_mapping=block_device_mapping,
            nics=nics, availability_zone=availability_zone,
            min_count=instance_count, admin_pass=admin_pass), request)


def server_delete(request, instance):
    havclient(request).servers.delete(instance)


def server_get(request, instance_id):
    return Server(havclient(request).servers.get(instance_id), request)

@timeout(5)
def server_port(User, p_id, server, search_opts=None, all_tenants=False):
    return havclient(User, p_id).servers.get_port(server.id,'spice')

@timeout(5)
def get_spice_secure(User, server, p_id):
    return havclient(User, p_id).servers.get_control(server.id)

@timeout(5)
def get_cipher(User, p_id, server):
    return havclient(User, p_id).cipher.get(server.id)

def get_hypervisor_type(User):
    return havclient(User).hypervisors.list()

@timeout(5)
def get_control(User, server, p_id):
    return havclient(User, p_id).servers.get_control(server.id)[1]

@timeout(5)
def connect_status(User, p_id, server):
    return havclient(User, p_id).servers.get_connect_status(server.id)[1]

#@timeout(5)
def vm_list(User, detailed, p_id=None, search_opts=None, all_tenants=False):
    return server_list(User, detailed, p_id, search_opts=search_opts, all_tenants=all_tenants)[0]

def server_list(User, detailed, p_id, search_opts=None, all_tenants=False):
    page_size = 20
    paginate = False
    if search_opts is None:
        search_opts = {}
    elif 'paginate' in search_opts:
        paginate = search_opts.pop('paginate')
        if paginate:
            search_opts['limit'] = page_size + 1

    if all_tenants:
        search_opts['all_tenants'] = True
    else:
        search_opts['project_id'] = p_id
        if detailed == True:
            search_opts['user_id'] = User.id
        elif detailed == "is_simply":
            pass
        #    search_opts['search_by_user'] = True
    servers = [Server(s, User)
                for s in havclient(User, p_id).servers.list(detailed, search_opts)]

    has_more_data = False
    if paginate and len(servers) > page_size:
        servers.pop(-1)
        has_more_data = True
    elif paginate and len(servers) == 1000:
        has_more_data = True

    return (servers, has_more_data)

def server_detail(p_id, request, id):
    return havclient(request, p_id).servers.get(id)

def server_console_output(request, instance_id, tail_length=None):
    """Gets console output of an instance."""
    return havclient(request).servers.get_console_output(instance_id,
                                                          length=tail_length)
@timeout(5)
def server_pause(User, instance_id,p_id):
    havclient(User, p_id).servers.pause(instance_id)

@timeout(5)
def server_unpause(User, instance_id, p_id):
    havclient(User, p_id).servers.unpause(instance_id)

def server_suspend(request, instance_id):
    havclient(request).servers.suspend(instance_id)


def server_resume(request, instance_id):
    havclient(request).servers.resume(instance_id)

@timeout(5)
def server_reboot(User, instance_id, p_id, soft_reboot=False):
    hardness = REBOOT_HARD
    if soft_reboot:
        hardness = REBOOT_SOFT
    havclient(User, p_id).servers.reboot(instance_id, hardness)


def server_rebuild(request, instance_id, image_id, password=None):
    return havclient(request).servers.rebuild(instance_id, image_id,
                                               password)


def server_update(request, instance_id, name):
    return havclient(request).servers.update(instance_id, name=name)


def server_migrate(request, instance_id):
    havclient(request).servers.migrate(instance_id)


def server_resize(request, instance_id, flavor, **kwargs):
    havclient(request).servers.resize(instance_id, flavor, **kwargs)


def server_confirm_resize(request, instance_id):
    havclient(request).servers.confirm_resize(instance_id)


def server_revert_resize(request, instance_id):
    havclient(request).servers.revert_resize(instance_id)

@timeout(5)
def server_start(User, instance_id, p_id):
    havclient(User, p_id).servers.start(instance_id)

@timeout(5)
def server_stop(User, instance_id, p_id):
    havclient(User, p_id).servers.stop(instance_id)


def tenant_quota_get(request, tenant_id):
    return base.QuotaSet(havclient(request).quotas.get(tenant_id))


def tenant_quota_update(request, tenant_id, **kwargs):
    havclient(request).quotas.update(tenant_id, **kwargs)


def default_quota_get(request, tenant_id):
    return base.QuotaSet(havclient(request).quotas.defaults(tenant_id))


def usage_get(request, tenant_id, start, end):
    return NovaUsage(havclient(request).usage.get(tenant_id, start, end))


def usage_list(request, start, end):
    return [NovaUsage(u) for u in
            havclient(request).usage.list(start, end, True)]


def virtual_interfaces_list(request, instance_id):
    return havclient(request).virtual_interfaces.list(instance_id)


def get_x509_credentials(request):
    return havclient(request).certs.create()


def get_x509_root_certificate(request):
    return havclient(request).certs.get()


def instance_volume_attach(request, volume_id, instance_id, device):
    return havclient(request).volumes.create_server_volume(instance_id,
                                                              volume_id,
                                                              device)

def instance_volume_detach(request, instance_id, att_id):
    return havclient(request).volumes.delete_server_volume(instance_id,
                                                                att_id)

def hypervisor_list(request, p_id):
    return havclient(request, p_id).hypervisors.list()

def hypervisor_search(request, hostsname, servers=True):
    return havclient(request).hypervisors.search(hostsname, servers)

def hypervisor_stats(request):
    return havclient(request).hypervisors.statistics()


@timeout(5)
def tenant_absolute_limits(user, reserved=False):
    # Add by wangderan 20150525 start 
    #if user == None:
    #    return None
    # Add by wangderan 20150525 end

    limits = havclient(user).limits.get().absolute
        
    limits_dict = {}
    for limit in limits:
        # -1 is used to represent unlimited quotas
        if limit.value == -1:
            limits_dict[limit.name] = float("inf")
        else:
            limits_dict[limit.name] = limit.value
    return limits_dict


def availability_zone_list(request, detailed=False):
    return havclient(request).availability_zones.list(detailed=detailed)


def service_list(request):
    return havclient(request).services.list()


def aggregate_list(request):
    result = []
    for aggregate in havclient(request).aggregates.list():
        result.append(havclient(request).aggregates.get(aggregate.id))

    return result

def list_extensions(request):
    return ListExtManager(havclient(request)).show_all()

def extension_supported(extension_name, request):
    """
    this method will determine if nova supports a given extension name.
    example values for the extension_name include AdminActions, ConsoleOutput,
    etc.
    """
    extensions = list_extensions(request)
    for extension in extensions:
        if extension.name == extension_name:
            return True
    return False

def check_connection(ip, port):
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sk.settimeout(1)
    try:
        sk.connect(ip, port)
        Logger.info("Server %s port %d is Ready!",(ip, port))
        return True
    except Exception:
        Logger.info("Server %s port %d is not Ready!" ,(ip, port))
        return False
    finally:
        sk.close()
    return False

def get_vm_ip(vm):
    address = getattr(vm, "addresses", None)
    for key in address.keys():
        vmnetwork = address[key][0]
    vmip = vmnetwork['addr']
    return vmip

@timeout(5)
def get_vm_type(User, p_id, vm):
    try:
        detail = server_detail(p_id, User, str(vm.id))
        hyper_host = getattr(detail, "OS-EXT-SRV-ATTR:hypervisor_hostname", None)

        visor_list = hypervisor_list(User, p_id)

        for i in visor_list:
            if i.hypervisor_hostname == hyper_host:
                vm_type = i.hypervisor_type
                break
        if vm_type.lower() == 'qemu':
            return 'JSP' 
        elif vm_type.lower() == 'xen' or vm_type.lower() == 'hyperv':
            return 'RDP'
    except:
        return 'UNKNOWN'

class IdentityAPIVersionManager(base.APIVersionManager):
    def upgrade_v2_user(self, user):
        if getattr(user, "project_id", None) is None:
            user.project_id = getattr(user, "default_project_id",
                                      getattr(user, "tenantId", None))
        return user

    def get_project_manager(self, *args, **kwargs):
        if VERSIONS.active < 3:
            manager = keystoneclient(*args, **kwargs).tenants
        else:
            manager = keystoneclient(*args, **kwargs).projects
        return manager

VERSIONS = IdentityAPIVersionManager("identity", preferred_version=2.0)

try:
    from keystoneclient.v2_0 import client as keystone_client_v2
    VERSIONS.load_supported_version(2.0, {"client": keystone_client_v2})
except ImportError:
    pass

def _get_endpoint_url(request, endpoint_type, catalog=None):
    if getattr(request, "service_catalog", None):
        url = base.url_for(request,
                           service_type='identity',
                           endpoint_type=endpoint_type)
    else:
        #auth_url = getattr(settings, 'OPENSTACK_KEYSTONE_URL')
        auth_url = 'OPENSTACK_KEYSTONE_URL'
        url = request.session.get('region_endpoint', auth_url)

    return url

def keystoneclient(request, admin=False):
    if admin:
        if not request.is_superuser:
            raise exceptions.NotAuthorized
        endpoint_type = 'adminURL'
    else:
        endpoint_type = 'internalURL'

    api_version = VERSIONS.get_active_version()

    cache_attr = "_keystoneclient_admin" if admin \
        else backend.KEYSTONE_CLIENT_ATTR
    if hasattr(request, cache_attr) and (not request.token.id
            or getattr(request, cache_attr).auth_token == request.token.id):
        LOG.debug("Using cached client for token: %s" % request.token.id)
        conn = getattr(request, cache_attr)
    else:
        endpoint = _get_endpoint_url(request, endpoint_type)
        insecure = False
        cacert = None
        LOG.debug("Creating a new keystoneclient connection to %s." % endpoint)
        #remote_addr = request.environ.get('REMOTE_ADDR', '')
        conn = api_version['client'].Client(token=request.token.id,
                                            endpoint=endpoint,
                                            #original_ip=remote_addr,
                                            insecure=insecure,
                                            cacert=cacert,
                                            auth_url=endpoint)
                                            #debug=settings.DEBUG)
        setattr(request, cache_attr, conn)
    return conn

def user_get(request, user_id, admin=True):
    user = keystoneclient(request, admin=admin).users.get(user_id)
    return VERSIONS.upgrade_v2_user(user)

#@timeout(5)
def tenant_list(User, user, paginate=False, marker=None, domain=None,
                admin=True):
    manager = VERSIONS.get_project_manager(User, admin=admin)
    page_size = 20

    limit = None
    if paginate:
        limit = page_size + 1

    has_more_data = False
    if VERSIONS.active < 3:
        tenants = manager.list(limit, marker, user)
        if paginate and len(tenants) > page_size:
            tenants.pop(-1)
            has_more_data = True
    else:
        tenants = manager.list(domain=domain, user=user)
    return (tenants, has_more_data)

def user_update_password(request, user, password, admin=True):
    manager = keystoneclient(request, admin=admin).users
    if VERSIONS.active < 3:
        return manager.update_password(user, password)
    else:
        return manager.update(user, password=password)

@timeout(5)
def user_update_own_password(request, origpassword, password):
    client = keystoneclient(request, admin=False)
    client.user_id = request.id
    if VERSIONS.active < 3:
        return client.users.update_own_password(origpassword, password)
    else:
        return client.users.update_password(origpassword, password)

@timeout(5)
def create_remote_assistance(User, p_id, data):
    return havclient(User, p_id).servers.create_remote_assistance(data)

@timeout(5)
def cancel_remote_assistance(User, p_id, server):
    return havclient(User, p_id).servers.cancel_remote_assistance(server)

@timeout(5)
def connect_client_info(User, p_id, server, body):
    return havclient(User, p_id).servers.sendvmlogininfo(server, body)

@timeout(5)
def usb_audit(User, p_id, server, body):
    return havclient(User, p_id).servers.usb_audit(server, body)
