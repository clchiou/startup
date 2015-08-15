import itertools
import random
import unittest

from startup import Argument, Closure, Variable


class ClosureTest(unittest.TestCase):

    class Inner:
        def foo(self):
            pass
        def bar(self):
            return itertools.count()
        def spam(self):
            pass
        def viz(self):
            pass

    @staticmethod
    def closure(func):
        return Closure(func, (), ())

    @staticmethod
    def as_closures(funcs):
        return [ClosureTest.closure(func) for func in funcs]

    @staticmethod
    def as_funcs(closures):
        return [closure.func for closure in closures]

    def setUp(self):
        # Deterministic random behavior.
        random.seed(7)

    def tearDown(self):
        # Restore randomness.
        random.seed()

    def test_key(self):
        self.assertEqual(
            ('tests.test_closure', 'ClosureTest.Inner.foo'),
            Closure._key(self.closure(ClosureTest.Inner.foo)))

        self.assertEqual(
            ('tests.test_closure', 'ClosureTest.Inner'),
            Closure._key(self.closure(ClosureTest.Inner)))

    def test_sort(self):
        self.assertEqual([], Closure.sort([]))

        funcs = [ClosureTest.Inner.foo]
        self.assertEqual(
            funcs, self.as_funcs(Closure.sort(self.as_closures(funcs))))

        funcs = [
            ClosureTest.Inner.bar,
            ClosureTest.Inner.foo,
            ClosureTest.Inner.spam,
            ClosureTest.Inner.viz,
        ]
        closures = self.as_closures(funcs)
        random.shuffle(closures)
        self.assertEqual(funcs, self.as_funcs(Closure.sort(closures)))

    def test_call(self):
        def foo(**kwargs):
            return [kwargs[key] for key in sorted(kwargs)]
        make_arg = lambda n: Argument('arg%d' % n, lambda: n)
        for n_args in [0, 1, 2, 4, 8, 16]:
            args = []
            writeto = []
            for i in range(n_args):
                args.append(make_arg(i))
                var = Variable()
                var.notify_will_write()
                writeto.append(var)
            closure = Closure(foo, args, writeto)
            for _ in range(n_args):
                self.assertFalse(closure.satisfied)
                closure.notify_read_ready()
            self.assertTrue(closure.satisfied)
            self.assertEqual(set(writeto), closure.call())

    def test_writeto(self):
        inner = ClosureTest.Inner()
        closure = Closure(inner.bar, (), None)
        self.assertTrue(closure.satisfied)
        self.assertEqual(set(), closure.call())
        self.assertRaises(Exception, closure.call)

        var = Variable()
        var.notify_will_write()
        closure = Closure(inner.bar, (), var)
        self.assertTrue(closure.satisfied)
        self.assertEqual({var}, closure.call())

        writeto = [Variable() for _ in range(10)]
        writeto_set = set(writeto)
        for var in writeto:
            var.notify_will_write()
        closure = Closure(inner.bar, (), writeto)
        self.assertTrue(closure.satisfied)
        self.assertEqual(writeto_set, closure.call())
        for i in range(10):
            self.assertEqual([i], writeto[i].values)

        var = Variable()
        writeto = []
        for _ in range(10):
            var.notify_will_write()
            writeto.append(var)
        closure = Closure(inner.bar, (), writeto)
        self.assertTrue(closure.satisfied)
        self.assertEqual({var}, closure.call())
        self.assertEqual([i for i in range(10)], var.values)

    def test_satisfied(self):
        for n_args in [0, 1, 2, 4, 8, 16]:
            closure = Closure(None, 'x' * n_args, None)
            for _ in range(n_args):
                self.assertFalse(closure.satisfied)
                closure.notify_read_ready()
            self.assertTrue(closure.satisfied)
            self.assertRaises(AssertionError, closure.notify_read_ready)


if __name__ == '__main__':
    unittest.main()
