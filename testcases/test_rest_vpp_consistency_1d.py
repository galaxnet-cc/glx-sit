import unittest
import time

from topo.topo_1d import Topo1D

class TestRestVppConsistency1D(unittest.TestCase):

    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_wan_object_ip_change(self):
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" in out)

        # 更改wan地址，验证变配成功
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.2.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        assert("192.168.1.1/24" not in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        assert("192.168.1.1/24" not in out)

        # 更改成dhcp模式
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        # no previous ip should be there.
        assert("192.168.2.1/24" not in out)
        assert("192.168.1.1/24" not in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        # BUG: https://github.com/galaxnet-cc/fwdmd/issues/24
        assert("192.168.2.1/24" not in out)
        assert("192.168.1.1/24" not in out)

    def test_wan_object_pppoe_switch(self):
        pass

if __name__ == '__main__':
    unittest.main()
