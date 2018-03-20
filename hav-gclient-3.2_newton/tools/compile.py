#!/usr/bin/env python
# coding=utf8
'''
Created on Jul 7, 2012

@author: gf
'''
import sys
import compileall

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage Error'
        print sys.argv[0], ' <directory>'
        sys.exit(0)
    
    compileall.compile_dir(sys.argv[1])
    
    
    