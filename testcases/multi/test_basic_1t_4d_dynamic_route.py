import unittest
import time
import threading

from lib.util import glx_assert
from topo.topo_1t_4d import Topo1T4D

SKIP_SETUP = False
SKIP_TEARDOWN = False


class TestBasic1T4DDynamicRoute(unittest.TestCase):
    # 创建一个最基本的配置场景：
    # dut1--wan1---dut2---wan3---dut3---wan1--dut4
    # |________88.0/24 tst ___ 89.0/24_________|
    #
    # 该测试场景为dut1从tst(dut1)上收集路由(外部路由学习)，模拟控制器将路由下发到dut4上，确认tst(dut4)上能学习到路由
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
        time.sleep(15)

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

        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)

    def test_01_ospf(self):
        # tst(dut1)<->dut1
        segment = 0
        dut1ns = "dut1"
        dut4ns = "dut4"
        ctrl_ns = "ctrl-ns"
        area = "0.0.0.0"
        hello_interval = 10
        wait_interval = 4 * hello_interval
        address = "111.111.111.111"
        route = address + "/32"

        # 启动tst(dut1)下的watchfrr，并启动ospfd
        dut1_watchfrr_thread = threading.Thread(target=self.start_tst_watchfrr, args=(dut1ns, True, False))
        dut1_watchfrr_thread.daemon = True
        dut1_watchfrr_thread.start()

        # 保证watchfrr把所有的进程拉起来
        time.sleep(15)

        # 配置tst(dut1)，将tst的if1设置成ospf interface及area
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router ospf" -c "network 192.168.1.2/24 area {area}"'
        )
        glx_assert(err == '')

        # 配置dut1，直接通过rest api
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting(enableBGP=False)
        glx_assert(201 == resp.status_code)

        # 因为fwdmd是异步拉起watchfrr，所以最好sleep一下
        time.sleep(15)

        # 配置dut1，将br-default设置成ospf interface及area
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router ospf" -c "network 192.168.1.1/24 area {area}"'
        )
        glx_assert(err == '')

        # 等待hello interval + wait interval, 保证DR和BDR可以被选举出来
        time.sleep(hello_interval + wait_interval + 5)

        # 从tst(dut1)上发布路由，确认路由是否能被vpp收集
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "interface lo" -c "ip address {route}"'
        )
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router ospf" -c "redistribute connected"'
        )
        glx_assert(err == '')

        # 检查dut1上是否收集到路由
        # 等待同步路由
        time.sleep(15)

        # 检查目的地址
        dst, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#{segment}#{route}" "Dst"'
        )
        glx_assert (err == '')
        dst = dst.rstrip()
        glx_assert (dst == route)

        # 检查网关
        gw, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#{segment}#{route}" "Gw" '
        )
        glx_assert (err == '')
        gw = gw.rstrip()
        glx_assert (gw == '192.168.1.2')

        # 检查协议
        protocol, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#{segment}#{route}" "Protocol" '
        )
        protocol = protocol.rstrip()
        glx_assert (err == '')
        glx_assert (protocol == 'OSPF')

        # 检查vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table {segment} {route}'
        )
        glx_assert (err == '')
        glx_assert (route in out)
        # 检查vpp fib source
        glx_assert ('fpm-route' in out)
        glx_assert('API' not in out)

        # 撤销发布路由
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router ospf" -c "no redistribute connected"'
        )
        glx_assert(err == '')

        # 等待同步路由
        time.sleep(15)

        # redis key应该不存在
        out, _ = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli exists "ZebraRouteContext#{segment}#{route}"'
        )
        glx_assert("0" in out)

        # vpp中应该也不存在
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table {segment} {route}'
        )
        glx_assert (err == '')
        glx_assert (route not in out)

        # tst(dut4)<->dut4
        # 启动tst(dut4)下的watchfrr，并启动ospfd
        dut4_watchfrr_thread = threading.Thread(target=self.start_tst_watchfrr, args=(dut4ns, True, False))
        dut4_watchfrr_thread.daemon = True
        dut4_watchfrr_thread.start()

        # 保证watchfrr把所有的进程拉起来
        time.sleep(15)

        # 配置dut4，直接通过rest api
        resp = self.topo.dut4.get_rest_device().create_dynamic_routing_setting(enableBGP=False)
        glx_assert(201 == resp.status_code)

        # 因为fwdmd是异步拉起watchfrr，所以最好sleep一下
        time.sleep(15)

        # 配置tst(dut4)，将tst的if2设置成ospf interface及area
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut4ns} -c "config" -c "router ospf" -c "network 192.168.4.2/24 area {area}"'
        )
        glx_assert(err == '')

        # 配置dut4，将br-default设置成ospf interface及area
        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router ospf" -c "network 192.168.4.1/24 area {area}"'
        )
        glx_assert(err == '')

        # 重新发布路由表
        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "ip import-table 212" -c "router ospf" -c "redistribute table 212"'
        )
        glx_assert(err == '')

        # 等待hello interval + wait interval, 保证DR和BDR可以被选举出来
        time.sleep(hello_interval + wait_interval + 5)

        # 模拟controller将dut1收集过来的路由下发到dut4上
        resp = self.topo.dut4.get_rest_device().create_edge_route(route, "0xffffffffff", advertise_enable=True)
        glx_assert(201 == resp.status_code)

        # 等待同步路由
        time.sleep(15)

        # 此时tst(dut4)上应该要能查到路由
        out, err = self.topo.tst.get_ns_cmd_result(dut4ns, f"ip route show")
        glx_assert(err == '')
        glx_assert(address in out)

        # 撤销发布路由
        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router ospf" -c "no redistribute table 212"'
        )
        glx_assert(err == '')

        # 等待同步路由
        time.sleep(15)

        # 此时tst(dut4)上应该没有路由了
        out, err = self.topo.tst.get_ns_cmd_result(dut4ns, f"ip route show")
        glx_assert(err == '')
        glx_assert(address not in out)

        # 清理环境
        resp = self.topo.dut1.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut4.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut4.get_rest_device().delete_edge_route(route)
        glx_assert(410 == resp.status_code)
        self.stop_tst_watchfrr(dut1ns, True, False)
        self.stop_tst_watchfrr(dut4ns, True, False)
        self.topo.tst.del_ns_if_ip(dut1ns, "lo", route)

    def test_02_bgp(self):
        # tst(dut1)<->dut1
        segment = 0
        dut1ns = "dut1"
        dut4ns = "dut4"
        ctrl_ns = "ctrl-ns"
        tst_dut1_asn = 7675
        dut1_asn = 7676
        tst_dut4_asn = 7685
        dut4_asn = 7686
        address = "111.111.111.111"
        route = address + "/32"

        # 启动tst(dut1)下的watchfrr，并启动bgpd
        dut1_watchfrr_thread = threading.Thread(target=self.start_tst_watchfrr, args=(dut1ns, False, True))
        dut1_watchfrr_thread.daemon = True
        dut1_watchfrr_thread.start()

        # 保证watchfrr把所有的进程拉起来
        time.sleep(15)

        # 配置tst(dut1)，设置AS、Neighbor
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router bgp {tst_dut1_asn}" -c "no bgp ebgp-requires-policy" -c "bgp router-id 192.168.1.2" -c "neighbor 192.168.1.1 remote-as {dut1_asn}"'
        )
        glx_assert(err == '')

        # 配置dut1，直接通过rest api
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting(enableOSPF=False)
        glx_assert(201 == resp.status_code)

        # 因为fwdmd是异步拉起watchfrr，所以最好sleep一下
        time.sleep(15)

        # 配置dut1，设置AS、Neighbor
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router bgp {dut1_asn}" -c "no bgp ebgp-requires-policy" -c "bgp router-id 192.168.1.1" -c "neighbor 192.168.1.2 remote-as {tst_dut1_asn}"'
        )
        glx_assert(err == '')

        # 等待建立连接
        time.sleep(15)

        # 从tst(dut1)上发布路由，确认路由是否能被vpp收集
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "interface lo" -c "ip address {route}"'
        )
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router bgp {tst_dut1_asn}" -c "redistribute connected"'
        )
        glx_assert(err == '')

        # 等待同步路由
        time.sleep(15)

        # 检查目的地址
        dst, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#{segment}#{route}" "Dst"'
        )
        glx_assert (err == '')
        dst = dst.rstrip()
        glx_assert (dst == route)

        # 检查网关
        gw, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#{segment}#{route}" "Gw" '
        )
        glx_assert (err == '')
        gw = gw.rstrip()
        glx_assert (gw == '192.168.1.2')

        # 检查协议
        protocol, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#{segment}#{route}" "Protocol" '
        )
        protocol = protocol.rstrip()
        glx_assert (err == '')
        glx_assert (protocol == 'BGP')

        # 检查vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table {segment} {route}'
        )
        glx_assert (err == '')
        glx_assert (route in out)
        # 检查vpp fib source
        glx_assert ('fpm-route' in out)
        glx_assert('API' not in out)

        # 撤销发布路由
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router bgp {tst_dut1_asn}" -c "no redistribute connected"'
        )
        glx_assert(err == '')

        # 等待同步路由
        time.sleep(15)

        # redis key应该不存在
        out, _ = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli exists "ZebraRouteContext#{segment}#{route}"'
        )
        glx_assert("0" in out)

        # vpp中应该也不存在
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table {segment} {route}'
        )
        glx_assert (err == '')
        glx_assert (route not in out)

        # tst(dut4)<->dut4
        # 启动tst(dut4)下的watchfrr，并启动bgpd
        dut4_watchfrr_thread = threading.Thread(target=self.start_tst_watchfrr, args=(dut4ns, False, True))
        dut4_watchfrr_thread.daemon = True
        dut4_watchfrr_thread.start()

        # 保证watchfrr把所有的进程拉起来
        time.sleep(15)

        # 配置dut4，直接通过rest api
        resp = self.topo.dut4.get_rest_device().create_dynamic_routing_setting(enableOSPF=False)
        glx_assert(201 == resp.status_code)

        # 因为fwdmd是异步拉起watchfrr，所以最好sleep一下
        time.sleep(15)

        # 配置tst(dut4)，设置AS、Neighbor
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut4ns} -c "config" -c "router bgp {tst_dut4_asn}" -c "no bgp ebgp-requires-policy" -c "bgp router-id 192.168.4.2" -c "neighbor 192.168.4.1 remote-as {dut4_asn}"'
        )
        glx_assert(err == '')

        # 配置dut4，设置AS、Neighbor
        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router bgp {dut4_asn}" -c "no bgp ebgp-requires-policy" -c "bgp router-id 192.168.4.1" -c "neighbor 192.168.4.2 remote-as {tst_dut4_asn}"'
        )
        glx_assert(err == '')

        # 重新发布路由表
        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "ip import-table 212" -c "router bgp {dut4_asn}" -c "redistribute table 212"'
        )
        glx_assert(err == '')

        # 等待建立连接
        time.sleep(15)

        # 模拟controller将dut1收集过来的路由下发到dut4上
        resp = self.topo.dut4.get_rest_device().create_edge_route(route, "0xffffffffff", advertise_enable=True)
        glx_assert(201 == resp.status_code)

        # 等待同步路由
        time.sleep(15)

        # 此时tst(dut4)上应该要能查到路由
        out, err = self.topo.tst.get_ns_cmd_result(dut4ns, f"ip route show")
        glx_assert(err == '')
        glx_assert(address in out)

        # 撤销发布路由
        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router bgp {dut4_asn}" -c "no redistribute table 212"'
        )
        glx_assert(err == '')

        # 等待同步路由
        time.sleep(15)

        # 此时tst(dut4)上应该没有路由了
        out, err = self.topo.tst.get_ns_cmd_result(dut4ns, f"ip route show")
        glx_assert(err == '')
        glx_assert(address not in out)

        # 清理环境
        resp = self.topo.dut1.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut4.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut4.get_rest_device().delete_edge_route(route)
        glx_assert(410 == resp.status_code)
        self.stop_tst_watchfrr(dut1ns, False, True)
        self.stop_tst_watchfrr(dut4ns, False, True)
        self.topo.tst.del_ns_if_ip(dut1ns, "lo", route)

    def test_03_mix(self):
        # tst(dut1)<->dut1
        segment = 0
        dut1ns = "dut1"
        dut4ns = "dut4"
        ctrl_ns = "ctrl-ns"
        tst_dut4_asn = 7685
        dut4_asn = 7686
        area = "0.0.0.0"
        hello_interval = 10
        wait_interval = 4 * hello_interval
        address1 = "111.111.111.111"
        address2 = "222.222.222.222"
        route1 = address1 + "/32"
        route2 = address2 + "/32"

        # 启动tst(dut1)下的watchfrr，并启动ospf
        dut1_watchfrr_thread = threading.Thread(target=self.start_tst_watchfrr, args=(dut1ns, True, False))
        dut1_watchfrr_thread.daemon = True
        dut1_watchfrr_thread.start()
        # 保证watchfrr把所有的进程拉起来
        time.sleep(15)

        # 配置tst(dut1)，将tst的if1设置成ospf interface及area
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router ospf" -c "network 192.168.1.2/24 area {area}"'
        )
        glx_assert(err == '')

        # 配置dut1，直接通过rest api
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting(enableBGP=False)
        glx_assert(201 == resp.status_code)

        # 因为fwdmd是异步拉起watchfrr，所以最好sleep一下
        time.sleep(15)

        # 配置dut1，将br-default设置成ospf interface及area
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router ospf" -c "network 192.168.1.1/24 area {area}"'
        )
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "ip import-table 212" -c "router ospf" -c "redistribute table 212"'
        )
        glx_assert(err == '')

        # 等待hello interval + wait interval, 保证DR和BDR可以被选举出来
        time.sleep(hello_interval + wait_interval + 5)

        # 从tst(dut1)上发布路由
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "interface lo" -c "ip address {route1}"'
        )
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut1ns} -c "config" -c "router ospf" -c "redistribute connected"'
        )
        glx_assert(err == '')

        # 将tst(dut4)路由同步到dut1下游路由器tst(dut1)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route2, route_label="0x3400010", advertise_enable=True)
        glx_assert(201 == resp.status_code)

        # 等待同步路由
        time.sleep(15)

        # tst(dut4)<->dut4
        # 启动tst(dut4)下的watchfrr，并启动bgpd
        dut4_watchfrr_thread = threading.Thread(target=self.start_tst_watchfrr, args=(dut4ns, False, True))
        dut4_watchfrr_thread.daemon = True
        dut4_watchfrr_thread.start()

        # 保证watchfrr把所有的进程拉起来
        time.sleep(15)

        # 配置dut4，直接通过rest api
        resp = self.topo.dut4.get_rest_device().create_dynamic_routing_setting(enableOSPF=False)
        glx_assert(201 == resp.status_code)

        # 因为fwdmd是异步拉起watchfrr，所以最好sleep一下
        time.sleep(15)

        # 配置tst(dut4)，设置AS、Neighbor
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut4ns} -c "config" -c "router bgp {tst_dut4_asn}" -c "no bgp ebgp-requires-policy" -c "bgp router-id 192.168.4.2" -c "neighbor 192.168.4.1 remote-as {dut4_asn}"'
        )
        glx_assert(err == '')

        # 配置dut4，设置AS、Neighbor
        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "router bgp {dut4_asn}" -c "no bgp ebgp-requires-policy" -c "bgp router-id 192.168.4.1" -c "neighbor 192.168.4.2 remote-as {tst_dut4_asn}"'
        )
        glx_assert(err == '')

        # 等待建立连接
        time.sleep(15)

        # 从tst(dut4)上发布路由，确认路由是否能被vpp收集
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut4ns} -c "config" -c "interface lo" -c "ip address {route2}"'
        )
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(
            f'vtysh -N {dut4ns} -c "config" -c "router bgp {tst_dut4_asn}" -c "redistribute connected"'
        )
        glx_assert(err == '')

        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N {ctrl_ns} -c "config" -c "ip import-table 212" -c "router bgp {dut4_asn}" -c "redistribute table 212"'
        )
        glx_assert(err == '')

        # 将tst(dut1)路由同步到dut4下游路由器tst(dut4)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route1, route_label="0x1200010", advertise_enable=True)
        glx_assert(201 == resp.status_code)

        # 等待同步路由
        time.sleep(15)

        # 测试是否能够ping通
        out, err = self.topo.tst.get_ns_cmd_result("dut1", f"ping -I {address1} {address2} -c 5 -i 0.05")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)

        # 清理环境
        resp = self.topo.dut1.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut4.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut4.get_rest_device().delete_edge_route(route1)
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().delete_edge_route(route2)
        glx_assert(410 == resp.status_code)
        self.stop_tst_watchfrr(dut1ns, True, False)
        self.stop_tst_watchfrr(dut4ns, False, True)
        self.topo.tst.del_ns_if_ip(dut1ns, "lo", route1)
        self.topo.tst.del_ns_if_ip(dut4ns, "lo", route2)

    def start_tst_watchfrr(self, ns: str, ospf: bool, bgp: bool):
        cfg_path = f"/etc/frr/{ns}"
        run_path =  f"/var/run/frr/{ns}"

        # 为了pid能建起来
        self.topo.tst.get_cmd_result(f"mkdir -p {run_path}")
        self.topo.tst.get_cmd_result(f"chmod 777 {run_path}")

        # 创建配置目录，写入配置文件
        self.topo.tst.get_cmd_result(f"mkdir -p {cfg_path}")
        self.topo.tst.get_cmd_result(f'echo \'zebra_options=" -A 127.0.0.1 -s 90000000"\' > {cfg_path}/daemons')
        self.topo.tst.get_cmd_result(f'touch {cfg_path}/frr.conf')
        self.topo.tst.get_cmd_result(f'touch {cfg_path}/vtysh.conf')

        # 启动watchfrr，zebra必须启动
        watchfrr_cmd = f"/usr/lib/frr/watchfrr -d -N {ns} --netns zebra mgmtd"
        if ospf:
            watchfrr_cmd += " ospfd"
        if bgp:
            watchfrr_cmd += " bgpd"
        self.topo.tst.get_cmd_result(watchfrr_cmd)

    def stop_tst_watchfrr(self, ns: str, ospf: bool, bgp: bool):
        cfg_path = f"/etc/frr/{ns}"
        run_path =  f"/var/run/frr/{ns}"

        # 读取所有的pid，并关闭，必须先关闭watchfrr
        pid, err = self.topo.tst.get_cmd_result(f"cat {run_path}/watchfrr.pid")
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(f"kill -9 {pid}")
        glx_assert(err == '')

        # staticd
        pid, err = self.topo.tst.get_cmd_result(f"cat {run_path}/staticd.pid")
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(f"kill -9 {pid}")
        glx_assert(err == '')

        # mgmtd
        pid, err = self.topo.tst.get_cmd_result(f"cat {run_path}/mgmtd.pid")
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(f"kill -9 {pid}")
        glx_assert(err == '')

        # zebra
        pid, err = self.topo.tst.get_cmd_result(f"cat {run_path}/zebra.pid")
        glx_assert(err == '')
        _, err = self.topo.tst.get_cmd_result(f"kill -9 {pid}")
        glx_assert(err == '')

        # ospfd
        if ospf:
            pid, err = self.topo.tst.get_cmd_result(f"cat {run_path}/ospfd.pid")
            glx_assert(err == '')
            _, err = self.topo.tst.get_cmd_result(f"kill -9 {pid}")
            glx_assert(err == '')

        # bgpd
        if bgp:
            pid, err = self.topo.tst.get_cmd_result(f"cat {run_path}/bgpd.pid")
            glx_assert(err == '')
            _, err = self.topo.tst.get_cmd_result(f"kill -9 {pid}")
            glx_assert(err == '')

        # 清理环境
        self.topo.tst.get_cmd_result(f"rm -rf {run_path}")
        self.topo.tst.get_cmd_result(f"rm -rf {cfg_path}")
