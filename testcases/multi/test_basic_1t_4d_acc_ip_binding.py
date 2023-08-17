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

class TestAccIpBinding(unittest.TestCase):

    # 创建一个最基本的加速场景：
    # 其中dut1作为cpe接入加速网络。dut4作为internet edge通过nat访问一个目标ip
    # 为减少外部依赖，我们可以通过dut4的wan访问与dut3互联的ip。
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
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip_gw("WAN1", "192.168.34.1/24", "192.168.34.2")
        self.topo.dut4.get_rest_device().set_logical_interface_static_ip_gw("WAN1", "192.168.34.2/24", "192.168.34.1")

        # 4, only wan1 used
        self.topo.dut4.get_rest_device().set_logical_interface_nat_direct("WAN2", False)

        # dut1 Lan 1 ip:
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.1.1/24")

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

        # 创建dut1/dut2的默认edge route label fwd表项
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=12)
        self.topo.dut4.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=34)

        # 初始化tst接口
        self.topo.tst.add_ns("dut1")
        self.topo.tst.add_if_to_ns(self.topo.tst.if1, "dut1")

        # 添加tst节点ip及路由
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.add_ns_route("dut1", "33.33.33.0/24", "192.168.1.1")

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # 无条件恢复加速带来的配置改动
        self.topo.dut4.get_rest_device().set_logical_interface_nat_direct("WAN2", True)

        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="33.33.33.0/24")
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

        self.topo.dut4.get_rest_device().delete_edge_route(route_prefix="11.11.11.0/24")
        self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=False)

        # revert acc ip binding related
        self.topo.dut3.get_rest_device().delete_acc_ip_binding(acc_ip="11.11.11.11")
        self.topo.dut3.get_rest_device().delete_logical_interface_additional_ips(name="WAN1")

        self.topo.dut4.get_rest_device().delete_acc_ip_binding(acc_ip="11.11.11.11")
        self.topo.dut4.get_rest_device().delete_acc_ip_binding(acc_ip="11.11.11.12")
        self.topo.dut4.get_rest_device().delete_logical_interface_additional_ips(name="WAN1")

        # revert nat44 session limit 65536-1024
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl set nat44 session limit 64512")

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")

        # 删除label-fwd表项
        # to dut4
        self.topo.dut2.get_rest_device().delete_glx_route_label_fwd(route_label="0x3400000")
        # to dut1
        self.topo.dut3.get_rest_device().delete_glx_route_label_fwd(route_label="0x1200000")

        # 删除dut2/3资源
        self.topo.dut2.get_rest_device().delete_glx_tunnel(tunnel_id=23)
        self.topo.dut3.get_rest_device().delete_glx_tunnel(tunnel_id=23)
        # 创建dut2->dut3的link
        self.topo.dut2.get_rest_device().delete_glx_link(link_id=23)

        # 更新default entry route label entry解除tunnel引用
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)
        self.topo.dut4.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)

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
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.88.0/24")

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    def test_acc_ip_binding(self):
        # 这里的测试配置，需要在teardown中无条件进行各种清理，恢复系统到初始状态。

        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="11.11.11.11")
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="33.33.33.0/24", route_label="0x3400010", is_acc=True)

        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="0x3400010")
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")

        # dut4 (int edge)准备
        # 1. 开启int edge.
        # 2. 配置回程路由　
        result = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut4.get_rest_device().create_edge_route(route_prefix="11.11.11.0/24", route_label="0x1200010", is_acc_reverse=True)

        # dut3 set probe ip, ping support is implemented with setting out ips, so create acc ip binding first
        self.topo.dut3.get_rest_device().create_acc_ip_binding(acc_ip="11.11.11.11", out_ip1="33.33.33.33")
        self.topo.dut3.get_rest_device().set_logical_interface_additional_ips(name="WAN1", add_ip1="33.33.33.33")
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl set nat44 session limit 5")
        time.sleep(1)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # out ip check, WAN1 ip should be used
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 sessions")
        glx_assert(err == '')
        sessions = out.strip().split('dynamic translation')
        sessions = [session.strip() for session in sessions if "33.33.33.33" in session]
        glx_assert(sessions)
        glx_assert("192.168.34.2" in sessions[-1])

        # create binding, out ip should be used
        self.topo.dut4.get_rest_device().create_acc_ip_binding(acc_ip="11.11.11.11", out_ip1="111.111.111.111", out_ip2="111.111.111.112")
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl set nat44 session limit 5")
        time.sleep(1)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # out ip check
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 sessions")
        glx_assert(err == '')
        sessions = out.strip().split('dynamic translation')
        sessions = [session.strip() for session in sessions if "33.33.33.33" in session]
        glx_assert(sessions)
        glx_assert("192.168.34.2" not in sessions[-1])
        glx_assert(("111.111.111.111" in sessions[-1]) or ("111.111.111.112" in sessions[-1]))

        # change binding, WAN1 ip should be used
        self.topo.dut4.get_rest_device().delete_acc_ip_binding(acc_ip="11.11.11.11")
        self.topo.dut4.get_rest_device().create_acc_ip_binding(acc_ip="11.11.11.12", out_ip1="111.111.111.113", out_ip2="111.111.111.114")
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl set nat44 session limit 5")
        time.sleep(1)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # out ip check
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 sessions")
        glx_assert(err == '')
        sessions = out.strip().split('dynamic translation')
        sessions = [session.strip() for session in sessions if "33.33.33.33" in session]
        glx_assert(sessions)
        glx_assert("192.168.34.2" in sessions[-1])
        glx_assert(("111.111.111.111" not in sessions[-1]) and ("111.111.111.112" not in sessions[-1]))

        # change acc ip, out ip should be used
        self.topo.dut1.get_rest_device().update_segment_acc_prop_accip(segment_id=0, acc_ip1="11.11.11.12")
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl set nat44 session limit 5")
        time.sleep(1)
        
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # out ip check
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 sessions")
        glx_assert(err == '')
        sessions = out.strip().split('dynamic translation')
        sessions = [session.strip() for session in sessions if "33.33.33.33" in session]
        glx_assert(sessions)
        glx_assert("192.168.34.2" not in sessions[-1])
        glx_assert(("111.111.111.113" in sessions[-1]) or ("111.111.111.114" in sessions[-1]))

        # revert to the first acc ip with binding, out ip should be used
        self.topo.dut1.get_rest_device().update_segment_acc_prop_accip(segment_id=0, acc_ip1="11.11.11.11")
        self.topo.dut4.get_rest_device().delete_acc_ip_binding(acc_ip="11.11.11.12")
        self.topo.dut4.get_rest_device().create_acc_ip_binding(acc_ip="11.11.11.11", out_ip1="111.111.111.111", out_ip2="111.111.111.112")
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl set nat44 session limit 5")
        time.sleep(1)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 33.33.33.33 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # out ip check
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 sessions")
        glx_assert(err == '')
        sessions = out.strip().split('dynamic translation')
        sessions = [session.strip() for session in sessions if "33.33.33.33" in session]
        glx_assert(sessions)
        glx_assert(("111.111.111.113" not in sessions[-1]) or ("111.111.111.114" not in sessions[-1]))
        glx_assert(("111.111.111.111" in sessions[-1]) or ("111.111.111.112" in sessions[-1]))

    def test_ping_additional_ip(self):
        # 这里的测试配置，需要在teardown中无条件进行各种清理，恢复系统到初始状态。

        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="11.11.11.11")
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="33.33.33.0/24", route_label="0x3400010", is_acc=True)

        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="0x3400010")
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")

        # dut4 (int edge)准备
        # 1. 开启int edge.
        # 2. 配置回程路由　
        result = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut4.get_rest_device().create_edge_route(route_prefix="11.11.11.0/24", route_label="0x1200010", is_acc_reverse=True)

        # dut3 set probe ip, ping support is implemented with setting out ips, so create acc ip binding first
        self.topo.dut3.get_rest_device().create_acc_ip_binding(acc_ip="11.11.11.11", out_ip1="33.33.33.33")
        self.topo.dut3.get_rest_device().set_logical_interface_additional_ips(name="WAN1", add_ip1="33.33.33.33")
        time.sleep(1)

        # create binding
        self.topo.dut4.get_rest_device().create_acc_ip_binding(acc_ip="11.11.11.11", out_ip1="111.111.111.111", out_ip2="111.111.111.112")

        # no loop ip set yet
        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ping 111.111.111.111 -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)

        # set loop ip
        self.topo.dut4.get_rest_device().set_logical_interface_additional_ips(name="WAN1", add_ip1="111.111.111.111", add_ip2="111.111.111.112")
        time.sleep(1)

        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.111 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.111 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.112 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.112 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # check delete out ips
        self.topo.dut4.get_rest_device().create_acc_ip_binding(acc_ip="11.11.11.12", out_ip1="111.111.111.111", out_ip2="111.111.111.112")
        self.topo.dut4.get_rest_device().delete_acc_ip_binding(acc_ip="11.11.11.12")
        time.sleep(1)

        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.111 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.111 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.112 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut3.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 ping 111.111.111.112 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

if __name__ == '__main__':
    unittest.main()
