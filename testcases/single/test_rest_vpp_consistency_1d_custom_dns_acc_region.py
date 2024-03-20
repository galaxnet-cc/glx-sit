import unittest
from lib.util import glx_assert
from topo.topo_1d import Topo1D
from os.path import join
import time

class TestRestVppConsistency1DCustomDnsAccRegion(unittest.TestCase):
    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_01_validation(self):
        # validation
        # region required
        name = "test"
        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name, "", "openai.com", acc_upstream_server1="8.8.8.8")
        glx_assert(500 == resp.status_code)
        # acc domain list required
        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name, "hongkong", "", acc_upstream_server1="8.8.8.8")
        glx_assert(500 == resp.status_code)
        # acc upstream server required
        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name, "hongkong", "openai.com")
        glx_assert(500 == resp.status_code)
        # validate domain list
        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name, "hongkong", "xxxx", acc_upstream_server1="8.8.8.8")
        glx_assert(500 == resp.status_code)
        # validate ip
        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name, "hongkong", "xxxx", acc_upstream_server1="8.8.8")
        glx_assert(500 == resp.status_code)

    def test_02_basic(self):
        # create
        name = "test"
        file_name = "dns_" + name + ".conf"
        region = "hongkong"
        acc_domain_list = "openai.com"
        acc_upstream_server1 = "8.8.8.8"
        acc_upstream_server2 = "1.1.1.1"

        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name, region, acc_domain_list, acc_upstream_server1=acc_upstream_server1)
        glx_assert(201 == resp.status_code)

        cfg_path = "/var/run/glx/dnsmasq/default"

        # check dns configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        glx_assert(file_name in out)

        # check dns configuration format
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat {join(cfg_path, file_name)}")
        glx_assert(err == '')
        glx_assert(f"/openai.com/acc-{region}" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        # update
        acc_domain_list = "openai.com|netflix.com"
        resp = self.topo.dut1.get_rest_device().update_custom_dns_acc_region(name, region, acc_domain_list, acc_upstream_server1=acc_upstream_server1, acc_upstream_server2=acc_upstream_server2)
        glx_assert(200 == resp.status_code)

        # check dns configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        glx_assert(file_name in out)
        
        # check dns configuration format
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat {join(cfg_path, file_name)}")
        glx_assert(err == '')
        glx_assert(f"/openai.com/acc-{region}" in out)
        glx_assert(f"/netflix.com/acc-{region}" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        # delete
        resp = self.topo.dut1.get_rest_device().delete_custom_dns_acc_region(name)
        glx_assert(410 == resp.status_code)
        # check dns configuration not exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        glx_assert(file_name not in out)

    def test_03_multi(self):
        # create
        name1 = "test1"
        name2 = "test2"
        region = "hongkong"
        acc_domain_list = "openai.com"
        acc_upstream_server1 = "8.8.8.8"
        acc_upstream_server2 = "1.1.1.1"

        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name1, region, acc_domain_list, acc_upstream_server1=acc_upstream_server1)
        glx_assert(201 == resp.status_code)

        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name2, region, acc_domain_list, acc_upstream_server1=acc_upstream_server2)
        glx_assert(201 == resp.status_code)

        cfg_path = "/var/run/glx/dnsmasq/default"
        file_name1 = "dns_" + name1 + ".conf"
        file_name2 = "dns_" + name2 + ".conf"

        # check dns configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(file_name1 in out)
        glx_assert(file_name2 in out)

        resp = self.topo.dut1.get_rest_device().delete_custom_dns_acc_region(name1)
        glx_assert(410 == resp.status_code)
        resp = self.topo.dut1.get_rest_device().delete_custom_dns_acc_region(name2)
        glx_assert(410 == resp.status_code)

    def test_04_restart(self):
        # create
        name = "test-restart"
        region = "hongkong"
        acc_domain_list = "openai.com"
        acc_upstream_server1 = "8.8.8.8"
        acc_upstream_server2 = "1.1.1.1"

        resp = self.topo.dut1.get_rest_device().create_custom_dns_acc_region(name, region, acc_domain_list, acc_upstream_server1=acc_upstream_server1)
        glx_assert(201 == resp.status_code)


        cfg_path = "/var/run/glx/dnsmasq/default"
        file_name = "dns_" + name + ".conf"

        # check dns configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        glx_assert(file_name in out)

        
        # check dns configuration format
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat {join(cfg_path, file_name)}")
        glx_assert(err == '')
        glx_assert(f"/openai.com/acc-{region}" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result("systemctl restart vpp")
        glx_assert(err == '')
        # 等待fwdmd配置
        time.sleep(15)

        # check dns configuration exists
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"ls {cfg_path}")
        glx_assert(err == '')
        glx_assert(file_name in out)

        # check dns configuration format
        out, err = self.topo.dut1.get_vpp_ssh_device(
        ).get_cmd_result(f"cat {join(cfg_path, file_name)}")
        glx_assert(err == '')
        glx_assert(f"/openai.com/acc-{region}" in out)
        # check if process exists
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(
            f"ip netns exec ctrl-ns ps -ef | grep dnsmasq")
        glx_assert(err == '')
        glx_assert(f"{cfg_path}/base.conf" in out)

        resp = self.topo.dut1.get_rest_device().delete_custom_dns_acc_region(name)
        glx_assert(410 == resp.status_code)
