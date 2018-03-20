#!/usr/bin/env python

class ConsoleInfo:
    def __init__(self,console_dict):
        self.type = console_dict['type']
        self.port = console_dict['port']
        self.tlsport = console_dict['tlsport']
        self.host = console_dict['host']
