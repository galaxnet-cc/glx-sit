import unittest
import time
import random
import os

from lib.util import glx_assert
from topo.topo_1d import Topo1D


class TestRestVppConsistency1DIP6(unittest.TestCase):
    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass
    
    def test_bridge(self):
        br_redis_key_pre = "BridgeContext#"
        br_redis_index_field = "BviSwIfIndex"
        brname = "bridge2"
        unused_ip4 = "192.168.2.1/24"
        ip_pre = "2001:db7"
        ip = ip_pre + "::2"
        prefix = "/64"
        ip_with_prefix = ip + prefix
        slaac_msg = "Hosts use stateless autoconfig for addresses"
        slaac_not_msg = "Hosts  don't use stateless autoconfig for addresses"

        # Create bridge with IPv6 address
        #  Address validation
        #   Loop back address
        resp = self.topo.dut1.rest_device.create_bridge(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix="::1/128")
        glx_assert(resp.status_code == 500)
        #   Link local address
        resp = self.topo.dut1.rest_device.create_bridge(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=self.generate_link_local_ip6())
        glx_assert(resp.status_code == 500)
        #   Multicast address
        resp = self.topo.dut1.rest_device.create_bridge(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=self.generate_multicast_ip6())
        glx_assert(resp.status_code == 500)
        #  Unique local address.
        resp = self.topo.dut1.rest_device.create_bridge(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=self.generate_unqiue_local_ip6())
        glx_assert(resp.status_code == 201)
        # Delete
        self.topo.dut1.rest_device.delete_bridge(brname)
        #  Create
        #  Global unique address.
        resp = self.topo.dut1.rest_device.create_bridge(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=ip_with_prefix)
        glx_assert(resp.status_code == 201)

        # Check ipv6 address in bvi.
        index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget {br_redis_key_pre}{brname} {br_redis_index_field}")
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {index}")
        glx_assert(err == '')
        glx_assert(ip_with_prefix in out)

        # Check ip6 nd.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip6 int {index}")
        glx_assert(err == '')
        # ip
        glx_assert(ip_with_prefix in out)
        # slaac message
        glx_assert(slaac_msg in out)

        time.sleep(4)

        # Restart fwdmd 
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart fwdmd")
        glx_assert(err == '')
        # 等待fwdmd重启完成（10s足够）
        time.sleep(10)

        # Update bridge
        #  Address validation
        #   Loop back address
        ip_pre = "2001:db6"
        ip = ip_pre + "::2"
        prefix = "/64"
        ip_with_prefix = ip + prefix
        resp = self.topo.dut1.rest_device.update_bridge_ip_or_mtu(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix="::1/128")
        glx_assert(resp.status_code == 500)
        #   Link local address
        resp = self.topo.dut1.rest_device.update_bridge_ip_or_mtu(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=self.generate_link_local_ip6())
        glx_assert(resp.status_code == 500)
        #   Multicast address
        resp = self.topo.dut1.rest_device.update_bridge_ip_or_mtu(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=self.generate_multicast_ip6())
        glx_assert(resp.status_code == 500)
        #  Update
        #  Unique local address.
        resp = self.topo.dut1.rest_device.update_bridge_ip_or_mtu(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=self.generate_unqiue_local_ip6())
        glx_assert(resp.status_code == 200)
        #  Global unique address.
        resp = self.topo.dut1.rest_device.update_bridge_ip_or_mtu(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=ip_with_prefix)
        glx_assert(resp.status_code == 200)
        # Check ipv6 address in bvi.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {index}")
        glx_assert(err == '')
        glx_assert(ip_with_prefix in out)
        # Check ip6 nd.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip6 int {index}")
        glx_assert(err == '')
        # ip
        glx_assert(ip_with_prefix in out)
        # slaac message
        glx_assert(slaac_msg in out)
        #  Update
        #  Global unique address
        #  Update prefix.It should not have slaac.
        prefix = "/80"
        ip_with_prefix = ip + prefix
        resp = self.topo.dut1.rest_device.update_bridge_ip_or_mtu(name=brname, bvi_ip_w_prefix=unused_ip4, bvi_ip6_w_prefix=ip_with_prefix)
        glx_assert(resp.status_code == 200)
        # Check ipv6 address in bvi.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {index}")
        glx_assert(err == '')
        glx_assert(ip_with_prefix in out)
        # Check ip6 nd.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip6 int {index}")
        glx_assert(err == '')
        # ip
        glx_assert(ip_with_prefix in out)
        # slaac message
        glx_assert(slaac_not_msg in out)

        # Remove ipv6.
        resp = self.topo.dut1.rest_device.update_bridge_ip_or_mtu(brname, unused_ip4, bvi_ip6_w_prefix="")
        glx_assert(resp.status_code == 200)
        # Check ipv6 address is not in bvi.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {index}")
        glx_assert(err == '')
        glx_assert(ip_with_prefix not in out)

        # Delete
        self.topo.dut1.rest_device.delete_bridge(brname)

        # Update default bridge
        brname="default"
        ip_pre = "2001:db8"
        ip = ip_pre + "::2"
        prefix = "/64"
        ip_with_prefix = ip + prefix
        default_bvi_ip = "192.168.88.1/24"
        resp = self.topo.dut1.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=default_bvi_ip, bvi_ip6_w_prefix=ip_with_prefix)
        glx_assert(resp.status_code == 200)
        index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget {br_redis_key_pre}{brname} {br_redis_index_field}")
        glx_assert(err == '')
        # Check ipv6 address in bvi.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {index}")
        glx_assert(err == '')
        glx_assert(ip_with_prefix in out)

        # Restart vpp, fwdmd 
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart vpp")
        glx_assert(err == '')
        time.sleep(3)
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("sudo systemctl restart fwdmd")
        glx_assert(err == '')
        # 等待fwdmd重启完成（10s足够）
        time.sleep(10)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {index}")
        glx_assert(err == '')
        glx_assert(ip_with_prefix in out)

        resp = self.topo.dut1.rest_device.set_default_bridge_ip_or_mtu(bvi_ip_w_prefix=default_bvi_ip, bvi_ip6_w_prefix="")
        glx_assert(resp.status_code == 200)
        # Check ipv6 address is not in bvi.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"vppctl show int addr {index}")
        glx_assert(err == '')
        glx_assert(ip_with_prefix not in out)

    def generate_link_local_ip6(self):
        prefix = "fe80"
        blocks = [format(random.randint(0, 0xFFFF), '04x') for _ in range(4)]
        return f"{prefix}::{':'.join(blocks)}/64"

    def generate_multicast_ip6(self):
        prefix = "ff"
        flgs = format(random.randint(0, 0xF), 'x')
        scop = format(random.randint(0, 0xF), 'x')
        blocks = [format(random.randint(0, 0xFFFF), '04x') for _ in range(7)]
        return f"{prefix}{flgs}{scop}::{':'.join(blocks)}/64"

    def generate_unqiue_local_ip6(self):
        random_hex = os.urandom(5).hex()

        formatted_hex = ":".join([random_hex[i:i+4] for i in range(0, len(random_hex), 4)])

        return f"fd00:{formatted_hex}::1/64"



        


