import unittest

import startup
from startup import StartupException
from startup import Variable


class TestParseArgs(unittest.TestCase):

    def test_parse_args_0(self):
        func = Mock({'return': 'y'})
        arg_read_var = startup._parse_args(func, {})
        self.assertEqual(0, len(arg_read_var))

    def test_parse_args_1(self):
        func = Mock({'return': 'y', 'x': 'x'})
        var_x = Variable()
        arg_read_var = startup._parse_args(func, {'x': var_x})
        self.assertEqual(1, len(arg_read_var))
        arg, var = arg_read_var[0]
        self.assertEqual('x', arg.name)
        self.assertEqual(var_x.read_latest, arg.read)
        self.assertEqual(var_x, var)

    def test_parse_args_many(self):
        letters = 'abcdefghijklmnopqrstuvwxyz'
        annos = {'return': 'ret'}
        for arg_name in letters:
            var_name = arg_name.upper()
            annos[arg_name] = var_name
        func = Mock(annos)
        variables = {letter.upper(): Variable for letter in letters}
        arg_read_var = startup._parse_args(func, variables)
        self.assertEqual(len(letters), len(arg_read_var))
        arg_names = []
        for arg, var in arg_read_var:
            letter = arg.name
            arg_names.append(arg.name)
            self.assertTrue(letter in letters)
            self.assertEqual(var.read_latest, arg.read)
            self.assertEqual(variables[letter.upper()], var)
        self.assertEqual(letters, ''.join(sorted(arg_names)))

    def test_read_all_values(self):
        func = Mock({'x': ['var']})
        var = Variable()
        arg_read_var = startup._parse_args(func, {'var': var})
        self.assertEqual(1, len(arg_read_var))
        arg = arg_read_var[0][0]
        self.assertEqual('x', arg.name)
        self.assertEqual(var.read_all, arg.read)

    def test_read_many_times(self):
        func = Mock({'x': 'var', 'y': 'var', 'z': 'var'})
        var = Variable()
        arg_read_var = startup._parse_args(func, {'var': var})
        self.assertEqual(3, len(arg_read_var))
        self.assertEqual(
            ['x', 'y', 'z'], sorted(arg.name for arg, _ in arg_read_var))
        self.assertEqual([var, var, var], [var for _, var in arg_read_var])

    def test_wrong_anno(self):
        func = Mock({'x': ['x', 'y']})
        self.assertRaises(
            StartupException, startup._parse_args, func, {})

        func = Mock({'x': 1})
        self.assertRaises(
            StartupException, startup._parse_args, func, {})

        func = Mock({'x': ('x',)})
        self.assertRaises(
            StartupException, startup._parse_args, func, {})


class TestParseRet(unittest.TestCase):

    def test_parse_ret_0(self):
        func = Mock({})
        self.assertEqual(None, startup._parse_ret(func, {}))

        func = Mock({'return': None})
        self.assertEqual(None, startup._parse_ret(func, {}))

    def test_parse_ret_1(self):
        var = Variable()
        func = Mock({'return': 'x'})
        self.assertEqual(var, startup._parse_ret(func, {'x': var}))

    def test_parse_ret_many(self):
        var_x = Variable()
        var_y = Variable()
        func = Mock({'return': ('x', 'x', 'y')})
        self.assertEqual(
            (var_x, var_x, var_y),
            startup._parse_ret(func, {'x': var_x, 'y': var_y}))

    def test_wrong_anno(self):
        func = Mock({'return': 1})
        self.assertRaises(
            StartupException, startup._parse_ret, func, {})

        func = Mock({'return': ['x']})
        self.assertRaises(
            StartupException, startup._parse_ret, func, {})

        func = Mock({'return': ['x', 'y']})
        self.assertRaises(
            StartupException, startup._parse_ret, func, {})


class Mock:
    def __init__(self, annotations):
        self.__annotations__ = annotations


if __name__ == '__main__':
    unittest.main()

