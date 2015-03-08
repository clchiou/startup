boot implements a function-call dependency graph resolver for
decoupling complex program initialization.

The initialization functions are annotated with input and output
dependencies, and boot will call them exactly once in topological
order.

Sample usage:

    from boot import boot

    @boot
    def parse_argv(argv: 'argv') -> 'args':
        args = {'config_path': argv[1]}
        return args

    @boot
    def read_config(args: 'args') -> 'config':
        with open(args['config_path']) as config_file:
            return config_file.read()

    def main(argv):
        config = boot.call(argv=argv)['config']

For more information, see `help(boot)`.
