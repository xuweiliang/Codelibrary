#-*- coding: utf8 -*-
import json
import copy

from utils import generate_uuid_str

def get_ovs_port_interface_uuid(ssh, port):
    cmd = ("ovsdb-client transact "
            "'[\"Open_vSwitch\","
            "{\"op\":\"select\", \"table\":\"Port\","
            " \"columns\":[\"interfaces\"],"
            "\"where\":[[\"name\", \"==\", \"%s\"]]}]'" % port)
    out = ssh.send_expect(cmd, "# ")

    out = json.loads(out)
    intf_uuids = []
    if out[0]['rows']:
        uuids = out[0]['rows'][0]['interfaces'][1:][0]
        for uuid in uuids:
            intf_uuids.append(uuid[1])

    return intf_uuids

def get_ovs_all_interface_uuid(ssh):
    cmd = ("ovsdb-client transact "
            "'[\"Open_vSwitch\","
            "{\"op\":\"select\", \"table\":\"Interface\","
            " \"columns\":[\"_uuid\",\"name\"],"
            "\"where\":[]}]'")
    out = ssh.send_expect(cmd, "# ")

    out = json.loads(out)

    intf_map_uuid = {}
    uuid_intfs = out[0]['rows']
    if uuid_intfs:
        for uuid_intf in uuid_intfs:
            uuid = uuid_intf['_uuid'][-1]
            intf = uuid_intf['name']
            intf_map_uuid[intf] = uuid

    return intf_map_uuid

def add_interface_to_port(ssh, port, *interfaces):
    insert_template = ("{\"row\":{\"name\":\"%(intf)s\"},\"table\":\"Interface\","
                       "\"uuid-name\":\"%(uuid_name)s\",\"op\":\"insert\"}")

    update_template = ("{\"row\":{\"interfaces\":[\"set\",[%(uuid)s]]},\"table\":\"Port\","
                        "\"where\":[[\"name\",\"==\",\"%(name)s\"]],\"op\":\"update\"}")

    uuid_template = "[\"uuid\", \"%s\"]"
    uuid_name_template = "[\"named-uuid\", \"%s\"]"

    intf_uuid_list = get_ovs_port_interface_uuid(ssh, port)
    
    cmd_list = []
    intf_uuid_name_list = [] 
    for interface in interfaces:
        uuid_name = generate_uuid_str('row') 
        insert_cmd = insert_template % {'intf':interface, 'uuid_name':uuid_name}
        intf_uuid_name_list.append(uuid_name)
        cmd_list.append(insert_cmd)

    uuid_set_list = []
    for uuid in intf_uuid_list:
        uuid_set = uuid_template % uuid
        uuid_set_list.append(uuid_set)
    for uuid_name in intf_uuid_name_list:
        uuid_name_set = uuid_name_template % uuid_name
        uuid_set_list.append(uuid_name_set)

    uuid_set_str = ','.join(uuid_set_list)
    update_cmd = update_template % {'uuid': uuid_set_str, 'name': port}

    cmd_list.append(update_cmd)
    cmd_str = ','.join(cmd_list)

    cmd = "ovsdb-client transact '[\"Open_vSwitch\", %s]'" % cmd_str
    ssh.send_expect(cmd, '# ')

def remove_interface_to_port(ssh, port, *interfaces):
    delete_template = ("{\"table\":\"Interface\","
                       "\"where\":[%(condition)s],\"op\":\"delete\"}")

    update_template = ("{\"row\":{\"interfaces\":[\"set\",[%(uuid)s]]},\"table\":\"Port\","
                        "\"where\":[[\"name\",\"==\",\"%(name)s\"]],\"op\":\"update\"}")

    uuid_template = "[\"uuid\", \"%s\"]"
    del_cond_template = "[\"name\",\"==\",\"%s\"]"

    intf_uuid_list = get_ovs_port_interface_uuid(ssh, port)

    intf_map_uuid = get_ovs_all_interface_uuid(ssh)

    del_intf = []
    # 这个remd_intf用来做策略判断，因为bond设备最少需要2个interface
    remd_intf_uuid = copy.copy(intf_uuid_list)
    for intf in interfaces:
        if (intf in intf_map_uuid.keys() and 
            intf_map_uuid[intf] in intf_uuid_list):
            del_intf.append(intf)
            remd_intf_uuid.remove(intf_map_uuid[intf])

    if len(remd_intf_uuid) < 2 and len(remd_intf_uuid) > 0:
        raise Exception("Bond device need two interfaces at least!")

    cmd_list = []

    del_cond_list = []
    for intf in del_intf:
        del_cond_str = del_cond_template % intf
        del_cond_list.append(del_cond_str)
    del_cond_str = ','.join(del_cond_list)
    delete_cmd = delete_template % {'condition': del_cond_str}

    cmd_list.append(delete_cmd)

    uuid_set_list = []
    for uuid in remd_intf_uuid:
        uuid_set = uuid_template % uuid
        uuid_set_list.append(uuid_set)

    uuid_set_str = ','.join(uuid_set_list)
    update_cmd = update_template % {'uuid': uuid_set_str, 'name': port}

    cmd_list.append(update_cmd)
    cmd_str = ','.join(cmd_list)

    cmd = "ovsdb-client transact '[\"Open_vSwitch\", %s]'" % cmd_str
    ssh.send_expect(cmd, '# ')

if __name__ == "__main__":
    from ssh_connection import SSHConnection

    ssh = SSHConnection('192.168.8.103', 'root', '111111')
    all_intf_uuid = get_ovs_all_interface_uuid(ssh)
    print "All interface uuids: ", all_intf_uuid
    ports = get_ovs_port_interface_uuid(ssh, 'bond0')
    print "ports uuid are: ", ports          
    add_interface_to_port(ssh, 'bond0', *['eth1'])
    interfaces = ssh.send_expect("ovsdb-client transact '[\"Open_vSwitch\", {\"op\":\"select\", \"table\":\"Interface\", \"columns\":[\"name\"], \"where\":[]}]'", '# ')
    print "Now interfaces: ", interfaces
    remove_interface_to_port(ssh, 'bond0', *['eth1'])
    interfaces = ssh.send_expect("ovsdb-client transact '[\"Open_vSwitch\", {\"op\":\"select\", \"table\":\"Interface\", \"columns\":[\"name\"], \"where\":[]}]'", '# ')
    print "Now interfaces: ", interfaces
