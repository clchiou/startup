"""startup
=======

The ``Startup`` class implements a function-call graph dependency
resolver for decoupling complex program initialization sequence.

To use ``startup``, you annotate functions with which variables they
read or write (remainder: you **must** annotate **all** non-optional
parameters).  Then ``startup`` generates a dependency graph from the
annotations, and call them in a stable and predictable order.  Each
function will be called exactly once, and if a function has never been
called (due to unsatisfiable dependency), ``startup`` will raise a
``StartupException``.

Sample usage:

.. code-block:: python

    from startup import startup

    # 'argv' is the variable name that parse_argv reads from, and
    # 'args' is the variable name that parse_argv writes to.
    # NOTE: All non-optional parameters must be annotated.
    @startup
    def parse_argv(argv: 'argv') -> 'args':
        args = {'config_path': argv[1]}
        return args

    @startup
    def read_config(args: 'args') -> 'config':
        with open(args['config_path']) as config_file:
            return config_file.read()

    def main(argv):
        # You may provide variable values to startup, like argv in this
        # case, and you may read variable, like config, which will be
        # returned by startup.call().
        config = startup.call(argv=argv)['config']

You **must** annotate **all** non-optional parameters with a variable
name, but annotating return value is optional.  A parameter annotation
can be annotated in the form ``['var']``, and this function will read
all values written to ``'var'`` (see below).  A return value annotation
can be a tuple of variable names, which means unpacking return value.

The variables in function annotations are not real but merely ``dict``
keys that ``startup`` stores internally (``startup.call()`` will return
this ``dict`` so that you too may read these variables).

NOTE: Currently the annotation formats are very strict: A parameter
annotation must be either a ``str`` or an one-element list of ``str``,
and a return value annotation must be either a ``str`` or a tuple of
``str``.  The flexibility is reserved for future extensions.

The functions that are satisfied by the same set of dependencies are
called in lexicographical order by their module name and qualified name.
This way, even if you change code layout and/or import order, the
functions would still be called in the same order, and thus ``startup``
is stable and predictable.

A variable may be written multiple times (if multiple functions are
annotated to write to it).  In this case, ``startup`` will call the
reader functions only after all writer functions are called.  The
reader functions may choose to read the latest value or all the values
written to that variable (by ``['var']`` annotation form).

The fact that all readers are blocked by all writers can be used to
express common patterns of program initialization, such as joining or
sequencing function calls.


Why ``startup``?
----------------

Starting up a program could be complex but should not be complicated.
For example, ``main.py`` imports ``orm.py`` and ``orm.py`` imports
``db.py``.  Say you want to initialize them in the order of ``db.py``,
``main.py``, and then ``orm.py``.  Then ``main.py`` has to know that it
transitively imports ``db.py`` and should initialize ``db.py`` before
itself.  Things get even more complex when each module requires phases
of initialization.  We usually end up with ``main.py`` importing all
other modules and manually order the initializations.  I think this kind
of problem can be better solved with topological sort on the dependency
graphs.  Basically you annotate each module's dependencies and then
``startup`` will resolve a stable and predictable function-call ordering
for you.
"""

__version__ = '0.2.1'

__author__ = 'Che-Liang Chiou'
__author_email__ = 'clchiou@gmail.com'
__copyright__ = 'Copyright 2015, Che-Liang Chiou'
__license__ = 'MIT'

__all__ = [
    'startup',
]

import inspect
import logging
from collections import defaultdict, namedtuple


LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


class Startup:
    """See ``help(startup)``."""

    def __init__(self):
        """Create a ``Startup`` object.

        You usually just use the global ``Startup`` object:

        .. code-block:: python

            from startup import startup

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
        """Add ``func`` to this ``Startup`` object's dependency graph
        (a ``Startup`` object is usually used as a decorator).

        NOTE: ``func``'s non-optional parameters **must** be annotated.
        """
        if not callable(func):
            raise StartupException('%r is not callable' % func)
        if func in self.funcs:
            raise StartupException('cannot add %r twice' % func)
        not_annotated = _get_not_annotated(func)
        if not_annotated:
            raise StartupException(
                'non-optional parameters %r of %r are not annotated' %
                (not_annotated, func))
        arg_read_var = _parse_args(func, self.variables)
        writeto = _parse_ret(func, self.variables)
        closure = Closure(func, tuple(arg for arg, _ in arg_read_var), writeto)
        for _, var in arg_read_var:
            var.readers.append(closure)
        if closure.satisfied:
            self.satisfied.append(closure)
        self.funcs.add(func)
        LOG.info('added %s.%s', func.__module__, func.__qualname__)
        return func

    def call(self, **kwargs):
        """Call all the functions that have previously been added to the
        dependency graph in topological and lexicographical order, and
        then return variables in a ``dict``.

        You may provide variable values with keyword arguments.  These
        values will be written and can satisfy dependencies.

        NOTE: This object will be **destroyed** after ``call()`` returns
        and should not be used any further.
        """
        if not hasattr(self, 'funcs'):
            raise StartupException('startup cannot be called again')
        for name, var in self.variables.items():
            var.name = name
        for name in kwargs:
            self.variables[name].name = name
        queue = Closure.sort(self.satisfied)
        queue.extend(_write_values(kwargs, self.variables))
        while queue:
            closure = queue.pop(0)
            writeto = closure.call()
            self.funcs.remove(closure.func)
            queue.extend(_notify_reader_writes(writeto))
        if self.funcs:
            raise StartupException(
                'cannot satisfy dependency for %r' % self.funcs)
        values = {
            name: var.read_latest() for name, var in self.variables.items()
        }
        # Call _release() on normal exit only; otherwise keep the dead body for
        # forensic analysis.
        self._release()
        return values


Startup.__doc__ = __doc__  # Sync __doc__ contents.  DRY!


def _get_not_annotated(func):
    """Return non-optional parameters that are not annotated."""
    argspec = inspect.getfullargspec(func)
    args = argspec.args
    if argspec.defaults is not None:
        args = args[:-len(argspec.defaults)]
    kwonlyargs = argspec.kwonlyargs
    if argspec.kwonlydefaults is not None:
        kwonlyargs = kwonlyargs[:-len(argspec.kwonlydefaults)]
    return [arg for arg in args + kwonlyargs if arg not in argspec.annotations]


def _parse_args(func, variables):
    """Return a list of arguments with the variable it reads.

    NOTE: Multiple arguments may read the same variable.
    """
    arg_read_var = []
    for arg_name, anno in func.__annotations__.items():
        if arg_name == 'return':
            continue
        var, read = _parse_arg(func, variables, arg_name, anno)
        arg = Argument(name=arg_name, read=read)
        arg_read_var.append((arg, var))
    return arg_read_var


def _parse_arg(func, variables, arg_name, anno):
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
    raise StartupException(
        'cannot parse annotation %r of parameter %r for %r' %
        (anno, arg_name, func))


def _parse_ret(func, variables):
    """Parse func's return annotation and return either None, a variable,
    or a tuple of variables.

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
    raise StartupException(
        'cannot parse return annotation %r for %r' % (anno, func))


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
        self.name = None  # Set later by Startup.call().
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
        if self.readable:
            LOG.info('%s becomes readable', self.name)

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
        # Keep self.func because Startup still needs it.
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
        LOG.info('calling %s.%s', self.func.__module__, self.func.__qualname__)
        kwargs = {arg.name: arg.read() for arg in self.args}
        out_value = self.func(**kwargs)
        if self.writeto is None:
            writeto = set()
        elif isinstance(self.writeto, Variable):
            self.writeto.write(out_value)
            writeto = {self.writeto}
        else:
            # A variable can be written multiple times, but we only
            # return a unique set of variables.
            for var, value in zip(self.writeto, out_value):
                var.write(value)
            writeto = set(self.writeto)
        self._release()  # Only call _release() on normal exit.
        return writeto


class StartupException(Exception):
    """A generic error of startup."""


# The global startup object.
startup = Startup()
