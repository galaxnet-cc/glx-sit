# 说明：这里定义基于rest api的device，可以实现基于api的管理。
import requests
import json

REQUEST_HEADER_CTYPE = {"Content-Type": "application/json"}

# 此函数将request库的response返回，由测试例自行决定是否要匹配rest api的结果


class RestDevice:
    def __init__(self, api_ip="127.0.0.1", api_port=8080):
        self.api_ip = api_ip
        self.api_port = api_port

    def do_post_request(self, obj_name, obj_data):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/config/{obj_name}'
        response = requests.post(url, data=json.dumps(
            obj_data), headers=REQUEST_HEADER_CTYPE)
        return response

    def do_action_request(self, action_name, action_data):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/action/{action_name}'
        response = requests.post(url, data=json.dumps(
            action_data), headers=REQUEST_HEADER_CTYPE)
        return response

    def do_patch_request(self, obj_name, obj_data):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/config/{obj_name}'
        response = requests.patch(url, data=json.dumps(
            obj_data), headers=REQUEST_HEADER_CTYPE)
        return response

    def do_delete_request(self, obj_name, obj_data):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/config/{obj_name}'
        response = requests.delete(url, data=json.dumps(
            obj_data), headers=REQUEST_HEADER_CTYPE)
        return response

    def do_get_configs_request(self, obj_name, filter=""):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/config/{obj_name}s'
        if filter != "":
            url = url + "?" + filter
        response = requests.get(url, headers=REQUEST_HEADER_CTYPE)
        return response

    def do_get_states_request(self, obj_name, filter=""):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/state/{obj_name}s'
        if filter != "":
            url = url + "?" + filter
        response = requests.get(url, headers=REQUEST_HEADER_CTYPE)
        return response

    def update_physical_interface(self, name, mtu, mode, bridgeName):
        physical_interface_data = {}
        physical_interface_data["Name"] = name
        physical_interface_data["Mtu"] = mtu
        physical_interface_data["Mode"] = mode
        physical_interface_data["BridgeName"] = bridgeName
        return self.do_patch_request("PhysicalInterface", physical_interface_data)

    def delete_host_stack_dnsmasq(self, name):
        host_stack_dnsmasq_data = {}
        host_stack_dnsmasq_data['Name'] = name
        return self.do_delete_request("DhcpAndDnsSettings", host_stack_dnsmasq_data)

    def update_host_stack_dnsmasq(self, name, start_ip, ip_num, lease_time, acc_dns_server1="", acc_dns_server2="", local_dns_server1="", local_dns_server2="", net_mask="255.255.255.0", acc_domain_list="", local_domain_list="", dhcp_enable=False, local_dns_server_enable=False, options=[]):
        host_stack_dnsmasq_data = {}
        host_stack_dnsmasq_data['Name'] = name
        host_stack_dnsmasq_data['StartIP'] = start_ip
        host_stack_dnsmasq_data['IPNum'] = ip_num
        host_stack_dnsmasq_data['NetMask'] = net_mask
        host_stack_dnsmasq_data['LeaseTIme'] = lease_time
        host_stack_dnsmasq_data['AccUpstreamDnsServer1'] = acc_dns_server1
        host_stack_dnsmasq_data['AccUpstreamDnsServer2'] = acc_dns_server2
        host_stack_dnsmasq_data['LocalUpstreamDnsServer1'] = local_dns_server1
        host_stack_dnsmasq_data['LocalUpstreamDnsServer2'] = local_dns_server2
        host_stack_dnsmasq_data['AccDomainList'] = acc_domain_list
        host_stack_dnsmasq_data['LocalDomainList'] = local_domain_list
        host_stack_dnsmasq_data['DhcpEnable'] = dhcp_enable
        host_stack_dnsmasq_data['LocalDnsServerEnable'] = local_dns_server_enable
        host_stack_dnsmasq_data['Options'] = options
        return self.do_patch_request("DhcpAndDnsSettings", host_stack_dnsmasq_data)

    def set_host_stack_dnsmasq(self, name, start_ip, ip_num, lease_time, acc_dns_server1="", acc_dns_server2="", local_dns_server1="", local_dns_server2="", net_mask="255.255.255.0", acc_domain_list="", local_domain_list="", dhcp_enable=False, local_dns_server_enable=False, options=[]):
        host_stack_dnsmasq_data = {}
        host_stack_dnsmasq_data['Name'] = name
        host_stack_dnsmasq_data['StartIP'] = start_ip
        host_stack_dnsmasq_data['IPNum'] = ip_num
        host_stack_dnsmasq_data['LeaseTIme'] = lease_time
        host_stack_dnsmasq_data['AccUpstreamDnsServer1'] = acc_dns_server1
        host_stack_dnsmasq_data['AccUpstreamDnsServer2'] = acc_dns_server2
        host_stack_dnsmasq_data['LocalUpstreamDnsServer1'] = local_dns_server1
        host_stack_dnsmasq_data['LocalUpstreamDnsServer2'] = local_dns_server2
        host_stack_dnsmasq_data['AccDomainList'] = acc_domain_list
        host_stack_dnsmasq_data['LocalDomainList'] = local_domain_list
        host_stack_dnsmasq_data['DhcpEnable'] = dhcp_enable
        host_stack_dnsmasq_data['LocalDnsServerEnable'] = local_dns_server_enable
        host_stack_dnsmasq_data['Options'] = options
        return self.do_post_request("DhcpAndDnsSettings", host_stack_dnsmasq_data)

    def delete_fire_wall_rule(self, rule_name, segment=0):
        rule_data = {}
        rule_data['Segment'] = segment
        rule_data['Name'] = rule_name
        return self.do_delete_request("FirewallRule", rule_data)

    def update_fire_wall_rule(self, rule_name, priority, dest_address, action, app_id=65535, segment=0,
                              src_addr_group="", dst_addr_group="", src_port_group="", dst_port_group="",protocol=0):
        rule_data = {}
        rule_data['Segment'] = segment
        rule_data['Name'] = rule_name
        rule_data['Priority'] = priority
        rule_data['SrcAddressWithPrefix'] = "0.0.0.0/0"
        rule_data['DstAddressWithPrefix'] = dest_address
        rule_data['Action'] = action
        rule_data['L4Protocol'] = protocol
        rule_data['AppId'] = app_id
        rule_data["SrcAddrGroup"] = src_addr_group
        rule_data["DstAddrGroup"] = dst_addr_group
        rule_data["SrcPortGroup"] = src_port_group
        rule_data["DstPortGroup"] = dst_port_group
        return self.do_patch_request("FirewallRule", rule_data)

    def set_fire_wall_rule(self, rule_name, priority, dest_address, action, app_id=65535, segment=0,
                           src_addr_group="", dst_addr_group="", src_port_group="", dst_port_group="", protocol=0):
        rule_data = {}
        rule_data['Segment'] = segment
        rule_data['Name'] = rule_name
        rule_data['Priority'] = priority
        rule_data['SrcAddressWithPrefix'] = "0.0.0.0/0"
        rule_data['DstAddressWithPrefix'] = dest_address
        rule_data['Action'] = action
        rule_data['L4Protocol'] = protocol
        rule_data['AppId'] = app_id
        rule_data["SrcAddrGroup"] = src_addr_group
        rule_data["DstAddrGroup"] = dst_addr_group
        rule_data["SrcPortGroup"] = src_port_group
        rule_data["DstPortGroup"] = dst_port_group
        return self.do_post_request("FirewallRule", rule_data)

    def set_logical_interface_segment(self, name, segment_id):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['Segment'] = segment_id
        return self.do_patch_request("LogicalInterface", logif_data)

    def set_logical_interface_static_ip(self, name, ip_w_prefix):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['AddressingType'] = "STATIC"
        logif_data['StaticIpAddrWithPrefix'] = ip_w_prefix
        return self.do_patch_request("LogicalInterface", logif_data)

    # ip+gw同时设置
    def set_logical_interface_static_ip_gw(self, name, ip_w_prefix, gw_ip):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['AddressingType'] = "STATIC"
        logif_data['StaticIpAddrWithPrefix'] = ip_w_prefix
        logif_data['StaticGWIpAddr'] = gw_ip
        return self.do_patch_request("LogicalInterface", logif_data)


    def set_logical_interface_static_gw(self, name, gw_ip):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['AddressingType'] = "STATIC"
        logif_data['StaticGWIpAddr'] = gw_ip
        return self.do_patch_request("LogicalInterface", logif_data)

    # default mode.
    def set_logical_interface_dhcp(self, name):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['AddressingType'] = "DHCP"
        return self.do_patch_request("LogicalInterface", logif_data)

    def set_logical_interface_pppoe(self, name, pppoe_user, pppoe_password):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['AddressingType'] = "PPPOE"
        logif_data['PppoeUsername'] = pppoe_user
        logif_data['PppoePassword'] = pppoe_password
        return self.do_patch_request("LogicalInterface", logif_data)

    def set_logical_interface_nat_direct(self, name, nat_direct_enable):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['NatDirectEnable'] = nat_direct_enable
        return self.do_patch_request("LogicalInterface", logif_data)

    def set_logical_interface_unspec(self, name):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['AddressingType'] = "UNSPEC"
        return self.do_patch_request("LogicalInterface", logif_data)

    def set_logical_interface_overlay_enable(self,name,overlay_enable):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['OverlayEnable'] = overlay_enable
        return self.do_patch_request("LogicalInterface",logif_data)

    def set_logical_interface_tcp_listen_enable(self,name, tcp_listen_enable):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['TcpListenEnable'] = tcp_listen_enable
        return self.do_patch_request("LogicalInterface",logif_data)

    def set_logical_interface_one_arm_mode_enable(self,name, enable):
        logif_data = {}
        logif_data['Name'] = name
        logif_data['OneArmModeEnable'] = enable
        return self.do_patch_request("LogicalInterface",logif_data)

    def set_logical_interface_additional_ips(self, name, add_ip1="", add_ip2=""):
        logif_data = {}
        logif_data['Name'] = name
        logif_data["AdditionalIps"] = []
        if add_ip1 != "":
            logif_data["AdditionalIps"].append({"IpAddr": add_ip1})
        if add_ip2 != "":
            logif_data["AdditionalIps"].append({"IpAddr": add_ip2})
        return self.do_patch_request("LogicalInterface", logif_data)
    
    def delete_logical_interface_additional_ips(self, name):
        logif_data = {}
        logif_data['Name'] = name
        logif_data["AdditionalIps"] = []
        return self.do_patch_request("LogicalInterface", logif_data)

    def delete_bridge(self, name):
        bridge_data = {}
        bridge_data['Name'] = name
        return self.do_delete_request("Bridge", bridge_data)

    def update_bridge_ip_or_mtu(self, name, bvi_ip_w_prefix, mtu=1500):
        bridge_data = {}
        bridge_data['Name'] = name
        bridge_data['BviEnable'] = True
        bridge_data['BviIpAddrWithPrefix'] = bvi_ip_w_prefix
        bridge_data['Mtu'] = mtu
        return self.do_patch_request("Bridge", bridge_data)

    def create_bridge(self, name, bvi_ip_w_prefix, mtu=1500):
        bridge_data = {}
        bridge_data['Name'] = name
        bridge_data['BviEnable'] = True
        bridge_data['Mtu'] = mtu
        bridge_data['BviIpAddrWithPrefix'] = bvi_ip_w_prefix
        return self.do_post_request("Bridge", bridge_data)

    def set_default_bridge_ip_or_mtu(self, bvi_ip_w_prefix, mtu=1500):
        bridge_data = {}
        bridge_data['Name'] = "default"
        bridge_data['BviEnable'] = True
        bridge_data['Mtu'] = mtu
        bridge_data['BviIpAddrWithPrefix'] = bvi_ip_w_prefix
        return self.do_patch_request("Bridge", bridge_data)

    def create_glx_link(self, link_id, wan_name="WAN1", remote_ip="127.0.0.1", remote_port=2288, tunnel_id=0, route_label="0xffffffffff", is_tcp=False, no_encryption=False, tag1="", tag2=""):
        link_data = {}
        link_data['LinkId'] = link_id
        link_data['LocalWanName'] = wan_name
        link_data['RemoteIp'] = remote_ip
        link_data['RemotePort'] = remote_port
        link_data['TunnelId'] = tunnel_id
        link_data['RouteLabel'] = route_label
        link_data['IsTcp'] = is_tcp
        link_data['NoEncryption'] = no_encryption
        link_data['Tag1'] = tag1
        link_data['Tag2'] = tag2
        return self.do_post_request("Link", link_data)

    def update_glx_link(self, link_id, qos_level=0):
        link_data = {}
        link_data['LinkId'] = link_id
        link_data['QosLevel'] = qos_level
        return self.do_patch_request("Link", link_data)

    def delete_glx_link(self, link_id):
        link_data = {}
        link_data['LinkId'] = link_id
        return self.do_delete_request("Link", link_data)

    # https://github.com/galaxnet-cc/fwdmd/issues/110
    # 移除passive参数，只能创建active的　
    def create_glx_tunnel(self, tunnel_id, tag1="", tag2=""):
        tunnel_data = {}
        tunnel_data['TunnelId'] = tunnel_id
        tunnel_data['Tag1'] = tag1
        tunnel_data['Tag2'] = tag2
        return self.do_post_request("Tunnel", tunnel_data)

    def delete_glx_tunnel(self, tunnel_id):
        tunnel_data = {}
        tunnel_data['TunnelId'] = tunnel_id
        return self.do_delete_request("Tunnel", tunnel_data)

    def create_glx_route_label_policy_type_table(self, route_label, table_id=0):
        label_data = {}
        label_data["RouteLabel"] = route_label
        label_data["Type"] = 0
        # TableID field is now deprecated.
        #label_data["TableID"] = table_id
        return self.do_post_request("RouteLabelPolicy", label_data)

    def delete_glx_route_label_policy_type_table(self, route_label):
        label_data = {}
        label_data["RouteLabel"] = route_label
        return self.do_delete_request("RouteLabelPolicy", label_data)

    def create_glx_route_label_policy_type_tunnel(self, route_label, tunnel_id=1):
        label_data = {}
        label_data["RouteLabel"] = route_label
        label_data["Type"] = 1
        tunnels = []
        # 仅支持单个tunnel
        tunnels.append(
            {"TunnelId": tunnel_id, "TunnelWeight": 100, "TunnelPriority": 100})
        label_data["NexthopTunnels"] = tunnels
        return self.do_post_request("RouteLabelPolicy", label_data)

    def delete_glx_route_label_policy_type_tunnel(self, route_label):
        label_data = {}
        label_data["RouteLabel"] = route_label
        return self.do_delete_request("RouteLabelPolicy", label_data)

    def create_glx_route_label_fwd(self, route_label, tunnel_id1, tunnel_id2=None):
        label_data = {}
        label_data["RouteLabel"] = route_label
        tunnels = []
        # support tunnel weight later.
        tunnels.append(
            {"TunnelId": tunnel_id1, "TunnelWeight": 100, "TunnelPriority": 100})
        if tunnel_id2 != None:
            tunnels.append(
                {"TunnelId": tunnel_id2, "TunnelWeight": 100, "TunnelPriority": 100})
        label_data["NexthopTunnels"] = tunnels
        return self.do_post_request("RouteLabelFwdEntry", label_data)

    def delete_glx_route_label_fwd(self, route_label):
        label_data = {}
        label_data["RouteLabel"] = route_label
        return self.do_delete_request("RouteLabelFwdEntry", label_data)

    def create_glx_edge_route_label_fwd(self, route_label, tunnel_id1, tunnel_id2=None):
        label_data = {}
        label_data["RouteLabel"] = route_label
        label_data["IsDefault"] = False
        tunnels = []
        # support tunnel weight later.
        tunnels.append(
            {"TunnelId": tunnel_id1, "TunnelWeight": 100, "TunnelPriority": 100})
        if tunnel_id2 != None:
            tunnels.append(
                {"TunnelId": tunnel_id2, "TunnelWeight": 100, "TunnelPriority": 100})
        label_data["NexthopTunnels"] = tunnels
        return self.do_post_request("EdgeRouteLabelFwdEntry", label_data)

    def update_glx_edge_route_label_fwd(self, route_label, tunnel_id1, tunnel_id2=None):
        label_data = {}
        label_data["RouteLabel"] = route_label
        label_data["IsDefault"] = False
        tunnels = []
        # support tunnel weight later.
        if tunnel_id1 != None:
            tunnels.append(
                {"TunnelId": tunnel_id1, "TunnelWeight": 100, "TunnelPriority": 100})
        if tunnel_id2 != None:
            tunnels.append(
                {"TunnelId": tunnel_id2, "TunnelWeight": 100, "TunnelPriority": 100})
        label_data["NexthopTunnels"] = tunnels
        return self.do_patch_request("EdgeRouteLabelFwdEntry", label_data)

    def update_glx_default_edge_route_label_fwd(self, tunnel_id1, tunnel_id2=None):
        label_data = {}
        label_data["RouteLabel"] = "0"
        label_data["IsDefault"] = True
        tunnels = []
        # support tunnel weight later.
        # We may update tunnel id1 too.
        if tunnel_id1 != None:
            tunnels.append(
                {"TunnelId": tunnel_id1, "TunnelWeight": 100, "TunnelPriority": 100})
        if tunnel_id2 != None:
            tunnels.append(
                {"TunnelId": tunnel_id2, "TunnelWeight": 100, "TunnelPriority": 100})
        label_data["NexthopTunnels"] = tunnels
        return self.do_patch_request("EdgeRouteLabelFwdEntry", label_data)

    def delete_glx_edge_route_label_fwd(self, route_label):
        label_data = {}
        label_data["RouteLabel"] = route_label
        return self.do_delete_request("EdgeRouteLabelFwdEntry", label_data)

    def create_edge_route(self, route_prefix, route_label, route_protocol="overlay", is_acc=False, is_acc_reverse=False, segment=0, tag1="", tag2="",
                          next_hop_ip=""):
        route_data = {}
        route_data["Segment"] = segment
        route_data["DestPrefix"] = route_prefix
        route_data["RouteProtocol"] = route_protocol
        if route_protocol == "static":
            # 当前仅支持ip模式
            route_data["NexthopType"] = "ip"
            route_data["NexthopIp"] = next_hop_ip
        route_data["RouteLabel"] = route_label
        route_data["IsAcc"] = is_acc
        route_data["IsAccReverse"] = is_acc_reverse
        route_data['Tag1'] = tag1
        route_data['Tag2'] = tag2
        return self.do_post_request("EdgeRoute", route_data)

    def delete_edge_route(self, route_prefix, route_protocol="overlay", segment=0, is_acc=False):
        route_data = {}
        route_data["Segment"] = segment
        route_data["DestPrefix"] = route_prefix
        route_data["RouteProtocol"] = route_protocol
        route_data["IsAcc"] = is_acc
        return self.do_delete_request("EdgeRoute", route_data)

    def create_bizpol(self, name, priority, src_prefix, dst_prefix, protocol, app_id=65535,
                      direct_enable=False,
                      steering_type=0, steering_mode=0, steering_interface="",
                      overlay_enable=False, acc_enable=False, route_label="0xffffffffff",
                      src_addr_group="", dst_addr_group="", src_port_group="", dst_port_group="",
                      src_port_first=0, src_port_last=65535,
                      dst_port_first=0, dst_port_last=65535,
                      sched_class="",
                      tag1="", tag2="",
                      segment=0,
                      qos_level=0,
                      rate_limit_enable=False,up_rate_limit=0,down_rate_limit=0, rate_burst=0):
        bizpol_data = {}
        bizpol_data["Segment"] = segment
        bizpol_data["Name"] = name
        bizpol_data["Priority"] = priority
        bizpol_data["SrcAddressWithPrefix"] = src_prefix
        bizpol_data["DstAddressWithPrefix"] = dst_prefix
        bizpol_data["L4Protocol"] = protocol
        bizpol_data["DirectEnable"] = direct_enable
        bizpol_data["SteeringType"] = steering_type
        bizpol_data["SteeringMode"] = steering_mode
        bizpol_data["SteeringInterface"] = steering_interface
        bizpol_data["AppId"] = app_id
        bizpol_data["OverlayEnable"] = overlay_enable
        bizpol_data["AccEnable"] = acc_enable
        bizpol_data["RouteLabelOverride"] = route_label
        bizpol_data["SrcAddrGroup"] = src_addr_group
        bizpol_data["DstAddrGroup"] = dst_addr_group
        bizpol_data["SrcPortGroup"] = src_port_group
        bizpol_data["DstPortGroup"] = dst_port_group
        bizpol_data["L4SourcePortOrICMPTypeFirst"] = src_port_first
        bizpol_data["L4SourcePortOrICMPTypeLast"] = src_port_last
        bizpol_data["L4DestPortOrICMPCodeFirst"] = dst_port_first
        bizpol_data["L4DestPortOrICMPCodeLast"] = dst_port_last
        bizpol_data["SchedClass"] = sched_class
        bizpol_data['Tag1'] = tag1
        bizpol_data['Tag2'] = tag2
        bizpol_data['QosLevel'] = qos_level
        bizpol_data['RateLimitEnable'] = rate_limit_enable
        bizpol_data['UpRateLimit'] = up_rate_limit
        bizpol_data['DownRateLimit'] = down_rate_limit
        bizpol_data['RateBurst'] = rate_burst
        return self.do_post_request("BusinessPolicy", bizpol_data)

    def update_bizpol(self, name, priority, src_prefix, dst_prefix, protocol, app_id=65535,
                      direct_enable=False,
                      steering_type=0, steering_mode=0, steering_interface="",
                      overlay_enable=False, acc_enable=False, route_label="0xffffffffff",
                      src_addr_group="", dst_addr_group="", src_port_group="", dst_port_group="",
                      src_port_first=0, src_port_last=65535,
                      dst_port_first=0, dst_port_last=65535,
                      sched_class="",
                      tag1="", tag2="",
                      segment=0,
                      qos_level=0,
                      rate_limit_enable=False,up_rate_limit=0,down_rate_limit=0, rate_burst=0):
        bizpol_data = {}
        bizpol_data["Segment"] = segment
        bizpol_data["Name"] = name
        bizpol_data["Priority"] = priority
        bizpol_data["SrcAddressWithPrefix"] = src_prefix
        bizpol_data["DstAddressWithPrefix"] = dst_prefix
        bizpol_data["L4Protocol"] = protocol
        bizpol_data["DirectEnable"] = direct_enable
        bizpol_data["SteeringType"] = steering_type
        bizpol_data["SteeringMode"] = steering_mode
        bizpol_data["SteeringInterface"] = steering_interface
        bizpol_data["AppId"] = app_id
        bizpol_data["OverlayEnable"] = overlay_enable
        bizpol_data["AccEnable"] = acc_enable
        bizpol_data["RouteLabelOverride"] = route_label
        bizpol_data["SrcAddrGroup"] = src_addr_group
        bizpol_data["DstAddrGroup"] = dst_addr_group
        bizpol_data["SrcPortGroup"] = src_port_group
        bizpol_data["DstPortGroup"] = dst_port_group
        bizpol_data["L4SourcePortOrICMPTypeFirst"] = src_port_first
        bizpol_data["L4SourcePortOrICMPTypeLast"] = src_port_last
        bizpol_data["L4DestPortOrICMPCodeFirst"] = dst_port_first
        bizpol_data["L4DestPortOrICMPCodeLast"] = dst_port_last
        bizpol_data["SchedClass"] = sched_class
        bizpol_data['Tag1'] = tag1
        bizpol_data['Tag2'] = tag2
        bizpol_data['QosLevel'] = qos_level
        bizpol_data['RateLimitEnable'] = rate_limit_enable
        bizpol_data['UpRateLimit'] = up_rate_limit
        bizpol_data['DownRateLimit'] = down_rate_limit
        bizpol_data['RateBurst'] = rate_burst
        return self.do_patch_request("BusinessPolicy", bizpol_data)

    def delete_bizpol(self, name, segment=0):
        bizpol_data = {}
        bizpol_data["Segment"] = segment
        bizpol_data["Name"] = name
        return self.do_delete_request("BusinessPolicy", bizpol_data)


    #  areas is an object list, only key in object supported now is AreaId(int)
    def create_ospf_setting(self, segment=0, overlayAdvertiseEnable=False, areas=[]):
        ospf_data = {}
        ospf_data["Segment"] = segment
        ospf_data["OverlayAdvertiseEnable"] = overlayAdvertiseEnable
        ospf_data["Areas"] = areas
        return self.do_post_request("OspfSetting", ospf_data)

    def delete_ospf_setting(self, segment=0):
        ospf_data = {}
        ospf_data["Segment"] = segment
        return self.do_delete_request("OspfSetting", ospf_data)

    def create_ospf_interface(self, interface, areaId):
        ospf_interface_data = {}
        ospf_interface_data["Interface"] = interface
        ospf_interface_data["AreaId"] = areaId
        return self.do_post_request("OspfInterface", ospf_interface_data)

    def delete_ospf_interface(self, interface, areaId):
        ospf_interface_data = {}
        ospf_interface_data["Interface"] = interface
        ospf_interface_data["AreaId"] = areaId
        return self.do_delete_request("OspfInterface", ospf_interface_data)

    def create_overlay_traffic_limit(self, tx_limit, rx_limit, is_combined):
        data = {}
        data["Segment"] = 0
        data["TxLimit"] = tx_limit
        data["RxLimit"] = rx_limit
        data["TxRxCombined"] = is_combined
        return self.do_post_request("OverlayTrafficLimit", data)

    def update_overlay_traffic_limit(self, tx_limit, rx_limit, is_combined):
        data = {}
        data["Segment"] = 0
        data["TxLimit"] = tx_limit
        data["RxLimit"] = rx_limit
        data["TxRxCombined"] = is_combined
        return self.do_patch_request("OverlayTrafficLimit", data)

    def delete_overlay_traffic_limit(self):
        data = {}
        data["Segment"] = 0
        return self.do_delete_request("OverlayTrafficLimit", data)

    def update_config_action(self, data):
        return self.do_action_request("UpdateConfig", data)

    def create_segment(self, segment_id, tag1="", tag2=""):
        data = {}
        data["Id"] = segment_id
        data["Tag1"] = tag1
        data["Tag2"] = tag2
        return self.do_post_request("Segment", data)

    def update_segment(self, segment_id, acc_enable=False, int_edge_enable=False, dns_intercept_enable=False,
                       dns_ip_collect_enable=False,dns_ip_collect_timeout=0, route_label="0xffffffffffffffff",
                       tag1="", tag2="",
                       min_qos_level=0, max_qos_level=7):
        data = {}
        data["Id"] = segment_id
        data["AccEnable"] = acc_enable
        data["IntEdgeEnable"] = int_edge_enable
        data["DnsInterceptEnable"] = dns_intercept_enable
        data["DnsIpCollectEnable"] = dns_ip_collect_enable
        data["DnsIpCollectTimeout"] = dns_ip_collect_timeout
        data["AccRouteLabel"] = route_label
        data["Tag1"] = tag1
        data["Tag2"] = tag2
        data["MinQosLevel"] = min_qos_level
        data["MaxQosLevel"] = max_qos_level
        return self.do_patch_request("Segment", data)

    def delete_segment(self, segment_id):
        data = {}
        data["Id"] = segment_id
        return self.do_delete_request("Segment", data)

    def create_segment_acc_prop(self, segment_id, batch_route_file_path="", acc_ip1="1.1.1.1", acc_fib_type=""):
        data = {}
        data["Segment"] = segment_id
        data["AccIps"] = []
        data["AccIps"].append({"Ip4Address": acc_ip1})
        data["BatchRouteFilePath"] = batch_route_file_path
        data["BatchRouteFibType"] = acc_fib_type
        return self.do_post_request("SegmentAccProperties", data)

    def update_segment_acc_prop_accip(self, segment_id, acc_ip1="1.1.1.1"):
        data = {}
        data["Segment"] = segment_id
        data["AccIps"] = []
        data["AccIps"].append({"Ip4Address": acc_ip1})
        return self.do_patch_request("SegmentAccProperties", data)

    def delete_segment_acc_prop(self, segment_id):
        data = {}
        data["Segment"] = segment_id
        return self.do_delete_request("SegmentAccProperties", data)

    def update_segment_acc_prop(self, segment_id, batch_route_file_path="", acc_ip1="1.1.1.1", acc_fib_type=""):
        data = {}
        data["Segment"] = segment_id
        data["AccIps"] = []
        data["AccIps"].append({"Ip4Address": acc_ip1})
        data["BatchRouteFilePath"] = batch_route_file_path
        data["BatchRouteFibType"] = acc_fib_type
        return self.do_patch_request("SegmentAccProperties", data)

    def create_segment_prop(self, segment_id, ip1="1.1.1.1"):
        data = {}
        data["Segment"] = segment_id
        data["E2EIps"] = []
        data["E2EIps"].append({"Ip4Address": ip1})
        return self.do_post_request("SegmentProperties", data)

    def delete_segment_prop(self, segment_id):
        data = {}
        data["Segment"] = segment_id
        return self.do_delete_request("SegmentProperties", data)

    def update_segment_prop(self, segment_id, ip1="3.3.3.3"):
        data = {}
        data["Segment"] = segment_id
        data["E2EIps"] = []
        data["E2EIps"].append({"Ip4Address": ip1})
        return self.do_patch_request("SegmentProperties", data)

    def update_dpi_setting(self, dpi_enable=False):
        data = {}
        data["Name"] = "default"
        data["DpiEnable"] = dpi_enable
        return self.do_patch_request("DpiSetting", data)

    def create_l3subif(self, physical_interface, sub_id, vlan_id):
        l3subif_data = {}
        l3subif_data['PhysicalInterface'] = physical_interface
        l3subif_data['SubId'] = sub_id
        l3subif_data['VlanId'] = vlan_id
        l3subif_data['Type'] = "dot1q"
        return self.do_post_request("L3SubInterface", l3subif_data)

    def delete_l3subif(self, physical_interface, sub_id):
        l3subif_data = {}
        l3subif_data['PhysicalInterface'] = physical_interface
        l3subif_data['SubId'] = sub_id
        return self.do_delete_request("L3SubInterface", l3subif_data)

    def create_port_mapping(self, logic_if, external_port=7777, protocol="tcp", segment=0, internal_addr="169.254.100.2", internal_port=7777):
        data = {}
        data['Interface'] = logic_if
        data['ExternalPort'] = external_port
        data['Protocol'] = protocol
        data['Segment'] = segment
        data['InternalAddr'] = internal_addr
        data['InternalPort'] = internal_port
        return self.do_post_request("PortMapping", data)

    def update_port_mapping(self, logic_if, external_port=7777, protocol="tcp", segment=0, internal_addr="169.254.100.2", internal_port=7777):
        data = {}
        data['Interface'] = logic_if
        data['ExternalPort'] = external_port
        data['Protocol'] = protocol
        data['Segment'] = segment
        data['InternalAddr'] = internal_addr
        data['InternalPort'] = internal_port
        return self.do_patch_request("PortMapping", data)

    def delete_port_mapping(self, logic_if, external_port=7777, protocol="tcp"):
        data = {}
        data['Interface'] = logic_if
        data['ExternalPort'] = external_port
        data['Protocol'] = protocol
        return self.do_delete_request("PortMapping", data)

    def delete_route_action(self, is_all=False, segment_id=0):
        data={}
        data["IsAll"] = is_all
        data["Segment"] = segment_id
        return self.do_action_request("BatchRouteFlush", data)

    def create_addr_group(self, group_name, addr_with_prefix1):
        data = {}
        data['AddrGroupName'] = group_name
        data['AddrGroupMembers'] = []
        data['AddrGroupMembers'].append({"IpAddrWithPrefix": addr_with_prefix1})
        return self.do_post_request("AddrGroup", data)

    def update_addr_group(self, group_name, addr_with_prefix1):
        data = {}
        data['AddrGroupName'] = group_name
        data['AddrGroupMembers'] = []
        data['AddrGroupMembers'].append({"IpAddrWithPrefix": addr_with_prefix1})
        return self.do_patch_request("AddrGroup", data)

    def delete_addr_group(self, group_name):
        data = {}
        data['AddrGroupName'] = group_name
        return self.do_delete_request("AddrGroup", data)

    def create_port_group(self, group_name, protocol1, port_list1):
        data = {}
        data['PortGroupName'] = group_name
        data['PortGroupMembers'] = []
        data['PortGroupMembers'].append({"ProtocolType": protocol1,
                                         "PortList": port_list1})
        return self.do_post_request("PortGroup", data)

    def update_port_group(self, group_name, protocol1, port_list1):
        data = {}
        data['PortGroupName'] = group_name
        data['PortGroupMembers'] = []
        data['PortGroupMembers'].append({"ProtocolType": protocol1,
                                         "PortList": port_list1})
        return self.do_patch_request("PortGroup", data)

    def delete_port_group(self, group_name):
        data = {}
        data['PortGroupName'] = group_name
        return self.do_delete_request("PortGroup", data)

    # bw unit is in kbps, default 10Mbps
    def update_sched_wan_agg_global_params(self,
                                           tx_enable=False,
                                           tx_agg_bw=10000,
                                           tx_critical_bw=2000,
                                           tx_high_bw=4000,
                                           tx_normal_bw=3000,
                                           tx_low_bw=1000,
                                           rx_enable=False,
                                           rx_agg_bw=10000,
                                           rx_critical_bw=2000,
                                           rx_high_bw=4000,
                                           rx_normal_bw=3000,
                                           rx_low_bw=1000):
        data = {}
        # 使用默认名称
        data["Name"] = "default"
        data["TxEnable"] = tx_enable
        data["TxAggregateBandwidth"] = tx_agg_bw
        data["TxCriticalSchedClassBandwidth"] = tx_critical_bw
        data["TxHighSchedClassBandwidth"] = tx_high_bw
        data["TxNormalSchedClassBandwidth"] = tx_normal_bw
        data["TxLowSchedClassBandwidth"] = tx_low_bw
        data["RxEnable"] = rx_enable
        data["RxAggregateBandwidth"] = rx_agg_bw
        data["RxCriticalSchedClassBandwidth"] = rx_critical_bw
        data["RxHighSchedClassBandwidth"] = rx_high_bw
        data["RxNormalSchedClassBandwidth"] = rx_normal_bw
        data["RxLowSchedClassBandwidth"] = rx_low_bw
        return self.do_patch_request("WanAggregateScheduler", data)

    # probe
    def create_probe(self,
                    name="probe1",
                    type="WAN",
                    if_name="WAN1",
                    mode="CMD_PING",
                    dst_addr="1.1.1.1",
                    dst_port=1111,
                    interval=2,
                    timeout=1,
                    fail_threshold=5,
                    ok_threshold=10,
                    tag1="",
                    tag2=""):
        data = {}
        data["Name"] = name
        data["Type"] = type
        data["IfName"] = if_name
        data["Mode"] = mode
        data["DstAddr"] = dst_addr
        data["DstPort"] = dst_port
        data["Interval"] = interval
        data["Timeout"] = timeout
        data["FailThreshold"] = fail_threshold
        data["OkThreshold"] = ok_threshold
        data["Tag1"] = tag1
        data["Tag2"] = tag2
        return self.do_post_request("Probe", data)

    def update_probe(self,
                    name="probe1",
                    type="WAN",
                    if_name="WAN1",
                    mode="CMD_PING",
                    dst_addr="1.1.1.1",
                    dst_port=1111,
                    interval=2,
                    timeout=1,
                    fail_threshold=5,
                    ok_threshold=10,
                    tag1="",
                    tag2=""):
        data = {}
        data["Name"] = name
        data["Type"] = type
        data["IfName"] = if_name
        data["Mode"] = mode
        data["DstAddr"] = dst_addr
        data["DstPort"] = dst_port
        data["Interval"] = interval
        data["Timeout"] = timeout
        data["FailThreshold"] = fail_threshold
        data["OkThreshold"] = ok_threshold
        data["Tag1"] = tag1
        data["Tag2"] = tag2
        return self.do_patch_request("Probe", data)

    def delete_probe(self, name):
        data = {}
        data['Name'] = name
        return self.do_delete_request("Probe", data)
    # vrrp
    def create_vrrp(self,
                    vr_id:int,
                    vip:str,
                    bridge:str,
                    priority:int,
                    adv_interval:int,
                    segment=0,
                    unicast=False,
                    peer_address="",
                    tag1="",
                    tag2=""):
        data = {}
        data["Segment"] = segment
        data["VRID"] = vr_id
        data["Bridge"] = bridge
        data["Priority"] = priority
        data["AdvInterval"] = adv_interval
        data["VIP"] = vip
        data["Unicast"] = unicast
        data["PeerAddress"] = peer_address
        data["Tag1"] = tag1
        data["Tag2"] = tag2
        return self.do_post_request("VRRPSetting", data)
    def update_vrrp(self,
                    vr_id:int,
                    vip:str,
                    bridge:str,
                    priority:int,
                    adv_interval:int,
                    segment=0,
                    unicast=False,
                    peer_address="",
                    tag1="",
                    tag2=""):
        data = {}
        data["Segment"] = segment
        data["VRID"] = vr_id
        data["Bridge"] = bridge
        data["Priority"] = priority
        data["AdvInterval"] = adv_interval
        data["VIP"] = vip
        data["Unicast"] = unicast
        data["PeerAddress"] = peer_address
        data["Tag1"] = tag1
        data["Tag2"] = tag2
        return self.do_patch_request("VRRPSetting", data)

    def delete_vrrp(self, vr_id:int, segment:0):
        data = {}
        data['VRID'] = vr_id
        data['Segment'] = segment
        return self.do_delete_request("VRRPSetting", data)

    def change_vrrp_priority(self,
                    vr_id:int,
                    segment:0,
                    down: True):
        data = {}
        data['VRID'] = vr_id
        data['Segment'] = segment
        data['Down'] = down
        return self.do_action_request("ChangeVRRPPriority", data)

    # AccIpBinding, all out ips should be synchronized with logical interface additional ips
    def create_acc_ip_binding(self, acc_ip, out_ip1="", out_ip2=""):
        data = {}
        data['AccIp'] = acc_ip
        data["OutIps"] = []
        if out_ip1 != "":
            data["OutIps"].append({"IpAddr": out_ip1})
        if out_ip2 != "":
            data["OutIps"].append({"IpAddr": out_ip2})
        return self.do_post_request("AccIpBinding", data)

    def update_acc_ip_binding(self, acc_ip, out_ip1="", out_ip2=""):
        data = {}
        data['AccIp'] = acc_ip
        data["OutIps"] = []
        if out_ip1 != "":
            data["OutIps"].append({"IpAddr": out_ip1})
        if out_ip2 != "":
            data["OutIps"].append({"IpAddr": out_ip2})
        return self.do_patch_request("AccIpBinding", data)
    
    def delete_acc_ip_binding(self, acc_ip):
        data = {}
        data['AccIp'] = acc_ip
        return self.do_delete_request("AccIpBinding", data)
