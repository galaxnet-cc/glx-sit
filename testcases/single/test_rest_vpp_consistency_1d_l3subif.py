from cgi import test
import unittest
import time

from topo.topo_1d import Topo1D


# TODO:
# 1. 多segment场景下地址切换，此部分等多segment的ctrl-ns改造完成后再增加
#    当前仅测试vpp segment。
class TestRestVppConsistency1DL3SubIf(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_l3subif_crud(self):
        # create a sub if.
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN1", 100, 100)
        # should be ok to create a l3sub if.
        assert(result.status_code == 201)
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        # verify vpp side have a subif there.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int")
        assert(err == '')
        assert(f"{wan1VppIf}.100" in out)
        # verify host side interface lays in ctrl-ns (segment 0) because
        # l3sub if is created without OverlayEnable.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip link show WAN1.100")
        assert(err == '')
        assert("WAN1.100" in out)
        assert("UP" in out)

        # create a link using the l3sub if.
        result = self.topo.dut1.get_rest_device().create_glx_link(link_id=1, wan_name="WAN1.100")
        # should be ok to create a glx link over the l3sub if.
        assert(result.status_code == 201)

        # try remove the l3sub if.
        result = self.topo.dut1.get_rest_device().delete_l3subif("WAN1", 100)
        # should be failed because link refer to it.
        assert(result.status_code == 500)

        # delete the link.
        result = self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        # should be ok to create a glx link over the l3sub if.
        assert(result.status_code == 410)

        # delete the l3sub if again.
        result = self.topo.dut1.get_rest_device().delete_l3subif("WAN1", 100)
        # should be failed because link refer to it.
        assert(result.status_code == 410)

        # verify vpp side have a subif there.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int")
        assert(err == '')
        assert(f"{wan1VppIf}.100" not in out)
        # verify host side interface lays in ctrl-ns (segment 0) because
        # l3sub if is created without OverlayEnable.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip link show WAN1.100")
        assert(err != '')
        assert("WAN1.100" not in out)
        assert("UP" not in out)

    def test_l3subif_parent_if_routed_mode_constraints(self):
        # Parent is bridge mode, can't create sub if.
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "switched", "default")
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN2", 100, 100)
        # should not ok because violate constraints.
        assert(result.status_code == 500)

        # 改回routed.
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "routed", "")
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN2", 100, 100)
        # should ok
        assert(result.status_code == 201)

        # 尝试更改物理口为switched应当失败
        result = self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "switched", "default")
        assert(result.status_code == 500)

        # 删除subif.
        result = self.topo.dut1.get_rest_device().delete_l3subif("WAN2", 100)
        # should ok
        assert(result.status_code == 410)

        # 恢复WAN2的overlayEnable属性，避免影响其他用例
        result = self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN2", True)
        assert(result.status_code == 200)

    def test_l3subif_parent_if_vlan_id_constraints(self):
        # create a sub if.
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN1", 100, 100)
        # should be ok to create a l3sub if.
        assert(result.status_code == 201)

        # 复用同一vlan id，不被允许
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN1", 200, 100)
        # should be not ok.
        assert(result.status_code == 500)

        # delete the sub if.
        result = self.topo.dut1.get_rest_device().delete_l3subif("WAN1", 100)
        # should be ok to remove.
        assert(result.status_code == 410)

        # 现在将允许了
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN1", 200, 100)
        # should be not ok.
        assert(result.status_code == 201)

        # 清理
        result = self.topo.dut1.get_rest_device().delete_l3subif("WAN1", 200)
        # should be ok to remove.
        assert(result.status_code == 410)

    def test_l3subif_logif_addrmode_switch(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        # create the l3subif.
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN1", 100, 100)
        # should be ok to create a l3sub if.
        assert(result.status_code == 201)

        testIp = "1.1.1.1"

        # unspec->static.
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1.100", "1.1.1.1/24")
        assert(result.status_code == 200)
        # vpp side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}.100")
        assert(err == '')
        assert(testIp in out)
        # kernel side. (segment 0)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1.100")
        assert(err == '')
        assert(testIp in out)

        # static->dhcp.
        result = self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1.100")
        assert(result.status_code == 200)
        # vpp side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}.100")
        assert(err == '')
        assert(testIp not in out)
        # kernel side. (segment 0)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1.100")
        assert(err == '')
        assert(testIp not in out)

        # dhcp->unspec.
        result = self.topo.dut1.get_rest_device().set_logical_interface_unspec("WAN1.100")
        assert(result.status_code == 200)

        # enable overlay before enable pppoe
        result = self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN1.100", True)
        assert(result.status_code == 200)
        # unspec->pppoe
        result = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1.100", "test", "test")
        assert(result.status_code == 200)
        # vpp side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        # kernel side. (segment 0)
        # check kernel using correct user and password.
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /tmp/glx-pppd-cfg-WAN1.100")
        assert(err == '')
        assert(f"test" in out)
        assert(f'test' in out)
        # get orig pid.
        pid, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /var/run/glx-pppd-WAN1.100.pid")
        assert(err == '')
        assert(pid != "")

        # remove the l3subif.
        result = self.topo.dut1.get_rest_device().delete_l3subif("WAN1", 100)
        # should be ok to remove.
        assert(result.status_code == 410)

    def test_l3subif_logif_properties(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        # create the l3subif.
        result = self.topo.dut1.get_rest_device().create_l3subif("WAN1", 100, 100)
        # should be ok to create a l3sub if.
        assert(result.status_code == 201)

        # obtain the sub if sw if index.
        l3SubIfSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget VppIfIndexContext#WAN1.100 IfIndex")
        assert(err == '')

        # Enable NatDirectEnable. (default is False)
        result = self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1.100", True)
        assert(result.status_code == 200)
        # check vpps side.
        # glx nat-interface is configured.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        assert(err == '')
        assert(f"sw-if-index {l3SubIfSwIfIndex}" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show nat44 interfaces")
        assert(err == '')
        assert(f"{wan1VppIf}.100" in out)
        # disable nat.
        result = self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1.100", False)
        assert(result.status_code == 200)
        # check vpp side nat interface being deleted.
        # glx nat-interface is configured.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        assert(err == '')
        assert(f"sw-if-index {l3SubIfSwIfIndex}" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show nat44 interfaces")
        assert(err == '')
        assert(f"{wan1VppIf}.100" not in out)

        # Enable OverlayEnable.
        result = self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN1.100", True)
        assert(result.status_code == 200)
        # change ns is moved to dedicate ns.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1.100 ip link show WAN1.100")
        assert(err == '')
        assert("WAN1.100" in out)
        assert("UP" in out)

        # Disable OverlayEnable
        result = self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN1.100", False)
        assert(result.status_code == 200)
        # back to ctrl-ns (segment 0).
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip link show WAN1.100")
        assert(err == '')
        assert("WAN1.100" in out)
        assert("UP" in out)

        # Segment. (we should enable OverlayEnable & NatDirectEnable both is off).
        self.topo.dut1.get_rest_device().create_segment(1)
        self.topo.dut1.get_rest_device().set_logical_interface_segment("WAN1.100", 1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx interface-to-segment")
        assert(err == '')
        assert(f"sw-if-index [{l3SubIfSwIfIndex}] bound to segment-id [1]" in out)
        # back to segment 0.
        self.topo.dut1.get_rest_device().set_logical_interface_segment("WAN1.100", 0)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx interface-to-segment")
        assert(err == '')
        assert(f"sw-if-index [{l3SubIfSwIfIndex}] bound to segment-id [0]" in out)
        self.topo.dut1.get_rest_device().delete_segment(1)

        # remove the l3sub if.
        result = self.topo.dut1.get_rest_device().delete_l3subif("WAN1", 100)
        # should ok.
        assert(result.status_code == 410)


    def test_l3subif_phyif_propeties(self):
        # 暂时先不支持MTU更新，继承父接口即可，后续有需要再增加此功能。
        # 当前vpp
        pass
