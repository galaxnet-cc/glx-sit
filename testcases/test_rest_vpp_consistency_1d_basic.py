import unittest
import time

from topo.topo_1d import Topo1D


class TestRestVppConsistency1DBasic(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_multi_wan_address_type_translation(self):
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        wan2VppIf = self.topo.dut1.get_if_map()["WAN2"]
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN2", "192.168.2.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.1/24" in out)
        # change address type to static from static
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN2", "192.168.2.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.2/24" in out)
        assert("192.168.2.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.2/24" in out)
        assert("192.168.2.1/24" not in out)

        # change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.3/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.3/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN2", "192.168.2.3/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.3/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.3/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)

        # change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_wan_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        self.topo.dut1.get_rest_device().set_wan_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        assert("pppox1" in out)
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl set interface ip address pppox0 1.1.1.1/32")
        assert(err == '')
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl set interface ip address pppox1 1.1.1.2/32")
        assert(err == '')
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr pppox0 | grep ip4 | awk '{{print $5}}'")
        assert(err == '')
        out = out.rstrip()
        assert(out>="8192")
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr pppox1 | grep ip4 | awk '{{print $5}}'")
        assert(err == '')
        out = out.rstrip()
        assert(out>="8192")
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl set interface ip address del pppox0 1.1.1.1/32")
        assert(err == '')
        out,err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl set interface ip address del pppox1 1.1.1.2/32")
        assert(err == '')

        # change address type of two wans to static successively
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        assert("192.168.1.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        assert("192.168.1.3/24" not in out)
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN2", "192.168.2.4/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan2VppIf}")
        assert(err == '')
        assert("192.168.2.4/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN2")
        assert(err == '')
        assert("192.168.2.4/24" in out)
        assert("192.168.2.1/24" not in out)
        assert("192.168.2.2/24" not in out)
        assert("192.168.2.3/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" not in out)
        assert("pppox1" not in out)

        #change to dhcp
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert(f'{wan2VppIf}' in out)

        #change address type of two wans to pppoe successively
        self.topo.dut1.get_rest_device().set_wan_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        self.topo.dut1.get_rest_device().set_wan_pppoe("WAN2", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        assert("pppox1" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' not in out)
        assert(f'{wan2VppIf}' not in out)

        #change address type of two wans to dhcp successively
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN1")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN2")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert(f'{wan2VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" not in out)
        assert("pppox1" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" in out)

        
    def test_change_address_type_to_static_from_static(self):
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.1/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check logical interface using static address type
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        # change ip and verify again
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.2/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)

        #test_change_address_type_to_dhcp_from_static
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.1/24" not in out)
        assert("192.168.1.2/24" not in out)

        #test_change_address_type_to_static_from_dhcp
        # change address to static
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.3/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.3/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.3/24" in out)

        #test_change_address_type_to_pppoe_from_static
        self.topo.dut1.get_rest_device().set_wan_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        
        #test_change_address_type_to_static_from_pppoe
        self.topo.dut1.get_rest_device().set_wan_static_ip("WAN1", "192.168.1.4/24")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {wan1VppIf}")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show WAN1")
        assert(err == '')
        assert("192.168.1.4/24" in out)
        # check if pppoe related configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep ppp")
        assert(err == '')

        #test change address type to dhcp from pppoe
        self.topo.dut1.get_rest_device().set_wan_pppoe("WAN1", "test", "123456")
        # change to dhcp
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN1")
        wan1VppIf = self.topo.dut1.get_if_map()["WAN1"]
        # check dhcp client
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show dhcp client")
        assert(err == '')
        assert(f'{wan1VppIf}' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox" not in out)

        #test_change_address_type_to_pppoe_from_dhcp
        self.topo.dut1.get_rest_device().set_wan_pppoe("WAN1", "test", "123456")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show int")
        assert(err == '')
        assert("pppox0" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe server")
        assert(err == '')
        assert("No pppoe servers configured" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show pppoe client")
        assert(err == '')
        assert("No pppoe clients configured" not in out)

        #recovery to dhcp
        self.topo.dut1.get_rest_device().set_wan_dhcp("WAN1")

    def test_fire_wall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule(
            "test_acl3", 3, "192.168.11.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("test_acl3" in out)
        assert("192.168.11.2/32" in out)
        # update
        self.topo.dut1.get_rest_device().update_fire_wall_rule(
            "test_acl3", 3, "192.168.12.2/32", "Deny")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("192.168.12.2/32" in out)
        assert("192.168.11.2/32" not in out)
        # delete
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("test_acl3" not in out)
        assert("192.168.12.2/32" not in out)

    def test_multi_fire_wall(self):
        self.topo.dut1.get_rest_device().set_fire_wall_rule("test_acl3",3,"192.168.11.3/32","Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule("test_acl5",5,"192.168.11.5/32","Deny")
        self.topo.dut1.get_rest_device().set_fire_wall_rule("test_acl4",4,"192.168.11.4/32","Deny")
        # default bvi is loop0.
        ifindex, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int loop0 | grep loop0 | awk '{{print $2}}'")
        assert(err == '')
        ifindex = ifindex.rstrip()
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show acl-plugin interface sw_if_index {ifindex} acl")
        assert(err == '')
        pos3 = out.index('192.168.11.3')
        pos4 = out.index('192.168.11.4')
        pos5 = out.index('192.168.11.5')
        assert(pos5<pos4<pos3)
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl3")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl4")
        self.topo.dut1.get_rest_device().delete_fire_wall_rule("test_acl5")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"vppctl show acl-plugin acl")
        assert(err == '')
        assert("test_acl3" not in out)
        assert("test_acl4" not in out)
        assert("test_acl5" not in out)

    def test_host_stack_dnsmasq(self):
        # check if config file exists
        self.topo.dut1.get_rest_device().set_host_stack_dnsmasq("default", "255.255.255.0",
                                                                "192.168.0.50", "192.168.0.150", "255.255.255.0", "12h")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /tmp")
        assert(err == '')
        assert("dnsmasq_default.pid" in out)
        assert("dnsmasq_dhcp_default.conf" in out)
        assert("dnsmasq_dhcp_default.leases" in out)
        # check conf
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /tmp/dnsmasq_dhcp_default.conf")
        assert(err == '')
        assert("dhcp-range=192.168.0.50,192.168.0.150,255.255.255.0,12h" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        assert(err == '')
        assert("/tmp/dnsmasq_dhcp_default.conf" in out)

        # update
        self.topo.dut1.get_rest_device().update_host_stack_dnsmasq("default", "255.255.255.0",
                                                                   "192.168.0.100", "192.168.0.150", "255.255.255.0", "12h")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /tmp")
        assert(err == '')
        assert("dnsmasq_default.pid" in out)
        assert("dnsmasq_dhcp_default.conf" in out)
        assert("dnsmasq_dhcp_default.leases" in out)
        # check conf
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns cat /tmp/dnsmasq_dhcp_default.conf")
        assert(err == '')
        assert("dhcp-range=192.168.0.50,192.168.0.150,255.255.255.0,12h" not in out)
        assert("dhcp-range=192.168.0.100,192.168.0.150,255.255.255.0,12h" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        assert(err == '')
        assert("/tmp/dnsmasq_dhcp_default.conf" in out)

        # delete and verify
        self.topo.dut1.get_rest_device().delete_host_stack_dnsmasq("default")
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ip netns exec ctrl-ns ls /tmp")
        assert(err == '')
        assert("dnsmasq_default.pid" not in out)
        assert("dnsmasq_dhcp_default.conf" not in out)
        assert("dnsmasq_dhcp_default.leases" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        assert(err == '')
        assert("/tmp/dnsmasq_dhcp_default.conf" not in out)

    def test_bridge(self):
        # Add new ip address
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.1.1/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr loop0")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show defBr")
        assert(err == '')
        assert("192.168.1.1/24" in out)
        # update and verify
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.1.2/24")
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr loop0")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ip addr show defBr")
        assert(err == '')
        assert("192.168.1.2/24" in out)
        assert("192.168.1.1/24" not in out)

        #recovery ip address to 88.1
        self.topo.dut1.get_rest_device().set_default_bridge_ip("192.168.88.1/24")
