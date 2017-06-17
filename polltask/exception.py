# -*- coding=utf-8 -*-

import six

from logger import get_default_logger
from setting import SUPPORT_TASK_TYPE

fatal_exception_format_errors = False

class PollTaskException(Exception):
    """Base Poll Task Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = ("An unknown exception occurred.")
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs
        self.logger = get_default_logger(self.__module__)

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                exc_info = sys.exc_info()
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                self.logger.warn('Exception in string format operation')
                for name, value in six.iteritems(kwargs):
                    self.logger.error("%s: %s" % (name, value))    # noqa

                global fatal_exception_format_errors
                if fatal_exception_format_errors:
                    six.reraise(*exc_info)
                else:
                    # at least get the core message out if something happened
                    message = self.msg_fmt

        self.message = message
        super(PollTaskException, self).__init__(message)

    def format_message(self):
        # NOTE(mrodden): use the first argument to the python Exception object
        # which should be our full NovaException message, (see __init__)
        return self.args[0]


class ConfigNotFound(PollTaskException):
    msg_fmt = ("Could not find config at %(path)s")

class TaskTypeException(PollTaskException):
    msg_fmt = ("Not support task type [ %(task_type)s ], now just support " + "%s" % SUPPORT_TASK_TYPE)

class PasteAppNotFound(PollTaskException):
    msg_fmt = ("Could not load paste app '%(name)s' from %(path)s")

class TimeoutException(PollTaskException):
    msg_fmt = ("Timeout when executing %(command)s")

class SSHConnectionException(PollTaskException):
    msg_fmt = ("Error trying to connect with %(host)s")

class SSHSessionDeadException(PollTaskException):
    msg_fmt = ("SSH session with %(host)s has been dead")

class NICNotFound(PollTaskException):
    msg_fmt = ("Could not find a NIC by the given IP %(ip)s")

class NetmaskErrorException(PollTaskException):
    mas_fmt = ("Netmask %(netmask)s error, maybe check the mapping between CIDR prefix and netmask")
