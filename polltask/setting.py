#-*- coding: utf-8 -*-

SUPPORT_TASK_TYPE = ['standalone', 'subwsgi']

DEFAULT_DISK_LABEL = 'gpt'

AUTO_GENERATE_POOL_NAME_NUMBER = 5
ZFS_CONFIG = '/etc/modprobe.d/zfs.conf'
ZFS_POOL_NAME_PREFIX = "pool.zfs."
DEFAULT_ZFS_LOG_CACHE_RATE = "1:9"
DEFAULT_ZFS_RAID_TYPE = "raidz"
DEFAULT_ZFS_POOL_MOUNT_POINT = '/accelerated-data'
ZFS_CREATE_STATE = {'create.start': 'create.start',
                    'create.storage': 'create.storage',
                    'create.accelerate': 'create.accelerate',
                    'create.cache': 'create.cache',
                    'create.log': 'create.log',
                    'create.mem_cache': 'create.mem_cache',
                    'create.used_openstack': 'create.used_openstack',
                    'create.end': 'create.end',
                    'create.success': 'success',
                    'create.error': 'error'}

RC_LOCAL_PATH = "/etc/rc.d/rc.local"

DEFAULT_SSH_KEY_DIR = "~/.ssh"
DEFAULT_SSH_KEY_NAME = 'id_rsa'
DEFAULT_SSH_KEY_TYPE = 'rsa'
DEFAULT_SSH_KEY_CONFIG_NAME = 'config'

DEFAULT_DOMAIN_NAME = 'localdomain'
