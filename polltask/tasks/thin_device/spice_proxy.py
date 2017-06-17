import os 
import subprocess

default_path = os.path.join('/etc/squid', 'squid.conf')

class SpiceProxy(object):
    def __init__(self, port=None):
        self.port = port

    def read_config(self, pathfile):
        path= open(pathfile, 'r')
        bufs = path.readlines()
        path.close()
        yield bufs

    def save_file(self):
        data = self.read_config(default_path)
        content = data.next()
        fp = open(default_path, 'w')
        for line in content:
            if line.find("http_port") == 0:
                change = ''.join(['http_port', ' ', '%s', '\n'])
                fp.write(change % self.port)
            else:
                fp.write(line)
        fp.close() 

    def services(self, args=[]): 
        return subprocess.call(args, shell=False)

if __name__=='__main__':
    p = SpiceProxy('23456')
    print p.start_service()
    
