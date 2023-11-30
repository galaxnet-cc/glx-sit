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

    #  测试icmp/udp/tcp流量
    def test_basic_traffic(self):
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)
        # 测试ping bvi
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.1 -c 5 -i 0.05")
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

    # 测试tunnel bfd联动机制以及fwdmd
    def test_tunnel_bfd(self):
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 清除事件队列
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli del /glx/eventqueue/TunnelStateEvent")
        glx_assert(err == '')
        # 将WAN1接口设置为down状态
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {wan1VppIf} down")
        glx_assert(err == '')
        # 5s is enough for event being handled and event generated.
        # tunnel bfd is 3*1 interval.
        time.sleep(5)
        # 读取事件队列
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli lpop /glx/eventqueue/TunnelStateEvent")
        glx_assert(err == '')
        glx_assert("TunnelId\":12" in out)
        glx_assert("IsUp\":false" in out)

        # 将WAN1接口设置为up状态
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {wan1VppIf} up")
        glx_assert(err == '')

        # 10s足够link & bfd恢复了
        time.sleep(10)
        # 读取事件队列
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli lpop /glx/eventqueue/TunnelStateEvent")
        glx_assert(err == '')
        glx_assert("TunnelId\":12" in out)
        glx_assert("IsUp\":true" in out)

        # 暂停fwdmd，模拟fwdmd重启过程中消息丢失场景
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"systemctl stop fwdmd")
        glx_assert(err == '')

        # 将WAN1接口设置为down状态
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {wan1VppIf} down")
        glx_assert(err == '')
        # 确保bfd down掉
        time.sleep(5)

        # 重启fwdmd，确保fwdm启动后重新拉取到bfd down消息。
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"systemctl start fwdmd")
        glx_assert(err == '')
        # 确保fwdmd重启ok
        time.sleep(10)
        # 读取事件队列
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli lpop /glx/eventqueue/TunnelStateEvent")
        glx_assert(err == '')
        glx_assert("TunnelId\":12" in out)
        glx_assert("IsUp\":false" in out)

        # 将WAN1接口设置为up状态
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {wan1VppIf} up")
        glx_assert(err == '')
        # 确保bfd up
        # 因为前面一共down掉了(5+10)，passive link被老化，对端ikev2 sa被移除。
        # 30s足够应该足够恢复（ikev2 sa keepalive detect time为3 * 5s）
        time.sleep(30)

        # 读取事件队列
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli lpop /glx/eventqueue/TunnelStateEvent")
        glx_assert(err == '')
        glx_assert("TunnelId\":12" in out)
        glx_assert("IsUp\":true" in out)

        # 模拟vpp重启
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"systemctl restart vpp")
        glx_assert(err == '')
        # 等待fwdmd检测vpp重启，并重新下发所有状态。
        # 20s足够了
        time.sleep(30)

        # 读取事件队列（此时需要控制平面支持处理重复up上报）
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli lpop /glx/eventqueue/TunnelStateEvent")
        glx_assert(err == '')
        glx_assert("TunnelId\":12" in out)
        glx_assert("IsUp\":true" in out)

        # 检测经过这些场景验证，业务仍能恢复。
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

    def test_bizpol_overlay_enable(self):
        # remove route.
        self.topo.dut1.get_rest_device().delete_edge_route("192.168.4.0/24")
        # use bizpol to steering the traffic.
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.4.0/24",
                                                       protocol=0,
                                                       overlay_enable=True,
                                                       route_label="0x3400010")

        # 测试流量
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 移除配置
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        # 无需移除路由，依赖setup.

    def test_bizpol_order(self):
        for name in self.topo.dut1.get_if_map():
            if name != "WAN1":
                self.topo.dut1.get_rest_device().set_logical_interface_nat_direct(name, False)
        # 随意配置一条无效的全加速规则
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=100,
                                                       src_prefix="0.0.0.0/0",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       overlay_enable=True,
                                                       acc_enable=True,
                                                       route_label="0x1")

        # 确认默认的策略生效, ping dut2 wan
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns", "ping 192.168.12.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns", "ping 192.168.12.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 移除配置
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        # 无需移除路由，依赖setup.
        for name in self.topo.dut1.get_if_map():
            if name != "WAN1":
                self.topo.dut1.get_rest_device().set_logical_interface_nat_direct(name, True)

    def test_link_transport_update(self):
        # 增加wan2一路配置。
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.122.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.122.2/24")

        # 更新link参数
        self.topo.dut1.get_rest_device().update_glx_link_wan(link_id=12, wan_name="WAN2")
        self.topo.dut1.get_rest_device().update_glx_link_remote_ip(link_id=12, remote_ip="192.168.122.2")

        # 等待10s
        time.sleep(10)

        # 测试更新后流量可以通达
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # WAN口配置在teardown中恢复之

if __name__ == '__main__':
    unittest.main()
