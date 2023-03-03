import unittest
import time
import math

from lib.util import glx_assert
from topo.topo_1t_4d import Topo1T4D

# 有时候需要反复测试一个用例，可先打开SKIP_TEARDOWN执行一轮用例初始化
# 拓朴配置，然后打开SKIP_SETUP即可反复执行单个测试例。
#
# TODO: 后面开发active link通知删除能力后，就可以支持用例反复setup down
# 就需要打开setup/teardown，并支持在一个复杂拓朴下，测试多个测试例了。　
#
SKIP_SETUP = False
SKIP_TEARDOWN = False

# TODO:
# 1. 暂时只测试dhcp + static场景
# 2. pppoe场景暂不稳定，后面专项增加用例
# 只在dut1<>dut2之间进行验证，dut3/dut4维持主接口静态ip方式互联
class TestBasic1T4DWanDynAddr(unittest.TestCase):

    # 创建一个最基本的配置场景：
    # dut1--wan3/wan4---dut2---wan3---dut3---wan1--dut4
    # |________88.0/24 tst ___ 89.0/24_________|
    #
    def setUp(self):
        self.topo = Topo1T4D()

        # 不具备pfsense的拓朴不执行
        if not self.topo.have_pfsense():
            self.skipTest("this case is disabled now due to pppoe instability.")
            return

        if SKIP_SETUP:
            return

        # NOTE: dut 1<>2 之间的link在测试例中创建，setup中不创建。

        # 2<>3 192.168.23.0/24
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.1/24")
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.2/24")
        # 3<>4 192.168.34.0/24
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.1/24")
        self.topo.dut4.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.2/24")

        # dut1 Lan 1 ip:
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.1.1/24")
        # dut4 Lan 1 ip:
        self.topo.dut4.get_rest_device().set_default_bridge_ip("192.168.4.1/24")

        # create dut1<>dut2 link.
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=12)

        # create dut3<>dut4 link.
        self.topo.dut4.get_rest_device().create_glx_tunnel(tunnel_id=34)
        self.topo.dut4.get_rest_device().create_glx_link(link_id=34, wan_name="WAN1",
                                                         remote_ip="192.168.34.1", remote_port=2288,
                                                         tunnel_id=34,
                                                         route_label="0x3400010")

        # create dut1 route label policy.
        self.topo.dut1.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x1200010", table_id=0)
        # create dut4 route label pocliy.
        self.topo.dut4.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x3400010", table_id=0)

        # create dut2/dut3 tunnel.
        # NC上需要显示创建双向tunnel
        self.topo.dut2.get_rest_device().create_glx_tunnel(tunnel_id=23)
        # need explitly mark as passive.
        self.topo.dut3.get_rest_device().create_glx_tunnel(tunnel_id=23, is_passive=True)
        # 创建dut2->dut3的link
        self.topo.dut2.get_rest_device().create_glx_link(link_id=23, wan_name="WAN3",
                                                         remote_ip="192.168.23.2", remote_port=2288,
                                                         tunnel_id=23,
                                                         route_label="0xffffffffff")

        # 创建label-fwd表项。
        # to dut4
        self.topo.dut2.get_rest_device().create_glx_route_label_fwd(route_label="0x3400000", tunnel_id1=23)
        # to dut1
        self.topo.dut3.get_rest_device().create_glx_route_label_fwd(route_label="0x1200000", tunnel_id1=23)

        # 创建overlay route以及default edge route label fwd entry
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=12)
        self.topo.dut1.get_rest_device().create_edge_route("192.168.4.0/24", route_label="0x3400010")
        self.topo.dut4.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=34)
        self.topo.dut4.get_rest_device().create_edge_route("192.168.1.0/24", route_label="0x1200010")

        # 初始化tst接口
        self.topo.tst.add_ns("dut1")
        self.topo.tst.add_ns("dut4")
        self.topo.tst.add_if_to_ns(self.topo.tst.if1, "dut1")
        self.topo.tst.add_if_to_ns(self.topo.tst.if2, "dut4")

        # 添加tst节点ip及路由
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.add_ns_route("dut1", "192.168.4.0/24", "192.168.1.1")
        self.topo.tst.add_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")
        self.topo.tst.add_ns_route("dut4", "192.168.1.0/24", "192.168.4.1")

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.del_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")

        # 删除edge route.
        self.topo.dut1.get_rest_device().delete_edge_route("192.168.4.0/24")
        self.topo.dut4.get_rest_device().delete_edge_route("192.168.1.0/24")

        # 删除label-fwd表项
        # to dut4
        self.topo.dut2.get_rest_device().delete_glx_route_label_fwd(route_label="0x3400000")
        # to dut1
        self.topo.dut3.get_rest_device().delete_glx_route_label_fwd(route_label="0x1200000")

        # 更新default entry route label entry解除tunnel引用
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)
        self.topo.dut4.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)

        # 删除dut2/3资源
        self.topo.dut2.get_rest_device().delete_glx_tunnel(tunnel_id=23)
        self.topo.dut3.get_rest_device().delete_glx_tunnel(tunnel_id=23)
        # 创建dut2->dut3的link
        self.topo.dut2.get_rest_device().delete_glx_link(link_id=23)

        # 删除dut3/4资源　
        self.topo.dut4.get_rest_device().delete_glx_tunnel(tunnel_id=34)
        self.topo.dut4.get_rest_device().delete_glx_link(link_id=34)
        # 删除dut1/2资源
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=12)

        # 删除label policy.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x1200010")
        # create dut4 route label pocliy.
        self.topo.dut4.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x3400010")

        # revert to default.
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.88.0/24")
        self.topo.dut4.get_rest_device().set_default_bridge_ip("192.168.88.0/24")

        # revert to default.
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    #  测试主接口互通
    def test_basic_traffic_with_main_interface_local_static_peer_dhcp(self):
        # dut1网络配置
        # pfsense对侧11.11.11.1/24，本地配置成11.11.11.2/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN3", "11.11.11.2/24")
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN3", "11.11.11.1")
        # dut2网络配置
        # WAN4默认就是dhcp，无需配置

        # 创建1->2 link，dut2 ip 20.20.20.2由pfsense分配并路由可达
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        # 等待link up
        # 端口注册时间5s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        # 考虑pppoe地址同步到fwdmd，增加5s
        time.sleep(15)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 添加firewall rule阻断
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "block_tst_traffic", 1, "192.168.4.2/32", "Deny")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时应当不通
        glx_assert("100% packet loss" in out)
        # 删除firewall rule
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("block_tst_traffic")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时应当恢复
        glx_assert("0% packet loss" in out)

        # 删除link，新测试例需重配置
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)

        # 恢复默认网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN4")

    def test_basic_traffic_with_sub_interface_local_dhcp_peer_static(self):
        # PFsense wan3.100 dhcp地址段为111.111.111.0/24
        self.topo.dut1.get_rest_device().create_l3subif("WAN3", 100, 100)
        self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN3.100", True)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3.100")

        # PFsense wan4.100地址段为200.200.200.0/24
        self.topo.dut2.get_rest_device().create_l3subif("WAN4", 100, 100)
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN4.100", True)
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN4.100", "200.200.200.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_gw("WAN4.100", "200.200.200.1")

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3.100",
                                                         remote_ip="200.200.200.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        # 等待link up
        # 端口注册时间5s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        # 考虑pppoe地址同步到fwdmd，增加5s
        time.sleep(15)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 添加firewall rule阻断
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "block_tst_traffic", 1, "192.168.4.2/32", "Deny")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时应当不通
        glx_assert("100% packet loss" in out)
        # 删除firewall rule
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("block_tst_traffic")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时应当恢复
        glx_assert("0% packet loss" in out)

        # 删除link，新测试例需重配置
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)

        # 恢复默认网络配置，直接删除三层子接口即可
        self.topo.dut1.get_rest_device().delete_l3subif("WAN3", 100)
        self.topo.dut2.get_rest_device().delete_l3subif("WAN4", 100)

    def test_change_pppoe_with_main_interface_local_pppoe_peer_static(self):
        # dut1网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN3", "dut1", "dut1")

        # dut2网络配置
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN4", "20.20.20.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_gw("WAN4", "20.20.20.1")

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        # 等待link up
        # 端口注册时间5s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        # 考虑pppoe地址同步到fwdmd，增加5s
        time.sleep(90)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)

        time.sleep(10)

        # dut1切到static
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN3", "11.11.11.2/24")
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN3", "11.11.11.1")

        time.sleep(10)

        # dut1网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN3", "dut1", "dut1")

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        
        # 等待link up
        time.sleep(90)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 删除link，新测试例需重配置
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)

        time.sleep(10)

        # 恢复默认网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN4")

    def test_pppoe_with_tcp_connect(self):
        # dut1网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN3", "dut1", "dut1")

        # dut2网络配置
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN4", "20.20.20.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_gw("WAN4", "20.20.20.1")
        self.topo.dut2.get_rest_device().set_logical_interface_tcp_listen_enable("WAN4", True)

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010",
                                                         is_tcp=True)

        # 等待link up
        time.sleep(90)
        
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx link")
        glx_assert(err == '')
        glx_assert("is_tcp_connected 1" in out)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 删除link，新测试例需重配置
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)

        # dut2 WAN4 tcp listen close.
        self.topo.dut2.get_rest_device().set_logical_interface_tcp_listen_enable("WAN4", False)

        # 恢复默认网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN4")

    def test_nat_bizpol_with_pppoe_create_first(self):
        # dut2 turn off WAN1 NAT.
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN4", False)
        # dut1 turn off other WAN NAT
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN2", False)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", False)
        
        # dut1网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN3", "dut1", "dut1")

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.1/24")

        # dut2网络配置
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN4", "20.20.20.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_gw("WAN4", "20.20.20.1")
        
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.2/24")

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN1",
                                                         remote_ip="30.30.30.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        time.sleep(15)

        # bizpol牵引流量至WAN3
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="169.254.100.2",
                                                       dst_prefix="0.0.0.0/0",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN3",
                                                       route_label="0x1200010",
                                                       direct_enable=True,
                                                       protocol=0)
        time.sleep(5)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 30.30.30.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 20.20.20.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 20.20.20.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # bizpol牵引流量至WAN1
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="169.254.100.2",
                                                       dst_prefix="0.0.0.0/0",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       route_label="0x1200010",
                                                       direct_enable=True,
                                                       protocol=0)
        time.sleep(5)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 20.20.20.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 30.30.30.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 30.30.30.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=122)

        # dut2 turn on WAN1 NAT.
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN4", True)
        # dut1 turn on other WAN NAT
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN2", True)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", True)

        # logif切回到dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN4")
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

    def test_nat_bizpol_with_pppoe_create_after(self):
        # bizpol牵引流量至WAN3
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="169.254.100.2",
                                                       dst_prefix="0.0.0.0/0",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN3",
                                                       route_label="0x1200010",
                                                       direct_enable=True,
                                                       protocol=0)
        time.sleep(5)
        # dut2 turn off WAN1 NAT.
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN4", False)
        # dut1 turn off other WAN NAT
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN2", False)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", False)
        
        # dut1网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN3", "dut1", "dut1")

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.1/24")

        # dut2网络配置
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN4", "20.20.20.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_gw("WAN4", "20.20.20.1")
        
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.2/24")

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN1",
                                                         remote_ip="30.30.30.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        time.sleep(15)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 30.30.30.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 20.20.20.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 20.20.20.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # bizpol牵引流量至WAN1
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="169.254.100.2",
                                                       dst_prefix="0.0.0.0/0",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       route_label="0x1200010",
                                                       direct_enable=True,
                                                       protocol=0)
        time.sleep(5)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 20.20.20.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 30.30.30.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ping 30.30.30.2 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=122)

        # dut2 turn on WAN1 NAT.
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN4", True)
        # dut1 turn on other WAN NAT
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN2", True)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", True)

        # logif切回到dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN4")
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

    def test_traffic_bizpol_with_pppoe_create_first(self):
        # dut1网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN3", "dut1", "dut1")
        time.sleep(10)

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.1/24")

        # dut2网络配置
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN4", "20.20.20.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_gw("WAN4", "20.20.20.1")
        
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.2/24")

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN1",
                                                         remote_ip="30.30.30.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        time.sleep(15)

        # bizpol牵引流量至WAN3
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN3",
                                                       protocol=0)
        time.sleep(5)
        
        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # iperf打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        time.sleep(5)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10")
        glx_assert(err == '')

        time.sleep(20)

        # 每个包大小应约为1400bytes
        # link tx
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 TxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 TxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=100))

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # bizpol牵引流量至WAN1
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       protocol=0)
        time.sleep(5)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10")
        glx_assert(err == '')

        time.sleep(20)
        
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 TxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 TxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=100))

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=122)

        # logif切回到dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN4")
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

    def test_traffic_bizpol_with_pppoe_create_after(self):
        # bizpol牵引流量至WAN3
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN3",
                                                       protocol=0)
        time.sleep(5)
        
        # dut1网络配置
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN3", "dut1", "dut1")
        time.sleep(10)

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.1/24")

        # dut2网络配置
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN4", "20.20.20.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_gw("WAN4", "20.20.20.1")
        
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "30.30.30.2/24")

        # 创建1->2 link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN3",
                                                         remote_ip="20.20.20.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN1",
                                                         remote_ip="30.30.30.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        time.sleep(15)
        
        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # iperf打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        time.sleep(5)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10")
        glx_assert(err == '')

        time.sleep(20)

        # 每个包大小应约为1400bytes
        # link tx
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 TxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 TxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=100))

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # bizpol牵引流量至WAN1
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       protocol=0)
        time.sleep(5)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10")
        glx_assert(err == '')

        time.sleep(20)
        
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 TxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 TxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=100))

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=122)

        # logif切回到dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN4")
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

if __name__ == '__main__':
    unittest.main()
