# 说明：这里定义基于rest api的device，可以实现基于api的管理。
import requests
import json

REQUEST_HEADER_CTYPE={"Content-Type": "application/json"}

# 此函数将request库的response返回，由测试例自行决定是否要匹配rest api的结果
class RestDevice:
    def __init__(self, api_ip="127.0.0.1", api_port=8080):
        self.api_ip = api_ip
        self.api_port = api_port

    def do_post_request(self, obj_name, obj_data):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/config/{obj_name}'
        response = requests.post(url, data=json.dumps(obj_data), headers=REQUEST_HEADER_CTYPE)
        return response

    def do_patch_request(self, obj_name, obj_data):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/config/{obj_name}'
        response = requests.patch(url, data=json.dumps(obj_data), headers=REQUEST_HEADER_CTYPE)
        return response

    def do_delete_request(self, obj_name, obj_data):
        url = f'http://{self.api_ip}:{self.api_port}/public/v1/config/{obj_name}'
        response = requests.delete(url, data=json.dumps(obj_data), headers=REQUEST_HEADER_CTYPE)
        return response

    def delete_host_stack_dnsmasq(self,name):
        host_stack_dnsmasq_data={}
        host_stack_dnsmasq_data['Name']=name
        return self.do_delete_request("HostStackDhcp",host_stack_dnsmasq_data) 

    def update_host_stack_dnsmasq(self,name,gateway,start_ip,end_ip,netmask,lease_time):
        host_stack_dnsmasq_data={}
        host_stack_dnsmasq_data['Name']=name
        host_stack_dnsmasq_data['GatewayIP']=gateway
        host_stack_dnsmasq_data['StartIP']=start_ip
        host_stack_dnsmasq_data['EndIP']=end_ip
        host_stack_dnsmasq_data['NetMask']=netmask
        host_stack_dnsmasq_data['LeaseTIme']=lease_time
        return self.do_patch_request("HostStackDhcp",host_stack_dnsmasq_data)

    def set_host_stack_dnsmasq(self,name,gateway,start_ip,end_ip,netmask,lease_time):
        host_stack_dnsmasq_data={}
        host_stack_dnsmasq_data['Name']=name
        host_stack_dnsmasq_data['GatewayIP']=gateway
        host_stack_dnsmasq_data['StartIP']=start_ip
        host_stack_dnsmasq_data['EndIP']=end_ip
        host_stack_dnsmasq_data['NetMask']=netmask
        host_stack_dnsmasq_data['LeaseTIme']=lease_time
        return self.do_post_request("HostStackDhcp",host_stack_dnsmasq_data)

    def delete_fire_wall_rule(self,rule_name):
        rule_data={}
        rule_data['Name']=rule_name
        return self.do_delete_request("FirewallRule",rule_data)

    def update_fire_wall_rule(self,rule_name,priority,dest_address,action):
        rule_data={}
        rule_data['Name']=rule_name
        rule_data['Priority']=priority
        rule_data['DestAddress']=dest_address
        rule_data['Action']=action
        rule_data['L3Protocol']=1
        return self.do_patch_request("FirewallRule",rule_data)

    def set_fire_wall_rule(self,rule_name,priority,dest_address,action):
        rule_data={}
        rule_data['Name']=rule_name
        rule_data['Priority']=priority
        rule_data['DestAddress']=dest_address
        rule_data['Action']=action
        rule_data['L3Protocol']=1
        return self.do_post_request("FirewallRule",rule_data)

    def set_wan_static_ip(self, wan_name, wan_ip_w_prefix):
        wan_data = {}
        wan_data['Name'] = wan_name
        wan_data['AddressingType'] = "STATIC"
        wan_data['StaticIpAddrWithPrefix'] = wan_ip_w_prefix
        return self.do_patch_request("LogicalInterface", wan_data)

    # default mode.
    def set_wan_dhcp(self, wan_name):
        wan_data = {}
        wan_data['Name'] = wan_name
        wan_data['AddressingType'] = "DHCP"
        return self.do_patch_request("LogicalInterface", wan_data)

    def set_wan_pppoe(self, wan_name, pppoe_user, pppoe_password):
        wan_data = {}
        wan_data['Name'] = wan_name
        wan_data['AddressingType'] = "PPPOE"
        wan_data['PppoeUsername'] = pppoe_user
        wan_data['PppoePassword'] = pppoe_password
        return self.do_patch_request("LogicalInterface", wan_data)

    def set_default_bridge_ip(self, bvi_ip_w_prefix):
        bridge_data = {}
        bridge_data['Name'] = "default"
        bridge_data['BviEnable'] = True
        bridge_data['BviIpAddrWithPrefix'] = bvi_ip_w_prefix
        return self.do_patch_request("Bridge", bridge_data)

    def create_glx_link(self, link_id, wan_name="WAN1", remote_ip="127.0.0.1", remote_port=2288, tunnel_id=0, route_label="0xffffffffff"):
        link_data = {}
        link_data['LinkId'] = link_id
        link_data['LocalWanName'] = wan_name
        link_data['RemoteIp'] = remote_ip
        link_data['RemotePort'] = remote_port
        link_data['TunnelId'] = tunnel_id
        link_data['RouteLabel'] = route_label
        return self.do_post_request("Link", link_data)

    def create_glx_link(self, link_id, wan_name="WAN1", remote_ip="127.0.0.1", remote_port=2288, tunnel_id=0, route_label="0xffffffffff"):
        link_data = {}
        link_data['LinkId'] = link_id
        link_data['LocalWanName'] = wan_name
        link_data['RemoteIp'] = remote_ip
        link_data['RemotePort'] = remote_port
        link_data['TunnelId'] = tunnel_id
        link_data['RouteLabel'] = route_label
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
        label_data["TableID"] = table_id
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
        tunnels.append({"TunnelId": tunnel_id, "TunnelWeight": 100, "TunnelPriority": 100})
        label_data["NexthopTunnels"] = tunnels
        return self.do_post_request("RouteLabelPolicy", label_data)

    def delete_glx_route_label_policy_type_tunnel(self, route_label):
        label_data = {}
        label_data["RouteLabel"] = route_label
        return self.do_delete_request("RouteLabelPolicy", label_data)

    def create_glx_route_label_fwd(self, route_label, tunnel_id1, tunnel_id2=None):
        label_data = {}
        label_data["RouteLabel"] = route_label
        label_data["NexthopMode"] = "active-backup"
        tunnels = []
        # support tunnel weight later.
        tunnels.append({"TunnelId": tunnel_id1, "TunnelWeight": 100, "TunnelPriority": 100})
        if tunnel_id2 != None:
            tunnels.append({"TunnelId": tunnel_id2, "TunnelWeight": 100, "TunnelPriority": 100})
        label_data["NexthopTunnels"] = tunnels
        return self.do_post_request("RouteLabelFwdEntry", label_data)

    def delete_glx_route_label_fwd(self, route_label):
        label_data = {}
        label_data["RouteLabel"] = route_label
        return self.do_delete_request("RouteLabelFwdEntry", label_data)

    def create_edge_route(self, route_prefix, route_label, tunnel_id1, tunnel_id2=None, tunnel1_priority=100, tunnel2_priority=200):
        route_data = {}
        route_data["VrfName"] = "default"
        route_data["DestPrefix"] = route_prefix
        route_data["RouteProtocol"] = "overlay"
        route_data["RouteLabel"] = route_label
        tunnels = []
        # support tunnel weight later.
        tunnels.append({"TunnelId": tunnel_id1, "TunnelWeight": 100, "TunnelPriority": tunnel1_priority})
        if tunnel_id2 != None:
            tunnels.append({"TunnelId": tunnel_id2, "TunnelWeight": 100, "TunnelPriority": tunnel2_priority})
        route_data["NexthopTunnels"] = tunnels
        return self.do_post_request("EdgeRoute", route_data)

    def delete_edge_route(self, route_prefix):
        route_data = {}
        route_data["VrfName"] = "default"
        route_data["DestPrefix"] = route_prefix
        route_data["RouteProtocol"] = "overlay"
        return self.do_delete_request("EdgeRoute", route_data)

    def create_bizpol(self, name, priority, src_prefix, dst_prefix, protocol, direct_enable, steering_type=0, steering_mode=0, steering_interface=""):
        bizpol_data = {}
        bizpol_data["Name"] = name
        bizpol_data["SrcAddressWithPrefix"] = src_prefix
        bizpol_data["DstAddressWithPrefix"] = dst_prefix
        bizpol_data["Protocol"] = protocol
        bizpol_data["DirectEnable"] = direct_enable
        bizpol_data["SteeringType"] = steering_type
        bizpol_data["SteeringMode"] = steering_mode
        bizpol_data["SteeringInterface"] = steering_interface
        return self.do_post_request("BusinessPolicy", bizpol_data)

    def update_bizpol(self, name, priority, src_prefix, dst_prefix, protocol, direct_enable, steering_type=0, steering_mode=0, steering_interface=""):
        bizpol_data = {}
        bizpol_data["Name"] = name
        bizpol_data["SrcAddressWithPrefix"] = src_prefix
        bizpol_data["DstAddressWithPrefix"] = dst_prefix
        bizpol_data["Protocol"] = protocol
        bizpol_data["DirectEnable"] = direct_enable
        bizpol_data["SteeringType"] = steering_type
        bizpol_data["SteeringMode"] = steering_mode
        bizpol_data["SteeringInterface"] = steering_interface
        return self.do_patch_request("BusinessPolicy", bizpol_data)

    def delete_bizpol(self, name):
        bizpol_data = {}
        bizpol_data["Name"] = name
        return self.do_delete_request("BusinessPolicy", bizpol_data)
