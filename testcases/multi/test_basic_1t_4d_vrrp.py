import unittest
import time

from lib.util import glx_assert
from topo.topo_1t_4d import Topo1T4D


# 有时候需要反复测试一个用例，可先打开SKIP_TEARDOWN执行一轮用例初始化
# 拓朴配置，然后打开SKIP_SETUP即可反复执行单个测试例。
#
# TODO: 后面开发active link通知删除能力后，就可以支持用例反复setup down
# 就需要打开setup/teardown，并支持在一个复杂拓朴下，测试多个测试例了。　
#
SKIP_SETUP = False
SKIP_TEARDOWN = False

class Testbasic1T4DVRRP(unittest.TestCase):
    def setUp(self):
        self.topo = Topo1T4D()
        if SKIP_SETUP:
            return
        # 1<>2 192.168.12.0/24
        self.topo.dut1.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.1/24")
        self.topo.dut2.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.12.2/24")
        # 3<>4 192.168.34.0/24
        self.topo.dut3.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.1/24")
        self.topo.dut4.get_rest_device().set_logical_interface_static_ip("WAN1", "192.168.34.2/24")

        # dut1 Lan 1 ip:
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.2/24", mtu=mtu)
        # dut4 Lan 1 ip:
        self.topo.dut4.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.3/24", mtu=mtu)

        # create dut1<>dut2 link.
        self.topo.dut1.get_rest_device().create_glx_tunnel(tunnel_id=12)
        self.topo.dut1.get_rest_device().create_glx_link(link_id=12, wan_name="WAN1",
                                                         remote_ip="192.168.12.2", remote_port=2288,
                                                         tunnel_id=12,
                                                         route_label="0x1200010")

        # create dut3<>dut4 link.
        self.topo.dut4.get_rest_device().create_glx_tunnel(tunnel_id=34)
        self.topo.dut4.get_rest_device().create_glx_link(link_id=34, wan_name="WAN1",
                                                         remote_ip="192.168.34.1", remote_port=2288,
                                                         tunnel_id=34,
                                                         route_label="0x3400010")

        # create dut1 route label policy.
        self.topo.dut1.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x1200010", table_id=0)
        # create dut4 route label pocliy.
        self.topo.dut4.get_rest_device().create_glx_route_label_policy_type_table(route_label="0x3400010", table_id=0)


        # 创建label-fwd表项。
        # to dut4
        self.topo.dut2.get_rest_device().create_glx_route_label_fwd(route_label="0x3400000", tunnel_id1=23)
        # to dut1
        self.topo.dut3.get_rest_device().create_glx_route_label_fwd(route_label="0x1200000", tunnel_id1=23)


        # 判断下if1是不是在dut1上和if2是不是在dut4上
        _, err = self.topo.tst.get_ns_cmd_result("dut1", f"ip link show {self.topo.tst.if1}")
        if err == '':
            self.topo.tst.add_ns_if_to_default_ns("dut1", self.topo.tst.if1)
        _, err = self.topo.tst.get_ns_cmd_result("dut4", f"ip link show {self.topo.tst.if2}")
        if err == '':
            self.topo.tst.add_ns_if_to_default_ns("dut4", self.topo.tst.if2)
        

        # 创建tst网桥
        br_name = "br_dut1_dut4"
        self.topo.tst.add_br(br_name)
        # 给网桥添加ip
        self.topo.tst.add_if_ip(br_name, "192.168.88.1/24")
        # 启用网桥
        self.topo.tst.up_down_if(br_name, True)
        # 将设备加入网桥
        self.topo.tst.add_br_if(br_name, self.topo.tst.if1)
        self.topo.tst.add_br_if(br_name, self.topo.tst.if2)
        # 启用网桥
        self.topo.tst.up_down_if(br_name, True)
        # 增加nat路由
        self.topo.tst.add_route("192.168.12.0/24", "192.168.88.100")
        self.topo.tst.add_route("192.168.34.0/24", "192.168.88.100")

        # 增加bizpol允许流量通过
        self.topo.dut1.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="192.168.12.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       protocol=0,
                                                       direct_enable=True)

        # 增加bizpol允许流量通过
        self.topo.dut4.get_rest_device().create_bizpol(name="bizpol1", priority=1,
                                                       src_prefix="192.168.88.0/24",
                                                       dst_prefix="192.168.34.0/24",
                                                       steering_type=1,
                                                       steering_mode=1,
                                                       steering_interface="WAN1",
                                                       protocol=0,
                                                       direct_enable=True)

        # 等待link up
        # 端口注册时间2s，10s应该都可以了（考虑arp首包丢失也应该可以了）。
        time.sleep(10)

    def tearDown(self):
        if SKIP_TEARDOWN:
            return

        # delete
        self.topo.dut1.get_rest_device().delete_bizpol(name="bizpol1")
        self.topo.dut1.get_rest_device().delete_glx_tunnel(tunnel_id=12)
        self.topo.dut1.get_rest_device().delete_glx_link(link_id=12)
        self.topo.dut1.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x1200010")

        self.topo.dut2.get_vpp_ssh_device().get_cmd_result("pkill nc")
        self.topo.dut2.get_rest_device().delete_port_mapping(logic_if="WAN1")
        # self.topo.dut2.get_rest_device().delete_segment(1)
        self.topo.dut2.get_rest_device().delete_glx_route_label_fwd(route_label="0x3400000")

        self.topo.dut3.get_rest_device().delete_glx_route_label_fwd(route_label="0x1200000")

        self.topo.dut4.get_rest_device().delete_bizpol(name="bizpol1")
        self.topo.dut4.get_rest_device().delete_glx_tunnel(tunnel_id=34)
        self.topo.dut4.get_rest_device().delete_glx_link(link_id=34)
        self.topo.dut4.get_rest_device().delete_glx_route_label_policy_type_table(route_label="0x3400010")



        self.topo.tst.del_route("192.168.12.0/24", "192.168.88.100")
        self.topo.tst.del_route("192.168.34.0/24", "192.168.88.100")

        # 删除tst节点ip（路由内核自动清除）
        # ns不用删除，后面其他用户可能还会用.
        self.topo.tst.up_down_if("br_dut1_dut4", False)
        self.topo.tst.del_br("br_dut1_dut4")
        # make sure to delete it.
        self.topo.tst.del_if("br_dut1_dut4")


        # revert to default.
        mtu = 1500
        self.topo.dut1.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)
        self.topo.dut4.get_rest_device().set_default_bridge_ip_or_mtu("192.168.88.0/24", mtu=mtu)

        # revert to default.
        self.topo.dut1.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut2.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut3.get_rest_device().set_logical_interface_dhcp("WAN1")
        self.topo.dut4.get_rest_device().set_logical_interface_dhcp("WAN1")

        # wait for all passive link to be aged.
        time.sleep(20)
    def test_startup(self):
        vr_id = 51
        vip = "192.168.88.100"
        vmac = "00:00:5e:00:01:33"
        vip_with_prefix = vip+"/32"
        master_priority = 254
        default_priority = 100
        br_name = "default"
        vrrp_name = "default"
        adv_interval = 1
        dut2_wan1 = "192.168.12.2"
        dut3_wan1 = "192.168.34.1"
        master_down_int = int(3*adv_interval+(((256-master_priority)*adv_interval)/256)+1)

        # master
        resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=master_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)

        # backup
        resp = self.topo.dut4.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=default_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)

        # 测试vrrp是否成功
        out, err = self.topo.tst.get_cmd_result(f"ping {vip} -c 5 -i {master_down_int}")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)

        # 测试virtual mac有被学习到
        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show l2fib verbose")
        glx_assert(err == '')
        glx_assert(vmac in out)

        # 测试访问dut2是否能通
        out, err = self.topo.tst.get_cmd_result(f"ping {dut2_wan1} -c 5 -i {master_down_int}")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)

        # 测试dut3是否是不通的
        out, err = self.topo.tst.get_cmd_result(f"ping {dut3_wan1} -c 5 -i {master_down_int}")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)
        self.topo.dut1.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
        self.topo.dut4.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
    def test_master_down(self):
        vr_id = 51
        vip = "192.168.88.100"
        vip_with_prefix = vip + "/32"
        master_priority = 200
        default_priority = 100
        br_name = "default"
        vrrp_name = "default"
        adv_interval = 1
        dut2_wan1 = "192.168.12.2"
        dut3_wan1 = "192.168.34.1"
        vmac = "00:00:5e:00:01:33"
        master_down_int = int(3*adv_interval + (((256-master_priority)*adv_interval) / 256)+ 1)

        # master
        resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=master_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)

        # backup
        resp = self.topo.dut4.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=default_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)


        # 测试流量
        out, err = self.topo.tst.get_cmd_result(f"ping {dut2_wan1} -c 5 -i {master_down_int}")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)

        # 停止dut1 vpp
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl stop vpp")
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl stop fwdmd")
        time.sleep(2)

        master_down_int = int(3*adv_interval + (((256 - default_priority) * adv_interval) / 256)+ 1)
        # 测试dut4是否升主
        out, err = self.topo.tst.get_cmd_result(f"ping {vip} -c 5 -i {master_down_int}")
        
        glx_assert(err == '')
        # 首包会因为arp而丢失，不为０即可
        glx_assert("100% packet loss" not in out)

        # 测试virtual mac有被学习到
        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"vppctl show l2fib verbose")
        glx_assert(err == '')
        glx_assert(vmac in out)

        out, err = self.topo.tst.get_cmd_result(f"ping {dut3_wan1} -c 5 -i {master_down_int}")
        glx_assert(err == '')
        glx_assert("100% packet loss" not in out)

        out, err = self.topo.tst.get_cmd_result(f"ping {dut2_wan1} -c 5 -i {master_down_int}")
        glx_assert(err == '')
        glx_assert("100% packet loss" in out)

        
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl start vpp")
        time.sleep(5)
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl start fwdmd")
        time.sleep(10)
        self.topo.dut1.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
        self.topo.dut4.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
    def test_dns(self):
        vr_id = 51
        vip = "192.168.88.100"
        vip_with_prefix = vip + "/32"
        master_priority = 200
        default_priority = 100
        br_name = "default"
        vrrp_name = "default"
        adv_interval = 1
        dut2_wan1 = "192.168.12.2"
        dut3_wan1 = "192.168.34.1"
        vmac = "00:00:5e:00:01:33"
        master_down_int = int(3*adv_interval + (((256-master_priority)*adv_interval) / 256)+ 1)
        upstream_dns_server = "223.5.5.5"
        dns_setting_name = "default"
        run_path = "/var/run"
        dnsmasq_conf = f"{run_path}/glx_dnsmasq_base_default.conf"
        dnsmasq_dns_conf = f"{run_path}/glx_dnsmasq_dns_default.conf"
        dnsmasq_pid_file = f"{run_path}/glx_dnsmasq_default.pid"
        domain = "www.baidu.com"
        domain_ip = "22.22.22.22"
        ns = "ctrl-ns"


        # 开启dut1 dns服务器
        self.topo.dut1.get_rest_device().set_host_stack_dnsmasq(name=dns_setting_name, start_ip="192.168.88.100", ip_num=8, lease_time="1h", local_dns_server_enable=True, local_dns_server1=upstream_dns_server)
        # 开启dut4 dns服务器
        self.topo.dut4.get_rest_device().set_host_stack_dnsmasq(name=dns_setting_name, start_ip="192.168.88.100", ip_num=8, lease_time="1h", local_dns_server_enable=True, local_dns_server1=upstream_dns_server)


        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"echo 'address=/{domain}/{domain_ip}' >> {dnsmasq_dns_conf}")
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"echo 'address=/{domain}/{domain_ip}' >> {dnsmasq_dns_conf}")

        # 重启dnsmasq
        dut1_dnsmasq_pid, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut1_dnsmasq_pid}")
        glx_assert(err == '')

        dut4_dnsmasq_pid, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut4_dnsmasq_pid}")
        glx_assert(err == '')

        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"dnsmasq -C {dnsmasq_conf}")
        glx_assert(err == '')
        out, err = self.topo.dut4.get_vpp_ssh_device().get_ns_cmd_result(ns, f"dnsmasq -C {dnsmasq_conf}")
        glx_assert(err == '')

        dut1_dnsmasq_pid, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        # master
        resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=master_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)

        # backup
        resp = self.topo.dut4.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=default_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)

        time.sleep(master_down_int)

        out, err = self.topo.tst.get_cmd_result(f"dig @{vip} {domain} +tries=5 +timeout=1")
        glx_assert(err == '')
        glx_assert(domain_ip in out)

        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut1_dnsmasq_pid}")
        glx_assert(err == '')

        # 停止dut1 vpp
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl stop vpp")
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl stop fwdmd")
        time.sleep(2)

        master_down_int = int(3*adv_interval + (((256 - default_priority) * adv_interval) / 256)+ 1)
        # 测试dut4是否升主
        time.sleep(master_down_int)
        out, err = self.topo.tst.get_cmd_result(f"dig @{vip} {domain} +tries=5 +timeout=1")
        glx_assert(err == '')
        glx_assert(domain_ip in out)

        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl start vpp")
        time.sleep(5)
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl start fwdmd")
        time.sleep(10)

        dut4_dnsmasq_pid, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut4_dnsmasq_pid}")
        glx_assert(err == '')

        self.topo.dut1.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
        self.topo.dut1.get_rest_device().delete_host_stack_dnsmasq(name=dns_setting_name)
        self.topo.dut4.get_rest_device().delete_host_stack_dnsmasq(name=dns_setting_name)
        self.topo.dut4.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
        
    def test_dns2(self):
        vr_id = 51
        vip = "192.168.88.100"
        vip_with_prefix = vip + "/32"
        master_priority = 200
        default_priority = 100
        br_name = "default"
        vrrp_name = "default"
        adv_interval = 1
        dut2_wan1 = "192.168.12.2"
        dut3_wan1 = "192.168.34.1"
        vmac = "00:00:5e:00:01:33"
        master_down_int = int(3*adv_interval + (((256-master_priority)*adv_interval) / 256)+ 1)
        upstream_dns_server = "223.5.5.5"
        dns_setting_name = "default"
        domain = "www.baidu.com"
        run_path = "/var/run"
        dnsmasq_conf = f"{run_path}/glx_dnsmasq_base_default.conf"
        dnsmasq_dns_conf = f"{run_path}/glx_dnsmasq_dns_default.conf"
        dnsmasq_pid_file = f"{run_path}/glx_dnsmasq_default.pid"
        domain = "www.baidu.com"
        domain_ip = "22.22.22.22"
        ns = "ctrl-ns"


        # master
        resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=master_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)

        # backup
        resp = self.topo.dut4.get_rest_device().create_vrrp(vip=vip_with_prefix, vr_id=vr_id, bridge=br_name, priority=default_priority, adv_interval=adv_interval)
        glx_assert(201 == resp.status_code)

        # 开启dut1 dns服务器
        self.topo.dut1.get_rest_device().set_host_stack_dnsmasq(name=dns_setting_name, start_ip="192.168.88.100", ip_num=8, lease_time="1h", local_dns_server_enable=True, local_dns_server1=upstream_dns_server)
        # 开启dut4 dns服务器
        self.topo.dut4.get_rest_device().set_host_stack_dnsmasq(name=dns_setting_name, start_ip="192.168.88.100", ip_num=8, lease_time="1h", local_dns_server_enable=True, local_dns_server1=upstream_dns_server)

        self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"echo 'address=/{domain}/{domain_ip}' >> {dnsmasq_dns_conf}")
        self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"echo 'address=/{domain}/{domain_ip}' >> {dnsmasq_dns_conf}")

        # 重启dnsmasq
        dut1_dnsmasq_pid, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut1_dnsmasq_pid}")
        glx_assert(err == '')

        dut4_dnsmasq_pid, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        out, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut4_dnsmasq_pid}")
        glx_assert(err == '')

        out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"dnsmasq -C {dnsmasq_conf}")
        glx_assert(err == '')
        out, err = self.topo.dut4.get_vpp_ssh_device().get_ns_cmd_result(ns, f"dnsmasq -C {dnsmasq_conf}")
        glx_assert(err == '')

        time.sleep(master_down_int)

        out, err = self.topo.tst.get_cmd_result(f"dig @{vip} {domain} +tries=5 +timeout=1")
        glx_assert(err == '')
        glx_assert(domain_ip in out)

        dut1_dnsmasq_pid, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        _, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut1_dnsmasq_pid}")
        glx_assert(err == '')

        # 停止dut1 vpp
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl stop vpp")
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl stop fwdmd")
        time.sleep(2)

        master_down_int = int(3*adv_interval + (((256 - default_priority) * adv_interval) / 256)+ 1)
        # 测试dut4是否升主
        time.sleep(master_down_int)

        out, err = self.topo.tst.get_cmd_result(f"dig @{vip} {domain} +tries=5 +timeout=1")
        glx_assert(err == '')
        glx_assert(domain_ip in out)

        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl start vpp")
        time.sleep(5)
        resp = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"systemctl start fwdmd")
        time.sleep(10)

        dut4_dnsmasq_pid, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"cat {dnsmasq_pid_file}")
        glx_assert(err == '')

        _, err = self.topo.dut4.get_vpp_ssh_device().get_cmd_result(f"kill -9 {dut4_dnsmasq_pid}")
        glx_assert(err == '')

        self.topo.dut1.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
        self.topo.dut1.get_rest_device().delete_host_stack_dnsmasq(name=dns_setting_name)
        self.topo.dut4.get_rest_device().delete_host_stack_dnsmasq(name=dns_setting_name)
        self.topo.dut4.get_rest_device().delete_vrrp(vr_id=vr_id,segment=0)
        






        






