# 说明：这里定义基于ssh的device，以实现基于ssh的管理。
# 可以使用paramiko这个库
import paramiko
import os

class VppSSHDevice:
    def __init__(self, server, user, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        self.ssh.connect(server, username=user, password=password)

    def get_cmd_result(self, cmd):
        shell_cmd = f'{cmd}'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(shell_cmd)
        return ssh_stdout.read().decode().rstrip(), ssh_stderr.read().decode().rstrip()
    def get_ns_cmd_result(self, ns_name, cmd):
        shell_cmd = f'ip netns exec {ns_name} {cmd}'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(shell_cmd)
        return ssh_stdout.read().decode(), ssh_stderr.read().decode()
