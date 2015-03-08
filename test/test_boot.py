import unittest

from boot import BootException
from boot import Boot


class TestBoot(unittest.TestCase):

    def test_lexicographical_order(self):
        boot = Boot()
        data = []
        @boot
        def func2():
            data.append(2)
        @boot
        def func1():
            data.append(1)
        @boot
        def func3():
            data.append(3)
        self.assertEqual({}, boot.call())
        self.assertEqual([1, 2, 3], data)
        # You cannot call run() again, by the way.
        self.assertRaises(BootException, boot.call)

    def test_sequential_order(self):
        boot = Boot()
        data = []
        @boot
        def func3(x: 'x') -> 'y':
            data.append(x)
            return x - 1
        @boot
        def func2(y: 'y') -> 'z':
            data.append(y)
            return y - 1
        @boot
        def func1(z: 'z'):
            data.append(z)
        self.assertEqual({'x': 3, 'y': 2, 'z': 1}, boot.call(x=3))
        self.assertEqual([3, 2, 1], data)

    def test_join(self):
        boot = Boot()
        data = []
        @boot
        def func2() -> 'x':
            data.append(2)
            return 2
        @boot
        def func1() -> 'x':
            data.append(1)
            return 1
        @boot
        def func3() -> 'x':
            data.append(3)
            return 3
        @boot
        def func_join_1(x: ['x']):
            self.assertEqual([1, 2, 3], x)
            data.append('join')
        self.assertEqual({'x': 3}, boot.call())
        self.assertEqual([1, 2, 3, 'join'], data)

    def test_multiple_return_1(self):
        boot = Boot()
        data = []
        @boot
        def func() -> ('x', 'y', 'z'):
            return 'x-str', 'y-str', 'z-str'
        @boot
        def func_z(z: 'z'):
            self.assertEqual('z-str', z)
            data.append('z')
        @boot
        def func_x(x: 'x'):
            self.assertEqual('x-str', x)
            data.append('x')
        @boot
        def func_y(y: 'y'):
            self.assertEqual('y-str', y)
            data.append('y')
        self.assertEqual(
            {'x': 'x-str', 'y': 'y-str', 'z': 'z-str'}, boot.call())
        self.assertEqual(['x', 'y', 'z'], data)

    def test_multiple_return_2(self):
        boot = Boot()
        @boot
        def func_repeat() -> ('x', 'x', 'x'):
            return 1, 3, 2
        @boot
        def func_collect(xs: ['x']) -> 'xs':
            return xs
        self.assertEqual({'xs': [1, 3, 2], 'x': 2}, boot.call())

    def test_wrong_annotations(self):
        boot = Boot()
        def func1(_: ('x',)): pass
        def func2(_: ['x', 'y']): pass
        def func3(_: 1): pass
        def func4() -> 1: pass
        def func5() -> []: pass
        def func6() -> (1, '2'): pass
        self.assertRaises(BootException, boot, func1)
        self.assertRaises(BootException, boot, func2)
        self.assertRaises(BootException, boot, func3)
        self.assertRaises(BootException, boot, func4)
        self.assertRaises(BootException, boot, func5)
        self.assertRaises(BootException, boot, func6)

    def test_annotate_twice(self):
        boot = Boot()
        def func(): pass
        self.assertEqual(func, boot(func))
        self.assertRaises(BootException, boot, func)

    def test_unsatisfable_dependency_1(self):
        boot = Boot()
        @boot
        def foo(x: ['x'], y: 'y'): pass
        self.assertRaises(BootException, boot.call, y=1)

    def test_unsatisfable_dependency_2(self):
        boot = Boot()
        @boot
        def func1(_: 'x') -> 'y': pass
        @boot
        def func2(_: 'y') -> 'z': pass
        @boot
        def func3(_: 'y') -> 'x': pass
        self.assertRaises(BootException, boot.call)


if __name__ == '__main__':
    unittest.main()
