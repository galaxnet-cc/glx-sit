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

class TestBasic1T4DWanDnat(unittest.TestCase):

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
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.21.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.21.2/24")

        # dut1 Lan 1 ip:
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.1.1/24", mtu=mtu)

        # 初始化tst接口
        self.topo.tst.add_ns("dut1")
        self.topo.tst.add_if_to_ns(self.topo.tst.if1, "dut1")

        # 添加tst节点ip及路由
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")

        # 添加路由
        self.topo.tst.add_ns_route("dut1", "192.168.12.0/24", "192.168.1.1")
        self.topo.tst.add_ns_route("dut1", "192.168.21.0/24", "192.168.1.1")
        # dut1 turn off other WAN NAT
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN3", False)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", False)
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.12.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       protocol=0,
                                                       direct_enable=True)
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol2", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.21.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN2",
                                                       protocol=0,
                                                       direct_enable=True)
        # 创建segment
        self.topo.dut2.get_rest_device().create_segment(1)

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        self.topo.tst.get_cmd_result("pkill nc")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("pkill nc")

        # delete
        self.topo.dut2.get_rest_device().delete_port_mapping(logic_if="WAN1")
        self.topo.dut2.get_rest_device().delete_port_mapping(logic_if="WAN2")
        self.topo.dut2.get_rest_device().delete_segment(1)
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol2")
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN3", True)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", True)

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")

        # revert to default.
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")

        # wait for all passive link to be aged.
        time.sleep(20)

    def test_segment_wan_dnat(self):
        # create port wan1 mapping
        self.topo.dut2.get_rest_device().create_port_mapping(logic_if="WAN1", segment=1, internal_addr="169.254.101.2")

        # 检查连接是否建立
        _, _ = self.topo.dut2.get_vpp_ssh_device().get_cmd_result("pkill nc")
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result("sh -c 'nohup ip netns exec ctrl-ns-seg-1 nc -l -v -n 169.254.101.2 7777 > /dev/null 2>&1 &'")
        glx_assert(err == '')
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "sh -c 'nohup nc -w 3 -v 192.168.12.2 7777 > /tmp/wan_dnat.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/wan_dnat.txt")
        glx_assert(err == '')
        glx_assert("Connection to 192.168.12.2 7777 port [tcp/*] succeeded!" in out)

    # check multi wans mapping to the same ip and port
    def test_multi_wan_dnat(self):
        resp = self.topo.dut2.get_rest_device().create_port_mapping(logic_if="WAN1")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut2.get_rest_device().create_port_mapping(logic_if="WAN2")
        glx_assert(resp.status_code == 201)

        # check wan1
        self.topo.tst.get_cmd_result("pkill nc")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("pkill nc")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("rm /tmp/wan_dnat*")
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result("sh -c 'nohup ip netns exec ctrl-ns nc -l -v -n 169.254.100.2 7777 > /dev/null 2>&1 &'")
        glx_assert(err == '')

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "sh -c 'nohup nc -w 3 -v 192.168.12.2 7777 > /tmp/wan_dnat1.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/wan_dnat1.txt")
        glx_assert(err == '')
        glx_assert("Connection to 192.168.12.2 7777 port [tcp/*] succeeded!" in out)

        # check wan2
        self.topo.tst.get_cmd_result("pkill nc")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("pkill nc")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("rm /tmp/wan_dnat*")
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result("sh -c 'nohup ip netns exec ctrl-ns nc -l -v -n 169.254.100.2 7777 > /dev/null 2>&1 &'")
        glx_assert(err == '')

        out, err = self.topo.tst.get_ns_cmd_result("dut1", "sh -c 'nohup nc -w 3 -v 192.168.21.2 7777 > /tmp/wan_dnat2.txt 2>&1 &'")
        glx_assert(err == '')
        time.sleep(3)
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "cat /tmp/wan_dnat2.txt")
        glx_assert(err == '')
        glx_assert("Connection to 192.168.21.2 7777 port [tcp/*] succeeded!" in out)

if __name__ == '__main__':
    unittest.main()
 
