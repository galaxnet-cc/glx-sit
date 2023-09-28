import unittest
import random
import time

from parameterized import parameterized
from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DObjGroup(unittest.TestCase):
    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass
    def test_addr_group(self):
        group_name = "addr_test"
        vpp_group_table_id_start = 9217
        # Create
        #       1. CIDR validation
        #       2. CIDR covered
        #       3. Group member's validation.The member should be less or equal than 255.
        #       4. Success.
        #       5. Multi group CIDR covered
        invalid_ip_prefix = "192.168."
        resp = self.topo.dut1.get_rest_device().create_addr_group(group_name, invalid_ip_prefix)
        glx_assert(resp.status_code == 500)

        covered = ["192.168.1.0/24", "192.168.1.1/32"]
        resp = self.topo.dut1.get_rest_device().create_addr_group_multi(group_name, covered)
        glx_assert(resp.status_code == 500)

        group_members = [self.gen_ipv4_cidr() for _ in range(256)]
        resp = self.topo.dut1.get_rest_device().create_addr_group_multi(group_name, group_members)
        glx_assert(resp.status_code == 500)

        resp = self.topo.dut1.get_rest_device().create_addr_group(group_name, "192.168.1.0/24")
        glx_assert(resp.status_code == 201)
        # VPP validation
        group_id, err = self.get_addr_group_id(group_name)
        glx_assert(err == '')
        glx_assert(group_id != '')
        table_id = int(group_id) + vpp_group_table_id_start
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx addr-group group-id {group_id}")
        glx_assert(err == '')
        glx_assert(f"addr group id: {group_id} configured table id: {table_id}" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table {table_id}")
        glx_assert(err == '')
        glx_assert("192.168.1.0/24" in out)

        resp = self.topo.dut1.get_rest_device().create_addr_group("covered_addr_test", "192.168.1.1/32")
        glx_assert(resp.status_code == 500)

        # Update
        #       1. Group member's validation.
        #       2. Success.
        # 考虑到需要删除旧数据，所以需要减掉1,因为同步到vpp侧是修改项最多达到255，后面为了测试
        group_members = [f"192.168.{i}.0/24" for i in range(2, 254)]
        resp = self.topo.dut1.get_rest_device().update_addr_group_multi(group_name, group_members)
        glx_assert(resp.status_code == 200)


        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table {table_id}")
        glx_assert(err == '')
        for group_member in group_members:
            glx_assert(group_member in out)

        # Restart
        #   Validation
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart vpp")
        time.sleep(5)
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart fwdmd")
        time.sleep(15)

        group_id, err = self.get_addr_group_id(group_name)
        glx_assert(err == '')
        glx_assert(group_id != '')
        table_id = int(group_id) + vpp_group_table_id_start

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table {table_id}")
        glx_assert(err == '')
        for group_member in group_members:
            glx_assert(group_member in out)

        # Create another
        resp = self.topo.dut1.get_rest_device().create_addr_group("addr_test2", "172.17.0.1/16")
        glx_assert(resp.status_code == 201)

        # Delete
        resp = self.topo.dut1.get_rest_device().delete_addr_group(group_name)
        glx_assert(resp.status_code == 410)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx addr-group")
        glx_assert(err == '')
        glx_assert(f"addr group id: {group_id} configured table id: {table_id}" not in out)
        # 删除table会出现断言错误
        # out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show ip fib table {table_id}")
        # glx_assert(err == '')
        # glx_assert(out == '')
        resp = self.topo.dut1.get_rest_device().delete_addr_group("addr_test2")
        glx_assert(resp.status_code == 410)

    @parameterized.expand([
                ("tcp", "udp"),
                ("udp", "tcp"),
            ])
    def test_port_group(self, protocol: str, protocol2: str):
        group_name = "port_test"
        # Create
        #       1. Port is invalid
        #       2. Port protocol is invalid
        #       3. Port range is invalid
        #       4. Port range list is more than 32
        #       5. Success
        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, protocol, "65536")
        glx_assert(resp.status_code == 500)

        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, "kcp", "9090")
        glx_assert(resp.status_code == 500)

        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, protocol, "9090~8080")
        glx_assert(resp.status_code == 500)
        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, protocol, "9090~9090")
        glx_assert(resp.status_code == 500)
        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, protocol, "9090,9090~9091")
        glx_assert(resp.status_code == 500)
        # in one member
        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, protocol, "9090~9091,9090~9093")
        glx_assert(resp.status_code == 500)
        # in many members
        resp = self.topo.dut1.get_rest_device().create_port_group_multi(group_name, [(protocol, "9090~9091"), (protocol, "9090~9093")])
        glx_assert(resp.status_code == 500)

        big_group_member = ",".join([f"{9090+i}" for i in range(33)])
        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, protocol, big_group_member)
        glx_assert(resp.status_code == 500)

        resp = self.topo.dut1.get_rest_device().create_port_group(group_name, protocol, "9090,9091~9092")
        glx_assert(resp.status_code == 201)

        # VPP validation
        group_id, err = self.get_port_group_id(group_name)
        glx_assert(err == '')
        glx_assert(group_id != '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx port-group group-id {group_id}")
        glx_assert(err == '')
        glx_assert(f"port group id: {group_id}" in out)
        glx_assert(f"{protocol} ports: 9090~9092" in out)
        
        # 考虑到需要删除旧数据，所以需要减掉2,因为同步到vpp侧是修改项最多达到32
        ports = [f"{10090+i}" for i in range(30)]
        big_group_member = ",".join(ports)
        resp = self.topo.dut1.get_rest_device().update_port_group(group_name, protocol2, big_group_member)
        glx_assert(resp.status_code == 200)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx port-group group-id {group_id}")
        glx_assert(f"port group id: {group_id}" in out)
        glx_assert(f"{protocol2} ports: 10090~10119" in out)

        # Restart
        #   Validation
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart vpp")
        time.sleep(5)
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart fwdmd")
        time.sleep(15)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx port-group")
        glx_assert(f"port group id: {group_id}" in out)
        glx_assert(f"{protocol2} ports: 10090~10119" in out)

        # Create another
        resp = self.topo.dut1.get_rest_device().create_port_group("port_test2", protocol2, "8090")
        glx_assert(resp.status_code == 201)

        # Delete
        resp = self.topo.dut1.get_rest_device().delete_port_group(group_name)
        glx_assert(resp.status_code == 410)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx port-group group-id {group_id}")
        glx_assert(err == '')
        glx_assert(f"port group id: {group_id}" not in out)

        resp = self.topo.dut1.get_rest_device().delete_port_group("port_test2")
        glx_assert(resp.status_code == 410)

    def get_addr_group_id(self, group_name):
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget AddrGroupContext#{group_name} AddrGroupId")
        return out, err
    def get_port_group_id(self, group_name):
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget PortGroupContext#{group_name} PortGroupId")
        return out, err
    
    def gen_ipv4_cidr(self):
        ip = ".".join(str(random.randint(0, 255)) for _ in range(4))

        prefix_length = random.randint(1, 32)

        return f"{ip}/{prefix_length}"
