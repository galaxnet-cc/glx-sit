from cgi import test
import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D


class TestRestVppConsistency1DBasic(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_multi_bridge(self):
        self.topo.dut1.get_rest_device().create_bridge("test", "192.168.89.1/24")
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("up" in out)
        glx_assert("192.168.89.1/24" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-test")
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" in out)
        # update bridge
        self.topo.dut1.get_rest_device().update_bridge_ip("test", "192.168.90.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("up" in out)
        glx_assert("192.168.89.1/24" not in out)
        glx_assert("192.168.90.1/24" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-test")
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" not in out)
        glx_assert("192.168.90.1/24" in out)

        self.topo.dut1.get_rest_device().delete_bridge("test")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("up" not in out)
        glx_assert("192.168.90.1/24" not in out)
        # linux side if have been removed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip link")
        glx_assert(err == '')
        glx_assert("br-test" not in out)

    def get_bd_id(self, ssh_device, bridge_name):
        out, err = ssh_device.get_cmd_result(f"redis-cli hget BridgeIdContext#{bridge_name} BdId")
        glx_assert(err == '')
        out = out.rstrip()
        out.replace('"', '')
        return out

    def test_physical_interface(self):
        # 验证mtu属性更新(routed only)
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        self.topo.dut1.get_rest_device().create_bridge("test", "192.168.89.1/24")
        self.topo.dut1.get_rest_device().create_bridge("test23", "192.168.90.1/24")
        self.topo.dut1.get_rest_device().update_physical_interface("WAN2", 1600, "routed", "")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("1600/0/0/0" in out)

        # change mode to switched
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1600, "switched", "test")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        bd_id = self.get_bd_id(self.topo.dut1.get_vpp_ssh_device(), "test")
        glx_assert(f"bridge bd-id {bd_id}" in out)
        # check host side
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr")
        glx_assert(err == '')
        glx_assert("WAN2" not in out)
        # change bridge
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "switched", "test23")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int {wan2VppIf}")
        glx_assert(err == '')
        # when change to bridge, the mtu will be keeped, we do not
        # apply mtu for bridged interface.
        glx_assert("1600/0/0/0" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        bd_id = self.get_bd_id(self.topo.dut1.get_vpp_ssh_device(), "test23")
        glx_assert(f"bridge bd-id {bd_id}" in out)

        # check ip address set on logical interface when it's underlying physical
        # interface under switched mode is not allowed.
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.1.1/24")
        # this should be failed with 500.
        glx_assert(result.status_code == 500)

        # change to routed（此时OverlayEnable将关闭）
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "routed", "")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("bridge" not in out)
        # check host side
        # 因为OverlayEnable关闭，所以在ctrl-ns(segment 0)中。
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr")
        glx_assert(err == '')
        glx_assert("WAN2" in out)
        self.topo.dut1.get_rest_device().delete_bridge("test")
        self.topo.dut1.get_rest_device().delete_bridge("test23")

        # check ip address set on logical interface is ok
        expectedIp = "192.168.1.1/24"
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", expectedIp)
        glx_assert(result.status_code != 500)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert(expectedIp in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        glx_assert(err == '')
        glx_assert(expectedIp in out)
        # change back to dhcp mode.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert(expectedIp not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        glx_assert(err == '')
        glx_assert(expectedIp not in out)

        # 验证重新打开OverlayEnable（需要先置unspec），成为出厂默认配置
        result = self.topo.dut1.get_rest_device().set_logical_interface_unspec("WAN2")
        glx_assert(result.status_code != 500)
        result = self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN2", True)
        glx_assert(result.status_code != 500)
        # 切换至独立ctrl-ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip link")
        glx_assert(err == '')
        glx_assert('WAN2' in out)


    def test_static_property_update(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.2.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)

        # set gw.
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "192.168.2.254")
        tableId, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show  int addr {wan1VppIf} | grep ip4 | awk '{{print $5}}'")
        glx_assert(err == '')
        tableId = tableId.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table {tableId} 0.0.0.0/0")
        glx_assert(err == '')
        glx_assert("192.168.2.254" in out)
        # kernel side.
        # 0815: WAN gw route not programmed to kernel now.
        # out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
        #     f"ip netns exec ctrl-ns ip route show default")
        # glx_assert(err == '')
        # glx_assert("192.168.2.254" in out)
        # update gw.
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "192.168.2.252")
        tableId, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show  int addr {wan1VppIf} | grep ip4 | awk '{{print $5}}'")
        glx_assert(err == '')
        tableId = tableId.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table {tableId} 0.0.0.0/0")
        glx_assert(err == '')
        glx_assert("192.168.2.254" not in out)
        glx_assert("192.168.2.252" in out)
        # 0815: WAN gw route not programmed to kernel now.
        # # kernel side.
        # out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
        #     f"ip netns exec ctrl-ns ip route show default")
        # glx_assert(err == '')
        # glx_assert("192.168.2.254" not in out)
        # glx_assert("192.168.2.252" in out)

        # change back to dhcp.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)

    def test_pppoe_property_update(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        # check kernel using correct user and password.
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /tmp/glx-pppd-cfg-WAN1")
        glx_assert(err == '')
        glx_assert(f"test" in out)
        glx_assert(f'123456' in out)
        # get orig pid.
        pid1, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /var/run/glx-pppd-WAN1.pid")
        glx_assert(err == '')
        glx_assert(pid1 != "")

        # update user and password.
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "hahaha", "654321")
        # check kernel using correct user and password.
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /tmp/glx-pppd-cfg-WAN1")
        glx_assert(err == '')
        glx_assert(f'hahaha' in out)
        glx_assert(f'654321' in out)
        # get new pid.
        pid2, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /var/run/glx-pppd-WAN1.pid")
        glx_assert(err == '')
        glx_assert(pid2 != "")
        # pid should changed to take effect of new auth info.
        glx_assert(pid1 != pid2)

        # change back to dhcp.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)

    def test_multi_wan_address_type_switch(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        # change address type to static from static
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.2/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.2/24" in out)
        glx_assert("192.168.2.1/24" not in out)

        # change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.3/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.3/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)

        # change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)
        glx_assert("pppox1" in out)
        # try to add address to pppoe interface to simulate pppoe
        # sync ip from kernel.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address pppox0 1.1.1.1/32")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address pppox1 1.1.1.2/32")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address del pppox0 1.1.1.1/32")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address del pppox1 1.1.1.2/32")
        glx_assert(err == '')

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        glx_assert("192.168.1.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        glx_assert("192.168.1.3/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.4/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        glx_assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.4/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        glx_assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" not in out)
        glx_assert("pppox1" not in out)

        # change to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert(f'{wan2VppIf}' in out)

        # change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)
        glx_assert("pppox1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' not in out)
        glx_assert(f'{wan2VppIf}' not in out)

        # change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" not in out)
        glx_assert("pppox1" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" in out)

    def test_change_address_type_to_static_from_static(self):
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check logical interface using static address type
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        # change ip and verify again
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)

        # test_change_address_type_to_dhcp_from_static
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)

        # test_change_address_type_to_static_from_dhcp
        # change address to static
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.3/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)

        # test_change_address_type_to_pppoe_from_static
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)

        # test_change_address_type_to_static_from_pppoe
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.4/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        # check if pppoe related configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ps -ef | grep ppp")
        glx_assert(err == '')

        # test change address type to dhcp from pppoe
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        # change to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox" not in out)

        # test_change_address_type_to_pppoe_from_dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" not in out)

        # recovery to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")

    def test_firewall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl3", 3, "192.168.11.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("test_acl3" in out)
        glx_assert("192.168.11.2/32" in out)
        # update
        self.topo.dut1.get_rest_device().update_fire_wall_rule(
            "test_acl3", 3, "192.168.12.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("192.168.12.2/32" in out)
        glx_assert("192.168.11.2/32" not in out)
        # delete
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("test_acl3" not in out)
        glx_assert("192.168.12.2/32" not in out)

    def test_multi_firewall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl3", 3, "192.168.11.3/32", "Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl5", 5, "192.168.11.5/32", "Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl4", 4, "192.168.11.4/32", "Deny")
        # We now apply firewall and bizpol to segment loop.
        # Use redis to get default segment's loop.
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                    f"redis-cli hget SegmentContext#0 LoopSwIfIndex")
        glx_assert(err == '')
        ifindex = ifindex.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show acl-plugin interface sw_if_index {ifindex} acl")
        glx_assert(err == '')
        pos3 = out.index('192.168.11.3')
        pos4 = out.index('192.168.11.4')
        pos5 = out.index('192.168.11.5')
        glx_assert(pos5 < pos4 < pos3)
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl4")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl5")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("test_acl3" not in out)
        glx_assert("test_acl4" not in out)
        glx_assert("test_acl5" not in out)

    def test_host_stack_dnsmasq(self):
        # set a false dhcp router, check if it can be reconfigured
        options=[
            {"OptionCode": 3, "OptionValue": "192.168.88"}
        ]
        result=self.topo.dut1.get_rest_device().set_host_stack_dnsmasq(name="default", start_ip="192.168.88.50", 
                                                                  ip_num=101, lease_time="12h", dns_server1="8.8.8.8", 
                                                                  acc_domain_list="a.b.c", local_domain_list="x.y.z", 
                                                                  dhcp_enable=True, options=options)
        glx_assert(result.status_code == 500)
        # check if config file exists
        options=[
            {"OptionCode": 3, "OptionValue": "192.168.88.1"}, {"OptionCode": 6, "OptionValue": "8.8.8.8"}
        ]
        result=self.topo.dut1.get_rest_device().set_host_stack_dnsmasq(name="default", start_ip="192.168.88.50", 
                                                                  ip_num=101, lease_time="12h", dns_server1="8.8.8.8", 
                                                                  acc_domain_list="a.b.c", local_domain_list="x.y.z", 
                                                                  dhcp_enable=True, options=options)
        glx_assert(result.status_code == 201)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /var/run")
        glx_assert(err == '')
        glx_assert("glx_dnsmasq_default.pid" in out)
        glx_assert("glx_dnsmasq_base_default.conf" in out)
        glx_assert("glx_dnsmasq_dhcp_default.conf" in out)
        glx_assert("glx_dnsmasq_dns_default.conf" in out)
        glx_assert("glx_dnsmasq_dhcp_default.leases" in out)
        # check conf
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /var/run/glx_dnsmasq_base_default.conf")
        glx_assert(err == '')
        glx_assert("conf-file=/var/run/glx_dnsmasq_dhcp_default.conf" in out)
        glx_assert("conf-file=/var/run/glx_dnsmasq_dns_default.conf" not in out)
        glx_assert("server=8.8.8.8" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /var/run/glx_dnsmasq_dhcp_default.conf")
        glx_assert(err == '')
        glx_assert("dhcp-range=192.168.88.50,192.168.88.150,255.255.255.0,12h" in out)
        glx_assert("dhcp-option=6,8.8.8.8" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /var/run/glx_dnsmasq_dns_default.conf")
        glx_assert(err == '')
        glx_assert("/a.b.c/acc" in out)
        glx_assert("/x.y.z/local" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert("/var/run/glx_dnsmasq_base_default.conf" in out)

        # update
        options=[
            {"OptionCode": 3, "OptionValue": "192.168.88.1"}, {"OptionCode": 6, "OptionValue": "114.114.114.114"}
        ]
        result = self.topo.dut1.get_rest_device().update_host_stack_dnsmasq(name="default", start_ip="192.168.88.100",
                                                                   ip_num=101, lease_time="12h", 
                                                                   local_dns_server_enable=True, options=options)
        glx_assert(result.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /var/run")
        glx_assert(err == '')
        glx_assert("glx_dnsmasq_default.pid" in out)
        glx_assert("glx_dnsmasq_base_default.conf" in out)
        glx_assert("glx_dnsmasq_dhcp_default.conf" in out)
        glx_assert("glx_dnsmasq_dns_default.conf" in out)
        glx_assert("glx_dnsmasq_dhcp_default.leases" in out)
        # check conf
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /var/run/glx_dnsmasq_base_default.conf")
        glx_assert(err == '')
        glx_assert("conf-file=/var/run/glx_dnsmasq_dhcp_default.conf" not in out)
        glx_assert("conf-file=/var/run/glx_dnsmasq_dns_default.conf" in out)
        glx_assert("server=8.8.8.8" not in out)
        # 192.168.88.1 is bvi ip address
        glx_assert("dhcp-option=6,192.168.88.1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /var/run/glx_dnsmasq_dhcp_default.conf")
        glx_assert(err == '')
        glx_assert("dhcp-range=192.168.88.50,192.168.88.150,255.255.255.0,12h" not in out)
        glx_assert("dhcp-range=192.168.88.100,192.168.88.200,255.255.255.0,12h" in out)
        glx_assert("dhcp-option=6,114.114.114.114" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /var/run/glx_dnsmasq_dns_default.conf")
        glx_assert(err == '')
        glx_assert("/a.b.c/acc" not in out)
        glx_assert("/x.y.z/local" not in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert("/var/run/glx_dnsmasq_base_default.conf" in out)

        # delete and verify
        self.topo.dut1.get_rest_device().delete_host_stack_dnsmasq("default")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /var/run")
        glx_assert(err == '')
        glx_assert("glx_dnsmasq_default.pid" not in out)
        glx_assert("glx_dnsmasq_base_default.conf" not in out)
        glx_assert("glx_dnsmasq_dhcp_default.conf" not in out)
        glx_assert("glx_dnsmasq_dns_default.conf" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert("/var/run/glx_dnsmasq_base_default.conf" not in out)

    def test_bridge(self):
        # Add new ip address
        self.topo.dut1.get_rest_device().update_bridge_ip("default", "192.168.1.1/24")
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-default")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        # update and verify
        self.topo.dut1.get_rest_device().update_bridge_ip("default", "192.168.1.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-default")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)

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
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" in out)
        glx_assert("192.168.88.1/24" not in out)

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
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" not in out)
        glx_assert("192.168.88.1/24" in out)

    def test_multi_segment(self):
        # create segment
        # change LAN1 to routed
        # set LAN1 to segment because it's address will be in UNSPEC mode.
        # (TODO): currently not supported. check LAN1 in seperate linux-ns
        # try delete segment, it will be blocked due to have reference.
        self.topo.dut1.get_rest_device().create_segment(1)
        self.topo.dut1.get_rest_device().update_physical_interface("LAN1", 1500, "routed", "")
        self.topo.dut1.get_rest_device().set_logical_interface_segment("LAN1", 1)
        result = self.topo.dut1.get_rest_device().delete_segment(1)
        # this should be failed with 500 because there are reference to the segment.
        glx_assert(result.status_code == 500)

        # change back to the segment 0
        self.topo.dut1.get_rest_device().set_logical_interface_segment("LAN1", 0)
        result = self.topo.dut1.get_rest_device().delete_segment(1)
        # this should be ok with 410 (http StatusGone)
        glx_assert(result.status_code == 410)
        # check back to switched interface.
        self.topo.dut1.get_rest_device().update_physical_interface("LAN1", 1500, "switched", "default")
