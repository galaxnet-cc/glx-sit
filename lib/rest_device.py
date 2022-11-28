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
        return self.do_delete_request("HostStackDhcp", host_stack_dnsmasq_data)

    def update_host_stack_dnsmasq(self, name, gateway, start_ip, end_ip, lease_time):
        host_stack_dnsmasq_data = {}
        host_stack_dnsmasq_data['Name'] = name
        host_stack_dnsmasq_data['GatewayIP'] = gateway
        host_stack_dnsmasq_data['StartIP'] = start_ip
        host_stack_dnsmasq_data['EndIP'] = end_ip
        host_stack_dnsmasq_data['LeaseTIme'] = lease_time
        return self.do_patch_request("HostStackDhcp", host_stack_dnsmasq_data)

    def set_host_stack_dnsmasq(self, name, gateway, start_ip, end_ip, lease_time):
        host_stack_dnsmasq_data = {}
        host_stack_dnsmasq_data['Name'] = name
        host_stack_dnsmasq_data['GatewayIP'] = gateway
        host_stack_dnsmasq_data['StartIP'] = start_ip
        host_stack_dnsmasq_data['EndIP'] = end_ip
        host_stack_dnsmasq_data['LeaseTIme'] = lease_time
        return self.do_post_request("HostStackDhcp", host_stack_dnsmasq_data)

    def delete_fire_wall_rule(self, rule_name):
        rule_data = {}
        rule_data['Name'] = rule_name
        return self.do_delete_request("FirewallRule", rule_data)

    def update_fire_wall_rule(self, rule_name, priority, dest_address, action, app_id=65535):
        rule_data = {}
        rule_data['Segment'] = 0
        rule_data['Name'] = rule_name
        rule_data['Priority'] = priority
        rule_data['SrcAddressWithPrefix'] = "0.0.0.0/0"
        rule_data['DstAddressWithPrefix'] = dest_address
        rule_data['Action'] = action
        rule_data['L4Protocol'] = 0
        rule_data['AppId'] = app_id
        return self.do_patch_request("FirewallRule", rule_data)

    def set_fire_wall_rule(self, rule_name, priority, dest_address, action, app_id=65535):
        rule_data = {}
        rule_data['Segment'] = 0
        rule_data['Name'] = rule_name
        rule_data['Priority'] = priority
        rule_data['SrcAddressWithPrefix'] = "0.0.0.0/0"
        rule_data['DstAddressWithPrefix'] = dest_address
        rule_data['Action'] = action
        rule_data['L4Protocol'] = 0
        rule_data['AppId'] = app_id
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

    def delete_bridge(self, name):
        bridge_data = {}
        bridge_data['Name'] = name
        return self.do_delete_request("Bridge", bridge_data)

    def update_bridge_ip(self, name, bvi_ip_w_prefix):
        bridge_data = {}
        bridge_data['Name'] = name
        bridge_data['BviEnable'] = True
        bridge_data['BviIpAddrWithPrefix'] = bvi_ip_w_prefix
        return self.do_patch_request("Bridge", bridge_data)

    def create_bridge(self, name, bvi_ip_w_prefix):
        bridge_data = {}
        bridge_data['Name'] = name
        bridge_data['BviEnable'] = True
        bridge_data['BviIpAddrWithPrefix'] = bvi_ip_w_prefix
        return self.do_post_request("Bridge", bridge_data)

    def set_default_bridge_ip(self, bvi_ip_w_prefix):
        bridge_data = {}
        bridge_data['Name'] = "default"
        bridge_data['BviEnable'] = True
        bridge_data['BviIpAddrWithPrefix'] = bvi_ip_w_prefix
        return self.do_patch_request("Bridge", bridge_data)

    def create_glx_link(self, link_id, wan_name="WAN1", remote_ip="127.0.0.1", remote_port=2288, tunnel_id=0, route_label="0xffffffffff", is_tcp=False):
        link_data = {}
        link_data['LinkId'] = link_id
        link_data['LocalWanName'] = wan_name
        link_data['RemoteIp'] = remote_ip
        link_data['RemotePort'] = remote_port
        link_data['TunnelId'] = tunnel_id
        link_data['RouteLabel'] = route_label
        link_data['IsTcp'] = is_tcp
        return self.do_post_request("Link", link_data)

    def delete_glx_link(self, link_id):
        link_data = {}
        link_data['LinkId'] = link_id
        return self.do_delete_request("Link", link_data)

    def create_glx_tunnel(self, tunnel_id):
        tunnel_data = {}
        tunnel_data['TunnelId'] = tunnel_id
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

    def create_edge_route(self, route_prefix, route_label, is_acc=False, is_acc_reverse=False, segment=0):
        route_data = {}
        route_data["Segment"] = segment
        route_data["DestPrefix"] = route_prefix
        route_data["RouteProtocol"] = "overlay"
        route_data["RouteLabel"] = route_label
        route_data["IsAcc"] = is_acc
        route_data["IsAccReverse"] = is_acc_reverse
        return self.do_post_request("EdgeRoute", route_data)

    def delete_edge_route(self, route_prefix, segment=0):
        route_data = {}
        route_data["Segment"] = segment
        route_data["DestPrefix"] = route_prefix
        route_data["RouteProtocol"] = "overlay"
        return self.do_delete_request("EdgeRoute", route_data)

    def create_bizpol(self, name, priority, src_prefix, dst_prefix, protocol, direct_enable, steering_type=0, steering_mode=0, steering_interface="", app_id=65535):
        bizpol_data = {}
        bizpol_data["Name"] = name
        bizpol_data["SrcAddressWithPrefix"] = src_prefix
        bizpol_data["DstAddressWithPrefix"] = dst_prefix
        bizpol_data["Protocol"] = protocol
        bizpol_data["DirectEnable"] = direct_enable
        bizpol_data["SteeringType"] = steering_type
        bizpol_data["SteeringMode"] = steering_mode
        bizpol_data["SteeringInterface"] = steering_interface
        bizpol_data["AppId"] = app_id
        return self.do_post_request("BusinessPolicy", bizpol_data)

    def update_bizpol(self, name, priority, src_prefix, dst_prefix, protocol, direct_enable, steering_type=0, steering_mode=0, steering_interface="", app_id=65535):
        bizpol_data = {}
        bizpol_data["Name"] = name
        bizpol_data["SrcAddressWithPrefix"] = src_prefix
        bizpol_data["DstAddressWithPrefix"] = dst_prefix
        bizpol_data["Protocol"] = protocol
        bizpol_data["DirectEnable"] = direct_enable
        bizpol_data["SteeringType"] = steering_type
        bizpol_data["SteeringMode"] = steering_mode
        bizpol_data["SteeringInterface"] = steering_interface
        bizpol_data["AppId"] = app_id
        return self.do_patch_request("BusinessPolicy", bizpol_data)

    def delete_bizpol(self, name):
        bizpol_data = {}
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

    def create_segment(self, segment_id):
        data = {}
        data["Id"] = segment_id
        return self.do_post_request("Segment", data)

    def update_segment(self, segment_id, acc_enable=False, int_edge_enable=False,dns_intercept_enable=False, route_label="0xffffffffffffffff"):
        data = {}
        data["Id"] = segment_id
        data["AccEnable"] = acc_enable
        data["IntEdgeEnable"] = int_edge_enable
        data["DnsInterceptEnable"] = dns_intercept_enable
        data["RouteLabel"] = route_label
        return self.do_patch_request("Segment", data)

    def delete_segment(self, segment_id):
        data = {}
        data["Id"] = segment_id
        return self.do_delete_request("Segment", data)

    def create_segment_acc_prop(self, segment_id, acc_ip1="1.1.1.1"):
        data = {}
        data["Segment"] = segment_id
        data["AccIps"] = []
        data["AccIps"].append({"Ip4Address": acc_ip1})
        return self.do_post_request("SegmentAccProperties", data)

    def delete_segment_acc_prop(self, segment_id):
        data = {}
        data["Segment"] = segment_id
        return self.do_delete_request("SegmentAccProperties", data)

    def update_segment_acc_prop(self, segment_id, acc_ip1="1.1.1.1"):
        data = {}
        data["Segment"] = segment_id
        data["AccIps"] = []
        data["AccIps"].append({"Ip4Address": acc_ip1})
        return self.do_patch_request("SegmentAccProperties", data)

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
