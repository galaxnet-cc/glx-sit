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

class TestBasic1T4DFlowstats(unittest.TestCase):

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

    # 测试本地互联网
    def test_01_local_nat(self):
        output_path = "/tmp/glx-flowstats"
        # 创建环境
        # 收集路径
        age_interval = 15
        src_port = 52010
        dst_ip = "192.168.12.2"

        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"rm -rf {output_path}")
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"mkdir -p {output_path}")
        glx_assert(err == '')
        # 添加路由
        _, err = self.topo.tst.add_ns_route("dut1", "192.168.12.0/24", "192.168.1.1")
        glx_assert(err == '')

        # 创建一条默认nat的规则
        resp = self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        glx_assert(200 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1, 
                                                              src_prefix="192.168.1.0/24", dst_prefix="0.0.0.0/0", protocol=0,
                                                              direct_enable=True,
                                                              steering_mode=1, steering_type=1, steering_interface="WAN1")
        glx_assert(201 == resp.status_code)

        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(active_interval=5, age_interval=age_interval)
        glx_assert(201 == resp.status_code)

        # 启动收集器
        resp = self.topo.dut1.get_rest_device().enable_disable_ipfix_collector()
        glx_assert(200 == resp.status_code)

        # 等待收集器收集到模板信息
        time.sleep(10)

        # 在dut2上开启iperf server
        _, err = self.topo.dut2.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", "iperf3 -s -D")
        glx_assert(err == '')

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

        bvi_sw_if_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#default BviSwIfIndex")
        glx_assert(err == '')

        # 查找流信息，匹配五元组
        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 检查五元组
                if (record.sourceIPv4Address == "192.168.1.2" and record.sourceTransportPort == src_port) and  \
                (record.destinationIPv4Address == dst_ip and record.destinationTransportPort == 5201) and \
                (record.protocolIdentifier == 6 and record.ingressInterface == int(bvi_sw_if_index)):
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
        # 查找流信息，匹配五元组
        # 需要检查收包接口是否为该接口
        wan_if_name = self.topo.dut1.get_if_map()["WAN1"]
        wan_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan_if_name} | grep -E '{wan_if_name}\s+[0-9]+' | awk '{{print $2}}'")
        glx_assert(err == '')

        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 过滤流，检查五元组
                if (record.sourceIPv4Address == dst_ip and record.sourceTransportPort == 5201) and  \
                (record.destinationIPv4Address == "192.168.1.2" and record.destinationTransportPort == src_port) and \
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
        _, err = self.topo.tst.del_ns_route("dut1", "192.168.12.0/24", "192.168.1.1")
        glx_assert(err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", "pkill iperf3")
        glx_assert(err == '')
        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        glx_assert(200 == resp.status_code)

    # 测试组网
    def test_02_tunnel(self):
        output_path = "/tmp/glx-flowstats"
        src_port = 52010
        dst_ip = "192.168.4.2"
        # 开启流统计能力
        age_interval = 15

        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"rm -rf {output_path}")
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"mkdir -p {output_path}")
        glx_assert(err == '')

        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(active_interval=5, age_interval=age_interval)
        glx_assert(201 == resp.status_code)

        # 启动收集器
        resp = self.topo.dut1.get_rest_device().enable_disable_ipfix_collector()
        glx_assert(200 == resp.status_code)

        # 等待收集器收集到模板信息
        time.sleep(10)

        # 在tst(dut4)lan侧开启iperf server
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "iperf3 -s -D")
        glx_assert(err == '')

        # 在tst上开启正向打流
        expected_biterate = 10.0
        _, err = self.topo.tst.get_ns_cmd_result("dut1", f"iperf3 -c {dst_ip} -b {str(expected_biterate)}M -t 15 --cport {str(src_port)}")
        glx_assert(err == '')

        # 等待流老化
        time.sleep(age_interval)
    
        resp = self.topo.dut1.get_rest_device().flush_ipfix_collector_records(output_path=f"{output_path}/flows.json")
        glx_assert(200 == resp.status_code)

        time.sleep(1)
        # 读取流数据
        data, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {output_path}/flows.json")
        glx_assert(err == '')

        bvi_sw_if_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#default BviSwIfIndex")
        glx_assert(err == '')

        # 查找流信息，匹配五元组
        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 检查五元组
                if (record.sourceIPv4Address == "192.168.1.2" and record.sourceTransportPort == src_port) and  \
                (record.destinationIPv4Address == dst_ip and record.destinationTransportPort == 5201) and \
                (record.protocolIdentifier == 6 and record.ingressInterface == int(bvi_sw_if_index)):
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
        glx_assert(expected_record.glxRouteLabel == 0x3400010)
        # 组网
        glx_assert(expected_record.glxTrafficType == 1)

        octetDeltaCount = expected_record.octetDeltaCount
        biterate = float(octetDeltaCount / (1024 ** 2) / 5 * 8)
        glx_assert(math.isclose(expected_biterate, biterate, abs_tol=0.2))

        _, err = self.topo.tst.get_ns_cmd_result("dut1", f"iperf3 -c {dst_ip} -b {str(expected_biterate)}M -t 15 --cport {str(src_port)} -R")
        glx_assert(err == '')

        # 等待流老化
        time.sleep(age_interval)
    
        resp = self.topo.dut1.get_rest_device().flush_ipfix_collector_records(output_path=f"{output_path}/flows.json")
        glx_assert(200 == resp.status_code)

        time.sleep(1)
        # 读取流数据
        data, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {output_path}/flows.json")
        glx_assert(err == '')

        loop_sw_if_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget SegmentContext#0 LoopSwIfIndex")
        glx_assert(err == '')

        # 查找流信息，匹配五元组
        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 检查五元组
                if (record.sourceIPv4Address == dst_ip and record.sourceTransportPort == 5201) and  \
                (record.destinationIPv4Address == "192.168.1.2" and record.destinationTransportPort == src_port) and \
                (record.protocolIdentifier == 6 and record.ingressInterface == int(loop_sw_if_index)):
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
        glx_assert(expected_record.glxRouteLabel == 0x1200010)
        # 组网
        glx_assert(expected_record.glxTrafficType == 1)

        octetDeltaCount = expected_record.octetDeltaCount
        biterate = float(octetDeltaCount / (1024 ** 2) / 5 * 8)
        glx_assert(math.isclose(expected_biterate, biterate, abs_tol=0.2))

        # 清理环境
        resp = self.topo.dut1.get_rest_device().enable_disable_ipfix_collector(enable=False)
        glx_assert(200 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().delete_flowstats_setting()
        glx_assert(410 == resp.status_code)
        _, err = self.topo.tst.get_ns_cmd_result("dut4", "pkill iperf3")
        glx_assert(err == '')
    
    # 测试加速
    def test_03_acc(self):
        # 设置test
        acc_ip = "192.168.34.1"
        src_port = 52010
        age_interval = 15
        output_path = "/tmp/glx-flowstats"

        _, err = self.topo.tst.add_ns_route("dut1", f"{acc_ip}/32", "192.168.1.1")
        glx_assert(err == '')

        # 设置dut1 acc属性
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.222")
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_edge_route(route_prefix=f"{acc_ip}/32", route_label="0x3400010", is_acc=True)
        glx_assert(resp.status_code == 201)

        # 设置dut4为int edge
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().create_edge_route(route_prefix="222.222.222.222/32", route_label="0x1200010", is_acc_reverse=True)
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut3.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().set_logical_interface_nat_direct("WAN2", False)
        glx_assert(resp.status_code == 200)

        # 开启流统计能力
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(active_interval=5, age_interval=age_interval)
        glx_assert(201 == resp.status_code)
        # 启动收集器
        resp = self.topo.dut1.get_rest_device().enable_disable_ipfix_collector()
        glx_assert(200 == resp.status_code)

        # 等待收集器收集到模板信息
        time.sleep(10)

        # 在tst(dut4)lan侧开启iperf server
        _, err = self.topo.dut3.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", "iperf3 -s -D")
        glx_assert(err == '')

        # 在tst上开启打流
        expected_biterate = 10.0
        _, err = self.topo.tst.get_ns_cmd_result("dut1", f"iperf3 -c {acc_ip} -b {str(expected_biterate)}M -t 15 --cport {str(src_port)}")
        glx_assert(err == '')

        time.sleep(age_interval)

        resp = self.topo.dut1.get_rest_device().flush_ipfix_collector_records(output_path=f"{output_path}/flows.json")
        glx_assert(200 == resp.status_code)

        time.sleep(1)
        # 读取流数据
        data, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {output_path}/flows.json")
        glx_assert(err == '')

        bvi_sw_if_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#default BviSwIfIndex")
        glx_assert(err == '')

        # 查找流信息，匹配五元组
        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 检查五元组
                if (record.sourceIPv4Address == "192.168.1.2" and record.sourceTransportPort == src_port) and  \
                (record.destinationIPv4Address == acc_ip and record.destinationTransportPort == 5201) and \
                (record.protocolIdentifier == 6 and record.ingressInterface == int(bvi_sw_if_index)):
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
        # route label
        glx_assert(expected_record.glxRouteLabel == 0x3400010)
        # 加速
        glx_assert(expected_record.glxTrafficType == 2)

        octetDeltaCount = expected_record.octetDeltaCount
        biterate = float(octetDeltaCount / (1024 ** 2) / 5 * 8)
        glx_assert(math.isclose(expected_biterate, biterate, abs_tol=0.2))

        # 在tst上开启打流
        _, err = self.topo.tst.get_ns_cmd_result("dut1", f"iperf3 -c {acc_ip} -b {str(expected_biterate)}M -t 15 --cport {str(src_port)} -R")
        glx_assert(err == '')

        time.sleep(age_interval)

        resp = self.topo.dut1.get_rest_device().flush_ipfix_collector_records(output_path=f"{output_path}/flows.json")
        glx_assert(200 == resp.status_code)

        time.sleep(1)
        # 读取流数据
        data, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {output_path}/flows.json")
        glx_assert(err == '')

        loop_sw_if_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget SegmentContext#0 LoopSwIfIndex")
        glx_assert(err == '')

        # 查找流信息，匹配五元组
        exported_flow_list = lib.flowstats_record.parse_json_to_struct(data)
        expected_record = None
        for exported_flow in exported_flow_list:
            for record in exported_flow.records:
                # 检查五元组
                if (record.sourceIPv4Address == acc_ip and record.sourceTransportPort == 5201) and  \
                (record.destinationIPv4Address == "192.168.1.2" and record.destinationTransportPort == src_port) and \
                (record.protocolIdentifier == 6 and record.ingressInterface == int(loop_sw_if_index)):
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
        # route label
        glx_assert(expected_record.glxRouteLabel == 0x1200010)
        # 加速
        glx_assert(expected_record.glxTrafficType == 2)

        octetDeltaCount = expected_record.octetDeltaCount
        biterate = float(octetDeltaCount / (1024 ** 2) / 5 * 8)
        glx_assert(math.isclose(expected_biterate, biterate, abs_tol=0.2))

        # 清理环境
        resp = self.topo.dut1.get_rest_device().enable_disable_ipfix_collector(enable=False)
        glx_assert(200 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().delete_flowstats_setting()
        glx_assert(410 == resp.status_code)
        _, err = self.topo.dut3.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", "pkill iperf3")
        glx_assert(err == '')
        _, err = self.topo.tst.del_ns_route("dut1", f"{acc_ip}/32", "192.168.1.1")
        glx_assert(err == '')
        resp = self.topo.dut4.get_rest_device().delete_edge_route(route_prefix="222.222.222.222/32")
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut4.get_rest_device().update_segment(segment_id=0, int_edge_enable=False)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut1.get_rest_device().delete_edge_route(route_prefix=f"{acc_ip}/32")
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut3.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        glx_assert(resp.status_code == 200)
        resp = self.topo.dut4.get_rest_device().set_logical_interface_nat_direct("WAN2", False)
        glx_assert(resp.status_code == 200)


if __name__ == '__main__':
    unittest.main()
