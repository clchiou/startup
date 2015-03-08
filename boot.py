"""boot

This module implements a function-call dependency graph resolver
for decoupling complex program initialization.

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

"""

__version__ = '0.1.0'

__author__ = 'Che-Liang Chiou'
__author_email__ = 'clchiou@gmail.com'
__copyright__ = 'Copyright 2015, Che-Liang Chiou'
__license__ = 'MIT'

__all__ = [
    'boot',
]

from collections import defaultdict, namedtuple


class Boot:
    """Boot

    The Boot class implements a function-call graph dependency resolver
    for decoupling complex program initialization.

    For example, there are three modules A, B, and C where A imports
    B and B imports C.  Say you want to initialize them in the order
    of C, A, and the B.  Then A's initializer has to know that itself
    transitively imports C and it has to call C's initializer before
    calling its and then B's initializer.  We usually end up with A
    importing all its transitive closure and calling each module's
    initializer in A's initializer.  Things can get even worse when
    initializers are grouped in phases where one phase's initializers
    have to wait until all prior phases' initializers are completed.
    This kind of problem should really be resolved with a topological
    sort on dependency graph.

    To use boot, you annotate functions with which variables they
    read or write.  Then boot generates a dependency graph from the
    annotations, and call them in a stable and predictable order.
    Each function will be called exactly once, and if a function has
    never been called (due to unsatisfiable dependency), boot will
    raise a BootException.

    The functions that are satisfied by the same set of dependencies
    are called in lexicographical order by their module name and
    qualified name.  This way, even if you change code layout and/or
    import order, the functions should still be called in the same
    order, and thus boot is stable and predictable.

    The variables are not real but merely values that boot stores
    internally in a dict (boot will return a variable dict after it
    finishes calling all the functions).

    A variable may be written multiple times (if multiple functions
    are annotated to write to it).  In this case, boot will call the
    reader functions only after all writer functions are called.  The
    reader functions may choose to read the latest value (default)
    or all the values written to that variable.

    The fact that all readers are blocked by all writers can be used
    to express common patterns of program initialization, such as
    joining or sequencing function calls.

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

    You must annotate every non-optional parameter with a variable name.
    Annotating return value is optional.  If a parameter annotation is
    of the form ['var'], this function will read all values written to
    that variable.  A return value annotation can be a tuple of variable
    names, and in this case, the function's return value is unpacked.

    NOTE: Currently the annotation formats are very strict: A parameter
    annotation must be either a str or an one-element list of str, and
    a return value annotation must be either a str or a tuple of str.
    We reserve the flexibility for future extensions.
    """

    def __init__(self):
        """Create a Boot object.

        You usually just use the global Boot object:

            from boot import boot

        """
        self.funcs = set()
        self.variables = defaultdict(Variable)
        self.satisfied = []

    def _release(self):
        """Destroy self since closures cannot be called again."""
        del self.funcs
        del self.variables
        del self.satisfied

    def __call__(self, func):
        """Add func to this Boot object's dependency graph (a Boot
        object is usually used as a decorator).

        NOTE: func's non-optional parameters must be annotated.
        """
        if not callable(func):
            raise BootException('\'%r\' is not callable' % func)
        if func in self.funcs:
            raise BootException('cannot add \'%r\' twice' % func)
        arg_read_var = _parse_args(func, self.variables)
        writeto = _parse_ret(func, self.variables)
        closure = Closure(func, tuple(arg for arg, _ in arg_read_var), writeto)
        for _, var in arg_read_var:
            var.readers.append(closure)
        if closure.satisfied:
            self.satisfied.append(closure)
        self.funcs.add(func)
        return func

    def call(self, **kwargs):
        """Call all the functions that have previously been added to
        the dependency graph in topological and lexicographical
        order, and then return variables in a dict.

        You may provide variable values with keyword arguments.
        These values will be written and can satisfy dependencies.

        NOTE: This object will be in a "destroyed" state after
        this function returns and should not be used.
        """
        if not hasattr(self, 'funcs'):
            raise BootException('boot cannot be called again')
        queue = Closure.sort(self.satisfied)
        queue.extend(_write_values(kwargs, self.variables))
        while queue:
            closure = queue.pop(0)
            writeto = closure.call()
            self.funcs.remove(closure.func)
            queue.extend(_notify_reader_writes(writeto))
        if self.funcs:
            raise BootException(
                'cannot satisfy dependency for %r' % self.funcs)
        values = {
            name: var.read_latest() for name, var in self.variables.items()
        }
        # Call _release() on normal exit only; otherwise keep the dead body for
        # forensic analysis.
        self._release()
        return values


def _parse_args(func, variables):
    """Return a list of arguments with the variable it reads.

    NOTE: Multiple arguments may read the same variable.
    """
    arg_read_var = []
    for arg_name, anno in func.__annotations__.items():
        if arg_name == 'return':
            continue
        var, read = _parse_arg_anno(func, variables, arg_name, anno)
        arg = Argument(name=arg_name, read=read)
        arg_read_var.append((arg, var))
    return arg_read_var


def _parse_arg_anno(func, variables, arg_name, anno):
    """Parse an argument's annotation."""
    if isinstance(anno, str):
        var = variables[anno]
        return var, var.read_latest
    elif (isinstance(anno, list) and len(anno) == 1 and
          isinstance(anno[0], str)):
        var = variables[anno[0]]
        return var, var.read_all
    # For now, be very strict about annotation format (e.g.,
    # allow list but not tuple) because we might want to use
    # tuple for other meanings in the future.
    raise BootException(
        'cannot parse annotation \'%r\' of \'%s\' for \'%r\'' %
        (anno, arg_name, func))


def _parse_ret(func, variables):
    """Parse func's return annotation and return either None, a var name,
    or a tuple of var names.

    NOTE:
      * _parse_ret() also notifies variables about will-writes.
      * A variable can be written multiple times per return annotation.
    """
    anno = func.__annotations__.get('return')
    if anno is None:
        return None
    elif isinstance(anno, str):
        writeto = variables[anno]
        writeto.notify_will_write()
        return writeto
    elif (isinstance(anno, tuple) and
          all(isinstance(name, str) for name in anno)):
        writeto = tuple(variables[name] for name in anno)
        for var in writeto:
            var.notify_will_write()
        return writeto
    # Be very strict about annotation format for now.
    raise BootException(
        'cannot parse return annotation \'%r\' for \'%r\'' % (anno, func))


def _write_values(kwargs, variables):
    """Write values of kwargs and return thus-satisfied closures."""
    writeto = []
    for var_name, value in kwargs.items():
        var = variables[var_name]
        var.notify_will_write()
        var.write(value)
        writeto.append(var)
    return _notify_reader_writes(writeto)


def _notify_reader_writes(writeto):
    """Notify reader closures about these writes and return a sorted
       list of thus-satisfied closures.
    """
    satisfied = []
    for var in writeto:
        if var.readable:
            for reader in var.readers:
                reader.notify_read_ready()
                if reader.satisfied:
                    satisfied.append(reader)
    return Closure.sort(satisfied)


class Variable:
    """A Variable object stores all (past) values written to it and arguments
    that need to read its value(s).
    """

    def __init__(self):
        # Number of writers that this variable is waiting for.
        self.num_write_waits = 0
        # Functions that need to read this variable.
        self.readers = []
        # All past and current values.
        self.values = []

    def __repr__(self):
        return ('Variable{%d, %r, %r}' %
                (self.num_write_waits, self.readers, self.values))

    def notify_will_write(self):
        """Notify that a writer will write to this variable."""
        self.num_write_waits += 1

    @property
    def readable(self):
        """True when arguments may read this variable."""
        assert self.num_write_waits >= 0, self
        return self.num_write_waits == 0 and self.values

    def write(self, value):
        """Write a (new) value to this variable."""
        assert self.num_write_waits > 0, self
        self.num_write_waits -= 1
        self.values.append(value)

    def read_latest(self):
        """Read the latest value."""
        assert self.readable, self
        return self.values[-1]

    def read_all(self):
        """Read all values."""
        assert self.readable, self
        return self.values


# An argument merely binds a function with a variable.
Argument = namedtuple('Argument', 'name read')


class Closure:
    """A closure can be called at most once."""

    @staticmethod
    def sort(closures):
        """Sort closures lexicographically *in-place*."""
        closures.sort(key=Closure._key)
        return closures

    @staticmethod
    def _key(closure):
        """Lexicographical order of a function."""
        return (closure.func.__module__, closure.func.__qualname__)

    def __init__(self, func, args, writeto):
        self.func = func
        self.args = args
        # Variables that this function writes to.
        self.writeto = writeto
        # Number of arguments that are waiting for read-ready.
        self.num_read_ready_waits = len(args)

    def __repr__(self):
        return 'Closure{%r, %d}' % (self.func, self.num_read_ready_waits)

    def _release(self):
        """Destroy self since closure can be called only once."""
        # Keep self.func because Boot still needs it.
        del self.args
        del self.writeto
        del self.num_read_ready_waits

    def notify_read_ready(self):
        """Notify that an argument's value is ready to be read."""
        assert self.num_read_ready_waits > 0, self
        self.num_read_ready_waits -= 1

    @property
    def satisfied(self):
        """True if this closure's dependencies are satisfied."""
        assert self.num_read_ready_waits >= 0, self
        return self.num_read_ready_waits == 0

    def call(self):
        """Call the closure and return variable(s) that is written."""
        assert self.satisfied, self
        kwargs = {arg.name: arg.read() for arg in self.args}
        out_value = self.func(**kwargs)
        if self.writeto is None:
            writeto = ()
        elif isinstance(self.writeto, Variable):
            self.writeto.write(out_value)
            writeto = (self.writeto,)
        else:
            # A variable can be written multiple times, but we only
            # return a unique set of variables.
            for var, value in zip(self.writeto, out_value):
                var.write(value)
            writeto = set(self.writeto)
        self._release()  # Only call _release() on normal exit.
        return writeto


class BootException(Exception):
    """A generic error of boot."""


# The global boot object.
boot = Boot()
