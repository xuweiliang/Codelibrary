# Copyright 2012 OpenStack Foundation
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

from contextlib import closing  # noqa
import json
import logging
import tempfile
import zipfile
from django.core.urlresolvers import reverse

from django.http import HttpResponse
from django.core.urlresolvers import reverse_lazy
from django import http
from django import shortcuts
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from openstack_auth import utils

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import views

from openstack_dashboard import api


from wsgiref.util import FileWrapper
import tarfile
from io import BytesIO

LOG = logging.getLogger(__name__)

def download_db_file(request):
#    template = 'admin/access_and_security/api_access/openrc.sh.template'
#    context = _get_openrc_credentials(request)

    # make v3 specific changes
#    context['user_domain_name'] = request.user.user_domain_name
    # sanity fix for removing v2.0 from the url if present
#    context['auth_url'] = utils.fix_auth_url_version(context['auth_url'])
#    context['os_identity_api_version'] = 3
#    context['os_auth_version'] = 3
#    return _download_rc_file_for_template(request, context, template)
#    try:
#        data = request.GET['data']
#        ret = api.device.download_db_file(request)
    d = api.device.download_db_file(request).text
    data = json.loads(d)
    #d = json.loads(d1,encoding="GBK")
    filename = data["filename"]
    filename_sql = filename + '.sql'
    out = data["buffer_out"]
#    filename = "a.tgz"
#    out = BytesIO()
#    tar = tarfile.open(mode = "w:gz", fileobj = out)
#    data = 'lala'.encode('utf-8')
#    file = BytesIO(data)
#    info = tarfile.TarInfo(name="1.txt")
#    info.size = len(data)
#    tar.addfile(tarinfo=info, fileobj=file)
#    tar.close()
    #response = HttpResponse(out, content_type='application/zip')
    response = HttpResponse(out, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename= %s' % filename_sql
    return response
#    return HttpResponse('success')
#    except Exception:
#        pass
#        #url = reverse('horizon:admin:access_and_security:index')
#        msg = _('Unable to download database.')
#        exceptions.handle(request, msg, redirect=url)
#
