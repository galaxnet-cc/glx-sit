import unittest
import time

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

class TestBasic1T4D(unittest.TestCase):

    # 创建一个最基本的配置场景：
    # dut1--wan1---dut2---wan3---dut3---wan1--dut4
    # |________88.0/24 tst ___ 89.0/24_________|
    #
    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return

        # 1<>2 192.168.12.0/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.2/24")
        # 2<>3 192.168.23.0/24
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.1/24")
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.2/24")
        # 3<>4 192.168.34.0/24
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.1/24")
        self.topo.dut4.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.2/24")

        mtu = 1500
        # dut1 Lan 1 ip:
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.1.1/24", mtu=mtu)
        # dut4 Lan 1 ip:
        self.topo.dut4.get_rest_device().set_default_bridge_ip_or_mtu("192.168.4.1/24", mtu=mtu)

        # create dut1<>dut2 link.
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=12)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
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
        # 松耦合了，不需创建
        # need explitly mark as passive.
        #self.topo.dut3.get_rest_device().create_glx_tunnel(tunnel_id=23, is_passive=True)
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

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        self.topo.tst.get_ns_cmd_result("dut1", f"ip -6 addr flush dev {self.topo.tst.if1}")
        self.topo.tst.get_ns_cmd_result("dut4", f"ip -6 addr flush dev {self.topo.tst.if2}")
        # important!
        # Link local Address will be flushed so that we should restart the interface
        self.topo.tst.ns_up_down_if("dut1", self.topo.tst.if1, False)
        self.topo.tst.ns_up_down_if("dut1", self.topo.tst.if1, True)
        self.topo.tst.ns_up_down_if("dut4", self.topo.tst.if2, False)
        self.topo.tst.ns_up_down_if("dut4", self.topo.tst.if2, True)

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
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)

        # 删除label policy.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x1200010")
        # create dut4 route label pocliy.
        self.topo.dut4.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x3400010")

        # revert to default.
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)
        self.topo.dut4.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    def test_02_ra(self):
        prefix = "/80"

        dut1_lan_ip4 = "192.168.1.1/24"
        dut1_route_label = "0x1200010"
        dut1_lan_ip6_net = "2001:db8"
        dut1_lan_ip6 = dut1_lan_ip6_net + "::1"
        dut1_lan_ip6_with_prefix = dut1_lan_ip6 + prefix
        dut1_ns = "dut1"

        dut4_lan_ip4 = "192.168.4.1/24"
        dut4_route_label = "0x3400010"
        dut4_lan_ip6_net = "2001:db9"
        dut4_lan_ip6 = dut4_lan_ip6_net + "::1"
        dut4_lan_ip6_with_prefix = dut4_lan_ip6 + prefix
        dut4_ns = "dut4"

        # setup
        #  dut1
        self.topo.dut1.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut1_lan_ip4, bvi_ip6_w_prefix=dut1_lan_ip6_with_prefix)
        self.topo.dut1.rest_device.create_edge_route(route_prefix=dut4_lan_ip6_with_prefix, route_label=dut4_route_label)
        #  dut4
        self.topo.dut4.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut4_lan_ip4, bvi_ip6_w_prefix=dut4_lan_ip6_with_prefix)
        self.topo.dut4.rest_device.create_edge_route(route_prefix=dut1_lan_ip6_with_prefix, route_label=dut1_route_label)

        #  wait for RA
        time.sleep(3)


        tst_if1_addr = dut1_lan_ip6_net + "::2" 
        tst_if1_addr_with_prefix =  tst_if1_addr + prefix
        self.topo.tst.add_ns_if_ip6(dut4_ns, self.topo.tst.if1, tst_if1_addr_with_prefix)
        #  ping gateway
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {dut1_lan_ip6} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {dut1_lan_ip6} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        # ping dut4
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {dut4_lan_ip6} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        # ping if2
        tst_if2_addr = dut4_lan_ip6_net + "::2" 
        tst_if2_addr_with_prefix =  tst_if2_addr + prefix
        self.topo.tst.add_ns_if_ip6(dut4_ns, self.topo.tst.if2, tst_if2_addr_with_prefix)

        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {tst_if2_addr} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        # tear down
        #  dut4
        self.topo.dut4.rest_device.delete_edge_route(dut1_lan_ip6_with_prefix)
        self.topo.dut4.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut4_lan_ip4, bvi_ip6_w_prefix="")
        #  dut1
        self.topo.dut1.rest_device.delete_edge_route(dut4_lan_ip6_with_prefix)
        self.topo.dut1.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut1_lan_ip4, bvi_ip6_w_prefix="")

    def test_01_slaac(self):
        # it should be 64
        prefix = "/64"

        dut1_lan_ip4 = "192.168.1.1/24"
        dut1_route_label = "0x1200010"
        dut1_lan_ip6_net = "2001:db8"
        dut1_lan_ip6 = dut1_lan_ip6_net + "::1"
        dut1_lan_ip6_with_prefix = dut1_lan_ip6 + prefix
        dut1_ns = "dut1"

        dut4_lan_ip4 = "192.168.4.1/24"
        dut4_route_label = "0x3400010"
        dut4_lan_ip6_net = "2001:db9"
        dut4_lan_ip6 = dut4_lan_ip6_net + "::1"
        dut4_lan_ip6_with_prefix = dut4_lan_ip6 + prefix
        dut4_ns = "dut4"

        # setup
        #  dut1
        self.topo.dut1.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut1_lan_ip4, bvi_ip6_w_prefix=dut1_lan_ip6_with_prefix)
        self.topo.dut1.rest_device.create_edge_route(route_prefix=dut4_lan_ip6_with_prefix, route_label=dut4_route_label)
        #  dut4
        self.topo.dut4.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut4_lan_ip4, bvi_ip6_w_prefix=dut4_lan_ip6_with_prefix)
        self.topo.dut4.rest_device.create_edge_route(route_prefix=dut1_lan_ip6_with_prefix, route_label=dut1_route_label)

        #  wait for RA
        time.sleep(3)

        #  ping gateway
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {dut1_lan_ip6} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {dut1_lan_ip6} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        # ping dut4
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {dut4_lan_ip6} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        # get slaac ip address
        if1_addr_with_prefix, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ip -6 addr show dev {self.topo.tst.if1} | grep '{dut1_lan_ip6_net}' | awk '{{print $2}}'")
        glx_assert(err == '')
        glx_assert(if1_addr_with_prefix != '')
        if1_addr = if1_addr_with_prefix.replace('\n', '').replace(prefix, '')

        if2_addr_with_prefix, err = self.topo.tst.get_ns_cmd_result(dut4_ns, f"ip -6 addr show dev {self.topo.tst.if2} | grep '{dut4_lan_ip6_net}' | awk '{{print $2}}'")
        glx_assert(err == '')
        glx_assert(if2_addr_with_prefix != '')
        if2_addr = if2_addr_with_prefix.replace('\n', '').replace(prefix, '')

        # ping 
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {if2_addr} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("0% packet loss" in out)

        # big packet
        out, err = self.topo.tst.get_ns_cmd_result(dut1_ns, f"ping {if2_addr} -M dont -s 3000 -c 5")
        glx_assert(err == '')
        glx_assert("Packet too big" in out)
        glx_assert("100% packet loss" not in out)

        # tear down
        #  dut4
        self.topo.dut4.rest_device.delete_edge_route(dut1_lan_ip6_with_prefix)
        self.topo.dut4.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut4_lan_ip4, bvi_ip6_w_prefix="")
        #  dut1
        self.topo.dut1.rest_device.delete_edge_route(dut4_lan_ip6_with_prefix)
        self.topo.dut1.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=dut1_lan_ip4, bvi_ip6_w_prefix="")



