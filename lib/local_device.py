# 本地设备，一般指tst节点本身，这时候不需要远程执行。

import os

class LocalDevice:
    def __init__(self, if1, if2):
        self.if1 = if1
        self.if2 = if2

    def add_ns(self, ns_name):
        os.system(f'ip netns add {ns_name}')
        os.system(f'ip netns exec {ns_name} ip link set lo up')

    def add_if_to_ns(self, if_name, ns_name):
        os.system(f'ip link set {if_name} netns {ns_name}')
        os.system(f'ip netns exec {ns_name} ip link set {if_name} up')

    def add_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        os.system(f'ip netns exec {ns_name} ip addr add {ip_with_prefix} dev  {if_name}')

    def del_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        os.system(f'ip netns exec {ns_name} ip addr del {ip_with_prefix} dev  {if_name}')

    def add_ns_route(self, ns_name, route_prefix, nexthop_ip):
        os.system(f'ip netns exec {ns_name} ip route add {route_prefix} via {nexthop_ip}')

    def del_ns_route(self, ns_name, route_prefix, nexthop_ip):
        os.system(f'ip netns exec {ns_name} ip route del {route_prefix} via {nexthop_ip}')
