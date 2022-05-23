# 办公室物理实验拓朴，文档如下：
# https://docs.google.com/document/d/1lGOlfb6dCZOyAk1Jy4y5zA6ELY_Qwutrf3fDUbSycUc/edit#

import os

from lib.local_device import LocalDevice
from lib.ssh_device import SSHDevice
from lib.rest_device import RestDevice

class Topo1T4D:
    def __init__(self):
        # TODO: 搞一个文件来加载这些IP，以方便基于虚拟机快速搭建另外一台测试环境。
        self.dut1 = RestDevice(api_ip="192.168.31.234")
        self.dut2 = RestDevice(api_ip="192.168.31.113")
        self.dut3 = RestDevice(api_ip="192.168.31.186")
        self.dut4 = RestDevice(api_ip="192.168.31.133")
        # TODO: if1/if2也需要配置文件化，本拓朴中if1固定接入dut1，if2固定接入dut2。
        self.tst = SSHDevice(server="192.168.31.218", user="root", password="OBCubuntuD102", if1="eth2", if2="eth3")
