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

class TestBasic1T4DSched(unittest.TestCase):

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
        # 松耦合了，不需创建
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
        # 增加nat路由
        self.topo.tst.add_ns_route("dut1", "192.168.12.0/24", "192.168.1.1")
        self.topo.tst.add_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")
        self.topo.tst.add_ns_route("dut4", "192.168.1.0/24", "192.168.4.1")

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.del_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")
        self.topo.tst.add_ns_if_to_default_ns("dut1", self.topo.tst.if1)
        self.topo.tst.add_ns_if_to_default_ns("dut4", self.topo.tst.if2)

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

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    # @unittest.skip("bug: 20231009: When received icmp packets, bizpol session will not be created")
    def test_overlay_sched_class(self):
        # 打开sched开关(rx+tx)，带宽分配按默认即可
        result = self.topo.dut1.get_rest_device().update_sched_wan_agg_global_params(tx_enable=True, rx_enable=True)
        glx_assert(result.status_code == 200)
        # 清一下统计
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx sched wan-agg clear")

        # 改写overlay流量优先级为high
        # 默认情况下没有流量进入high
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol-overlay-high", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       protocol=0,
                                                       sched_class="high")

        # telnet 发送tcp报文
        _ = self.topo.tst.get_ns_cmd_result("dut1", "telnet 192.168.4.2 5555")
        # out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        # glx_assert(err == '')
        # # 首包会因为arp而丢失，不为０即可
        # glx_assert("100% packet loss" not in out)
        # out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        # glx_assert(err == '')
        # # 此时不应当再丢包
        # glx_assert("0% packet loss" in out)

        # bizpol进行了有状态能力跟踪，因此检查high队列的rx tx均有数据
        # tx
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx sched wan-agg tx")
        glx_assert(err == '')
        # 队列里应当有值，不能是0
        glx_assert("queue [1] enq_count 0 deq_count 0" not in out)
        # rx，通过bizpol session来识别class.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx sched wan-agg rx")
        glx_assert(err == '')
        # 队列里应当有值，不能是0
        glx_assert("queue [1] enq_count 0 deq_count 0" not in out)

        # 移除配置
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol-overlay-high")
        # 无需移除路由，依赖setup.

        # 关闭sched.
        result = self.topo.dut1.get_rest_device().update_sched_wan_agg_global_params(tx_enable=False, rx_enable=False)
        glx_assert(result.status_code == 200)

    # @unittest.skip("bug: 20231009: When received icmp packets, bizpol session will not be created")
    def test_internet_sched_class(self):
        # 打开sched开关(rx+tx)，带宽分配按默认即可
        result = self.topo.dut1.get_rest_device().update_sched_wan_agg_global_params(tx_enable=True, rx_enable=True)
        glx_assert(result.status_code == 200)
        # 清一下统计
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx sched wan-agg clear")

        # 确保WAN1能力开启(测试模型上默认是开启的)，以便流量能够固定进入WAN1
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", True)


        # 改写internet流量优先级为low
        # 默认情况下没有流量进入low
        # TODO: 后续增加sched计数清除时，我们可以重用high能力
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol-internet-low", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.12.2/32",
                                                       protocol=0,
                                                       sched_class="low",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       direct_enable=True)

        # telnet 发送tcp报文
        _ = self.topo.tst.get_ns_cmd_result("dut1", "telnet 192.168.12.2 5555")
        # out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.12.2 -c 5 -i 0.05")
        # glx_assert(err == '')
        # # 首包会因为arp而丢失，不为０即可
        # glx_assert("100% packet loss" not in out)
        # out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.12.2 -c 5 -i 0.05")
        # glx_assert(err == '')
        # # 此时不应当再丢包
        # glx_assert("0% packet loss" in out)

        # bizpol进行了有状态能力跟踪，因此检查high队列的rx tx均有数据
        # tx
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx sched wan-agg tx")
        glx_assert(err == '')
        # 队列里应当有值，不能是0
        glx_assert("queue [3] enq_count 0 deq_count 0" not in out)
        # rx，通过bizpol session来识别class.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx sched wan-agg rx")
        glx_assert(err == '')
        # 队列里应当有值，不能是0
        glx_assert("queue [3] enq_count 0 deq_count 0" not in out)

        # 移除配置
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol-internet-low")
        # 无需移除路由，依赖setup.

        # 关闭sched.
        result = self.topo.dut1.get_rest_device().update_sched_wan_agg_global_params(tx_enable=False, rx_enable=False)
        glx_assert(result.status_code == 200)

if __name__ == '__main__':
    unittest.main()
