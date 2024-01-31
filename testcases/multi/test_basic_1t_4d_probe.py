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

class TestBasic1T4DProbe(unittest.TestCase):

    # tst--dut1-(wan1+wan2)-dut2-bvi

    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return

        # dut1 WAN3-WAN5 disable nat direct
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN3", False)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", False)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN5", False)

        # dut2 WAN1 WAN2 disable overlay and nat direct
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN2", False)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN2", False)

        # 1<>2 WAN1 192.168.11.0/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.11.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.11.2/24")
        # gateway
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "192.168.11.2")

        # 1<>2 WAN2 192.168.12.0/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.12.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.12.2/24")
        # gateway
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN2", "192.168.12.2")

        # dut1 Lan1 ip
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.1.1/24", mtu=mtu)

        # dut2 bvi ip:
        self.topo.dut2.get_rest_device().set_default_bridge_ip_or_mtu("192.168.22.1/24", mtu=mtu)
    

        # 初始化tst接口
        self.topo.tst.add_ns("dut1")
        self.topo.tst.add_if_to_ns(self.topo.tst.if1, "dut1")

        # 添加tst节点ip及路由
        self.topo.tst.add_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.add_ns_route("dut1", "192.168.22.0/24", "192.168.1.1")

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # dut1 enable nat direct
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN2", True)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN3", True)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN4", True)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN5", True)

        # dut2 WAN1 WAN2 enable overlay and nat direct
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN2", True)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN2", True)

        # 1<>2 WAN1 192.168.11.0/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "")
        # gateway
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "")

        # 1<>2 WAN2 192.168.12.0/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "")
        # gateway
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN2", "")

        # revert dut1 dut2 WAN dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")

        # dut1 Lan1 ip
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)

        # dut2 bvi ip
        self.topo.dut2.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.1/24", mtu=mtu)

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.del_ns_if_ip("dut1", self.topo.tst.if1, "192.168.1.2/24")
        self.topo.tst.add_ns_if_to_default_ns("dut1", self.topo.tst.if1)

        # delete netem 
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 tc qdisc del dev WAN1 root netem")

        # delete probe
        self.topo.dut1.get_rest_device().delete_probe(name="probe1")
        self.topo.dut1.get_rest_device().delete_probe(name="probe2")
        # kill dnsmasq
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"kill -9 $(pidof dnsmasq)")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"rm /tmp/digdnswan1.conf")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"rm /tmp/digdnswan2.conf")
        # dut2 wan1 up
        dut2wan1 = self.topo.dut2.get_if_map()["WAN1"]
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"vppctl set interface state {dut2wan1} up")

        # wait for all passive link to be aged.
        time.sleep(20)

    # check probe result
    def test_probe_result(self):
        # set netem
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 tc qdisc del dev WAN1 root netem")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 tc qdisc add dev WAN1 root netem loss 20%")

        # create probe
        self.topo.dut1.get_rest_device().create_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="CMD_PING",
                                                      dst_addr="192.168.11.2",
                                                      dst_port=1111,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      tag1="",
                                                      tag2="")
        time.sleep(70)

        # check probe result
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 State")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(out == "0" or out == "1")

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 Rtt")
        out = float(out.rstrip())
        glx_assert(err == "")
        glx_assert(out > -2 and out < 2) # -1 means fail, else rtt should be in [0, 2] ms

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 AvgRtt")
        out = float(out.rstrip())
        glx_assert(err == "")
        glx_assert(out > 0 and out < 2) # 0 < avg rtt < 2

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 Jitter")
        out = float(out.rstrip())
        glx_assert(err == "")
        glx_assert(out > 0 and out < 2) # 0 < jitter < 2

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 Loss")
        out = float(out.rstrip())
        glx_assert(err == "")
        glx_assert(out > 0.1 and out < 0.3) # loss rate is set 20%, so 0.1 < loss < 0.3

    # mandatory wan1, mainly for auto switch
    def test_probe_with_mandatory_bizpol(self):
        # bizpol
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.22.0/24",
                                                       steering_type=1,
                                                       steering_mode=1, # mandatory
                                                       steering_interface="WAN1",
                                                       protocol=0,
                                                       direct_enable=True)

        # create probe
        self.topo.dut1.get_rest_device().create_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="CMD_PING",
                                                      dst_addr="192.168.11.2",
                                                      dst_port=1111,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      tag1="",
                                                      tag2="")
        time.sleep(10)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("192.168.11.2" in out)

       # wan names
        dut1wan1 = self.topo.dut1.get_if_map()["WAN1"]
        dut1wan2 = self.topo.dut1.get_if_map()["WAN2"]
        dut2wan1 = self.topo.dut2.get_if_map()["WAN1"]

        # 首包会因为arp而丢失
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 1")
        glx_assert(err == '')
        time.sleep(1)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")

        # ping another time
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # wan1 tx packets >= packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan1}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        glx_assert(tx_packets_line)
        tx_packets = tx_packets_line[0].split()[-1]
        # print(tx_packets)
        glx_assert(int(tx_packets) >= 100)
        
        # dut2 wan1 down
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {dut2wan1} down")
        glx_assert(err == '')
        time.sleep(10)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")
        
        # all loss
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)
        time.sleep(5)

        # wan1 tx packets < packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan2}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        if tx_packets_line:
            tx_packets = tx_packets_line[0].split()[-1]
            # print(tx_packets)
            glx_assert(int(tx_packets) < 100)

        # dut2 wan1 up
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {dut2wan1} up")
        glx_assert(err == '')
        time.sleep(10)
        
        # 首包会因为arp而丢失
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 1")
        glx_assert(err == '')
        time.sleep(1)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")

        # ping another time
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # wan1 tx packets >= packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan1}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        glx_assert(tx_packets_line)
        tx_packets = tx_packets_line[0].split()[-1]
        # print(tx_packets)
        glx_assert(int(tx_packets) >= 100)

        # update probe
        self.topo.dut1.get_rest_device().update_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="CMD_PING",
                                                      dst_addr="2.2.2.2",
                                                      dst_port=1111,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      tag1="",
                                                      tag2="")
        time.sleep(10)

        # check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("2.2.2.2" in out)
        
        # 首包会因为arp而丢失
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 1")
        glx_assert(err == '')
        time.sleep(1)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")

        # ping another time
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # wan1 tx packets >= packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan1}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        glx_assert(tx_packets_line)
        tx_packets = tx_packets_line[0].split()[-1]
        # print(tx_packets)
        glx_assert(int(tx_packets) >= 100)

        # delete probe
        self.topo.dut1.get_rest_device().delete_probe(name="probe1")
        time.sleep(10)

        # get if index
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget VppIfIndexContext#WAN1 IfIndex")
        glx_assert(err == "")
        dut1wan1index = out.rstrip()

        # vpp probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        wan1line = [line for line in lines if f"sw-if-index {dut1wan1index}" in line]
        glx_assert(wan1line)
        glx_assert("init" in wan1line[0])

        # delete bizpol
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

    # available wan1, mainly for auto switch
    def test_probe_with_available_bizpol(self):
        # bizpol
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="192.168.22.0/24",
                                                       steering_type=1,
                                                       steering_mode=0, # available
                                                       steering_interface="WAN1",
                                                       protocol=0,
                                                       direct_enable=True)

        # create probe
        self.topo.dut1.get_rest_device().create_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="CMD_PING",
                                                      dst_addr="192.168.11.2",
                                                      dst_port=1111,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      tag1="",
                                                      tag2="")
        time.sleep(10)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("192.168.11.2" in out)
        
        # wan names
        dut1wan1 = self.topo.dut1.get_if_map()["WAN1"]
        dut1wan2 = self.topo.dut1.get_if_map()["WAN2"]
        dut2wan1 = self.topo.dut2.get_if_map()["WAN1"]

        # 首包会因为arp而丢失
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 1")
        glx_assert(err == '')
        time.sleep(1)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")

        # ping another time
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # wan1 tx packets >= packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan1}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        glx_assert(tx_packets_line)
        tx_packets = tx_packets_line[0].split()[-1]
        # print(tx_packets)
        glx_assert(int(tx_packets) >= 100)

        # dut2 wan1 down
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {dut2wan1} down")
        glx_assert(err == '')
        time.sleep(10)

        # 首包会因为arp而丢失
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 1")
        glx_assert(err == '')
        time.sleep(1)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")

        # ping another time
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # wan2 tx packets >= packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan2}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        glx_assert(tx_packets_line)
        tx_packets = tx_packets_line[0].split()[-1]
        # print(tx_packets)
        glx_assert(int(tx_packets) >= 100)

        # dut2 wan1 up
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {dut2wan1} up")
        glx_assert(err == '')
        time.sleep(10)

        # 首包会因为arp而丢失
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 1")
        glx_assert(err == '')
        time.sleep(1)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")

        # ping another time
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # wan1 tx packets >= packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan1}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        glx_assert(tx_packets_line)
        tx_packets = tx_packets_line[0].split()[-1]
        # print(tx_packets)
        glx_assert(int(tx_packets) >= 100)

        # update probe
        self.topo.dut1.get_rest_device().update_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="CMD_PING",
                                                      dst_addr="2.2.2.2",
                                                      dst_port=1111,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      tag1="",
                                                      tag2="")
        time.sleep(10)

        # check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("2.2.2.2" in out)

        # 首包会因为arp而丢失
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 1")
        glx_assert(err == '')
        time.sleep(1)

        # clear counter
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl clear interfaces")
        glx_assert(err == "")

        # ping another time
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # wan2 tx packets >= packet sent
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"vppctl show int {dut1wan2}")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        tx_packets_line = [line for line in lines if "tx packets" in line]
        glx_assert(tx_packets_line)
        tx_packets = tx_packets_line[0].split()[-1]
        # print(tx_packets)
        glx_assert(int(tx_packets) >= 100)

        # delete probe
        self.topo.dut1.get_rest_device().delete_probe(name="probe1")
        time.sleep(10)

        # get if index
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget VppIfIndexContext#WAN1 IfIndex")
        glx_assert(err == "")
        dut1wan1index = out.rstrip()

        # vpp probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        wan1line = [line for line in lines if f"sw-if-index {dut1wan1index}" in line]
        glx_assert(wan1line)
        glx_assert("init" in wan1line[0])

        # delete bizpol
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")

    # dig dns, mainly for redis and vpp state
    def test_probe_dig_dns(self):

        # 为dut2设备的wan1 wan2 dnsmasq添加conf文件
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"touch /tmp/digdnswan1.conf")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"echo 'listen-address=192.168.11.2' > /tmp/digdnswan1.conf") # dnsmasq won't reply if 0.0.0.0 
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"echo 'no-resolv' >> /tmp/digdnswan1.conf") # ignore /etc/resolv.conf
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"echo 'address=/www.baidu.com/11.11.11.11' >> /tmp/digdnswan1.conf")# set A record

        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"touch /tmp/digdnswan2.conf")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"echo 'listen-address=192.168.12.2' > /tmp/digdnswan2.conf")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"echo 'no-resolv' >> /tmp/digdnswan2.conf")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"echo 'address=/www.baidu.com/22.22.22.22' >> /tmp/digdnswan2.conf")

        # start dut2 wan1 wan2 dnsmasq
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN1 dnsmasq -p 1153 -C /tmp/digdnswan1.conf")
        glx_assert(err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns-wan-WAN2 dnsmasq -p 2253 -C /tmp/digdnswan2.conf")
        glx_assert(err == '')

        # dut2 wan1 wan2 enable overlay (set unspec then overlay finally revert)
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN2", True)
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.11.2/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.12.2/24")

        # create probe
        self.topo.dut1.get_rest_device().create_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="DIG_DNS",
                                                      dst_addr="192.168.11.2",
                                                      dst_port=1153,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      tag1="",
                                                      tag2="")
        self.topo.dut1.get_rest_device().create_probe(name="probe2",                                                             
                                                      type="WAN",
                                                      if_name="WAN2",
                                                      mode="DIG_DNS",
                                                      dst_addr="192.168.12.2",
                                                      dst_port=2253,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      tag1="",
                                                      tag2="")
        time.sleep(10)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("192.168.11.2" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe2 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("192.168.12.2" in out)

        # fwdmd probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 State")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe2 State")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("1" in out)

        # get if index
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget VppIfIndexContext#WAN1 IfIndex")
        glx_assert(err == "")
        dut1wan1index = out.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget VppIfIndexContext#WAN2 IfIndex")
        glx_assert(err == "")
        dut1wan2index = out.rstrip()

        # vpp probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        wan1line = [line for line in lines if f"sw-if-index {dut1wan1index}" in line]
        glx_assert(wan1line)
        glx_assert("probe_up" in wan1line[0])
        wan2line = [line for line in lines if f"sw-if-index {dut1wan2index}" in line]
        glx_assert(wan2line)
        glx_assert("probe_up" in wan2line[0])

        # dut2 wan1 down
        dut2wan1 = self.topo.dut2.get_if_map()["WAN1"]
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {dut2wan1} down")
        glx_assert(err == '')
        time.sleep(10)

        # fwdmd probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 State")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("0" in out) # dut2 wan1 down
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe2 State")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("1" in out)
        
        # vpp probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        wan1line = [line for line in lines if f"sw-if-index {dut1wan1index}" in line]
        glx_assert(wan1line)
        glx_assert("probe_down" in wan1line[0]) # dut2 wan1 down
        wan2line = [line for line in lines if f"sw-if-index {dut1wan2index}" in line]
        glx_assert(wan2line)
        glx_assert("probe_up" in wan2line[0])

        # dut2 wan1 up
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface state {dut2wan1} up")
        glx_assert(err == '')
        time.sleep(10)

        # fwdmd probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe1 State")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget ProbeState#probe2 State")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("1" in out)

        # vpp probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        wan1line = [line for line in lines if f"sw-if-index {dut1wan1index}" in line]
        glx_assert(wan1line)
        glx_assert("probe_up" in wan1line[0])
        wan2line = [line for line in lines if f"sw-if-index {dut1wan2index}" in line]
        glx_assert(wan2line)
        glx_assert("probe_up" in wan2line[0])

        # delete probe
        self.topo.dut1.get_rest_device().delete_probe(name="probe1")
        self.topo.dut1.get_rest_device().delete_probe(name="probe2")
        time.sleep(10)

        # vpp probe state
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx nat-interface")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        wan1line = [line for line in lines if f"sw-if-index {dut1wan1index}" in line]
        glx_assert(wan1line)
        glx_assert("init" in wan1line[0])
        wan2line = [line for line in lines if f"sw-if-index {dut1wan2index}" in line]
        glx_assert(wan2line)
        glx_assert("init" in wan2line[0])

        # kill dnsmasq
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"kill -9 $(pidof dnsmasq)")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"rm /tmp/digdnswan1.conf")
        self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f"rm /tmp/digdnswan2.conf")

    def test_probe_only(self):
        # bizpol，强制全部流量走WAN1
        resp = self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.1.0/24",
                                                       dst_prefix="0.0.0.0",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       protocol=0,
                                                       direct_enable=True)
        glx_assert(201 == resp.status_code)

        # 配置probe only，访问一个不存在的ip
        resp = self.topo.dut1.get_rest_device().create_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="CMD_PING",
                                                      dst_addr="1.1.1.1",
                                                      dst_port=1111,
                                                      interval=1,
                                                      timeout=1,
                                                      fail_threshold=2,
                                                      ok_threshold=2,
                                                      probe_only=True,
                                                      tag1="",
                                                      tag2="")
        glx_assert(201 == resp.status_code)
        time.sleep(10)

        # 不影响正常的nat转发
        out, err = self.topo.tst.get_ns_cmd_result("dut1", "ping 192.168.22.1 -c 100 -i 0.01")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)
        time.sleep(5)

        # 清理环境
        resp = self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().delete_probe(name="probe1")
        glx_assert(410 == resp.status_code)

if __name__ == '__main__':
    unittest.main()
 
