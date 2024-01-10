from cgi import test
import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D


class TestRestVppConsistency1DDynRouting(unittest.TestCase):

    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_01_basic(self):
        source = "fpm-route"
        # check segment exists
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting(segment=1)
        glx_assert(500 == resp.status_code)

        # check fib source is created
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show fib source | grep {source}")
        glx_assert(err == '')
        glx_assert(source in out)

        # check vpp's fib source id is equal to fwdmd's fib source
        fib_src_id, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget FpmRouteSourceContext#{source} ID")
        glx_assert(err == '')
        glx_assert(fib_src_id in out)

        # enable ospf
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting(enableBGP=False)
        glx_assert(201 == resp.status_code)
        time.sleep(1)
        
        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)
        # check daemons are managed by watchfrr
        glx_assert(f"ospfd" in out)
        glx_assert(f"zebra" in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check fpm server is listening 2620 port
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(self.get_ns(), "ss -l -n | grep 2620")
        glx_assert(err == '')
        glx_assert("LISTEN" in out)
        
        # disable ospf but enable bgp
        resp = self.topo.dut1.get_rest_device().update_dynamic_routing_setting(enableOSPF=False)
        glx_assert(200 == resp.status_code)
        time.sleep(1)

        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)
        # check daemons are managed by watchfrr
        glx_assert(f"bgpd" in out)
        glx_assert(f"zebra" in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # enable ospf and enable bgp
        resp = self.topo.dut1.get_rest_device().update_dynamic_routing_setting()
        glx_assert(200 == resp.status_code)
        time.sleep(1)

        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)
        # check daemons are managed by watchfrr
        glx_assert(f"ospfd" in out)
        glx_assert(f"bgpd" in out)
        glx_assert(f"zebra" in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # delete
        resp = self.topo.dut1.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        time.sleep(1)

        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check fpm server is stop
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(self.get_ns(), "ss -l -n | grep 2620")
        glx_assert(err == '')
        glx_assert("LISTEN" not in out)

    def test_02_restart(self):
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting()
        glx_assert(201 == resp.status_code)
        time.sleep(1)

        # when we restart vpp, it should keep the old environment
        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("systemctl restart vpp")
        glx_assert(err == '')
        time.sleep(20)

        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)
        # check daemons are managed by watchfrr
        glx_assert(f"ospfd" in out)
        glx_assert(f"bgpd" in out)
        glx_assert(f"zebra" in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check fpm server
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(self.get_ns(), "ss -l -n | grep 2620")
        glx_assert(err == '')
        glx_assert("LISTEN" in out)

        resp = self.topo.dut1.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        time.sleep(1)

    def test_03_multi_segments(self):
        # segment 0
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting()
        glx_assert(201 == resp.status_code)
        time.sleep(1)

        # segment 1
        resp = self.topo.dut1.get_rest_device().create_segment(segment_id=1)
        glx_assert(201 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().create_dynamic_routing_setting(segment=1)
        glx_assert(201 == resp.status_code)
        time.sleep(1)

        # check segment 0
        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)
        # check daemons are managed by watchfrr
        glx_assert(f"ospfd" in out)
        glx_assert(f"bgpd" in out)
        glx_assert(f"zebra" in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" in out)

        # check fpm server
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(self.get_ns(), "ss -l -n | grep 2620")
        glx_assert(err == '')
        glx_assert("LISTEN" in out)

        # check segment 1
        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" in out)
        # check daemons are managed by watchfrr
        glx_assert(f"ospfd" in out)
        glx_assert(f"bgpd" in out)
        glx_assert(f"zebra" in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" in out)

        # check fpm server
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(self.get_ns(1), "ss -l -n | grep 2620")
        glx_assert(err == '')
        glx_assert("LISTEN" in out)

        resp = self.topo.dut1.get_rest_device().delete_dynamic_routing_setting()
        glx_assert(410 == resp.status_code)
        time.sleep(1)

        resp = self.topo.dut1.get_rest_device().delete_dynamic_routing_setting(segment=1)
        glx_assert(410 == resp.status_code)
        time.sleep(1)


        # check segment 0
        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns()}" not in out)

        # check fpm server is stop
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(self.get_ns(), "ss -l -n | grep 2620")
        glx_assert(err == '')
        glx_assert("LISTEN" not in out)

        # check segment 1
        # check watchfrr process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep watchfrr")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" not in out)

        # check zebra process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep zebra")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" not in out)

        # check bgpd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep bgpd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" not in out)

        # check ospfd process
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("ps aufx | grep ospfd")
        glx_assert(err == '')
        glx_assert(f"-N {self.get_ns(1)}" not in out)

        # check fpm server is stop
        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(self.get_ns(1), "ss -l -n | grep 2620")
        glx_assert(err == '')
        glx_assert("LISTEN" not in out)

        resp = self.topo.dut1.get_rest_device().delete_segment(1)
        glx_assert(410 == resp.status_code)
        
    
    def get_ns(self, segment=0):
        return "ctrl-ns" if segment == 0 else f"ctrl-ns-seg-{segment}"
