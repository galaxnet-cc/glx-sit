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
        self.ssh.exec_command(f'ip netns add {ns_name}')
        self.ssh.exec_command(f'ip netns exec {ns_name} ip link set lo up')

    def add_if_to_ns(self, if_name, ns_name):
        self.ssh.exec_command(f'ip link set {if_name} netns {ns_name}')
        self.ssh.exec_command(f'ip netns exec {ns_name} ip link set {if_name} up')
        # lqk
        # Flush the bvi's old mac address which was cached in ARP cache, because when we have done a factory init request,
        # we will regenerate a new mac address to bvi.
        self.ssh.exec_command(f'ip netns exec {ns_name} ip neigh flush dev {if_name}')

    def add_ns_if_to_ns(self, src_ns, if_name, dst_ns):
        self.get_ns_cmd_result(src_ns, f"ip link set {if_name} netns {dst_ns}")
        self.get_ns_cmd_result(dst_ns, f"ip link set {if_name} up")
        # lqk
        # Flush the bvi's old mac address which was cached in ARP cache, because when we have done a factory init request,
        # we will regenerate a new mac address to bvi.
        self.get_ns_cmd_result(dst_ns, f"ip neigh flush dev {if_name}")

    def add_ns_if_to_default_ns(self, src_ns, if_name):
        self.get_ns_cmd_result(src_ns, f"ip link set {if_name} netns 1")
        self.get_cmd_result(f"ip link set {if_name} up")
        # lqk
        # Flush the bvi's old mac address which was cached in ARP cache, because when we have done a factory init request,
        # we will regenerate a new mac address to bvi.
        self.get_cmd_result(f"ip neigh flush dev {if_name}")

    def del_if(self, name):
        self.ssh.exec_command(f'ip link del {name}')

    def add_br(self, br_name):
        self.ssh.exec_command(f'brctl addbr {br_name}')

    def add_br_to_ns(self,ns_name, br_name):
        self.ssh.exec_command(f'ip netns exec {ns_name} brctl addbr {br_name}')

    def add_br_if(self, br_name, if_name):
        self.ssh.exec_command(f'brctl addif {br_name} {if_name}')

    def add_ns_br_if(self, br_name, if_name):
        self.ssh.exec_command(f'brctl addif {br_name} {if_name}')

    def del_br(self, br_name):
        self.ssh.exec_command(f'brctl delbr {br_name}')

    def del_ns_br(self,ns_name, br_name):
        self.ssh.exec_command(f'ip netns exec {ns_name} brctl delbr {br_name}')

    def del_br_if(self, br_name):
        self.ssh.exec_command(f'brctl delbr {br_name}')

    def del_ns_br_if(self, br_name, if_name):
        self.ssh.exec_command(f'brctl delif {br_name} {if_name}')

    def add_ns_br_if(self, br_name, if_name):
        self.ssh.exec_command(f'ip netns exec brctl addif {br_name} {if_name}')

    def add_br_to_ns(self,ns_name, br_name):
        self.ssh.exec_command(f'ip netns exec {ns_name} brctl addbr {br_name}')

    def add_if_ip(self, if_name, ip_with_prefix):
        self.ssh.exec_command(f'ip addr add {ip_with_prefix} dev  {if_name}')

    def add_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip addr add {ip_with_prefix} dev  {if_name}')

    def del_if_ip(self, if_name, ip_with_prefix):
        self.ssh.exec_command(f'ip addr del {ip_with_prefix} dev  {if_name}')

    def del_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip addr del {ip_with_prefix} dev  {if_name}')

    def up_down_if(self, if_name:str, is_up:bool):
        state = 'up' if is_up else 'down'
        self.ssh.exec_command(f'ip link set dev {if_name} {state}')

    def up_down_if(self, if_name:str, is_up:bool):
        state = 'up' if is_up else 'down'
        self.ssh.exec_command(f'ip link set dev {if_name} {state}')

    def add_route(self, route_prefix, nexthop_ip):
        self.ssh.exec_command(f'ip route replace {route_prefix} via {nexthop_ip}')

    def add_ns_route(self, ns_name, route_prefix, nexthop_ip):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip route replace {route_prefix} via {nexthop_ip}')

    def del_route(self, route_prefix, nexthop_ip):
        self.ssh.exec_command(f'ip route del {route_prefix} via {nexthop_ip}')

    def del_ns_route(self, ns_name, route_prefix, nexthop_ip):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip route del {route_prefix} via {nexthop_ip}')

    def get_cmd_result(self, cmd):
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd)
        return ssh_stdout.read().decode(), ssh_stderr.read().decode()

    def get_ns_cmd_result(self, ns_name, cmd):
        shell_cmd = f'ip netns exec {ns_name} {cmd}'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(shell_cmd)
        return ssh_stdout.read().decode(), ssh_stderr.read().decode()
