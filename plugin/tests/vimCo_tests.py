import unittest
import vimCo as sut


@unittest.skip("Don't forget to test!")
class VimcoTests(unittest.TestCase):

    def test_example_fail(self):
        result = sut.vimCo_example()
        self.assertEqual("Happy Hacking", result)
