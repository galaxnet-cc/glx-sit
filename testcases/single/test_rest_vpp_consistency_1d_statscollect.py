import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DStatsCollect(unittest.TestCase):

    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_glx_link_get_stats_from_vpp(self):
        # 创建link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" in out)

        # 等待stats collect读取数据，fwdmd配置文件里默认为10s一次，等待时间需要大于它
        time.sleep(15)
        # 检测redis里数据与vpp是否一致
        linkState, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#1 State")
        linkState = linkState.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link | grep link-id\ 1 -A 20")
        glx_assert(err == '')
        glx_assert(f"state: {linkState}" in out)
        linkState, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget LinkState#2 State")
        linkState = linkState.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link | grep link-id\ 2 -A 20")
        glx_assert(err == '')
        glx_assert(f"state: {linkState}" in out)

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" not in out)

    def test_glx_tunnel_get_stats_from_vpp(self):
        # 由于tunnel未创建link时较默认数据无变动，所以为tunnel创建link
        self.topo.dut1.get_rest_device().create_glx_link(link_id=1, tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=2, tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" in out)
        # 创建tunnel
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" in out)
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2" in out)

        # 等待stats collect读取数据，fwdmd配置文件里默认为10s一次，等待时间需要大于它
        time.sleep(15)
        # 检测redis里数据与vpp是否一致
        tunnelMembers, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#1 Members")
        tunnelMembers = tunnelMembers.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel | grep tunnel-id\ 1 -A 6")
        glx_assert(err == '')
        glx_assert(f"members {tunnelMembers}" in out)
        tunnelMembers, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"redis-cli hget TunnelState#2 Members")
        tunnelMembers = tunnelMembers.rstrip()
        glx_assert(err == '')
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel | grep tunnel-id\ 2 -A 6")
        glx_assert(err == '')
        glx_assert(f"members {tunnelMembers}" in out)

        # 删除link
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 1" not in out)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx link")
        glx_assert(err == '')
        glx_assert(f"link-id 2" not in out)
        # 删除tunnel
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=1)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 1" not in out)
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=2)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx tunnel")
        glx_assert(err == '')
        glx_assert(f"tunnel-id 2" not in out)