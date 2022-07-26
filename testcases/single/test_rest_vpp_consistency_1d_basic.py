from cgi import test
import unittest
import time

from topo.topo_1d import Topo1D


class TestRestVppConsistency1DBasic(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_multi_bridge(self):
        self.topo.dut1.get_rest_device().set_bridge_ip("test", "192.168.89.1/24")
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        assert(err == '')
        assert("up" in out)
        assert("192.168.89.1/24" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr | grep bridge2")
        assert(err == '')
        assert("192.168.89.1/24" in out)
        # update bridge
        self.topo.dut1.get_rest_device().update_bridge_ip("test", "192.168.90.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        assert(err == '')
        assert("up" in out)
        assert("192.168.89.1/24" not in out)
        assert("192.168.90.1/24" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr | grep bridge2")
        assert(err == '')
        assert("192.168.89.1/24" not in out)
        assert("192.168.90.1/24" in out)
        # delete bridge
        self.topo.dut1.get_rest_device().delete_bridge_ip("test", "192.168.90.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        assert(err == '')
        assert("up" not in out)
        assert("192.168.90.1/24" not in out)

    def get_bd_id(self, ssh_device, bridge_name):
        out, err = ssh_device.get_cmd_result(f"redis-cli hget BridgeIdContext#{bridge_name} BdId")
        assert(err == '')
        out = out.rstrip()
        out.replace('"', '')
        return out

    def test_physical_interface(self):
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        self.topo.dut1.get_rest_device().set_bridge_ip("test", "192.168.89.1/24")
        self.topo.dut1.get_rest_device().set_bridge_ip("test23", "192.168.90.1/24")
        self.topo.dut1.get_rest_device().update_physical_interface("WAN2", 1600, "routed", "")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int {wan2VppIf}")
        assert(err == '')
        assert("1600/0/0/0" in out)

        # change mode to switched
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1600, "switched", "test")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        bd_id = self.get_bd_id(self.topo.dut1.get_vpp_ssh_device(), "test")
        assert(f"bridge bd-id {bd_id}" in out)
        # check host side
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr")
        assert(err == '')
        assert("WAN2" not in out)
        # change bridge
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "switched", "test23")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int {wan2VppIf}")
        assert(err == '')
        # when change to bridge, the mtu will be keeped, we do not
        # apply mtu for bridged interface.
        assert("1600/0/0/0" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        bd_id = self.get_bd_id(self.topo.dut1.get_vpp_ssh_device(), "test23")
        assert(f"bridge bd-id {bd_id}" in out)

        # check ip address set on logical interface when it's underlying physical
        # interface under switched mode is not allowed.
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.1.1/24")
        # this should be failed with 500.
        assert(result.status_code == 500)

        # change to routed
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "routed", "")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("bridge" not in out)
        # check host side
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr")
        assert(err == '')
        assert("WAN2" in out)
        self.topo.dut1.get_rest_device().delete_bridge_ip("test", "192.168.89.1/24")
        self.topo.dut1.get_rest_device().delete_bridge_ip("test23", "192.168.90.1/24")

        # check ip address set on logical interface is ok
        expectedIp = "192.168.1.1/24"
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", expectedIp)
        assert(result.status_code != 500)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert(expectedIp in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert(expectedIp in out)
        # change back to dhcp mode.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert(expectedIp not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert(expectedIp not in out)

    def test_static_property_update(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" in out)

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.2.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.2.1/24" in out)

        # set gw.
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "192.168.2.254")
        tableId, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show  int addr {wan1VppIf} | grep ip4 | awk '{{print $5}}'")
        assert(err == '')
        tableId = tableId.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table {tableId} 0.0.0.0/0")
        assert(err == '')
        assert("192.168.2.254" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip route show default")
        assert(err == '')
        assert("192.168.2.254" in out)
        # update gw.
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "192.168.2.252")
        tableId, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show  int addr {wan1VppIf} | grep ip4 | awk '{{print $5}}'")
        assert(err == '')
        tableId = tableId.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table {tableId} 0.0.0.0/0")
        assert(err == '')
        assert("192.168.2.254" not in out)
        assert("192.168.2.252" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip route show default")
        assert(err == '')
        assert("192.168.2.254" not in out)
        assert("192.168.2.252" in out)

        # change back to dhcp.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)

    def test_pppoe_property_update(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        # check kernel using correct user and password.
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /tmp/dsl-provider-WAN1")
        assert(err == '')
        assert(f"test" in out)
        assert(f'123456' in out)
        # get orig pid.
        pid1, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /var/run/glx-pppd-WAN1.pid")
        assert(err == '')
        assert(pid1 != "")

        # update user and password.
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "hahaha", "654321")
        # check kernel using correct user and password.
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /tmp/dsl-provider-WAN1")
        assert(err == '')
        assert(f'hahaha' in out)
        assert(f'654321' in out)
        # get new pid.
        pid2, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /var/run/glx-pppd-WAN1.pid")
        assert(err == '')
        assert(pid2 != "")
        # pid should changed to take effect of new auth info.
        assert(pid1 != pid2)

        # change back to dhcp.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)

    def test_multi_wan_address_type_translation(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        # change address type to static from static
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.2/24" in out)
        assert("192.168.2.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.2/24" in out)
        assert("192.168.2.1/24" not in out)

        # change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.3/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.3/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.3/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.3/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)

        # change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        assert("pppox1" in out)
        # try to add address to pppoe interface to simulate pppoe
        # sync ip from kernel.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address pppox0 1.1.1.1/32")
        assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address pppox1 1.1.1.2/32")
        assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address del pppox0 1.1.1.1/32")
        assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address del pppox1 1.1.1.2/32")
        assert(err == '')

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        assert("192.168.1.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        assert("192.168.1.3/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.4/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.4/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" not in out)
        assert("pppox1" not in out)

        # change to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert(f'{wan2VppIf}' in out)

        # change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        assert("pppox1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' not in out)
        assert(f'{wan2VppIf}' not in out)

        # change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" not in out)
        assert("pppox1" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" in out)

    def test_change_address_type_to_static_from_static(self):
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check logical interface using static address type
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        # change ip and verify again
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)

        # test_change_address_type_to_dhcp_from_static
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)

        # test_change_address_type_to_static_from_dhcp
        # change address to static
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.3/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.3/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.3/24" in out)

        # test_change_address_type_to_pppoe_from_static
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)

        # test_change_address_type_to_static_from_pppoe
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.4/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        # check if pppoe related configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep ppp")
        assert(err == '')

        # test change address type to dhcp from pppoe
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        # change to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox" not in out)

        # test_change_address_type_to_pppoe_from_dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" not in out)

        # recovery to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")

    def test_fire_wall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl3", 3, "192.168.11.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("test_acl3" in out)
        assert("192.168.11.2/32" in out)
        # update
        self.topo.dut1.get_rest_device().update_fire_wall_rule(
            "test_acl3", 3, "192.168.12.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("192.168.12.2/32" in out)
        assert("192.168.11.2/32" not in out)
        # delete
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("test_acl3" not in out)
        assert("192.168.12.2/32" not in out)

    def test_multi_fire_wall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl3", 3, "192.168.11.3/32", "Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl5", 5, "192.168.11.5/32", "Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl4", 4, "192.168.11.4/32", "Deny")
        # default bvi is loop0.
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int loop0 | grep loop0 | awk '{{print $2}}'")
        assert(err == '')
        ifindex = ifindex.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show acl-plugin interface sw_if_index {ifindex} acl")
        assert(err == '')
        pos3 = out.index('192.168.11.3')
        pos4 = out.index('192.168.11.4')
        pos5 = out.index('192.168.11.5')
        assert(pos5 < pos4 < pos3)
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl4")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl5")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("test_acl3" not in out)
        assert("test_acl4" not in out)
        assert("test_acl5" not in out)

    def test_host_stack_dnsmasq(self):
        # check if config file exists
        a=self.topo.dut1.get_rest_device().set_host_stack_dnsmasq("default", "255.255.255.0",
                                                                "192.168.88.50", "192.168.88.150", "12h")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /tmp")
        assert(err == '')
        assert("dnsmasq_default.pid" in out)
        assert("dnsmasq_dhcp_default.conf" in out)
        assert("dnsmasq_dhcp_default.leases" in out)
        # check conf
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /tmp/dnsmasq_dhcp_default.conf")
        assert(err == '')
        assert("dhcp-range=192.168.88.50,192.168.88.150,255.255.255.0,12h" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        assert(err == '')
        assert("/tmp/dnsmasq_dhcp_default.conf" in out)

        # update
        self.topo.dut1.get_rest_device().update_host_stack_dnsmasq("default", "255.255.255.0",
                                                                   "192.168.88.100", "192.168.88.150", "12h")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /tmp")
        assert(err == '')
        assert("dnsmasq_default.pid" in out)
        assert("dnsmasq_dhcp_default.conf" in out)
        assert("dnsmasq_dhcp_default.leases" in out)
        # check conf
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /tmp/dnsmasq_dhcp_default.conf")
        assert(err == '')
        assert("dhcp-range=192.168.88.50,192.168.88.150,255.255.255.0,12h" not in out)
        assert("dhcp-range=192.168.88.100,192.168.88.150,255.255.255.0,12h" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        assert(err == '')
        assert("/tmp/dnsmasq_dhcp_default.conf" in out)

        # delete and verify
        self.topo.dut1.get_rest_device().delete_host_stack_dnsmasq("default")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /tmp")
        assert(err == '')
        assert("dnsmasq_default.pid" not in out)
        assert("dnsmasq_dhcp_default.conf" not in out)
        assert("dnsmasq_dhcp_default.leases" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        assert(err == '')
        assert("/tmp/dnsmasq_dhcp_default.conf" not in out)

    def test_bridge(self):
        # Add new ip address
        self.topo.dut1.get_rest_device().update_bridge_ip("default", "192.168.1.1/24")
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show bridge1")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        # update and verify
        self.topo.dut1.get_rest_device().update_bridge_ip("default", "192.168.1.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show bridge1")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)

        # recovery ip address to 88.1
        self.topo.dut1.get_rest_device().update_bridge_ip("default", "192.168.88.1/24")

    # the interface is very generic so we only
    # test it works by some table.
    # Use BridgeTable because it do not depend on interface much.
    def test_update_config(self):
        data={}
        data["IgnoreNotSpecifiedTable"] = True
        bridgeTable = {}
        bridgeTable["Table"] = "Bridge"
        defBridge = {}
        defBridge["Name"] = "default"
        defBridge["BviEnable"] = True
        defBridge["BviIpAddrWithPrefix"] = "192.168.89.1/24"
        bridgeTable["Items"] = []
        bridgeTable["Items"].append(defBridge)
        data["Tables"] = []
        data["Tables"].append(bridgeTable)

        self.topo.dut1.get_rest_device().update_config_action(data)
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        assert(err == '')
        assert("192.168.89.1/24" in out)
        assert("192.168.88.1/24" not in out)

        # change back.
        data2 = {}
        data2["IgnoreNotSpecifiedTable"] = True
        bridgeTable2 = {}
        bridgeTable2["Table"] = "Bridge"
        defBridge2 = {}
        defBridge2["Name"] = "default"
        defBridge2["BviEnable"] = True
        defBridge2["BviIpAddrWithPrefix"] = "192.168.88.1/24"
        bridgeTable2["Items"] = []
        bridgeTable2["Items"].append(defBridge2)
        data2["Tables"] = []
        data2["Tables"].append(bridgeTable2)

        self.topo.dut1.get_rest_device().update_config_action(data2)
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        assert(err == '')
        assert("192.168.89.1/24" not in out)
        assert("192.168.88.1/24" in out)

    def test_multi_segment(self):
        # create segment
        # change LAN1 to routed
        # set LAN1 to segment because it's address will be in UNSPEC mode.
        # check LAN1 in seperate linux-ns
        # try delete segment, it will be blocked due to have reference.
        pass
