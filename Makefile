test-basic:
	python3 -m unittest testcases/test_basic_1t_4d.py

test-rest-glx:
	python3 -m unittest testcases/test_rest_vpp_consistency_1d_glx.py

test-rest-basic:
	python3 -m unittest testcases/test_rest_vpp_consistency_1d_basic.py
