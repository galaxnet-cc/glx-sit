from cgi import test
import unittest
import time

from topo.topo_1d import Topo1D


class TestRestVppConsistency1DDynRouting(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_ospf(self):
        # set LAN1 to routed mode.
        self.topo.dut1.get_rest_device().update_physical_interface(
            "LAN1", 1500, "routed", "")
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("LAN1", "192.168.1.1/24")

        # create default seg ospf.
        areas = [
            {"AreaId": 1}
        ]
        self.topo.dut1.get_rest_device().create_ospf_setting(areas=areas)
        self.topo.dut1.get_rest_device().create_ospf_interface("LAN1", 1)

        # Wait for ospf config applied because the ospf interface is applied
        # async and it may still checking readiness of ospfd status.
        time.sleep(10)

        # verify ospf is enabled on the interface.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "show ip ospf interface"')
        assert(err == '')
        assert("LAN1 is up" in out)

        # delete default seg ospf.
        self.topo.dut1.get_rest_device().delete_ospf_interface("LAN1", 1)
        self.topo.dut1.get_rest_device().delete_ospf_setting()

        # verify ospf is not enabled on the interface.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "show ip ospf interface"')
        assert('ospfd is not running' in err)
        assert("LAN1 is up" not in out)
        # verify ospf is stopped.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "show ip ospf"')
        assert('ospfd is not running' in err)
        assert("" == out)

        # revert back to bridged mode.
        result = self.topo.dut1.get_rest_device().update_physical_interface(
            "LAN1", 1500, "switched", "default")
