#!/usr/bin/evn python3

"""Example of using startup to initialize a program."""

import argparse
import logging
import sys

from startup import startup


# This will show what startup is doing behind the scene.
logging.basicConfig(level=logging.INFO)


@startup
def create_argparser(argv: 'argv') -> 'parser':
    """Create an ArgumentParser.

    NOTE: You **must** annotate **all** non-optional parameters, which
    in this case, is ``argv``.
    """
    return argparse.ArgumentParser(
        prog=argv[0], description='Multiply X by Y.')


@startup
def add_argument_verbose(parser: 'parser') -> 'basic_opts':
    """Add -v to the argument parser.

    Use basic_opts as a tool for sequencing function calls.
    """
    parser.add_argument('-v', action='count', help='enable additional output')


@startup
def add_argument_x(parser: 'parser', _: 'basic_opts') -> 'opts':
    """Add -x argument.

    The dependencies of add_argument_{x,y} are satisfied at the same
    time, and in this case, startup calls them in lexicographical order
    by their names (not the order that they are added to startup, which
    varies when you reorder imports).  This should provide a stable
    and predictable function-call order.
    """
    parser.add_argument(
        '-x', type=int, default=0, help='set x value (default to %(default)s)')


@startup
def add_argument_y(parser: 'parser', _: 'basic_opts') -> 'opts':
    """Add -y argument."""
    parser.add_argument(
        '-y', type=int, default=0, help='set y value (default to %(default)s)')


@startup
def parse_argv(parser: 'parser', argv: 'argv', _: 'opts') -> 'args':
    """Parse argv.

    Depend dummy parameter '_' on 'opts' to make a join point on
    add_argument_{x,y} function calls.
    """
    return parser.parse_args(argv[1:])


def main(argv):
    """Call startup.call() in your main()."""
    args = startup.call(argv=argv)['args']
    if args.v:
        print('x * y = %d' % (args.x * args.y))
    else:
        print(args.x * args.y)
    return 0


@startup
def collect_opts(all_opts: ['opts']) -> 'all_opts':
    """Collect values of variable opts.

    startup.call returns a dict of variables' last value.  This is usually good
    enough (such as getting 'args' value in main).  If in cases you need all
    the values of a variable, you may collect them like here.

    In this case, all_opts is [None, None] because add_argument_{x,y} did
    not return anything.
    """
    return all_opts


if __name__ == '__main__':
    sys.exit(main(sys.argv))
