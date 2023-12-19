# 说明：这里定义基于ssh的device，以实现基于ssh的管理。
# 可以使用paramiko这个库
import paramiko
import os

class SSHDevice:
    def __init__(self, server, user, password, if1, if2, if3=None, if4=None, if5=None):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(server, username=user, password=password)
        self.if1 = if1
        self.if2 = if2
        self.if3 = if3
        self.if4 = if4
        self.if5 = if5

    def add_ns(self, ns_name):
        out, err = self.get_cmd_result(f'ip netns add {ns_name}')
        if err != "":
            return out, err
        return self.get_cmd_result(f'ip netns exec {ns_name} ip link set lo up')

    def del_ns(self, ns_name):
        return self.get_cmd_result(f'ip netns delete {ns_name}')

    def add_if_to_ns(self, if_name, ns_name):
        _, err = self.get_cmd_result(f'ip link show {if_name}')
        # 如果在默认ns，就移动到目标ns
        if err == '':
            out, err = self.get_cmd_result(f'ip link set {if_name} netns {ns_name}')
            if err != "":
                return out, err
<<<<<<< HEAD
=======
        out, err = self.get_ns_cmd_result(ns_name, f'ip link set {if_name} up')
        if err != "":
            return out, err
>>>>>>> d2aca84 ([glx-sit] move interface into default ns when tear down)
        # lqk
        # Flush the bvi's old mac address which was cached in ARP cache, because when we have done a factory init request,
        # we will regenerate a new mac address to bvi.
        return self.get_ns_cmd_result(ns_name, f'ip neigh flush dev {if_name}')

    def add_ns_if_to_default_ns(self, src_ns, if_name):
        self.get_ns_cmd_result(src_ns, f"ip link set {if_name} netns 1")
        self.get_cmd_result(f"ip link set {if_name} up")
        # lqk
        # Flush the bvi's old mac address which was cached in ARP cache, because when we have done a factory init request,
        # we will regenerate a new mac address to bvi.
        self.get_cmd_result(f"ip neigh flush dev {if_name}")

    def del_if(self, name):
        return self.get_cmd_result(f'ip link del {name}')

    def add_br(self, br_name):
        return self.get_cmd_result(f'brctl addbr {br_name}')

    def add_br_to_ns(self,ns_name, br_name):
        return self.get_ns_cmd_result(ns_name, f'brctl addbr {br_name}')

    def add_br_if(self, br_name, if_name):
        return self.get_cmd_result(f'brctl addif {br_name} {if_name}')

    def add_ns_br_if(self, ns_name, br_name, if_name):
        return self.get_ns_cmd_result(ns_name, f'brctl addif {br_name} {if_name}')

    def del_br(self, br_name):
        return self.get_cmd_result(f'brctl delbr {br_name}')

    def del_ns_br(self, ns_name, br_name):
        return self.get_ns_cmd_result(ns_name, f'brctl delbr {br_name}')

    def del_br_if(self, br_name):
        return self.get_cmd_result(f'brctl delbr {br_name}')

    def del_ns_br_if(self, ns_name, br_name, if_name):
        return self.get_ns_cmd_result(ns_name, f'brctl delif {br_name} {if_name}')

    def add_if_ip(self, if_name, ip_with_prefix):
        return self.get_cmd_result(f'ip addr add {ip_with_prefix} dev {if_name}')

    def add_if_ip6(self, if_name, ip_with_prefix):
        return self.get_cmd_result(f'ip -6 addr add {ip_with_prefix} dev {if_name}')

    def add_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        return self.get_ns_cmd_result(ns_name, f'ip addr add {ip_with_prefix} dev {if_name}')

    def add_ns_if_ip6(self, ns_name, if_name, ip_with_prefix):
        return self.get_ns_cmd_result(ns_name, f"ip -6 addr add {ip_with_prefix} dev {if_name}")

    def del_if_ip(self, if_name, ip_with_prefix):
        return self.get_cmd_result(f'ip addr del {ip_with_prefix} dev {if_name}')

    def del_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        return self.get_ns_cmd_result(ns_name, f'ip addr del {ip_with_prefix} dev {if_name}')

    def up_down_if(self, if_name:str, is_up:bool):
        state = 'up' if is_up else 'down'
        return self.get_cmd_result(f'ip link set dev {if_name} {state}')

    def ns_up_down_if(self, ns_name, if_name:str, is_up:bool):
        state = 'up' if is_up else 'down'
        return self.get_ns_cmd_result(ns_name, f"ip link set dev {if_name} {state}")

    def add_route(self, route_prefix, nexthop_ip):
        return self.get_cmd_result(f'ip route replace {route_prefix} via {nexthop_ip}')

    def add_ns_route(self, ns_name, route_prefix, nexthop_ip):
        return self.get_ns_cmd_result(ns_name, f'ip route replace {route_prefix} via {nexthop_ip}')

    def add_ip6_route(self, route_prefix, nexthop_ip):
        return self.get_cmd_result(f'ip -6 route replace {route_prefix} via {nexthop_ip}')

    def add_ns_ip6_route(self, ns_name, route_prefix, nexthop_ip):
        return self.get_ns_cmd_result(ns_name, f'ip -6 route replace {route_prefix} via {nexthop_ip}')

    def del_route(self, route_prefix, nexthop_ip):
        return self.get_cmd_result(f'ip route del {route_prefix} via {nexthop_ip}')

    def del_ip6_route(self, route_prefix, nexthop_ip):
        return self.get_cmd_result(f'ip -6 route del {route_prefix} via {nexthop_ip}')

    def del_ns_ip6_route(self, ns_name, route_prefix, nexthop_ip):
        return self.get_ns_cmd_result(ns_name, f'ip -6 route del {route_prefix} via {nexthop_ip}')

    def del_ns_route(self, ns_name, route_prefix, nexthop_ip):
        return self.get_ns_cmd_result(ns_name, f'ip route del {route_prefix} via {nexthop_ip}')

    def get_cmd_result(self, cmd):
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd)
        return ssh_stdout.read().decode(), ssh_stderr.read().decode()

    def get_ns_cmd_result(self, ns_name, cmd):
        shell_cmd = f'ip netns exec {ns_name} {cmd}'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(shell_cmd)
        return ssh_stdout.read().decode(), ssh_stderr.read().decode()
