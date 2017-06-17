#-*- coding: utf-8 -*- 
import os
import json
import subprocess

import webob.dec

from polltask.wsgi import Application, Request
from polltask.logger import get_default_logger
from polltask.ssh_connection import SSHConnection
from polltask.utils import (hostname_to_ip, 
                            get_domain_name, 
                            get_local_host,
                            get_etc_hosts,
                            add_etc_hosts,
                            execute,
                            copy_ssh_key_to)
from polltask.config import Config
from polltask.tasks.openstack.openstack_utils import get_option_from_nova_host

INSTALL_APP_CONF_NAME = '.fire_openstack.ini'
INSTALL_APP_CONF_PATH = os.path.join('/root', INSTALL_APP_CONF_NAME)

INSTALL_APP_SERVICE = "fire-openstack.service"

CONTROLLER_NOVA_SSH_BAK_PATH = '/root/.ssh-controller'
CONTROLLER_NOVA_HOME_PATH = get_option_from_nova_host('DEFAULT', 'state_path')

CONTROLLER_LIBVIRT_PKI_PATH = '/etc/pki/libvirt-spice'
COMPUTE_LIBVIRT_PKI_PATH = CONTROLLER_LIBVIRT_PKI_PATH

class SetupInstallEnv(Application):
    def __init__(self):
        super(SetupInstallEnv, self).__init__()
        self.logger = get_default_logger('OpenstackSetupInstallEnv') 

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, req):
	token = req.environ.get('HTTP_X_AUTH_TOKEN', None)
        if not token:
            headers = []
            status=(204, 'No Token')
            headers.append(('Vary', 'X-Auth-Token'))
            return webob.Response(
                             body='',
                             status='%s %s' % status,
                             headerlist=headers)

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

    def add_compute_node(self, **kwargs):
        for key in ['compute_server', 'compute_root_pw']:
            if key not in kwargs.keys():
                return webob.exc.HTTPBadRequest
        compute_host = kwargs['compute_server']
        compute_root_pw = kwargs['compute_root_pw']
        try:
            compute_ssh = self._host_root_pw_is_right(compute_host,
                                        compute_root_pw)
        except Exception as e:
            raise e

        controller_hostname = get_local_host('NAME')
        self._authorize_compute_key(controller_hostname, 
                                compute_host,
                                'root',
                                compute_root_pw)

        installed_flag = self._compute_service_has_installed(compute_ssh)
        if installed_flag:
            self._reset_compute_node(compute_ssh)
        else:
            self._setup_compute_node(compute_ssh, **kwargs)

        self._add_controller_libvirt_pki(compute_ssh)

        #compute_ssh.send_expect('reboot', '# ')
        global INSTALL_APP_SERVICE
        #compute_ssh.send_expect('systemctl restart %s &' % INSTALL_APP_SERVICE, '# ', None)
        compute_ssh.send_expect('shutdown -r 1', '# ')

        return 'Installing'

    def delete_compute_node(self, **kwargs):
        pass

    def _compute_service_has_installed(self, compute_ssh):
        ret = compute_ssh.send_expect("systemctl list-unit-files | grep openstack-nova-compute", '# ')
        if 'openstack-nova-compute' in ret:
            return True
        else:
            return False

    def _host_root_pw_is_right(self, host, password):
        try:
            ssh = SSHConnection(host, 'root', password)
            return ssh
        except SSHConnectionException as e:
            return webob.exc.HTTPExpectationFailed(str(e))

    def _reset_compute_node(self, compute_ssh):
        pass

    def _setup_compute_node(self, compute_ssh, **kwargs):
        compute_user = compute_ssh.username
        if compute_user != 'root':
            raise Exception("Not [root] user when setting compute install env!")

        compute_hostip = hostname_to_ip(compute_ssh)
        compute_pw = compute_ssh.password
        compute_hostname = compute_ssh.send_expect('hostname', '# ')
        compute_domain = get_domain_name(compute_ssh)
        add_etc_hosts(compute_ssh, 
                        compute_hostip,
                        compute_hostname,
                        compute_domain,
                        True)

        controller_hostname = get_local_host('NAME')
        controller_hostip = get_local_host()
        controller_hostline = get_etc_hosts(None, controller_hostip)
        if not controller_hostline:
            controller_domain = get_domain_name(None, True)
            controller_hostline = add_etc_hosts(None,
                                                controller_hostip,
                                                controller_hostname,
                                                controller_domain)
        # Add compute host line on the controller node
        compute_hostline = add_etc_hosts(None, 
                                            compute_hostip,
                                            compute_hostname,
                                            compute_domain,
                                            True)

        # Add controller host line on the compute node
        #if controller_hostline.endswith('\n'):
        #    add_cmd = "echo -e '%s' >> /etc/hosts" % controller_hostline
        #else:
        #    add_cmd = "echo -e '%s\n' >> /etc/hosts" % controller_hostline
        add_cmd = "echo -e '%s' >> /etc/hosts" % controller_hostline.strip('\n')
        del_cmd = "sed -i '/^ *%s .*/d' /etc/hosts" % controller_hostip
        compute_ssh.send_expect(del_cmd, '# ')
        compute_ssh.send_expect(add_cmd, '# ')

        # update the fire_openstack.ini file
        global INSTALL_APP_CONF_PATH
        tmp_path = '/tmp'
        tmp_conf_path = os.path.join(tmp_path, os.path.basename(INSTALL_APP_CONF_PATH))

        if self._file_exists(tmp_conf_path):
            cmd = 'rm -f %s' % tmp_conf_path
            subprocess.call(cmd.split())

        if self._file_exists(INSTALL_APP_CONF_PATH, compute_ssh):
            compute_ssh.copy_file_from(INSTALL_APP_CONF_PATH, tmp_path)

        conf_handle = Config(tmp_conf_path, False)
        self._add_install_env(conf_handle, 'compute', compute_pw)
        self._add_controller_env(conf_handle, 
                                controller_hostname,
                                '',
                                '')
        conf_handle.rewrite_config()

        compute_ssh.copy_file_to(tmp_conf_path, os.path.dirname(INSTALL_APP_CONF_PATH))

        # copy controller nova .ssh directory to compute node, and renamed to .ssh.controller
        global CONTROLLER_NOVA_SSH_BAK_PATH 
        if (self._file_exists(CONTROLLER_NOVA_SSH_BAK_PATH, compute_ssh, 'd') or 
            self._file_exists(CONTROLLER_NOVA_SSH_BAK_PATH, compute_ssh, 'f')):
            compute_ssh.send_expect('rm -rf %s' % CONTROLLER_NOVA_SSH_BAK_PATH, '# ')
        nova_src_ssh_path = os.path.join(CONTROLLER_NOVA_SSH_BAK_PATH, '.ssh')
        compute_ssh.send_expect('mkdir -p %s' % nova_src_ssh_path, '# ')
        global CONTROLLER_NOVA_HOME_PATH
        for f in ['authorized_keys', 'config', 'id_rsa']:
            compute_ssh.copy_file_to(os.path.join(CONTROLLER_NOVA_HOME_PATH, '.ssh/%s' % f), 
                                        nova_src_ssh_path) 

    def _authorize_compute_key(self, controller_addr, compute_addr, compute_user, compute_pass):
        try:
            controller_ssh = SSHConnection(controller_addr, 'root', '')
        except SSHConnectionException as e:
            return webob.exc.HTTPExpectationFailed(str(e))
        ret = copy_ssh_key_to(controller_ssh, compute_addr, compute_user, compute_pass) 
        if not ret:
            raise Exception("Authorize compute host key failed!")

    def _file_exists(self, f_path, ssh=None, f_type='f'):
        cmd = "test -%s %s" % (f_type, f_path)
        if ssh:
            retcode, out = ssh.send_expect(cmd, '# ', verify=True)
        else:
            _, err = execute(cmd, shell=False)
            if err is not None:
                retcode = 1
            else:
                retcode = 0

        if retcode == 0:
            return True
        else:
            return False

    def _add_install_env(self, conf_handle, install_type, install_root_pw):
        sections = conf_handle.get_sections()
        if 'install_env' not in sections:
            conf_handle.add_section('install_env')
        conf_handle.set_option_value('install_env', 
                                        'install_type', 
                                        install_type)
        conf_handle.set_option_value('install_env', 
                                        'install_root_pw', 
                                        install_root_pw)


    def _add_controller_env(self,
                            conf_handle,
                            peer_controller_server,
                            peer_controller_user,
                            peer_controller_pw):
        CONTROLLER_ENV_SECTION = 'controller_env'
        sections = conf_handle.get_sections()
        if CONTROLLER_ENV_SECTION not in sections:
            conf_handle.add_section(CONTROLLER_ENV_SECTION)
        conf_handle.set_option_value(CONTROLLER_ENV_SECTION,
                                        'controller_server',
                                        peer_controller_server)
        conf_handle.set_option_value(CONTROLLER_ENV_SECTION,
                                        'controller_user',
                                        peer_controller_user)
        conf_handle.set_option_value(CONTROLLER_ENV_SECTION,
                                        'controller_password',
                                        peer_controller_pw)

    def _add_controller_libvirt_pki(self,
                                    compute_ssh, 
                                    controller_pki_path=CONTROLLER_LIBVIRT_PKI_PATH,
                                    compute_pki_path=COMPUTE_LIBVIRT_PKI_PATH):
        try:
            compute_ssh.copy_file_to('-r ' + controller_pki_path,
                                        compute_pki_path)
            cmd = "chcon -R -u system_u %s" % compute_pki_path
            compute_ssh.send_expect(cmd, '# ')
        except Exception as e:
            return webob.exc.HTTPExpectationFailed(str(e))
        
