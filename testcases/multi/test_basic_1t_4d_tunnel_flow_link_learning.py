import threading
import re
import unittest
import time
import math

from lib.util import glx_assert
from topo.topo_1t_4d import Topo1T4D

def delayed_update_bizpol(update_func, delay, **kwargs):
    time.sleep(delay)  # 延时
    # 调用更新函数
    update_func(**kwargs)

# 有时候需要反复测试一个用例，可先打开SKIP_TEARDOWN执行一轮用例初始化
# 拓朴配置，然后打开SKIP_SETUP即可反复执行单个测试例。
#
# TODO: 后面开发active link通知删除能力后，就可以支持用例反复setup down
# 就需要打开setup/teardown，并支持在一个复杂拓朴下，测试多个测试例了。　
#
SKIP_SETUP = False
SKIP_TEARDOWN = False

class TestBasic1T4DTunnelFlowLinkLearning(unittest.TestCase):
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
        # dut1<->dut2 wan pair 2.
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.22.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.22.2/24")
        # 2<>3 192.168.23.0/24
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.1/24")
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.2/24")
        # 3<>4 192.168.34.0/24
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.1/24")
        self.topo.dut4.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.2/24")

        # set flow link sessions aging time to 20s
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("vppctl set glx global tunnel-flow-link-sessions-aging-time 20")
        # set flow link sessions check time to 1s for test
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("vppctl set glx global tunnel-flow-link-sessions-check-time 1")

        # dut1 Lan 1 ip:
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.1.1/24", mtu=mtu)
        # dut4 Lan 1 ip:
        self.topo.dut4.get_rest_device().set_default_bridge_ip_or_mtu("192.168.4.1/24", mtu=mtu)

        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=12)
        # create dut1<>dut2 link.
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN2",
                                                         remote_ip="192.168.22.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        # create dut1<>dut2 link2.（共享tunnel id & route label）
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
        self.topo.tst.add_ns("dut4")
        self.topo.tst.add_if_to_ns(self.topo.tst.if1, "dut1")
        self.topo.tst.add_if_to_ns(self.topo.tst.if2, "dut4")

        # 添加tst节点ip及路由
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.add_ns_route("dut1", "0.0.0.0/0", "192.168.1.1")
        self.topo.tst.add_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")
        self.topo.tst.add_ns_route("dut4", "222.222.222.222/32", "192.168.4.1")

        # 等待link up
        # 端口注册时间5s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="192.168.4.0/24")

        # set flow link sessions aging time to default
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("vppctl set glx global tunnel-flow-link-sessions-aging-time 300")
        # set flow link sessions check time to default
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("vppctl set glx global tunnel-flow-link-sessions-check-time 30")

        # 无条件恢复加速带来的配置改动
        self.topo.dut4.get_rest_device().delete_edge_route(route_prefix="222.222.222.222/32")
        self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=False)

        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="192.168.34.1/32")
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.del_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")
        self.topo.tst.add_ns_if_to_default_ns("dut1", self.topo.tst.if1)
        self.topo.tst.add_ns_if_to_default_ns("dut4", self.topo.tst.if2)

        # 删除label-fwd表项
        # to dut4
        self.topo.dut2.get_rest_device().delete_glx_route_label_fwd(route_label="0x3400000")
        # to dut1
        self.topo.dut3.get_rest_device().delete_glx_route_label_fwd(route_label="0x1200000")

        # 删除dut2/3资源
        self.topo.dut2.get_rest_device().delete_glx_tunnel(tunnel_id=23)
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
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    def test_01_baisc(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        tunnel_id = 12
        # 默认选择link[0]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel id {tunnel_id}")
        glx_assert(err == '')
        match = re.search(r'member \[0\] link-id (\d+)', out)
        glx_assert(match)
        link_id = match.group(1)

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=tunnel_id, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # 打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        # link rx
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print(f"link{link_id} rx: ", int(link_rx_bytes) / int(link_rx_packets))
        glx_assert(math.isclose(1400, int(link_rx_bytes) / int(link_rx_packets), abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print(f"tunnel{tunnel_id} rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))

        # 检查session
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" in out)
        glx_assert("192.168.4.2" in out)
        # iperf server port
        glx_assert("5201" in out)
        glx_assert(f"tunnel-id {tunnel_id}" in out)
        glx_assert(f"link-id {link_id}" in out)

        # 等待session老化
        time.sleep(25)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" not in out)
        glx_assert("192.168.4.2" not in out)
        # iperf server port
        glx_assert("5201" not in out)
        glx_assert(f"tunnel-id {tunnel_id}" not in out)
        glx_assert(f"link-id {link_id}" not in out)

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

    def test_02_steering_interface(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        tunnel_id = 12
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel id {tunnel_id}")
        glx_assert(err == '')
        match = re.search(r'member \[0\] link-id (\d+)', out)
        glx_assert(match)
        link_id = match.group(1)
        match = re.search(r'member \[1\] link-id (\d+)', out)
        glx_assert(match)
        backup_link_id = match.group(1) 

        # 调度到link[1]的接口
        backup_interface = "WAN2" if link_id == "12" else "WAN1"
        
        # 配置策略强制走link[1]
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface=backup_interface,
                                                       protocol=0,
                                                       direct_enable=False)
        glx_assert(resp.status_code == 201)

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=tunnel_id, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # 打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        # link rx
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print(f"link{backup_link_id} rx: ", int(link_rx_bytes) / int(link_rx_packets))
        glx_assert(math.isclose(1400, int(link_rx_bytes) / int(link_rx_packets), abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print(f"tunnel{tunnel_id} rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))

        # 检查session
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" in out)
        glx_assert("192.168.4.2" in out)
        # iperf server port
        glx_assert("5201" in out)
        glx_assert(f"tunnel-id {tunnel_id}" in out)
        glx_assert(f"link-id {backup_link_id}" in out)

        # 等待session老化
        time.sleep(25)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" not in out)
        glx_assert("192.168.4.2" not in out)
        # iperf server port
        glx_assert("5201" not in out)
        glx_assert(f"tunnel-id {tunnel_id}" not in out)
        glx_assert(f"link-id {backup_link_id}" not in out)

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

    def test_03_change_steering_interface(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        tunnel_id = 12
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel id {tunnel_id}")
        glx_assert(err == '')
        match = re.search(r'member \[0\] link-id (\d+)', out)
        glx_assert(match)
        link_id = match.group(1)
        match = re.search(r'member \[1\] link-id (\d+)', out)
        glx_assert(match)
        backup_link_id = match.group(1) 

        # 调度到link[1]的接口
        backup_interface = "WAN2" if link_id == "12" else "WAN1"
        interface = "WAN1" if backup_interface == "WAN2"  else "WAN2"
        
        # 配置策略强制走link[1]
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface=backup_interface,
                                                       protocol=0,
                                                       direct_enable=False)
        glx_assert(resp.status_code == 201)

        # 等待一段时间切换到link[0]
        delay_thread = threading.Thread(target=lambda: delayed_update_bizpol(
            self.topo.dut1.get_rest_device().update_bizpol,
            5,  # 延时5秒
            name="bizpol1", 
            priority=1,
            src_prefix="192.168.1.0/24",
            dst_prefix="192.168.4.0/24",
            steering_type=1,
            steering_mode=1,
            steering_interface=interface,  # 使用新的接口
            protocol=0,
            direct_enable=False
        ))

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=tunnel_id, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # 打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')

        # 启动切换线程
        delay_thread.start()
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

        # link rx
        back_link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxPackets")
        back_link_rx_packets = back_link_rx_packets.rstrip()
        glx_assert(err == '')
        back_link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxBytes")
        back_link_rx_bytes = back_link_rx_bytes.rstrip()
        glx_assert(err == '')
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print(f"link{link_id} rx bytes: ", link_rx_bytes)
        print(f"link{backup_link_id} rx bytes: ", back_link_rx_bytes)

        total_rx_bytes = int(link_rx_bytes) + int(back_link_rx_bytes)
        total_rx_packets = int(link_rx_packets) + int(back_link_rx_packets)
        print(f"link rx: ", total_rx_bytes / total_rx_packets)
        glx_assert(math.isclose(1400, total_rx_bytes / total_rx_packets, abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print(f"tunnel rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))
        # 等待session老化
        time.sleep(25)

    def test_04_steering_interface_no_mandatory(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        tunnel_id = 12
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel id {tunnel_id}")
        glx_assert(err == '')
        match = re.search(r'member \[0\] link-id (\d+)', out)
        glx_assert(match)
        link_id = match.group(1)
        match = re.search(r'member \[1\] link-id (\d+)', out)
        glx_assert(match)
        backup_link_id = match.group(1) 

        # 调度到link[1]的接口
        backup_interface = "WAN2" if link_id == "12" else "WAN1"
        
        # 配置策略强制走link[1]
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=1,
                                                       steering_mode=0,
                                                       steering_interface=backup_interface,
                                                       protocol=0,
                                                       direct_enable=False)
        glx_assert(resp.status_code == 201)

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=tunnel_id, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        # 更新link让link不可用
        resp = self.topo.dut1.get_rest_device().update_glx_link_remote_ip(link_id=int(backup_link_id))
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # 打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        # link rx
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print(f"link{link_id} rx: ", int(link_rx_bytes) / int(link_rx_packets))
        glx_assert(math.isclose(1400, int(link_rx_bytes) / int(link_rx_packets), abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print(f"tunnel{tunnel_id} rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))

        # 检查session
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" in out)
        glx_assert("192.168.4.2" in out)
        # iperf server port
        glx_assert("5201" in out)
        glx_assert(f"tunnel-id {tunnel_id}" in out)
        glx_assert(f"link-id {link_id}" in out)

        # 等待session老化
        time.sleep(25)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" not in out)
        glx_assert("192.168.4.2" not in out)
        # iperf server port
        glx_assert("5201" not in out)
        glx_assert(f"tunnel-id {tunnel_id}" not in out)
        glx_assert(f"link-id {link_id}" not in out)

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

    def test_05_steering_link_steering_label(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        tunnel_id = 12
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel id {tunnel_id}")
        glx_assert(err == '')
        match = re.search(r'member \[0\] link-id (\d+)', out)
        glx_assert(match)
        link_id = match.group(1)
        match = re.search(r'member \[1\] link-id (\d+)', out)
        glx_assert(match)
        backup_link_id = match.group(1) 

        backup_link_steering_label = 1
        resp = self.topo.dut1.get_rest_device().update_glx_link(link_id=int(backup_link_id), steering_label=backup_link_steering_label)
        glx_assert(resp.status_code == 200)
        
        # 配置策略强制走link[1]
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=2,
                                                       steering_mode=1,
                                                       steering_link_steering_label=backup_link_steering_label,
                                                       protocol=0,
                                                       direct_enable=False)
        glx_assert(resp.status_code == 201)

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=tunnel_id, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # 打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        # link rx
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print(f"link{backup_link_id} rx: ", int(link_rx_bytes) / int(link_rx_packets))
        glx_assert(math.isclose(1400, int(link_rx_bytes) / int(link_rx_packets), abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print(f"tunnel{tunnel_id} rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))

        # 检查session
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" in out)
        glx_assert("192.168.4.2" in out)
        # iperf server port
        glx_assert("5201" in out)
        glx_assert(f"tunnel-id {tunnel_id}" in out)
        glx_assert(f"link-id {backup_link_id}" in out)

        # 等待session老化
        time.sleep(25)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" not in out)
        glx_assert("192.168.4.2" not in out)
        # iperf server port
        glx_assert("5201" not in out)
        glx_assert(f"tunnel-id {tunnel_id}" not in out)
        glx_assert(f"link-id {backup_link_id}" not in out)

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

    def test_06_steering_link_steering_label_no_mandatory(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        tunnel_id = 12
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel id {tunnel_id}")
        glx_assert(err == '')
        match = re.search(r'member \[0\] link-id (\d+)', out)
        glx_assert(match)
        link_id = match.group(1)
        match = re.search(r'member \[1\] link-id (\d+)', out)
        glx_assert(match)
        backup_link_id = match.group(1) 

        backup_link_steering_label = 1
        resp = self.topo.dut1.get_rest_device().update_glx_link(link_id=int(backup_link_id), steering_label=backup_link_steering_label)
        glx_assert(resp.status_code == 200)

        
        # 配置策略强制走link[1]
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=2,
                                                       steering_mode=0,
                                                       steering_link_steering_label=backup_link_steering_label,
                                                       protocol=0,
                                                       direct_enable=False)
        glx_assert(resp.status_code == 201)

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=tunnel_id, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        # 更新link让link不可用
        resp = self.topo.dut1.get_rest_device().update_glx_link_remote_ip(link_id=int(backup_link_id), steering_label=backup_link_steering_label)
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # 打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        # link rx
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print(f"link{link_id} rx: ", int(link_rx_bytes) / int(link_rx_packets))
        glx_assert(math.isclose(1400, int(link_rx_bytes) / int(link_rx_packets), abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print(f"tunnel{tunnel_id} rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))

        # 检查session
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" in out)
        glx_assert("192.168.4.2" in out)
        # iperf server port
        glx_assert("5201" in out)
        glx_assert(f"tunnel-id {tunnel_id}" in out)
        glx_assert(f"link-id {link_id}" in out)

        # 等待session老化
        time.sleep(25)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx flow link sessions")
        glx_assert(err == '')

        glx_assert("222.222.222.222" not in out)
        glx_assert("192.168.4.2" not in out)
        # iperf server port
        glx_assert("5201" not in out)
        glx_assert(f"tunnel-id {tunnel_id}" not in out)
        glx_assert(f"link-id {link_id}" not in out)

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

    def test_07_change_steering_link_steering_label(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        tunnel_id = 12
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel id {tunnel_id}")
        glx_assert(err == '')
        match = re.search(r'member \[0\] link-id (\d+)', out)
        glx_assert(match)
        link_id = match.group(1)
        match = re.search(r'member \[1\] link-id (\d+)', out)
        glx_assert(match)
        backup_link_id = match.group(1) 

        # 调度到link[1]的接口
        backup_link_steering_label = 1 if link_id == "12" else 2
        link_steering_label = 2 if backup_link_steering_label == 1 else 1

        resp = self.topo.dut1.get_rest_device().update_glx_link(int(backup_link_id), steering_label=backup_link_steering_label)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().update_glx_link(int(link_id), steering_label=link_steering_label)
        glx_assert(resp.status_code == 200)
        
        # 配置策略强制走link[1]
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       steering_type=2,
                                                       steering_mode=1,
                                                       steering_link_steering_label=backup_link_steering_label,
                                                       protocol=0,
                                                       direct_enable=False)
        glx_assert(resp.status_code == 201)

        # 等待一段时间切换到link[0]
        delay_thread = threading.Thread(target=lambda: delayed_update_bizpol(
            self.topo.dut1.get_rest_device().update_bizpol,
            5,  # 延时5秒
            name="bizpol1", 
            priority=1,
            src_prefix="192.168.1.0/24",
            dst_prefix="192.168.4.0/24",
            steering_type=2,
            steering_mode=1,
            steering_link_steering_label=link_steering_label,
            protocol=0,
            direct_enable=False
        ))

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=tunnel_id, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')
        # 打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')

        # 启动切换线程
        delay_thread.start()
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')

        # link rx
        back_link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxPackets")
        back_link_rx_packets = back_link_rx_packets.rstrip()
        glx_assert(err == '')
        back_link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{backup_link_id} RxBytes")
        back_link_rx_bytes = back_link_rx_bytes.rstrip()
        glx_assert(err == '')
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#{link_id} RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print(f"link{link_id} rx bytes: ", link_rx_bytes)
        print(f"link{backup_link_id} rx bytes: ", back_link_rx_bytes)

        total_rx_bytes = int(link_rx_bytes) + int(back_link_rx_bytes)
        total_rx_packets = int(link_rx_packets) + int(back_link_rx_packets)
        print(f"link rx: ", total_rx_bytes / total_rx_packets)
        glx_assert(math.isclose(1400, total_rx_bytes / total_rx_packets, abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#{tunnel_id} RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print(f"tunnel rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))
        # 等待session老化
        time.sleep(25)

    def test_08_multi(self):
        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        # 3. 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # 开启flow link learning
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=12, passive_flow_link_learning_enable=True)
        glx_assert(resp.status_code == 200)
        time.sleep(5)

        # dut4 (int edge)准备
        # 配置回程路由　
        # 开启int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 配置策略强制走link12
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.2/32",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       protocol=0,
                                                       direct_enable=False)


        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')

        # iperf打流
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.2 -t 10 -R")
        glx_assert(err == '')

        # link12 rx
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#12 RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print("link12 rx: ", int(link_rx_bytes) / int(link_rx_packets))
        glx_assert(math.isclose(1400, int(link_rx_bytes) / int(link_rx_packets), abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#12 RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#12 RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print("tunnel12 rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))

        # 配置策略强制走link122
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol2", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.1/32",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN2",
                                                       protocol=0,
                                                       direct_enable=False)
        glx_assert(resp.status_code == 201)

        # 清除接口计数
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear interfaces")
        glx_assert(err == '')

        # iperf打流
        _, err = self.topo.dut4.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns", "iperf3 -s -D")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "iperf3 -c 192.168.4.1 -t 10 -R")
        glx_assert(err == '')

        # link122 rx
        link_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 RxPackets")
        link_rx_packets = link_rx_packets.rstrip()
        glx_assert(err == '')
        link_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#122 RxBytes")
        link_rx_bytes = link_rx_bytes.rstrip()
        glx_assert(err == '')

        print("link122 rx: ", int(link_rx_bytes) / int(link_rx_packets))
        glx_assert(math.isclose(1400, int(link_rx_bytes) / int(link_rx_packets), abs_tol=200))

        tunnel_rx_packets, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#12 RxPackets")
        tunnel_rx_packets = tunnel_rx_packets.rstrip()
        glx_assert(err == '')
        tunnel_rx_bytes, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#12 RxBytes")
        tunnel_rx_bytes = tunnel_rx_bytes.rstrip()
        glx_assert(err == '')
        print("tunnel12 rx: ", int(tunnel_rx_bytes) / int(tunnel_rx_packets))
        glx_assert(math.isclose(1400, int(tunnel_rx_bytes) / int(tunnel_rx_packets), abs_tol=200))

        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol2")
        glx_assert(resp.status_code == 410)
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')
        _, err = self.topo.dut4.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns", "pkill iperf3")
        glx_assert(err == '')




if __name__ == '__main__':
    unittest.main()
