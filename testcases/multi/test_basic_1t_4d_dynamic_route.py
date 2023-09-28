import unittest
import time

from lib.util import glx_assert
from topo.topo_1t_4d import Topo1T4D

SKIP_SETUP = False
SKIP_TEARDOWN = False


class TestBasic1T4DDynamicRoute(unittest.TestCase):
    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return
        # setup ospf interface on dut1
        # ospf setting on dut1
        # setup ospf interface on dut1
        # setup logical interface on  dut1
        # 1、WAN1 change to UNSPEC
        # 2、WAN1 disable overlay
        # 3、WAN1 set static ip
        # 4、create ospf
        mtu = 1500
        self.topo.dut1.get_rest_device().set_logical_interface_unspec("WAN1")
        result1 = self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu("default", "192.168.88.1/24", mtu=mtu)
        self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN1", False)
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        areas = [
            {"AreaId": 1}
        ]
        self.topo.dut1.get_rest_device().create_ospf_setting(areas=areas)
        self.topo.dut1.get_rest_device().create_ospf_interface("WAN1", 1)

        # config ospf on dut2
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN1")
        result2 = self.topo.dut2.get_rest_device().update_bridge_ip_or_mtu("default", "192.168.89.1/24", mtu=mtu)
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        self.topo.dut2.get_rest_device().create_ospf_setting(areas=areas)
        self.topo.dut2.get_rest_device().create_ospf_interface("WAN1", 1)

    def tearDown(self):

        if SKIP_TEARDOWN:
            return
        mtu = 1500
        self.topo.dut2.get_rest_device().delete_ospf_interface("WAN1", 1)
        self.topo.dut2.get_rest_device().delete_ospf_setting()
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().update_bridge_ip_or_mtu("default", "192.168.88.1/24", mtu=mtu)

        self.topo.dut1.get_rest_device().delete_ospf_interface("WAN1", 1)
        self.topo.dut1.get_rest_device().delete_ospf_setting()
        self.topo.dut1.get_rest_device().set_logical_interface_unspec("WAN1")
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN1", True)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut1.get_rest_device().update_bridge_ip_or_mtu("default", "192.168.88.1/24", mtu=mtu)

    # testcases
    def test_dynamic_route(self):
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "show ip ospf interface" -c "clear ip ospf process"')
        glx_assert (err == '')

        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "show ip ospf interface" -c "clear ip ospf process"')
        glx_assert (err == '')

        # fwdmd store route message to redis db and distribute route message to vpp

        # add route
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.8/32 Null0"'
        )
        glx_assert (err == '')
        # sleep enough to wait ospf resync.
        time.sleep(120)
        segment, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Segment"'
        )
        glx_assert (err == '')
        segment = segment.rstrip()
        glx_assert (segment == '0')
        dst, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Dst"'
        )
        glx_assert (err == '')
        dst = dst.rstrip()
        glx_assert (dst == '8.8.8.8/32')
        gw, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Gw" '
        )
        glx_assert (err == '')
        gw = gw.rstrip()
        glx_assert (gw == '192.168.1.2')
        protocol, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Protocol" '
        )
        protocol = protocol.rstrip()
        glx_assert (err == '')
        glx_assert (protocol == '188')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table 0 8.8.8.8'
        )
        glx_assert (err == '')
        glx_assert ('8.8.8.8' in out)
        glx_assert ('fpm-route' in out)
        glx_assert('API' not in out)
        # delete route
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "no ip route 8.8.8.8/32 Null0"'
        )
        glx_assert (err == '')
        time.sleep(5)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.8/32"'
        )
        out = out.rstrip()
        glx_assert (err == '')
        glx_assert (out == '')

        # update route message in redis db and update route message to vpp when fwdmd restart,flushing the expired redis data
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.8/32 Null0"'
        )
        glx_assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.9/32 Null0"'
        )
        glx_assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.10/32 Null0"'
        )
        glx_assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.11/32 Null0"'
        )
        glx_assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.12/32 Null0"'
        )
        glx_assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.13/32 Null0"'
        )
        glx_assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.14/32 Null0"'
        )
        glx_assert (err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'systemctl stop fwdmd.service'
        )
        glx_assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "no ip route 8.8.8.8/32 Null0"'
        )
        time.sleep(10)
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'systemctl restart fwdmd.service'
        )
        glx_assert (err == '')
        time.sleep(105)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.8/32"'
        )
        glx_assert (err == '')
        glx_assert (out == '')

        # when the vpp restarts,read the redis db and redistribute to the vpp
        _,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'systemctl restart vpp'
        )
        glx_assert(err == '')
        time.sleep(30)
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.9/32"'
        )
        segment1, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Segment"'
        )
        segment1 = segment1.rstrip()
        glx_assert (err == '')
        glx_assert (segment1 == '0')
        dst, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Dst"'
        )
        dst = dst.rstrip()
        glx_assert (err == '')
        glx_assert (dst == '8.8.8.9/32')

        gw, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Gw" '
        )
        gw = gw.rstrip()
        glx_assert (err == '')
        glx_assert (gw == '192.168.1.2')
        protocol, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Protocol" '
        )
        glx_assert (err == '')
        glx_assert (protocol == '188')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table 0 8.8.8.9/32'
        )
        glx_assert (err == '')
        glx_assert ('8.8.8.9' in out)
        glx_assert ('fpm-route' in out)
        glx_assert('API' not in out)
        # when the ospf is disabled,flush the ospf routes in redis and vpp
        _,err = self.topo.dut2.get_rest_device().delete_ospf_interface("WAN1",1)
        _,err = self.topo.dut2.get_rest_device().delete_ospf_setting()
        time.sleep(60)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.9/32"'
        )
        glx_assert (err == '')
        glx_assert (out == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table 0 8.8.8.9'
        )
        out = out.rstrip()
        glx_assert (err == '')
        glx_assert ('8.8.8.9' not in out)
