import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DFlowstats(unittest.TestCase):
    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_01_validation(self):
        # Segment
        # For now, we only support default segment,so,we need to check non-default segment
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(segment=1)
        glx_assert(500 == resp.status_code)

        # Collector Address
        # Check collector address is empty
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(collector_address="")
        glx_assert(500 == resp.status_code)
        # Check collector address is invalid ip address
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(collector_address="")
        glx_assert(500 == resp.status_code)
        # For now, we only support ip4 address,so,we need to check if collector address is ip6 address
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(collector_address="2001:db7")
        glx_assert(500 == resp.status_code)

        # Collector Src Address
        # Check collector src address is empty
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(collector_src_address="")
        glx_assert(500 == resp.status_code)
        # Check collector src address is invalid ip address
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(collector_src_address="")
        glx_assert(500 == resp.status_code)
        # For now, we only support ip4 address,so,we need to check if collector address is ip6 address
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(collector_src_address="2001:db7")
        glx_assert(500 == resp.status_code)

    def test_02_basic(self):
        # Flowstats configuration can only exist as a single setting.
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting()
        glx_assert(201 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting(name="default2")
        glx_assert(500 == resp.status_code)

        flowstats_input_feature = "glx-flowstats-input-ip4"
        flowstats_output_feature = "glx-flowstats-output-ip4"

        # check segment loop features
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 1 glx4-fib-lookupmiss-dispatch")
        glx_assert(err == '')
        glx_assert(flowstats_input_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 1 glx4-fib-lookupmiss-localnat-dispatch")
        glx_assert(err == '')
        glx_assert(flowstats_input_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 1 glx4-overlay-tx-dispatch")
        glx_assert(err == '')
        glx_assert(flowstats_input_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 5 tunnel-link-rx-routing4-nonacc")
        glx_assert(err == '')
        glx_assert(flowstats_output_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -v 'tunnel-link-rx-routing4-nonacc' | grep -C 5 'tunnel-link-rx-routing4'")
        glx_assert(err == '')
        glx_assert(flowstats_output_feature in out)

        resp = self.topo.dut1.get_rest_device().delete_flowstats_setting()
        glx_assert(410 == resp.status_code)

    def test_03_restart(self):
        # Flowstats configuration can only exist as a single setting.
        resp = self.topo.dut1.get_rest_device().create_flowstats_setting()
        glx_assert(201 == resp.status_code)

        flowstats_input_feature = "glx-flowstats-input-ip4"
        flowstats_output_feature = "glx-flowstats-output-ip4"

        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl restart vpp")
        glx_assert(err == '')
        time.sleep(15)

        # check segment loop features
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 1 glx4-fib-lookupmiss-dispatch")
        glx_assert(err == '')
        glx_assert(flowstats_input_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 1 glx4-fib-lookupmiss-localnat-dispatch")
        glx_assert(err == '')
        glx_assert(flowstats_input_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 1 glx4-overlay-tx-dispatch")
        glx_assert(err == '')
        glx_assert(flowstats_input_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -C 5 tunnel-link-rx-routing4-nonacc")
        glx_assert(err == '')
        glx_assert(flowstats_output_feature in out)

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show int features loop0 | grep -v 'tunnel-link-rx-routing4-nonacc' | grep -C 5 'tunnel-link-rx-routing4'")
        glx_assert(err == '')
        glx_assert(flowstats_output_feature in out)

        resp = self.topo.dut1.get_rest_device().delete_flowstats_setting()
        glx_assert(410 == resp.status_code)
