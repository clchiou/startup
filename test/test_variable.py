import unittest

from startup import Variable


class TestVariable(unittest.TestCase):

    def test_variable(self):
        var = Variable()
        self.assertFalse(var.readable)
        var.notify_will_write()
        var.write(1)
        self.assertTrue(var.readable)
        self.assertEqual(1, var.read_latest())
        self.assertEqual([1], var.read_all())

        var.notify_will_write()
        self.assertFalse(var.readable)
        var.write(2)
        self.assertTrue(var.readable)
        self.assertEqual(2, var.read_latest())
        self.assertEqual([1, 2], var.read_all())

        var.notify_will_write()
        self.assertFalse(var.readable)
        var.write(3)
        self.assertTrue(var.readable)
        self.assertEqual(3, var.read_latest())
        self.assertEqual([1, 2, 3], var.read_all())


if __name__ == '__main__':
    unittest.main()
