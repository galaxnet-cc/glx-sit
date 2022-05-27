import os
import json

from lib.dut import Dut
from lib.vpp_ssh_device import VppSSHDevice
from lib.rest_device import RestDevice

# 一个简单的单DUT测试，用于本地验证
class Topo1D:
    def __init__(self):
        sitconf = {}
        # 我们总在sit根目录下执行测试用例，这里是相对根目录的路径，而不是文件路径。
        with open('conf/sitconf.json') as f:
            sitconf = json.load(f)

        dut1conf = sitconf["Topos"]["Topo1D"]["Duts"]["DUT1"]
        self.dut1 = Dut("DUT1")
        self.dut1.set_if_map(dut1conf['IfMap'])
        self.dut1.set_rest_device(RestDevice(api_ip=dut1conf['MgmtIp']))
        self.dut1.set_vpp_ssh_device(VppSSHDevice(server=dut1conf['MgmtIp'],
                                                  user=dut1conf['SshUsername'],
                                                  password=dut1conf['SshPassword']))
