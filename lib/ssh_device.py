# 说明：这里定义基于ssh的device，以实现基于ssh的管理。
# 可以使用paramiko这个库
import paramiko
import os

class SSHDevice:
    def __init__(self, server, user, password, if1, if2, if3=None, if4=None, if5=None):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
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

    def add_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip addr add {ip_with_prefix} dev  {if_name}')

    def del_ns_if_ip(self, ns_name, if_name, ip_with_prefix):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip addr del {ip_with_prefix} dev  {if_name}')

    def add_ns_route(self, ns_name, route_prefix, nexthop_ip):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip route add {route_prefix} via {nexthop_ip}')

    def del_ns_route(self, ns_name, route_prefix, nexthop_ip):
        self.ssh.exec_command(f'ip netns exec {ns_name} ip route del {route_prefix} via {nexthop_ip}')

    def get_ns_cmd_result(self, ns_name, cmd):
        shell_cmd = f'ip netns exec {ns_name} {cmd}'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(shell_cmd)
        return ssh_stdout.read().decode(), ssh_stderr.read().decode()
