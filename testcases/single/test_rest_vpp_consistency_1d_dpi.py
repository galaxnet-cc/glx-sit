import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DDPI(unittest.TestCase):
    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_standalone_mode(self):
        memif_name = "memif0/1"
        glx_memif_ip = "169.254.254.1"
        glx_memif_ip_with_prefix = glx_memif_ip + "/30"
        dpi_memif_ip = "169.254.254.2"
        dpi_memif_ip_with_prefix = dpi_memif_ip + "/30"

        dpi_sock = "/run/vpp/dpi-cli.sock"

        # 基本场景
        resp = self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=True, dpi_standalone=True)
        glx_assert(resp.status_code == 200)

        # fwdmd设置的尝试时间间隔
        time.sleep(5)

        self.check_glx_vpp(memif_name, glx_memif_ip_with_prefix)
        self.check_dpi_vpp(memif_name, dpi_memif_ip_with_prefix, dpi_sock)

        # check memif connection
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl -s {dpi_sock} ping {glx_memif_ip}")
        glx_assert(err == '')
        glx_assert('0% packet loss' in out)

        # 只重启fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart fwdmd")
        glx_assert(err == '')
        time.sleep(10)
        self.check_glx_vpp(memif_name, glx_memif_ip_with_prefix)
        self.check_dpi_vpp(memif_name, dpi_memif_ip_with_prefix, dpi_sock)

        # 重启dpi-vpp和fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart dpi-vpp")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart fwdmd")
        glx_assert(err == '')
        time.sleep(10)
        self.check_glx_vpp(memif_name, glx_memif_ip_with_prefix)
        self.check_dpi_vpp(memif_name, dpi_memif_ip_with_prefix, dpi_sock)

        # 重启vpp和fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart vpp")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart fwdmd")
        glx_assert(err == '')
        time.sleep(10)
        self.check_glx_vpp(memif_name, glx_memif_ip_with_prefix)
        self.check_dpi_vpp(memif_name, dpi_memif_ip_with_prefix, dpi_sock)

        # 重启vpp和dpi-vpp和fwdmd
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart vpp")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart dpi-vpp")
        glx_assert(err == '')
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart fwdmd")
        glx_assert(err == '')
        time.sleep(10)
        self.check_glx_vpp(memif_name, glx_memif_ip_with_prefix)
        self.check_dpi_vpp(memif_name, dpi_memif_ip_with_prefix, dpi_sock)

        # 关闭特性
        resp = self.topo.dut1.get_rest_device().update_dpi_setting(dpi_enable=False, dpi_standalone=False)
        glx_assert(resp.status_code == 200)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl status dpi-vpp")
        glx_assert(err == '')
        glx_assert("inactive" in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int")
        glx_assert(err == '')
        glx_assert(memif_name not in out)


    def check_glx_vpp(self, memif_name, ip):
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show memif {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        # listener
        glx_assert('yes' in out)
        # connected
        glx_assert('connected' in out)
        # glx-vpp state check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        glx_assert('up' in out)
        # glx-vpp ip check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int addr {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        glx_assert(ip in out)
        # glx-vpp ip table
        glx_assert('8190' in out)
        # glx-vpp feature arc check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        glx_assert("glx-dpi-ctrl4" in out)

        # get glx-vpp memif index 
        index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int {memif_name} | grep -E '{memif_name}\s+[0-9]+' | awk '{{print $2}}'")
        glx_assert(err == '')
        glx_assert(index != '')
        # check glx-vpp dpi peer 
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show glx global")
        glx_assert(err == '')
        glx_assert(f"dpi_peer_if {index}" in out)

    def check_dpi_vpp(self, memif_name, ip, sock):
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl -s {sock} show memif {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        # connected
        glx_assert('connected' in out)
        # dpi-vpp state check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl -s {sock} show int {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        glx_assert('up' in out)
        # dpi-vpp ip check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl -s {sock} show int addr {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        glx_assert(ip in out)
        # dpi-vpp feature arc check
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl -s {sock} show int features {memif_name}")
        glx_assert(err == '')
        glx_assert(out != '')
        glx_assert("glx-dpi4-bypass" in out)
        # get dpi-vpp memif index 
        index, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl -s {sock} show int {memif_name} | grep -E '{memif_name}\s+[0-9]+' | awk '{{print $2}}'")
        glx_assert(err == '')
        glx_assert(index != '')
        # dpi-vpp gdpi peer
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl -s {sock} show glx dpi global")
        glx_assert(err == '')
        glx_assert(out != '')
        glx_assert(f"peer interface {index}" in out)
        # dpi-vpp ctrl context
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli exists DpiMgrContext#default")
        glx_assert(err == '')
        glx_assert("1" in out)
