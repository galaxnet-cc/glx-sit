import unittest
import time
import json

from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DConfigureFilter(unittest.TestCase):

    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_get_configobjs_and_stateobjs_filter(self):
        # 创建link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010",
                                                         tag1="kk",
                                                         tag2="1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=2, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010",
                                                         tag1="kk",
                                                         tag2="2")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" in out)

        # 过滤得到link 1
        resp = self.topo.dut1.get_rest_device().do_get_configs_request("Link", filter="Filter[LinkId][eq]=1")
        glx_assert(resp.status_code == 200)
        data = json.loads(resp.text)
        glx_assert(data["ObjCount"] == 1)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 1)
        resp = self.topo.dut1.get_rest_device().do_get_states_request("Link", filter="Filter[LinkId][eq]=1")
        glx_assert(resp.status_code == 200)
        glx_assert(data["ObjCount"] == 1)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 1)


        # 过滤TunnelId为12, Tag1为kk
        resp = self.topo.dut1.get_rest_device().do_get_configs_request("Link", filter="Filter[TunnelId][eq]=12&Filter[Tag1][eq]=kk")
        glx_assert(resp.status_code == 200)
        data = json.loads(resp.text)
        glx_assert(data["ObjCount"] == 2)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 1)
        glx_assert(data["Objects"][1]["Object"]["LinkId"] == 2)
        resp = self.topo.dut1.get_rest_device().do_get_states_request("Link", filter="Filter[State][eq]=registering&Filter[TxBytes][eq]=0")
        glx_assert(resp.status_code == 200)
        glx_assert(data["ObjCount"] == 2)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 1)
        glx_assert(data["Objects"][1]["Object"]["LinkId"] == 2)

        # 过滤tag2为1, 得到link 1
        resp = self.topo.dut1.get_rest_device().do_get_configs_request("Link", filter="Filter[Tag2][eq]=1")
        glx_assert(resp.status_code == 200)
        data = json.loads(resp.text)
        glx_assert(data["ObjCount"] == 1)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 1)
        

        # 过滤为空，得到两条link
        resp = self.topo.dut1.get_rest_device().do_get_configs_request("Link", filter="")
        glx_assert(resp.status_code == 200)
        data = json.loads(resp.text)
        glx_assert(data["ObjCount"] == 2)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 1)
        glx_assert(data["Objects"][1]["Object"]["LinkId"] == 2)
        resp = self.topo.dut1.get_rest_device().do_get_states_request("Link", filter="")
        glx_assert(resp.status_code == 200)
        glx_assert(data["ObjCount"] == 2)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 1)
        glx_assert(data["Objects"][1]["Object"]["LinkId"] == 2)

        # 删除link 1
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)
        # config/state仅有link 2
        resp = self.topo.dut1.get_rest_device().do_get_configs_request("Link", filter="")
        glx_assert(resp.status_code == 200)
        data = json.loads(resp.text)
        glx_assert(data["ObjCount"] == 1)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 2)
        resp = self.topo.dut1.get_rest_device().do_get_states_request("Link", filter="")
        glx_assert(resp.status_code == 200)
        data = json.loads(resp.text)
        glx_assert(data["ObjCount"] == 1)
        glx_assert(data["Objects"][0]["Object"]["LinkId"] == 2)
        # 删除link 2
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=2)
        resp = self.topo.dut1.get_rest_device().do_get_configs_request("Link", filter="")
        glx_assert(resp.status_code == 200)
        data = json.loads(resp.text)
        glx_assert(data["ObjCount"] == 0)

    def test_update_tunnels_config_filter(self):
        # 过滤条件不生效，创建两个tunnel
        data1={}
        data1["IgnoreNotSpecifiedTable"] = True
        tunnelTable = {}
        tunnelTable["Table"] = "Tunnel"
        tunnelTable["Filters"] = "Filter[TunnelId][eq]=1"
        tunnel1 = {}
        tunnel1["TunnelId"] = 1
        tunnel1["SchedMode"] = ""
        tunnel1["BandwidthLimit"] = 0
        tunnel1["IsPassive"] = False
        tunnel1["Tag1"] = "k"
        tunnel1["Tag2"] = "emmm"
        tunnel2 = {}
        tunnel2["TunnelId"] = 2
        tunnel2["SchedMode"] = ""
        tunnel2["BandwidthLimit"] = 0
        tunnel2["IsPassive"] = False
        tunnel2["Tag1"] = "k"
        tunnel2["Tag2"] = "emmm"
        tunnel3 = {}
        tunnel3["TunnelId"] = 3
        tunnel3["SchedMode"] = ""
        tunnel3["BandwidthLimit"] = 0
        tunnel3["IsPassive"] = False
        tunnel3["Tag1"] = "k"
        tunnel3["Tag2"] = "emmm"
        tunnelTable["Items"] = []
        tunnelTable["Items"].append(tunnel1)
        tunnelTable["Items"].append(tunnel2)
        tunnelTable["Items"].append(tunnel3)
        data1["Tables"] = []
        data1["Tables"].append(tunnelTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data1)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert("tunnel-id 1" in out)
        glx_assert("tunnel-id 2" in out)
        glx_assert("tunnel-id 3" in out)
        

        # 更新过滤不生效，tunnel 1更新；删除过滤生效，只对tunnel 2进行删除
        data2={}
        data2["IgnoreNotSpecifiedTable"] = True
        tunnelTable = {}
        tunnelTable["Table"] = "Tunnel"
        tunnelTable["Filters"] = "Filter[Tag1][eq]=k&Filter[TunnelId][eq]=2"
        tunnel1 = {}
        tunnel1["TunnelId"] = 1
        tunnel1["SchedMode"] = ""
        tunnel1["BandwidthLimit"] = 0
        tunnel1["IsPassive"] = False
        tunnel1["Tag1"] = "kkkk"
        tunnel1["Tag2"] = "emmm"
        tunnelTable["Items"] = []
        tunnelTable["Items"].append(tunnel1)
        data2["Tables"] = []
        data2["Tables"].append(tunnelTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data2)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx tunnel | grep tunnel-id\ 2")
        glx_assert(err == '')
        glx_assert("tunnel-id 2" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx tunnel | grep tunnel-id\ 3")
        glx_assert(err == '')
        glx_assert("tunnel-id 3" in out)
        tag1, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Tunnel#1 Tag1")
        glx_assert(err == '')
        tag1 = tag1.rstrip()
        glx_assert("kkkk" == tag1)
        

        # 过滤条件为空，删除两条tunnel
        data3={}
        data3["IgnoreNotSpecifiedTable"] = True
        tunnelTable = {}
        tunnelTable["Table"] = "Tunnel"
        tunnelTable["Filters"] = ""
        tunnel2 = {}
        tunnel2["TunnelId"] = 2
        tunnel2["SchedMode"] = ""
        tunnel2["BandwidthLimit"] = 0
        tunnel2["IsPassive"] = False
        tunnel2["Tag1"] = "k"
        tunnel2["Tag2"] = "emmm"
        tunnelTable["Items"] = []
        tunnelTable["Items"].append(tunnel2)
        data3["Tables"] = []
        data3["Tables"].append(tunnelTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data3)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert("tunnel-id 1" not in out)
        glx_assert("tunnel-id 2" in out)
        glx_assert("tunnel-id 3" not in out)

        # 删除tunnel
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert("No glx tunnel configured" in out)

    def test_update_links_config_filter(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, tag1="kk")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=2, tag1="2")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" in out)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=3, tag1="kk")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 3" in out)

        # 更新过滤不生效，link 1更新；删除过滤生效，只对link 2进行删除
        data={}
        data["IgnoreNotSpecifiedTable"] = True
        linkTable = {}
        linkTable["Table"] = "Link"
        linkTable["Filters"] = "Filter[Tag1][eq]=2"
        link1 = {}
        link1["LinkId"] = 1
        link1["Tag1"] = "kkkk"
        linkTable["Items"] = []
        linkTable["Items"].append(link1)
        data["Tables"] = []
        data["Tables"].append(linkTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx link | grep link-id\ 2")
        glx_assert(err == '')
        glx_assert("link-id 2" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx link | grep link-id\ 3")
        glx_assert(err == '')
        glx_assert("link-id 3" in out)
        tag1, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Link#1 Tag1")
        glx_assert(err == '')
        tag1 = tag1.rstrip()
        glx_assert("kkkk" == tag1)

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=3)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx link")
        glx_assert(err == '')
        glx_assert("No glx link configured" in out)

    def test_update_edge_routes_config_filter(self):
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.1.1/32", route_label="0x111", tag1="kk")
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.1.2/32", route_label="0x222", tag1="2")
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.1.3/32", route_label="0x333", tag1="kk")

        # 更新过滤不生效， 1更新；删除过滤生效，只对 2进行删除
        data={}
        data["IgnoreNotSpecifiedTable"] = True
        edgerouteTable = {}
        edgerouteTable["Table"] = "EdgeRoute"
        edgerouteTable["Filters"] = "Filter[Tag1][eq]=2"
        edgeroute1 = {}
        edgeroute1["Segment"] = 0
        edgeroute1["DestPrefix"] = "192.168.1.1/32"
        edgeroute1["RouteProtocol"] = "overlay"
        edgeroute1["Tag1"] = "kkkk"
        edgerouteTable["Items"] = []
        edgerouteTable["Items"].append(edgeroute1)
        data["Tables"] = []
        data["Tables"].append(edgerouteTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "EdgeRoute#0#192.168.1.2/32#overlay"'
        )
        glx_assert (err == '')
        glx_assert (out == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "EdgeRoute#0#192.168.1.3/32#overlay"'
        )
        glx_assert (err == '')
        glx_assert (out != '')
        tag1, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget EdgeRoute#0#192.168.1.1/32#overlay Tag1")
        glx_assert(err == '')
        tag1 = tag1.rstrip()
        glx_assert("kkkk" == tag1)

        # 删除
        resp = self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="192.168.1.1/32")
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="192.168.1.3/32")
        glx_assert(resp.status_code == 410)

    def test_update_bizpols_config_filter(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="2.2.2.2/32",
                                                       protocol=0,
                                                       direct_enable=True,
                                                       tag1="kk")
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol2",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="2.2.2.2/32",
                                                       protocol=0,
                                                       direct_enable=True,
                                                       tag1="2")
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol3",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="2.2.2.2/32",
                                                       protocol=0,
                                                       direct_enable=True,
                                                       tag1="kk")                                                       

        # 更新过滤不生效， 1更新；删除过滤生效，只对 2进行删除
        data={}
        data["IgnoreNotSpecifiedTable"] = True
        bizpolTable = {}
        bizpolTable["Table"] = "BusinessPolicy"
        bizpolTable["Filters"] = "Filter[Tag1][eq]=2"
        bizpol1 = {}
        bizpol1["Name"] = "bizpol1"
        bizpol1["Segment"] = 0
        bizpol1["Tag1"] = "kkkk"
        bizpolTable["Items"] = []
        bizpolTable["Items"].append(bizpol1)
        data["Tables"] = []
        data["Tables"].append(bizpolTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "BusinessPolicy#0#bizpol2"'
        )
        glx_assert (err == '')
        glx_assert (out == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "BusinessPolicy#0#bizpol3"'
        )
        glx_assert (err == '')
        glx_assert (out != '')
        tag1, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BusinessPolicy#0#bizpol1 Tag1")
        glx_assert(err == '')
        tag1 = tag1.rstrip()
        glx_assert("kkkk" == tag1)

        # 删除
        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol3")
        glx_assert(resp.status_code == 410)

    def test_update_single_non_tag_field_by_action(self):
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x111")

        data={}
        data["IgnoreNotSpecifiedTable"] = True
        edgerouteTable = {}
        edgerouteTable["Table"] = "EdgeRoute"
        edgerouteTable["Filters"] = "Filter[DestPrefix][eq]=1.1.1.1/32"
        edgeroute1 = {}
        edgeroute1["Segment"] = 0
        edgeroute1["DestPrefix"] = "1.1.1.1/32"
        edgeroute1["RouteProtocol"] = "overlay"
        edgeroute1["RouteLabel"] = "0x222"
        edgerouteTable["Items"] = []
        edgerouteTable["Items"].append(edgeroute1)
        data["Tables"] = []
        data["Tables"].append(edgerouteTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data)
        glx_assert(resp.status_code == 200)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 | grep 1.1.1.1/32 -A 5")
        glx_assert(err == '')
        glx_assert("0x222" in out)
        glx_assert("0x111" not in out)

        # 删除
        resp = self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        glx_assert(resp.status_code == 410)

    def test_update_single_non_tag_field_by_api(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="1.1.1.1/32",
                                                       protocol=0,
                                                       direct_enable=True)

        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol1",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="2.2.2.2/32",
                                                       protocol=0,
                                                       direct_enable=True)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol")
        glx_assert(err == '')
        glx_assert(f"2.2.2.2/32" in out)
        glx_assert(f"1.1.1.1/32" not in out)

        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        glx_assert(resp.status_code == 410)

    def test_update_multi_tag_field(self):
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1, tag2="k")
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=2, tag2="k")
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=3, tag2="k")

        data1={}
        data1["IgnoreNotSpecifiedTable"] = True
        tunnelTable = {}
        tunnelTable["Table"] = "Tunnel"
        tunnelTable["Filters"] = "Filter[TunnelId][eq]=1"
        tunnel1 = {}
        tunnel1["TunnelId"] = 1
        tunnel1["SchedMode"] = ""
        tunnel1["BandwidthLimit"] = 0
        tunnel1["IsPassive"] = False
        tunnel1["Tag2"] = "emmm"
        tunnel2 = {}
        tunnel2["TunnelId"] = 2
        tunnel2["SchedMode"] = ""
        tunnel2["BandwidthLimit"] = 0
        tunnel2["IsPassive"] = False
        tunnel2["Tag2"] = "emmm"
        tunnel3 = {}
        tunnel3["TunnelId"] = 3
        tunnel3["SchedMode"] = ""
        tunnel3["BandwidthLimit"] = 0
        tunnel3["IsPassive"] = False
        tunnel3["Tag2"] = "emmm"
        tunnelTable["Items"] = []
        tunnelTable["Items"].append(tunnel1)
        tunnelTable["Items"].append(tunnel2)
        tunnelTable["Items"].append(tunnel3)
        data1["Tables"] = []
        data1["Tables"].append(tunnelTable)

        resp = self.topo.dut1.get_rest_device().update_config_action(data1)
        glx_assert(resp.status_code == 200)

        tag, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Tunnel#1 Tag2")
        glx_assert(err == '')
        tag = tag.rstrip()
        glx_assert("emmm" == tag)
        tag, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Tunnel#2 Tag2")
        glx_assert(err == '')
        tag = tag.rstrip()
        glx_assert("emmm" == tag)
        tag, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Tunnel#3 Tag2")
        glx_assert(err == '')
        tag = tag.rstrip()
        glx_assert("emmm" == tag)

        # 删除
        resp = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=3)
        glx_assert(resp.status_code == 410)

    def test_update_single_only_tag_field(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="1.1.1.1/32",
                                                       protocol=0,
                                                       tag1="kk")
        # vpp event log clear
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl event-logger clear")
        glx_assert(err == '')

        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol1",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="1.1.1.1/32",
                                                       protocol=0,
                                                       tag1="emmm")

        tag1, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BusinessPolicy#0#bizpol1 Tag1")
        glx_assert(err == '')
        tag1 = tag1.rstrip()
        glx_assert("emmm" == tag1)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show event-logger")
        glx_assert(err == '')
        glx_assert("bizpol_add_replace" not in out)

        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        glx_assert(resp.status_code == 410)

    def test_update_single_tag_and_other_together(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1",priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="1.1.1.1/32",
                                                       protocol=0,
                                                       tag1="kk")
        # vpp event log clear
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl event-logger clear")
        glx_assert(err == '')

        # use raw interface to update only some portion of field.
        bizpol_data = {}
        bizpol_data["Segment"] = 0
        bizpol_data["Name"] = "bizpol1"
        # test for non string field.
        bizpol_data["Priority"] = 2
        bizpol_data['Tag1'] = "kk"
        resp = self.topo.dut1.get_rest_device().do_patch_request("BusinessPolicy", bizpol_data)
        glx_assert(resp.status_code == 200)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show event-logger")
        glx_assert(err == '')
        glx_assert("bizpol_add_replace" in out)

        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        glx_assert(resp.status_code == 410)
