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

class TestBasic1T4DDpi(unittest.TestCase):

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

        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN3")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN3")

        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")



        # 无论失败成功，都删除dns block rule
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("block_app_dns")
        # 重启一下vpp以便删除fast tuple.
        _, _ = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f'systemctl restart vpp')
        # 等待以便vpp能够重新配置好
        time.sleep(10)

        # wait for all passive link to be aged.
        time.sleep(20)

    # 测试dig工具被firewall拦截
    def dpi_block_app_dns(self):
        # dut1上打开dpi
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=True)
        # 清掉node计数，因为我们要通过计数来确定报文是否被firwall放行。
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl clear node counters")
        glx_assert(err == '')
        # dut4上ip上并不存在dns服务，只是采用此方式触发dns查询以及dpi能力
        # 多试几次避免arp查询丢失情况
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.2 www.baidu.com +tries=5 +timeout=1")
        glx_assert(err == '')
        # 首次应当需要识别并生成fast-tuple，所以会有流量被加密
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show node counters")
        glx_assert(err == '')
        glx_assert("ACL deny packets" not in out)
        # 221213: 不能检查esp了，因为tunnel bfd follow同样的路径，也会加密送到对方，以便验证加密通路可用。
        #glx_assert("esp4-encrypt" in out)
        # 检查是否有dns的fast-tuple生成
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx dpi fast-tuple4")
        glx_assert(err == '')
        glx_assert("app_port 53 app_id 5" in out)
        # 清掉node计数，因为我们要通过计数来确定报文是否被firwall放行。
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl clear node counters")
        glx_assert(err == '')
        # 添加firewall rule阻断dns报文（app id 5）
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "block_app_dns", 1, "0.0.0.0/0", action="Deny", app_id=5)
        # 此时fast-tuple还在，此时应当发不出dns报文了
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.2 www.baidu.com +tries=2 +timeout=1")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show node counters")
        glx_assert(err == '')
        # 221213: 不能检查esp了，因为tunnel bfd follow同样的路径，也会加密送到对方，以便验证加密通路可用。
        #glx_assert("esp4-encrypt" not in out)
        glx_assert("ACL deny packets" in out)
        # dut1上关闭dpi
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=False)

    def test_dpi_standalone_mode(self):
        # dut1上打开dpi
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=True, dpi_standalone=True)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.1.1 www.baidu.com +tries=5 +timeout=1")
        glx_assert(err == '')
        # 检查是否有dns的fast-tuple生成
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx dpi fast-tuple4")
        glx_assert(err == '')
        glx_assert("app_port 53 app_id 5" in out)
        # dut1上关闭dpi
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=False, dpi_standalone=False)

    # 测试dig工具被firewall拦截
    def test_dpi_standalone_mode_block_app_dns(self):
        # dut1上打开dpi
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=True, dpi_standalone=True)
        # 清掉node计数，因为我们要通过计数来确定报文是否被firwall放行。
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl clear node counters")
        glx_assert(err == '')
        # dut4上ip上并不存在dns服务，只是采用此方式触发dns查询以及dpi能力
        # 多试几次避免arp查询丢失情况
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.2 www.baidu.com +tries=5 +timeout=1")
        glx_assert(err == '')
        # 首次应当需要识别并生成fast-tuple，所以会有流量被加密
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show node counters")
        glx_assert(err == '')
        glx_assert("ACL deny packets" not in out)
        # 221213: 不能检查esp了，因为tunnel bfd follow同样的路径，也会加密送到对方，以便验证加密通路可用。
        #glx_assert("esp4-encrypt" in out)
        # 检查是否有dns的fast-tuple生成
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx dpi fast-tuple4")
        glx_assert(err == '')
        glx_assert("app_port 53 app_id 5" in out)
        # 清掉node计数，因为我们要通过计数来确定报文是否被firwall放行。
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl clear node counters")
        glx_assert(err == '')
        # 添加firewall rule阻断dns报文（app id 5）
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "block_app_dns", 1, "0.0.0.0/0", action="Deny", app_id=5)
        # 此时fast-tuple还在，此时应当发不出dns报文了
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "dig @192.168.4.2 www.baidu.com +tries=2 +timeout=1")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show node counters")
        glx_assert(err == '')
        # 221213: 不能检查esp了，因为tunnel bfd follow同样的路径，也会加密送到对方，以便验证加密通路可用。
        #glx_assert("esp4-encrypt" not in out)
        glx_assert("ACL deny packets" in out)
        # dut1上关闭dpi
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=False, dpi_standalone=False)


if __name__ == '__main__':
    unittest.main()
