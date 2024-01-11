import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DBasicMultiSegment(unittest.TestCase):

    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_delete_non_default_segment_with_relation(self):
        # delete non default segment with bizpol
        self.topo.dut1.get_rest_device().create_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)
        self.topo.dut1.get_rest_device().create_bizpol(segment=1, name="bizpol1", priority=1,
                                                       src_prefix="1.1.1.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0)

        resp = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(resp.status_code != 410)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        resp = self.topo.dut1.get_rest_device().delete_bizpol(segment=1, name="bizpol1")
        glx_assert(resp.status_code == 410)
        self.topo.dut1.get_rest_device().delete_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" not in out)

        # delete non default segment with firewall
        self.topo.dut1.get_rest_device().create_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)
        self.topo.dut1.get_rest_device().set_fire_wall_rule(segment=1, rule_name="fwrule1", priority=1,
                                                            dest_address="0.0.0.0/0", action="Deny")

        resp = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(resp.status_code != 410)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        resp = self.topo.dut1.get_rest_device().delete_fire_wall_rule(segment=1, rule_name="fwrule1")
        glx_assert(resp.status_code == 410)
        self.topo.dut1.get_rest_device().delete_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" not in out)

        # delete non default segment with edgeroute
        self.topo.dut1.get_rest_device().create_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)
        self.topo.dut1.get_rest_device().create_edge_route(segment=1, route_prefix="2.2.2.2/32", route_label="0x222")

        resp = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(resp.status_code != 410)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        resp = self.topo.dut1.get_rest_device().delete_edge_route(segment=1, route_prefix="2.2.2.2/32")
        glx_assert(resp.status_code == 410)
        self.topo.dut1.get_rest_device().delete_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" not in out)

        # delete non default segment with interface
        self.topo.dut1.get_rest_device().create_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        self.topo.dut1.get_rest_device().set_logical_interface_unspec(name="WAN1")
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct(name="WAN1", nat_direct_enable=False)
        self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable(name="WAN1", overlay_enable=False)
        self.topo.dut1.get_rest_device().set_logical_interface_segment(name="WAN1", segment_id=1)
        
        resp = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(resp.status_code != 410)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        self.topo.dut1.get_rest_device().set_logical_interface_segment(name="WAN1", segment_id=0)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct(name="WAN1", nat_direct_enable=True)
        self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable(name="WAN1", overlay_enable=True)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp(name="WAN1")

        self.topo.dut1.get_rest_device().delete_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" not in out)

        # delete non default segment with segment properties
        self.topo.dut1.get_rest_device().create_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)
        self.topo.dut1.get_rest_device().create_segment_prop(segment_id=1)

        resp = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(resp.status_code != 410)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        resp = self.topo.dut1.get_rest_device().delete_segment_prop(segment_id=1)
        glx_assert(resp.status_code == 410)
        self.topo.dut1.get_rest_device().delete_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" not in out)

    def test_non_default_segment_recover(self):
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns delete ctrl-ns-seg-1")
        
        self.topo.dut1.get_rest_device().create_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        # 创建segment 1 properties
        self.topo.dut1.get_rest_device().create_segment_prop(segment_id=1, ip1="1.1.1.1")
        
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns-seg-1 ip addr")
        glx_assert(err == "")
        glx_assert("1.1.1.1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 1")
        glx_assert(err == "")
        glx_assert("1.1.1.1" in out)

        # 重启vpp
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("systemctl restart vpp")
        glx_assert(err == "")
        time.sleep(15)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns-seg-1 ip addr")
        glx_assert(err == "")
        glx_assert("1.1.1.1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 1")
        glx_assert(err == "")
        glx_assert("1.1.1.1" in out)

        # 删除segment 1 properties
        self.topo.dut1.get_rest_device().delete_segment_prop(segment_id=1)
        
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns-seg-1 ip addr")
        glx_assert(err == "")
        glx_assert("1.1.1.1" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 1")
        glx_assert(err == "")
        glx_assert("1.1.1.1" not in out)

        # 删除segment 1
        self.topo.dut1.get_rest_device().delete_segment(1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" not in out)

    def test_no_to_update_return_status_code_ok(self):
        self.topo.dut1.get_rest_device().create_segment(segment_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("segment-id [1] configed" in out)

        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=1, route_label="")
        glx_assert(resp.status_code == 200)

        self.topo.dut1.get_rest_device().delete_segment(segment_id=1)


        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, tag1="kk")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)

        data={}
        data["IgnoreNotSpecifiedTable"] = True
        linkTable = {}
        linkTable["Table"] = "Link"
        link1 = {}
        link1["LinkId"] = 1
        link1["Tag1"] = "kkkk"
        linkTable["Items"] = []
        linkTable["Items"].append(link1)
        data["Tables"] = []
        data["Tables"].append(linkTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data)
        glx_assert(resp.status_code == 200)

        data={}
        data["IgnoreNotSpecifiedTable"] = True
        linkTable = {}
        linkTable["Table"] = "Link"
        link1 = {}
        link1["LinkId"] = 1
        link1["Tag1"] = "kkkk"
        linkTable["Items"] = []
        linkTable["Items"].append(link1)
        data["Tables"] = []
        data["Tables"].append(linkTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data)
        glx_assert(resp.status_code == 200)

        self.topo.dut1.get_rest_device().delete_glx_link(1)
