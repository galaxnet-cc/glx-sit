import unittest
import time

from topo.topo_1t_4d import Topo1T4D

# 有时候需要反复测试一个用例，可先打开SKIP_TEARDOWN执行一轮用例初始化
# 拓朴配置，然后打开SKIP_SETUP即可反复执行单个测试例。
#
# TODO: 后面开发active link通知删除能力后，就可以支持用例反复setup down
# 就需要打开setup/teardown，并支持在一个复杂拓朴下，测试多个测试例了。　
#
SKIP_SETUP = False
SKIP_TEARDOWN = False

class TestBasic1T4DAutoDns(unittest.TestCase):

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
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.1.1/24")
        # dut4 Lan 1 ip:
        self.topo.dut4.get_rest_device().set_default_bridge_ip("192.168.4.1/24")

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
        self.topo.dut3.get_rest_device().create_glx_tunnel(tunnel_id=23)
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
        self.topo.tst.add_ns_route("dut1", "192.168.4.0/24", "192.168.1.1")
        self.topo.tst.add_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")
        self.topo.tst.add_ns_route("dut4", "222.222.222.222/32", "192.168.4.1")

        # 等待link up
        # 端口注册时间5s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

        # dut2 dut4 link aging time update.
        # lower the timeout to make testcase not running that long happy
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f'vppctl set glx global passive-link-gc-time 15')
        assert (err == '')
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f'vppctl set glx global passive-link-gc-time 15')
        assert (err == '')

        # 为dnsmasq添加autodns.conf文件
        self.topo.tst.get_ns_cmd_result("dut4", "touch /tmp/autodns.conf")
        self.topo.tst.get_ns_cmd_result("dut4", "echo 'listen-address=192.168.4.2' > /tmp/autodns.conf")
        self.topo.tst.get_ns_cmd_result("dut4", "echo 'no-resolv' >> /tmp/autodns.conf")
        self.topo.tst.get_ns_cmd_result("dut4", "echo 'strict-order' >> /tmp/autodns.conf")
        self.topo.tst.get_ns_cmd_result("dut4", "echo 'address=/www.baidu.com/1.1.1.1' >> /tmp/autodns.conf")
        self.topo.tst.get_ns_cmd_result("dut4", "echo 'address=/www.google.com/2.2.2.2' >> /tmp/autodns.conf")

        # 为dut1设备的dnsmasq添加autodns.conf文件
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"touch /tmp/autodns.conf")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"echo 'listen-address=169.254.100.2' > /tmp/autodns.conf")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"echo 'no-resolv' >> /tmp/autodns.conf")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"echo 'strict-order' >> /tmp/autodns.conf")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"echo 'server=/www.baidu.com/192.168.4.2#53' >> /tmp/autodns.conf")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"echo 'server=/www.google.com/192.168.4.2#53' >> /tmp/autodns.conf")

    def tearDown(self):
        if SKIP_TEARDOWN:
            return
        
        # kill dnsmasq
        self.topo.tst.get_ns_cmd_result("dut4", "kill -9 $(pidof dnsmasq)")
        self.topo.tst.get_ns_cmd_result("dut4", "rm /tmp/autodns.conf")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"kill -9 $(pidof dnsmasq)")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"rm /tmp/autodns.conf")

        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="192.168.4.0/24")
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

        # 无条件恢复加速带来的配置改动
        self.topo.dut4.get_rest_device().delete_edge_route(route_prefix="222.222.222.222/32")
        self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=False)

        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="192.168.34.1/32")
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

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
        self.topo.dut4.get_rest_device().set_default_bridge_ip("192.168.88.0/24")

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)
        # dut2 dut4 link aging time update.
        # lower the timeout to make testcase not running that long happy
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f'vppctl set glx global passive-link-gc-time 120')
        assert (err == '')
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f'vppctl set glx global passive-link-gc-time 120')
        assert (err == '')

    #  测试加速流量
    def test_basic_traffic(self):
        # 这里的测试配置，需要在teardown中无条件进行各种清理，恢复系统到初始状态。

        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        assert(result.status_code == 200)
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)

        # 开启autodns
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="0x3400010")
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        assert(err == "")

        # dut4 (int edge)准备
        # 1. 配置回程路由　
        self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        assert(err == '')
        # 此时不应当再丢包
        assert("0% packet loss" in out)

        # dig并检测结果
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "dnsmasq -C /tmp/autodns.conf")
        assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.2 www.baidu.com +tries=5 +timeout=1")
        assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx auto-dns ips")
        assert(err == '')
        assert("1.1.1.1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 1.1.1.1/32")
        assert(err == '')
        assert("is_acc: 1" in out)

        # flush掉数据
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl flush glx auto-dns ips")
        assert(err == '')
        assert("1.1.1.1" not in out)

        # dig并检测结果
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.2 www.google.com +tries=5 +timeout=1")
        assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx auto-dns ips")
        assert(err == '')
        assert("2.2.2.2" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 2.2.2.2/32")
        assert(err == '')
        assert("is_acc: 1" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl flush glx auto-dns ips")
        assert(err == '')
        assert("2.2.2.2" not in out)

    def test_basic_dns_intercept(self):
        # 这里的测试配置，需要在teardown中无条件进行各种清理，恢复系统到初始状态。

        # dut1 (acc cpe) 准备
        # 1. 开启acc
        # 2. 设置加速ip
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        assert(result.status_code == 200)
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="192.168.4.0/24", route_label="0x3400010", is_acc=True)

        # 开启dns-intercept
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, dns_intercept_enable=True, acc_enable=True, route_label="0x3400010")
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        assert(err == "")

        # dut4 (int edge)准备
        # 1. 配置回程路由　
        self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        assert(err == '')
        # 此时不应当再丢包
        assert("0% packet loss" in out)

        # 开启dut1，dut4的dnsmasq的能力
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "dnsmasq -C /tmp/autodns.conf")
        assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns dnsmasq -C /tmp/autodns.conf")
        assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sysctl -w net.ipv4.conf.lo.rp_filter=0")
        assert(err == '')

        # dig并检测结果
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.3 www.baidu.com +tries=5 +timeout=1")
        assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx auto-dns ips")
        assert(err == '')
        assert("1.1.1.1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 1.1.1.1/32")
        assert(err == '')
        assert("is_acc: 1" in out)

        # flush掉数据
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl flush glx auto-dns ips")
        assert(err == '')
        assert("1.1.1.1" not in out)

        # dig并检测结果
        _, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.3 www.google.com +tries=5 +timeout=1")
        assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx auto-dns ips")
        assert(err == '')
        assert("2.2.2.2" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 2.2.2.2/32")
        assert(err == '')
        assert("is_acc: 1" in out)

        # flush掉数据
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl flush glx auto-dns ips")
        assert(err == '')
        assert("2.2.2.2" not in out)
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns iptables -t nat -F")
        assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sysctl -w net.ipv4.conf.lo.rp_filter=2")
        assert(err == '')

if __name__ == '__main__':
    unittest.main()
