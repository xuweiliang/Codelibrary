import hashlib
import logging
import time
import re
from keystoneclient.v2_0 import tokens
from keystoneclient.v2_0 import client as keystone_client
from keystoneclient import exceptions as keystone_exceptions



from smtplib import SMTP

LOG = logging.getLogger(__name__)

def sendcode(emailfrom, emailto, passwd, msg):
    try :
        conn = SMTP("smtp.gmail.com",587)
        conn.ehlo()
        conn.starttls()
        conn.ehlo
        conn.login(emailfrom,passwd)
        message = "From: %s\nTo: %s\nSubject: %s\n\n%s" % (emailfrom, emailto, "Validation code", msg)
        conn.sendmail(emailfrom,emailto, message)
        conn.close()
    except Exception as err:
        pass

def set_session_from_user(request, user):
    
    if 'token_list' not in request.session:
        request.session['token_list'] = []
    token_tuple = (user.endpoint, user.token.id)
    request.session['token_list'].append(token_tuple)
    request.session['token'] = user.token._info
    request.session['user_id'] = user.id
    request.session['region_endpoint'] = user.endpoint
#    request.session['otp'] = user.otp

def create_user_from_token(token, endpoint, alltoken, client):
    return User(id=token.user['id'],
                username=token.user['name'],
                password=client.password,
                token=token,
                ksclient=client,
                tenant_id=token.tenant['id'],
                tenant_name=token.tenant['name'],
                enabled=True,
                service_catalog=token.serviceCatalog,
                roles=token.user['roles'],
                endpoint=endpoint,authorized_tenants=alltoken)

class User(object):
    """ A User class with some extra special sauce for Keystone.

    In addition to the standard Django user attributes, this class also has
    the following:

    .. attribute:: token

        The Keystone token object associated with the current user/tenant.

    .. attribute:: tenant_id

        The id of the Keystone tenant for the current user/token.

    .. attribute:: tenant_name

        The name of the Keystone tenant for the current user/token.

    .. attribute:: service_catalog

        The ``ServiceCatalog`` data returned by Keystone.

    .. attribute:: roles

        A list of dictionaries containing role names and ids as returned
        by Keystone.
    """
    def __init__(self, id=None, token=None, tenant_id=None, username=None, password=None,
                    service_catalog=None, tenant_name=None, roles=None, ksclient=None, auth_ok_time=None,
                    authorized_tenants=None, endpoint=None, enabled=False, life_time=None):
        self.id = id
        self.username=username
        self.password=password
        self.token= token
        self.ksclient = ksclient
        self.auth_ok_time = auth_ok_time or time.time()
        self.life_time = life_time or self._caculate_life_time()
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.service_catalog = service_catalog
        self.roles = roles or []
        self.endpoint = endpoint
        self.enabled = enabled
        self._authorized_tenants = authorized_tenants
#        self.otp = otp

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.username)

    def _caculate_life_time(self):
        def _translate(t):
            t = re.search(r'\d+-\d+-\d+T\d+:\d+:\d+', t).group()
            t_array = time.strptime(t, '%Y-%m-%dT%H:%M:%S')
            t_stamp = int(time.mktime(t_array))
            return t_stamp
        if self.token is None:
            return None
        if not isinstance(self.token, tokens.Token):
            raise Exception('') 
        issue = self.token.token['issued_at']
        expires = self.token.expires
        issue_stamp = _translate(issue)
        expires_stamp = _translate(expires)
        return (expires_stamp - issue_stamp)

    def is_token_expired(self):
        """
        Returns ``True`` if the token is expired, ``False`` if not, and
        ``None`` if there is no token set.
        """
        if self.token is None:
            return True

        if not isinstance(self.ksclient, keystone_client.Client):
            raise Exception('client is not the instance of keystoneclient.v2_0')
        if isinstance(self.token, tokens.Token):
            exist_time = time.time() - self.auth_ok_time
            if exist_time < self.life_time - 10:
                return False
            else:
                return True
        else:
            return True

    def is_authenticated(self):
        """ Checks for a valid token that has not yet expired. """
        pass
#    def print_otp(self):
#        return self.otp
#    def is_otp(self):
#        my_secret = 'MFRGGZDFMZTWQ2LK'
#        my_token = onetimepass.get_totp(my_secret)
#        sendcode('openstacktest@gmail.com','20082778@student.hut.edu.vn','1qa2ws3ed4',self.otp)
#        if onetimepass.valid_totp(token=self.otp, secret=my_secret):#
#	   return True
#	return False

    def is_anonymous(self):
        """
        Returns ``True`` if the user is not authenticated,``False`` otherwise.
        """
        return not self.is_authenticated()

    @property
    def is_active(self):
        return self.enabled

   # @property
    def is_superuser(self):
        """
        Evaluates whether this user has admin privileges. Returns
        ``True`` or ``False``.
        """
        return 'admin' in [role['name'].lower() for role in self.roles]

    @property
    def authorized_tenants(self):
        """ Returns a memoized list of tenants this user may access. """
        if self.is_authenticated() and self._authorized_tenants is None:
            endpoint = self.endpoint
            token = self.token
            try:
                client = keystone_client.Client(username=self.username,
                                                auth_url=endpoint,
                                                token=token.id)
                self._authorized_tenants = client.tenants.list()
            except (keystone_exceptions.ClientException,
                    keystone_exceptions.AuthorizationFailure):
                LOG.exception('Unable to retrieve tenant list.')
        return self._authorized_tenants or []

    @authorized_tenants.setter
    def authorized_tenants(self, tenant_list):
        self._authorized_tenants = tenant_list

    def save(*args, **kwargs):
        # Presume we can't write to Keystone.
        pass

    def delete(*args, **kwargs):
        # Presume we can't write to Keystone.
        pass
