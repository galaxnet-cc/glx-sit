import unittest
import time

from topo.topo_1t_4d import Topo1T4D

# 有时候需要反复测试一个用例，可先打开SKIP_TEARDOWN执行一轮用例初始化
# 拓朴配置，然后打开SKIP_SETUP即可反复执行单个测试例。
#
# TODO: 后面开发active link通知删除能力后，就可以支持用例反复setup down
# 就需要打开setup/teardown，并支持在一个复杂拓朴下，测试多个测试例了。　
#
SKIP_SETUP = False
SKIP_TEARDOWN = False

class TestBasic1T4DGlxNego(unittest.TestCase):

    # 创建一个最基本的配置场景：
    # dut1--wan1(tcp)---dut2---wan3---dut3---wan1--dut4
    #

    def setUp(self):
        self.topo = Topo1T4D()

        if SKIP_SETUP:
            return

        # dut1<->dut2 wan pair 1.
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.2/24")
        # enable dut2 WAN1 tcp listen.
        self.topo.dut2.get_rest_device().set_logical_interface_tcp_listen_enable("WAN1", True)

        # dut1<->dut2 wan pair 2.
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.22.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN2", "192.168.22.2/24")
        # enable dut2 WAN2 tcp listen.
        self.topo.dut2.get_rest_device().set_logical_interface_tcp_listen_enable("WAN2", True)

        # lower the timeout to make testcase not running that long happy
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f'vppctl set glx global passive-link-gc-time 15')
        assert (err == '')


    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_tcp_listen_enable("WAN1", False)

        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN2")
        self.topo.dut2.get_rest_device().set_logical_interface_tcp_listen_enable("WAN2", False)

        # revert the gc time.
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(f'vppctl set glx global passive-link-gc-time 120')
        assert (err == '')

    def test_dut1_2_udp_link(self):
        # create dut1<>dut2 2 udp links.
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0xffffffffffffffff",
                                                         is_tcp=False)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=22, wan_name="WAN2",
                                                         remote_ip="192.168.22.2", remote_port=2288,
                                                         tunnel_id=22,
                                                         route_label="0xffffffffffffffff",
                                                         is_tcp=False)

        # 5s init register timer, so 10s should enough for both link to come up.
        time.sleep(10)

        # verify dut1.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 12,"')
        print(err)
        assert (err == '')
        assert(f'state: active' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 22,"')
        assert (err == '')
        assert(f'state: active' in out)

        # verify dut2.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 12,"')
        assert (err == '')
        assert(f'state: active' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 22,"')
        assert (err == '')
        assert(f'state: active' in out)

        # delete the link.
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=22)

        # we modify the gc time to 15s, sleep 20s to wait all link GCed..
        time.sleep(20)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link')
        assert (err == '')
        assert(f'link-id 12,' not in out)
        assert(f'link-id 22,' not in out)

    def test_dut1_1_udp_1_tcp_link(self):
        # create dut1<>dut2 1 tcp + 1 udp links.
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0xffffffffffffffff",
                                                         is_tcp=True)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=22, wan_name="WAN2",
                                                         remote_ip="192.168.22.2", remote_port=2288,
                                                         tunnel_id=22,
                                                         route_label="0xffffffffffffffff",
                                                         is_tcp=False)

        # 5s init register timer, so 10s should enough for both link to come up.
        # tcp handkshake should not last long in LAN network.
        time.sleep(10)

        # verify dut1.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 12,"')
        print(err)
        assert (err == '')
        assert(f'state: active' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 22,"')
        assert (err == '')
        assert(f'state: active' in out)

        # verify dut2.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 12,"')
        assert (err == '')
        assert(f'state: active' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 22,"')
        assert (err == '')
        assert(f'state: active' in out)

        # delete the link.
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=22)

        # we modify the gc time to 15s, sleep 20s to wait all link GCed..
        time.sleep(20)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link')
        assert (err == '')
        assert(f'link-id 12,' not in out)
        assert(f'link-id 22,' not in out)

    def test_dut1_2_tcp_link(self):
        # create dut1<>dut2 2 tcp links.
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0xffffffffffffffff",
                                                         is_tcp=True)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=22, wan_name="WAN2",
                                                         remote_ip="192.168.22.2", remote_port=2288,
                                                         tunnel_id=22,
                                                         route_label="0xffffffffffffffff",
                                                         is_tcp=True)

        # 5s init register timer, so 10s should enough for both link to come up.
        # tcp handkshake should not last long in LAN network.
        time.sleep(10)

        # verify dut1.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 12,"')
        print(err)
        assert (err == '')
        assert(f'state: active' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 22,"')
        assert (err == '')
        assert(f'state: active' in out)

        # verify dut2.
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 12,"')
        assert (err == '')
        assert(f'state: active' in out)
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link | grep -C 4 "link-id 22,"')
        assert (err == '')
        assert(f'state: active' in out)

        # delete the link.
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=22)

        # we modify the gc time to 15s, sleep 20s to wait all link GCed..
        time.sleep(20)
        out, err = self.topo.dut2.get_vpp_ssh_device().get_cmd_result(
            f'vppctl show glx link')
        assert (err == '')
        assert(f'link-id 12,' not in out)
        assert(f'link-id 22,' not in out)


if __name__ == '__main__':
    unittest.main()
