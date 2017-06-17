# Copyright 2012 Nebula, Inc.
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

from django.conf import settings
from django import shortcuts
import django.views.decorators.vary
from django.views.generic import View as AjaxView
from django.http import HttpResponse
from django.conf import settings
from oslo_log import log as logging
from datetime import datetime
import api
import json
import horizon
from horizon import base
from horizon import exceptions
from horizon import notifications
from xmlrpclib import ServerProxy
from openstack_dashboard.dashboards.\
     admin.instances import console
LOG = logging.getLogger(__name__)

MESSAGES_PATH = getattr(settings, 'MESSAGES_PATH', None)


def get_user_home(user):
    dashboard = None
    if user.is_superuser:
        try:
            dashboard = horizon.get_dashboard('admin')
        except base.NotRegistered:
            pass

    if dashboard is None:
        dashboard = horizon.get_default_dashboard()

    # Domain Admin, Project Admin will default to identity
    #if (user.token.project.get('id') is None or
    #        (user.is_superuser and user.token.project.get('id'))):
        #dashboard = horizon.get_dashboard('identity')
    dashboard = horizon.get_dashboard('admin')

    return dashboard.get_absolute_url()


@django.views.decorators.vary.vary_on_cookie
def splash(request):
    if not request.user.is_authenticated():
        raise exceptions.NotAuthenticated()

    response = shortcuts.redirect(horizon.get_user_home(request.user))
    if 'logout_reason' in request.COOKIES:
        response.delete_cookie('logout_reason')
    # Display Message of the Day message from the message files
    # located in MESSAGES_PATH
    if MESSAGES_PATH:
        notifications.process_message_notification(request, MESSAGES_PATH)
    return response

class RemoteAssistance(AjaxView):

    def get(self, request, *args, **kwargs):

        raise NotImplementedError()

class HandleRemote(RemoteAssistance):

    def get(self, request, *args, **kwargs):

        try:
            if kwargs.get('remote_id') and hasattr(request.user,'token'):
                instance_id, password = kwargs['remote_id'].split('_')
                instance = api.nova.server_get(request, instance_id)
                console_type = getattr(settings, 'CONSOLE_TYPE', 'VNC')
                _type, console_url = console.get_console(request, 
                              console_type, instance, password=password)
                callback = request.GET['callback']
                data = ''.join([callback, '({"success":"%s"})' % console_url])
                return HttpResponse(data, 
                       content_type="text/plain")
            else:
                return HttpResponse('token is invalid',\
                    content_type="text/plain")
        except Exception:
            return HttpResponse('Handle Remote Error!',\
                content_type="text/plain")

class WaitforRemote(RemoteAssistance):

    def get(self, request, *args, **kwargs):
        
        try:
            if kwargs.get('remote_id') and hasattr(request.user, 'token'):
                instance_id, update_id = kwargs['remote_id'].split('_')
                remote = {"instance_id":instance_id,
                          "status":'wait'}
                api.nova.create_remote(request, remote)
                callback = request.GET['callback']
                data = ''.join([callback, 
                       '({"update":"%s","status":"wait"})' % update_id])
                return HttpResponse(data,\
                    content_type="text/plain")
            else:
                return HttpResponse('token is invalid',\
                    content_type="text/plain")
        except Exception:
            return HttpResponse('Waiting Remote Error!',\
                   content_type="text/plain")

class DeleteRemote(RemoteAssistance):

    def get(self, request, *args, **kwargs):
        try:
            if kwargs.get('remote_id') and hasattr(request.user, 'token'):
                instance_id = kwargs['remote_id']
                api.nova.delete_remote(request, instance_id)
                callback = request.GET['callback']
                data =''.join([callback, '({"success":"success"})'])
                return HttpResponse(data,\
                   content_type="text/plain")
            else:
                return HttpResponse('token is invalid',\
                    content_type="text/plain")
        except Exception:
            return HttpResponse('Delete Remote Error!', 
                   content_type="text/plain")

class RemoteNumber(RemoteAssistance):

    def get(self, request, *args, **kwargs):
                
        try:
            if hasattr(request.user, 'token'):
                remote = api.nova.remote_assistance_list(request)
                callback = request.GET['callback']
                data = ''.join([callback, 
                          '({"remote":'+json.dumps(remote.get("remote",{}))+',\
                          "count":"%s"})' % \
                          (len(remote.get('remote', 0)))])
                return HttpResponse(data,\
                    content_type="text/plain")
            else:
                return HttpResponse('token is invalid',\
                    content_type="text/plain")
        except Exception:
            data = request.GET['callback']+'({"count":0})'
            return HttpResponse(data,\
                   content_type="text/plain")


class FinishRemote(RemoteAssistance):

    def get(self, request, *args, **kwargs):

        try:
            if hasattr(request.user, 'token'):
                remote = api.nova.remote_assistance_list(
                         request, kwargs['remote_id'])
                if remote:
                    api.nova.delete_remote(request, kwargs['remote_id'])
                    result = remote.get('remote')
                    client_ip = result.get('client_ip', '0.0.0.0')
                    #obj_instance=ServerProxy("http://%s:8099" % client_ip)
                    #socket.setdefaulttimeout(10)
                    #result = obj_instance.receive(\
                    #         "c9748aad-4e82-499a-b8aa-2c74358457fc")
                    socket.setdefaulttimeout(None)
                    callback = request.GET['callback']
                    data =''.join([callback, '({"success":"success"})'])
                    LOG.info("FinishRemote ================%s" % client_ip) 
                return HttpResponse(data,\
                           content_type="text/plain")
            else:
                return HttpResponse('token is invalid',\
                    content_type="text/plain")
        except Exception:
            return HttpResponse('Finish Remote Error!',\
                   content_type="text/plain")
