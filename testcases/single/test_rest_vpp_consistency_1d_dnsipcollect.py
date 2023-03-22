import unittest
import time
import random

from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DDnsIpCollect(unittest.TestCase):

    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset flush")

    def test_glx_segment_dnsipcollect_enable(self):
        # 开启 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True)
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add local 1.1.1.0/24")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add acc 2.2.2.0/24")
        glx_assert(err == '')
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" in out)
        # 从set中删除数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset del local 1.1.1.0/24")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset del acc 2.2.2.0/24")
        glx_assert(err == '')
        # 检测路由已经删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" not in out)
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add local 1.1.1.0/24")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add acc 2.2.2.0/24")
        glx_assert(err == '')
        # 重启vpp，模拟vpp crash场景
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart vpp")
        glx_assert(err == '')
        # 等待fwdmd配置
        time.sleep(10)
        # 检测路由是否已经重新配置
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" in out)
        # 关闭 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)
        # 检测路由是否已删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" not in out)

    def test_glx_segment_delivery_batch_route(self):
        # 获取chnroute.txt中的路由数目
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wget -P /opt -N https://cdn.jsdelivr.net/gh/QiuSimons/Chnroute/dist/chnroute/chnroute.txt")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wc -l /opt/chnroute.txt")
        glx_assert(err == "")
        outlist = out.split(' ')
        chnroute_num = int(outlist[0])
        # 开启acc_enable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        # 获取acc table与local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_before = int(out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep / | wc -l")
        glx_assert(err == "")
        acc_route_num_before = int(out)
        # 创建SegmentAccProperties，添加BatchRouteFilePath
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, batch_route_file_path="/opt/chnroute.txt", acc_fib_type="local")
        time.sleep(5)
        # 获取local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_after = int(out)
        # 检测比较local table是否增加了相应条数路由
        glx_assert((local_route_num_after - local_route_num_before - 1) == chnroute_num)
        # 更改SegmentAccProperties IsAcc属性
        self.topo.dut1.get_rest_device().update_segment_acc_prop(segment_id=0, batch_route_file_path="/opt/chnroute.txt", acc_fib_type="acc")
        time.sleep(5)
        # 获取acc table与local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_after = int(out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep / | wc -l")
        glx_assert(err == "")
        acc_route_num_after = int(out)
        # 检测比较acc table是否增加相应条数路由
        glx_assert(acc_route_num_after - acc_route_num_before == chnroute_num)
        glx_assert(local_route_num_after == local_route_num_before + 1)
        # 删除SegmentAccProperties BatchRouteFilePath属性
        self.topo.dut1.get_rest_device().update_segment_acc_prop(segment_id=0, batch_route_file_path="")
        time.sleep(5)
        # 获取acc table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_after = int(out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep / | wc -l")
        glx_assert(err == "")
        acc_route_num_after = int(out)
        # 检测比较路由数目是否恢复初始状态
        glx_assert(acc_route_num_after == acc_route_num_before)
        glx_assert(local_route_num_after == local_route_num_before + 1)
        # 关闭acc_enable
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

    def test_glx_segment_flush_ip_collect_route(self):
        # 开启 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True)
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add local 1.1.1.0/24")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add acc 2.2.2.0/24")
        glx_assert(err == '')
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" in out)
        # 发送flush Action
        self.topo.dut1.get_rest_device().delete_route_action(segment_id=0)
        # 检测路由已经删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" not in out)
        # 关闭 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)

    def test_glx_edge_route_local(self):
        # 检测没有将要配置的路由
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("8.8.8.8/32" not in out)
        # 配置edge route local模式
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="8.8.8.8/32", route_label="0x3400010", route_protocol="local")
        # 检查配置的路由已经下发
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("8.8.8.8/32" in out)
        # 删除配置的edge route
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="8.8.8.8/32", route_protocol="local")
        # 检测配置路由已经删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("8.8.8.8/32" not in out)

    def test_dnsipcollect_after_fwdmd_restart(self):
        # 开启 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True)
        # 检测路由不存在
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" not in out)
        # 重启fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart fwdmd")
        glx_assert(err == '')
        # 等待fwdmd配置
        time.sleep(10)
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add local 1.1.1.0/24")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add acc 2.2.2.0/24")
        glx_assert(err == '')
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" in out)
        # 关闭 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)
        # 检测路由是否已删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" not in out)

    def test_dnsipcollect_when_fwdmd_restart(self):
        # 开启 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True)
        # 检测路由不存在
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" not in out)
        # 停止fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl stop fwdmd")
        glx_assert(err == '')
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add local 1.1.1.0/24")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add acc 2.2.2.0/24")
        glx_assert(err == '')
         # 重启fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart fwdmd")
        glx_assert(err == '')
        # 等待fwdmd配置
        time.sleep(10)
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" in out)
        # 关闭 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)
        # 检测路由是否已删除
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" not in out)

    def test_dnsipcollect_when_change_routelabel(self):
        # 开启 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True, route_label="10000")
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add acc 1.1.1.0/24")
        glx_assert(err == '')
        time.sleep(3)
        # 检测是否已经下发路由成功
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 1.1.1.0/24")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" in out)
        glx_assert("route-label: 10000" in out)
        # 更新 segment AccRouteLabel
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, dns_ip_collect_enable=True, route_label="20000")
        # 向set中写入数据
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns ipset add acc 2.2.2.0/24")
        glx_assert(err == '')
        # 等待路由更新
        time.sleep(3)
        # 检测下发的路由的AccRouteLabel是否已经更改
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 1.1.1.0/24")
        glx_assert(err == "")
        glx_assert("1.1.1.0/24" in out)
        glx_assert("route-label: 20000" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 2.2.2.0/24")
        glx_assert(err == "")
        glx_assert("2.2.2.0/24" in out)
        glx_assert("route-label: 20000" in out)
        # 关闭 segment DnsIpCollectEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False, dns_ip_collect_enable=False)

    def test_glx_segment_delivery_batch_route_when_fwdmd_restart(self):
        # 获取chnroute.txt中的路由数目
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wget -P /opt -N https://cdn.jsdelivr.net/gh/QiuSimons/Chnroute/dist/chnroute/chnroute.txt")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wc -l /opt/chnroute.txt")
        glx_assert(err == "")
        outlist = out.split(' ')
        chnroute_num = int(outlist[0])
        # 开启acc_enable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        # 获取acc table与local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_before = int(out)
        # 创建SegmentAccProperties，添加BatchRouteFilePath
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, batch_route_file_path="/opt/chnroute.txt", acc_fib_type="local")
        # 重启fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart fwdmd")
        glx_assert(err == '')
        # 等待fwdmd配置
        time.sleep(10)
        # 获取local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_after = int(out)
        # 检测比较local table是否增加了相应条数路由
        glx_assert((local_route_num_after - local_route_num_before - 1) == chnroute_num)
        # 删除SegmentAccProperties BatchRouteFilePath属性
        self.topo.dut1.get_rest_device().update_segment_acc_prop(segment_id=0, batch_route_file_path="")
        time.sleep(5)
        # 获取local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_after = int(out)
        # 检测比较路由数目是否恢复初始状态
        glx_assert(local_route_num_after == local_route_num_before + 1)
        # 关闭acc_enable
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

    def test_glx_segment_delivery_batch_route_when_vpp_restart(self):
        # 获取chnroute.txt中的路由数目
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wget -P /opt -N https://cdn.jsdelivr.net/gh/QiuSimons/Chnroute/dist/chnroute/chnroute.txt")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wc -l /opt/chnroute.txt")
        glx_assert(err == "")
        outlist = out.split(' ')
        chnroute_num = int(outlist[0])
        # 开启acc_enable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        # 获取acc table与local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_before = int(out)
        # 创建SegmentAccProperties，添加BatchRouteFilePath
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, batch_route_file_path="/opt/chnroute.txt", acc_fib_type="local")
        # 重启vpp
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart vpp")
        glx_assert(err == '')
        # 等待vpp配置
        time.sleep(10)
        # 获取local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_after = int(out)
        # 检测比较local table是否增加了相应条数路由
        glx_assert((local_route_num_after - local_route_num_before - 1) == chnroute_num)
        # 删除SegmentAccProperties BatchRouteFilePath属性
        self.topo.dut1.get_rest_device().update_segment_acc_prop(segment_id=0, batch_route_file_path="")
        time.sleep(5)
        # 获取local table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 0 | grep / | wc -l")
        glx_assert(err == "")
        local_route_num_after = int(out)
        # 检测比较路由数目是否恢复初始状态
        glx_assert(local_route_num_after == local_route_num_before + 1)
        # 关闭acc_enable
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

    def test_glx_segment_delivery_batch_route_when_routelabel_change(self):
        # 获取chnroute.txt中的路由数目
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wget -P /opt -N https://cdn.jsdelivr.net/gh/QiuSimons/Chnroute/dist/chnroute/chnroute.txt")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wc -l /opt/chnroute.txt")
        glx_assert(err == "")
        outlist = out.split(' ')
        chnroute_num = int(outlist[0])
        # 开启acc_enable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="0x777")
        # 创建SegmentAccProperties，添加BatchRouteFilePath
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, batch_route_file_path="/opt/chnroute.txt", acc_fib_type="acc")
        time.sleep(3)
        # 获取acc table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep 0x0000000777 | wc -l")
        glx_assert(err == "")
        acc_route_num_before = int(out)
        glx_assert(acc_route_num_before == chnroute_num)
        #修改routelabel
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="0x999")
        time.sleep(3)
        # 检测比较acc table是否增加了相应条数路由
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep 0x0000000777 | wc -l")
        glx_assert(err == "")
        acc_route_num_before = int(out)
        glx_assert(acc_route_num_before == 0)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep 0x0000000999 | wc -l")
        glx_assert(err == "")
        acc_route_num_after = int(out)
        glx_assert(acc_route_num_after == chnroute_num)
        # 删除SegmentAccProperties BatchRouteFilePath属性
        self.topo.dut1.get_rest_device().update_segment_acc_prop(segment_id=0, batch_route_file_path="")
        time.sleep(3)
        # 获取acc table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep 0x0000000999 | wc -l")
        glx_assert(err == "")
        acc_route_num_after = int(out)
        # 检测比较路由数目是否恢复初始状态
        glx_assert(acc_route_num_after == 0)
        # 关闭acc_enable
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)

    def test_glx_segment_delivery_batch_route_fib_src(self):
        # 获取chnroute.txt中的路由数目
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wget -P /opt -N https://cdn.jsdelivr.net/gh/QiuSimons/Chnroute/dist/chnroute/chnroute.txt")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("wc -l /opt/chnroute.txt")
        glx_assert(err == "")
        outlist = out.split(' ')
        chnroute_num = int(outlist[0])
        # 开启acc_enable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="0x777")
        # 获取acc table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep 0x0000000777 | wc -l")
        glx_assert(err == "")
        acc_route_num_before = int(out)
        glx_assert(acc_route_num_before == 0)
        # 创建SegmentAccProperties，添加BatchRouteFilePath
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, batch_route_file_path="/opt/chnroute.txt", acc_fib_type="acc")
        time.sleep(3)
        # 获取acc table中的路由数目
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 128 | grep 0x0000000777 | wc -l")
        glx_assert(err == "")
        acc_route_num_after = int(out)
        glx_assert(acc_route_num_after == chnroute_num)
        # 随机获取文件中的一条路由
        rand_num = random.randint(1, chnroute_num)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat /opt/chnroute.txt | head -n {rand_num} | tail -n +{rand_num}")
        glx_assert(err == "")
        route_entry = out
        # 检测fib src batch-route-delivery已下发
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {route_entry}")
        glx_assert(err == "")
        glx_assert("batch-route-delivery" in out)
        # 检测添加路由的优先级
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {route_entry} | grep forwarding -A 2 | awk '{{print $3}}'")
        glx_assert(err == "")
        glx_assert("dpo-drop" not in out)
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl ip route {route_entry} table 128 via drop")
        glx_assert(err == "")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128 {route_entry} | grep forwarding -A 2 | awk '{{print $3}}'")
        glx_assert(err == "")
        glx_assert("dpo-drop" in out)
        # 删除添加的drop路由
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl ip route del {route_entry} table 128 via drop")
        glx_assert(err == "")
        # 关闭acc_enable
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        time.sleep(3)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)
