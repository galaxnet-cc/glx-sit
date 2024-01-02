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

class TestBasic1T4DAcc(unittest.TestCase):

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
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.1/24")
        self.topo.dut4.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.2/24")

        # dut1 Lan 1 ip:
        mtu = 1500
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
        # 添加到加速目标(192.168.34.0/24)的路由
        self.topo.tst.add_ns_route("dut1", "192.168.34.0/24", "192.168.1.1")

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # 无条件恢复加速带来的配置改动
        self.topo.dut4.get_rest_device().set_logical_interface_nat_direct("WAN2", True)
        self.topo.dut3.get_rest_device().set_logical_interface_nat_direct("WAN1", True)

        self.topo.dut4.get_rest_device().delete_edge_route(route_prefix="222.222.222.222/32")
        self.topo.dut4.get_rest_device().delete_edge_route(route_prefix="222.222.222.223/32")
        self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=False)

        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="192.168.34.1/32")
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.add_ns_if_to_default_ns("dut1", self.topo.tst.if1)

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
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)
        self.topo.dut4.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    #  测试加速流量
    def test_basic_traffic(self):
        # 这里的测试配置，需要在teardown中无条件进行各种清理，恢复系统到初始状态。

        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.34.1/32", route_label="0x3400010", is_acc=True)

        # dut4 (int edge)准备
        # 开启WAN1 NAT能力(WAN1默认开启，因此不需要再配置了)
        # 1. 开启int edge.
        # 2. 配置回程路由　
        # 3. DUT3的WAN关闭NAT能力，以便于WAN IP(34.1)被访问
        result = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        # dut3 turn off WAN1 NAT.
        self.topo.dut3.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        # (优化点!)
        # TODO: WAN2默认开启NAT，因接口up所以被选择，后续需要增加一个healtcheck机制，设置每个接口的health状态。
        self.topo.dut4.get_rest_device().set_logical_interface_nat_direct("WAN2", False)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 检查dut1上存在使用加速ip的nat session
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show nat44 sessions")
        glx_assert(err == '')
        glx_assert("222.222.222.222" in out)
        # 检查dut4上同样存在使用加速ip的nat session
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"vppctl show nat44 sessions")
        glx_assert(err == '')
        glx_assert("222.222.222.222" in out)

        # 230704: 增加加速ip变更的验证，以验证bugfix.
        self.topo.dut1.get_rest_device().update_segment_acc_prop_accip(segment_id=0, acc_ip1="222.222.222.223")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show nat44 addresses")
        glx_assert(err == '')
        # nat所用地址需要切换掉
        glx_assert("222.222.222.222" not in out)
        glx_assert("222.222.222.223" in out)
        # 增加一条回程路由
        self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.223/32", route_label="0x1200010", is_acc_reverse=True)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 检查dut1上存在使用加速ip的nat session
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show nat44 sessions")
        glx_assert(err == '')
        glx_assert("222.222.222.223" in out)
        # 检查dut4上同样存在使用加速ip的nat session
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"vppctl show nat44 sessions")
        glx_assert(err == '')
        glx_assert("222.222.222.223" in out)

        # 测试ttl为1的时候能收到icmp error
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 1 -t 1")
        glx_assert(err == '')
        glx_assert("Time to live exceeded" in out)

    def test_basic_traffic_using_bizpol(self):
        # 这里的测试配置，需要在teardown中无条件进行各种清理，恢复系统到初始状态。

        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        # 基于bizpol实现加速路由
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.34.1/32",
                                                       protocol=0,
                                                       overlay_enable=True,
                                                       acc_enable=True,
                                                       route_label="0x3400010")

        # dut4 (int edge)准备
        # 开启WAN1 NAT能力(WAN1默认开启，因此不需要再配置了)
        # 1. 开启int edge.
        # 2. 配置回程路由　
        # 3. DUT3的WAN关闭NAT能力，以便于WAN IP(34.1)被访问
        result = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(result.status_code == 200)
        self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        # dut3 turn off WAN1 NAT.
        self.topo.dut3.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        # (优化点!)
        # TODO: WAN2默认开启NAT，因接口up所以被选择，后续需要增加一个healtcheck机制，设置每个接口的health状态。
        self.topo.dut4.get_rest_device().set_logical_interface_nat_direct("WAN2", False)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 检查dut1上存在使用加速ip的nat session
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show nat44 sessions")
        glx_assert(err == '')
        glx_assert("222.222.222.222" in out)
        # 检查dut4上同样存在使用加速ip的nat session
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"vppctl show nat44 sessions")
        glx_assert(err == '')
        glx_assert("222.222.222.222" in out)

        # 测试ttl为1的时候能收到icmp error
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.34.1 -c 1 -t 1")
        glx_assert(err == '')
        glx_assert("Time to live exceeded" in out)

        # 移除bizpol.
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

if __name__ == '__main__':
    unittest.main()
