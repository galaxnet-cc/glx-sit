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

class TestBasic1T4DSched(unittest.TestCase):

    # 创建一个最基本的双link配置场景：
    # dut1--wan1/wan2---dut2---wan3---dut3---wan1--dut4
    # |________88.0/24 tst ___ 89.0/24_________|
    #
    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return

        # 1<>2 192.168.12.0/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.1/24")
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.122.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.122.2/24")
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
        # 辅助link复用同一个route-label.
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN2",
                                                         remote_ip="192.168.122.2", remote_port=2288,
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
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=122)

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
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    def test_overlay_wan_tx_qos_level(self):
        #将link 122的qos level更新为非默认的1
        self.topo.dut1.get_rest_device().update_glx_link(link_id=122, qos_level=1)
        # 配置一条bizpol，将流量qos level标记为1
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol-overlay-level1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       protocol=0,
                                                       qos_level=1)

        # 测试流量
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # iperf正向打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10")
        glx_assert(err == '')
        # 验证应当在122上
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 TxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 TxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link0 tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=200))

        # 更新segment，约束上限qos level为0，此时将走link 12.
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, max_qos_level=0)
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10")
        glx_assert(err == '')
        # 再次打流，验证应当在12上（122级别太高，不能使用）
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 TxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 TxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link0 tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=200))

        # 移除配置
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol-overlay-level1")
        # 恢复默认上限
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, max_qos_level=7)

        # 关闭iperf3服务器.
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

    def test_overlay_wan_rx_qos_level(self):
        #将link 122的qos level更新为非默认的1
        self.topo.dut1.get_rest_device().update_glx_link(link_id=122, qos_level=1)
        # 在dut4上配置一条bizpol，将流量qos level标记为1
        self.topo.dut4.get_rest_device().create_bizpol(name="bizpol-overlay-level1", priority=1,
                                                       dst_prefix="192.168.1.0/24",
                                                       src_prefix="192.168.4.0/24",
                                                       protocol=0,
                                                       qos_level=1)

        # 测试流量
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为0即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # iperf反向打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')
        # 因为qos level全网携带，因此应当仍在122上
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 RxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 RxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link0 tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=200))

        # 更新dut4上的segment，约束上限qos level为0，此时将走link 12.
        self.topo.dut4.get_rest_device().update_segment(segment_id=0, max_qos_level=0)
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')
        # 再次打流，验证应当在12上（122级别太高，不能使用）
        linkTxPacket, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 RxPackets")
        linkTxPacket = linkTxPacket.rstrip()
        glx_assert(err == '')
        linkTxBytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 RxBytes")
        linkTxBytes = linkTxBytes.rstrip()
        glx_assert(err == '')
        print("link0 tx: ", int(linkTxBytes)/int(linkTxPacket))
        glx_assert(math.isclose(1400, int(linkTxBytes)/int(linkTxPacket), abs_tol=200))

        # 移除配置
        self.topo.dut4.get_rest_device().delete_bizpol(name="bizpol-overlay-level1")
        # 恢复默认上限
        self.topo.dut4.get_rest_device().update_segment(segment_id=0, max_qos_level=7)

        # 关闭iperf3服务器.
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')


if __name__ == '__main__':
    unittest.main()
