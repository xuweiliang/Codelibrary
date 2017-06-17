# coding=utf-8

from oslo_config import cfg

addr = cfg.StrOpt("addrip",
                  default="http://%s:8099",
                  help="This is the client addrip")
CONF=cfg.CONF
CONF.register_opt(addr)

