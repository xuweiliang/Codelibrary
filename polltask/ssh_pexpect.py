import time
import subprocess

import pexpect
import pxssh

from polltask.exception import TimeoutException, SSHConnectionException, SSHSessionDeadException

"""
Module handle ssh sessions between two machines.
Implement send_expect function to send command and get output data.
Aslo support transfer files to one machine.
"""


class SSHPexpect(object):

    def __init__(self, host, username, password, login_expected='# ', login_timeout=30):
        self.magic_prompt = "MAGIC PROMPT"
        try:
            self.host = host
            self.username = username
            self.password = password
            self.login_timeout = login_timeout
            self._session_login()
            self.send_expect('stty -echo', login_expected, timeout=2)
        except Exception as e:
            if getattr(self, 'port', None):
                suggestion = "\nSuggession: Check if the fireware on [ %s ] " % \
                    self.ip + "is stoped\n"

            raise SSHConnectionException(str(e))

    def _session_login(self):
        def _login():
            self.session = pxssh.pxssh()
            if ':' in self.host:
                self.ip = self.host.split(':')[0]
                self.port = int(self.host.split(':')[1])
                self.session.login(self.ip, self.username,
                                   self.password, original_prompt='[$#>]',
                                   port=self.port, login_timeout=self.login_timeout)
            else:
                self.session.login(self.host, self.username,
                                   self.password, original_prompt='[$#>]', login_timeout=self.login_timeout)
        try:
            _login()
        except pexpect.EOF:
            cmd = "ssh-keygen -R {0}".format(self.host)
            subprocess.call(cmd.split())
            _login()
    
    def init_log(self, logger):
        self.logger = logger
        self.logger.info("ssh %s@%s" % (self.username, self.host))

    def send_expect_base(self, command, expected, timeout):
        self.__flush() # clear buffer
        self.session.PROMPT = expected
        self.__sendline(command)
        self.__prompt(command, timeout)

        before = self.get_output_before()
        return before

    def send_expect(self, command, expected, timeout=15, verify=False):
        out = self.send_expect_base(command, expected, timeout)
        if verify:
            ret_status = self.send_expect_base("echo $?", expected, timeout)
            retcode = int(ret_status)
            if retcode == 0:
                return (retcode, out)
            else:
                self.logger.error("Command: %s failure!" % command)
                self.logger.error(out)
                return (retcode, out)
        else:
            return out

    def get_session_before(self, timeout=15):
        """
        Get all output before timeout
        """
        self.session.PROMPT = self.magic_prompt
        try:
            self.session.prompt(timeout)
        except Exception as e:
            pass

        before = self.get_output_before()
        self.__flush()
        return before

    def __flush(self):
        """
        Clear all session buffer
        """
        self.session.buffer = ""
        self.session.before = ""

    def __prompt(self, command, timeout):
        if not self.session.prompt(timeout):
            raise TimeoutException(self.get_output_all(), command=command)

    def __sendline(self, command):
        if not self.isalive():
            raise SSHSessionDeadException(self.host)
        if len(command) == 2 and command.startswith('^'):
            self.session.sendcontrol(command[1])
        else:
            self.session.sendline(command)

    def get_output_before(self):
        if not self.isalive():
            raise SSHSessionDeadException(self.host)
        self.session.flush()
        before = self.session.before.rsplit('\r\n', 1)
        if before[0] == "[PEXPECT]":
            before[0] = ""

        return before[0]

    def get_output_all(self):
        self.session.flush()
        output = self.session.before
        output.replace("[PEXPECT]", "")
        return output

    def close(self):
        if self.isalive():
            self.session.logout()

    def isalive(self):
        return self.session.isalive()

    def copy_file_from(self, src, dst=".", password=''):
        """
        Copies a file from a remote place into local.
        """
        command = 'scp {0}@{1}:{2} {3}'.format(self.username, self.host, src, dst)
        if password == '':
            self._spawn_scp(command, self.password)
        else:
            self._spawn_scp(command, password)

    def copy_file_to(self, src, dst="~/", password=''):
        """
        Sends a local file to a remote place.
        """
        command = 'scp {0} {1}@{2}:{3}'.format(src, self.username, self.host, dst)
        if ':' in self.host:
            command = 'scp -P {0} -o NoHostAuthenticationForLocalhost=yes {1} {2}@{3}:{4}'.format(
                str(self.port), src, self.username, self.ip, dst)
        else:
            command = 'scp {0} {1}@{2}:{3}'.format(
                src, self.username, self.host, dst)
        if password == '':
            self._spawn_scp(command, self.password)
        else:
            self._spawn_scp(command, password)

    def _spawn_scp(self, scp_cmd, password):
        """
        Transfer a file with SCP
        """
        self.logger.info(scp_cmd)
        p = pexpect.spawn(scp_cmd)
        time.sleep(0.5)
        ssh_newkey = 'Are you sure you want to continue connecting'
        i = p.expect([ssh_newkey, 'password: ', "# ", pexpect.EOF,
                      pexpect.TIMEOUT], 120)
        if i == 0:  # add once in trust list
            p.sendline('yes')
            i = p.expect([ssh_newkey, '[pP]assword: ', pexpect.EOF], 2)

        if i == 1:
            time.sleep(0.5)
            p.sendline(password)
            p.expect("100%", 60)
        if i == 4:
            self.logger.error("SCP TIMEOUT error %d" % i)

        p.close()
