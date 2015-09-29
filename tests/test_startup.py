import unittest

import inspect

from startup import StartupError
from startup import Startup


class StartupTest(unittest.TestCase):

    def test_annotate_all_nonoptional_parameters(self):
        startup = Startup()
        def func1(x): pass
        def func2(x, y=1): pass
        def func3(x, y=1, z=2): pass
        def func4(*, a): pass
        def func5(*, a, b=1): pass
        def func6(*, a, b=1, c=2): pass
        self.assertRaises(StartupError, startup, func1)
        self.assertRaises(StartupError, startup, func2)
        self.assertRaises(StartupError, startup, func3)
        self.assertRaises(StartupError, startup, func4)
        self.assertRaises(StartupError, startup, func5)
        self.assertRaises(StartupError, startup, func6)

    def test_lexicographical_order(self):
        startup = Startup()
        data = []
        @startup
        def func2():
            data.append(2)
        @startup
        def func1():
            data.append(1)
        @startup
        def func3():
            data.append(3)
        self.assertEqual({}, startup.call())
        self.assertEqual([1, 2, 3], data)
        # You cannot call run() again, by the way.
        self.assertRaises(StartupError, startup.call)

    def test_sequential_order(self):
        startup = Startup()
        data = []
        @startup
        def func3(x: 'x') -> 'y':
            data.append(x)
            return x - 1
        @startup
        def func2(y: 'y') -> 'z':
            data.append(y)
            return y - 1
        @startup
        def func1(z: 'z'):
            data.append(z)
        self.assertEqual({'x': 3, 'y': 2, 'z': 1}, startup.call(x=3))
        self.assertEqual([3, 2, 1], data)

    def test_join(self):
        startup = Startup()
        data = []
        @startup
        def func2() -> 'x':
            data.append(2)
            return 2
        @startup
        def func1() -> 'x':
            data.append(1)
            return 1
        @startup
        def func3() -> 'x':
            data.append(3)
            return 3
        @startup
        def func_join_1(x: ['x']):
            self.assertEqual([1, 2, 3], x)
            data.append('join')
        self.assertEqual({'x': 3}, startup.call())
        self.assertEqual([1, 2, 3, 'join'], data)

    def test_multiple_return_1(self):
        startup = Startup()
        data = []
        @startup
        def func() -> ('x', 'y', 'z'):
            return 'x-str', 'y-str', 'z-str'
        @startup
        def func_z(z: 'z'):
            self.assertEqual('z-str', z)
            data.append('z')
        @startup
        def func_x(x: 'x'):
            self.assertEqual('x-str', x)
            data.append('x')
        @startup
        def func_y(y: 'y'):
            self.assertEqual('y-str', y)
            data.append('y')
        self.assertEqual(
            {'x': 'x-str', 'y': 'y-str', 'z': 'z-str'}, startup.call())
        self.assertEqual(['x', 'y', 'z'], data)

    def test_multiple_return_2(self):
        startup = Startup()
        @startup
        def func_repeat() -> ('x', 'x', 'x'):
            return 1, 3, 2
        @startup
        def func_collect(xs: ['x']) -> 'xs':
            return xs
        self.assertEqual({'xs': [1, 3, 2], 'x': 2}, startup.call())

    def test_wrong_annotations(self):
        startup = Startup()
        def func1(_: ('x',)): pass
        def func2(_: ['x', 'y']): pass
        def func3(_: 1): pass
        def func4() -> 1: pass
        def func5() -> []: pass
        def func6() -> (1, '2'): pass
        self.assertRaises(StartupError, startup, func1)
        self.assertRaises(StartupError, startup, func2)
        self.assertRaises(StartupError, startup, func3)
        self.assertRaises(StartupError, startup, func4)
        self.assertRaises(StartupError, startup, func5)
        self.assertRaises(StartupError, startup, func6)

    def test_annotate_twice(self):
        startup = Startup()
        def func(): pass
        self.assertEqual(func, startup(func))
        self.assertRaises(StartupError, startup, func)

    def test_unsatisfable_dependency_1(self):
        startup = Startup()
        @startup
        def foo(x: ['x'], y: 'y'): pass
        self.assertRaises(StartupError, startup.call, y=1)

    def test_unsatisfable_dependency_2(self):
        startup = Startup()
        @startup
        def func1(_: 'x') -> 'y': pass
        @startup
        def func2(_: 'y') -> 'z': pass
        @startup
        def func3(_: 'y') -> 'x': pass
        self.assertRaises(StartupError, startup.call)

    def test_set_variable(self):

        def func1(_: '#x') -> '#y': return 2
        def func2(_: '#x') -> '#z': return 3

        startup = Startup()
        startup.set('#x', 1)
        self.assertDictEqual({'#x': 1}, startup.call())

        # Call Startup.set() before registering functions.
        startup = Startup()
        startup.set('#x', 1)
        startup.set('#z', 0)
        startup(func1)
        startup(func2)
        self.assertDictEqual({'#x': 1, '#y': 2, '#z': 3}, startup.call())

        # Call Startup.set() after registering functions.
        startup = Startup()
        startup(func1)
        startup(func2)
        startup.set('#x', 1)
        startup.set('#z', 0)
        self.assertDictEqual({'#x': 1, '#y': 2, '#z': 3}, startup.call())

        # Overwrite Startup.set().
        startup = Startup()
        startup.set('x', 1)
        self.assertDictEqual({'x': 2}, startup.call(x=2))

        with self.assertRaises(StartupError):
            startup.set('v', 1)

    def test_with_annotations(self):
        startup = Startup()

        @startup.with_annotations({'a': 'a', 'b': 'b', 'return': 'c'})
        def func(a, b): return (a, b)

        self.assertDictEqual(
            {'a': 1, 'b': 2, 'c': (1, 2)}, startup.call(a=1, b=2))

    def test_class_and_method(self):
        startup = Startup()

        @startup.with_annotations({'return': 'foo'})
        class Foo:
            def __init__(self):
                pass

        @startup.with_annotations({'return': 'bar'})
        class Bar:

            @classmethod
            def c(cls):
                return 'c'

            def m(self):
                return 'm'

        self.assertListEqual(['self'], inspect.getfullargspec(Foo).args)
        self.assertListEqual([], inspect.getfullargspec(Bar).args)

        self.assertListEqual(['cls'], inspect.getfullargspec(Bar.c).args)
        self.assertTrue(inspect.ismethod(Bar.c))

        self.assertListEqual(['self'], inspect.getfullargspec(Bar().m).args)
        self.assertTrue(inspect.ismethod(Bar().m))

        startup.add_func(Bar.c, {'return': 'c'})
        startup.add_func(Bar().m, {'return': 'm'})

        variables = startup.call()
        self.assertTrue(isinstance(variables['foo'], Foo))
        self.assertTrue(isinstance(variables['bar'], Bar))
        self.assertEqual('c', variables['c'])
        self.assertTrue('m', variables['m'])


if __name__ == '__main__':
    unittest.main()
