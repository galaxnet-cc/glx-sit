import unittest
import time

from lib.util import glx_assert
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
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.1.1/24" in out)

        # 更改wan地址，验证变配成功
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.2.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr {wan1VppIf}")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        glx_assert("192.168.1.1/24" not in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        glx_assert("192.168.2.1/24" in out)
        glx_assert("192.168.1.1/24" not in out)

        # 更改成dhcp模式
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check vpp
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show dhcp client")
        glx_assert(err == '')
        glx_assert(f'{wan1VppIf}' in out)
        # no previous ip should be there.
        glx_assert("192.168.2.1/24" not in out)
        glx_assert("192.168.1.1/24" not in out)
        # check ctrl ns
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"ip netns exec ctrl-ns-wan-WAN1 ip addr show WAN1")
        glx_assert(err == '')
        # BUG: https://github.com/galaxnet-cc/fwdmd/issues/24
        #glx_assert("192.168.2.1/24" not in out)
        #glx_assert("192.168.1.1/24" not in out)

    def test_glx_link_config(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)

    def test_glx_link_block_wan_mode(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == "")
        glx_assert(f"link-id 1" in out)
        # try to change wan mode to pppoe is not allowed.
        result = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "test")
        # this should be failed with 500.
        glx_assert(result.status_code == 500)
        # cleanup
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)

    def test_glx_link_transport_modify(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        # 更新wan接口
        self.topo.dut1.get_rest_device().update_glx_link_wan(link_id=1, wan_name="WAN2")
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan2VppIf} | grep {wan2VppIf} | awk '{{print $2}}'")
        # remove the possible extra newline.
        ifindex = ifindex.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')

        glx_assert(f"wan-sw-if-index {ifindex}" in out)
        # 更新remote ip
        self.topo.dut1.get_rest_device().update_glx_link_remote_ip(link_id=1, remote_ip="192.168.44.1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"remote-ip 192.168.44.1" in out)

        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)

    def test_glx_tunnel_config(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 1" in out)
        # delete the link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)
        # verify link members count changed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        # delete the tunnel
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)

        # verify mld enable and fec enable
        resp = self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1, mld_enable=True, fec_enable=True)
        glx_assert(resp.status_code == 201)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert("state: init" in out)
        glx_assert("mld-enable: 1" in out)
        glx_assert("cfg-ver: 1" in out)
        glx_assert("fec-enable: 1" in out)
        # check configuration version
        # verify passive mld enable
        resp = self.topo.dut1.get_rest_device().update_glx_tunnel(tunnel_id=1, mld_enable=True, fec_enable=True, passive_mld_enable=True, passive_fec_enable=True)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert("passive-fec-enable: 1" in out)
        glx_assert("passive-mld-enable: 1" in out)
        # check configuration version
        glx_assert("cfg-ver: 2" in out)
        
        resp = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        glx_assert(resp.status_code == 410)



    def test_glx_tunnel_multi_link_config(self):
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 1" in out)
        # add link2
        self.topo.dut1.get_rest_device().create_glx_link(link_id=2, wan_name="WAN2", tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 2" in out)
        # delete the link 1
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)
        # verify link members count changed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 1" in out)
        # delete the link 2
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" not in out)
        # verify link members count changed.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        # delete the tunnel
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)

    def test_glx_single_route_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        # add the route.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        glx_assert(err == '')
        glx_assert(f"0x0000001234" in out)
        # 0824: the route is not associated with tunnel, so tunnel can be deleted.
        # try to delete the tunnel and failed.
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        #glx_assert(result.status_code == 500)
        # delete the route.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        glx_assert(err == '')
        glx_assert(f"1.1.1.1/32" not in out)
        # delete the tunnel and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)

    def test_glx_multi_route_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        # add the route 1.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        glx_assert(err == '')
        glx_assert(f"0x0000001234" in out)
        # add the route 2.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="2.2.2.2/32", route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 2.2.2.2")
        glx_assert(err == '')
        glx_assert(f"0x0000001234" in out)
        # 0824: the route is not associated with tunnel, so tunnel can be deleted.
        # try to delete the tunnel and failed.
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        #glx_assert(result.status_code == 500)
        # delete the route 1.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        glx_assert(err == '')
        glx_assert(f"1.1.1.1/32" not in out)
        # delete the route 2.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="2.2.2.2/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 2.2.2.2")
        glx_assert(err == '')
        glx_assert(f"2.2.2.2/32" not in out)
        # delete the tunnel and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)

    def test_glx_route_multi_tunnel_config(self):
        # prepare the tunnel 1 & 2
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2(0x00000002) members 0" in out)
        # add the route.
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        glx_assert(err == '')
        glx_assert(f"0x0000001234" in out)
        # 0824: the route is not associated with tunnel, so tunnel can be deleted.
        # try to delete the tunnel and failed.
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        #glx_assert(result.status_code == 500)
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        #glx_assert(result.status_code == 500)
        # delete the route 1.
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 0 1.1.1.1")
        glx_assert(err == '')
        glx_assert(f"1.1.1.1/32" not in out)
        # delete the tunnels and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2(0x00000002) members 0" not in out)

    def test_glx_route_label_fwd_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        # add the route label fwd entry.
        self.topo.dut1.get_rest_device().create_glx_route_label_fwd(route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label-fwd")
        glx_assert(err == '')
        glx_assert('0x0000001234' in out)
        #glx_assert(f"is_failover: 1" in out)
        # try to delete the tunnel and failed.
        # 220926: tunnel因允许passive/active创建，不再报错，改为判断不为500，这里有点违背了http RESTful逻辑。
        # 这里会导致对应的fwdmd对象已经删除，但底层如果有多个，其实会对应于fwdmd的另外一个对象，该对象也需要
        # 删除，比如active tunnel & passive tunnel共存的情况，从语义上来说也是合理的。
        # 本质上，这是控制面不共享对象，数据面对象对象的一个典型示例。
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        #glx_assert(result.status_code == 500)
        # delete the route label fwd entry.
        self.topo.dut1.get_rest_device().delete_glx_route_label_fwd(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label-fwd")
        glx_assert(err == '')
        glx_assert('0x0000001234' not in out)
        # delete the tunnels and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)

    @unittest.skip("20230820: type 1 tunnel will be installed in vpp automatically, api is ignored...")
    def test_glx_route_label_policy_type_tunnel_config(self):
        # prepare the tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        # add the route label policy entry.
        self.topo.dut1.get_rest_device().create_glx_route_label_policy_type_tunnel(route_label="0x1234", tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        glx_assert(err == '')
        glx_assert('0x0000001234' in out)
        #glx_assert(f"is_failover: 1" in out)
        # try to delete the tunnel and failed.
        # 220926: tunnel因允许passive/active创建，不再报错，改为判断不为500，这里有点违背了http RESTful逻辑。
        # 这里会导致对应的fwdmd对象已经删除，但底层如果有多个，其实会对应于fwdmd的另外一个对象，该对象也需要
        # 删除，比如active tunnel & passive tunnel共存的情况，从语义上来说也是合理的。
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        #glx_assert(result.status_code == 500)
        # delete the route label policy entry.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_tunnel(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        glx_assert(err == '')
        glx_assert('0x0000001234' not in out)
        # delete the tunnels and now it should ok.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)

    def test_glx_route_label_policy_type_table_config(self):
        # add the route label policy entry.
        self.topo.dut1.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        glx_assert(err == '')
        glx_assert('0x0000001234' in out)
        # delete the route label policy entry.
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx route-label")
        glx_assert(err == '')
        glx_assert('0x0000001234' not in out)

    def test_glx_bizpol_nat_config(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=True)
        # XXX: should exclude ns default exit if nat rule.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep -v seg_0_exit_if_nat_pol | grep -v 169.254")
        glx_assert(err == '')
        glx_assert('192.168.88.0/24' in out)
        # now no interface needed due to auto steering feature support.
        glx_assert(f'[nat]' in out)
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sit")

    def test_glx_bizpol_order(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sit", priority=100,
                                                       src_prefix="0.0.0.0/0",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       overlay_enable=True,
                                                       acc_enable=True,
                                                       route_label="0x1")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol interface")
        glx_assert(err == '')
        glx_assert('input bizpol(s): 0, 1' in out)

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
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep -v seg_0_exit_if_nat_pol | grep -v 169.254")
        glx_assert(err == '')
        glx_assert('192.168.89.0/24' in out)
        glx_assert('[nat]' in out)
        glx_assert('steering' in out)
        # get the wan1 if index.
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # use double curly to insert a curly symbol into the f-string, python3 is cool:)
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan1VppIf} | grep {wan1VppIf} | awk '{{print $2}}'")
        # remove the possible extra newline.
        ifindex = ifindex.rstrip()
        glx_assert(f'[nat]  [link-steering type 1 mode 1 steering-sw-if-index {ifindex}]' in out)
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sit")

    def test_glx_bizpol_nat_pppoe_mode_switch(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.90.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep -v seg_0_exit_if_nat_pol | grep -v 169.254")
        glx_assert(err == '')
        glx_assert('192.168.90.0/24' in out)
        # now interface is needed now.
        glx_assert(f'[nat]' in out)
        # try to change wan mode to pppoe is not allowed.
        result = self.topo.dut1.get_rest_device().set_logical_interface_pppoe("WAN1", "test", "test")
        # this should be success with 200.
        glx_assert(result.status_code == 200)
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
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
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep -v seg_0_exit_if_nat_pol | grep -v 169.254")
        glx_assert(err == '')
        glx_assert('192.168.89.0/24' in out)
        glx_assert('[nat]' not in out)
        glx_assert('steering' in out)
        # get the wan1 if index.
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # use double curly to insert a curly symbol into the f-string, python3 is cool:)
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan1VppIf} | grep {wan1VppIf} | awk '{{print $2}}'")
        # remove the possible extra newline.
        ifindex = ifindex.rstrip()
        glx_assert(f'[link-steering type 1 mode 1 steering-sw-if-index {ifindex}]' in out)

        # update the bizpol to WAN2.
        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol_sit", priority=1,
                                                       src_prefix="192.168.89.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=False,
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep -v seg_0_exit_if_nat_pol | grep -v 169.254")
        glx_assert(err == '')
        glx_assert('192.168.89.0/24' in out)
        glx_assert('[nat]' not in out)
        glx_assert('steering' in out)

        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        # use double curly to insert a curly symbol into the f-string, python3 is cool:)
        wan2ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {wan2VppIf} | grep {wan2VppIf} | awk '{{print $2}}'")
        # remove the possible extra newline.
        wan2ifindex = wan2ifindex.rstrip()
        glx_assert(f'[link-steering type 1 mode 1 steering-sw-if-index {ifindex}]' not in out)
        glx_assert(f'[link-steering type 1 mode 1 steering-sw-if-index {wan2ifindex}]' in out)

        # delete the bizpol.
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sit")

    def test_glx_overlay_traffic_limit(self):
        # only tx is limited.
        self.topo.dut1.get_rest_device().create_overlay_traffic_limit(10000, 4294967295, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        txName = txName.rstrip()
        glx_assert(err == '')
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        txIndex = txIndex.rstrip()
        glx_assert(err == '')
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep index | awk '{{print $4}}' | cut -d':' -f1")
        glx_assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        glx_assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'tx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        glx_assert(glxTxIndex == vppTxIndex)

        # update tx.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 4294967295, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        glx_assert(err == '')
        txName = txName.rstrip()
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        glx_assert(err == '')
        txIndex = txIndex.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep index | awk '{{print $4}}' | cut -d':' -f1 ")
        glx_assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        glx_assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'tx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        glx_assert(glxTxIndex == vppTxIndex)

        # enable rx.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 30000, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        glx_assert(err == '')
        txName = txName.rstrip()
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        glx_assert(err == '')
        txIndex = txIndex.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep index | awk '{{print $4}}' | cut -d':' -f1 ")
        glx_assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        glx_assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'tx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        glx_assert(glxTxIndex == vppTxIndex)
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        glx_assert(err == '')
        rxName = rxName.rstrip()
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        glx_assert(err == '')
        rxIndex = rxIndex.rstrip()
        # verify vpp and glx.
        vppRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {rxName} | grep index | awk '{{print $4}}' | cut -d':' -f1 ")
        glx_assert(err == '')
        vppRxIndex = vppRxIndex.rstrip()
        glx_assert(vppRxIndex == rxIndex)
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'rx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxRxIndex = glxRxIndex.rstrip()
        glx_assert(glxRxIndex == vppRxIndex)
        # should not same.
        glx_assert(glxRxIndex != glxTxIndex)

        # enable combined.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 30000, True)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        txName = txName.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep index | awk '{{print $4}}' | cut -d':' -f1 ")
        glx_assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        glx_assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'tx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        glx_assert(glxTxIndex == vppTxIndex)
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        glx_assert(err == '')
        rxName = rxName.rstrip()
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        glx_assert(err == '')
        rxIndex = rxIndex.rstrip()
        # verify vpp and glx.
        vppRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {rxName} | grep index | awk '{{print $4}}' | cut -d':' -f1 ")
        glx_assert(err == '')
        vppRxIndex = vppRxIndex.rstrip()
        glx_assert(vppRxIndex == rxIndex)
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'rx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxRxIndex = glxRxIndex.rstrip()
        glx_assert(glxRxIndex == vppRxIndex)
        # both vpp glx rx and tx should be same.
        glx_assert(vppRxIndex == vppTxIndex)
        glx_assert(glxRxIndex == glxTxIndex)

        # disable combined.
        self.topo.dut1.get_rest_device().update_overlay_traffic_limit(20000, 30000, False)
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        txName = txName.rstrip()
        # verify vpp and glx.
        vppTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {txName} | grep index | awk '{{print $4}}' | cut -d':' -f1 ")
        glx_assert(err == '')
        vppTxIndex = vppTxIndex.rstrip()
        glx_assert(vppTxIndex == txIndex)
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'tx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxTxIndex = glxTxIndex.rstrip()
        glx_assert(glxTxIndex == vppTxIndex)
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        glx_assert(err == '')
        rxName = rxName.rstrip()
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        glx_assert(err == '')
        rxIndex = rxIndex.rstrip()
        # verify vpp and glx.
        vppRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer name {rxName} | grep index | awk '{{print $4}}' | cut -d':' -f1 ")
        glx_assert(err == '')
        vppRxIndex = vppRxIndex.rstrip()
        glx_assert(vppRxIndex == rxIndex)
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'rx policer' | awk '{{print $5}}'")
        glx_assert(err == '')
        glxRxIndex = glxRxIndex.rstrip()
        glx_assert(glxRxIndex == vppRxIndex)
        # both vpp glx rx and tx should not be same.
        glx_assert(vppRxIndex != vppTxIndex)
        glx_assert(glxRxIndex != glxTxIndex)

        # delete the limit.
        self.topo.dut1.get_rest_device().delete_overlay_traffic_limit()
        glxTxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'tx policer' | awk '{{print $5}}'")
        glxTxIndex = glxTxIndex.rstrip()
        glx_assert(glxTxIndex == "4294967295")
        glxRxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx global | grep 'rx policer' | awk '{{print $5}}'")
        glxRxIndex = glxRxIndex.rstrip()
        glx_assert(glxRxIndex == "4294967295")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show policer pools")
        # policer should be be remained.
        glx_assert("policers=0" in out)
        # redis should also be empty.
        txName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerName")
        glx_assert(err == '')
        txName = txName.rstrip()
        glx_assert(txName == "")
        txIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 TxVppPolicerIndex")
        glx_assert(err == '')
        txIndex = txIndex.rstrip()
        glx_assert(txIndex == "4294967295")
        rxName, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerName")
        glx_assert(err == '')
        rxName = rxName.rstrip()
        glx_assert(rxName == "")
        rxIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget PolicerContext#0 RxVppPolicerIndex")
        glx_assert(err == '')
        rxIndex = rxIndex.rstrip()
        glx_assert(rxIndex == "4294967295")

    def test_glx_acc_cpe_side(self):
        # 1. enable acc feature on the segment.
        # 2. add acc route
        # 3. check route have is_acc field (this also means we have checked the acc fib table).
        # 4. try to disable acc with failed.
        # 5. remove route
        # 6. disable the acc feature on the segment.

        self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=True)
        # verify default fib changed to fib acc.
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table 0 0.0.0.0/0")
        glx_assert(err == '')
        glx_assert("fib_lookupmiss_acc" in fibResult)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        self.topo.dut1.get_rest_device().create_edge_route(route_prefix="1.1.1.1/32", route_label="0x1234", is_acc=True)
        # acc fib for segment 0 is 128.
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table 128 1.1.1.1")
        glx_assert(err == '')
        glx_assert("is_acc: 1" in fibResult)
        glx_assert("1.1.1.1" in fibResult)
        glx_assert("0x0000001234" in fibResult)
        # try to disable acc when there is route.
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)
        # this should be failed with 500.
        glx_assert(result.status_code == 500)
        # remove the acc route.
        # 目前acc对控制平面不是key，所以无需传参。fwdmd可以从db中知道是否是加速路由。
        self.topo.dut1.get_rest_device().delete_edge_route(route_prefix="1.1.1.1/32")
        # 不能基于dip查询，否则将命中默认路由
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128")
        glx_assert(err == '')
        glx_assert(f"1.1.1.1/32" not in fibResult)
        glx_assert("0x0000001234" not in fibResult)
        # acc disable should ok.
        # try to disable acc when there is route.
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, acc_enable=False)
        # this should be ok with 200.
        glx_assert(result.status_code == 200)
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table 128")
        # the fib is pruned.
        glx_assert(fibResult == '')
        glx_assert(err == '')
        # verify default fib changed to fib miss normal.
        fibResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show ip fib table 0 0.0.0.0/0")
        glx_assert(err == '')
        glx_assert("fib_lookupmiss" in fibResult)
        glx_assert("fib_lookupmiss_acc" not in fibResult)

        # cleanup.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)

    def test_glx_acc_int_edge_side(self):
        # 1. enable int edge
        # 2. set acc ip.
        # 3. check ip address configured on loop.
        # 4. unset acc ip.
        # 5. unset int edge.
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, int_edge_enable=True)
        glx_assert(result.status_code == 200)
        # check vpp applied.
        result, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx segment segment-id 0")
        glx_assert(err == '')
        glx_assert("int_edge_enable 1" in result)
        # Use redis to get default segment's loop.
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
                    f"redis-cli hget SegmentContext#0 LoopSwIfIndex")
        glx_assert(err == '')
        ifindex = ifindex.rstrip()
        self.topo.dut1.get_rest_device().create_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.1")
        ipResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {ifindex}")
        glx_assert(err == '')
        glx_assert("222.222.222.1" in ipResult)
        # udpate the acc ip.
        self.topo.dut1.get_rest_device().update_segment_acc_prop(segment_id=0, acc_ip1="222.222.222.2")
        ipResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {ifindex}")
        glx_assert(err == '')
        glx_assert("222.222.222.1" not in ipResult)
        glx_assert("222.222.222.2" in ipResult)
        # delete the acc ip.
        self.topo.dut1.get_rest_device().delete_segment_acc_prop(segment_id=0)
        ipResult, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {ifindex}")
        glx_assert(err == '')
        glx_assert("222.222.222.1" not in ipResult)
        glx_assert("222.222.222.2" not in ipResult)
        # disable the int edge
        result = self.topo.dut1.get_rest_device().update_segment(segment_id=0, int_edge_enable=False)
        glx_assert(result.status_code == 200)
        # check vpp applied.
        result, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show glx segment segment-id 0")
        glx_assert(err == '')
        glx_assert("int_edge_enable 0" in result)

    def test_glx_edge_route_label_fwd_entry_default(self):
        # add t1/t2.
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2(0x00000002) members 0" in out)

        # update to t1 ok.
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" in out)
        glx_assert(f"tunnel-count 1" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 0" in out)

        # update to t2 ok.
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" not in out)
        glx_assert(f"tunnel-id 2" in out)
        glx_assert(f"tunnel-count 1" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 0" in out)

        # update to load balance ok.
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=1, tunnel_id2=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" in out)
        glx_assert(f"tunnel-id 2" in out)
        glx_assert(f"tunnel-count 2" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 1" in out)

        # TODO: update to failover ok.

        # remove t1/t2 should fail because there is ref.
        # 220926: tunnel因允许passive/active创建，不再报错，改为判断不为500，这里有点违背了http RESTful逻辑。
        # 这里会导致对应的fwdmd对象已经删除，但底层如果有多个，其实会对应于fwdmd的另外一个对象，该对象也需要
        # 删除，比如active tunnel & passive tunnel共存的情况，从语义上来说也是合理的。
        # 所以这里就得改为不去删除一次，避免影响引用计数。
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        #glx_assert(result.status_code == 410)
        #result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        #glx_assert(result.status_code == 410)

        # update to zero.
        self.topo.dut1.get_rest_device().update_glx_default_edge_route_label_fwd(tunnel_id1=None)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" not in out)
        glx_assert(f"tunnel-id 2" not in out)
        glx_assert(f"tunnel-count 0" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 0" in out)

        # remove t1/t2 should ok now.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2(0x00000002) members 0" not in out)

    # 创建特定route_label的fwd表项
    def test_glx_edge_route_label_fwd_entry_non_default(self):
        # add t1/t2.
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2(0x00000002) members 0" in out)

        # create a edge route label fwd entry.
        self.topo.dut1.get_rest_device().create_glx_edge_route_label_fwd(route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"0x0000001234" in out)

        # update to t1 ok.
        self.topo.dut1.get_rest_device().update_glx_edge_route_label_fwd(route_label="0x1234", tunnel_id1=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" in out)
        glx_assert(f"tunnel-count 1" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 0" in out)

        # update to t2 ok.
        self.topo.dut1.get_rest_device().update_glx_edge_route_label_fwd(route_label="0x1234", tunnel_id1=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" not in out)
        glx_assert(f"tunnel-id 2" in out)
        glx_assert(f"tunnel-count 1" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 0" in out)

        # update to load balance ok.
        self.topo.dut1.get_rest_device().update_glx_edge_route_label_fwd(route_label="0x1234", tunnel_id1=1, tunnel_id2=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" in out)
        glx_assert(f"tunnel-id 2" in out)
        glx_assert(f"tunnel-count 2" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 1" in out)

        # TODO: update to failover ok.

        # remove t1/t2 should fail because there is ref.
        # 220926: tunnel因允许passive/active创建，不再报错，改为判断不为500，这里有点违背了http RESTful逻辑。
        # 这里会导致对应的fwdmd对象已经删除，但底层如果有多个，其实会对应于fwdmd的另外一个对象，该对象也需要
        # 删除，比如active tunnel & passive tunnel共存的情况，从语义上来说也是合理的。
        # result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        # glx_assert(result.status_code == 500)
        # result = self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        # glx_assert(result.status_code == 500)

        # update to zero.
        self.topo.dut1.get_rest_device().update_glx_edge_route_label_fwd(route_label="0x1234", tunnel_id1=None)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" not in out)
        glx_assert(f"tunnel-id 2" not in out)
        glx_assert(f"tunnel-count 0" in out)
        glx_assert(f"is_failover: 0" in out)
        glx_assert(f"is_loadbalance: 0" in out)

        # remove t1/t2 should ok now.
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1(0x00000001) members 0" not in out)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2(0x00000002) members 0" not in out)

        # remove the label should ok.
        self.topo.dut1.get_rest_device().delete_glx_edge_route_label_fwd(route_label="0x1234")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx edge-route-label-fwd")
        glx_assert(err == '')
        glx_assert(f"0x0000001234" not in out)

    def test_glx_dpi_sameprocess_mode(self):
        # enable dpi.
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=True)
        # verify glx plugin using dpi loop to cross connect.
        dpiLoopIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget DpiContext#default DpiLoopSwIfIndex")
        dpiLoopIfIndex = dpiLoopIfIndex.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx global")
        glx_assert(err == "")
        glx_assert(f"dpi_peer_if {dpiLoopIfIndex}" in out)
        # verify dpi plugin using glx loop to cross connect.
        glxLoopIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget DpiContext#default GlxLoopSwIfIndex")
        glxLoopIfIndex = glxLoopIfIndex.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx dpi global")
        glx_assert(err == "")
        glx_assert(f"peer interface {glxLoopIfIndex}" in out)

        # disable dpi.
        self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=False)
        # verify glx plugin peer if to ~0.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx global")
        glx_assert(err == "")
        glx_assert(f"dpi_peer_if 4294967295" in out)
        # the glx loop should be deleted.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {glxLoopIfIndex}")
        glx_assert(err == "")
        glx_assert("unknown interface" in out)
        # verify dpi plugin peer if to ~0.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx dpi global")
        glx_assert(err == "")
        glx_assert(f"peer interface 4294967295" in out)
        # the dpi loop should be deleted.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {dpiLoopIfIndex}")
        glx_assert(err == "")
        glx_assert("unknown interface" in out)

    def test_glx_dpi_with_firewall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
                    "test_acl3", 3, "192.168.11.2/32", "Deny", app_id=65535)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show acl acl | grep 11.2")
        glx_assert(err == "")
        glx_assert("appid 65535" in out)
        self.topo.dut1.get_rest_device().update_fire_wall_rule(
                    "test_acl3", 3, "192.168.11.2/32", "Deny", app_id=100)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show acl acl | grep 11.2")
        glx_assert(err == "")
        glx_assert("appid 100" in out)
        self.topo.dut1.get_rest_device().delete_fire_wall_rule(
            "test_acl3")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show acl acl | grep 11.2")
        glx_assert(err == "")
        glx_assert("appid 100" not in out)

    def test_glx_dpi_with_bizpol(self):
        self.topo.dut1.get_rest_device().create_bizpol(
                    "test_bizpol_withapp", 3, "0.0.0.0/0", "192.168.11.2/32", 0, direct_enable=False, app_id=65535)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 11.2")
        glx_assert(err == "")
        glx_assert("appid 65535" in out)
        self.topo.dut1.get_rest_device().update_bizpol(
                    "test_bizpol_withapp", 3, "0.0.0.0/0", "192.168.11.2/32", 0, direct_enable=False, app_id=100)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 11.2")
        glx_assert(err == "")
        glx_assert("appid 100" in out)
        self.topo.dut1.get_rest_device().delete_bizpol(
            "test_bizpol_withapp")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 11.2")
        glx_assert(err == "")
        glx_assert("appid 100" not in out)

    @unittest.skip("2023.09.15 segment route label is deprecated.")
    def duplicated_test_glx_segment_routelabel_update(self):
        # 检查segment routelabel 初始值为全f
        #self.topo.dut1.get_rest_device().create_segment(segment_id = 0)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("route-label 1099511627775" in out)

        # 更新segment
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, route_label="123")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("route-label 123" in out)

        # 再次更新segment
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, route_label="456")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("route-label 456" in out)

        # 将segment置为全f
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, route_label="0xffffffffffffffff")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment")
        glx_assert(err == "")
        glx_assert("route-label 1099511627775" in out)

    def test_glx_segment_dns_intercept_enable(self):
        mtu = 1500
        # 检查segment 0 exit-if已配置
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx segment segment-id 0")
        glx_assert(err == "")
        glx_assert("exit-if-index 4294967295" not in out)

        # 检查 default bvi 上未使能 dns-intercept
        bviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#default BviSwIfIndex")
        bviSwIfIndex = bviSwIfIndex.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {bviSwIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" not in out)

        # 开启 segment DnsInterceptEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, dns_intercept_enable=True)

        # 检查 default bvi 已经使能 dns-intercept
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {bviSwIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" in out)

        # 创建获取一个新 bvi 和一个新 logical interface
        self.topo.dut1.get_rest_device().create_bridge("test", "192.168.89.1/24", mtu=mtu)
        self.topo.dut1.get_rest_device().update_physical_interface("LAN1", 1500, "routed", "default")

        # 检查发现已经使能
        testBviSwIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget BridgeContext#test BviSwIfIndex")
        testBviSwIfIndex = testBviSwIfIndex.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {testBviSwIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" in out)
        logicalIfIndex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget VppIfIndexContext#LAN1 IfIndex")
        logicalIfIndex = logicalIfIndex.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {logicalIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" in out)

        # 创建一个新segment
        self.topo.dut1.get_rest_device().create_segment(segment_id=1)
        # 切换到新segment上
        self.topo.dut1.get_rest_device().set_logical_interface_segment("LAN1", 1)
        # 未使能
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {logicalIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" not in out)
        # 切回segment0
        self.topo.dut1.get_rest_device().set_logical_interface_segment("LAN1", 0)
        # 使能
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {logicalIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" in out)

        # 关闭 segment DnsInterceptEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, dns_intercept_enable=False)

        # 检查发现都已去使能
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {bviSwIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {testBviSwIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int feat {logicalIfIndex} | grep ip4-unicast -A 20")
        glx_assert(err == "")
        glx_assert("dns-intercept" not in out)

        # 将LAN1改动改回
        self.topo.dut1.get_rest_device().update_physical_interface("LAN1", 1500, "switched", "default")
        # 删除test bridge
        self.topo.dut1.get_rest_device().delete_bridge("test")
        # 删除segment 1
        self.topo.dut1.get_rest_device().delete_segment(segment_id=1)

    @unittest.skip("need to fix")
    def test_glx_namespace_nat_rules(self):
        # 检查nat规则
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns iptables -L -nv -t nat | grep SNAT | wc -l")
        glx_assert(err == '')
        glx_assert("1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns iptables -L -nv -t nat | grep DNAT | wc -l")
        glx_assert(err == '')
        glx_assert("0" in out)
        # 开启 segment DnsInterceptEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, dns_intercept_enable=True)
        # 检查nat是否有且只有一条规则
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns iptables -L -nv -t nat | grep DNAT | wc -l")
        glx_assert(err == '')
        glx_assert("1" in out)
        # 关闭 segment DnsInterceptEnable
        self.topo.dut1.get_rest_device().update_segment(segment_id=0, dns_intercept_enable=False)
        # 检查nat规则
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns iptables -L -nv -t nat | grep SNAT | wc -l")
        glx_assert(err == '')
        glx_assert("1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns iptables -L -nv -t nat | grep DNAT | wc -l")
        glx_assert(err == '')
        glx_assert("0" in out)
        # 重启vpp，模拟vpp crash场景
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart vpp")
        glx_assert(err == '')
        # 等待fwdmd配置
        time.sleep(10)
        # 检查nat规则
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ip netns exec ctrl-ns iptables -L -nv -t nat | grep SNAT | wc -l")
        glx_assert(err == '')
        glx_assert("1" in out)

    # 测试glx link不加密
    def test_glx_link_no_encryption(self):
        # create a link with no encryption
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, no_encryption=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ikev2 profile")
        glx_assert(err == '')
        # no ikev2 profile is installed.
        glx_assert(f"ActiveIkeV2Profile_1" not in out)
        glx_assert(f"glx_link0" not in out)
        # remove the link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)

    # 验证port range可以正确配置，避免功能异常
    def test_glx_bizpol_port_range(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_port_range",priority=1,
                                                       src_prefix="192.168.89.5/32",
                                                       dst_prefix="0.0.0.0/0",
                                                       # tcp
                                                       protocol=1,
                                                       src_port_first=10000,
                                                       src_port_last=20000,
                                                       dst_port_first=10000,
                                                       dst_port_last=20000,
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 192.168.89.5")
        glx_assert(err == '')
        glx_assert('sport 10000-20000' in out)
        glx_assert('dport 10000-20000' in out)
        glx_assert('[nat]' in out)

        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol_port_range",priority=1,
                                                       src_prefix="192.168.89.5/32",
                                                       dst_prefix="0.0.0.0/0",
                                                       # tcp
                                                       protocol=1,
                                                       src_port_first=30000,
                                                       src_port_last=40000,
                                                       dst_port_first=30000,
                                                       dst_port_last=40000,
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 192.168.89.5")
        glx_assert(err == '')
        glx_assert('sport 10000-20000' not in out)
        glx_assert('sport 30000-40000' in out)
        glx_assert('dport 10000-20000' not in out)
        glx_assert('dport 30000-40000' in out)
        glx_assert('[nat]' in out)

        # delete the bizpol.
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_port_range")

    def test_glx_bizpol_sched_class(self):
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol_sched_class",priority=1,
                                                       src_prefix="192.168.89.6/32",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       sched_class="normal",
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 192.168.89.6")
        glx_assert(err == '')
        glx_assert('sched-class 2' in out)
        glx_assert('[nat]' in out)

        self.topo.dut1.get_rest_device().update_bizpol(name="bizpol_sched_class",priority=1,
                                                       src_prefix="192.168.89.6/32",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       sched_class="high",
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 192.168.89.6")
        glx_assert(err == '')
        glx_assert('sched-class 1' in out)
        glx_assert('[nat]' in out)

        # delete the bizpol.
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol_sched_class")

    def test_glx_bizpol_rate_limit(self):
        # no limit test
        name = "bizpol-nat"
        key = f"BusinessPolicyContext#{name}"
        up_policer_name = f"up_policer_{name}_0"
        up_limit = 4096
        down_policer_name = f"down_policer_{name}_0"
        down_limit = 4096
        self.topo.dut1.get_rest_device().create_bizpol(name=name, priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       direct_enable=True)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol | grep 192.168.88.0")
        glx_assert(err == '')
        glx_assert('192.168.88.0/24' in out)
        # now no interface needed due to auto steering feature support.
        glx_assert(f'[nat]' in out)

        # check policy index
        policy_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {key} PolicyIndex")
        glx_assert(err == '')

        # up limit test
        out = self.topo.dut1.get_rest_device().update_bizpol(name=name,priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       rate_limit_enable=True, up_rate_limit=up_limit, down_rate_limit=0)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx policer | grep {up_policer_name}")
        glx_assert(err == '')

        glx_assert(up_policer_name in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hgetall {key}")

        glx_assert(err == '')
        glx_assert('UpPolicerIndex' in out)

        # 测试index是否一致
        policer_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {key} UpPolicerIndex")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol index {policy_index} | grep up-limit-index | awk -F 'up-limit-index' '{{print $2}}' | awk '{{print $1}}'")
        glx_assert(policer_index in out)

        # down limit test
        self.topo.dut1.get_rest_device().update_bizpol(name=name,priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol=0,
                                                       rate_limit_enable=True, up_rate_limit=0, down_rate_limit=down_limit)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx policer | grep {down_policer_name}")
        glx_assert(err == '')
        glx_assert(down_policer_name in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hgetall {key}")
        glx_assert(err == '')
        glx_assert('DownPolicerIndex' in out)

        # check policer index
        policer_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {key} DownPolicerIndex")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol index {policy_index} | grep down-limit-index | awk -F 'down-limit-index' '{{print $2}}' | awk '{{print $1}}'")
        glx_assert(policer_index in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show policer | grep {up_policer_name}")
        glx_assert(err == '')
        glx_assert(up_policer_name not in out)

        # up and down limit test
        self.topo.dut1.get_rest_device().update_bizpol(name=name,priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol= 0,
                                                       rate_limit_enable=True, up_rate_limit=up_limit, down_rate_limit=down_limit)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx policer | grep {up_policer_name}")
        glx_assert(err == '')
        glx_assert(up_policer_name in out)


        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx policer | grep {down_policer_name}")
        glx_assert(err == '')
        glx_assert(down_policer_name in out)

        # 测试index是否一致
        policer_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {key} UpPolicerIndex")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol index {policy_index} | grep up-limit-index | awk -F 'up-limit-index' '{{print $2}}' | awk '{{print $1}}'")
        glx_assert(policer_index in out)

        # check policer index
        policer_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {key} DownPolicerIndex")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol index {policy_index} | grep down-limit-index | awk -F 'down-limit-index' '{{print $2}}' | awk '{{print $1}}'")
        glx_assert(policer_index in out)


        # disable up and down limit
        self.topo.dut1.get_rest_device().update_bizpol(name=name,priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="0.0.0.0/0",
                                                       protocol= 0,
                                                       rate_limit_enable=False)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx policer | grep {up_policer_name}")
        glx_assert(err == '')
        glx_assert(up_policer_name not in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx policer | grep {down_policer_name}")
        glx_assert(err == '')
        glx_assert(down_policer_name not in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show policer | grep {up_policer_name}")
        glx_assert(err == '')
        glx_assert(up_policer_name not in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show policer | grep {down_policer_name}")
        glx_assert(err == '')
        glx_assert(down_policer_name not in out)

        # 测试index是否一致
        policer_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {key} UpPolicerIndex")
        glx_assert(err == '')
        glx_assert(policer_index == '4294967295')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol index {policy_index} | grep up-limit-index | awk -F 'up-limit-index' '{{print $2}}' | awk '{{print $1}}'")
        glx_assert('255' in out)

        # check policer index
        policer_index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {key} DownPolicerIndex")
        glx_assert(err == '')
        glx_assert(policer_index == '4294967295')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show bizpol bizpol index {policy_index} | grep down-limit-index | awk -F 'down-limit-index' '{{print $2}}' | awk '{{print $1}}'")
        glx_assert('255' in out)

        # delete the bizpol.
        self.topo.dut1.get_rest_device().delete_bizpol(name=name)

if __name__ == '__main__':
    unittest.main()
