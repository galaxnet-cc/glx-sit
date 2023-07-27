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

class TestBasic1T4DObjectGroup(unittest.TestCase):

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


    def test_firewall_with_obj_group(self):
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 创建group
        self.topo.dut1.get_rest_device().create_addr_group(group_name="addrgroup1", addr_with_prefix1="192.168.4.2/32")
        # 添加firewall rule阻断
        self.topo.dut1.get_rest_device().set_fire_wall_rule(rule_name="firewall_test", priority=1,
                                                            dest_address="0.0.0.0/0",
                                                            action="Deny",
                                                            dst_addr_group="addrgroup1")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时应当不通
        glx_assert("100% packet loss" in out)
        # 删除firewall rule
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("firewall_test")
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时应当恢复
        glx_assert("0% packet loss" in out)
        # 删除group
        self.topo.dut1.get_rest_device().delete_addr_group(group_name="addrgroup1")

    def test_bizpol_with_obj_group(self):
        # remove route.
        self.topo.dut1.get_rest_device().delete_edge_route("192.168.4.0/24")
        # 创建group
        self.topo.dut1.get_rest_device().create_addr_group(group_name="addrgroup1", addr_with_prefix1="192.168.4.0/24")
        self.topo.dut1.get_rest_device().create_port_group(group_name="portgroup1", protocol1="tcp", port_list1="7777")
        # use bizpol to steering the traffic.
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       overlay_enable=True,
                                                       dst_addr_group="addrgroup1",
                                                       route_label="0x3400010")

        # 测试流量
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为0即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # update bizpol
        # self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        # time.sleep(5)
        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=1,
                                                       overlay_enable=True,
                                                       dst_addr_group="addrgroup1",
                                                       dst_port_group="portgroup1",
                                                       route_label="0x3400010")

        # 非group port命中失败
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill nc")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "sh -c 'nohup nc -l -v -n 192.168.4.2 8888 > /dev/null 2>&1 &'")
        glx_assert(err == '')
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "sh -c 'nohup nc -w 3 -v 192.168.4.2 8888 > /tmp/bizpol_obj_group_test.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/bizpol_obj_group_test.txt")
        glx_assert(err == '')
        glx_assert("Connection to 192.168.4.2 8888 port [tcp/*] succeeded!" not in out)
        
        # 连接成功
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill nc")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "sh -c 'nohup nc -l -v -n 192.168.4.2 7777 > /dev/null 2>&1 &'")
        glx_assert(err == '')
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "sh -c 'nohup nc -w 3 -v 192.168.4.2 7777 > /tmp/bizpol_obj_group_test.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/bizpol_obj_group_test.txt")
        glx_assert(err == '')
        glx_assert("Connection to 192.168.4.2 7777 port [tcp/*] succeeded!" in out)

        # 增加bizpol连接成功
        self.topo.dut1.get_rest_device().create_port_group(group_name="portgroup2", protocol1="tcp", port_list1="8888")
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol2", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=1,
                                                       overlay_enable=True,
                                                       dst_addr_group="addrgroup1",
                                                       dst_port_group="portgroup2",
                                                       route_label="0x3400010")
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill nc")
        glx_assert(err == '')
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "sh -c 'nohup nc -l -v -n 192.168.4.2 8888 > /dev/null 2>&1 &'")
        glx_assert(err == '')
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "sh -c 'nohup nc -w 3 -v 192.168.4.2 8888 > /tmp/bizpol_obj_group_test.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/bizpol_obj_group_test.txt")
        glx_assert(err == '')
        glx_assert("Connection to 192.168.4.2 8888 port [tcp/*] succeeded!" in out)

        # 移除配置
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol2")
        self.topo.dut1.get_rest_device().delete_addr_group(group_name="addrgroup1")
        self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup1")
        self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup2")
        self.topo.tst.get_ns_cmd_result("dut4", "pkill nc")
        # 无需恢复路由，依赖setup.

    def test_bizpol_session_misc_change_with_obj_group(self):
        # remove route.
        self.topo.dut1.get_rest_device().delete_edge_route("192.168.4.0/24")
        # 创建group
        # 不能在这里建立，因为仍会查到并记录到session上
        #self.topo.dut1.get_rest_device().create_addr_group(group_name="addrgroup1", addr_with_prefix1="192.168.4.0/24")

        # 清除计数
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear bizpol sessions")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl clear node counters")

        # 初始情况下，不配置addr group
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       overlay_enable=True,
                                                       route_label="0x3400010")

        # 测试流量
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为0即可
        glx_assert("100% packet loss" not in out)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        # 创建add group.
        self.topo.dut1.get_rest_device().create_addr_group(group_name="addrgroup1", addr_with_prefix1="192.168.4.0/24")
        # update bizpol
        # self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        # time.sleep(5)
        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       overlay_enable=True,
                                                       dst_addr_group="addrgroup1",
                                                       route_label="0x3400010")

        # 重新发包，触发misc change.
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.4.2 -c 5 -i 0.05")
        glx_assert(err == '')
        # 此时不应当再丢包
        glx_assert("0% packet loss" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show node counters | grep misc")
        glx_assert(err == '')
        # 有session因misc变动的删除计数
        glx_assert("misc change" in out)
        # session数量仍为1
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show bizpol sessions | grep elements")
        glx_assert(err == '')
        # 仍只有一个session (2个elements，正反向)
        glx_assert("2 active" in out)

        # 移除配置
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        self.topo.dut1.get_rest_device().delete_addr_group(group_name="addrgroup1")

if __name__ == '__main__':
    unittest.main()
