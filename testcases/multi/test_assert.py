import unittest
import time
from lib.util import glx_assert

class TestAssert(unittest.TestCase):
    def test_assert(self):
        glx_assert("1" in "123")
