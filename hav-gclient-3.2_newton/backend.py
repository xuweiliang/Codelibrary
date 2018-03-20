""" Module defining the Django auth backend class for the Keystone API. """
import time
import hashlib
import logging
import havclient
import Setting
import Logger
import traceback

from keystoneclient.v2_0 import client as keystone_client
from keystoneclient import exceptions as keystone_exceptions
from keystoneclient.v2_0.tokens import Token, TokenManager


from user import create_user_from_token

LOG = logging.getLogger(__name__)

KEYSTONE_CLIENT_ATTR = "_keystoneclient"

def _parse_url_to_host(url):
    host = url.replace('http://', '')
    host = host.split(':')[0]
    host = host.split('/')[0]
    return host

def get_identity_public_endpoint(keystone_client, parse_host=True):
    public_endpoint = keystone_client.service_catalog.get_endpoints(service_type='identity')['identity'][0]['publicURL']
    if parse_host:
        return _parse_url_to_host(public_endpoint)
    else:
        return public_endpoint 

class KeystoneBackend(object):
    """
    Django authentication backend class for use with ``django.contrib.auth``.
    """
    def __init__(self):
        pass
    
    def get_user(self, user_id):
        """
        Returns the current user (if authenticated) based on the user ID
        and session data.

        Note: this required monkey-patching the ``contrib.auth`` middleware
        to make the ``request`` object available to the auth backend class.
        """
        if user_id == self.request.session["user_id"]:
            token = Token(TokenManager(None),
                          self.request.session['token'],
                          loaded=True)
            endpoint = self.request.session['region_endpoint']
            return create_user_from_token(self.request, token, endpoint)
        else:
            return None

    #@havclient.timeout(15)
    def authenticate(self, username=None, password=None,
                     tenant=None, auth_url=None, otp=None):
        """ Authenticates a user via the Keystone Identity API. """
        LOG.debug('Beginning user authentication for user "%s".' % username)

        insecure = False

        try:
            client = keystone_client.Client(username=username,
                                            password=password,
                                            tenant_id=tenant,
                                            auth_url=auth_url,
                                            insecure=insecure,
                                            timeout=8)
        except (keystone_exceptions.Unauthorized,
                keystone_exceptions.Forbidden,
                keystone_exceptions.NotFound) as exc:
            msg = ('Invalid user name or password.')
            LOG.debug(exc.message)
            return username, u'Invalid'

        except (keystone_exceptions.ClientException,
                keystone_exceptions.AuthorizationFailure) as exc:
            msg = ("An error occurred authenticating. "
                    "Please try again later.")
            #if u'Authorization Failed: InvalidResponse' == exc.args[0]:
            #    print exc.args[0]
            LOG.debug(exc.message)
            return username, u'IPError'

        try:
            tenants = client.tenants.list()
        except (keystone_exceptions.ClientException,
                keystone_exceptions.AuthorizationFailure):
            msg = ('Unable to retrieve authorized projects.')

        if not tenants:
            msg = ('You are not authorized for any projects.')
        alltoken={}
        alltoken.clear()
        while tenants:
            tenant = tenants.pop()
            try:
                token = client.tokens.authenticate(username=username,
                                                    password=password,
                                                    tenant_id=tenant.id) 
                alltoken[tenant.id]=token
            except (keystone_exceptions.ClientException,
                    keystone_exceptions.AuthorizationFailure):
                token = None

        if token is None:
            msg = ("Unable to authenticate to any available projects.")

        user = create_user_from_token(token,
                                      client.auth_url, alltoken, client)
        LOG.debug('Authentication completed for user "%s".' % username)
        return user, u'' 

    def get_group_permissions(self, user, obj=None):
        """ Returns an empty set since Keystone doesn't support "groups". """
        return set()

    def get_all_permissions(self, user, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        Keystone "roles".

        The permissions are returned as ``"openstack.{{ role.name }}"``.
        """
        if user.is_anonymous() or obj is not None:
            return set()
        role_perms = set(["openstack.roles.%s" % role['name'].lower()
                          for role in user.roles])
        service_perms = set(["openstack.services.%s" % service['type'].lower()
                          for service in user.service_catalog])
        return role_perms | service_perms

    def has_perm(self, user, perm, obj=None):
        """ Returns True if the given user has the specified permission. """
        if not user.is_active:
            return False
        return perm in self.get_all_permissions(user, obj)

    def has_module_perms(self, user, app_label):
        """
        Returns True if user has any permissions in the given app_label.

        Currently this matches for the app_label ``"openstack"``.
        """
        if not user.is_active:
            return False
        for perm in self.get_all_permissions(user):
            if perm[:perm.index('.')] == app_label:
                return True
        return False
