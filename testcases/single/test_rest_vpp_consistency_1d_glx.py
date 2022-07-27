import unittest
import time

from topo.topo_1d import Topo1D

class TestRestVppConsistency1DGlx(unittest.TestCase):

    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_wan_object_ip_change(self):
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.1.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" in out)

        # 更改wan地址，验证变配成功
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.2.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        assert("192.168.1.1/24" not in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        assert("192.168.1.1/24" not in out)

        # 更改成dhcp模式
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        # no previous ip should be there.
        assert("192.168.2.1/24" not in out)
        assert("192.168.1.1/24" not in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        # BUG: https://github.com/galaxnet-cc/fwdmd/issues/24
        #assert("192.168.2.1/24" not in out)
        #assert("192.168.1.1/24" not in out)

    def test_glx_link_config(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 1" not in out)

    def test_glx_link_block_wan_mode(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == "")
        assert(f"link-id 1" in out)
        # try to change wan mode to pppoe is not allowed.
        result = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "test")
        # this should be failed with 500.
        assert(result.status_code == 500)
        # cleanup
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)

    def test_glx_tunnel_config(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 1" in out)
        # delete the link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 1" not in out)
        # verify link members count changed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        # delete the tunnel
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)

    def test_glx_tunnel_multi_link_config(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 1" in out)
        # add link2
        self.topo.dut1.get_rest_device().create_glx_link(link_id=2, wan_name="WAN2", tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 2" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 2" in out)
        # delete the link 1
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 1" not in out)
        # verify link members count changed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 1" in out)
        # delete the link 2
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        assert(err == '')
        assert(f"link-id 2" not in out)
        # verify link members count changed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        # delete the tunnel
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)

    def test_glx_single_route_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        # add the route.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1" in out)
        # try to delete the tunnel and failed.
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        assert(result.status_code == 500)
        # delete the route.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1 tunnel-priority 100" not in out)
        assert(f"1.1.1.1/32" not in out)
        # delete the tunnel and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)

    def test_glx_multi_route_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        # add the route 1.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1" in out)
        # add the route 2.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="2.2.2.2/32", route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 2.2.2.2")
        assert(err == '')
        assert(f"tunnel-id 1" in out)
        # try to delete the tunnel and failed.
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        assert(result.status_code == 500)
        # delete the route 1.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1 tunnel-priority 100" not in out)
        assert(f"1.1.1.1/32" not in out)
        # delete the route 2.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="2.2.2.2/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 2.2.2.2")
        assert(err == '')
        assert(f"tunnel-id 1 tunnel-priority 100" not in out)
        assert(f"2.2.2.2/32" not in out)
        # delete the tunnel and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)

    def test_glx_multi_route_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        # add the route 1.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1" in out)
        # add the route 2.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="2.2.2.2/32", route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 2.2.2.2")
        assert(err == '')
        assert(f"tunnel-id 1" in out)
        # try to delete the tunnel and failed.
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        assert(result.status_code == 500)
        # delete the route 1.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1 tunnel-priority 100" not in out)
        assert(f"1.1.1.1/32" not in out)
        # delete the route 2.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="2.2.2.2/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 2.2.2.2")
        assert(err == '')
        assert(f"tunnel-id 1 tunnel-priority 100" not in out)
        assert(f"2.2.2.2/32" not in out)
        # delete the tunnel and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)

    def test_glx_route_multi_tunnel_config(self):
        # prepare the tunnel 1 & 2
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 2 members 0" in out)
        # add the route.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234",
                                                           tunnel_id1=1, tunnel_id2=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1" in out)
        assert(f"tunnel-id 2" in out)
        # default in load balance mode.
        # BUG: typo (blance->balance), change to is_failover 0.
        # assert(f"is_loadblance: 1" in out)
        assert(f"is_failover: 0" in out)
        # try to delete the tunnel and failed.
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        assert(result.status_code == 500)
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        assert(result.status_code == 500)
        # delete the route 1.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1 tunnel-priority 100" not in out)
        assert(f"tunnel-id 2 tunnel-priority 100" not in out)
        assert(f"1.1.1.1/32" not in out)
        # delete the tunnels and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 2 members 0" not in out)

    def test_glx_route_multi_tunnel_failover_config(self):
        # prepare the tunnel 1 & 2
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 2 members 0" in out)
        # add the route.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234",
                                                           tunnel_id1=1, tunnel_id2=2, tunnel1_priority=100, tunnel2_priority=50)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1" in out)
        assert(f"tunnel-id 2" in out)
        assert(f"is_failover: 1" in out)
        # try to delete the tunnel and failed.
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        assert(result.status_code == 500)
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        assert(result.status_code == 500)
        # delete the route 1.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        assert(err == '')
        assert(f"tunnel-id 1 tunnel-priority 100" not in out)
        assert(f"tunnel-id 2 tunnel-priority 100" not in out)
        assert(f"1.1.1.1/32" not in out)
        # delete the tunnels and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 2 members 0" not in out)

    def test_glx_route_label_fwd_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        # add the route label fwd entry.
        self.topo.dut1.get_rest_device().create_glx_route_label_fwd(route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label-fwd")
        assert(err == '')
        assert('0x1234' in out)
        #assert(f"is_failover: 1" in out)
        # try to delete the tunnel and failed.
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        assert(result.status_code == 500)
        # delete the route label fwd entry.
        self.topo.dut1.get_rest_device().delete_glx_route_label_fwd(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label-fwd")
        assert(err == '')
        assert('0x1234' not in out)
        # delete the tunnels and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)

    def test_glx_route_label_policy_type_tunnel_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" in out)
        # add the route label policy entry.
        self.topo.dut1.get_rest_device().create_glx_route_label_policy_type_tunnel(route_label="0x1234", tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        assert(err == '')
        assert('0x1234' in out)
        #assert(f"is_failover: 1" in out)
        # try to delete the tunnel and failed.
        result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        assert(result.status_code == 500)
        # delete the route label policy entry.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_tunnel(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        assert(err == '')
        assert('0x1234' not in out)
        # delete the tunnels and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        assert(err == '')
        assert(f"tunnel-id 1 members 0" not in out)

    def test_glx_route_label_policy_type_table_config(self):
        # add the route label policy entry.
        self.topo.dut1.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        assert(err == '')
        assert('0x1234' in out)
        # delete the route label policy entry.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        assert(err == '')
        assert('0x1234' not in out)

    def test_glx_bizpol_nat_config(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol")
        assert(err == '')
        assert('192.168.88.0/24' in out)
        # now no interface needed due to auto steering feature support.
        assert(f'nat' in out)
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sit")

    def test_glx_bizpol_nat_config_w_steering(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.89.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=True,
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol")
        assert(err == '')
        assert('192.168.89.0/24' in out)
        assert('nat' in out)
        assert('steering' in out)
        # get the wan1 if index.
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # use double curly to insert a curly symbol into the f-string, python3 is cool:)
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan1VppIf} | grep {wan1VppIf} | awk '{{print $2}}'")
        # remove the possible extra newline.
        ifindex = ifindex.rstrip()
        assert(f'[nat]  [link-steering type 1 mode 1 steering-sw-if-index {ifindex}]' in out)
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sit")

    def test_glx_bizpol_nat_pppoe_mode_switch(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.90.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol")
        assert(err == '')
        assert('192.168.90.0/24' in out)
        # now interface is needed now.
        assert(f'nat' in out)
        # try to change wan mode to pppoe is not allowed.
        result = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "test")
        # this should be failed with 500.
        assert(result.status_code == 500)
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sit")

    def test_glx_bizpol_tunnel_config_w_steering(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.89.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=False,
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol")
        assert(err == '')
        assert('192.168.89.0/24' in out)
        assert('nat' not in out)
        assert('steering' in out)
        # get the wan1 if index.
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # use double curly to insert a curly symbol into the f-string, python3 is cool:)
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan1VppIf} | grep {wan1VppIf} | awk '{{print $2}}'")
        # remove the possible extra newline.
        ifindex = ifindex.rstrip()
        assert(f'[link-steering type 1 mode 1 steering-sw-if-index {ifindex}]' in out)

        # update the bizpol to WAN2.
        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.89.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=False,
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol")
        assert(err == '')
        assert('192.168.89.0/24' in out)
        assert('nat' not in out)
        assert('steering' in out)

        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        # use double curly to insert a curly symbol into the f-string, python3 is cool:)
        wan2ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan2VppIf} | grep {wan2VppIf} | awk '{{print $2}}'")
        # remove the possible extra newline.
        wan2ifindex = wan2ifindex.rstrip()
        assert(f'[link-steering type 1 mode 1 steering-sw-if-index {ifindex}]' not in out)
        assert(f'[link-steering type 1 mode 1 steering-sw-if-index {wan2ifindex}]' in out)

        # delete the bizpol.
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sit")

    def test_glx_overlay_traffic_limit(self):
        # only tx is limited.
        self.topo.dut1.get_rest_device().create_overlay_traffic_limit(10000, 4294967295, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        txName = txName.rstrip()
        assert(err == '')
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        txIndex = txIndex.rstrip()
        assert(err == '')
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep tx | awk '{{print $5}}'")
        assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        assert(glxTxIndex == vppTxIndex)

        # update tx.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 4294967295, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        assert(err == '')
        txName = txName.rstrip()
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        assert(err == '')
        txIndex = txIndex.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep tx | awk '{{print $5}}'")
        assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        assert(glxTxIndex == vppTxIndex)

        # enable rx.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 30000, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        assert(err == '')
        txName = txName.rstrip()
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        assert(err == '')
        txIndex = txIndex.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep tx | awk '{{print $5}}'")
        assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        assert(glxTxIndex == vppTxIndex)
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        assert(err == '')
        rxName = rxName.rstrip()
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        assert(err == '')
        rxIndex = rxIndex.rstrip()
        # verify vpp and glx.
        vppRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {rxName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppRxIndex = vppRxIndex.rstrip()
        assert(vppRxIndex == rxIndex)
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep rx | awk '{{print $5}}'")
        assert(err == '')
        glxRxIndex = glxRxIndex.rstrip()
        assert(glxRxIndex == vppRxIndex)
        # should not same.
        assert(glxRxIndex != glxTxIndex)

        # enable combined.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 30000, True)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        txName = txName.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep tx | awk '{{print $5}}'")
        assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        assert(glxTxIndex == vppTxIndex)
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        assert(err == '')
        rxName = rxName.rstrip()
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        assert(err == '')
        rxIndex = rxIndex.rstrip()
        # verify vpp and glx.
        vppRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {rxName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppRxIndex = vppRxIndex.rstrip()
        assert(vppRxIndex == rxIndex)
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep rx | awk '{{print $5}}'")
        assert(err == '')
        glxRxIndex = glxRxIndex.rstrip()
        assert(glxRxIndex == vppRxIndex)
        # both vpp glx rx and tx should be same.
        assert(vppRxIndex == vppTxIndex)
        assert(glxRxIndex == glxTxIndex)

        # disable combined.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 30000, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        txName = txName.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep tx | awk '{{print $5}}'")
        assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        assert(glxTxIndex == vppTxIndex)
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        assert(err == '')
        rxName = rxName.rstrip()
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        assert(err == '')
        rxIndex = rxIndex.rstrip()
        # verify vpp and glx.
        vppRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {rxName} | grep Template | awk '{{print $3}}'")
        assert(err == '')
        vppRxIndex = vppRxIndex.rstrip()
        assert(vppRxIndex == rxIndex)
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep rx | awk '{{print $5}}'")
        assert(err == '')
        glxRxIndex = glxRxIndex.rstrip()
        assert(glxRxIndex == vppRxIndex)
        # both vpp glx rx and tx should not be same.
        assert(vppRxIndex != vppTxIndex)
        assert(glxRxIndex != glxTxIndex)

        # delete the limit.
        self.topo.dut1.get_rest_device().delete_overlay_traffic_limit()
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep tx | awk '{{print $5}}'")
        glxTxIndex = glxTxIndex.rstrip()
        assert(glxTxIndex == "4294967295")
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep rx | awk '{{print $5}}'")
        glxRxIndex = glxRxIndex.rstrip()
        assert(glxRxIndex == "4294967295")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer pools")
        # policer should be be remained.
        assert("policers=0" in out)
        # redis should also be empty.
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        assert(err == '')
        txName = txName.rstrip()
        assert(txName == "")
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        assert(err == '')
        txIndex = txIndex.rstrip()
        assert(txIndex == "4294967295")
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        assert(err == '')
        rxName = rxName.rstrip()
        assert(rxName == "")
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        assert(err == '')
        rxIndex = rxIndex.rstrip()
        assert(rxIndex == "4294967295")

if __name__ == '__main__':
    unittest.main()
