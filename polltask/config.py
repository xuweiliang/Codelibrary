#-*- coding: utf-8 -*-
import ConfigParser
import os


DEBUG_CONFIG = os.path.join(os.path.dirname(__file__), "../config", "poll_task.ini")
DEFAULT_CONFIG = os.path.join("/etc/polltask", "poll_task.ini")

class Config(object):
    def __init__(self, config_path, raise_if_no_config=True):
        self.config_path = config_path
        if not self._is_file_path():
            if raise_if_no_config:
                raise Exception("Configure [{0}] does not exist!!!".format(self.config_path))
            else:
                self._create_file(self.config_path)

        self.config = ConfigParser.ConfigParser()
        self.config.read(self.config_path)
        
    def _is_file_path(self):
        if os.path.isfile(self.config_path):
            return True
        else:
            return False

    def _create_file(self, f_path):
        with open(f_path, 'a+') as f:
            pass

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

    def add_section(self, section):
        self.config.add_section(section)

    def set_option_value(self, section, option, value):
        self.config.set(section, option, value)

    def remove_option(self, section, option):
        self.config.remove_option(section, option)

    def rewrite_config(self):
        with open(self.config_path, 'wb') as f:
            self.config.write(f)

    
def get_default_config():
    global DEFAULT_CONFIG
    config = Config(DEFAULT_CONFIG)
    return config

def get_debug_config():
    global DEBUG_CONFIG
    config = Config(DEBUG_CONFIG)
    return config

if __name__ == "__main__":
    default_config = get_default_config()
    print default_config.get_section_items('openstack_auth')
    print default_config.get_section_options('openstack_auth')
