# BSD LICENSE
#
# Copyright(c) 2010-2014 Intel Corporation. All rights reserved.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Intel Corporation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from polltask.logger import get_default_logger
from polltask.ssh_pexpect import SSHPexpect


class SSHConnection(object):

    """
    Module for create session to host.
    Implement send_expect/copy function upper SSHPexpet module.
    """

    def __init__(self, host, username, password='', login_expected='# ', login_timeout=30):
        self.host = host
        self.username = username
        self.password = password
        self.login_timeout = login_timeout
        self.login_expected = login_expected

        self.session = SSHPexpect(self.host, self.username, self.password, self.login_expected, self.login_timeout)
        self.logger = get_default_logger(self.host)
        self.init_log()

    def reconnect(self):
        self.session.close()
        self.session = None
        self.logger = None

        self.session = SSHPexpect(self.host, self.username, self.password, self.login_expected, self.login_timeout)
        self.logger = get_default_logger(self.host)
        self.init_log()

    def init_log(self):
        self.session.init_log(self.logger)

    def send_expect(self, cmds, expected, timeout=30, verify=False):
        "timout: if you want there is no timeout, then set timout to None."
        def _clear_result(result):
            #if '\r\n' in result:
            #    result = result.replace('\r\n', ' ')
            if 'You have new mail in' in result:
                result = result[:result.find('You have new mail in')]
                result = result.strip('\r\n')
            return result

        self.logger.info(cmds)
        if not verify:
            out = self.session.send_expect(cmds, expected, timeout, verify)
            self.logger.debug(out)
            out = _clear_result(out)
            return out
        else:
            retcode, out = self.session.send_expect(cmds, expected, timeout, verify)
            self.logger.debug(out)
            out = _clear_result(out)
            return (retcode, out)

    def get_session_before(self, timeout=30):
        out = self.session.get_session_before(timeout)
        self.logger.debug(out)
        return out

    def close(self):
        self.session.close()

    def isalive(self):
        return self.session.isalive()

    def copy_file_from(self, src, dst=".", password=''):
        self.session.copy_file_from(src, dst, password)

    def copy_file_to(self, src, dst="~/", password=''):
        self.session.copy_file_to(src, dst, password)

if __name__ == "__main__":
    ssh = SSHConnection('192.168.8.103', 'root', '111111')
    ssh.reconnect()
    out = ssh.send_expect('ls', '# ')
    """
    print out
    for i in out.split(' '):
        if not i:
            continue
        print i
    ssh.close()
    if ssh.isalive():
        ssh.send_expect("ls", '# ')
    
    ssh.send_expect("systemctl restart network", '# ')
    ssh_1 = SSHConnection('192.168.8.106', 'root', '111111', 20)
    out = ssh_1.send_expect("ls", '# ')
    print out
    """
    #out = out.replace('\r\n', ' ')
    #ssh.send_expect("openstack-service restart %s" % out, '# ', 60)
