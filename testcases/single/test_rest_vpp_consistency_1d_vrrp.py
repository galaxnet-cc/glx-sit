import unittest
import time

from lib.util import glx_assert
from topo.topo_1d import Topo1D

class TestRestVppConsistency1DVRRP(unittest.TestCase):
    # 因只验证rest与vpp的一致性，不验证功能，因此只使用单台设备拓朴。
    def setUp(self):
        self.topo = Topo1D()

    def tearDown(self):
        pass

    def test_vrrp(self):
       segment = 0
       priority = 254
       vip = "192.168.88.100"
       prefix = "/32"
       vip_with_prefix = vip + prefix
       bridge = "default"
       brname = "br-" + bridge
       adv_interval = 1
       adv_interval_centiseconds = adv_interval * 100
       unicast = False
       ns = "ctrl-ns"
       peer_address = ""
       ctx_key_prefix = "VRRPContext#"
       setting_key_prefix = "VRRPSetting#"

       # create vrrp
       # validation
       # vr_id shouldn't be zero
       vr_id = 0
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       vr_id = 51

       # priority shouldn't be 0
       priority = 0
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       priority = 254

       # priority shouldn't be 255
       priority = 255 
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       priority = 254

       # adv_interval shouldn't be zero
       adv_interval = 0
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       adv_interval = 1

       # vip shouldn't be invalid
       vip_with_prefix = "192"
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       vip_with_prefix = vip + prefix

       # bridge shouldn't be invalid
       bridge = "xxxx"
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       bridge = "default"

       # peer address empty when unicast is true
       unicast = True
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0, unicast=unicast)
       glx_assert(500 == resp.status_code)
       # recover
       unicast = False

       # should be successfully created.
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(201 == resp.status_code)
       # can't add repeatly
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)

       # check vrrp context in redis
       setting_key = setting_key_prefix + f"0#{vr_id}"
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli exists {setting_key}")
       glx_assert(err == '')
       glx_assert("1" in out)


       ctx_key = ctx_key_prefix + f"0#{vr_id}"
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli exists {ctx_key}")
       glx_assert(err == '')
       glx_assert("1" in out)

       # check relation key in redis
       relation_key = "InterfaceVRRPRelationContext#"
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli keys {relation_key}*")
       glx_assert(err == '')


       # check vrrp vr bridge in redis
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli hget {ctx_key} SwIfIndex")
       glx_assert(err == '')
       sw_if_index = int(out)

       # wait for Backup turn into Master
       time.sleep(5)


       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')

       # check parameters
       # check sw if index
       glx_assert(f"sw_if_index {sw_if_index}" in out)
       # check priority in out
       glx_assert(f"priority: configured {priority}" in out)
       # check ip in out
       glx_assert(vip in out)
       # check preempt and accept in out
       glx_assert("preempt yes" in out)
       glx_assert("accept yes" in out)
       # check adv interval is equal with what i setted.
       glx_assert(f"adv interval {adv_interval_centiseconds}" in out)
       # check state Master
       glx_assert("state Master" in out)

       # get runtime state
       resp = self.topo.dut1.get_rest_device().get_vrrp_state(vr_id=vr_id, segment=segment)
       glx_assert(200 == resp.status_code)
       glx_assert("MASTER" in str(resp.content))

       # check macvlan
       out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ip addr show dev {brname}.{vr_id}")
       glx_assert(err == '')
       glx_assert(vip_with_prefix in out)
       glx_assert("state UP" in out)

       # down master. but it's just a single test, we can't make sure it will be Backup state
       resp = self.topo.dut1.get_rest_device().change_vrrp_priority(vr_id=vr_id, segment=segment, priority=1)
       glx_assert(200 == resp.status_code)

       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check priority in out
       glx_assert("priority: configured 1" in out)

       # up master. but it's just a single test, we can't make sure it will be Backup state
       resp = self.topo.dut1.get_rest_device().change_vrrp_priority(vr_id=vr_id, segment=segment, priority=254)
       glx_assert(200 == resp.status_code)

       # wait for changing state
       time.sleep(5)

       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check priority in out
       glx_assert("priority: configured 254" in out)

       # wait for changing state
       time.sleep(5)



       # check parameters
       # check ip in out
       glx_assert(vip in out)
       # check priority in out
       glx_assert(f"priority: configured {priority}" in out)
       # check preempt and accept in out
       glx_assert("preempt yes" in out)
       glx_assert("accept yes" in out)
       # check adv interval is equal with what i setted.
       glx_assert(f"adv interval {adv_interval_centiseconds}" in out)
       # check state Master
       glx_assert("state Master" in out)

       # delete vrrp
       resp = self.topo.dut1.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
       glx_assert(410 == resp.status_code)
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       # check vrrp not in vpp
       glx_assert(err == '')
       # check vrrp context not in redis
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli exists {ctx_key}")
       glx_assert(err == '')
       glx_assert("0" in out)

       # create vrrp with unicast
       unicast = True
       peer_address = "192.168.88.4"
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0, unicast=unicast, peer_address=peer_address)
       glx_assert(201 == resp.status_code)
       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check peer address in out
       glx_assert(f"peer addresses {peer_address}" in out)

       # create another vrrp for checking multiply vrrp vrs
       resp = self.topo.dut1.get_rest_device().create_vrrp(vip="192.168.88.101",vr_id=52, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0, unicast=unicast, peer_address=peer_address)
       glx_assert(201 == resp.status_code)
       resp = self.topo.dut1.get_rest_device().delete_vrrp(vr_id=52, segment=0)
       glx_assert(410 == resp.status_code)

       # update vrrp
       # validation
       # vr_id shouldn't be updated
       vr_id = 1
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(404 == resp.status_code)
       # recover
       vr_id = 51

       # bridge shouldn't be update
       bridge = "xxxx"
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       bridge = "default"

       # vip shouldn't be invalid
       vip_with_prefix = "192"
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       vip_with_prefix = vip + prefix
       # recover
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
    
       # priority shouldn't be 0
       priority = 0
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       priority = 254

       # priority shouldn't be 255
       priority = 0
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       priority = 254

       # adv_interval shouldn't be zero
       adv_interval = 0
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(500 == resp.status_code)
       # recover
       adv_interval = 1

       # peer address empty when unicast is true
       unicast = True
       peer_address = ""
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0, unicast=unicast)
       glx_assert(500 == resp.status_code)
       # recover
       unicast = False

       # update vrrp unicast false
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0, unicast=unicast)
       glx_assert(200 == resp.status_code)
       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check peer address in out
       glx_assert(f"peer addresses {peer_address}" in out)

       # update vrrp priority
       priority = 1
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(200 == resp.status_code)
       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check priority in out
       glx_assert(f"priority: configured {priority}" in out)

       # update vrrp adv interval
       adv_interval = 2
       adv_interval_centiseconds = adv_interval * 100
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(200 == resp.status_code)
       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check adv interval is equal with what i setted.
       glx_assert(f"adv interval {adv_interval_centiseconds}" in out)

       # update vrrp vip
       vip = "192.168.88.101"
       vip_with_prefix = vip + prefix
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0)
       glx_assert(200 == resp.status_code)
       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check ip in out
       glx_assert(vip in out)

       # check macvlan
       out, err = self.topo.dut1.get_vpp_ssh_device().get_ns_cmd_result(ns, f"ip addr show dev {brname}.{vr_id}")
       glx_assert(err == '')
       glx_assert(vip_with_prefix in out)
       glx_assert("state UP" in out)

       # update vrrp with unicast
       unicast = True
       peer_address = "192.168.88.4"
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0, unicast=unicast, peer_address=peer_address)
       glx_assert(200 == resp.status_code)
       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check peer address in out
       glx_assert(f"peer addresses {peer_address}" in out)

       # update vrrp unicast peer address
       peer_address = "192.168.88.5"
       resp = self.topo.dut1.get_rest_device().update_vrrp(vip=vip_with_prefix,vr_id=vr_id, bridge=bridge, priority=priority, adv_interval=adv_interval, segment=0, unicast=unicast, peer_address=peer_address)
       glx_assert(200 == resp.status_code)
       # check vrrp in vpp
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       glx_assert(err == '')
       glx_assert(out != '')
       # check peer address in out
       glx_assert(f"peer addresses {peer_address}" in out)

       # delete vrrp
       resp = self.topo.dut1.get_rest_device().delete_vrrp(vr_id=vr_id, segment=0)
       glx_assert(410 == resp.status_code)
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"vppctl show vrrp vr {bridge}")
       # check vrrp not in vpp
       glx_assert(err == '')
       # check vrrp context not in redis
       out, err = self.topo.dut1.get_vpp_ssh_device().get_cmd_result(f"redis-cli exists {ctx_key}")
       glx_assert(err == '')
       glx_assert("0" in out)






       




       




