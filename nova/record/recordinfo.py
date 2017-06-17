from nova import objects
from nova.record import instance_actions

def exception_to_dict(fault):
    """Converts exceptions to a dict for use in notifications."""
    # TODO(johngarbutt) move to nova/exception.py to share with wrap_exception
    code = 500
    if hasattr(fault, "kwargs"):
        code = fault.kwargs.get('code', 500)
    try:
        message = fault.format_message()
    except Exception:
        try:
            message = unicode(fault)
        except Exception:
            message = None
    if not message:
        message = fault.__class__.__name__
    u_message = unicode(message)[:255]

    fault_dict = dict(exception=fault)
    fault_dict["message"] = u_message
    fault_dict["code"] = code
    return fault_dict

def conductor_action_log(action):
    def _decorator_checker(function):
        def decorated_function(self, context, instances, *args, **kwargs):
            try:
                return function(self, context, instances, *args, **kwargs)
            except Exception as error:
                names = format_name(instances)
                if names:
                    for name in names:
                        error_current_record_from_exc(context, name, action, error)
                raise
        return decorated_function
    return _decorator_checker

def format_name(meta_data):
    name = []
    if type(meta_data) == dict:
        name.append(meta_data['server'].get('name'))
    elif type(meta_data) == list:
        for meta in meta_data:
            name.append(meta.display_name)
    else:
        name.append(meta_data.display_name)
    return name

def error_action_log(action):
    def _decorator_checker(function):
        def decorated_function(self, req, body, id=None, *args, **kwargs):
            context = req.environ['nova.context']
            try:
                if id:
                    return function(self, req, body, id, *args, **kwargs)
                else:
                    return function(self, req, body, *args, **kwargs)
            except Exception as error:
                names = format_name(body)
                if names:
                    for name in names:
                        error_current_record_from_exc(context, name, action, error)
                raise
        return decorated_function
    return _decorator_checker

def func_action_log(action):
    def _decorator_checker(function):
        def decorated_function(context, name, *args, **kwargs):
            try:
                tmp = function(context, name, *args, **kwargs)
                add_current_record_for_success(context, name, action)
                return tmp
            except Exception as error:
                error_current_record_from_exc(context, name, action, error)
                raise
        return decorated_function
    return _decorator_checker

def class_action_log(action):
    def _decorator_checker(function):
        #@functools.wraps(function)
        def decorated_function(self, context, instance, *args, **kwargs):
            types = type(instance)
            if types == dict:
                name = instance.get('display_name') or instance.get('name')
            elif types == unicode or types == str:
                name = instance
            else:
                name = instance.display_name
            try:
                tmp = function(self, context, instance, *args, **kwargs)
                add_current_record_for_success(context, name, action)
                return tmp
            except Exception as error:
                error_current_record_from_exc(context, name, action, error)
                raise
        return decorated_function
    return _decorator_checker

def record_args(context, name, event_subject, result, detail):
    record_obj = objects.Systemlogs(context=context)
    record_obj.event_subject = event_subject
    record_obj.event_object = name
    #record_obj.action = action
    if context.visit_ip:
        record_obj.visit_ip = context.visit_ip
    else:
        record_obj.visit_ip = context.remote_address
    if getattr(context, 'user_name', None):
        record_obj.user_name = context.user_name
    else:
        record_obj.user_name = 'admin'
    if getattr(context, 'project_name', None):
        record_obj.project_name = context.project_name
    else:
        record_obj.project_name = 'admin'
    record_obj.result = result
    if detail:
        exc = exception_to_dict(detail)
        record_obj.update(exc)
    else:
        record_obj.message = detail
    return record_obj.systemlogs_create(context)

def add_current_record_for_success(context, name, event_subject, message='-'):
    result = instance_actions.SUCCESS
    return record_args(context, name, event_subject, result, message)

def error_current_record_from_exc(context, name, event_subject, fault):
    result = instance_actions.FAILURE
    return record_args(context, name, event_subject, result, fault)
