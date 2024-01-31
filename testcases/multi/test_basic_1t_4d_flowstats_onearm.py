import unittest
import time
import math
import lib.flowstats_record

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

class TestBasic1T4DFlowstatsOneArm(unittest.TestCase):

    # 创建一个最基本的one arm场景：
    # tst(linuxif5)---------
    #                       \
    # dut1--wan5(单臂模式)--<one-arm-br>---<linux-router>-<uplink-br>-wan5
    #
    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return

        # dut1与dut2的link/tunnel配置，在测试例中执行。

        # 配置dut2到uplink-br的ip+gw
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip_gw("WAN5", "192.168.202.2/24", "192.168.202.1")

        # 初始化tst接口
        self.topo.tst.add_ns("dut1")
        # 接口移入ns后，就不会自动分地址了，我们就可以自己控制了
        self.topo.tst.add_if_to_ns(self.topo.tst.if5, "dut1")

        # 添加tst节点ip及路由
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if5, "192.168.201.201/24")

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if5, "192.168.201.201/24")
        self.topo.tst.add_ns_if_to_default_ns("dut1", self.topo.tst.if5)

        # 清理dut2环境
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN5")

        # wait for all passive link to be aged.
        time.sleep(20)

    def test_01_local_nat(self):
        output_path = "/tmp/glx-flowstats"
        age_interval = 15
        src_port = 52010
        dst_ip = "192.168.202.2"

        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"rm -rf {output_path}")
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"mkdir -p {output_path}")
        glx_assert(err == '')

        resp = self.topo.dut1.get_rest_device().set_logical_interface_static_ip_gw("WAN5", "192.168.201.2/24", "192.168.201.1")
        glx_assert(200 == resp.status_code)
        # 开启one arm模式
        resp = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN5", True)
        glx_assert(200 == resp.status_code)

        _, err = self.topo.tst.add_ns_route("dut1", "192.168.202.0/24", "192.168.201.2")
        glx_assert(err == '')
        # 配置bizpol
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol-dut2-wan5-nat", priority=1,
                                                       src_prefix="192.168.201.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       # 强制选择WAN5，避免影响
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN5",
                                                       direct_enable=True)
        glx_assert(201 == resp.status_code)

        # 在dut2上开启iperf server
        _, err = self.topo.dut2.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN5", "iperf3 -s -D")
        glx_assert(err == '')

        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(active_interval=5, age_interval=age_interval)
        glx_assert(201 == resp.status_code)

        # 启动收集器
        resp = self.topo.dut1.get_rest_device().enable_disable_ipfix_collector()
        glx_assert(200 == resp.status_code)

        # 等待收集器收集到模板信息
        time.sleep(10)

        # 在tst上开启正向打流
        expected_biterate = 10.0
        _, err = self.topo.tst.get_ns_cmd_result("dut1", f"iperf3 -c {dst_ip} -b {str(expected_biterate)}M -t 15 --cport {str(src_port)}")
        glx_assert(err == '')

        time.sleep(age_interval)

        # 导出流数据
        resp = self.topo.dut1.get_rest_device().flush_ipfix_collector_records(output_path=f"{output_path}/flows.json")
        glx_assert(200 == resp.status_code)

        time.sleep(1)
        # 读取流数据
        data, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {output_path}/flows.json")
        glx_assert(err == '')

        # 查找流信息，匹配五元组
        # 需要检查收包接口是否为该接口
        wan_if_name = self.topo.dut1.get_if_map()["WAN5"]
        wan_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan_if_name} | grep -E '{wan_if_name}\s+[0-9]+' | awk '{{print $2}}'")
        glx_assert(err == '')

        # 查找流信息，匹配五元组
        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 检查五元组
                if (record.sourceIPv4Address == "192.168.201.201" and record.sourceTransportPort == src_port) and  \
                (record.destinationIPv4Address == dst_ip and record.destinationTransportPort == 5201) and \
                (record.protocolIdentifier == 6 and record.ingressInterface == int(wan_index)):
                    time_difference = (record.flowEndNanoseconds - record.flowStartNanoseconds).total_seconds()
                    if (math.isclose(time_difference, 5, abs_tol=0.5)):
                        expected_record = record
                        break 
            if expected_record is not None:
                break

        # 检查自定义信息
        glx_assert(expected_record is not None) 
        # segment肯定为0
        glx_assert(expected_record.glxSegmentId == 0)
        # 不应该存在route label
        glx_assert(expected_record.glxRouteLabel == 0)
        # 本地互联网
        glx_assert(expected_record.glxTrafficType == 0)

        octetDeltaCount = expected_record.octetDeltaCount
        biterate = float(octetDeltaCount / (1024 ** 2) / 5 * 8)
        glx_assert(math.isclose(expected_biterate, biterate, abs_tol=0.15))

        # 在tst上开启反向打流
        _, err = self.topo.tst.get_ns_cmd_result("dut1", f"iperf3 -c {dst_ip} -b {str(expected_biterate)}M -t 15 --cport {str(src_port)} -R")
        glx_assert(err == '')

        time.sleep(age_interval)

        # 导出流数据
        resp = self.topo.dut1.get_rest_device().flush_ipfix_collector_records(output_path=f"{output_path}/flows.json")
        glx_assert(200 == resp.status_code)

        time.sleep(1)

        # 读取流数据
        data, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {output_path}/flows.json")
        glx_assert(err == '')

        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 过滤流，检查五元组
                if (record.sourceIPv4Address == dst_ip and record.sourceTransportPort == 5201) and  \
                (record.destinationIPv4Address == "192.168.201.201" and record.destinationTransportPort == src_port) and \
                (record.protocolIdentifier == 6 and record.ingressInterface == int(wan_index)):
                    time_difference = (record.flowEndNanoseconds - record.flowStartNanoseconds).total_seconds()
                    # 只取5秒钟的数据，这样子可以保证不会是流的最后
                    if (math.isclose(time_difference, 5, abs_tol=0.5)):
                        expected_record = record
                        break 
            if expected_record is not None:
                break

        # 检查自定义信息
        glx_assert(expected_record is not None) 
        # segment肯定为0
        glx_assert(expected_record.glxSegmentId == 0)
        # 不应该存在route label
        glx_assert(expected_record.glxRouteLabel == 0)
        # 本地互联网
        glx_assert(expected_record.glxTrafficType == 0)

        octetDeltaCount = expected_record.octetDeltaCount
        biterate = float(octetDeltaCount / (1024 ** 2) / 5 * 8)
        glx_assert(math.isclose(expected_biterate, biterate, abs_tol=0.2))

        # 清理环境
        resp = self.topo.dut1.get_rest_device().enable_disable_ipfix_collector(enable=False)
        glx_assert(200 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().delete_flowstats_setting()
        glx_assert(410 == resp.status_code)
        _, err = self.topo.tst.del_ns_route("dut1", "192.168.202.0/24", "192.168.201.2")
        glx_assert(err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN5", "pkill iperf3")
        glx_assert(err == '')
        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol-dut2-wan5-nat")
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().set_logical_interface_one_arm_mode_enable("WAN5", False)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN5")
        glx_assert(resp.status_code == 200)


if __name__ == '__main__':
    unittest.main()
