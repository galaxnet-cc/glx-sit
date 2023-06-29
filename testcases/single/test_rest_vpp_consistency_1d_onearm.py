from cgi import test
import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D


class TestRestVppConsistency1DOneArm(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_one_arm_config_constraints(self):
        # 测试环境里WAN1接口为routed接口，默认就在overlay+nat模式下
        result = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "test")
        glx_assert(result.status_code == 200)
        # Test1: pppoe模式不支持one arm mode.
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", True)
        glx_assert(result.status_code == 500)
        # Test2: 改回dhcp模式即可配置成功
        result = self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        glx_assert(result.status_code == 200)
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", True)
        glx_assert(result.status_code == 200)

        # Test3: one arm模式下，不允许变更overlay以有nat direct enable属性
        result = self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN1", False)
        glx_assert(result.status_code == 500)
        result = self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        glx_assert(result.status_code == 500)

        # Test4: 只允许一个接口处于one arm模式（WAN2同样默认开启overlay+nat）
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN2", True)
        glx_assert(result.status_code == 500)
        # 关闭WAN1则WAN2成功
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", False)
        glx_assert(result.status_code == 200)
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN2", True)
        glx_assert(result.status_code == 200)
        # 验证device global context里的数值为WAN2
        interface, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget DeviceGlobalContext#default OneArmInterface")
        glx_assert(err == '')
        glx_assert(interface == "WAN2")
        # 清除配置
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN2", False)
        glx_assert(result.status_code == 200)
        interface, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget DeviceGlobalContext#default OneArmInterface")
        glx_assert(err == '')
        glx_assert(interface == "")

    def test_one_arm_with_edge_route(self):
        # Test1: 验证有edge route与one arm相关的限制与交互
        # 配置一个edge route（目前粒度较粗，配置一个overlay route即可，因为参数较少）
        result = self.topo.dut1.get_rest_device().create_edge_route("1.1.1.1/32", route_label="100")
        glx_assert(result.status_code == 201) # http.statuscreated
        # 打开one arm则失败
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", True)
        glx_assert(result.status_code == 500)
        # 删掉edge route就成功
        result = self.topo.dut1.get_rest_device().delete_edge_route("1.1.1.1/32")
        glx_assert(result.status_code == 410) # http.statusgone
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", True)
        glx_assert(result.status_code == 200)
        interface, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget DeviceGlobalContext#default OneArmInterface")
        glx_assert(err == '')
        glx_assert(interface == "WAN1")
        # 创建一个static edge route，检查fwdmd会下发携带WAN vpp if的递归
        result = self.topo.dut1.get_rest_device().create_edge_route("1.1.1.1/32", route_label="0xffffffffff",
                                                                    route_protocol="static",
                                                                    next_hop_ip="192.168.1.1")
        glx_assert(result.status_code == 201)
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table 0 1.1.1.1/32")
        glx_assert(err == '')
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        glx_assert(wan1VppIf in fibResult)
        # Test2: 仅重启fwdmd后，新创建新的路由，仍能携带此标志
        # restart fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart fwdmd")
        glx_assert(err == '')
        # 等待fwdmd重启完成（10s足够）
        time.sleep(10)
        result = self.topo.dut1.get_rest_device().create_edge_route("1.1.1.2/32", route_label="0xffffffffff",
                                                                    route_protocol="static",
                                                                    next_hop_ip="192.168.1.1")
        glx_assert(result.status_code == 201)
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table 0 1.1.1.2/32")
        glx_assert(err == '')
        glx_assert(wan1VppIf in fibResult)

        # Test3: 重启vpp，也能成功
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart vpp")
        glx_assert(err == '')
        # 等待fwdmd+vpp重启完成（10s足够）
        time.sleep(10)
        # 路由都恢复正确
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table 0 1.1.1.2/32")
        glx_assert(err == '')
        glx_assert(wan1VppIf in fibResult)
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table 0 1.1.1.2/32")
        glx_assert(err == '')
        glx_assert(wan1VppIf in fibResult)

        # 清除配置
        # 删除路由
        result = self.topo.dut1.get_rest_device().delete_edge_route("1.1.1.1/32", route_protocol="static")
        glx_assert(result.status_code == 410)
        result = self.topo.dut1.get_rest_device().delete_edge_route("1.1.1.2/32", route_protocol="static")
        glx_assert(result.status_code == 410)
        # 移除one arm模式
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", False)
        glx_assert(result.status_code == 200)

    # 验证one arm if的ns切换动作
    def test_one_arm_host_ns_switch(self):
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip_gw("WAN1", "192.168.1.2/24", "192.168.1.1")
        glx_assert(result.status_code == 200)
        # 打开one arm成功
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", True)
        glx_assert(result.status_code == 200)
        # lcp接口移入ctrl-ns，且地址同步过去
        result, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip link")
        glx_assert(err == '')
        glx_assert("WAN1" in result)
        result, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in result)
        # 关闭one arm成功，且地址移回
        result = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN1", False)
        result, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip link")
        glx_assert(err == '')
        glx_assert("WAN1" in result)
        result, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in result)
        # 网关也补回到wan ctrl-ns中
        result, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip route show default")
        glx_assert(err == '')
        glx_assert("192.168.1.1" in result)

        # 配置清除，恢复为dhcp配置
        result = self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        glx_assert(result.status_code == 200)
