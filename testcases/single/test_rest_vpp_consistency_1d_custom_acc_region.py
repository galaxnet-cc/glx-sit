import unittest
import time
from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DCustomAccRegion(unittest.TestCase):
    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_01_validation(self):
        # validation
        # route-label required
        name = "test"
        resp = self.topo.dut1.get_rest_device().create_custom_acc_region(name, acc_route_label="")
        glx_assert(500 == resp.status_code)
        # route-label validation
        resp = self.topo.dut1.get_rest_device().create_custom_acc_region(name, acc_route_label="xxxx")
        glx_assert(500 == resp.status_code)
        # only support default segment
        resp = self.topo.dut1.get_rest_device().create_custom_acc_region(name, acc_route_label="0x1", segment=1)
        glx_assert(500 == resp.status_code)

    def test_02_basic(self):
        name = "test"
        ipset = "acc-" + name
        acc_route = "1.1.1.0/24"
        ns = "ctrl-ns"
        acc_route_label="1"

        # 开启 segment DnsIpCollectEnable
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True)
        glx_assert(200 == resp.status_code)
        # create
        resp = self.topo.dut1.get_rest_device().create_custom_acc_region(name, acc_route_label=acc_route_label)
        glx_assert(201 == resp.status_code)
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ipset add {ipset} {acc_route}")
        glx_assert(err == '')
        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route}")
        glx_assert(err == "")
        glx_assert(acc_route in out)
        glx_assert(f"route-label: {acc_route_label}" in out)
        glx_assert("is_acc: 1" in out)
        # 从set中删除数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ipset del {ipset} {acc_route}")

        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测路由已经删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route}")
        glx_assert(err == "")
        glx_assert(acc_route not in out)

        # update
        acc_route_label = "2" 
        resp = self.topo.dut1.get_rest_device().update_custom_acc_region(name, acc_route_label=acc_route_label)
        glx_assert(200 == resp.status_code)

        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ipset add {ipset} {acc_route}")
        glx_assert(err == '')
        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route}")
        glx_assert(err == "")
        glx_assert(f"route-label: {acc_route_label}" in out)
        glx_assert(acc_route in out)
        # 从set中删除数据
        resp = self.topo.dut1.get_rest_device().delete_custom_acc_region(name)
        glx_assert(410 == resp.status_code)
        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测路由已经删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route}")
        glx_assert(err == "")
        glx_assert(acc_route not in out)
        # 关闭 segment DnsIpCollectEnable
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)
        glx_assert(200 == resp.status_code)

    def test_03_multi(self):
        # create
        name1 = "test1"
        name2 = "test2"
        ipset1 = "acc-" + name1
        ipset2 = "acc-" + name2
        acc_route1 = "1.1.1.0/24"
        acc_route_label1 = "1"
        acc_route_label2 = "2"
        acc_route2 = "2.2.2.0/24"
        ns = "ctrl-ns"
        acc_route_label = "1"

        # 开启 segment DnsIpCollectEnable
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True)
        glx_assert(200 == resp.status_code)

        # 创建自定义region
        resp = self.topo.dut1.get_rest_device().create_custom_acc_region(name1, acc_route_label=acc_route_label1)
        glx_assert(201 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().create_custom_acc_region(name2, acc_route_label=acc_route_label2)
        glx_assert(201 == resp.status_code)

        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ipset add {ipset1} {acc_route1}")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ipset add {ipset2} {acc_route2}")
        glx_assert(err == '')
        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route1}")
        glx_assert(err == "")
        glx_assert(f"route-label: {acc_route_label1}" in out)
        glx_assert(acc_route1 in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route2}")
        glx_assert(err == "")
        glx_assert(f"route-label: {acc_route_label2}" in out)
        glx_assert(acc_route2 in out)

        resp = self.topo.dut1.get_rest_device().delete_custom_acc_region(name1)
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().delete_custom_acc_region(name2)
        glx_assert(410 == resp.status_code)

        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测路由已经删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route1}")
        glx_assert(err == "")
        glx_assert(acc_route1 not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route2}")
        glx_assert(err == "")
        glx_assert(acc_route2 not in out)

        # 关闭 segment DnsIpCollectEnable
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)
        glx_assert(200 == resp.status_code)

    def test_04_restart(self):
        name = "test"
        ipset = "acc-" + name
        acc_route = "1.1.1.0/24"
        ns = "ctrl-ns"
        acc_route_label = "1"
        # 开启 segment DnsIpCollectEnable
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True)
        glx_assert(200 == resp.status_code)
        # create
        resp = self.topo.dut1.get_rest_device().create_custom_acc_region(name, acc_route_label=acc_route_label)
        glx_assert(201 == resp.status_code)
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ipset add {ipset} {acc_route}")
        glx_assert(err == '')
        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route}")
        glx_assert(err == "")
        glx_assert(acc_route in out)
        # 重启vpp，模拟vpp crash场景
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("systemctl restart vpp")
        glx_assert(err == '')
        # 等待fwdmd配置
        time.sleep(10)
        # 检测路由是否已经重新配置
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route}")
        glx_assert(err == "")
        glx_assert(acc_route in out)
        glx_assert(acc_route in out)
        glx_assert(f"route-label: {acc_route_label}" in out)
        glx_assert("is_acc: 1" in out)
        resp = self.topo.dut1.get_rest_device().delete_custom_acc_region(name)
        glx_assert(410 == resp.status_code)
        # 增加一点延迟以便go处理完毕
        time.sleep(5)
        # 检测路由已经删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {acc_route}")
        glx_assert(err == "")
        glx_assert(acc_route not in out)
        # 关闭 segment DnsIpCollectEnable
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)
        glx_assert(200 == resp.status_code)

