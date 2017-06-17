from polltaskclient.openstack.common.gettextutils import _
#from polltaskclient import Logger as LOG
from polltaskclient import exc
import six
import json
#import logging
from oslo_log import log as logging
LOG=logging.getLogger(__name__)
def getid(obj):
    """
    Abstracts the common pattern of allowing both an object or an object's ID
    as a parameter when dealing with relationships.
    """
    try:
        return obj.id
    except AttributeError:
        return obj

class Resource(object):
    def __init__(self, manager=None, info=None):
        self.manager=manager
        self.info=info
        self._add_details(info)

    def _add_details(self, info):
        for k, v in six.iteritems(info):
            setattr(self, k, v)
    
    def _get_attr(self, name): 
        try:
            return getattr(self, name)
        except Exception:
            raise AttributeError(name)

#    def __repr__(self):
#        reprkeys = sorted(k
#                          for k in self.__dict__.keys()
#                          if k[0] != '_' and k != 'manager')
#        info = ", ".join("%s=%s" % (k, getattr(self, k)) for k in reprkeys)
#        return "<%s %s>" % (self.__class__.__name__, info)

    def __repr__(self):
        return "<%s:%s>" % (self.__class__.name, self.info)


class BassManager(object):
    resource_class=None
    def __init__(self, client):
        self.client=client

    def _get(self, url, id=0):
        try:
            body = self.client.get(url, params={"id":id}).json()
            if body:
                data = body.pop()
                obj = self.resource_class(self, data)
                return obj
            return body
        except Exception:
            message=_("Connection server error")
            raise exc.HTTPInternalServerError(message=message)

    def _list(self, url):
        objlist=[]
        try:
            body = self.client.get(url).json()
            for obj in body:
                data = self.resource_class(self, obj)
                objlist.append(data)
            return objlist
        except Exception:
            message=_("Connection server error")
            raise exc.HTTPInternalServerError(message=message)

    def _delete(self, url, id=0):
        try:
            _body = self.client.delete(url, params={"id": id}).json()
            return _body
        except:
            return False
        
    def _action(self, url, id=None):
        try:
            _body = self.client.get(url, params={"id":json.dumps(id)}).json()
            return _body
        except Exception:
            message=_("Connection server error")
            raise exc.HTTPInternalServerError(message=message) 


    def _post(self, url, body=None):
        try:
            _body = self.client.post(url, params=body)
            return _body
        except Exception:
            message=_("Connection server error")
            raise exc.HTTPInternalServerError(message=message)
