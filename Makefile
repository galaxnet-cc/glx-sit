test-multi-basic:
	python3 -m unittest testcases/multi/test_basic_1t_4d.py

test-single-all:
	python3 -m unittest testcases/single/test*.py

test-single-basic:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_basic.py

test-single-glx:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_glx.py

test-single-dynrouting:
	python3 -m unittest testcases/single/test_rest_vpp_consistency_1d_dynrouting.py

