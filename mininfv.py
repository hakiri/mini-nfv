#!/usr/bin/python

# Author: Jose Castillo Lema <josecastillolema@gmail.com>
# Author: Alberico Castro <>

"Main module of the mini-nfv framework"

import sys
import netaddr
import yaml
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
# from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import OVSController
from mininet.node import RemoteController
from mininet.cli import CLI, output

MAX_VDUS = 100
VNFDS = {}
VNFS = []
HOSTS = []
SWITCH = {}
INC = 10

def parse_vnfd(path):
    "Parses the yaml file corresponding to the vnfd"
    try:
        yaml_file = open(path, 'r')
    except IOError:
        print 'File does not exist'
        return None
    content = yaml_file.read()
    parsed_file = yaml.load(content)
    return parsed_file['topology_template']['node_templates']

def parse_vnffgd(path):
    "Parses the yaml file corresponding to the vnffgd"
    return path

class MyTopo(Topo):
    "Creates the mininet topology"
    def __init__(self, **opts):
        Topo.__init__(self, **opts)

def configure_network(net, vnfd, host):
    "Configures the networks."
    i = 1
    switchs= []
    while vnfd.has_key('VL%s' % i):
        if vnfd['CP%s' % i]['properties'].has_key('ip_address'):
            ip_address = vnfd['CP%s' % i]['properties']['ip_address']
            switch_name = 's' + ip_address
            switchs.append(switch_name)
            if not SWITCH.has_key(switch_name):
                SWITCH[switch_name] = net.addSwitch(switch_name[:10])
        else:
            if vnfd['VL%s' % i]['properties']['network_name'] == 'net_mgmt':
                switch_name = 's' + '192.168.120.0'
                switchs.append(switch_name[:10])
                if not SWITCH.has_key(switch_name):
                    SWITCH[switch_name] = net.addSwitch(switch_name[:10])
            elif vnfd['VL%s' % i]['properties']['network_name'] == 'net0':
                switch_name = 's' + '10.10.0.0'
                switchs.append(switch_name[:10])
                if not SWITCH.has_key(switch_name):
                    SWITCH[switch_name] = net.addSwitch(switch_name[:10])
            elif vnfd['VL%s' % i]['properties']['network_name'] == 'net1':
                switch_name = 's' + '10.10.1.0'
                switchs.append(switch_name[:10])
                if not SWITCH.has_key(switch_name):
                    SWITCH[switch_name] = net.addSwitch(switch_name[:10])
            elif vnfd['VL%s' % i]['properties'].has_key('cidr'):
                cidr = netaddr.IPNetwork(vnfd['VL%s' % i]['properties']['cidr'])
                if vnfd['VL%s' % i]['properties'].has_key('start_ip'):
                    start_ip = netaddr.IPNetwork(vnfd['VL%s' % i]['properties']['start_ip'])
                    switch_name = 's%s' % start_ip.network
                    switchs.append(switch_name[:10])
                    if not SWITCH.has_key(switch_name):
                        SWITCH[switch_name] = net.addSwitch(switch_name[:10])
                else:
                    switch_name = 's%s' % cidr.ip
                    switchs.append(switch_name[:10])
                    if not SWITCH.has_key(switch_name):
                        SWITCH[switch_name] = net.addSwitch(switch_name[:10])
        i += 1

    host1 = net.getNodeByName(host)
    for i in switchs:
        net.addLink(i, host1)

def configure_host(net, vnfd, host):
    "Configures the host."
    host1 = net.getNodeByName(host)
    i = 1
    global INC
    while vnfd.has_key('VL%s' % i):
        if vnfd['CP%s' % i]['properties'].has_key('ip_address'):
            ip_address = vnfd['CP%s' % i]['properties']['ip_address']
            host1.setIP(ip_address, intf=host+'-eth%s' % (i-1))
        else:
            if vnfd['VL%s' % i]['properties']['network_name'] == 'net_mgmt':
                host1.setIP('192.168.120.%s' % INC + '/24', intf=host+'-eth%s' % (i-1))
                INC += 1
            elif vnfd['VL%s' % i]['properties']['network_name'] == 'net0':
                host1.setIP('10.10.0.%s' % INC+'/24', intf=host+'-eth%s' % (i-1))
                INC += 1
            elif vnfd['VL%s' % i]['properties']['network_name'] == 'net1':
                host1.setIP('10.10.1.%s'%INC+'/24', intf=host+'-eth%s' % (i-1))
                INC += 1
            elif vnfd['VL%s' % i]['properties'].has_key('cidr'):
                cidr = netaddr.IPNetwork(vnfd['VL%s' % i]['properties']['cidr'])
                if vnfd['VL%s' % i]['properties'].has_key('start_ip'):
                    start_ip = vnfd['VL%s' % i]['properties']['start_ip']
                    host1.setIP(start_ip+'/%s' % cidr.prefixlen, intf=host+'-eth%s' % (i-1))
                else:
                    host1.setIP(str(cidr.ip+INC)+'/%s' % cidr.prefixlen, intf=host+'-eth%s' % (i-1))
                    INC += 1
            else:
                host1.setIP('10.0.%s.%s/24' %(i, INC), intf=host+'-eth%s' % (i-1))
                INC += 1
        if vnfd['CP%s' % i]['properties'].has_key('mac_address'):
            mac_address = vnfd['CP%s' % i]['properties']['mac_address']
            host1.setMAC(mac_address, intf=host+'-eth%s' % (i-1))
        i += 1

def configure_host2(net, ips, host):
    "Configures the host."
    host1 = net.getNodeByName(host)
    for i in range(len(ips)):
        ip_address = netaddr.IPNetwork(ips[i])
        print ip_address.ip
        host1.setIP('%s' % ip_address.ip, intf=host+'-eth%s' % (i))

def add_host(self, line):
    "Adds a host to the mininet topology."
    net = self.mn
    if len(line.split()) < 1:
        output('Wrong number or arguments\n')
        output('Use: add_host <HOST-NAME> [<IP1/masc> <IP2/masc> ...]\n')
        return None
    host_name = line.split()[0]
    if host_name in HOSTS:
        output('<HOST-NAME> already in use\n')
        return None
    i = 1
    ips = line.split()[1:]
    switchs = []
    for i in ips:
        try:
            ip_address = netaddr.IPNetwork(i)
        except netaddr.core.AddrFormatError:
            output('IP format not valid: ' + i + '\n')
            output('Use: add_host <HOST-NAME> [<IP1/masc> <IP2/masc> ...]\n')
            return None
        switch_name = 's%s' % ip_address.network
        if not SWITCH.has_key(switch_name):
            SWITCH[switch_name] = net.addSwitch(switch_name[:10])
        switchs.append(switch_name)
    HOSTS.append(host_name)
    host = net.addHost(host_name)
    for i in switchs:
        net.addLink(i, host)
    configure_host2(net, ips, host_name)
    return None

def cloud_init(net, vnfd, host_name):
    "Configures the networks."
    host = net.getNodeByName(host_name)
    cloudinit = vnfd['VDU1']['properties']['user_data']
    output('*** Initializing VDU ' + host_name + ' ...\n')
    host.cmdPrint(cloudinit)

# VNFD

def vnfd_create(self, line):
    "Creates vnfd from template."
    net = self.mn
    if len(line.split()) != 3 or line.split()[0] != '--vnfd-file':
        output('Use: vnfd_create --vnfd-file <yaml file path> <VNFD-NAME>\n')
        return None
    file_path = line.split()[1]
    vnfd = parse_vnfd(file_path)
    if vnfd:
        vnfd_name = line.split()[2]
        if not VNFDS.has_key(vnfd_name):
            VNFDS[vnfd_name] = vnfd
        else:
            output('<VNFD-NAME> already in use\n')
    return None

def vnfd_list(self, line):
    "Lists all vnfds uploaded."
    if line:
        output('Use: vnfd_list\n')
        return None
    output('%s' % VNFDS.keys() + '\n')
    return None

def vnfd_delete(self, line):
    "Deletes a given vnfd."
    if len(line.split()) != 1:
        output('Use: vnfd_delete <VNFD-NAME>\n')
        return None
    vnfd_name = line.split()[0]
    if VNFDS.has_key(vnfd_name):
        del VNFDS[vnfd_name]
    else:
        output('<VNFD-NAME> does not exist\n')
    return None

def vnfd_template_show(self, line):
    "Shows the template of a given vnfd."
    if len(line.split()) != 1:
        output('Wrong number or arguments\n')
        output('Use: vnfd_template_show <VNFD-NAME>\n')
        return None
    vnfd_name = line.split()[0]
    output(('%s' % VNFDS[vnfd_name])+'\n')
    return None

# VNF

def vnf_create(self, line):
    "Creates vnf from vnfd previously created or directly from template."
    net = self.mn
    if len(line.split()) != 3 or line.split()[0] not in ['--vnfd-name', '--vnfd-file', '--vnfd-template']:
        output('Use: vnf_create --vnfd-name <VNFD-NAME> <VNF-NAME>\n')
        output('     vnf_create --vnfd-file <yaml file path> <VNFD-NAME>\n')
        output('     vnf_create --vnfd-template <yaml file path> <VNFD-NAME>\n')
        return None
    if line.split()[0] in ['--vnfd-file', '--vnfd-template']:
        file_path = line.split()[1]
        vnfd = parse_vnfd(file_path)
    else:  # --vnfd-name
        vnfd_name = line.split()[1]
        vnfd = VNFDS[vnfd_name]
    if vnfd:
        vnf_name = line.split()[2]
        if vnf_name in VNFS:
            output('<VNF-NAME> already in use\n')
            return None
        VNFS.append(vnf_name)
        net.addHost(vnf_name)
        configure_network(net, vnfd, vnf_name)
        configure_host(net, vnfd, vnf_name)
        if vnfd['VDU1']['properties'].has_key('user_data'):
            cloud_init(net, vnfd, vnf_name)
        return None
    return None

def vnf_list(self, line):
    "Lists all vnfs created."
    output('%s' % VNFS + '\n')

def vnf_delete(self, line):
    "Deletes a given vnf."
    net = self.mn
    if len(line.split()) != 1:
        output('Use: vnf_delete <VNF-NAME>\n')
        return None
    vnf_name = line.split()[0]
    if vnf_name in VNFS:
        del VNFS[VNFS.index(vnf_name)]
        # net.delNode(vnf_name)
        # AttributeError: 'Mininet' object has no attribute 'delNode'
    else:
        output('<VNF-NAME> does not exist\n')
    return None

if __name__ == '__main__':
    setLogLevel('info')
    if len(sys.argv) > 2:
        sys.exit('Uso: ./mininfv [--standalone]')
    elif len(sys.argv) == 2 and sys.argv[1] != '--standalone':
        sys.exit('Uso: ./mininfv [--standalone]')
    elif len(sys.argv) == 2 and sys.argv[1] == '--standalone':
        standalone = True
    else:
        standalone = False

    TOPO = MyTopo()
    # NET = Mininet(topo=topo, link=TCLink, controller=RemoteController)
    # NET = Mininet(topo=topo, link=TCLink)
    # NET = Mininet(topo=TOPO, link=TCLink, controller=OVSController)
    if standalone:
        NET = Mininet(link=TCLink, controller=OVSController)
    else:
        NET = Mininet(topo=TOPO, link=TCLink, controller=RemoteController)
    NET.start()
    CLI.do_add_host = add_host
    CLI.do_vnfd_create = vnfd_create
    CLI.do_vnfd_list = vnfd_list
    CLI.do_vnfd_delete = vnfd_delete
    CLI.do_vnfd_template_show = vnfd_template_show
    CLI.do_vnf_create = vnf_create
    CLI.do_vnf_list = vnf_list
    CLI.do_vnf_delete = vnf_delete
    CLI(NET)
    NET.stop()
