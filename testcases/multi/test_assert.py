import unittest
import time
from lib.util import glx_assert

class TestAssert(unittest.TestCase):
    def test_assert(self):
        exp = "1"
        data = "23"
        glx_assert(exp in data)
