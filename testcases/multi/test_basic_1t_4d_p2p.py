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

class TestBasic1T4DP2P(unittest.TestCase):

    # 创建一个CPE直连的场景
    # dut1(cpe1)--wan1/wan2---dut2(cpe2)
    # |___88.0/24          |___89.0/24
    #
    # 基于tst访问dut2的bvi ip来验证可达性
    # 并验证双link
    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return

        # 1<>2 192.168.12.0/24
        # WAN1.
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.2/24")
        # WAN2.
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.122.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.122.2/24")

        mtu = 1500
        # dut1 Lan 1 ip:
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.1.1/24", mtu=mtu)
        # dut4 Lan 1 ip:
        self.topo.dut2.get_rest_device().set_default_bridge_ip_or_mtu("192.168.2.1/24", mtu=mtu)

        # create dut1<>dut2 tunnel.
        # LINK在用例中按需创建.
        # DUT2作为被动方不需要创建tunnel.
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=12)

        # create dut1 route label policy.
        self.topo.dut1.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x1200010", table_id=0)
        # create dut2 route label pocliy.
        self.topo.dut2.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x2100010", table_id=0)

        # 创建overlay route以及default edge route label fwd entry
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=12)
        self.topo.dut1.get_rest_device().create_edge_route("192.168.2.0/24", route_label="0x2100010")
        # Edge route label fwd这里不配置，由用例根据需要配置
        # self.topo.dut2.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=12)
        self.topo.dut2.get_rest_device().create_edge_route("192.168.1.0/24", route_label="0x1200010")

        # 初始化tst接口
        self.topo.tst.add_ns("dut1")
        self.topo.tst.add_if_to_ns(self.topo.tst.if1, "dut1")

        # 添加tst节点ip及路由
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.add_ns_route("dut1", "192.168.2.0/24", "192.168.1.1")

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")

        # 删除edge route.
        self.topo.dut1.get_rest_device().delete_edge_route("192.168.2.0/24")
        self.topo.dut2.get_rest_device().delete_edge_route("192.168.1.0/24")

        # 删除label-fwd表项
        # 更新default entry route label entry解除tunnel引用
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)

        # 删除dut1/2资源
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=12)

        # 删除label policy.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x1200010")
        # create dut2 route label pocliy.
        self.topo.dut2.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x2100010")

        # revert to default.
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)
        self.topo.dut2.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")

        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")

        # wait for all passive link to be aged.
        time.sleep(20)

    # 测试显式配置edge route label fwd表项
    def test_p2p_explit_erlfe(self):
        # 创建双link(不指定route label).
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN2",
                                                         remote_ip="192.168.122.2", remote_port=2288,
                                                         tunnel_id=12)
        # DUT2配置显式edge route label fwd表项
        self.topo.dut2.get_rest_device().create_glx_edge_route_label_fwd("0x1200010", 12)

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

        # 第一轮测试: 双link.
        # 测试dut2 bvi即可
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.2.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.2.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 第二轮测试：单link.
        self.topo.dut1.get_rest_device().delete_glx_link(122)
        # 仍应当可达
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.2.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 清除配置.
        self.topo.dut1.get_rest_device().delete_glx_link(12)
        self.topo.dut2.get_rest_device().delete_glx_edge_route_label_fwd("0x1200010")


    # 将dut2配置为edge role，并在link上指定route label，从而触发dut2自动下发route label fwd表项
    def test_p2p_auto_erlfe(self):
        # 将dut2指定为edge角色
        self.topo.dut2.get_rest_device().set_global_cfg(role_is_edge=True)
        # 创建双link（指定route-label.）
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        self.topo.dut1.get_rest_device().create_glx_link(link_id=122, wan_name="WAN2",
                                                         remote_ip="192.168.122.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")
        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        # erlfe表项自动创建
        glx_assert("1200010" in out)

        # 第一轮测试: 双link.
        # 测试dut2 bvi即可
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.2.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.2.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 第二轮测试：单link.
        self.topo.dut1.get_rest_device().delete_glx_link(122)
        # 仍应当可达
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.2.1 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 第三轮测试：删除link，等待link gc掉后erlfe表项删除。
        self.topo.dut1.get_rest_device().delete_glx_link(12)
        time.sleep(20)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        # erlfe表项被自动删除
        glx_assert("1200010" not in out)

        # 清除配置
        result = self.topo.dut2.get_rest_device().set_global_cfg(role_is_edge=False)
        glx_assert(result.status_code == 200)

if __name__ == '__main__':
    unittest.main()
