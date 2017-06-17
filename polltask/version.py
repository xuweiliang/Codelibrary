#-*- coding: utf-8 -*-

POLLTASK_VENDOR = "Junesh"
POLLTASK_PRODUCT = "polltask"
POLLTASK_PACKAGE = None  # OS distro package version suffix

MAJOR = 0
MINOR = 3
REVISION = 2

RELEASE = '3'

loaded = False
version_string = '.'.join([str(MAJOR), str(MINOR), str(REVISION)])
version_info = '-'.join([POLLTASK_VENDOR, POLLTASK_PRODUCT, version_string])

def get_version_string():
    return version_string

def get_release_string():
    return RELEASE
