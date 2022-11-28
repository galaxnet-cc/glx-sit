# 办公室物理实验拓朴，文档如下：
# https://docs.google.com/document/d/1lGOlfb6dCZOyAk1Jy4y5zA6ELY_Qwutrf3fDUbSycUc/edit#

import os
import json

from lib.dut import Dut
from lib.local_device import LocalDevice
from lib.ssh_device import SSHDevice
from lib.vpp_ssh_device import VppSSHDevice
from lib.rest_device import RestDevice

class Topo1T4D:
    def __init__(self):
        self.sitconf = {}
        # 我们总在sit根目录下执行测试用例，这里是相对根目录的路径，而不是文件路径。
        with open('conf/sitconf.json') as f:
            self.sitconf = json.load(f)

        dutconf = self.sitconf["Topos"]["Topo1T4D"]["Duts"]["DUT1"]
        dut = Dut("DUT1")
        dut.set_if_map(dutconf['IfMap'])
        dut.set_rest_device(RestDevice(api_ip=dutconf['MgmtIp']))
        dut.set_vpp_ssh_device(VppSSHDevice(server=dutconf['MgmtIp'],
                                            user=dutconf['SshUsername'],
                                            password=dutconf['SshPassword']))
        self.dut1 = dut

        dutconf = self.sitconf["Topos"]["Topo1T4D"]["Duts"]["DUT2"]
        dut = Dut("DUT2")
        dut.set_if_map(dutconf['IfMap'])
        dut.set_rest_device(RestDevice(api_ip=dutconf['MgmtIp']))
        dut.set_vpp_ssh_device(VppSSHDevice(server=dutconf['MgmtIp'],
                                            user=dutconf['SshUsername'],
                                            password=dutconf['SshPassword']))
        self.dut2 = dut

        dutconf = self.sitconf["Topos"]["Topo1T4D"]["Duts"]["DUT3"]
        dut = Dut("DUT3")
        dut.set_if_map(dutconf['IfMap'])
        dut.set_rest_device(RestDevice(api_ip=dutconf['MgmtIp']))
        dut.set_vpp_ssh_device(VppSSHDevice(server=dutconf['MgmtIp'],
                                            user=dutconf['SshUsername'],
                                            password=dutconf['SshPassword']))
        self.dut3 = dut

        dutconf = self.sitconf["Topos"]["Topo1T4D"]["Duts"]["DUT4"]
        dut = Dut("DUT4")
        dut.set_if_map(dutconf['IfMap'])
        dut.set_rest_device(RestDevice(api_ip=dutconf['MgmtIp']))
        dut.set_vpp_ssh_device(VppSSHDevice(server=dutconf['MgmtIp'],
                                            user=dutconf['SshUsername'],
                                            password=dutconf['SshPassword']))
        self.dut4 = dut

        tstconf = self.sitconf["Topos"]["Topo1T4D"]["Tst"]
        self.tst = SSHDevice(server=tstconf['MgmtIp'],
                             user=tstconf['SshUsername'],
                             password=tstconf['SshPassword'],
                             if1=tstconf['LinuxIf1'],
                             if2=tstconf['LinuxIf2'],
                             if3=tstconf['LinuxIf3'],
                             if4=tstconf['LinuxIf4'])

    def have_pfsense(self):
        return self.sitconf["Topos"]["Topo1T4D"]["HavePfsense"]
