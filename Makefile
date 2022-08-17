# 由于当前link被动删除需要老化时间，因此多节点的测试集之间要么人工等待，
# 要么可以强制reset。

test-multi-basic:
	python3 -m unittest testcases/multi/test_basic_1t_4d.py

test-multi-acc:
	python3 -m unittest testcases/multi/test_basic_1t_4d_acc.py

test-multi-mseg:
	python3 -m unittest testcases/multi/test_basic_1t_4d_mseg.py

test-single-all:
	python3 -m unittest testcases/single/test*.py

test-single-basic:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_basic.py

test-single-glx:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_glx.py

test-single-dynrouting:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_dynrouting.py

