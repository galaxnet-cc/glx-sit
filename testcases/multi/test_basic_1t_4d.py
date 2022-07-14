import unittest
import time

from topo.topo_1t_4d import Topo1T4D

class TestBasic1T4D(unittest.TestCase):

    # 创建一个最基本的配置场景：
    # dut1--wan1---dut2---wan3---dut3---wan1--dut4
    # |________88.0/24 tst ___ 89.0/24_________|
    #
    def setUp(self):
        self.topo = Topo1T4D()
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

        # 创建overlay route
        self.topo.dut1.get_rest_device().create_edge_route("192.168.4.0/24", route_label="0x3400010", tunnel_id1=12)
        self.topo.dut4.get_rest_device().create_edge_route("192.168.1.0/24", route_label="0x1200010", tunnel_id1=34)

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
        # 端口注册时间5s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
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
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.88.0/24")
        self.topo.dut4.get_rest_device().set_default_bridge_ip("192.168.88.0/24")

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

    #  测试icmp/udp/tcp流量
    def test_basic_traffic(self):
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        assert(err == '')
        # 此时不应当再丢包
        assert("0% packet loss" in out)

if __name__ == '__main__':
    unittest.main()
