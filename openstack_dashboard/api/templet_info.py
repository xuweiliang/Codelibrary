from openstack_dashboard.api import base
from django.utils.translation import ugettext_lazy as _
import ConfigParser
import os, sys
import logging
LOG = logging.getLogger(__name__)

DEFAULT_CONFIG =os.path.join("/etc/polltask", "poll_task.ini")

class TempletInfo(object):
    def __init__(self, filename):
        self.filename=filename
        self.filter_info=[]

    def check_path(self):
        if os.path.exists(self.filename):
            return self.filename 
        else:
            return None

    def get_templet_info(self):
        infolist = []
        check_file=self.check_path()
        f=open(check_file, 'r')
        bufs= f.readlines()
        f.close()
        for line in bufs:
            print line
            splits = ''.join(line.split()).split(',')
            infolist.append(splits)
        for info in infolist:
            if 'name' in info:
                colname = info.index('name')
            if info[colname] and info[colname]!='name':
                self.filter_info.append(info)
        return self.filter_info

    def dispose_info(self):
        filter_info = self.get_templet_info()
        templet_info=[]
        for info in filter_info:
            instances={'swap':info[9], 'ephemeral_gb':info[8],
                       'root_gb':info[7], 'memory_mb':info[6],
                       'vcpus':info[5], 'flavors':info[4],
                       'count':info[3], 'user':info[2], 
                       'project':info[1],'name':info[0]}
            templet_info.append(instances)
        return templet_info

    def download_image(self, image, do_checksum):
        data = self.filename.images.data(image, do_checksum=do_checksum)
        return data


class Config(object):
    def __init__(self, config_path):
        if not config_path:
            mess=('not find config path')
            raise ValueError(mess) 
        self.config_path = config_path
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.config_path)

    def get_sections(self):
        return self.config.sections()
   
    def get_section_options(self, section):
        return self.config.options(section)

    def get_option_value(self, section, option):
        try:
            return self.config.get(section, option)
        except ConfigParser.NoOptionError as e:
            return None

    def get_section_items(self, section):
        return self.config.items(section)

class Url(Config):
    global DEFAULT_CONFIG
    def __init__(self, request):
        self.request=request
        super(Url, self).__init__(DEFAULT_CONFIG)
    
    def get_port(self):
        return self.get_option_value("WSGI", "device_port")

    def url_path(self):
        try:
            base_url = base.url_for(self.request, 'identity')
            port = self.get_port()
            url=base_url.split(':')
            if url:
                url.pop()
            url.append(port)
            return ':'.join(url)
        except Exception:
            raise Exception(_("Url Path Mosaic Error !"))
        

