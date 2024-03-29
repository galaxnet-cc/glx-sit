from cgi import test
import random
import unittest
import time

from os.path import join

from lib.util import glx_assert
from topo.topo_1d import Topo1D


class TestRestVppConsistency1DBasic(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_multi_bridge(self):
        mtu = 1500
        self.topo.dut1.get_rest_device().create_bridge("test", "192.168.89.1/24", mtu=mtu)
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("up" in out)
        glx_assert("192.168.89.1/24" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-test")
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" in out)
        # update bridge
        self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu("test", "192.168.90.1/24", mtu=mtu)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("up" in out)
        glx_assert("192.168.89.1/24" not in out)
        glx_assert("192.168.90.1/24" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-test")
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" not in out)
        glx_assert("192.168.90.1/24" in out)

        self.topo.dut1.get_rest_device().delete_bridge("test")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("up" not in out)
        glx_assert("192.168.90.1/24" not in out)
        # linux side if have been removed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip link")
        glx_assert(err == '')
        glx_assert("br-test" not in out)
    def test_bridge_mtu(self):
        mtu = 2000
        brname = "test"
        lcpname = "br-" + brname
        ip = "192.168.89.1/24"
        ns = "ctrl-ns"
        # create bridge with mtu
        self.topo.dut1.get_rest_device().create_bridge(brname, ip, mtu=mtu)
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {bviSwIfIndex} | awk '{{print $4}}'")
        glx_assert(err == '')
        glx_assert(str(mtu) in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ip link show {lcpname}")
        glx_assert(err == '')
        glx_assert(f"mtu {mtu}" in out)

        # update bridge with mtu
        mtu = 3000
        self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu(brname, ip, mtu=mtu)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {bviSwIfIndex} | awk '{{print $4}}'")
        glx_assert(err == '')
        glx_assert(str(mtu) in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ip link show {lcpname}")
        glx_assert(err == '')
        glx_assert(f"mtu {mtu}" in out)

        self.topo.dut1.get_rest_device().delete_bridge(brname)



    def get_bd_id(self, ssh_device, bridge_name):
        out, err = ssh_device.get_cmd_result(f"redis-cli hget BridgeIdContext#{bridge_name} BdId")
        glx_assert(err == '')
        out = out.rstrip()
        out.replace('"', '')
        return out

    def test_physical_interface(self):
        # 验证mtu属性更新(routed only)
        mtu = 1500
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        self.topo.dut1.get_rest_device().create_bridge("test", "192.168.89.1/24", mtu=mtu)
        self.topo.dut1.get_rest_device().create_bridge("test23", "192.168.90.1/24", mtu=mtu)
        self.topo.dut1.get_rest_device().update_physical_interface("WAN2", 1600, "routed", "")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("1600/0/0/0" in out)

        # change mode to switched
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1600, "switched", "test")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        bd_id = self.get_bd_id(self.topo.dut1.get_vpp_ssh_device(), "test")
        glx_assert(f"bridge bd-id {bd_id}" in out)
        # check host side
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr")
        glx_assert(err == '')
        glx_assert("WAN2" not in out)
        # change bridge
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1500, "switched", "test23")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int {wan2VppIf}")
        glx_assert(err == '')
        # when change to bridge, the mtu will be keeped, we do not
        # apply mtu for bridged interface.
        glx_assert("1600/0/0/0" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        bd_id = self.get_bd_id(self.topo.dut1.get_vpp_ssh_device(), "test23")
        glx_assert(f"bridge bd-id {bd_id}" in out)

        # check ip address set on logical interface when it's underlying physical
        # interface under switched mode is not allowed.
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.1.1/24")
        # this should be failed with 500.
        glx_assert(result.status_code == 500)

        # change to routed（此时OverlayEnable将关闭）
        self.topo.dut1.get_rest_device().update_physical_interface(
            "WAN2", 1600, "routed", "")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("bridge" not in out)
        # check host side
        # 因为OverlayEnable关闭，所以在ctrl-ns(segment 0)中。
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show dev WAN2")
        glx_assert(err == '')
        glx_assert("1600" in out)
        self.topo.dut1.get_rest_device().delete_bridge("test")
        self.topo.dut1.get_rest_device().delete_bridge("test23")

        # check ip address set on logical interface is ok
        expectedIp = "192.168.1.1/24"
        result = self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", expectedIp)
        glx_assert(result.status_code != 500)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert(expectedIp in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        glx_assert(err == '')
        glx_assert(expectedIp in out)
        # change back to dhcp mode.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert(expectedIp not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        glx_assert(err == '')
        glx_assert(expectedIp not in out)

        # 验证重新打开OverlayEnable（需要先置unspec），成为出厂默认配置
        result = self.topo.dut1.get_rest_device().set_logical_interface_unspec("WAN2")
        glx_assert(result.status_code != 500)
        result = self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN2", True)
        glx_assert(result.status_code != 500)
        # 切换至独立ctrl-ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip link")
        glx_assert(err == '')
        glx_assert('WAN2' in out)

    # the states update every 1 minute, so maybe there is nothing in redis,
    # but usually we run this test more than 1 minute after fwdmd starts
    def test_physical_interface_state(self):
        time.sleep(60)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli keys PhysicalInterfaceState#*")
        glx_assert(err == "")
        lines = out.strip().split('\n')
        phyIfs = [line.strip().lstrip("PhysicalInterfaceState#") for line in lines if "PhysicalInterfaceState#" in line]
        glx_assert(phyIfs)

        # check each physical interface info
        for phyIf in phyIfs:
            out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"redis-cli hget PhysicalInterfaceState#{phyIf} Name")
            glx_assert(err == "")
            glx_assert(phyIf == out.strip())

            out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"redis-cli hget PhysicalInterfaceState#{phyIf} Speed")
            glx_assert(err == "")
            speed = int(out.strip())  
            glx_assert(speed >= 0)

            out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"redis-cli hget PhysicalInterfaceState#{phyIf} Duplex")
            glx_assert(err == "")
            duplex = int(out.strip())  
            glx_assert(duplex >= 0 and duplex <= 2)

            out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                f"redis-cli hget PhysicalInterfaceState#{phyIf} Flags")
            glx_assert(err == "")
            flags = int(out.strip())  
            glx_assert(flags >= 0 and flags <= 3)

    def test_static_property_update(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)

        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.2.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        # kernel side.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)

        # set gw.
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "192.168.2.254")
        tableId, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show  int addr {wan1VppIf} | grep ip4 | awk '{{print $5}}'")
        glx_assert(err == '')
        tableId = tableId.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table {tableId} 0.0.0.0/0")
        glx_assert(err == '')
        glx_assert("192.168.2.254" in out)
        # kernel side.
        # 0815: WAN gw route not programmed to kernel now.
        # out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
        #     f"ip netns exec ctrl-ns ip route show default")
        # glx_assert(err == '')
        # glx_assert("192.168.2.254" in out)
        # update gw.
        self.topo.dut1.get_rest_device().set_logical_interface_static_gw("WAN1", "192.168.2.252")
        tableId, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show  int addr {wan1VppIf} | grep ip4 | awk '{{print $5}}'")
        glx_assert(err == '')
        tableId = tableId.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table {tableId} 0.0.0.0/0")
        glx_assert(err == '')
        glx_assert("192.168.2.254" not in out)
        glx_assert("192.168.2.252" in out)
        # 0815: WAN gw route not programmed to kernel now.
        # # kernel side.
        # out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
        #     f"ip netns exec ctrl-ns ip route show default")
        # glx_assert(err == '')
        # glx_assert("192.168.2.254" not in out)
        # glx_assert("192.168.2.252" in out)

        # change back to dhcp.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)

    def test_pppoe_property_update(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]

        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        # check kernel using correct user and password.
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /tmp/glx-pppd-cfg-WAN1")
        glx_assert(err == '')
        glx_assert(f"test" in out)
        glx_assert(f'123456' in out)
        # get orig pid.
        pid1, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /var/run/glx-pppd-WAN1.pid")
        glx_assert(err == '')
        glx_assert(pid1 != "")

        # update user and password.
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "hahaha", "654321")
        # check kernel using correct user and password.
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /tmp/glx-pppd-cfg-WAN1")
        glx_assert(err == '')
        glx_assert(f'hahaha' in out)
        glx_assert(f'654321' in out)
        # get new pid.
        pid2, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat /var/run/glx-pppd-WAN1.pid")
        glx_assert(err == '')
        glx_assert(pid2 != "")
        # pid should changed to take effect of new auth info.
        glx_assert(pid1 != pid2)

        # change back to dhcp.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)

    def test_change_pppoe_when_link_exists(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        
        ifIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan1VppIf} | grep {wan1VppIf} | awk '{{print $2}}'")
        glx_assert(err == '')

        resp = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        glx_assert(resp.status_code == 200)

        pppoxIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int pppox0 | grep pppox0 | awk '{{print $2}}'")
        glx_assert(err == '')

        # 建两条link，保证每条link上对应的WAN口都被刷新
        resp = self.topo.dut1.get_rest_device().create_glx_link(link_id=1)
        glx_assert(resp.status_code == 201)
        resp = self.topo.dut1.get_rest_device().create_glx_link(link_id=2, remote_ip="100.64.0.1")
        glx_assert(resp.status_code == 201)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link id 1")
        glx_assert(err == '')
        glx_assert(f"wan-sw-if-index {pppoxIfIndex}" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link id 2")
        glx_assert(err == '')
        glx_assert(f"wan-sw-if-index {pppoxIfIndex}" in out)

        resp = self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        glx_assert(resp.status_code == 200)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link id 1")
        glx_assert(err == '')
        glx_assert(f"wan-sw-if-index {ifIndex}" in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link id 2")
        glx_assert(err == '')
        glx_assert(f"wan-sw-if-index {ifIndex}" in out)

        resp = self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        glx_assert(resp.status_code == 410)
        resp = self.topo.dut1.get_rest_device().delete_glx_link(link_id=2)
        glx_assert(resp.status_code == 410)

    def test_pppoe_address_subscribe(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        pppoeLink = "pppoe-WAN1"

        resp = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        glx_assert(resp.status_code == 200)

        # 检查netlink socket
        pid, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep fwdmd | grep -v grep | awk '{print $2}'")
        glx_assert(err == '')
        
        out, _ = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"lsof -p {pid} | grep NETLINK")
        glx_assert(err == '')
        glx_assert("protocol: NETLINK" in out)

        # 等待接口
        cnt = 0
        while True:
            _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip link show {pppoeLink}")
            cnt += 1
            if err == '' or cnt == 20:
                cnt = 0
                break
            time.sleep(1)

        ip = "100.64.0.1/32"
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip addr add {ip} dev {pppoeLink}")
        glx_assert(err == '')
        
        # 此时应当立马订阅到地址
        time.sleep(2)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr pppox0")
        glx_assert(err == '')
        glx_assert(ip in out)
        _, _ = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip addr flush dev {pppoeLink}")

        resp = self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        glx_assert(resp.status_code == 200)

    def test_pppoe_address_subscribe_restart(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        pppoeLink = "pppoe-WAN1"

        resp = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        glx_assert(resp.status_code == 200)

        # 重启fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("systemctl restart fwdmd")
        glx_assert(err == '')

        time.sleep(3)

        pid, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep fwdmd | grep -v grep | awk '{print $2}'")
        glx_assert(err == '')
        
        # socket应该还要监听着
        out, _ = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"lsof -p {pid} | grep NETLINK")
        glx_assert(err == '')
        glx_assert("protocol: NETLINK" in out)

        fd, _ = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"lsof -p {pid} 2>/dev/null | grep NETLINK | awk '{{print $4}}' | sed 's/u$//'")

        ip = "100.64.0.2/32"
        cnt = 0
        while True:
            _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip link show {pppoeLink}")
            cnt += 1
            if err == '' or cnt == 20:
                cnt = 0
                break
            time.sleep(1)
        _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip addr add {ip} dev {pppoeLink}")

        if err != '':
            while True:
                _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip link show {pppoeLink}")
                cnt += 1
                if err == '' or cnt == 20:
                    cnt = 0
                    break
                time.sleep(1)
            _, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip addr add {ip} dev {pppoeLink}")
            glx_assert(err == '')
         
        # 此时应当立马订阅到地址
        time.sleep(2)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr pppox0")
        glx_assert(err == '')
        glx_assert(ip in out)
        _, _ = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result("ctrl-ns-wan-WAN1", f"ip addr flush dev {pppoeLink}")

        resp = self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        glx_assert(resp.status_code == 200)

    def test_multi_wan_address_type_switch(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        # change address type to static from static
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.2/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.2/24" in out)
        glx_assert("192.168.2.1/24" not in out)

        # change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.3/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.3/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)

        # change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)
        glx_assert("pppox1" in out)
        # try to add address to pppoe interface to simulate pppoe
        # sync ip from kernel.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address pppox0 1.1.1.1/32")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address pppox1 1.1.1.2/32")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address del pppox0 1.1.1.1/32")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl set interface ip address del pppox1 1.1.1.2/32")
        glx_assert(err == '')

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        glx_assert("192.168.1.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        glx_assert("192.168.1.3/24" not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.2.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.4/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        glx_assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN2 ip addr show WAN2")
        glx_assert(err == '')
        glx_assert("192.168.2.4/24" in out)
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.2.2/24" not in out)
        glx_assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" not in out)
        glx_assert("pppox1" not in out)

        # change to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert(f'{wan2VppIf}' in out)

        # change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)
        glx_assert("pppox1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' not in out)
        glx_assert(f'{wan2VppIf}' not in out)

        # change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" not in out)
        glx_assert("pppox1" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" in out)

    def test_change_address_type_to_static_from_static(self):
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check logical interface using static address type
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        # change ip and verify again
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)

        # test_change_address_type_to_dhcp_from_static
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" not in out)
        glx_assert("192.168.1.2/24" not in out)

        # test_change_address_type_to_static_from_dhcp
        # change address to static
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.3/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.3/24" in out)

        # test_change_address_type_to_pppoe_from_static
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)

        # test_change_address_type_to_static_from_pppoe
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.4/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.4/24" in out)
        # check if pppoe related configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ps -ef | grep ppp")
        glx_assert(err == '')

        # test change address type to dhcp from pppoe
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        # change to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox" not in out)

        # test_change_address_type_to_pppoe_from_dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert("pppox0" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        glx_assert(err == '')
        glx_assert("No pppoe servers configured" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        glx_assert(err == '')
        glx_assert("No pppoe clients configured" not in out)

        # recovery to dhcp
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")

    def test_firewall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl3", 3, "192.168.11.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("test_acl3" in out)
        glx_assert("192.168.11.2/32" in out)
        # update
        self.topo.dut1.get_rest_device().update_fire_wall_rule(
            "test_acl3", 3, "192.168.12.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("192.168.12.2/32" in out)
        glx_assert("192.168.11.2/32" not in out)
        # delete
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("test_acl3" not in out)
        glx_assert("192.168.12.2/32" not in out)

    def test_multi_firewall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl3", 3, "192.168.11.3/32", "Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl5", 5, "192.168.11.5/32", "Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl4", 4, "192.168.11.4/32", "Deny")
        # We now apply firewall and bizpol to segment loop.
        # Use redis to get default segment's loop.
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                    f"redis-cli hget SegmentContext#0 LoopSwIfIndex")
        glx_assert(err == '')
        ifindex = ifindex.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show acl-plugin interface sw_if_index {ifindex} acl")
        glx_assert(err == '')
        pos3 = out.index('192.168.11.3')
        pos4 = out.index('192.168.11.4')
        pos5 = out.index('192.168.11.5')
        glx_assert(pos5 < pos4 < pos3)
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl4")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl5")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        glx_assert(err == '')
        glx_assert("test_acl3" not in out)
        glx_assert("test_acl4" not in out)
        glx_assert("test_acl5" not in out)

    def test_host_stack_dnsmasq(self):
        # set a false dhcp router, check if it can be reconfigured
        name = "default"
        cfg_path = join("/var/run/glx/dnsmasq", name)
        options = [
            {"OptionCode": 3, "OptionValue": "192.168.88"}
        ]
        result = self.topo.dut1.get_rest_device().set_host_stack_dnsmasq(name=name, start_ip="192.168.88.50", 
                                                                  ip_num=101, lease_time="12h", 
                                                                  dhcp_enable=True, options=options)
        glx_assert(result.status_code == 500)
        options = [
            {"OptionCode": 3, "OptionValue": "192.168.88.1"}, {"OptionCode": 6, "OptionValue": "8.8.8.8"}
        ]
        result = self.topo.dut1.get_rest_device().set_host_stack_dnsmasq(name=name, start_ip="192.168.88.50", 
                                                                  ip_num=101, lease_time="12h", 
                                                                  dhcp_enable=True, options=options)
        glx_assert(result.status_code == 201)
        time.sleep(3)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        # check base configuration
        glx_assert("glx_dnsmasq.pid" in out)
        glx_assert("base.conf" in out)
        # check dhcp configuration exists
        glx_assert(f"dhcp_{name}.conf" in out)
        glx_assert(f"dhcp_{name}.leases" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"cat {cfg_path}/dhcp_{name}.conf")
        glx_assert(err == '')
        # check dhcp configuration format
        glx_assert("dhcp-range=192.168.88.50,192.168.88.150,255.255.255.0,12h" in out)
        glx_assert("dhcp-option=6,8.8.8.8" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        # update dhcp configuration
        options = [
            {"OptionCode": 3, "OptionValue": "192.168.88.1"}, {"OptionCode": 6, "OptionValue": "114.114.114.114"}
        ]
        result = self.topo.dut1.get_rest_device().update_host_stack_dnsmasq(name=name, start_ip="192.168.88.100",
                                                                   ip_num=101, lease_time="12h", 
                                                                   dhcp_enable=True, options=options)
        time.sleep(3)
        glx_assert(result.status_code == 200)
        # check dhcp configuration format
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"cat {cfg_path}/dhcp_{name}.conf")
        glx_assert(err == '')
        # 192.168.88.1 is bvi ip address
        glx_assert("dhcp-option=3,192.168.88.1" in out)
        glx_assert("dhcp-range=192.168.88.50,192.168.88.150,255.255.255.0,12h" not in out)
        glx_assert("dhcp-range=192.168.88.100,192.168.88.200,255.255.255.0,12h" in out)
        glx_assert("dhcp-option=6,114.114.114.114" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        # check dns configuration
        resp = self.topo.dut1.get_rest_device().update_host_stack_dnsmasq(name=name, local_dns_server_enable=True,
                                                                acc_dns_server1="8.8.8.8", local_dns_server1="114.114.114.114",
                                                                acc_domain_list="a.b.c|d.e.f", local_domain_list="u.v.w|x.y.z")
        glx_assert(200 == resp.status_code)
        # check dhcp configuration doesn't exist
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(f"dhcp_{name}.conf" not in out)
        # check dns configuration exists
        glx_assert(f"dns_{name}.conf" in out)

        
        # check dns configuration format
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat {cfg_path}/dns_{name}.conf")
        glx_assert(err == '')
        glx_assert("server=114.114.114.114" in out)
        glx_assert("/a.b.c/acc" in out)
        glx_assert("/d.e.f/acc" in out)
        glx_assert("/u.v.w/local" in out)
        glx_assert("/x.y.z/local" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        # update dns configuration
        result = self.topo.dut1.get_rest_device().update_host_stack_dnsmasq(name=name, local_dns_server_enable=True,
                                                                acc_dns_server1="8.8.8.8", acc_dns_server2 = "1.1.1.1", 
                                                                local_dns_server1="114.114.114.114", local_dns_server2="223.5.5.5",
                                                                acc_domain_list="a.b.c|d.e.f", local_domain_list="u.v.w|x.y.z")

        # check dns configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(f"dns_{name}.conf" in out)

        # check dns configuration format
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat {cfg_path}/dns_{name}.conf")
        glx_assert(err == '')
        glx_assert("server=114.114.114.114" in out)
        glx_assert("server=223.5.5.5" in out)
        glx_assert("/a.b.c/acc" in out)
        glx_assert("/d.e.f/acc" in out)
        glx_assert("/u.v.w/local" in out)
        glx_assert("/x.y.z/local" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        # delete and verify
        resp = self.topo.dut1.get_rest_device().delete_host_stack_dnsmasq(name)
        glx_assert(410 == resp.status_code)
        time.sleep(3)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        glx_assert("glx_dnsmasq.pid" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" not in out)

    # 之前存在fwdmd做配置恢复的时候创建了多个dnsmasq进程，现在添加该测试避免该情况
    def test_host_stack_dnsmasq_unique(self):
        name = "default"
        cfg_path = join("/var/run/glx/dnsmasq", name)
        options=[
            {"OptionCode": 3, "OptionValue": "192.168.88.1"}, {"OptionCode": 6, "OptionValue": "8.8.8.8"}
        ]
        result=self.topo.dut1.get_rest_device().set_host_stack_dnsmasq(name=name, start_ip="192.168.88.50", 
                                                                  ip_num=101, lease_time="12h",
                                                                  dhcp_enable=True, options=options)
        glx_assert(result.status_code == 201)
        time.sleep(3)
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("systemctl restart vpp")
        self.topo.dut1.get_vpp_ssh_device().get_cmd_result("systemctl restart fwdmd")
        time.sleep(10)

        cnt, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ps aux | grep 'dnsmasq -C {cfg_path}/base.conf' | grep -v 'grep' | wc -l")
        glx_assert(err == '')
        cnt = int(cnt)
        glx_assert(cnt == 1)

        # delete and verify
        self.topo.dut1.get_rest_device().delete_host_stack_dnsmasq(name)
        time.sleep(3)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        glx_assert("glx_dnsmasq.pid" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" not in out)

    def test_bridge(self):
        # Add new ip address
        mtu = 1500
        self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu("default", "192.168.1.1/24", mtu=mtu)
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#default BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-default")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        # update and verify
        self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu("default", "192.168.1.2/24", mtu=mtu)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show br-default")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        glx_assert("192.168.1.1/24" not in out)

        # clear ip address
        resp = self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu("default", "", mtu=mtu)
        glx_assert(200 == resp.status_code)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("L3" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(
            "ctrl-ns", f"ip addr show br-default")
        glx_assert(err == '')
        glx_assert("inet 192.168.1.2/24 scope global br-default" not in out)

        # recovery ip address to 88.1
        resp = self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu("default", "192.168.88.1/24", mtu=mtu)
        glx_assert(200 == resp.status_code)



    # the interface is very generic so we only
    # test it works by some table.
    # Use BridgeTable because it do not depend on interface much.
    def test_update_config(self):
        data={}
        data["IgnoreNotSpecifiedTable"] = True
        bridgeTable = {}
        bridgeTable["Table"] = "Bridge"
        defBridge = {}
        defBridge["Name"] = "default"
        defBridge["BviEnable"] = True
        defBridge["BviIpAddrWithPrefix"] = "192.168.89.1/24"
        bridgeTable["Items"] = []
        bridgeTable["Items"].append(defBridge)
        data["Tables"] = []
        data["Tables"].append(bridgeTable)

        self.topo.dut1.get_rest_device().update_config_action(data)
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" in out)
        glx_assert("192.168.88.1/24" not in out)

        # change back.
        data2 = {}
        data2["IgnoreNotSpecifiedTable"] = True
        bridgeTable2 = {}
        bridgeTable2["Table"] = "Bridge"
        defBridge2 = {}
        defBridge2["Name"] = "default"
        defBridge2["BviEnable"] = True
        defBridge2["BviIpAddrWithPrefix"] = "192.168.88.1/24"
        bridgeTable2["Items"] = []
        bridgeTable2["Items"].append(defBridge2)
        data2["Tables"] = []
        data2["Tables"].append(bridgeTable2)

        self.topo.dut1.get_rest_device().update_config_action(data2)
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {bviSwIfIndex}")
        glx_assert(err == '')
        glx_assert("192.168.89.1/24" not in out)
        glx_assert("192.168.88.1/24" in out)

    def test_multi_segment(self):
        # create segment
        # change LAN1 to routed
        # set LAN1 to segment because it's address will be in UNSPEC mode.
        # (TODO): currently not supported. check LAN1 in seperate linux-ns
        # try delete segment, it will be blocked due to have reference.
        self.topo.dut1.get_rest_device().create_segment(1)
        self.topo.dut1.get_rest_device().update_physical_interface("LAN1", 1500, "routed", "")
        self.topo.dut1.get_rest_device().set_logical_interface_segment("LAN1", 1)
        result = self.topo.dut1.get_rest_device().delete_segment(1)
        # this should be failed with 500 because there are reference to the segment.
        glx_assert(result.status_code == 500)

        # change back to the segment 0
        self.topo.dut1.get_rest_device().set_logical_interface_segment("LAN1", 0)
        result = self.topo.dut1.get_rest_device().delete_segment(1)
        # this should be ok with 410 (http StatusGone)
        glx_assert(result.status_code == 410)
        # check back to switched interface.
        self.topo.dut1.get_rest_device().update_physical_interface("LAN1", 1500, "switched", "default")

    def test_segment_validation(self):
        # 未启用acc不能启用dns ip collect
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, dns_ip_collect_enable=True)
        glx_assert(resp.status_code == 500)
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        # 启用acc不能启用int-edge
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, int_edge_enable=True)
        glx_assert(resp.status_code == 500)
        # 启用检验非法的route label
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="xxxxx")
        glx_assert(resp.status_code == 500)

        # 打开acc并打开dns_ip_collect_enable
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True, route_label="0x1", dns_ip_collect_enable=True)
        glx_assert(resp.status_code == 200)

        # 恢复到原来的状态
        resp = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)
        glx_assert(resp.status_code == 200)

    def test_port_mapping(self):
        self.topo.dut1.get_rest_device().create_port_mapping(logic_if="WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 static mappings | grep 'TCP local 169.254.100.2:7777'")
        glx_assert(err == '')
        glx_assert("7777 vrf 0" in out)

        # check multi wans mapping to the same ip and port
        resp = self.topo.dut1.get_rest_device().create_port_mapping(logic_if="WAN2")
        glx_assert(resp.status_code == 201)
        self.topo.dut1.get_rest_device().delete_port_mapping(logic_if="WAN2")

        self.topo.dut1.get_rest_device().create_segment(1)
        self.topo.dut1.get_rest_device().update_port_mapping(logic_if="WAN1", segment=1, internal_addr="169.254.101.2")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 static mappings | grep 'TCP local 169.254.100.2:7777'")
        glx_assert(err == '')
        glx_assert("7777 vrf 0" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 static mappings | grep 'TCP local 169.254.101.2:7777'")
        glx_assert(err == '')
        glx_assert("7777 vrf 1" in out)
        # this should be failed with 500 because there are reference to the segment.
        result = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(result.status_code == 500)
        # delete
        self.topo.dut1.get_rest_device().delete_port_mapping(logic_if="WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show nat44 static mappings | grep 'TCP local 169.254.101.2:7777'")
        glx_assert(err == '')
        glx_assert("7777 vrf 1" not in out)
        result = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(result.status_code == 410)

    def test_update_config_get_all_keys(self):
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert("tunnel-id 1(0x00000001)" in out)

        data1={}
        data1["IgnoreNotSpecifiedTable"] = True
        table = {}
        table["Table"] = "EdgeRouteLabelFwdEntry"
        entry1 = {}
        entry1["RouteLabel"] = "0"
        entry1["IsDefault"] = True
        nexthopTunnel = {}
        nexthopTunnel["TunnelId"] = 1
        nexthopTunnel["TunnelPriority"] = 0
        nexthopTunnel["TunnelWeight"] = 0
        entry1["NexthopTunnels"] = []
        entry1["NexthopTunnels"].append(nexthopTunnel)
        table["Items"] = []
        table["Items"].append(entry1)
        data1["Tables"] = []
        data1["Tables"].append(table)
        
        resp = self.topo.dut1.get_rest_device().update_config_action(data1)
        glx_assert(resp.status_code == 200)

        data1={}
        data1["IgnoreNotSpecifiedTable"] = True
        table = {}
        table["Table"] = "EdgeRouteLabelFwdEntry"
        entry1 = {}
        entry1["RouteLabel"] = "0"
        entry1["IsDefault"] = True
        entry1["NexthopTunnels"] = []
        table["Items"] = []
        table["Items"].append(entry1)
        data1["Tables"] = []
        data1["Tables"].append(table)
        
        resp = self.topo.dut1.get_rest_device().update_config_action(data1)
        glx_assert(resp.status_code == 200)

        # self.topo.dut1.get_rest_device().update_glx_edge_route_label_fwd(route_label="0", tunnel_id1=None)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert("tunnel-id 1(0x00000001)" not in out)

    def test_addr_group(self):
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx addr-group")
        glx_assert(err == '')
        glx_assert("No glx addr group configured" in out)
        # create
        self.topo.dut1.get_rest_device().create_addr_group(group_name="addrgroup1", addr_with_prefix1="1.1.1.0/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx addr-group")
        glx_assert(err == '')
        glx_assert("addr group id: 1 configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 9218")
        glx_assert(err == '')
        glx_assert("1.1.1.0/24" in out)
        # update
        self.topo.dut1.get_rest_device().update_addr_group(group_name="addrgroup1", addr_with_prefix1="2.2.0.0/16")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 9218")
        glx_assert(err == '')
        glx_assert("1.1.1.0/24" not in out)
        glx_assert("2.2.0.0/16" in out)
        self.topo.dut1.get_rest_device().create_addr_group(group_name="addrgroup2", addr_with_prefix1="1.1.1.0/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx addr-group")
        glx_assert(err == '')
        glx_assert("addr group id: 2 configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 9219")
        glx_assert(err == '')
        glx_assert("1.1.1.0/24" in out)
        # delete
        self.topo.dut1.get_rest_device().delete_addr_group(group_name="addrgroup1")
        self.topo.dut1.get_rest_device().delete_addr_group(group_name="addrgroup2")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx addr-group")
        glx_assert(err == '')
        glx_assert("No glx addr group configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show ip fib table 9218")
        glx_assert(err == '')
        glx_assert("2.2.0.0/16" not in out)

    def test_port_group(self):
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx port-group")
        glx_assert(err == '')
        glx_assert("No glx port group configured" in out)
        # create
        self.topo.dut1.get_rest_device().create_port_group(group_name="portgroup1", protocol1="tcp", port_list1="7777,9990~9999")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx port-group | grep 'port group id: 1' -A 2")
        glx_assert(err == '')
        glx_assert("tcp ports: 7777" in out)
        glx_assert("tcp ports: 9990~9999" in out)
        # update
        self.topo.dut1.get_rest_device().update_port_group(group_name="portgroup1", protocol1="tcp", port_list1="9990~9995,9997~9999")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx port-group | grep 'port group id: 1' -A 2")
        glx_assert(err == '')
        glx_assert("tcp ports: 7777" not in out)
        glx_assert("tcp ports: 9990~9999" not in out)
        glx_assert("tcp ports: 9990~9995" in out)
        glx_assert("tcp ports: 9997~9999" in out)
        # restart fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart fwdmd")
        glx_assert(err == '')
        # 等待fwdmd重启完成（10s足够）
        time.sleep(10)
        resp = self.topo.dut1.get_rest_device().create_port_group(group_name="portgroup2", protocol1="tcp", port_list1="9999")
        glx_assert(resp.status_code == 500)
        self.topo.dut1.get_rest_device().create_port_group(group_name="portgroup2", protocol1="tcp", port_list1="3333")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx port-group | grep 'port group id: 2' -A 1")
        glx_assert(err == '')
        glx_assert("tcp ports: 3333" in out)
        # delete
        self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup1")
        self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup2")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx port-group")
        glx_assert(err == '')
        glx_assert("No glx port group configured" in out)

    def test_bizpol_with_obj_group(self):
        # 确保分配的group id为1
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx addr-group")
        glx_assert(err == '')
        glx_assert("No glx addr group configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx port-group")
        glx_assert(err == '')
        glx_assert("No glx port group configured" in out)
        # create group
        self.topo.dut1.get_rest_device().create_addr_group(group_name="addrgroup1", addr_with_prefix1="1.1.1.0/24")
        self.topo.dut1.get_rest_device().create_port_group(group_name="portgroup1", protocol1="tcp", port_list1="7777")
        # create bizpol
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_test", priority=1,
                                                       src_prefix="1.1.1.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=1, # tcp.
                                                       dst_addr_group="addrgroup1", dst_port_group="portgroup1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show bizpol bizpol | grep 1.1.1.0")
        glx_assert(err == "")
        glx_assert("dst-addr-group-id 1" in out)
        glx_assert("dst-port-group-id 1" in out)
        # update
        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol_test", priority=1,
                                                       src_prefix="0.0.0.0/0",
                                                       dst_prefix="1.1.1.0/24",
                                                       protocol=1, # tcp.
                                                       src_addr_group="addrgroup1", src_port_group="portgroup1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show bizpol bizpol | grep 1.1.1.0")
        glx_assert(err == "")
        glx_assert("src-addr-group-id 1" in out)
        glx_assert("src-port-group-id 1" in out)
        glx_assert("dst-addr-group-id 0" in out)
        glx_assert("dst-port-group-id 0" in out)
        # check relation
        resp = self.topo.dut1.get_rest_device().delete_addr_group(group_name="addrgroup1")
        glx_assert(resp.status_code == 500)
        resp = self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup1")
        glx_assert(resp.status_code == 500)
        # delete
        self.topo.dut1.get_rest_device().delete_bizpol("bizpol_test")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show bizpol bizpol | grep 1.1.1.0")
        glx_assert(err == "")
        glx_assert("src-addr-group-id 1" not in out)
        self.topo.dut1.get_rest_device().delete_addr_group(group_name="addrgroup1")
        self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup1")

    def test_firewall_with_obj_group(self):
        # 确保分配的group id为1
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show glx port-group")
        glx_assert(err == '')
        glx_assert("No glx port group configured" in out)
        # create group
        self.topo.dut1.get_rest_device().create_port_group(group_name="portgroup1", protocol1="tcp", port_list1="7777")
        # create firewall
        self.topo.dut1.get_rest_device().set_fire_wall_rule(rule_name="firewall_test", priority=1,
                                                            dest_address="1.1.1.0/24",
                                                            action="Deny",
                                                            protocol=1, # tcp.
                                                            dst_port_group="portgroup1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show acl-plugin acl | grep 1.1.1.0")
        glx_assert(err == "")
        glx_assert("dst-port-group-id 1" in out)
        # update
        self.topo.dut1.get_rest_device().update_fire_wall_rule(rule_name="firewall_test", priority=1,
                                                               dest_address="1.1.1.0/24",
                                                               action="Deny",
                                                               protocol=1, # tcp.
                                                               src_port_group="portgroup1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show acl-plugin acl | grep 1.1.1.0")
        glx_assert(err == "")
        glx_assert("src-port-group-id 1" in out)
        glx_assert("dst-port-group-id 0" in out)
        # check relation
        resp = self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup1")
        glx_assert(resp.status_code == 500)
        # delete
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("firewall_test")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("vppctl show acl-plugin acl | grep 1.1.1.0")
        glx_assert(err == "")
        glx_assert("src-port-group-id 1" not in out)
        self.topo.dut1.get_rest_device().delete_port_group(group_name="portgroup1")

    # probe
    def test_probe(self):

        # create
        self.topo.dut1.get_rest_device().create_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="CMD_PING",
                                                      dst_addr="1.1.1.1",
                                                      dst_port=1111,
                                                      interval=2,
                                                      timeout=1,
                                                      fail_threshold=5,
                                                      ok_threshold=10,
                                                      tag1="",
                                                      tag2="")
        # time.sleep(1)

        # check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        # print("out: [" + out + "]")
        glx_assert("1.1.1.1" in out)

        # update to icmp ping
        self.topo.dut1.get_rest_device().update_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="ICMP_PING",
                                                      dst_addr="2.2.2.2",
                                                      dst_port=1111,
                                                      interval=2,
                                                      timeout=1,
                                                      fail_threshold=5,
                                                      ok_threshold=10,
                                                      tag1="",
                                                      tag2="")
        # time.sleep(1)

        # check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        # print("out: [" + out + "]")
        glx_assert("2.2.2.2" in out)

        # update to dig dns
        self.topo.dut1.get_rest_device().update_probe(name="probe1",                                                             
                                                      type="WAN",
                                                      if_name="WAN1",
                                                      mode="DIG_DNS",
                                                      dst_addr="2.2.2.2",
                                                      dst_port=1111,
                                                      interval=2,
                                                      timeout=1,
                                                      fail_threshold=5,
                                                      ok_threshold=10,
                                                      tag1="",
                                                      tag2="")
        # time.sleep(1)

        # check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        # print("out: [" + out + "]")
        glx_assert("2.2.2.2" in out)

        # delete
        self.topo.dut1.get_rest_device().delete_probe(name="probe1")
        # time.sleep(1)
        
        # check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget Probe#probe1 DstAddr")
        out = out.rstrip()
        glx_assert(err == "")
        # print("out: [" + out + "]")
        glx_assert(out == "")

    def test_logical_interface_addr_switch_using_update_action(self):
        data={}
        data["IgnoreNotSpecifiedTable"] = True
        logIfTable = {}
        logIfTable["Table"] = "LogicalInterface"
        # 只处理WAN1
        logIfTable["Filters"] = "Filter[Name][eq]=WAN1"
        wan1 = {}
        wan1["Name"] = "WAN1"
        wan1["Segment"] = 0
        wan1["AddressingType"] = "STATIC"
        wan1["StaticIpAddrWithPrefix"] = "192.168.1.2/24"
        logIfTable["Items"] = []
        logIfTable["Items"].append(wan1)
        data["Tables"] = []
        data["Tables"].append(logIfTable)

        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        result = self.topo.dut1.get_rest_device().update_config_action(data)
        glx_assert(result.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" in out)
        # 不能出现dhcp client.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(wan1VppIf not in out)

        data2={}
        data2["IgnoreNotSpecifiedTable"] = True
        logIfTable = {}
        logIfTable["Table"] = "LogicalInterface"
        # 只处理WAN1
        logIfTable["Filters"] = "Filter[Name][eq]=WAN1"
        wan1 = {}
        wan1["Name"] = "WAN1"
        wan1["Segment"] = 0
        wan1["AddressingType"] = "DHCP"
        wan1["StaticIpAddrWithPrefix"] = ""
        logIfTable["Items"] = []
        logIfTable["Items"].append(wan1)
        data2["Tables"] = []
        data2["Tables"].append(logIfTable)

        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        result = self.topo.dut1.get_rest_device().update_config_action(data2)
        glx_assert(result.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.1.2/24" not in out)
        # 恢复为dhcp模式
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(wan1VppIf in out)

    # AccIpBinding, all out ips should be synchronized with logical interface additional ips
    def test_acc_ip_binding(self):
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.1/24") 
        acc_ip1 = "11.11.11.11"
        acc_ip2 = "11.11.11.12"
        out_ip1="111.111.111.111"
        out_ip2="111.111.111.112"
        out_ip3="111.111.111.113"
        out_ip4="111.111.111.114"

        # create
        self.topo.dut1.get_rest_device().create_acc_ip_binding(acc_ip=acc_ip1, out_ip1=out_ip1, out_ip2=out_ip2)
        self.topo.dut1.get_rest_device().set_logical_interface_additional_ips(name="WAN1", add_ip1=out_ip1, add_ip2=out_ip2)
        time.sleep(1)

        # check redis and vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli get AccIpBinding#{acc_ip1}OutIps")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(out_ip1 in out)
        glx_assert(out_ip2 in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show nat44 acc-ip-bind acc-ip {acc_ip1}")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(out_ip1 in out)
        glx_assert(out_ip2 in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr")
        glx_assert(err == '')
        glx_assert(out_ip1 in out)
        glx_assert(out_ip2 in out)

        # update
        self.topo.dut1.get_rest_device().update_acc_ip_binding(acc_ip=acc_ip1, out_ip1=out_ip3)
        self.topo.dut1.get_rest_device().set_logical_interface_additional_ips(name="WAN1", add_ip1=out_ip3)
        time.sleep(1)

        # check redis and vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli get AccIpBinding#{acc_ip1}OutIps")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(out_ip1 not in out)
        glx_assert(out_ip2 not in out)
        glx_assert(out_ip3 in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show nat44 acc-ip-bind acc-ip {acc_ip1}")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(out_ip1 not in out)
        glx_assert(out_ip2 not in out)
        glx_assert(out_ip3 in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr")
        glx_assert(err == '')
        glx_assert(out_ip1 not in out)
        glx_assert(out_ip2 not in out)
        glx_assert(out_ip3 in out)

        # add another
        self.topo.dut1.get_rest_device().create_acc_ip_binding(acc_ip=acc_ip2, out_ip1=out_ip4)
        self.topo.dut1.get_rest_device().set_logical_interface_additional_ips(name="WAN1", add_ip1=out_ip3, add_ip2=out_ip4)
        time.sleep(1)

        # check redis and vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli get AccIpBinding#{acc_ip2}OutIps")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(out_ip4 in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show nat44 acc-ip-bind")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(out_ip3 in out)
        glx_assert(out_ip4 in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr")
        glx_assert(err == '')
        glx_assert(out_ip3 in out)
        glx_assert(out_ip4 in out)

        # delete
        self.topo.dut1.get_rest_device().delete_acc_ip_binding(acc_ip=acc_ip1)
        self.topo.dut1.get_rest_device().delete_acc_ip_binding(acc_ip=acc_ip2)
        self.topo.dut1.get_rest_device().delete_logical_interface_additional_ips(name="WAN1")
        time.sleep(1)

        # check redis and vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli keys *AccIpBinding*")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert("AccIpBinding" not in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show nat44 acc-ip-bind")
        out = out.rstrip()
        glx_assert(err == "")
        glx_assert(acc_ip1 not in out)
        glx_assert(acc_ip2 not in out)
        glx_assert(out_ip3 not in out)
        glx_assert(out_ip4 not in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr")
        glx_assert(err == '')
        glx_assert(out_ip3 not in out)
        glx_assert(out_ip4 not in out)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")

    def test_global_arp_timeout(self):
        default_timeout="600"
        new_timeout="100"

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip neighbor-config | grep -C 1 ip4")
        glx_assert(err == '')
        # ipv4 default is 600s.
        glx_assert(default_timeout in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip neighbor-config | grep -C 1 ip6")
        glx_assert(err == '')
        # ipv6 nd default is 600s.
        glx_assert(default_timeout in out)

        # update to 100s.
        self.topo.dut1.get_rest_device().set_global_cfg(arp_timeout=100)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip neighbor-config | grep -C 1 ip4")
        glx_assert(err == '')
        glx_assert(new_timeout in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip neighbor-config | grep -C 1 ip6")
        glx_assert(err == '')
        glx_assert(new_timeout in out)

        # revert to default.
        self.topo.dut1.get_rest_device().set_global_cfg(arp_timeout=0)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip neighbor-config | grep -C 1 ip4")
        glx_assert(err == '')
        # ipv4 default is 600s.
        glx_assert(default_timeout in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip neighbor-config | grep -C 1 ip6")
        glx_assert(err == '')
        # ipv6 nd default is 600s.
        glx_assert(default_timeout in out)
    def test_global_node_id(self):
        high = random.getrandbits(32)
        low = random.getrandbits(32)
        node_id = (high << 32) | low
        resp = self.topo.dut1.get_rest_device().set_global_cfg(node_id=node_id)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx global")
        glx_assert(err == '')
        glx_assert(f"node_id {node_id}" in out)

    def test_get_segment_state(self):
        resp = self.topo.dut1.get_rest_device().get_segment_state()
        glx_assert(200 == resp.status_code)
        glx_assert("ctrl-ns" in str(resp.content))
        resp = self.topo.dut1.get_rest_device().create_segment(1)
        glx_assert(201 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().get_segment_state(id=1)
        glx_assert(200 == resp.status_code)
        glx_assert("ctrl-ns-seg-1" in str(resp.content))
        resp = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(410 == resp.status_code)

    def test_get_bridge_state(self):
        resp = self.topo.dut1.get_rest_device().get_bridge_state()
        glx_assert(200 == resp.status_code)
        glx_assert("br-default" in str(resp.content))
        resp = self.topo.dut1.get_rest_device().create_bridge(name="test" ,bvi_ip_w_prefix="192.168.89.1/24")
        glx_assert(201 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().get_bridge_state(name="test")
        glx_assert(200 == resp.status_code)
        glx_assert("br-test" in str(resp.content))
        resp = self.topo.dut1.get_rest_device().delete_bridge(name="test")
        glx_assert(410 == resp.status_code)
