startup
=======

``startup`` implements a function-call dependency graph resolver
for decoupling complex program startup.

Functions are annotated with input and output dependencies, and
``startup`` will call them exactly once in topological order.

Sample usage:

.. code-block:: python

    from startup import startup

    @startup
    def parse_argv(argv: 'argv') -> 'args':
        args = {'config_path': argv[1]}
        return args

    @startup
    def read_config(args: 'args') -> 'config':
        with open(args['config_path']) as config_file:
            return config_file.read()

    def main(argv):
        config = startup.call(argv=argv)['config']

For more information, see ``help(startup)``.
