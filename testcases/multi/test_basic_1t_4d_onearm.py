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

class TestBasic1T4DOneArm(unittest.TestCase):

    # 创建一个最基本的one arm场景：
    # tst(linuxif5)---------
    #                       \
    # dut1--wan5(单臂模式)--<one-arm-br>---<linux-router>-<uplink-br>-wan5--dut2---wan3---dut3---wan1--dut4
    #
    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return

        # dut1与dut2的link/tunnel配置，在测试例中执行。

        # 配置dut2到uplink-br的ip+gw
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip_gw("WAN5", "192.168.202.2/24", "192.168.202.1")

        # 2<>3 192.168.23.0/24
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.1/24")
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN3", "192.168.23.2/24")
        # 3<>4 192.168.34.0/24
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.1/24")
        self.topo.dut4.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.2/24")

        # dut4 Lan 1 ip:
        self.topo.dut4.get_rest_device().set_default_bridge_ip("192.168.4.1/24")

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
        # to dut1.
        self.topo.dut3.get_rest_device().create_glx_route_label_fwd(route_label="0x1200000", tunnel_id1=23)

        # 创建overlay route以及default edge route label fwd entry
        self.topo.dut4.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=34)
        # 单臂模式下, dut1采用如下两个网段用于回访，这部分路由固定，因此预下好
        self.topo.dut4.get_rest_device().create_edge_route("192.168.201.0/24", route_label="0x1200010")
        self.topo.dut4.get_rest_device().create_edge_route("201.201.201.201/32", route_label="0x1200010")

        # 初始化tst接口
        self.topo.tst.add_ns("dut1")
        self.topo.tst.add_ns("dut4")
        # 接口移入ns后，就不会自动分地址了，我们就可以自己控制了
        self.topo.tst.add_if_to_ns(self.topo.tst.if5, "dut1")
        self.topo.tst.add_if_to_ns(self.topo.tst.if2, "dut4")

        # 添加tst节点ip及路由
        # 配置一个假地址到lo口
        self.topo.tst.add_ns_if_ip("dut1", "lo", "201.201.201.201/32")
        # 100-200为dhcp地址端，0-100为静态ip范围，200-255为tst所用ip
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if5, "192.168.201.201/24")
        # ns内路由因涉及到dhcp，因此这部分需要在用例里配置。
        # self.topo.tst.add_ns_route("dut1", "192.168.4.0/24", "192.168.201.2")
        self.topo.tst.add_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")
        # 单臂模式下dut1采用如下固定网段
        self.topo.tst.add_ns_route("dut4", "192.168.201.0/24", "192.168.4.1")
        self.topo.tst.add_ns_route("dut4", "201.201.201.201/32", "192.168.4.1")

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if5, "192.168.201.201/24")
        self.topo.tst.del_ns_if_ip("dut1", "lo", "201.201.201.201/32")
        self.topo.tst.del_ns_if_ip("dut4", self.topo.tst.if2, "192.168.4.2/24")

        # 删除edge route.
        self.topo.dut4.get_rest_device().delete_edge_route("192.168.201.0/24")
        self.topo.dut4.get_rest_device().delete_edge_route("201.201.201.201/32")

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

        # 删除label policy.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x1200010")
        # create dut4 route label pocliy.
        self.topo.dut4.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x3400010")

        # revert to default.
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.88.0/24")
        self.topo.dut4.get_rest_device().set_default_bridge_ip("192.168.88.0/24")

        # WAN5恢复至dhcp模式
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN5")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    # 测试以static ip地址方式配置one arm.
    def test_one_arm_static_ip(self):
        # 以宿主机ip的one arm br ip为网关，此地址由拓朴设计规定
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip_gw("WAN5", "192.168.201.2/24", "192.168.201.1")
        # 开启one arm模式
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN5", True)
        glx_assert(result.status_code == 200)

        # TEST1: 测试tst访问NAT场景(以uplink br ip为目标)
        self.topo.tst.add_ns_route("dut1", "192.168.202.0/24", "192.168.201.2")
        # 配置bizpol
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol-dut2-wan5-nat", priority=1,
                                                       src_prefix="192.168.201.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       # 强制选择WAN5，避免影响
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN5",
                                                       direct_enable=True)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.202.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.202.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # TEST2: 测试tst访问组网场景（one arm网段 + one arm跨网）
        # 配置到dut4的路由
        self.topo.tst.add_ns_route("dut1", "192.168.4.0/24", "192.168.201.2")
        # 配置到tst dut4 的edge route.
        self.topo.dut1.get_rest_device().create_edge_route("192.168.4.0/24", route_label="0x3400010")
        # 创建dut1到dut2的link
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=12)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN5",
                                                         remote_ip="192.168.202.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        # edge route label fwd.
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=12)

        # 等待link建立
        time.sleep(10)

        # 验证one arm网关通达性
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 验证one arm跨网段通达性
        # 需要先给DUT1添加一条到tst lo地址（用于跨网访问）的static路由.
        self.topo.dut1.get_rest_device().create_edge_route("201.201.201.201/32", route_label="0xffffffffff",
                                                           route_protocol="static",
                                                           # ts linuxif5 ip.
                                                           next_hop_ip="192.168.201.201")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping -I 201.201.201.201 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping -I 201.201.201.201 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包0
        glx_assert("0% packet loss" in out)

        # TEST3: 验证被one arm移至ctrl-ns内的WAN5可以承载tcp业务
        # one arm内网可访问
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns pkill nc")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns sh -c 'nohup nc -l -v -n 192.168.201.2 8888 > /dev/null 2>&1 &'")
        glx_assert(err == '')
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "sh -c 'nohup nc -w 3 -v 192.168.201.2 8888 > /tmp/one_arm_nc_test.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/one_arm_nc_test.txt")
        glx_assert(err == '')
        glx_assert("Connection to 192.168.201.2 8888 port [tcp/*] succeeded!" in out)
        # dut4组网可访问
        # 此场景暂不支持，因为目前lcp接口的punt机制，要求必须是从IP所在接口过来，单臂模式下
        # 上面的测试环境必然正确，而从隧道过来的情况，则不符合这个条件。
        # 从vppctl show ip punt redirect可以看到
        #   [@3]: ip4-dvr-tap6-dpo l3
        # rx GigabitEthernetc/0/0 via:
        # path-list:[29] locks:1 flags:no-uRPF, uRPF-list: None
        # path:[31] pl-index:29 ip4 weight=1 pref=0 dvr:  oper-flags:resolved,
        # tap7
        # forwarding
        # 未来如果需要支持，可以添加一条从segment loop if或者tunnel接口来身来的punt表项即可。
        # _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns pkill nc")
        # glx_assert(err == '')
        # _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns sh -c 'nohup nc -l -v -n 192.168.201.2 8888 > /dev/null 2>&1 &'")
        # glx_assert(err == '')
        # out, err = self.topo.tst.get_ns_cmd_result("dut4", "sh -c 'nohup nc -w 3 -v 192.168.201.2 8888 > /tmp/one_arm_nc_test.txt 2>&1 &'")
        # glx_assert(err == '')
        # time.sleep(3)
        # out, err = self.topo.tst.get_ns_cmd_result("dut4", "cat /tmp/one_arm_nc_test.txt")
        # glx_assert(err == '')
        # glx_assert("Connection to 192.168.201.2 8888 port [tcp/*] succeeded!" in out)

        # 清除配置
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)

        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=12)

        self.topo.dut1.get_rest_device().delete_edge_route("192.168.4.0/24")

        self.topo.dut1.get_rest_device().delete_edge_route("201.201.201.201/32", route_protocol="static")

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol-dut2-wan5-nat")

        self.topo.tst.del_ns_route("dut1", "192.168.202.0/24", "192.168.201.2")
        self.topo.tst.del_ns_route("dut1", "192.168.4.0/24", "192.168.201.2")

        # 关闭one arm模式
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN5", False)
        glx_assert(result.status_code == 200)
        # 恢复接口为dhcp模式
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN5")

    # 测试以dhcp地址方式配置one arm.
    def test_one_arm_dhcp(self):
        # 以宿主机ip的one arm br ip为网关，此地址由拓朴设计规定
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN5")
        # 确保dhcp得到ip地址
        time.sleep(10)
        wan5VppIf = self.topo.dut1.get_if_map()["WAN5"]
        dhcpIp, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan5VppIf} | grep fib | awk '{{print $2}}' | awk -F/ '{{print $1}}'")
        glx_assert(err == '')
        glx_assert("192.168.201" in dhcpIp)
        tableId, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan5VppIf} | grep fib | awk '{{print $5}}'")
        glx_assert(err == '')
        print("one arm mode get dhcp ip " + dhcpIp)
        print("one arm mode get wan5 table id " + tableId)

        # 因为one-arm br处于isolated模式,它并不推送gw地址，这里我们手工配下路由到vpp
        # 网关地址是设计决定为201.1
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl ip route add 0.0.0.0/0 table {tableId} via 192.168.201.1 {wan5VppIf}")
        glx_assert(err == '')

        # 开启one arm模式
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN5", True)
        glx_assert(result.status_code == 200)

        # TEST1: 测试tst访问NAT场景(以uplink br ip为目标)
        self.topo.tst.add_ns_route("dut1", "192.168.202.0/24", dhcpIp)
        # 配置bizpol
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol-dut2-wan5-nat", priority=1,
                                                       src_prefix="192.168.201.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       # 强制选择WAN5，避免影响
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN5",
                                                       direct_enable=True)

        out, err = self.topo.tst.get_ns_cmd_result("dut1", f"ping {dhcpIp} -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", f"ping {dhcpIp} -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # TEST2: 测试tst访问组网场景（one arm网段 + one arm跨网）
        # 配置到dut4的路由
        self.topo.tst.add_ns_route("dut1", "192.168.4.0/24", dhcpIp)
        # 配置到tst dut4 的edge route.
        self.topo.dut1.get_rest_device().create_edge_route("192.168.4.0/24", route_label="0x3400010")
        # 创建dut1到dut2的link
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=12)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN5",
                                                         remote_ip="192.168.202.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        # edge route label fwd.
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=12)

        # 等待link建立
        time.sleep(10)

        # 验证one arm网关通达性
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 验证one arm跨网段通达性
        # 需要先给DUT1添加一条到tst lo地址（用于跨网访问）的static路由.
        self.topo.dut1.get_rest_device().create_edge_route("201.201.201.201/32", route_label="0xffffffffff",
                                                           route_protocol="static",
                                                           # ts linuxif5 ip.
                                                           next_hop_ip="192.168.201.201")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping -I 201.201.201.201 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping -I 201.201.201.201 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包0
        glx_assert("0% packet loss" in out)

        # TEST3: 验证被one arm移至ctrl-ns内的WAN5可以承载tcp业务
        # one arm内网可访问
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns pkill nc")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns sh -c 'nohup nc -l -v -n {dhcpIp} 8888 > /dev/null 2>&1 &'")
        glx_assert(err == '')
        out, err = self.topo.tst.get_ns_cmd_result("dut1", f"sh -c 'nohup nc -w 3 -v {dhcpIp} 8888 > /tmp/one_arm_nc_test.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/one_arm_nc_test.txt")
        glx_assert(err == '')
        glx_assert(f"Connection to {dhcpIp} 8888 port [tcp/*] succeeded!" in out)

        # 清除配置
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)

        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=12)

        self.topo.dut1.get_rest_device().delete_edge_route("192.168.4.0/24")

        self.topo.dut1.get_rest_device().delete_edge_route("201.201.201.201/32", route_protocol="static")

        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol-dut2-wan5-nat")

        self.topo.tst.del_ns_route("dut1", "192.168.202.0/24", dhcpIp)
        self.topo.tst.del_ns_route("dut1", "192.168.4.0/24", dhcpIp)

        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl ip route del 0.0.0.0/0 table {tableId} via 192.168.201.1 {wan5VppIf}")
        glx_assert(err == '')


        # 关闭one arm模式
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN5", False)
        glx_assert(result.status_code == 200)

if __name__ == '__main__':
    unittest.main()
