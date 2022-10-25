import unittest
import time

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
        # TODO:
        # 1、WAN1 change to UNSPEC
        # 2、WAN1 disable overlay
        # 3、WAN1 set static ip
        # 4、create ospf
        self.topo.dut1.get_rest_device().set_logical_interface_unspec("WAN1")
        result1 = self.topo.dut1.get_rest_device().update_bridge_ip("default", "192.168.88.1/24")
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
        result2 = self.topo.dut2.get_rest_device().update_bridge_ip("default", "192.168.89.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", False)
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.2/24")
        self.topo.dut2.get_rest_device().create_ospf_setting(areas=areas)
        self.topo.dut2.get_rest_device().create_ospf_interface("WAN1", 1)

    def tearDown(self):

        if SKIP_TEARDOWN:
            return
        self.topo.dut2.get_rest_device().delete_ospf_interface("WAN1", 1)
        self.topo.dut2.get_rest_device().delete_ospf_setting()
        self.topo.dut2.get_rest_device().set_logical_interface_unspec("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_overlay_enable("WAN1", True)
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().update_bridge_ip("default", "192.168.88.1/24")

        self.topo.dut1.get_rest_device().delete_ospf_interface("WAN1", 1)
        self.topo.dut1.get_rest_device().delete_ospf_setting()
        self.topo.dut1.get_rest_device().set_logical_interface_unspec("WAN1")
        self.topo.dut1.get_rest_device().set_logical_interface_nat_direct("WAN1", True)
        self.topo.dut1.get_rest_device().set_logical_interface_overlay_enable("WAN1", True)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut1.get_rest_device().update_bridge_ip("default", "192.168.88.1/24")

    # testcases
    def test_dynamic_route(self):
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "show ip ospf interface" -c "clear ip ospf process"')
        assert (err == '')

        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "show ip ospf interface" -c "clear ip ospf process"')
        assert (err == '')

        # fwdmd store route message to redis db and distribute route message to vpp

        # add route
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.8/32 Null0"'
        )
        assert (err == '')
        # sleep enough to wait ospf resync.
        time.sleep(120)
        segment, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Segment"'
        )
        assert (err == '')
        segment = segment.rstrip()
        assert (segment == '0')
        dst, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Dst"'
        )
        assert (err == '')
        dst = dst.rstrip()
        assert (dst == '8.8.8.8/32')
        gw, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Gw" '
        )
        assert (err == '')
        gw = gw.rstrip()
        assert (gw == '192.168.1.2')
        protocol, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.8/32" "Protocol" '
        )
        protocol = protocol.rstrip()
        assert (err == '')
        assert (protocol == '11')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table 0 8.8.8.8'
        )
        assert (err == '')
        assert ('8.8.8.8' in out)
        # delete route
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "no ip route 8.8.8.8/32 Null0"'
        )
        assert (err == '')
        time.sleep(5)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.8/32"'
        )
        out = out.rstrip()
        assert (err == '')
        assert (out == '')

        # update route message in redis db and update route message to vpp when fwdmd restart,flushing the expired redis data
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.8/32 Null0"'
        )
        assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.9/32 Null0"'
        )
        assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.10/32 Null0"'
        )
        assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.11/32 Null0"'
        )
        assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.12/32 Null0"'
        )
        assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.13/32 Null0"'
        )
        assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "ip route 8.8.8.14/32 Null0"'
        )
        assert (err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'systemctl stop fwdmd.service'
        )
        assert (err == '')
        _, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vtysh -N ctrl-ns -c "config" -c "router ospf" -c "redistribute static" -c "no ip route 8.8.8.8/32 Null0"'
        )
        time.sleep(10)
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'systemctl restart fwdmd.service'
        )
        assert (err == '')
        time.sleep(105)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.8/32"'
        )
        assert (err == '')
        assert (out == '')

        # when the vpp restarts,read the redis db and redistribute to the vpp
        _,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'systemctl restart vpp'
        )
        assert(err == '')
        time.sleep(30)
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.9/32"'
        )
        segment1, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Segment"'
        )
        segment1 = segment1.rstrip()
        assert (err == '')
        assert (segment1 == '0')
        dst, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Dst"'
        )
        dst = dst.rstrip()
        assert (err == '')
        assert (dst == '8.8.8.9/32')
        gw, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Gw" '
        )
        gw = gw.rstrip()
        assert (err == '')
        assert (gw == '192.168.1.2')
        protocol, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hget "ZebraRouteContext#0#8.8.8.9/32" "Protocol" '
        )
        assert (err == '')
        assert (protocol == '11')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table 0 8.8.8.9/32'
        )
        assert (err == '')
        assert ('8.8.8.9' in out)

        # when the ospf is disabled,flush the ospf routes in redis and vpp
        _,err = self.topo.dut2.get_rest_device().delete_ospf_interface("WAN1",1)
        _,err = self.topo.dut2.get_rest_device().delete_ospf_setting()
        time.sleep(10)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'redis-cli hgetall "ZebraRouteContext#0#8.8.8.9/32"'
        )
        assert (err == '')
        assert (out == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show ip fib table 0 8.8.8.9'
        )
        out = out.rstrip()
        assert (err == '')
        assert ('8.8.8.9' not in out)
