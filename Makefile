# 多机测试例
test-multi-basic:
	python3 -m unittest testcases/multi/test_basic_1t_4d.py

test-multi-hubspoke:
	python3 -m unittest testcases/multi/test_basic_1t_4d_hub_spoke.py

test-multi-acc:
	python3 -m unittest testcases/multi/test_basic_1t_4d_acc.py

test-multi-mseg:
	python3 -m unittest testcases/multi/test_basic_1t_4d_mseg.py

# 由伟明编写，目前看不太稳定，需要进一步测试，动态路由这部分功能，后面在增加
# bgp能力时，需要再多增加些验证用例。
test-multi-dynroute:
	python3 -m unittest testcases/multi/test_basic_1t_4d_dynamic_route.py

test-multi-dpi:
	python3 -m unittest testcases/multi/test_basic_1t_4d_dpi.py

test-multi-tcp:
	python3 -m unittest testcases/multi/test_basic_1t_4d_tcp.py

test-multi-glx-nego:
	python3 -m unittest testcases/multi/test_basic_1t_4d_glx_nego.py

# sjs
# test-multi-auto-dns:
# 	python3 -m unittest testcases/multi/test_basic_1t_4d_autodns.py

test-multi-dnsipcollect:
	python3 -m unittest testcases/multi/test_basic_1t_4d_dnsipcollect.py

test-multi-stats-collect:
	python3 -m unittest testcases/multi/test_basic_1t_4d_stats_collect.py

test-multi-segment-detection:
	python3 -m unittest testcases/multi/test_basic_1t_4d_segment_detection.py

test-multi-dhcp-and-dns:
	python3 -m unittest testcases/multi/test_basic_1t_4d_dhcp_and_dns_settings.py

test-multi-wan-dnat:
	python3 -m unittest testcases/multi/test_basic_1t_4d_wan_dnat.py

test-multi-l3subif:
	python3 -m unittest testcases/multi/test_basic_1t_4d_l3subif.py

test-multi-wan-dynaddr:
	python3 -m unittest testcases/multi/test_basic_1t_4d_wan_dynamic_addr.py

test-multi-object-group:
	python3 -m unittest testcases/multi/test_basic_1t_4d_object_group.py

test-multi-sched:
	python3 -m unittest testcases/multi/test_basic_1t_4d_sched.py

# 单机测试例

test-single-all:
	python3 -m unittest testcases/single/test*.py

test-single-basic:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_basic.py

test-single-glx:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_glx.py

test-single-dynrouting:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_dynrouting.py

test-single-l3subif:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_l3subif.py

# sjs
test-single-dnsipcollect:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_dnsipcollect.py

test-single-statscollect:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_statscollect.py

test-single-configurefilter:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_configurefilter.py

test-single-segment-detection:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_basicmultisegment.py

# 验证所有多节点用例目标
# 这里定义成依赖方式，以方便调试因某个用例导致的全量用例无法执行通过。
# 1025: dynroute不太稳定，暂时先不运行这部分功能用例，不加入依赖。
test-multi-all: test-multi-basic test-multi-hubspoke test-multi-acc test-multi-mseg test-multi-dpi test-multi-tcp test-multi-glx-nego test-multi-l3subif test-multi-wan-dynaddr test-multi-dnsipcollect test-multi-stats-collect test-multi-segment-detection test-multi-dhcp-and-dns test-multi-wan-dnat test-multi-object-group test-multi-sched
	echo "test-multi-all-finished"
