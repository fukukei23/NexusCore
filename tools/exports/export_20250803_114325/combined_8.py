
# === NexusCore/openenv\Lib\site-packages\IPython\lib\pretty.py ===
"""
Python advanced pretty printer.  This pretty printer is intended to
replace the old `pprint` python module which does not allow developers
to provide their own pretty print callbacks.

This module is based on ruby's `prettyprint.rb` library by `Tanaka Akira`.


Example Usage
-------------

To directly print the representation of an object use `pprint`::

    from pretty import pprint
    pprint(complex_object)

To get a string of the output use `pretty`::

    from pretty import pretty
    string = pretty(complex_object)


Extending
---------

The pretty library allows developers to add pretty printing rules for their
own objects.  This process is straightforward.  All you have to do is to
add a `_repr_pretty_` method to your object and call the methods on the
pretty printer passed::

    class MyObject(object):

        def _repr_pretty_(self, p, cycle):
            ...

Here's an example for a class with a simple constructor::

    class MySimpleObject:

        def __init__(self, a, b, *, c=None):
            self.a = a
            self.b = b
            self.c = c

        def _repr_pretty_(self, p, cycle):
            ctor = CallExpression.factory(self.__class__.__name__)
            if self.c is None:
                p.pretty(ctor(a, b))
            else:
                p.pretty(ctor(a, b, c=c))

Here is an example implementation of a `_repr_pretty_` method for a list
subclass::

    class MyList(list):

        def _repr_pretty_(self, p, cycle):
            if cycle:
                p.text('MyList(...)')
            else:
                with p.group(8, 'MyList([', '])'):
                    for idx, item in enumerate(self):
                        if idx:
                            p.text(',')
                            p.breakable()
                        p.pretty(item)

The `cycle` parameter is `True` if pretty detected a cycle.  You *have* to
react to that or the result is an infinite loop.  `p.text()` just adds
non breaking text to the output, `p.breakable()` either adds a whitespace
or breaks here.  If you pass it an argument it's used instead of the
default space.  `p.pretty` prettyprints another object using the pretty print
method.

The first parameter to the `group` function specifies the extra indentation
of the next line.  In this example the next item will either be on the same
line (if the items are short enough) or aligned with the right edge of the
opening bracket of `MyList`.

If you just want to indent something you can use the group function
without open / close parameters.  You can also use this code::

    with p.indent(2):
        ...

Inheritance diagram:

.. inheritance-diagram:: IPython.lib.pretty
   :parts: 3

:copyright: 2007 by Armin Ronacher.
            Portions (c) 2009 by Robert Kern.
:license: BSD License.
"""

from contextlib import contextmanager
import datetime
import os
import re
import sys
import types
from collections import deque
from inspect import signature
from io import StringIO
from warnings import warn

from IPython.utils.decorators import undoc
from IPython.utils.py3compat import PYPY

from typing import Dict

__all__ = ['pretty', 'pprint', 'PrettyPrinter', 'RepresentationPrinter',
    'for_type', 'for_type_by_name', 'RawText', 'RawStringLiteral', 'CallExpression']


MAX_SEQ_LENGTH = 1000
_re_pattern_type = type(re.compile(''))

def _safe_getattr(obj, attr, default=None):
    """Safe version of getattr.

    Same as getattr, but will return ``default`` on any Exception,
    rather than raising.
    """
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default

def _sorted_for_pprint(items):
    """
    Sort the given items for pretty printing. Since some predictable
    sorting is better than no sorting at all, we sort on the string
    representation if normal sorting fails.
    """
    items = list(items)
    try:
        return sorted(items)
    except Exception:
        try:
            return sorted(items, key=str)
        except Exception:
            return items

def pretty(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Pretty print the object's representation.
    """
    stream = StringIO()
    printer = RepresentationPrinter(stream, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    return stream.getvalue()


def pprint(obj, verbose=False, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
    """
    Like `pretty` but print to stdout.
    """
    printer = RepresentationPrinter(sys.stdout, verbose, max_width, newline, max_seq_length=max_seq_length)
    printer.pretty(obj)
    printer.flush()
    sys.stdout.write(newline)
    sys.stdout.flush()

class _PrettyPrinterBase:

    @contextmanager
    def indent(self, indent):
        """with statement support for indenting/dedenting."""
        self.indentation += indent
        try:
            yield
        finally:
            self.indentation -= indent

    @contextmanager
    def group(self, indent=0, open='', close=''):
        """like begin_group / end_group but for the with statement."""
        self.begin_group(indent, open)
        try:
            yield
        finally:
            self.end_group(indent, close)

class PrettyPrinter(_PrettyPrinterBase):
    """
    Baseclass for the `RepresentationPrinter` prettyprinter that is used to
    generate pretty reprs of objects.  Contrary to the `RepresentationPrinter`
    this printer knows nothing about the default pprinters or the `_repr_pretty_`
    callback method.
    """

    def __init__(self, output, max_width=79, newline='\n', max_seq_length=MAX_SEQ_LENGTH):
        self.output = output
        self.max_width = max_width
        self.newline = newline
        self.max_seq_length = max_seq_length
        self.output_width = 0
        self.buffer_width = 0
        self.buffer = deque()

        root_group = Group(0)
        self.group_stack = [root_group]
        self.group_queue = GroupQueue(root_group)
        self.indentation = 0

    def _break_one_group(self, group):
        while group.breakables:
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width
        while self.buffer and isinstance(self.buffer[0], Text):
            x = self.buffer.popleft()
            self.output_width = x.output(self.output, self.output_width)
            self.buffer_width -= x.width

    def _break_outer_groups(self):
        while self.max_width < self.output_width + self.buffer_width:
            group = self.group_queue.deq()
            if not group:
                return
            self._break_one_group(group)

    def text(self, obj):
        """Add literal text to the output."""
        width = len(obj)
        if self.buffer:
            text = self.buffer[-1]
            if not isinstance(text, Text):
                text = Text()
                self.buffer.append(text)
            text.add(obj, width)
            self.buffer_width += width
            self._break_outer_groups()
        else:
            self.output.write(obj)
            self.output_width += width

    def breakable(self, sep=' '):
        """
        Add a breakable separator to the output.  This does not mean that it
        will automatically break here.  If no breaking on this position takes
        place the `sep` is inserted which default to one space.
        """
        width = len(sep)
        group = self.group_stack[-1]
        if group.want_break:
            self.flush()
            self.output.write(self.newline)
            self.output.write(' ' * self.indentation)
            self.output_width = self.indentation
            self.buffer_width = 0
        else:
            self.buffer.append(Breakable(sep, width, self))
            self.buffer_width += width
            self._break_outer_groups()

    def break_(self):
        """
        Explicitly insert a newline into the output, maintaining correct indentation.
        """
        group = self.group_queue.deq()
        if group:
            self._break_one_group(group)
        self.flush()
        self.output.write(self.newline)
        self.output.write(' ' * self.indentation)
        self.output_width = self.indentation
        self.buffer_width = 0


    def begin_group(self, indent=0, open=''):
        """
        Begin a group.
        The first parameter specifies the indentation for the next line (usually
        the width of the opening text), the second the opening text.  All
        parameters are optional.
        """
        if open:
            self.text(open)
        group = Group(self.group_stack[-1].depth + 1)
        self.group_stack.append(group)
        self.group_queue.enq(group)
        self.indentation += indent

    def _enumerate(self, seq):
        """like enumerate, but with an upper limit on the number of items"""
        for idx, x in enumerate(seq):
            if self.max_seq_length and idx >= self.max_seq_length:
                self.text(',')
                self.breakable()
                self.text('...')
                return
            yield idx, x

    def end_group(self, dedent=0, close=''):
        """End a group. See `begin_group` for more details."""
        self.indentation -= dedent
        group = self.group_stack.pop()
        if not group.breakables:
            self.group_queue.remove(group)
        if close:
            self.text(close)

    def flush(self):
        """Flush data that is left in the buffer."""
        for data in self.buffer:
            self.output_width += data.output(self.output, self.output_width)
        self.buffer.clear()
        self.buffer_width = 0


def _get_mro(obj_class):
    """ Get a reasonable method resolution order of a class and its superclasses
    for both old-style and new-style classes.
    """
    if not hasattr(obj_class, '__mro__'):
        # Old-style class. Mix in object to make a fake new-style class.
        try:
            obj_class = type(obj_class.__name__, (obj_class, object), {})
        except TypeError:
            # Old-style extension type that does not descend from object.
            # FIXME: try to construct a more thorough MRO.
            mro = [obj_class]
        else:
            mro = obj_class.__mro__[1:-1]
    else:
        mro = obj_class.__mro__
    return mro


class RepresentationPrinter(PrettyPrinter):
    """
    Special pretty printer that has a `pretty` method that calls the pretty
    printer for a python object.

    This class stores processing data on `self` so you must *never* use
    this class in a threaded environment.  Always lock it or reinstanciate
    it.

    Instances also have a verbose flag callbacks can access to control their
    output.  For example the default instance repr prints all attributes and
    methods that are not prefixed by an underscore if the printer is in
    verbose mode.
    """

    def __init__(self, output, verbose=False, max_width=79, newline='\n',
        singleton_pprinters=None, type_pprinters=None, deferred_pprinters=None,
        max_seq_length=MAX_SEQ_LENGTH):

        PrettyPrinter.__init__(self, output, max_width, newline, max_seq_length=max_seq_length)
        self.verbose = verbose
        self.stack = []
        if singleton_pprinters is None:
            singleton_pprinters = _singleton_pprinters.copy()
        self.singleton_pprinters = singleton_pprinters
        if type_pprinters is None:
            type_pprinters = _type_pprinters.copy()
        self.type_pprinters = type_pprinters
        if deferred_pprinters is None:
            deferred_pprinters = _deferred_type_pprinters.copy()
        self.deferred_pprinters = deferred_pprinters

    def pretty(self, obj):
        """Pretty print the given object."""
        obj_id = id(obj)
        cycle = obj_id in self.stack
        self.stack.append(obj_id)
        self.begin_group()
        try:
            obj_class = _safe_getattr(obj, '__class__', None) or type(obj)
            # First try to find registered singleton printers for the type.
            try:
                printer = self.singleton_pprinters[obj_id]
            except (TypeError, KeyError):
                pass
            else:
                return printer(obj, self, cycle)
            # Next walk the mro and check for either:
            #   1) a registered printer
            #   2) a _repr_pretty_ method
            for cls in _get_mro(obj_class):
                if cls in self.type_pprinters:
                    # printer registered in self.type_pprinters
                    return self.type_pprinters[cls](obj, self, cycle)
                else:
                    # deferred printer
                    printer = self._in_deferred_types(cls)
                    if printer is not None:
                        return printer(obj, self, cycle)
                    else:
                        # Finally look for special method names.
                        # Some objects automatically create any requested
                        # attribute. Try to ignore most of them by checking for
                        # callability.
                        if '_repr_pretty_' in cls.__dict__:
                            meth = cls._repr_pretty_
                            if callable(meth):
                                return meth(obj, self, cycle)
                        if (
                            cls is not object
                            # check if cls defines __repr__
                            and "__repr__" in cls.__dict__
                            # check if __repr__ is callable.
                            # Note: we need to test getattr(cls, '__repr__')
                            #   instead of cls.__dict__['__repr__']
                            #   in order to work with descriptors like partialmethod,
                            and callable(_safe_getattr(cls, "__repr__", None))
                        ):
                            return _repr_pprint(obj, self, cycle)

            return _default_pprint(obj, self, cycle)
        finally:
            self.end_group()
            self.stack.pop()

    def _in_deferred_types(self, cls):
        """
        Check if the given class is specified in the deferred type registry.

        Returns the printer from the registry if it exists, and None if the
        class is not in the registry. Successful matches will be moved to the
        regular type registry for future use.
        """
        mod = _safe_getattr(cls, '__module__', None)
        name = _safe_getattr(cls, '__name__', None)
        key = (mod, name)
        printer = None
        if key in self.deferred_pprinters:
            # Move the printer over to the regular registry.
            printer = self.deferred_pprinters.pop(key)
            self.type_pprinters[cls] = printer
        return printer


class Printable:

    def output(self, stream, output_width):
        return output_width


class Text(Printable):

    def __init__(self):
        self.objs = []
        self.width = 0

    def output(self, stream, output_width):
        for obj in self.objs:
            stream.write(obj)
        return output_width + self.width

    def add(self, obj, width):
        self.objs.append(obj)
        self.width += width


class Breakable(Printable):

    def __init__(self, seq, width, pretty):
        self.obj = seq
        self.width = width
        self.pretty = pretty
        self.indentation = pretty.indentation
        self.group = pretty.group_stack[-1]
        self.group.breakables.append(self)

    def output(self, stream, output_width):
        self.group.breakables.popleft()
        if self.group.want_break:
            stream.write(self.pretty.newline)
            stream.write(' ' * self.indentation)
            return self.indentation
        if not self.group.breakables:
            self.pretty.group_queue.remove(self.group)
        stream.write(self.obj)
        return output_width + self.width


class Group(Printable):

    def __init__(self, depth):
        self.depth = depth
        self.breakables = deque()
        self.want_break = False


class GroupQueue:

    def __init__(self, *groups):
        self.queue = []
        for group in groups:
            self.enq(group)

    def enq(self, group):
        depth = group.depth
        while depth > len(self.queue) - 1:
            self.queue.append([])
        self.queue[depth].append(group)

    def deq(self):
        for stack in self.queue:
            for idx, group in enumerate(reversed(stack)):
                if group.breakables:
                    del stack[idx]
                    group.want_break = True
                    return group
            for group in stack:
                group.want_break = True
            del stack[:]

    def remove(self, group):
        try:
            self.queue[group.depth].remove(group)
        except ValueError:
            pass


class RawText:
    """ Object such that ``p.pretty(RawText(value))`` is the same as ``p.text(value)``.

    An example usage of this would be to show a list as binary numbers, using
    ``p.pretty([RawText(bin(i)) for i in integers])``.
    """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        p.text(self.value)


class CallExpression:
    """ Object which emits a line-wrapped call expression in the form `__name(*args, **kwargs)` """
    def __init__(__self, __name, *args, **kwargs):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.
        self = __self
        self.name = __name
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def factory(cls, name):
        def inner(*args, **kwargs):
            return cls(name, *args, **kwargs)
        return inner

    def _repr_pretty_(self, p, cycle):
        # dunders are to avoid clashes with kwargs, as python's name managing
        # will kick in.

        started = False
        def new_item():
            nonlocal started
            if started:
                p.text(",")
                p.breakable()
            started = True

        prefix = self.name + "("
        with p.group(len(prefix), prefix, ")"):
            for arg in self.args:
                new_item()
                p.pretty(arg)
            for arg_name, arg in self.kwargs.items():
                new_item()
                arg_prefix = arg_name + "="
                with p.group(len(arg_prefix), arg_prefix):
                    p.pretty(arg)


class RawStringLiteral:
    """ Wrapper that shows a string with a `r` prefix """
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        base_repr = repr(self.value)
        if base_repr[:1] in 'uU':
            base_repr = base_repr[1:]
            prefix = 'ur'
        else:
            prefix = 'r'
        base_repr = prefix + base_repr.replace('\\\\', '\\')
        p.text(base_repr)


def _default_pprint(obj, p, cycle):
    """
    The default print function.  Used if an object does not provide one and
    it's none of the builtin objects.
    """
    klass = _safe_getattr(obj, '__class__', None) or type(obj)
    if _safe_getattr(klass, '__repr__', None) is not object.__repr__:
        # A user-provided repr. Find newlines and replace them with p.break_()
        _repr_pprint(obj, p, cycle)
        return
    p.begin_group(1, '<')
    p.pretty(klass)
    p.text(' at 0x%x' % id(obj))
    if cycle:
        p.text(' ...')
    elif p.verbose:
        first = True
        for key in dir(obj):
            if not key.startswith('_'):
                try:
                    value = getattr(obj, key)
                except AttributeError:
                    continue
                if isinstance(value, types.MethodType):
                    continue
                if not first:
                    p.text(',')
                p.breakable()
                p.text(key)
                p.text('=')
                step = len(key) + 1
                p.indentation += step
                p.pretty(value)
                p.indentation -= step
                first = False
    p.end_group(1, '>')


def _seq_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sequences.  Used by
    the default pprint for tuples and lists.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        step = len(start)
        p.begin_group(step, start)
        for idx, x in p._enumerate(obj):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(x)
        if len(obj) == 1 and isinstance(obj, tuple):
            # Special case for 1-item tuples.
            p.text(',')
        p.end_group(step, end)
    return inner


def _set_pprinter_factory(start, end):
    """
    Factory that returns a pprint function useful for sets and frozensets.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text(start + '...' + end)
        if len(obj) == 0:
            # Special case.
            p.text(type(obj).__name__ + '()')
        else:
            step = len(start)
            p.begin_group(step, start)
            # Like dictionary keys, we will try to sort the items if there aren't too many
            if not (p.max_seq_length and len(obj) >= p.max_seq_length):
                items = _sorted_for_pprint(obj)
            else:
                items = obj
            for idx, x in p._enumerate(items):
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(x)
            p.end_group(step, end)
    return inner


def _dict_pprinter_factory(start, end):
    """
    Factory that returns a pprint function used by the default pprint of
    dicts and dict proxies.
    """
    def inner(obj, p, cycle):
        if cycle:
            return p.text('{...}')
        step = len(start)
        p.begin_group(step, start)
        keys = obj.keys()
        for idx, key in p._enumerate(keys):
            if idx:
                p.text(',')
                p.breakable()
            p.pretty(key)
            p.text(': ')
            p.pretty(obj[key])
        p.end_group(step, end)
    return inner


def _super_pprint(obj, p, cycle):
    """The pprint for the super type."""
    p.begin_group(8, '<super: ')
    p.pretty(obj.__thisclass__)
    p.text(',')
    p.breakable()
    if PYPY: # In PyPy, super() objects don't have __self__ attributes
        dself = obj.__repr__.__self__
        p.pretty(None if dself is obj else dself)
    else:
        p.pretty(obj.__self__)
    p.end_group(8, '>')



class _ReFlags:
    def __init__(self, value):
        self.value = value

    def _repr_pretty_(self, p, cycle):
        done_one = False
        for flag in (
            "IGNORECASE",
            "LOCALE",
            "MULTILINE",
            "DOTALL",
            "UNICODE",
            "VERBOSE",
            "DEBUG",
        ):
            if self.value & getattr(re, flag):
                if done_one:
                    p.text('|')
                p.text('re.' + flag)
                done_one = True


def _re_pattern_pprint(obj, p, cycle):
    """The pprint function for regular expression patterns."""
    re_compile = CallExpression.factory('re.compile')
    if obj.flags:
        p.pretty(re_compile(RawStringLiteral(obj.pattern), _ReFlags(obj.flags)))
    else:
        p.pretty(re_compile(RawStringLiteral(obj.pattern)))


def _types_simplenamespace_pprint(obj, p, cycle):
    """The pprint function for types.SimpleNamespace."""
    namespace = CallExpression.factory('namespace')
    if cycle:
        p.pretty(namespace(RawText("...")))
    else:
        p.pretty(namespace(**obj.__dict__))


def _type_pprint(obj, p, cycle):
    """The pprint for classes and types."""
    # Heap allocated types might not have the module attribute,
    # and others may set it to None.

    # Checks for a __repr__ override in the metaclass. Can't compare the
    # type(obj).__repr__ directly because in PyPy the representation function
    # inherited from type isn't the same type.__repr__
    if [m for m in _get_mro(type(obj)) if "__repr__" in vars(m)][:1] != [type]:
        _repr_pprint(obj, p, cycle)
        return

    mod = _safe_getattr(obj, '__module__', None)
    try:
        name = obj.__qualname__
        if not isinstance(name, str):
            # This can happen if the type implements __qualname__ as a property
            # or other descriptor in Python 2.
            raise Exception("Try __name__")
    except Exception:
        name = obj.__name__
        if not isinstance(name, str):
            name = '<unknown type>'

    if mod in (None, '__builtin__', 'builtins', 'exceptions'):
        p.text(name)
    else:
        p.text(mod + '.' + name)


def _repr_pprint(obj, p, cycle):
    """A pprint that just redirects to the normal repr function."""
    # Find newlines and replace them with p.break_()
    output = repr(obj)
    lines = output.splitlines()
    with p.group():
        for idx, output_line in enumerate(lines):
            if idx:
                p.break_()
            p.text(output_line)


def _function_pprint(obj, p, cycle):
    """Base pprint for all functions and builtin functions."""
    name = _safe_getattr(obj, '__qualname__', obj.__name__)
    mod = obj.__module__
    if mod and mod not in ('__builtin__', 'builtins', 'exceptions'):
        name = mod + '.' + name
    try:
       func_def = name + str(signature(obj))
    except ValueError:
       func_def = name
    p.text('<function %s>' % func_def)


def _exception_pprint(obj, p, cycle):
    """Base pprint for all exceptions."""
    name = getattr(obj.__class__, '__qualname__', obj.__class__.__name__)
    if obj.__class__.__module__ not in ('exceptions', 'builtins'):
        name = '%s.%s' % (obj.__class__.__module__, name)

    p.pretty(CallExpression(name, *getattr(obj, 'args', ())))


#: the exception base
_exception_base: type
try:
    _exception_base = BaseException
except NameError:
    _exception_base = Exception


#: printers for builtin types
_type_pprinters = {
    int:                        _repr_pprint,
    float:                      _repr_pprint,
    str:                        _repr_pprint,
    tuple:                      _seq_pprinter_factory('(', ')'),
    list:                       _seq_pprinter_factory('[', ']'),
    dict:                       _dict_pprinter_factory('{', '}'),
    set:                        _set_pprinter_factory('{', '}'),
    frozenset:                  _set_pprinter_factory('frozenset({', '})'),
    super:                      _super_pprint,
    _re_pattern_type:           _re_pattern_pprint,
    type:                       _type_pprint,
    types.FunctionType:         _function_pprint,
    types.BuiltinFunctionType:  _function_pprint,
    types.MethodType:           _repr_pprint,
    types.SimpleNamespace:      _types_simplenamespace_pprint,
    datetime.datetime:          _repr_pprint,
    datetime.timedelta:         _repr_pprint,
    _exception_base:            _exception_pprint
}

# render os.environ like a dict
_env_type = type(os.environ)
# future-proof in case os.environ becomes a plain dict?
if _env_type is not dict:
    _type_pprinters[_env_type] = _dict_pprinter_factory('environ{', '}')

_type_pprinters[types.MappingProxyType] = _dict_pprinter_factory("mappingproxy({", "})")
_type_pprinters[slice] = _repr_pprint

_type_pprinters[range] = _repr_pprint
_type_pprinters[bytes] = _repr_pprint

#: printers for types specified by name
_deferred_type_pprinters: Dict = {}


def for_type(typ, func):
    """
    Add a pretty printer for a given type.
    """
    oldfunc = _type_pprinters.get(typ, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _type_pprinters[typ] = func
    return oldfunc

def for_type_by_name(type_module, type_name, func):
    """
    Add a pretty printer for a type specified by the module and name of a type
    rather than the type object itself.
    """
    key = (type_module, type_name)
    oldfunc = _deferred_type_pprinters.get(key, None)
    if func is not None:
        # To support easy restoration of old pprinters, we need to ignore Nones.
        _deferred_type_pprinters[key] = func
    return oldfunc


#: printers for the default singletons
_singleton_pprinters = dict.fromkeys(map(id, [None, True, False, Ellipsis,
                                      NotImplemented]), _repr_pprint)


def _defaultdict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.default_factory, dict(obj)))

def _ordereddict_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(list(obj.items())))
    else:
        p.pretty(cls_ctor())

def _deque_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif obj.maxlen is not None:
        p.pretty(cls_ctor(list(obj), maxlen=obj.maxlen))
    else:
        p.pretty(cls_ctor(list(obj)))

def _counter_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    elif len(obj):
        p.pretty(cls_ctor(dict(obj.most_common())))
    else:
        p.pretty(cls_ctor())


def _userlist_pprint(obj, p, cycle):
    cls_ctor = CallExpression.factory(obj.__class__.__name__)
    if cycle:
        p.pretty(cls_ctor(RawText("...")))
    else:
        p.pretty(cls_ctor(obj.data))


for_type_by_name('collections', 'defaultdict', _defaultdict_pprint)
for_type_by_name('collections', 'OrderedDict', _ordereddict_pprint)
for_type_by_name('collections', 'deque', _deque_pprint)
for_type_by_name('collections', 'Counter', _counter_pprint)
for_type_by_name("collections", "UserList", _userlist_pprint)

if __name__ == '__main__':
    from random import randrange

    class Foo:
        def __init__(self):
            self.foo = 1
            self.bar = re.compile(r'\s+')
            self.blub = dict.fromkeys(range(30), randrange(1, 40))
            self.hehe = 23424.234234
            self.list = ["blub", "blah", self]

        def get_foo(self):
            print("foo")

    pprint(Foo(), verbose=True)

# === NexusCore/src\dev_tools\test_openai_connection.py ===
# test_openai_connection.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# .env から APIキーを読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ .env に OPENAI_API_KEY が定義されていません。")
    exit(1)

client = OpenAI(api_key=api_key)

# GPT-4 に簡単な質問を送信して動作確認
try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": "こんにちは！APIは正常に動いていますか？"}
        ]
    )
    print("✅ 接続成功！レスポンス：\n")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"❌ エラーが発生しました：{e}")

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_iotools.py ===
"""A collection of functions designed to help I/O with ascii files.

"""
__docformat__ = "restructuredtext en"

import itertools

import numpy as np
import numpy._core.numeric as nx
from numpy._utils import asbytes, asunicode


def _decode_line(line, encoding=None):
    """Decode bytes from binary input streams.

    Defaults to decoding from 'latin1'.

    Parameters
    ----------
    line : str or bytes
         Line to be decoded.
    encoding : str
         Encoding used to decode `line`.

    Returns
    -------
    decoded_line : str

    """
    if type(line) is bytes:
        if encoding is None:
            encoding = "latin1"
        line = line.decode(encoding)

    return line


def _is_string_like(obj):
    """
    Check whether obj behaves like a string.
    """
    try:
        obj + ''
    except (TypeError, ValueError):
        return False
    return True


def _is_bytes_like(obj):
    """
    Check whether obj behaves like a bytes object.
    """
    try:
        obj + b''
    except (TypeError, ValueError):
        return False
    return True


def has_nested_fields(ndtype):
    """
    Returns whether one or several fields of a dtype are nested.

    Parameters
    ----------
    ndtype : dtype
        Data-type of a structured array.

    Raises
    ------
    AttributeError
        If `ndtype` does not have a `names` attribute.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([('name', 'S4'), ('x', float), ('y', float)])
    >>> np.lib._iotools.has_nested_fields(dt)
    False

    """
    return any(ndtype[name].names is not None for name in ndtype.names or ())


def flatten_dtype(ndtype, flatten_base=False):
    """
    Unpack a structured data-type by collapsing nested fields and/or fields
    with a shape.

    Note that the field names are lost.

    Parameters
    ----------
    ndtype : dtype
        The datatype to collapse
    flatten_base : bool, optional
       If True, transform a field with a shape into several fields. Default is
       False.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
    ...                ('block', int, (2, 3))])
    >>> np.lib._iotools.flatten_dtype(dt)
    [dtype('S4'), dtype('float64'), dtype('float64'), dtype('int64')]
    >>> np.lib._iotools.flatten_dtype(dt, flatten_base=True)
    [dtype('S4'),
     dtype('float64'),
     dtype('float64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64'),
     dtype('int64')]

    """
    names = ndtype.names
    if names is None:
        if flatten_base:
            return [ndtype.base] * int(np.prod(ndtype.shape))
        return [ndtype.base]
    else:
        types = []
        for field in names:
            info = ndtype.fields[field]
            flat_dt = flatten_dtype(info[0], flatten_base)
            types.extend(flat_dt)
        return types


class LineSplitter:
    """
    Object to split a string at a given delimiter or at given places.

    Parameters
    ----------
    delimiter : str, int, or sequence of ints, optional
        If a string, character used to delimit consecutive fields.
        If an integer or a sequence of integers, width(s) of each field.
    comments : str, optional
        Character used to mark the beginning of a comment. Default is '#'.
    autostrip : bool, optional
        Whether to strip each individual field. Default is True.

    """

    def autostrip(self, method):
        """
        Wrapper to strip each member of the output of `method`.

        Parameters
        ----------
        method : function
            Function that takes a single argument and returns a sequence of
            strings.

        Returns
        -------
        wrapped : function
            The result of wrapping `method`. `wrapped` takes a single input
            argument and returns a list of strings that are stripped of
            white-space.

        """
        return lambda input: [_.strip() for _ in method(input)]

    def __init__(self, delimiter=None, comments='#', autostrip=True,
                 encoding=None):
        delimiter = _decode_line(delimiter)
        comments = _decode_line(comments)

        self.comments = comments

        # Delimiter is a character
        if (delimiter is None) or isinstance(delimiter, str):
            delimiter = delimiter or None
            _handyman = self._delimited_splitter
        # Delimiter is a list of field widths
        elif hasattr(delimiter, '__iter__'):
            _handyman = self._variablewidth_splitter
            idx = np.cumsum([0] + list(delimiter))
            delimiter = [slice(i, j) for (i, j) in itertools.pairwise(idx)]
        # Delimiter is a single integer
        elif int(delimiter):
            (_handyman, delimiter) = (
                    self._fixedwidth_splitter, int(delimiter))
        else:
            (_handyman, delimiter) = (self._delimited_splitter, None)
        self.delimiter = delimiter
        if autostrip:
            self._handyman = self.autostrip(_handyman)
        else:
            self._handyman = _handyman
        self.encoding = encoding

    def _delimited_splitter(self, line):
        """Chop off comments, strip, and split at delimiter. """
        if self.comments is not None:
            line = line.split(self.comments)[0]
        line = line.strip(" \r\n")
        if not line:
            return []
        return line.split(self.delimiter)

    def _fixedwidth_splitter(self, line):
        if self.comments is not None:
            line = line.split(self.comments)[0]
        line = line.strip("\r\n")
        if not line:
            return []
        fixed = self.delimiter
        slices = [slice(i, i + fixed) for i in range(0, len(line), fixed)]
        return [line[s] for s in slices]

    def _variablewidth_splitter(self, line):
        if self.comments is not None:
            line = line.split(self.comments)[0]
        if not line:
            return []
        slices = self.delimiter
        return [line[s] for s in slices]

    def __call__(self, line):
        return self._handyman(_decode_line(line, self.encoding))


class NameValidator:
    """
    Object to validate a list of strings to use as field names.

    The strings are stripped of any non alphanumeric character, and spaces
    are replaced by '_'. During instantiation, the user can define a list
    of names to exclude, as well as a list of invalid characters. Names in
    the exclusion list are appended a '_' character.

    Once an instance has been created, it can be called with a list of
    names, and a list of valid names will be created.  The `__call__`
    method accepts an optional keyword "default" that sets the default name
    in case of ambiguity. By default this is 'f', so that names will
    default to `f0`, `f1`, etc.

    Parameters
    ----------
    excludelist : sequence, optional
        A list of names to exclude. This list is appended to the default
        list ['return', 'file', 'print']. Excluded names are appended an
        underscore: for example, `file` becomes `file_` if supplied.
    deletechars : str, optional
        A string combining invalid characters that must be deleted from the
        names.
    case_sensitive : {True, False, 'upper', 'lower'}, optional
        * If True, field names are case-sensitive.
        * If False or 'upper', field names are converted to upper case.
        * If 'lower', field names are converted to lower case.

        The default value is True.
    replace_space : '_', optional
        Character(s) used in replacement of white spaces.

    Notes
    -----
    Calling an instance of `NameValidator` is the same as calling its
    method `validate`.

    Examples
    --------
    >>> import numpy as np
    >>> validator = np.lib._iotools.NameValidator()
    >>> validator(['file', 'field2', 'with space', 'CaSe'])
    ('file_', 'field2', 'with_space', 'CaSe')

    >>> validator = np.lib._iotools.NameValidator(excludelist=['excl'],
    ...                                           deletechars='q',
    ...                                           case_sensitive=False)
    >>> validator(['excl', 'field2', 'no_q', 'with space', 'CaSe'])
    ('EXCL', 'FIELD2', 'NO_Q', 'WITH_SPACE', 'CASE')

    """

    defaultexcludelist = 'return', 'file', 'print'
    defaultdeletechars = frozenset(r"""~!@#$%^&*()-=+~\|]}[{';: /?.>,<""")

    def __init__(self, excludelist=None, deletechars=None,
                 case_sensitive=None, replace_space='_'):
        # Process the exclusion list ..
        if excludelist is None:
            excludelist = []
        excludelist.extend(self.defaultexcludelist)
        self.excludelist = excludelist
        # Process the list of characters to delete
        if deletechars is None:
            delete = set(self.defaultdeletechars)
        else:
            delete = set(deletechars)
        delete.add('"')
        self.deletechars = delete
        # Process the case option .....
        if (case_sensitive is None) or (case_sensitive is True):
            self.case_converter = lambda x: x
        elif (case_sensitive is False) or case_sensitive.startswith('u'):
            self.case_converter = lambda x: x.upper()
        elif case_sensitive.startswith('l'):
            self.case_converter = lambda x: x.lower()
        else:
            msg = f'unrecognized case_sensitive value {case_sensitive}.'
            raise ValueError(msg)

        self.replace_space = replace_space

    def validate(self, names, defaultfmt="f%i", nbfields=None):
        """
        Validate a list of strings as field names for a structured array.

        Parameters
        ----------
        names : sequence of str
            Strings to be validated.
        defaultfmt : str, optional
            Default format string, used if validating a given string
            reduces its length to zero.
        nbfields : integer, optional
            Final number of validated names, used to expand or shrink the
            initial list of names.

        Returns
        -------
        validatednames : list of str
            The list of validated field names.

        Notes
        -----
        A `NameValidator` instance can be called directly, which is the
        same as calling `validate`. For examples, see `NameValidator`.

        """
        # Initial checks ..............
        if (names is None):
            if (nbfields is None):
                return None
            names = []
        if isinstance(names, str):
            names = [names, ]
        if nbfields is not None:
            nbnames = len(names)
            if (nbnames < nbfields):
                names = list(names) + [''] * (nbfields - nbnames)
            elif (nbnames > nbfields):
                names = names[:nbfields]
        # Set some shortcuts ...........
        deletechars = self.deletechars
        excludelist = self.excludelist
        case_converter = self.case_converter
        replace_space = self.replace_space
        # Initializes some variables ...
        validatednames = []
        seen = {}
        nbempty = 0

        for item in names:
            item = case_converter(item).strip()
            if replace_space:
                item = item.replace(' ', replace_space)
            item = ''.join([c for c in item if c not in deletechars])
            if item == '':
                item = defaultfmt % nbempty
                while item in names:
                    nbempty += 1
                    item = defaultfmt % nbempty
                nbempty += 1
            elif item in excludelist:
                item += '_'
            cnt = seen.get(item, 0)
            if cnt > 0:
                validatednames.append(item + '_%d' % cnt)
            else:
                validatednames.append(item)
            seen[item] = cnt + 1
        return tuple(validatednames)

    def __call__(self, names, defaultfmt="f%i", nbfields=None):
        return self.validate(names, defaultfmt=defaultfmt, nbfields=nbfields)


def str2bool(value):
    """
    Tries to transform a string supposed to represent a boolean to a boolean.

    Parameters
    ----------
    value : str
        The string that is transformed to a boolean.

    Returns
    -------
    boolval : bool
        The boolean representation of `value`.

    Raises
    ------
    ValueError
        If the string is not 'True' or 'False' (case independent)

    Examples
    --------
    >>> import numpy as np
    >>> np.lib._iotools.str2bool('TRUE')
    True
    >>> np.lib._iotools.str2bool('false')
    False

    """
    value = value.upper()
    if value == 'TRUE':
        return True
    elif value == 'FALSE':
        return False
    else:
        raise ValueError("Invalid boolean")


class ConverterError(Exception):
    """
    Exception raised when an error occurs in a converter for string values.

    """
    pass


class ConverterLockError(ConverterError):
    """
    Exception raised when an attempt is made to upgrade a locked converter.

    """
    pass


class ConversionWarning(UserWarning):
    """
    Warning issued when a string converter has a problem.

    Notes
    -----
    In `genfromtxt` a `ConversionWarning` is issued if raising exceptions
    is explicitly suppressed with the "invalid_raise" keyword.

    """
    pass


class StringConverter:
    """
    Factory class for function transforming a string into another object
    (int, float).

    After initialization, an instance can be called to transform a string
    into another object. If the string is recognized as representing a
    missing value, a default value is returned.

    Attributes
    ----------
    func : function
        Function used for the conversion.
    default : any
        Default value to return when the input corresponds to a missing
        value.
    type : type
        Type of the output.
    _status : int
        Integer representing the order of the conversion.
    _mapper : sequence of tuples
        Sequence of tuples (dtype, function, default value) to evaluate in
        order.
    _locked : bool
        Holds `locked` parameter.

    Parameters
    ----------
    dtype_or_func : {None, dtype, function}, optional
        If a `dtype`, specifies the input data type, used to define a basic
        function and a default value for missing data. For example, when
        `dtype` is float, the `func` attribute is set to `float` and the
        default value to `np.nan`.  If a function, this function is used to
        convert a string to another object. In this case, it is recommended
        to give an associated default value as input.
    default : any, optional
        Value to return by default, that is, when the string to be
        converted is flagged as missing. If not given, `StringConverter`
        tries to supply a reasonable default value.
    missing_values : {None, sequence of str}, optional
        ``None`` or sequence of strings indicating a missing value. If ``None``
        then missing values are indicated by empty entries. The default is
        ``None``.
    locked : bool, optional
        Whether the StringConverter should be locked to prevent automatic
        upgrade or not. Default is False.

    """
    _mapper = [(nx.bool, str2bool, False),
               (nx.int_, int, -1),]

    # On 32-bit systems, we need to make sure that we explicitly include
    # nx.int64 since ns.int_ is nx.int32.
    if nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize:
        _mapper.append((nx.int64, int, -1))

    _mapper.extend([(nx.float64, float, nx.nan),
                    (nx.complex128, complex, nx.nan + 0j),
                    (nx.longdouble, nx.longdouble, nx.nan),
                    # If a non-default dtype is passed, fall back to generic
                    # ones (should only be used for the converter)
                    (nx.integer, int, -1),
                    (nx.floating, float, nx.nan),
                    (nx.complexfloating, complex, nx.nan + 0j),
                    # Last, try with the string types (must be last, because
                    # `_mapper[-1]` is used as default in some cases)
                    (nx.str_, asunicode, '???'),
                    (nx.bytes_, asbytes, '???'),
                    ])

    @classmethod
    def _getdtype(cls, val):
        """Returns the dtype of the input variable."""
        return np.array(val).dtype

    @classmethod
    def _getsubdtype(cls, val):
        """Returns the type of the dtype of the input variable."""
        return np.array(val).dtype.type

    @classmethod
    def _dtypeortype(cls, dtype):
        """Returns dtype for datetime64 and type of dtype otherwise."""

        # This is a bit annoying. We want to return the "general" type in most
        # cases (ie. "string" rather than "S10"), but we want to return the
        # specific type for datetime64 (ie. "datetime64[us]" rather than
        # "datetime64").
        if dtype.type == np.datetime64:
            return dtype
        return dtype.type

    @classmethod
    def upgrade_mapper(cls, func, default=None):
        """
        Upgrade the mapper of a StringConverter by adding a new function and
        its corresponding default.

        The input function (or sequence of functions) and its associated
        default value (if any) is inserted in penultimate position of the
        mapper.  The corresponding type is estimated from the dtype of the
        default value.

        Parameters
        ----------
        func : var
            Function, or sequence of functions

        Examples
        --------
        >>> import dateutil.parser
        >>> import datetime
        >>> dateparser = dateutil.parser.parse
        >>> defaultdate = datetime.date(2000, 1, 1)
        >>> StringConverter.upgrade_mapper(dateparser, default=defaultdate)
        """
        # Func is a single functions
        if callable(func):
            cls._mapper.insert(-1, (cls._getsubdtype(default), func, default))
            return
        elif hasattr(func, '__iter__'):
            if isinstance(func[0], (tuple, list)):
                for _ in func:
                    cls._mapper.insert(-1, _)
                return
            if default is None:
                default = [None] * len(func)
            else:
                default = list(default)
                default.append([None] * (len(func) - len(default)))
            for fct, dft in zip(func, default):
                cls._mapper.insert(-1, (cls._getsubdtype(dft), fct, dft))

    @classmethod
    def _find_map_entry(cls, dtype):
        # if a converter for the specific dtype is available use that
        for i, (deftype, func, default_def) in enumerate(cls._mapper):
            if dtype.type == deftype:
                return i, (deftype, func, default_def)

        # otherwise find an inexact match
        for i, (deftype, func, default_def) in enumerate(cls._mapper):
            if np.issubdtype(dtype.type, deftype):
                return i, (deftype, func, default_def)

        raise LookupError

    def __init__(self, dtype_or_func=None, default=None, missing_values=None,
                 locked=False):
        # Defines a lock for upgrade
        self._locked = bool(locked)
        # No input dtype: minimal initialization
        if dtype_or_func is None:
            self.func = str2bool
            self._status = 0
            self.default = default or False
            dtype = np.dtype('bool')
        else:
            # Is the input a np.dtype ?
            try:
                self.func = None
                dtype = np.dtype(dtype_or_func)
            except TypeError:
                # dtype_or_func must be a function, then
                if not callable(dtype_or_func):
                    errmsg = ("The input argument `dtype` is neither a"
                              " function nor a dtype (got '%s' instead)")
                    raise TypeError(errmsg % type(dtype_or_func))
                # Set the function
                self.func = dtype_or_func
                # If we don't have a default, try to guess it or set it to
                # None
                if default is None:
                    try:
                        default = self.func('0')
                    except ValueError:
                        default = None
                dtype = self._getdtype(default)

            # find the best match in our mapper
            try:
                self._status, (_, func, default_def) = self._find_map_entry(dtype)
            except LookupError:
                # no match
                self.default = default
                _, func, _ = self._mapper[-1]
                self._status = 0
            else:
                # use the found default only if we did not already have one
                if default is None:
                    self.default = default_def
                else:
                    self.default = default

            # If the input was a dtype, set the function to the last we saw
            if self.func is None:
                self.func = func

            # If the status is 1 (int), change the function to
            # something more robust.
            if self.func == self._mapper[1][1]:
                if issubclass(dtype.type, np.uint64):
                    self.func = np.uint64
                elif issubclass(dtype.type, np.int64):
                    self.func = np.int64
                else:
                    self.func = lambda x: int(float(x))
        # Store the list of strings corresponding to missing values.
        if missing_values is None:
            self.missing_values = {''}
        else:
            if isinstance(missing_values, str):
                missing_values = missing_values.split(",")
            self.missing_values = set(list(missing_values) + [''])

        self._callingfunction = self._strict_call
        self.type = self._dtypeortype(dtype)
        self._checked = False
        self._initial_default = default

    def _loose_call(self, value):
        try:
            return self.func(value)
        except ValueError:
            return self.default

    def _strict_call(self, value):
        try:

            # We check if we can convert the value using the current function
            new_value = self.func(value)

            # In addition to having to check whether func can convert the
            # value, we also have to make sure that we don't get overflow
            # errors for integers.
            if self.func is int:
                try:
                    np.array(value, dtype=self.type)
                except OverflowError:
                    raise ValueError

            # We're still here so we can now return the new value
            return new_value

        except ValueError:
            if value.strip() in self.missing_values:
                if not self._status:
                    self._checked = False
                return self.default
            raise ValueError(f"Cannot convert string '{value}'")

    def __call__(self, value):
        return self._callingfunction(value)

    def _do_upgrade(self):
        # Raise an exception if we locked the converter...
        if self._locked:
            errmsg = "Converter is locked and cannot be upgraded"
            raise ConverterLockError(errmsg)
        _statusmax = len(self._mapper)
        # Complains if we try to upgrade by the maximum
        _status = self._status
        if _status == _statusmax:
            errmsg = "Could not find a valid conversion function"
            raise ConverterError(errmsg)
        elif _status < _statusmax - 1:
            _status += 1
        self.type, self.func, default = self._mapper[_status]
        self._status = _status
        if self._initial_default is not None:
            self.default = self._initial_default
        else:
            self.default = default

    def upgrade(self, value):
        """
        Find the best converter for a given string, and return the result.

        The supplied string `value` is converted by testing different
        converters in order. First the `func` method of the
        `StringConverter` instance is tried, if this fails other available
        converters are tried.  The order in which these other converters
        are tried is determined by the `_status` attribute of the instance.

        Parameters
        ----------
        value : str
            The string to convert.

        Returns
        -------
        out : any
            The result of converting `value` with the appropriate converter.

        """
        self._checked = True
        try:
            return self._strict_call(value)
        except ValueError:
            self._do_upgrade()
            return self.upgrade(value)

    def iterupgrade(self, value):
        self._checked = True
        if not hasattr(value, '__iter__'):
            value = (value,)
        _strict_call = self._strict_call
        try:
            for _m in value:
                _strict_call(_m)
        except ValueError:
            self._do_upgrade()
            self.iterupgrade(value)

    def update(self, func, default=None, testing_value=None,
               missing_values='', locked=False):
        """
        Set StringConverter attributes directly.

        Parameters
        ----------
        func : function
            Conversion function.
        default : any, optional
            Value to return by default, that is, when the string to be
            converted is flagged as missing. If not given,
            `StringConverter` tries to supply a reasonable default value.
        testing_value : str, optional
            A string representing a standard input value of the converter.
            This string is used to help defining a reasonable default
            value.
        missing_values : {sequence of str, None}, optional
            Sequence of strings indicating a missing value. If ``None``, then
            the existing `missing_values` are cleared. The default is ``''``.
        locked : bool, optional
            Whether the StringConverter should be locked to prevent
            automatic upgrade or not. Default is False.

        Notes
        -----
        `update` takes the same parameters as the constructor of
        `StringConverter`, except that `func` does not accept a `dtype`
        whereas `dtype_or_func` in the constructor does.

        """
        self.func = func
        self._locked = locked

        # Don't reset the default to None if we can avoid it
        if default is not None:
            self.default = default
            self.type = self._dtypeortype(self._getdtype(default))
        else:
            try:
                tester = func(testing_value or '1')
            except (TypeError, ValueError):
                tester = None
            self.type = self._dtypeortype(self._getdtype(tester))

        # Add the missing values to the existing set or clear it.
        if missing_values is None:
            # Clear all missing values even though the ctor initializes it to
            # set(['']) when the argument is None.
            self.missing_values = set()
        else:
            if not np.iterable(missing_values):
                missing_values = [missing_values]
            if not all(isinstance(v, str) for v in missing_values):
                raise TypeError("missing_values must be strings or unicode")
            self.missing_values.update(missing_values)


def easy_dtype(ndtype, names=None, defaultfmt="f%i", **validationargs):
    """
    Convenience function to create a `np.dtype` object.

    The function processes the input `dtype` and matches it with the given
    names.

    Parameters
    ----------
    ndtype : var
        Definition of the dtype. Can be any string or dictionary recognized
        by the `np.dtype` function, or a sequence of types.
    names : str or sequence, optional
        Sequence of strings to use as field names for a structured dtype.
        For convenience, `names` can be a string of a comma-separated list
        of names.
    defaultfmt : str, optional
        Format string used to define missing names, such as ``"f%i"``
        (default) or ``"fields_%02i"``.
    validationargs : optional
        A series of optional arguments used to initialize a
        `NameValidator`.

    Examples
    --------
    >>> import numpy as np
    >>> np.lib._iotools.easy_dtype(float)
    dtype('float64')
    >>> np.lib._iotools.easy_dtype("i4, f8")
    dtype([('f0', '<i4'), ('f1', '<f8')])
    >>> np.lib._iotools.easy_dtype("i4, f8", defaultfmt="field_%03i")
    dtype([('field_000', '<i4'), ('field_001', '<f8')])

    >>> np.lib._iotools.easy_dtype((int, float, float), names="a,b,c")
    dtype([('a', '<i8'), ('b', '<f8'), ('c', '<f8')])
    >>> np.lib._iotools.easy_dtype(float, names="a,b,c")
    dtype([('a', '<f8'), ('b', '<f8'), ('c', '<f8')])

    """
    try:
        ndtype = np.dtype(ndtype)
    except TypeError:
        validate = NameValidator(**validationargs)
        nbfields = len(ndtype)
        if names is None:
            names = [''] * len(ndtype)
        elif isinstance(names, str):
            names = names.split(",")
        names = validate(names, nbfields=nbfields, defaultfmt=defaultfmt)
        ndtype = np.dtype({"formats": ndtype, "names": names})
    else:
        # Explicit names
        if names is not None:
            validate = NameValidator(**validationargs)
            if isinstance(names, str):
                names = names.split(",")
            # Simple dtype: repeat to match the nb of names
            if ndtype.names is None:
                formats = tuple([ndtype.type] * len(names))
                names = validate(names, defaultfmt=defaultfmt)
                ndtype = np.dtype(list(zip(names, formats)))
            # Structured dtype: just validate the names as needed
            else:
                ndtype.names = validate(names, nbfields=len(ndtype.names),
                                        defaultfmt=defaultfmt)
        # No implicit names
        elif ndtype.names is not None:
            validate = NameValidator(**validationargs)
            # Default initial names : should we change the format ?
            numbered_names = tuple(f"f{i}" for i in range(len(ndtype.names)))
            if ((ndtype.names == numbered_names) and (defaultfmt != "f%i")):
                ndtype.names = validate([''] * len(ndtype.names),
                                        defaultfmt=defaultfmt)
            # Explicit initial names : just validate
            else:
                ndtype.names = validate(ndtype.names, defaultfmt=defaultfmt)
    return ndtype

# === NexusCore/my-crm-app\app\routes.py ===
# TODO: Define routes for customer management

from flask import Blueprint, request, jsonify
from .models import Customer
from . import db

bp = Blueprint('main', __name__)

@bp.route('/customers', methods=['GET'])
def get_customers():
    # TODO: Implement logic to retrieve customers
    pass

@bp.route('/customers', methods=['POST'])
def add_customer():
    # TODO: Implement logic to add a new customer
    pass

@bp.route('/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    # TODO: Implement logic to update an existing customer
    pass

@bp.route('/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    # TODO: Implement logic to delete a customer
    pass

# === NexusCore/workspace\default_project\app\main.py ===
def add(num1: float, num2: float) -> float:
    """二つの数値を受け取り、その合計を返す関数。

    Args:
        num1 (float): 最初の数値
        num2 (float): 二番目の数値

    Returns:
        float: 二つの数値の合計
    """
    if not isinstance(num1, (int, float)) or not isinstance(num2, (int, float)):
        raise TypeError("Invalid input type")

    return float(num1) + float(num2)


def subtract(a: float, b: float) -> float:
    """二つの数値を引く。

    Args:
        a (int or float): 引かれる数
        b (int or float): 引く数

    Returns:
        int or float: a - b の結果
    """
    return a - b

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_arraypad_impl.py ===
"""
The arraypad module contains a group of functions to pad values onto the edges
of an n-dimensional array.

"""
import numpy as np
from numpy._core.overrides import array_function_dispatch
from numpy.lib._index_tricks_impl import ndindex

__all__ = ['pad']


###############################################################################
# Private utility functions.


def _round_if_needed(arr, dtype):
    """
    Rounds arr inplace if destination dtype is integer.

    Parameters
    ----------
    arr : ndarray
        Input array.
    dtype : dtype
        The dtype of the destination array.
    """
    if np.issubdtype(dtype, np.integer):
        arr.round(out=arr)


def _slice_at_axis(sl, axis):
    """
    Construct tuple of slices to slice an array in the given dimension.

    Parameters
    ----------
    sl : slice
        The slice for the given dimension.
    axis : int
        The axis to which `sl` is applied. All other dimensions are left
        "unsliced".

    Returns
    -------
    sl : tuple of slices
        A tuple with slices matching `shape` in length.

    Examples
    --------
    >>> np._slice_at_axis(slice(None, 3, -1), 1)
    (slice(None, None, None), slice(None, 3, -1), (...,))
    """
    return (slice(None),) * axis + (sl,) + (...,)


def _view_roi(array, original_area_slice, axis):
    """
    Get a view of the current region of interest during iterative padding.

    When padding multiple dimensions iteratively corner values are
    unnecessarily overwritten multiple times. This function reduces the
    working area for the first dimensions so that corners are excluded.

    Parameters
    ----------
    array : ndarray
        The array with the region of interest.
    original_area_slice : tuple of slices
        Denotes the area with original values of the unpadded array.
    axis : int
        The currently padded dimension assuming that `axis` is padded before
        `axis` + 1.

    Returns
    -------
    roi : ndarray
        The region of interest of the original `array`.
    """
    axis += 1
    sl = (slice(None),) * axis + original_area_slice[axis:]
    return array[sl]


def _pad_simple(array, pad_width, fill_value=None):
    """
    Pad array on all sides with either a single value or undefined values.

    Parameters
    ----------
    array : ndarray
        Array to grow.
    pad_width : sequence of tuple[int, int]
        Pad width on both sides for each dimension in `arr`.
    fill_value : scalar, optional
        If provided the padded area is filled with this value, otherwise
        the pad area left undefined.

    Returns
    -------
    padded : ndarray
        The padded array with the same dtype as`array`. Its order will default
        to C-style if `array` is not F-contiguous.
    original_area_slice : tuple
        A tuple of slices pointing to the area of the original array.
    """
    # Allocate grown array
    new_shape = tuple(
        left + size + right
        for size, (left, right) in zip(array.shape, pad_width)
    )
    order = 'F' if array.flags.fnc else 'C'  # Fortran and not also C-order
    padded = np.empty(new_shape, dtype=array.dtype, order=order)

    if fill_value is not None:
        padded.fill(fill_value)

    # Copy old array into correct space
    original_area_slice = tuple(
        slice(left, left + size)
        for size, (left, right) in zip(array.shape, pad_width)
    )
    padded[original_area_slice] = array

    return padded, original_area_slice


def _set_pad_area(padded, axis, width_pair, value_pair):
    """
    Set empty-padded area in given dimension.

    Parameters
    ----------
    padded : ndarray
        Array with the pad area which is modified inplace.
    axis : int
        Dimension with the pad area to set.
    width_pair : (int, int)
        Pair of widths that mark the pad area on both sides in the given
        dimension.
    value_pair : tuple of scalars or ndarrays
        Values inserted into the pad area on each side. It must match or be
        broadcastable to the shape of `arr`.
    """
    left_slice = _slice_at_axis(slice(None, width_pair[0]), axis)
    padded[left_slice] = value_pair[0]

    right_slice = _slice_at_axis(
        slice(padded.shape[axis] - width_pair[1], None), axis)
    padded[right_slice] = value_pair[1]


def _get_edges(padded, axis, width_pair):
    """
    Retrieve edge values from empty-padded array in given dimension.

    Parameters
    ----------
    padded : ndarray
        Empty-padded array.
    axis : int
        Dimension in which the edges are considered.
    width_pair : (int, int)
        Pair of widths that mark the pad area on both sides in the given
        dimension.

    Returns
    -------
    left_edge, right_edge : ndarray
        Edge values of the valid area in `padded` in the given dimension. Its
        shape will always match `padded` except for the dimension given by
        `axis` which will have a length of 1.
    """
    left_index = width_pair[0]
    left_slice = _slice_at_axis(slice(left_index, left_index + 1), axis)
    left_edge = padded[left_slice]

    right_index = padded.shape[axis] - width_pair[1]
    right_slice = _slice_at_axis(slice(right_index - 1, right_index), axis)
    right_edge = padded[right_slice]

    return left_edge, right_edge


def _get_linear_ramps(padded, axis, width_pair, end_value_pair):
    """
    Construct linear ramps for empty-padded array in given dimension.

    Parameters
    ----------
    padded : ndarray
        Empty-padded array.
    axis : int
        Dimension in which the ramps are constructed.
    width_pair : (int, int)
        Pair of widths that mark the pad area on both sides in the given
        dimension.
    end_value_pair : (scalar, scalar)
        End values for the linear ramps which form the edge of the fully padded
        array. These values are included in the linear ramps.

    Returns
    -------
    left_ramp, right_ramp : ndarray
        Linear ramps to set on both sides of `padded`.
    """
    edge_pair = _get_edges(padded, axis, width_pair)

    left_ramp, right_ramp = (
        np.linspace(
            start=end_value,
            stop=edge.squeeze(axis),  # Dimension is replaced by linspace
            num=width,
            endpoint=False,
            dtype=padded.dtype,
            axis=axis
        )
        for end_value, edge, width in zip(
            end_value_pair, edge_pair, width_pair
        )
    )

    # Reverse linear space in appropriate dimension
    right_ramp = right_ramp[_slice_at_axis(slice(None, None, -1), axis)]

    return left_ramp, right_ramp


def _get_stats(padded, axis, width_pair, length_pair, stat_func):
    """
    Calculate statistic for the empty-padded array in given dimension.

    Parameters
    ----------
    padded : ndarray
        Empty-padded array.
    axis : int
        Dimension in which the statistic is calculated.
    width_pair : (int, int)
        Pair of widths that mark the pad area on both sides in the given
        dimension.
    length_pair : 2-element sequence of None or int
        Gives the number of values in valid area from each side that is
        taken into account when calculating the statistic. If None the entire
        valid area in `padded` is considered.
    stat_func : function
        Function to compute statistic. The expected signature is
        ``stat_func(x: ndarray, axis: int, keepdims: bool) -> ndarray``.

    Returns
    -------
    left_stat, right_stat : ndarray
        Calculated statistic for both sides of `padded`.
    """
    # Calculate indices of the edges of the area with original values
    left_index = width_pair[0]
    right_index = padded.shape[axis] - width_pair[1]
    # as well as its length
    max_length = right_index - left_index

    # Limit stat_lengths to max_length
    left_length, right_length = length_pair
    if left_length is None or max_length < left_length:
        left_length = max_length
    if right_length is None or max_length < right_length:
        right_length = max_length

    if (left_length == 0 or right_length == 0) \
            and stat_func in {np.amax, np.amin}:
        # amax and amin can't operate on an empty array,
        # raise a more descriptive warning here instead of the default one
        raise ValueError("stat_length of 0 yields no value for padding")

    # Calculate statistic for the left side
    left_slice = _slice_at_axis(
        slice(left_index, left_index + left_length), axis)
    left_chunk = padded[left_slice]
    left_stat = stat_func(left_chunk, axis=axis, keepdims=True)
    _round_if_needed(left_stat, padded.dtype)

    if left_length == right_length == max_length:
        # return early as right_stat must be identical to left_stat
        return left_stat, left_stat

    # Calculate statistic for the right side
    right_slice = _slice_at_axis(
        slice(right_index - right_length, right_index), axis)
    right_chunk = padded[right_slice]
    right_stat = stat_func(right_chunk, axis=axis, keepdims=True)
    _round_if_needed(right_stat, padded.dtype)

    return left_stat, right_stat


def _set_reflect_both(padded, axis, width_pair, method,
                      original_period, include_edge=False):
    """
    Pad `axis` of `arr` with reflection.

    Parameters
    ----------
    padded : ndarray
        Input array of arbitrary shape.
    axis : int
        Axis along which to pad `arr`.
    width_pair : (int, int)
        Pair of widths that mark the pad area on both sides in the given
        dimension.
    method : str
        Controls method of reflection; options are 'even' or 'odd'.
    original_period : int
        Original length of data on `axis` of `arr`.
    include_edge : bool
        If true, edge value is included in reflection, otherwise the edge
        value forms the symmetric axis to the reflection.

    Returns
    -------
    pad_amt : tuple of ints, length 2
        New index positions of padding to do along the `axis`. If these are
        both 0, padding is done in this dimension.
    """
    left_pad, right_pad = width_pair
    old_length = padded.shape[axis] - right_pad - left_pad

    if include_edge:
        # Avoid wrapping with only a subset of the original area
        # by ensuring period can only be a multiple of the original
        # area's length.
        old_length = old_length // original_period * original_period
        # Edge is included, we need to offset the pad amount by 1
        edge_offset = 1
    else:
        # Avoid wrapping with only a subset of the original area
        # by ensuring period can only be a multiple of the original
        # area's length.
        old_length = ((old_length - 1) // (original_period - 1)
            * (original_period - 1) + 1)
        edge_offset = 0  # Edge is not included, no need to offset pad amount
        old_length -= 1  # but must be omitted from the chunk

    if left_pad > 0:
        # Pad with reflected values on left side:
        # First limit chunk size which can't be larger than pad area
        chunk_length = min(old_length, left_pad)
        # Slice right to left, stop on or next to edge, start relative to stop
        stop = left_pad - edge_offset
        start = stop + chunk_length
        left_slice = _slice_at_axis(slice(start, stop, -1), axis)
        left_chunk = padded[left_slice]

        if method == "odd":
            # Negate chunk and align with edge
            edge_slice = _slice_at_axis(slice(left_pad, left_pad + 1), axis)
            left_chunk = 2 * padded[edge_slice] - left_chunk

        # Insert chunk into padded area
        start = left_pad - chunk_length
        stop = left_pad
        pad_area = _slice_at_axis(slice(start, stop), axis)
        padded[pad_area] = left_chunk
        # Adjust pointer to left edge for next iteration
        left_pad -= chunk_length

    if right_pad > 0:
        # Pad with reflected values on right side:
        # First limit chunk size which can't be larger than pad area
        chunk_length = min(old_length, right_pad)
        # Slice right to left, start on or next to edge, stop relative to start
        start = -right_pad + edge_offset - 2
        stop = start - chunk_length
        right_slice = _slice_at_axis(slice(start, stop, -1), axis)
        right_chunk = padded[right_slice]

        if method == "odd":
            # Negate chunk and align with edge
            edge_slice = _slice_at_axis(
                slice(-right_pad - 1, -right_pad), axis)
            right_chunk = 2 * padded[edge_slice] - right_chunk

        # Insert chunk into padded area
        start = padded.shape[axis] - right_pad
        stop = start + chunk_length
        pad_area = _slice_at_axis(slice(start, stop), axis)
        padded[pad_area] = right_chunk
        # Adjust pointer to right edge for next iteration
        right_pad -= chunk_length

    return left_pad, right_pad


def _set_wrap_both(padded, axis, width_pair, original_period):
    """
    Pad `axis` of `arr` with wrapped values.

    Parameters
    ----------
    padded : ndarray
        Input array of arbitrary shape.
    axis : int
        Axis along which to pad `arr`.
    width_pair : (int, int)
        Pair of widths that mark the pad area on both sides in the given
        dimension.
    original_period : int
        Original length of data on `axis` of `arr`.

    Returns
    -------
    pad_amt : tuple of ints, length 2
        New index positions of padding to do along the `axis`. If these are
        both 0, padding is done in this dimension.
    """
    left_pad, right_pad = width_pair
    period = padded.shape[axis] - right_pad - left_pad
    # Avoid wrapping with only a subset of the original area by ensuring period
    # can only be a multiple of the original area's length.
    period = period // original_period * original_period

    # If the current dimension of `arr` doesn't contain enough valid values
    # (not part of the undefined pad area) we need to pad multiple times.
    # Each time the pad area shrinks on both sides which is communicated with
    # these variables.
    new_left_pad = 0
    new_right_pad = 0

    if left_pad > 0:
        # Pad with wrapped values on left side
        # First slice chunk from left side of the non-pad area.
        # Use min(period, left_pad) to ensure that chunk is not larger than
        # pad area.
        slice_end = left_pad + period
        slice_start = slice_end - min(period, left_pad)
        right_slice = _slice_at_axis(slice(slice_start, slice_end), axis)
        right_chunk = padded[right_slice]

        if left_pad > period:
            # Chunk is smaller than pad area
            pad_area = _slice_at_axis(slice(left_pad - period, left_pad), axis)
            new_left_pad = left_pad - period
        else:
            # Chunk matches pad area
            pad_area = _slice_at_axis(slice(None, left_pad), axis)
        padded[pad_area] = right_chunk

    if right_pad > 0:
        # Pad with wrapped values on right side
        # First slice chunk from right side of the non-pad area.
        # Use min(period, right_pad) to ensure that chunk is not larger than
        # pad area.
        slice_start = -right_pad - period
        slice_end = slice_start + min(period, right_pad)
        left_slice = _slice_at_axis(slice(slice_start, slice_end), axis)
        left_chunk = padded[left_slice]

        if right_pad > period:
            # Chunk is smaller than pad area
            pad_area = _slice_at_axis(
                slice(-right_pad, -right_pad + period), axis)
            new_right_pad = right_pad - period
        else:
            # Chunk matches pad area
            pad_area = _slice_at_axis(slice(-right_pad, None), axis)
        padded[pad_area] = left_chunk

    return new_left_pad, new_right_pad


def _as_pairs(x, ndim, as_index=False):
    """
    Broadcast `x` to an array with the shape (`ndim`, 2).

    A helper function for `pad` that prepares and validates arguments like
    `pad_width` for iteration in pairs.

    Parameters
    ----------
    x : {None, scalar, array-like}
        The object to broadcast to the shape (`ndim`, 2).
    ndim : int
        Number of pairs the broadcasted `x` will have.
    as_index : bool, optional
        If `x` is not None, try to round each element of `x` to an integer
        (dtype `np.intp`) and ensure every element is positive.

    Returns
    -------
    pairs : nested iterables, shape (`ndim`, 2)
        The broadcasted version of `x`.

    Raises
    ------
    ValueError
        If `as_index` is True and `x` contains negative elements.
        Or if `x` is not broadcastable to the shape (`ndim`, 2).
    """
    if x is None:
        # Pass through None as a special case, otherwise np.round(x) fails
        # with an AttributeError
        return ((None, None),) * ndim

    x = np.array(x)
    if as_index:
        x = np.round(x).astype(np.intp, copy=False)

    if x.ndim < 3:
        # Optimization: Possibly use faster paths for cases where `x` has
        # only 1 or 2 elements. `np.broadcast_to` could handle these as well
        # but is currently slower

        if x.size == 1:
            # x was supplied as a single value
            x = x.ravel()  # Ensure x[0] works for x.ndim == 0, 1, 2
            if as_index and x < 0:
                raise ValueError("index can't contain negative values")
            return ((x[0], x[0]),) * ndim

        if x.size == 2 and x.shape != (2, 1):
            # x was supplied with a single value for each side
            # but except case when each dimension has a single value
            # which should be broadcasted to a pair,
            # e.g. [[1], [2]] -> [[1, 1], [2, 2]] not [[1, 2], [1, 2]]
            x = x.ravel()  # Ensure x[0], x[1] works
            if as_index and (x[0] < 0 or x[1] < 0):
                raise ValueError("index can't contain negative values")
            return ((x[0], x[1]),) * ndim

    if as_index and x.min() < 0:
        raise ValueError("index can't contain negative values")

    # Converting the array with `tolist` seems to improve performance
    # when iterating and indexing the result (see usage in `pad`)
    return np.broadcast_to(x, (ndim, 2)).tolist()


def _pad_dispatcher(array, pad_width, mode=None, **kwargs):
    return (array,)


###############################################################################
# Public functions


@array_function_dispatch(_pad_dispatcher, module='numpy')
def pad(array, pad_width, mode='constant', **kwargs):
    """
    Pad an array.

    Parameters
    ----------
    array : array_like of rank N
        The array to pad.
    pad_width : {sequence, array_like, int}
        Number of values padded to the edges of each axis.
        ``((before_1, after_1), ... (before_N, after_N))`` unique pad widths
        for each axis.
        ``(before, after)`` or ``((before, after),)`` yields same before
        and after pad for each axis.
        ``(pad,)`` or ``int`` is a shortcut for before = after = pad width
        for all axes.
    mode : str or function, optional
        One of the following string values or a user supplied function.

        'constant' (default)
            Pads with a constant value.
        'edge'
            Pads with the edge values of array.
        'linear_ramp'
            Pads with the linear ramp between end_value and the
            array edge value.
        'maximum'
            Pads with the maximum value of all or part of the
            vector along each axis.
        'mean'
            Pads with the mean value of all or part of the
            vector along each axis.
        'median'
            Pads with the median value of all or part of the
            vector along each axis.
        'minimum'
            Pads with the minimum value of all or part of the
            vector along each axis.
        'reflect'
            Pads with the reflection of the vector mirrored on
            the first and last values of the vector along each
            axis.
        'symmetric'
            Pads with the reflection of the vector mirrored
            along the edge of the array.
        'wrap'
            Pads with the wrap of the vector along the axis.
            The first values are used to pad the end and the
            end values are used to pad the beginning.
        'empty'
            Pads with undefined values.

        <function>
            Padding function, see Notes.
    stat_length : sequence or int, optional
        Used in 'maximum', 'mean', 'median', and 'minimum'.  Number of
        values at edge of each axis used to calculate the statistic value.

        ``((before_1, after_1), ... (before_N, after_N))`` unique statistic
        lengths for each axis.

        ``(before, after)`` or ``((before, after),)`` yields same before
        and after statistic lengths for each axis.

        ``(stat_length,)`` or ``int`` is a shortcut for
        ``before = after = statistic`` length for all axes.

        Default is ``None``, to use the entire axis.
    constant_values : sequence or scalar, optional
        Used in 'constant'.  The values to set the padded values for each
        axis.

        ``((before_1, after_1), ... (before_N, after_N))`` unique pad constants
        for each axis.

        ``(before, after)`` or ``((before, after),)`` yields same before
        and after constants for each axis.

        ``(constant,)`` or ``constant`` is a shortcut for
        ``before = after = constant`` for all axes.

        Default is 0.
    end_values : sequence or scalar, optional
        Used in 'linear_ramp'.  The values used for the ending value of the
        linear_ramp and that will form the edge of the padded array.

        ``((before_1, after_1), ... (before_N, after_N))`` unique end values
        for each axis.

        ``(before, after)`` or ``((before, after),)`` yields same before
        and after end values for each axis.

        ``(constant,)`` or ``constant`` is a shortcut for
        ``before = after = constant`` for all axes.

        Default is 0.
    reflect_type : {'even', 'odd'}, optional
        Used in 'reflect', and 'symmetric'.  The 'even' style is the
        default with an unaltered reflection around the edge value.  For
        the 'odd' style, the extended part of the array is created by
        subtracting the reflected values from two times the edge value.

    Returns
    -------
    pad : ndarray
        Padded array of rank equal to `array` with shape increased
        according to `pad_width`.

    Notes
    -----
    For an array with rank greater than 1, some of the padding of later
    axes is calculated from padding of previous axes.  This is easiest to
    think about with a rank 2 array where the corners of the padded array
    are calculated by using padded values from the first axis.

    The padding function, if used, should modify a rank 1 array in-place. It
    has the following signature::

        padding_func(vector, iaxis_pad_width, iaxis, kwargs)

    where

    vector : ndarray
        A rank 1 array already padded with zeros.  Padded values are
        vector[:iaxis_pad_width[0]] and vector[-iaxis_pad_width[1]:].
    iaxis_pad_width : tuple
        A 2-tuple of ints, iaxis_pad_width[0] represents the number of
        values padded at the beginning of vector where
        iaxis_pad_width[1] represents the number of values padded at
        the end of vector.
    iaxis : int
        The axis currently being calculated.
    kwargs : dict
        Any keyword arguments the function requires.

    Examples
    --------
    >>> import numpy as np
    >>> a = [1, 2, 3, 4, 5]
    >>> np.pad(a, (2, 3), 'constant', constant_values=(4, 6))
    array([4, 4, 1, ..., 6, 6, 6])

    >>> np.pad(a, (2, 3), 'edge')
    array([1, 1, 1, ..., 5, 5, 5])

    >>> np.pad(a, (2, 3), 'linear_ramp', end_values=(5, -4))
    array([ 5,  3,  1,  2,  3,  4,  5,  2, -1, -4])

    >>> np.pad(a, (2,), 'maximum')
    array([5, 5, 1, 2, 3, 4, 5, 5, 5])

    >>> np.pad(a, (2,), 'mean')
    array([3, 3, 1, 2, 3, 4, 5, 3, 3])

    >>> np.pad(a, (2,), 'median')
    array([3, 3, 1, 2, 3, 4, 5, 3, 3])

    >>> a = [[1, 2], [3, 4]]
    >>> np.pad(a, ((3, 2), (2, 3)), 'minimum')
    array([[1, 1, 1, 2, 1, 1, 1],
           [1, 1, 1, 2, 1, 1, 1],
           [1, 1, 1, 2, 1, 1, 1],
           [1, 1, 1, 2, 1, 1, 1],
           [3, 3, 3, 4, 3, 3, 3],
           [1, 1, 1, 2, 1, 1, 1],
           [1, 1, 1, 2, 1, 1, 1]])

    >>> a = [1, 2, 3, 4, 5]
    >>> np.pad(a, (2, 3), 'reflect')
    array([3, 2, 1, 2, 3, 4, 5, 4, 3, 2])

    >>> np.pad(a, (2, 3), 'reflect', reflect_type='odd')
    array([-1,  0,  1,  2,  3,  4,  5,  6,  7,  8])

    >>> np.pad(a, (2, 3), 'symmetric')
    array([2, 1, 1, 2, 3, 4, 5, 5, 4, 3])

    >>> np.pad(a, (2, 3), 'symmetric', reflect_type='odd')
    array([0, 1, 1, 2, 3, 4, 5, 5, 6, 7])

    >>> np.pad(a, (2, 3), 'wrap')
    array([4, 5, 1, 2, 3, 4, 5, 1, 2, 3])

    >>> def pad_with(vector, pad_width, iaxis, kwargs):
    ...     pad_value = kwargs.get('padder', 10)
    ...     vector[:pad_width[0]] = pad_value
    ...     vector[-pad_width[1]:] = pad_value
    >>> a = np.arange(6)
    >>> a = a.reshape((2, 3))
    >>> np.pad(a, 2, pad_with)
    array([[10, 10, 10, 10, 10, 10, 10],
           [10, 10, 10, 10, 10, 10, 10],
           [10, 10,  0,  1,  2, 10, 10],
           [10, 10,  3,  4,  5, 10, 10],
           [10, 10, 10, 10, 10, 10, 10],
           [10, 10, 10, 10, 10, 10, 10]])
    >>> np.pad(a, 2, pad_with, padder=100)
    array([[100, 100, 100, 100, 100, 100, 100],
           [100, 100, 100, 100, 100, 100, 100],
           [100, 100,   0,   1,   2, 100, 100],
           [100, 100,   3,   4,   5, 100, 100],
           [100, 100, 100, 100, 100, 100, 100],
           [100, 100, 100, 100, 100, 100, 100]])
    """
    array = np.asarray(array)
    pad_width = np.asarray(pad_width)

    if not pad_width.dtype.kind == 'i':
        raise TypeError('`pad_width` must be of integral type.')

    # Broadcast to shape (array.ndim, 2)
    pad_width = _as_pairs(pad_width, array.ndim, as_index=True)

    if callable(mode):
        # Old behavior: Use user-supplied function with np.apply_along_axis
        function = mode
        # Create a new zero padded array
        padded, _ = _pad_simple(array, pad_width, fill_value=0)
        # And apply along each axis

        for axis in range(padded.ndim):
            # Iterate using ndindex as in apply_along_axis, but assuming that
            # function operates inplace on the padded array.

            # view with the iteration axis at the end
            view = np.moveaxis(padded, axis, -1)

            # compute indices for the iteration axes, and append a trailing
            # ellipsis to prevent 0d arrays decaying to scalars (gh-8642)
            inds = ndindex(view.shape[:-1])
            inds = (ind + (Ellipsis,) for ind in inds)
            for ind in inds:
                function(view[ind], pad_width[axis], axis, kwargs)

        return padded

    # Make sure that no unsupported keywords were passed for the current mode
    allowed_kwargs = {
        'empty': [], 'edge': [], 'wrap': [],
        'constant': ['constant_values'],
        'linear_ramp': ['end_values'],
        'maximum': ['stat_length'],
        'mean': ['stat_length'],
        'median': ['stat_length'],
        'minimum': ['stat_length'],
        'reflect': ['reflect_type'],
        'symmetric': ['reflect_type'],
    }
    try:
        unsupported_kwargs = set(kwargs) - set(allowed_kwargs[mode])
    except KeyError:
        raise ValueError(f"mode '{mode}' is not supported") from None
    if unsupported_kwargs:
        raise ValueError("unsupported keyword arguments for mode "
                         f"'{mode}': {unsupported_kwargs}")

    stat_functions = {"maximum": np.amax, "minimum": np.amin,
                      "mean": np.mean, "median": np.median}

    # Create array with final shape and original values
    # (padded area is undefined)
    padded, original_area_slice = _pad_simple(array, pad_width)
    # And prepare iteration over all dimensions
    # (zipping may be more readable than using enumerate)
    axes = range(padded.ndim)

    if mode == "constant":
        values = kwargs.get("constant_values", 0)
        values = _as_pairs(values, padded.ndim)
        for axis, width_pair, value_pair in zip(axes, pad_width, values):
            roi = _view_roi(padded, original_area_slice, axis)
            _set_pad_area(roi, axis, width_pair, value_pair)

    elif mode == "empty":
        pass  # Do nothing as _pad_simple already returned the correct result

    elif array.size == 0:
        # Only modes "constant" and "empty" can extend empty axes, all other
        # modes depend on `array` not being empty
        # -> ensure every empty axis is only "padded with 0"
        for axis, width_pair in zip(axes, pad_width):
            if array.shape[axis] == 0 and any(width_pair):
                raise ValueError(
                    f"can't extend empty axis {axis} using modes other than "
                    "'constant' or 'empty'"
                )
        # passed, don't need to do anything more as _pad_simple already
        # returned the correct result

    elif mode == "edge":
        for axis, width_pair in zip(axes, pad_width):
            roi = _view_roi(padded, original_area_slice, axis)
            edge_pair = _get_edges(roi, axis, width_pair)
            _set_pad_area(roi, axis, width_pair, edge_pair)

    elif mode == "linear_ramp":
        end_values = kwargs.get("end_values", 0)
        end_values = _as_pairs(end_values, padded.ndim)
        for axis, width_pair, value_pair in zip(axes, pad_width, end_values):
            roi = _view_roi(padded, original_area_slice, axis)
            ramp_pair = _get_linear_ramps(roi, axis, width_pair, value_pair)
            _set_pad_area(roi, axis, width_pair, ramp_pair)

    elif mode in stat_functions:
        func = stat_functions[mode]
        length = kwargs.get("stat_length")
        length = _as_pairs(length, padded.ndim, as_index=True)
        for axis, width_pair, length_pair in zip(axes, pad_width, length):
            roi = _view_roi(padded, original_area_slice, axis)
            stat_pair = _get_stats(roi, axis, width_pair, length_pair, func)
            _set_pad_area(roi, axis, width_pair, stat_pair)

    elif mode in {"reflect", "symmetric"}:
        method = kwargs.get("reflect_type", "even")
        include_edge = mode == "symmetric"
        for axis, (left_index, right_index) in zip(axes, pad_width):
            if array.shape[axis] == 1 and (left_index > 0 or right_index > 0):
                # Extending singleton dimension for 'reflect' is legacy
                # behavior; it really should raise an error.
                edge_pair = _get_edges(padded, axis, (left_index, right_index))
                _set_pad_area(
                    padded, axis, (left_index, right_index), edge_pair)
                continue

            roi = _view_roi(padded, original_area_slice, axis)
            while left_index > 0 or right_index > 0:
                # Iteratively pad until dimension is filled with reflected
                # values. This is necessary if the pad area is larger than
                # the length of the original values in the current dimension.
                left_index, right_index = _set_reflect_both(
                    roi, axis, (left_index, right_index),
                    method, array.shape[axis], include_edge
                )

    elif mode == "wrap":
        for axis, (left_index, right_index) in zip(axes, pad_width):
            roi = _view_roi(padded, original_area_slice, axis)
            original_period = padded.shape[axis] - right_index - left_index
            while left_index > 0 or right_index > 0:
                # Iteratively pad until dimension is filled with wrapped
                # values. This is necessary if the pad area is larger than
                # the length of the original values in the current dimension.
                left_index, right_index = _set_wrap_both(
                    roi, axis, (left_index, right_index), original_period)

    return padded

# === NexusCore/src\utils\log_monitor.py ===
import threading
import time
import os
from auto_cycle_manager import auto_repair_cycle

LOG_FILE = "run.log"
WATCH_DIR = "watch_folder"
already_seen = set()

def log_watcher():
    print("🔍 エラーログ監視中...")
    while True:
        for filename in os.listdir(WATCH_DIR):
            if filename.endswith(".py") and filename not in already_seen:
                filepath = os.path.join(WATCH_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    code = f.read()
                print(f"📄 新ファイル検知: {filename}")
                fixed_code, output = auto_repair_cycle(code)
                with open(filepath.replace(".py", "_fixed.py"), "w", encoding="utf-8") as f:
                    f.write(fixed_code)
                already_seen.add(filename)
        time.sleep(10)

threading.Thread(target=log_watcher, daemon=True).start()


# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_histograms.py ===
import pytest

import numpy as np
from numpy import histogram, histogram_bin_edges, histogramdd
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_array_max_ulp,
    assert_equal,
    assert_raises,
    assert_raises_regex,
    suppress_warnings,
)


class TestHistogram:

    def setup_method(self):
        pass

    def teardown_method(self):
        pass

    def test_simple(self):
        n = 100
        v = np.random.rand(n)
        (a, b) = histogram(v)
        # check if the sum of the bins equals the number of samples
        assert_equal(np.sum(a, axis=0), n)
        # check that the bin counts are evenly spaced when the data is from
        # a linear function
        (a, b) = histogram(np.linspace(0, 10, 100))
        assert_array_equal(a, 10)

    def test_one_bin(self):
        # Ticket 632
        hist, edges = histogram([1, 2, 3, 4], [1, 2])
        assert_array_equal(hist, [2, ])
        assert_array_equal(edges, [1, 2])
        assert_raises(ValueError, histogram, [1, 2], bins=0)
        h, e = histogram([1, 2], bins=1)
        assert_equal(h, np.array([2]))
        assert_allclose(e, np.array([1., 2.]))

    def test_density(self):
        # Check that the integral of the density equals 1.
        n = 100
        v = np.random.rand(n)
        a, b = histogram(v, density=True)
        area = np.sum(a * np.diff(b))
        assert_almost_equal(area, 1)

        # Check with non-constant bin widths
        v = np.arange(10)
        bins = [0, 1, 3, 6, 10]
        a, b = histogram(v, bins, density=True)
        assert_array_equal(a, .1)
        assert_equal(np.sum(a * np.diff(b)), 1)

        # Test that passing False works too
        a, b = histogram(v, bins, density=False)
        assert_array_equal(a, [1, 2, 3, 4])

        # Variable bin widths are especially useful to deal with
        # infinities.
        v = np.arange(10)
        bins = [0, 1, 3, 6, np.inf]
        a, b = histogram(v, bins, density=True)
        assert_array_equal(a, [.1, .1, .1, 0.])

        # Taken from a bug report from N. Becker on the numpy-discussion
        # mailing list Aug. 6, 2010.
        counts, dmy = np.histogram(
            [1, 2, 3, 4], [0.5, 1.5, np.inf], density=True)
        assert_equal(counts, [.25, 0])

    def test_outliers(self):
        # Check that outliers are not tallied
        a = np.arange(10) + .5

        # Lower outliers
        h, b = histogram(a, range=[0, 9])
        assert_equal(h.sum(), 9)

        # Upper outliers
        h, b = histogram(a, range=[1, 10])
        assert_equal(h.sum(), 9)

        # Normalization
        h, b = histogram(a, range=[1, 9], density=True)
        assert_almost_equal((h * np.diff(b)).sum(), 1, decimal=15)

        # Weights
        w = np.arange(10) + .5
        h, b = histogram(a, range=[1, 9], weights=w, density=True)
        assert_equal((h * np.diff(b)).sum(), 1)

        h, b = histogram(a, bins=8, range=[1, 9], weights=w)
        assert_equal(h, w[1:-1])

    def test_arr_weights_mismatch(self):
        a = np.arange(10) + .5
        w = np.arange(11) + .5
        with assert_raises_regex(ValueError, "same shape as"):
            h, b = histogram(a, range=[1, 9], weights=w, density=True)

    def test_type(self):
        # Check the type of the returned histogram
        a = np.arange(10) + .5
        h, b = histogram(a)
        assert_(np.issubdtype(h.dtype, np.integer))

        h, b = histogram(a, density=True)
        assert_(np.issubdtype(h.dtype, np.floating))

        h, b = histogram(a, weights=np.ones(10, int))
        assert_(np.issubdtype(h.dtype, np.integer))

        h, b = histogram(a, weights=np.ones(10, float))
        assert_(np.issubdtype(h.dtype, np.floating))

    def test_f32_rounding(self):
        # gh-4799, check that the rounding of the edges works with float32
        x = np.array([276.318359, -69.593948, 21.329449], dtype=np.float32)
        y = np.array([5005.689453, 4481.327637, 6010.369629], dtype=np.float32)
        counts_hist, xedges, yedges = np.histogram2d(x, y, bins=100)
        assert_equal(counts_hist.sum(), 3.)

    def test_bool_conversion(self):
        # gh-12107
        # Reference integer histogram
        a = np.array([1, 1, 0], dtype=np.uint8)
        int_hist, int_edges = np.histogram(a)

        # Should raise an warning on booleans
        # Ensure that the histograms are equivalent, need to suppress
        # the warnings to get the actual outputs
        with suppress_warnings() as sup:
            rec = sup.record(RuntimeWarning, 'Converting input from .*')
            hist, edges = np.histogram([True, True, False])
            # A warning should be issued
            assert_equal(len(rec), 1)
            assert_array_equal(hist, int_hist)
            assert_array_equal(edges, int_edges)

    def test_weights(self):
        v = np.random.rand(100)
        w = np.ones(100) * 5
        a, b = histogram(v)
        na, nb = histogram(v, density=True)
        wa, wb = histogram(v, weights=w)
        nwa, nwb = histogram(v, weights=w, density=True)
        assert_array_almost_equal(a * 5, wa)
        assert_array_almost_equal(na, nwa)

        # Check weights are properly applied.
        v = np.linspace(0, 10, 10)
        w = np.concatenate((np.zeros(5), np.ones(5)))
        wa, wb = histogram(v, bins=np.arange(11), weights=w)
        assert_array_almost_equal(wa, w)

        # Check with integer weights
        wa, wb = histogram([1, 2, 2, 4], bins=4, weights=[4, 3, 2, 1])
        assert_array_equal(wa, [4, 5, 0, 1])
        wa, wb = histogram(
            [1, 2, 2, 4], bins=4, weights=[4, 3, 2, 1], density=True)
        assert_array_almost_equal(wa, np.array([4, 5, 0, 1]) / 10. / 3. * 4)

        # Check weights with non-uniform bin widths
        a, b = histogram(
            np.arange(9), [0, 1, 3, 6, 10],
            weights=[2, 1, 1, 1, 1, 1, 1, 1, 1], density=True)
        assert_almost_equal(a, [.2, .1, .1, .075])

    def test_exotic_weights(self):

        # Test the use of weights that are not integer or floats, but e.g.
        # complex numbers or object types.

        # Complex weights
        values = np.array([1.3, 2.5, 2.3])
        weights = np.array([1, -1, 2]) + 1j * np.array([2, 1, 2])

        # Check with custom bins
        wa, wb = histogram(values, bins=[0, 2, 3], weights=weights)
        assert_array_almost_equal(wa, np.array([1, 1]) + 1j * np.array([2, 3]))

        # Check with even bins
        wa, wb = histogram(values, bins=2, range=[1, 3], weights=weights)
        assert_array_almost_equal(wa, np.array([1, 1]) + 1j * np.array([2, 3]))

        # Decimal weights
        from decimal import Decimal
        values = np.array([1.3, 2.5, 2.3])
        weights = np.array([Decimal(1), Decimal(2), Decimal(3)])

        # Check with custom bins
        wa, wb = histogram(values, bins=[0, 2, 3], weights=weights)
        assert_array_almost_equal(wa, [Decimal(1), Decimal(5)])

        # Check with even bins
        wa, wb = histogram(values, bins=2, range=[1, 3], weights=weights)
        assert_array_almost_equal(wa, [Decimal(1), Decimal(5)])

    def test_no_side_effects(self):
        # This is a regression test that ensures that values passed to
        # ``histogram`` are unchanged.
        values = np.array([1.3, 2.5, 2.3])
        np.histogram(values, range=[-10, 10], bins=100)
        assert_array_almost_equal(values, [1.3, 2.5, 2.3])

    def test_empty(self):
        a, b = histogram([], bins=([0, 1]))
        assert_array_equal(a, np.array([0]))
        assert_array_equal(b, np.array([0, 1]))

    def test_error_binnum_type(self):
        # Tests if right Error is raised if bins argument is float
        vals = np.linspace(0.0, 1.0, num=100)
        histogram(vals, 5)
        assert_raises(TypeError, histogram, vals, 2.4)

    def test_finite_range(self):
        # Normal ranges should be fine
        vals = np.linspace(0.0, 1.0, num=100)
        histogram(vals, range=[0.25, 0.75])
        assert_raises(ValueError, histogram, vals, range=[np.nan, 0.75])
        assert_raises(ValueError, histogram, vals, range=[0.25, np.inf])

    def test_invalid_range(self):
        # start of range must be < end of range
        vals = np.linspace(0.0, 1.0, num=100)
        with assert_raises_regex(ValueError, "max must be larger than"):
            np.histogram(vals, range=[0.1, 0.01])

    def test_bin_edge_cases(self):
        # Ensure that floating-point computations correctly place edge cases.
        arr = np.array([337, 404, 739, 806, 1007, 1811, 2012])
        hist, edges = np.histogram(arr, bins=8296, range=(2, 2280))
        mask = hist > 0
        left_edges = edges[:-1][mask]
        right_edges = edges[1:][mask]
        for x, left, right in zip(arr, left_edges, right_edges):
            assert_(x >= left)
            assert_(x < right)

    def test_last_bin_inclusive_range(self):
        arr = np.array([0.,  0.,  0.,  1.,  2.,  3.,  3.,  4.,  5.])
        hist, edges = np.histogram(arr, bins=30, range=(-0.5, 5))
        assert_equal(hist[-1], 1)

    def test_bin_array_dims(self):
        # gracefully handle bins object > 1 dimension
        vals = np.linspace(0.0, 1.0, num=100)
        bins = np.array([[0, 0.5], [0.6, 1.0]])
        with assert_raises_regex(ValueError, "must be 1d"):
            np.histogram(vals, bins=bins)

    def test_unsigned_monotonicity_check(self):
        # Ensures ValueError is raised if bins not increasing monotonically
        # when bins contain unsigned values (see #9222)
        arr = np.array([2])
        bins = np.array([1, 3, 1], dtype='uint64')
        with assert_raises(ValueError):
            hist, edges = np.histogram(arr, bins=bins)

    def test_object_array_of_0d(self):
        # gh-7864
        assert_raises(ValueError,
            histogram, [np.array(0.4) for i in range(10)] + [-np.inf])
        assert_raises(ValueError,
            histogram, [np.array(0.4) for i in range(10)] + [np.inf])

        # these should not crash
        np.histogram([np.array(0.5) for i in range(10)] + [.500000000000002])
        np.histogram([np.array(0.5) for i in range(10)] + [.5])

    def test_some_nan_values(self):
        # gh-7503
        one_nan = np.array([0, 1, np.nan])
        all_nan = np.array([np.nan, np.nan])

        # the internal comparisons with NaN give warnings
        sup = suppress_warnings()
        sup.filter(RuntimeWarning)
        with sup:
            # can't infer range with nan
            assert_raises(ValueError, histogram, one_nan, bins='auto')
            assert_raises(ValueError, histogram, all_nan, bins='auto')

            # explicit range solves the problem
            h, b = histogram(one_nan, bins='auto', range=(0, 1))
            assert_equal(h.sum(), 2)  # nan is not counted
            h, b = histogram(all_nan, bins='auto', range=(0, 1))
            assert_equal(h.sum(), 0)  # nan is not counted

            # as does an explicit set of bins
            h, b = histogram(one_nan, bins=[0, 1])
            assert_equal(h.sum(), 2)  # nan is not counted
            h, b = histogram(all_nan, bins=[0, 1])
            assert_equal(h.sum(), 0)  # nan is not counted

    def test_datetime(self):
        begin = np.datetime64('2000-01-01', 'D')
        offsets = np.array([0, 0, 1, 1, 2, 3, 5, 10, 20])
        bins = np.array([0, 2, 7, 20])
        dates = begin + offsets
        date_bins = begin + bins

        td = np.dtype('timedelta64[D]')

        # Results should be the same for integer offsets or datetime values.
        # For now, only explicit bins are supported, since linspace does not
        # work on datetimes or timedeltas
        d_count, d_edge = histogram(dates, bins=date_bins)
        t_count, t_edge = histogram(offsets.astype(td), bins=bins.astype(td))
        i_count, i_edge = histogram(offsets, bins=bins)

        assert_equal(d_count, i_count)
        assert_equal(t_count, i_count)

        assert_equal((d_edge - begin).astype(int), i_edge)
        assert_equal(t_edge.astype(int), i_edge)

        assert_equal(d_edge.dtype, dates.dtype)
        assert_equal(t_edge.dtype, td)

    def do_signed_overflow_bounds(self, dtype):
        exponent = 8 * np.dtype(dtype).itemsize - 1
        arr = np.array([-2**exponent + 4, 2**exponent - 4], dtype=dtype)
        hist, e = histogram(arr, bins=2)
        assert_equal(e, [-2**exponent + 4, 0, 2**exponent - 4])
        assert_equal(hist, [1, 1])

    def test_signed_overflow_bounds(self):
        self.do_signed_overflow_bounds(np.byte)
        self.do_signed_overflow_bounds(np.short)
        self.do_signed_overflow_bounds(np.intc)
        self.do_signed_overflow_bounds(np.int_)
        self.do_signed_overflow_bounds(np.longlong)

    def do_precision_lower_bound(self, float_small, float_large):
        eps = np.finfo(float_large).eps

        arr = np.array([1.0], float_small)
        range = np.array([1.0 + eps, 2.0], float_large)

        # test is looking for behavior when the bounds change between dtypes
        if range.astype(float_small)[0] != 1:
            return

        # previously crashed
        count, x_loc = np.histogram(arr, bins=1, range=range)
        assert_equal(count, [0])
        assert_equal(x_loc.dtype, float_large)

    def do_precision_upper_bound(self, float_small, float_large):
        eps = np.finfo(float_large).eps

        arr = np.array([1.0], float_small)
        range = np.array([0.0, 1.0 - eps], float_large)

        # test is looking for behavior when the bounds change between dtypes
        if range.astype(float_small)[-1] != 1:
            return

        # previously crashed
        count, x_loc = np.histogram(arr, bins=1, range=range)
        assert_equal(count, [0])

        assert_equal(x_loc.dtype, float_large)

    def do_precision(self, float_small, float_large):
        self.do_precision_lower_bound(float_small, float_large)
        self.do_precision_upper_bound(float_small, float_large)

    def test_precision(self):
        # not looping results in a useful stack trace upon failure
        self.do_precision(np.half, np.single)
        self.do_precision(np.half, np.double)
        self.do_precision(np.half, np.longdouble)
        self.do_precision(np.single, np.double)
        self.do_precision(np.single, np.longdouble)
        self.do_precision(np.double, np.longdouble)

    def test_histogram_bin_edges(self):
        hist, e = histogram([1, 2, 3, 4], [1, 2])
        edges = histogram_bin_edges([1, 2, 3, 4], [1, 2])
        assert_array_equal(edges, e)

        arr = np.array([0.,  0.,  0.,  1.,  2.,  3.,  3.,  4.,  5.])
        hist, e = histogram(arr, bins=30, range=(-0.5, 5))
        edges = histogram_bin_edges(arr, bins=30, range=(-0.5, 5))
        assert_array_equal(edges, e)

        hist, e = histogram(arr, bins='auto', range=(0, 1))
        edges = histogram_bin_edges(arr, bins='auto', range=(0, 1))
        assert_array_equal(edges, e)

    def test_small_value_range(self):
        arr = np.array([1, 1 + 2e-16] * 10)
        with pytest.raises(ValueError, match="Too many bins for data range"):
            histogram(arr, bins=10)

    # @requires_memory(free_bytes=1e10)
    # @pytest.mark.slow
    @pytest.mark.skip(reason="Bad memory reports lead to OOM in ci testing")
    def test_big_arrays(self):
        sample = np.zeros([100000000, 3])
        xbins = 400
        ybins = 400
        zbins = np.arange(16000)
        hist = np.histogramdd(sample=sample, bins=(xbins, ybins, zbins))
        assert_equal(type(hist), type((1, 2)))

    def test_gh_23110(self):
        hist, e = np.histogram(np.array([-0.9e-308], dtype='>f8'),
                               bins=2,
                               range=(-1e-308, -2e-313))
        expected_hist = np.array([1, 0])
        assert_array_equal(hist, expected_hist)

    def test_gh_28400(self):
        e = 1 + 1e-12
        Z = [0, 1, 1, 1, 1, 1, e, e, e, e, e, e, 2]
        counts, edges = np.histogram(Z, bins="auto")
        assert len(counts) < 10
        assert edges[0] == Z[0]
        assert edges[-1] == Z[-1]

class TestHistogramOptimBinNums:
    """
    Provide test coverage when using provided estimators for optimal number of
    bins
    """

    def test_empty(self):
        estimator_list = ['fd', 'scott', 'rice', 'sturges',
                          'doane', 'sqrt', 'auto', 'stone']
        # check it can deal with empty data
        for estimator in estimator_list:
            a, b = histogram([], bins=estimator)
            assert_array_equal(a, np.array([0]))
            assert_array_equal(b, np.array([0, 1]))

    def test_simple(self):
        """
        Straightforward testing with a mixture of linspace data (for
        consistency). All test values have been precomputed and the values
        shouldn't change
        """
        # Some basic sanity checking, with some fixed data.
        # Checking for the correct number of bins
        basic_test = {50:   {'fd': 4,  'scott': 4,  'rice': 8,  'sturges': 7,
                             'doane': 8, 'sqrt': 8, 'auto': 7, 'stone': 2},
                      500:  {'fd': 8,  'scott': 8,  'rice': 16, 'sturges': 10,
                             'doane': 12, 'sqrt': 23, 'auto': 10, 'stone': 9},
                      5000: {'fd': 17, 'scott': 17, 'rice': 35, 'sturges': 14,
                             'doane': 17, 'sqrt': 71, 'auto': 17, 'stone': 20}}

        for testlen, expectedResults in basic_test.items():
            # Create some sort of non uniform data to test with
            # (2 peak uniform mixture)
            x1 = np.linspace(-10, -1, testlen // 5 * 2)
            x2 = np.linspace(1, 10, testlen // 5 * 3)
            x = np.concatenate((x1, x2))
            for estimator, numbins in expectedResults.items():
                a, b = np.histogram(x, estimator)
                assert_equal(len(a), numbins, err_msg=f"For the {estimator} estimator "
                             f"with datasize of {testlen}")

    def test_small(self):
        """
        Smaller datasets have the potential to cause issues with the data
        adaptive methods, especially the FD method. All bin numbers have been
        precalculated.
        """
        small_dat = {1: {'fd': 1, 'scott': 1, 'rice': 1, 'sturges': 1,
                         'doane': 1, 'sqrt': 1, 'stone': 1},
                     2: {'fd': 2, 'scott': 1, 'rice': 3, 'sturges': 2,
                         'doane': 1, 'sqrt': 2, 'stone': 1},
                     3: {'fd': 2, 'scott': 2, 'rice': 3, 'sturges': 3,
                         'doane': 3, 'sqrt': 2, 'stone': 1}}

        for testlen, expectedResults in small_dat.items():
            testdat = np.arange(testlen).astype(float)
            for estimator, expbins in expectedResults.items():
                a, b = np.histogram(testdat, estimator)
                assert_equal(len(a), expbins, err_msg=f"For the {estimator} estimator "
                             f"with datasize of {testlen}")

    def test_incorrect_methods(self):
        """
        Check a Value Error is thrown when an unknown string is passed in
        """
        check_list = ['mad', 'freeman', 'histograms', 'IQR']
        for estimator in check_list:
            assert_raises(ValueError, histogram, [1, 2, 3], estimator)

    def test_novariance(self):
        """
        Check that methods handle no variance in data
        Primarily for Scott and FD as the SD and IQR are both 0 in this case
        """
        novar_dataset = np.ones(100)
        novar_resultdict = {'fd': 1, 'scott': 1, 'rice': 1, 'sturges': 1,
                            'doane': 1, 'sqrt': 1, 'auto': 1, 'stone': 1}

        for estimator, numbins in novar_resultdict.items():
            a, b = np.histogram(novar_dataset, estimator)
            assert_equal(len(a), numbins,
                         err_msg=f"{estimator} estimator, No Variance test")

    def test_limited_variance(self):
        """
        Check when IQR is 0, but variance exists, we return a reasonable value.
        """
        lim_var_data = np.ones(1000)
        lim_var_data[:3] = 0
        lim_var_data[-4:] = 100

        edges_auto = histogram_bin_edges(lim_var_data, 'auto')
        assert_equal(edges_auto[0], 0)
        assert_equal(edges_auto[-1], 100.)
        assert len(edges_auto) < 100

        edges_fd = histogram_bin_edges(lim_var_data, 'fd')
        assert_equal(edges_fd, np.array([0, 100]))

        edges_sturges = histogram_bin_edges(lim_var_data, 'sturges')
        assert_equal(edges_sturges, np.linspace(0, 100, 12))

    def test_outlier(self):
        """
        Check the FD, Scott and Doane with outliers.

        The FD estimates a smaller binwidth since it's less affected by
        outliers. Since the range is so (artificially) large, this means more
        bins, most of which will be empty, but the data of interest usually is
        unaffected. The Scott estimator is more affected and returns fewer bins,
        despite most of the variance being in one area of the data. The Doane
        estimator lies somewhere between the other two.
        """
        xcenter = np.linspace(-10, 10, 50)
        outlier_dataset = np.hstack((np.linspace(-110, -100, 5), xcenter))

        outlier_resultdict = {'fd': 21, 'scott': 5, 'doane': 11, 'stone': 6}

        for estimator, numbins in outlier_resultdict.items():
            a, b = np.histogram(outlier_dataset, estimator)
            assert_equal(len(a), numbins)

    def test_scott_vs_stone(self):
        """Verify that Scott's rule and Stone's rule converges for normally distributed data"""

        def nbins_ratio(seed, size):
            rng = np.random.RandomState(seed)
            x = rng.normal(loc=0, scale=2, size=size)
            a, b = len(np.histogram(x, 'stone')[0]), len(np.histogram(x, 'scott')[0])
            return a / (a + b)

        ll = [[nbins_ratio(seed, size) for size in np.geomspace(start=10, stop=100, num=4).round().astype(int)]
              for seed in range(10)]

        # the average difference between the two methods decreases as the dataset size increases.
        avg = abs(np.mean(ll, axis=0) - 0.5)
        assert_almost_equal(avg, [0.15, 0.09, 0.08, 0.03], decimal=2)

    def test_simple_range(self):
        """
        Straightforward testing with a mixture of linspace data (for
        consistency). Adding in a 3rd mixture that will then be
        completely ignored. All test values have been precomputed and
        the shouldn't change.
        """
        # some basic sanity checking, with some fixed data.
        # Checking for the correct number of bins
        basic_test = {
                      50:   {'fd': 8,  'scott': 8,  'rice': 15,
                             'sturges': 14, 'auto': 14, 'stone': 8},
                      500:  {'fd': 15, 'scott': 16, 'rice': 32,
                             'sturges': 20, 'auto': 20, 'stone': 80},
                      5000: {'fd': 33, 'scott': 33, 'rice': 69,
                             'sturges': 27, 'auto': 33, 'stone': 80}
                     }

        for testlen, expectedResults in basic_test.items():
            # create some sort of non uniform data to test with
            # (3 peak uniform mixture)
            x1 = np.linspace(-10, -1, testlen // 5 * 2)
            x2 = np.linspace(1, 10, testlen // 5 * 3)
            x3 = np.linspace(-100, -50, testlen)
            x = np.hstack((x1, x2, x3))
            for estimator, numbins in expectedResults.items():
                a, b = np.histogram(x, estimator, range=(-20, 20))
                msg = f"For the {estimator} estimator"
                msg += f" with datasize of {testlen}"
                assert_equal(len(a), numbins, err_msg=msg)

    @pytest.mark.parametrize("bins", ['auto', 'fd', 'doane', 'scott',
                                      'stone', 'rice', 'sturges'])
    def test_signed_integer_data(self, bins):
        # Regression test for gh-14379.
        a = np.array([-2, 0, 127], dtype=np.int8)
        hist, edges = np.histogram(a, bins=bins)
        hist32, edges32 = np.histogram(a.astype(np.int32), bins=bins)
        assert_array_equal(hist, hist32)
        assert_array_equal(edges, edges32)

    @pytest.mark.parametrize("bins", ['auto', 'fd', 'doane', 'scott',
                                      'stone', 'rice', 'sturges'])
    def test_integer(self, bins):
        """
        Test that bin width for integer data is at least 1.
        """
        with suppress_warnings() as sup:
            if bins == 'stone':
                sup.filter(RuntimeWarning)
            assert_equal(
                np.histogram_bin_edges(np.tile(np.arange(9), 1000), bins),
                np.arange(9))

    def test_integer_non_auto(self):
        """
        Test that the bin-width>=1 requirement *only* applies to auto binning.
        """
        assert_equal(
            np.histogram_bin_edges(np.tile(np.arange(9), 1000), 16),
            np.arange(17) / 2)
        assert_equal(
            np.histogram_bin_edges(np.tile(np.arange(9), 1000), [.1, .2]),
            [.1, .2])

    def test_simple_weighted(self):
        """
        Check that weighted data raises a TypeError
        """
        estimator_list = ['fd', 'scott', 'rice', 'sturges', 'auto']
        for estimator in estimator_list:
            assert_raises(TypeError, histogram, [1, 2, 3],
                          estimator, weights=[1, 2, 3])


class TestHistogramdd:

    def test_simple(self):
        x = np.array([[-.5, .5, 1.5], [-.5, 1.5, 2.5], [-.5, 2.5, .5],
                      [.5,  .5, 1.5], [.5,  1.5, 2.5], [.5,  2.5, 2.5]])
        H, edges = histogramdd(x, (2, 3, 3),
                               range=[[-1, 1], [0, 3], [0, 3]])
        answer = np.array([[[0, 1, 0], [0, 0, 1], [1, 0, 0]],
                           [[0, 1, 0], [0, 0, 1], [0, 0, 1]]])
        assert_array_equal(H, answer)

        # Check normalization
        ed = [[-2, 0, 2], [0, 1, 2, 3], [0, 1, 2, 3]]
        H, edges = histogramdd(x, bins=ed, density=True)
        assert_(np.all(H == answer / 12.))

        # Check that H has the correct shape.
        H, edges = histogramdd(x, (2, 3, 4),
                               range=[[-1, 1], [0, 3], [0, 4]],
                               density=True)
        answer = np.array([[[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]],
                           [[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 1, 0]]])
        assert_array_almost_equal(H, answer / 6., 4)
        # Check that a sequence of arrays is accepted and H has the correct
        # shape.
        z = [np.squeeze(y) for y in np.split(x, 3, axis=1)]
        H, edges = histogramdd(
            z, bins=(4, 3, 2), range=[[-2, 2], [0, 3], [0, 2]])
        answer = np.array([[[0, 0], [0, 0], [0, 0]],
                           [[0, 1], [0, 0], [1, 0]],
                           [[0, 1], [0, 0], [0, 0]],
                           [[0, 0], [0, 0], [0, 0]]])
        assert_array_equal(H, answer)

        Z = np.zeros((5, 5, 5))
        Z[list(range(5)), list(range(5)), list(range(5))] = 1.
        H, edges = histogramdd([np.arange(5), np.arange(5), np.arange(5)], 5)
        assert_array_equal(H, Z)

    def test_shape_3d(self):
        # All possible permutations for bins of different lengths in 3D.
        bins = ((5, 4, 6), (6, 4, 5), (5, 6, 4), (4, 6, 5), (6, 5, 4),
                (4, 5, 6))
        r = np.random.rand(10, 3)
        for b in bins:
            H, edges = histogramdd(r, b)
            assert_(H.shape == b)

    def test_shape_4d(self):
        # All possible permutations for bins of different lengths in 4D.
        bins = ((7, 4, 5, 6), (4, 5, 7, 6), (5, 6, 4, 7), (7, 6, 5, 4),
                (5, 7, 6, 4), (4, 6, 7, 5), (6, 5, 7, 4), (7, 5, 4, 6),
                (7, 4, 6, 5), (6, 4, 7, 5), (6, 7, 5, 4), (4, 6, 5, 7),
                (4, 7, 5, 6), (5, 4, 6, 7), (5, 7, 4, 6), (6, 7, 4, 5),
                (6, 5, 4, 7), (4, 7, 6, 5), (4, 5, 6, 7), (7, 6, 4, 5),
                (5, 4, 7, 6), (5, 6, 7, 4), (6, 4, 5, 7), (7, 5, 6, 4))

        r = np.random.rand(10, 4)
        for b in bins:
            H, edges = histogramdd(r, b)
            assert_(H.shape == b)

    def test_weights(self):
        v = np.random.rand(100, 2)
        hist, edges = histogramdd(v)
        n_hist, edges = histogramdd(v, density=True)
        w_hist, edges = histogramdd(v, weights=np.ones(100))
        assert_array_equal(w_hist, hist)
        w_hist, edges = histogramdd(v, weights=np.ones(100) * 2, density=True)
        assert_array_equal(w_hist, n_hist)
        w_hist, edges = histogramdd(v, weights=np.ones(100, int) * 2)
        assert_array_equal(w_hist, 2 * hist)

    def test_identical_samples(self):
        x = np.zeros((10, 2), int)
        hist, edges = histogramdd(x, bins=2)
        assert_array_equal(edges[0], np.array([-0.5, 0., 0.5]))

    def test_empty(self):
        a, b = histogramdd([[], []], bins=([0, 1], [0, 1]))
        assert_array_max_ulp(a, np.array([[0.]]))
        a, b = np.histogramdd([[], [], []], bins=2)
        assert_array_max_ulp(a, np.zeros((2, 2, 2)))

    def test_bins_errors(self):
        # There are two ways to specify bins. Check for the right errors
        # when mixing those.
        x = np.arange(8).reshape(2, 4)
        assert_raises(ValueError, np.histogramdd, x, bins=[-1, 2, 4, 5])
        assert_raises(ValueError, np.histogramdd, x, bins=[1, 0.99, 1, 1])
        assert_raises(
            ValueError, np.histogramdd, x, bins=[1, 1, 1, [1, 2, 3, -3]])
        assert_(np.histogramdd(x, bins=[1, 1, 1, [1, 2, 3, 4]]))

    def test_inf_edges(self):
        # Test using +/-inf bin edges works. See #1788.
        with np.errstate(invalid='ignore'):
            x = np.arange(6).reshape(3, 2)
            expected = np.array([[1, 0], [0, 1], [0, 1]])
            h, e = np.histogramdd(x, bins=[3, [-np.inf, 2, 10]])
            assert_allclose(h, expected)
            h, e = np.histogramdd(x, bins=[3, np.array([-1, 2, np.inf])])
            assert_allclose(h, expected)
            h, e = np.histogramdd(x, bins=[3, [-np.inf, 3, np.inf]])
            assert_allclose(h, expected)

    def test_rightmost_binedge(self):
        # Test event very close to rightmost binedge. See Github issue #4266
        x = [0.9999999995]
        bins = [[0., 0.5, 1.0]]
        hist, _ = histogramdd(x, bins=bins)
        assert_(hist[0] == 0.0)
        assert_(hist[1] == 1.)
        x = [1.0]
        bins = [[0., 0.5, 1.0]]
        hist, _ = histogramdd(x, bins=bins)
        assert_(hist[0] == 0.0)
        assert_(hist[1] == 1.)
        x = [1.0000000001]
        bins = [[0., 0.5, 1.0]]
        hist, _ = histogramdd(x, bins=bins)
        assert_(hist[0] == 0.0)
        assert_(hist[1] == 0.0)
        x = [1.0001]
        bins = [[0., 0.5, 1.0]]
        hist, _ = histogramdd(x, bins=bins)
        assert_(hist[0] == 0.0)
        assert_(hist[1] == 0.0)

    def test_finite_range(self):
        vals = np.random.random((100, 3))
        histogramdd(vals, range=[[0.0, 1.0], [0.25, 0.75], [0.25, 0.5]])
        assert_raises(ValueError, histogramdd, vals,
                      range=[[0.0, 1.0], [0.25, 0.75], [0.25, np.inf]])
        assert_raises(ValueError, histogramdd, vals,
                      range=[[0.0, 1.0], [np.nan, 0.75], [0.25, 0.5]])

    def test_equal_edges(self):
        """ Test that adjacent entries in an edge array can be equal """
        x = np.array([0, 1, 2])
        y = np.array([0, 1, 2])
        x_edges = np.array([0, 2, 2])
        y_edges = 1
        hist, edges = histogramdd((x, y), bins=(x_edges, y_edges))

        hist_expected = np.array([
            [2.],
            [1.],  # x == 2 falls in the final bin
        ])
        assert_equal(hist, hist_expected)

    def test_edge_dtype(self):
        """ Test that if an edge array is input, its type is preserved """
        x = np.array([0, 10, 20])
        y = x / 10
        x_edges = np.array([0, 5, 15, 20])
        y_edges = x_edges / 10
        hist, edges = histogramdd((x, y), bins=(x_edges, y_edges))

        assert_equal(edges[0].dtype, x_edges.dtype)
        assert_equal(edges[1].dtype, y_edges.dtype)

    def test_large_integers(self):
        big = 2**60  # Too large to represent with a full precision float

        x = np.array([0], np.int64)
        x_edges = np.array([-1, +1], np.int64)
        y = big + x
        y_edges = big + x_edges

        hist, edges = histogramdd((x, y), bins=(x_edges, y_edges))

        assert_equal(hist[0, 0], 1)

    def test_density_non_uniform_2d(self):
        # Defines the following grid:
        #
        #    0 2     8
        #   0+-+-----+
        #    + |     +
        #    + |     +
        #   6+-+-----+
        #   8+-+-----+
        x_edges = np.array([0, 2, 8])
        y_edges = np.array([0, 6, 8])
        relative_areas = np.array([
            [3, 9],
            [1, 3]])

        # ensure the number of points in each region is proportional to its area
        x = np.array([1] + [1] * 3 + [7] * 3 + [7] * 9)
        y = np.array([7] + [1] * 3 + [7] * 3 + [1] * 9)

        # sanity check that the above worked as intended
        hist, edges = histogramdd((y, x), bins=(y_edges, x_edges))
        assert_equal(hist, relative_areas)

        # resulting histogram should be uniform, since counts and areas are proportional
        hist, edges = histogramdd((y, x), bins=(y_edges, x_edges), density=True)
        assert_equal(hist, 1 / (8 * 8))

    def test_density_non_uniform_1d(self):
        # compare to histogram to show the results are the same
        v = np.arange(10)
        bins = np.array([0, 1, 3, 6, 10])
        hist, edges = histogram(v, bins, density=True)
        hist_dd, edges_dd = histogramdd((v,), (bins,), density=True)
        assert_equal(hist, hist_dd)
        assert_equal(edges, edges_dd[0])

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_shape_base.py ===
import functools
import sys

import pytest

import numpy as np
from numpy import (
    apply_along_axis,
    apply_over_axes,
    array_split,
    column_stack,
    dsplit,
    dstack,
    expand_dims,
    hsplit,
    kron,
    put_along_axis,
    split,
    take_along_axis,
    tile,
    vsplit,
)
from numpy.exceptions import AxisError
from numpy.testing import assert_, assert_array_equal, assert_equal, assert_raises

IS_64BIT = sys.maxsize > 2**32


def _add_keepdims(func):
    """ hack in keepdims behavior into a function taking an axis """
    @functools.wraps(func)
    def wrapped(a, axis, **kwargs):
        res = func(a, axis=axis, **kwargs)
        if axis is None:
            axis = 0  # res is now a scalar, so we can insert this anywhere
        return np.expand_dims(res, axis=axis)
    return wrapped


class TestTakeAlongAxis:
    def test_argequivalent(self):
        """ Test it translates from arg<func> to <func> """
        from numpy.random import rand
        a = rand(3, 4, 5)

        funcs = [
            (np.sort, np.argsort, {}),
            (_add_keepdims(np.min), _add_keepdims(np.argmin), {}),
            (_add_keepdims(np.max), _add_keepdims(np.argmax), {}),
            #(np.partition, np.argpartition, dict(kth=2)),
        ]

        for func, argfunc, kwargs in funcs:
            for axis in list(range(a.ndim)) + [None]:
                a_func = func(a, axis=axis, **kwargs)
                ai_func = argfunc(a, axis=axis, **kwargs)
                assert_equal(a_func, take_along_axis(a, ai_func, axis=axis))

    def test_invalid(self):
        """ Test it errors when indices has too few dimensions """
        a = np.ones((10, 10))
        ai = np.ones((10, 2), dtype=np.intp)

        # sanity check
        take_along_axis(a, ai, axis=1)

        # not enough indices
        assert_raises(ValueError, take_along_axis, a, np.array(1), axis=1)
        # bool arrays not allowed
        assert_raises(IndexError, take_along_axis, a, ai.astype(bool), axis=1)
        # float arrays not allowed
        assert_raises(IndexError, take_along_axis, a, ai.astype(float), axis=1)
        # invalid axis
        assert_raises(AxisError, take_along_axis, a, ai, axis=10)
        # invalid indices
        assert_raises(ValueError, take_along_axis, a, ai, axis=None)

    def test_empty(self):
        """ Test everything is ok with empty results, even with inserted dims """
        a = np.ones((3, 4, 5))
        ai = np.ones((3, 0, 5), dtype=np.intp)

        actual = take_along_axis(a, ai, axis=1)
        assert_equal(actual.shape, ai.shape)

    def test_broadcast(self):
        """ Test that non-indexing dimensions are broadcast in both directions """
        a = np.ones((3, 4, 1))
        ai = np.ones((1, 2, 5), dtype=np.intp)
        actual = take_along_axis(a, ai, axis=1)
        assert_equal(actual.shape, (3, 2, 5))


class TestPutAlongAxis:
    def test_replace_max(self):
        a_base = np.array([[10, 30, 20], [60, 40, 50]])

        for axis in list(range(a_base.ndim)) + [None]:
            # we mutate this in the loop
            a = a_base.copy()

            # replace the max with a small value
            i_max = _add_keepdims(np.argmax)(a, axis=axis)
            put_along_axis(a, i_max, -99, axis=axis)

            # find the new minimum, which should max
            i_min = _add_keepdims(np.argmin)(a, axis=axis)

            assert_equal(i_min, i_max)

    def test_broadcast(self):
        """ Test that non-indexing dimensions are broadcast in both directions """
        a = np.ones((3, 4, 1))
        ai = np.arange(10, dtype=np.intp).reshape((1, 2, 5)) % 4
        put_along_axis(a, ai, 20, axis=1)
        assert_equal(take_along_axis(a, ai, axis=1), 20)

    def test_invalid(self):
        """ Test invalid inputs """
        a_base = np.array([[10, 30, 20], [60, 40, 50]])
        indices = np.array([[0], [1]])
        values = np.array([[2], [1]])

        # sanity check
        a = a_base.copy()
        put_along_axis(a, indices, values, axis=0)
        assert np.all(a == [[2, 2, 2], [1, 1, 1]])

        # invalid indices
        a = a_base.copy()
        with assert_raises(ValueError) as exc:
            put_along_axis(a, indices, values, axis=None)
        assert "single dimension" in str(exc.exception)


class TestApplyAlongAxis:
    def test_simple(self):
        a = np.ones((20, 10), 'd')
        assert_array_equal(
            apply_along_axis(len, 0, a), len(a) * np.ones(a.shape[1]))

    def test_simple101(self):
        a = np.ones((10, 101), 'd')
        assert_array_equal(
            apply_along_axis(len, 0, a), len(a) * np.ones(a.shape[1]))

    def test_3d(self):
        a = np.arange(27).reshape((3, 3, 3))
        assert_array_equal(apply_along_axis(np.sum, 0, a),
                           [[27, 30, 33], [36, 39, 42], [45, 48, 51]])

    def test_preserve_subclass(self):
        def double(row):
            return row * 2

        class MyNDArray(np.ndarray):
            pass

        m = np.array([[0, 1], [2, 3]]).view(MyNDArray)
        expected = np.array([[0, 2], [4, 6]]).view(MyNDArray)

        result = apply_along_axis(double, 0, m)
        assert_(isinstance(result, MyNDArray))
        assert_array_equal(result, expected)

        result = apply_along_axis(double, 1, m)
        assert_(isinstance(result, MyNDArray))
        assert_array_equal(result, expected)

    def test_subclass(self):
        class MinimalSubclass(np.ndarray):
            data = 1

        def minimal_function(array):
            return array.data

        a = np.zeros((6, 3)).view(MinimalSubclass)

        assert_array_equal(
            apply_along_axis(minimal_function, 0, a), np.array([1, 1, 1])
        )

    def test_scalar_array(self, cls=np.ndarray):
        a = np.ones((6, 3)).view(cls)
        res = apply_along_axis(np.sum, 0, a)
        assert_(isinstance(res, cls))
        assert_array_equal(res, np.array([6, 6, 6]).view(cls))

    def test_0d_array(self, cls=np.ndarray):
        def sum_to_0d(x):
            """ Sum x, returning a 0d array of the same class """
            assert_equal(x.ndim, 1)
            return np.squeeze(np.sum(x, keepdims=True))
        a = np.ones((6, 3)).view(cls)
        res = apply_along_axis(sum_to_0d, 0, a)
        assert_(isinstance(res, cls))
        assert_array_equal(res, np.array([6, 6, 6]).view(cls))

        res = apply_along_axis(sum_to_0d, 1, a)
        assert_(isinstance(res, cls))
        assert_array_equal(res, np.array([3, 3, 3, 3, 3, 3]).view(cls))

    def test_axis_insertion(self, cls=np.ndarray):
        def f1to2(x):
            """produces an asymmetric non-square matrix from x"""
            assert_equal(x.ndim, 1)
            return (x[::-1] * x[1:, None]).view(cls)

        a2d = np.arange(6 * 3).reshape((6, 3))

        # 2d insertion along first axis
        actual = apply_along_axis(f1to2, 0, a2d)
        expected = np.stack([
            f1to2(a2d[:, i]) for i in range(a2d.shape[1])
        ], axis=-1).view(cls)
        assert_equal(type(actual), type(expected))
        assert_equal(actual, expected)

        # 2d insertion along last axis
        actual = apply_along_axis(f1to2, 1, a2d)
        expected = np.stack([
            f1to2(a2d[i, :]) for i in range(a2d.shape[0])
        ], axis=0).view(cls)
        assert_equal(type(actual), type(expected))
        assert_equal(actual, expected)

        # 3d insertion along middle axis
        a3d = np.arange(6 * 5 * 3).reshape((6, 5, 3))

        actual = apply_along_axis(f1to2, 1, a3d)
        expected = np.stack([
            np.stack([
                f1to2(a3d[i, :, j]) for i in range(a3d.shape[0])
            ], axis=0)
            for j in range(a3d.shape[2])
        ], axis=-1).view(cls)
        assert_equal(type(actual), type(expected))
        assert_equal(actual, expected)

    def test_subclass_preservation(self):
        class MinimalSubclass(np.ndarray):
            pass
        self.test_scalar_array(MinimalSubclass)
        self.test_0d_array(MinimalSubclass)
        self.test_axis_insertion(MinimalSubclass)

    def test_axis_insertion_ma(self):
        def f1to2(x):
            """produces an asymmetric non-square matrix from x"""
            assert_equal(x.ndim, 1)
            res = x[::-1] * x[1:, None]
            return np.ma.masked_where(res % 5 == 0, res)
        a = np.arange(6 * 3).reshape((6, 3))
        res = apply_along_axis(f1to2, 0, a)
        assert_(isinstance(res, np.ma.masked_array))
        assert_equal(res.ndim, 3)
        assert_array_equal(res[:, :, 0].mask, f1to2(a[:, 0]).mask)
        assert_array_equal(res[:, :, 1].mask, f1to2(a[:, 1]).mask)
        assert_array_equal(res[:, :, 2].mask, f1to2(a[:, 2]).mask)

    def test_tuple_func1d(self):
        def sample_1d(x):
            return x[1], x[0]
        res = np.apply_along_axis(sample_1d, 1, np.array([[1, 2], [3, 4]]))
        assert_array_equal(res, np.array([[2, 1], [4, 3]]))

    def test_empty(self):
        # can't apply_along_axis when there's no chance to call the function
        def never_call(x):
            assert_(False)  # should never be reached

        a = np.empty((0, 0))
        assert_raises(ValueError, np.apply_along_axis, never_call, 0, a)
        assert_raises(ValueError, np.apply_along_axis, never_call, 1, a)

        # but it's sometimes ok with some non-zero dimensions
        def empty_to_1(x):
            assert_(len(x) == 0)
            return 1

        a = np.empty((10, 0))
        actual = np.apply_along_axis(empty_to_1, 1, a)
        assert_equal(actual, np.ones(10))
        assert_raises(ValueError, np.apply_along_axis, empty_to_1, 0, a)

    def test_with_iterable_object(self):
        # from issue 5248
        d = np.array([
            [{1, 11}, {2, 22}, {3, 33}],
            [{4, 44}, {5, 55}, {6, 66}]
        ])
        actual = np.apply_along_axis(lambda a: set.union(*a), 0, d)
        expected = np.array([{1, 11, 4, 44}, {2, 22, 5, 55}, {3, 33, 6, 66}])

        assert_equal(actual, expected)

        # issue 8642 - assert_equal doesn't detect this!
        for i in np.ndindex(actual.shape):
            assert_equal(type(actual[i]), type(expected[i]))


class TestApplyOverAxes:
    def test_simple(self):
        a = np.arange(24).reshape(2, 3, 4)
        aoa_a = apply_over_axes(np.sum, a, [0, 2])
        assert_array_equal(aoa_a, np.array([[[60], [92], [124]]]))


class TestExpandDims:
    def test_functionality(self):
        s = (2, 3, 4, 5)
        a = np.empty(s)
        for axis in range(-5, 4):
            b = expand_dims(a, axis)
            assert_(b.shape[axis] == 1)
            assert_(np.squeeze(b).shape == s)

    def test_axis_tuple(self):
        a = np.empty((3, 3, 3))
        assert np.expand_dims(a, axis=(0, 1, 2)).shape == (1, 1, 1, 3, 3, 3)
        assert np.expand_dims(a, axis=(0, -1, -2)).shape == (1, 3, 3, 3, 1, 1)
        assert np.expand_dims(a, axis=(0, 3, 5)).shape == (1, 3, 3, 1, 3, 1)
        assert np.expand_dims(a, axis=(0, -3, -5)).shape == (1, 1, 3, 1, 3, 3)

    def test_axis_out_of_range(self):
        s = (2, 3, 4, 5)
        a = np.empty(s)
        assert_raises(AxisError, expand_dims, a, -6)
        assert_raises(AxisError, expand_dims, a, 5)

        a = np.empty((3, 3, 3))
        assert_raises(AxisError, expand_dims, a, (0, -6))
        assert_raises(AxisError, expand_dims, a, (0, 5))

    def test_repeated_axis(self):
        a = np.empty((3, 3, 3))
        assert_raises(ValueError, expand_dims, a, axis=(1, 1))

    def test_subclasses(self):
        a = np.arange(10).reshape((2, 5))
        a = np.ma.array(a, mask=a % 3 == 0)

        expanded = np.expand_dims(a, axis=1)
        assert_(isinstance(expanded, np.ma.MaskedArray))
        assert_equal(expanded.shape, (2, 1, 5))
        assert_equal(expanded.mask.shape, (2, 1, 5))


class TestArraySplit:
    def test_integer_0_split(self):
        a = np.arange(10)
        assert_raises(ValueError, array_split, a, 0)

    def test_integer_split(self):
        a = np.arange(10)
        res = array_split(a, 1)
        desired = [np.arange(10)]
        compare_results(res, desired)

        res = array_split(a, 2)
        desired = [np.arange(5), np.arange(5, 10)]
        compare_results(res, desired)

        res = array_split(a, 3)
        desired = [np.arange(4), np.arange(4, 7), np.arange(7, 10)]
        compare_results(res, desired)

        res = array_split(a, 4)
        desired = [np.arange(3), np.arange(3, 6), np.arange(6, 8),
                   np.arange(8, 10)]
        compare_results(res, desired)

        res = array_split(a, 5)
        desired = [np.arange(2), np.arange(2, 4), np.arange(4, 6),
                   np.arange(6, 8), np.arange(8, 10)]
        compare_results(res, desired)

        res = array_split(a, 6)
        desired = [np.arange(2), np.arange(2, 4), np.arange(4, 6),
                   np.arange(6, 8), np.arange(8, 9), np.arange(9, 10)]
        compare_results(res, desired)

        res = array_split(a, 7)
        desired = [np.arange(2), np.arange(2, 4), np.arange(4, 6),
                   np.arange(6, 7), np.arange(7, 8), np.arange(8, 9),
                   np.arange(9, 10)]
        compare_results(res, desired)

        res = array_split(a, 8)
        desired = [np.arange(2), np.arange(2, 4), np.arange(4, 5),
                   np.arange(5, 6), np.arange(6, 7), np.arange(7, 8),
                   np.arange(8, 9), np.arange(9, 10)]
        compare_results(res, desired)

        res = array_split(a, 9)
        desired = [np.arange(2), np.arange(2, 3), np.arange(3, 4),
                   np.arange(4, 5), np.arange(5, 6), np.arange(6, 7),
                   np.arange(7, 8), np.arange(8, 9), np.arange(9, 10)]
        compare_results(res, desired)

        res = array_split(a, 10)
        desired = [np.arange(1), np.arange(1, 2), np.arange(2, 3),
                   np.arange(3, 4), np.arange(4, 5), np.arange(5, 6),
                   np.arange(6, 7), np.arange(7, 8), np.arange(8, 9),
                   np.arange(9, 10)]
        compare_results(res, desired)

        res = array_split(a, 11)
        desired = [np.arange(1), np.arange(1, 2), np.arange(2, 3),
                   np.arange(3, 4), np.arange(4, 5), np.arange(5, 6),
                   np.arange(6, 7), np.arange(7, 8), np.arange(8, 9),
                   np.arange(9, 10), np.array([])]
        compare_results(res, desired)

    def test_integer_split_2D_rows(self):
        a = np.array([np.arange(10), np.arange(10)])
        res = array_split(a, 3, axis=0)
        tgt = [np.array([np.arange(10)]), np.array([np.arange(10)]),
                   np.zeros((0, 10))]
        compare_results(res, tgt)
        assert_(a.dtype.type is res[-1].dtype.type)

        # Same thing for manual splits:
        res = array_split(a, [0, 1], axis=0)
        tgt = [np.zeros((0, 10)), np.array([np.arange(10)]),
               np.array([np.arange(10)])]
        compare_results(res, tgt)
        assert_(a.dtype.type is res[-1].dtype.type)

    def test_integer_split_2D_cols(self):
        a = np.array([np.arange(10), np.arange(10)])
        res = array_split(a, 3, axis=-1)
        desired = [np.array([np.arange(4), np.arange(4)]),
                   np.array([np.arange(4, 7), np.arange(4, 7)]),
                   np.array([np.arange(7, 10), np.arange(7, 10)])]
        compare_results(res, desired)

    def test_integer_split_2D_default(self):
        """ This will fail if we change default axis
        """
        a = np.array([np.arange(10), np.arange(10)])
        res = array_split(a, 3)
        tgt = [np.array([np.arange(10)]), np.array([np.arange(10)]),
                   np.zeros((0, 10))]
        compare_results(res, tgt)
        assert_(a.dtype.type is res[-1].dtype.type)
        # perhaps should check higher dimensions

    @pytest.mark.skipif(not IS_64BIT, reason="Needs 64bit platform")
    def test_integer_split_2D_rows_greater_max_int32(self):
        a = np.broadcast_to([0], (1 << 32, 2))
        res = array_split(a, 4)
        chunk = np.broadcast_to([0], (1 << 30, 2))
        tgt = [chunk] * 4
        for i in range(len(tgt)):
            assert_equal(res[i].shape, tgt[i].shape)

    def test_index_split_simple(self):
        a = np.arange(10)
        indices = [1, 5, 7]
        res = array_split(a, indices, axis=-1)
        desired = [np.arange(0, 1), np.arange(1, 5), np.arange(5, 7),
                   np.arange(7, 10)]
        compare_results(res, desired)

    def test_index_split_low_bound(self):
        a = np.arange(10)
        indices = [0, 5, 7]
        res = array_split(a, indices, axis=-1)
        desired = [np.array([]), np.arange(0, 5), np.arange(5, 7),
                   np.arange(7, 10)]
        compare_results(res, desired)

    def test_index_split_high_bound(self):
        a = np.arange(10)
        indices = [0, 5, 7, 10, 12]
        res = array_split(a, indices, axis=-1)
        desired = [np.array([]), np.arange(0, 5), np.arange(5, 7),
                   np.arange(7, 10), np.array([]), np.array([])]
        compare_results(res, desired)


class TestSplit:
    # The split function is essentially the same as array_split,
    # except that it test if splitting will result in an
    # equal split.  Only test for this case.

    def test_equal_split(self):
        a = np.arange(10)
        res = split(a, 2)
        desired = [np.arange(5), np.arange(5, 10)]
        compare_results(res, desired)

    def test_unequal_split(self):
        a = np.arange(10)
        assert_raises(ValueError, split, a, 3)


class TestColumnStack:
    def test_non_iterable(self):
        assert_raises(TypeError, column_stack, 1)

    def test_1D_arrays(self):
        # example from docstring
        a = np.array((1, 2, 3))
        b = np.array((2, 3, 4))
        expected = np.array([[1, 2],
                             [2, 3],
                             [3, 4]])
        actual = np.column_stack((a, b))
        assert_equal(actual, expected)

    def test_2D_arrays(self):
        # same as hstack 2D docstring example
        a = np.array([[1], [2], [3]])
        b = np.array([[2], [3], [4]])
        expected = np.array([[1, 2],
                             [2, 3],
                             [3, 4]])
        actual = np.column_stack((a, b))
        assert_equal(actual, expected)

    def test_generator(self):
        with pytest.raises(TypeError, match="arrays to stack must be"):
            column_stack(np.arange(3) for _ in range(2))


class TestDstack:
    def test_non_iterable(self):
        assert_raises(TypeError, dstack, 1)

    def test_0D_array(self):
        a = np.array(1)
        b = np.array(2)
        res = dstack([a, b])
        desired = np.array([[[1, 2]]])
        assert_array_equal(res, desired)

    def test_1D_array(self):
        a = np.array([1])
        b = np.array([2])
        res = dstack([a, b])
        desired = np.array([[[1, 2]]])
        assert_array_equal(res, desired)

    def test_2D_array(self):
        a = np.array([[1], [2]])
        b = np.array([[1], [2]])
        res = dstack([a, b])
        desired = np.array([[[1, 1]], [[2, 2, ]]])
        assert_array_equal(res, desired)

    def test_2D_array2(self):
        a = np.array([1, 2])
        b = np.array([1, 2])
        res = dstack([a, b])
        desired = np.array([[[1, 1], [2, 2]]])
        assert_array_equal(res, desired)

    def test_generator(self):
        with pytest.raises(TypeError, match="arrays to stack must be"):
            dstack(np.arange(3) for _ in range(2))


# array_split has more comprehensive test of splitting.
# only do simple test on hsplit, vsplit, and dsplit
class TestHsplit:
    """Only testing for integer splits.

    """
    def test_non_iterable(self):
        assert_raises(ValueError, hsplit, 1, 1)

    def test_0D_array(self):
        a = np.array(1)
        try:
            hsplit(a, 2)
            assert_(0)
        except ValueError:
            pass

    def test_1D_array(self):
        a = np.array([1, 2, 3, 4])
        res = hsplit(a, 2)
        desired = [np.array([1, 2]), np.array([3, 4])]
        compare_results(res, desired)

    def test_2D_array(self):
        a = np.array([[1, 2, 3, 4],
                  [1, 2, 3, 4]])
        res = hsplit(a, 2)
        desired = [np.array([[1, 2], [1, 2]]), np.array([[3, 4], [3, 4]])]
        compare_results(res, desired)


class TestVsplit:
    """Only testing for integer splits.

    """
    def test_non_iterable(self):
        assert_raises(ValueError, vsplit, 1, 1)

    def test_0D_array(self):
        a = np.array(1)
        assert_raises(ValueError, vsplit, a, 2)

    def test_1D_array(self):
        a = np.array([1, 2, 3, 4])
        try:
            vsplit(a, 2)
            assert_(0)
        except ValueError:
            pass

    def test_2D_array(self):
        a = np.array([[1, 2, 3, 4],
                  [1, 2, 3, 4]])
        res = vsplit(a, 2)
        desired = [np.array([[1, 2, 3, 4]]), np.array([[1, 2, 3, 4]])]
        compare_results(res, desired)


class TestDsplit:
    # Only testing for integer splits.
    def test_non_iterable(self):
        assert_raises(ValueError, dsplit, 1, 1)

    def test_0D_array(self):
        a = np.array(1)
        assert_raises(ValueError, dsplit, a, 2)

    def test_1D_array(self):
        a = np.array([1, 2, 3, 4])
        assert_raises(ValueError, dsplit, a, 2)

    def test_2D_array(self):
        a = np.array([[1, 2, 3, 4],
                  [1, 2, 3, 4]])
        try:
            dsplit(a, 2)
            assert_(0)
        except ValueError:
            pass

    def test_3D_array(self):
        a = np.array([[[1, 2, 3, 4],
                   [1, 2, 3, 4]],
                  [[1, 2, 3, 4],
                   [1, 2, 3, 4]]])
        res = dsplit(a, 2)
        desired = [np.array([[[1, 2], [1, 2]], [[1, 2], [1, 2]]]),
                   np.array([[[3, 4], [3, 4]], [[3, 4], [3, 4]]])]
        compare_results(res, desired)


class TestSqueeze:
    def test_basic(self):
        from numpy.random import rand

        a = rand(20, 10, 10, 1, 1)
        b = rand(20, 1, 10, 1, 20)
        c = rand(1, 1, 20, 10)
        assert_array_equal(np.squeeze(a), np.reshape(a, (20, 10, 10)))
        assert_array_equal(np.squeeze(b), np.reshape(b, (20, 10, 20)))
        assert_array_equal(np.squeeze(c), np.reshape(c, (20, 10)))

        # Squeezing to 0-dim should still give an ndarray
        a = [[[1.5]]]
        res = np.squeeze(a)
        assert_equal(res, 1.5)
        assert_equal(res.ndim, 0)
        assert_equal(type(res), np.ndarray)


class TestKron:
    def test_basic(self):
        # Using 0-dimensional ndarray
        a = np.array(1)
        b = np.array([[1, 2], [3, 4]])
        k = np.array([[1, 2], [3, 4]])
        assert_array_equal(np.kron(a, b), k)
        a = np.array([[1, 2], [3, 4]])
        b = np.array(1)
        assert_array_equal(np.kron(a, b), k)

        # Using 1-dimensional ndarray
        a = np.array([3])
        b = np.array([[1, 2], [3, 4]])
        k = np.array([[3, 6], [9, 12]])
        assert_array_equal(np.kron(a, b), k)
        a = np.array([[1, 2], [3, 4]])
        b = np.array([3])
        assert_array_equal(np.kron(a, b), k)

        # Using 3-dimensional ndarray
        a = np.array([[[1]], [[2]]])
        b = np.array([[1, 2], [3, 4]])
        k = np.array([[[1, 2], [3, 4]], [[2, 4], [6, 8]]])
        assert_array_equal(np.kron(a, b), k)
        a = np.array([[1, 2], [3, 4]])
        b = np.array([[[1]], [[2]]])
        k = np.array([[[1, 2], [3, 4]], [[2, 4], [6, 8]]])
        assert_array_equal(np.kron(a, b), k)

    def test_return_type(self):
        class myarray(np.ndarray):
            __array_priority__ = 1.0

        a = np.ones([2, 2])
        ma = myarray(a.shape, a.dtype, a.data)
        assert_equal(type(kron(a, a)), np.ndarray)
        assert_equal(type(kron(ma, ma)), myarray)
        assert_equal(type(kron(a, ma)), myarray)
        assert_equal(type(kron(ma, a)), myarray)

    @pytest.mark.parametrize(
        "array_class", [np.asarray, np.asmatrix]
    )
    def test_kron_smoke(self, array_class):
        a = array_class(np.ones([3, 3]))
        b = array_class(np.ones([3, 3]))
        k = array_class(np.ones([9, 9]))

        assert_array_equal(np.kron(a, b), k)

    def test_kron_ma(self):
        x = np.ma.array([[1, 2], [3, 4]], mask=[[0, 1], [1, 0]])
        k = np.ma.array(np.diag([1, 4, 4, 16]),
                mask=~np.array(np.identity(4), dtype=bool))

        assert_array_equal(k, np.kron(x, x))

    @pytest.mark.parametrize(
        "shape_a,shape_b", [
            ((1, 1), (1, 1)),
            ((1, 2, 3), (4, 5, 6)),
            ((2, 2), (2, 2, 2)),
            ((1, 0), (1, 1)),
            ((2, 0, 2), (2, 2)),
            ((2, 0, 0, 2), (2, 0, 2)),
        ])
    def test_kron_shape(self, shape_a, shape_b):
        a = np.ones(shape_a)
        b = np.ones(shape_b)
        normalised_shape_a = (1,) * max(0, len(shape_b) - len(shape_a)) + shape_a
        normalised_shape_b = (1,) * max(0, len(shape_a) - len(shape_b)) + shape_b
        expected_shape = np.multiply(normalised_shape_a, normalised_shape_b)

        k = np.kron(a, b)
        assert np.array_equal(
                k.shape, expected_shape), "Unexpected shape from kron"


class TestTile:
    def test_basic(self):
        a = np.array([0, 1, 2])
        b = [[1, 2], [3, 4]]
        assert_equal(tile(a, 2), [0, 1, 2, 0, 1, 2])
        assert_equal(tile(a, (2, 2)), [[0, 1, 2, 0, 1, 2], [0, 1, 2, 0, 1, 2]])
        assert_equal(tile(a, (1, 2)), [[0, 1, 2, 0, 1, 2]])
        assert_equal(tile(b, 2), [[1, 2, 1, 2], [3, 4, 3, 4]])
        assert_equal(tile(b, (2, 1)), [[1, 2], [3, 4], [1, 2], [3, 4]])
        assert_equal(tile(b, (2, 2)), [[1, 2, 1, 2], [3, 4, 3, 4],
                                       [1, 2, 1, 2], [3, 4, 3, 4]])

    def test_tile_one_repetition_on_array_gh4679(self):
        a = np.arange(5)
        b = tile(a, 1)
        b += 2
        assert_equal(a, np.arange(5))

    def test_empty(self):
        a = np.array([[[]]])
        b = np.array([[], []])
        c = tile(b, 2).shape
        d = tile(a, (3, 2, 5)).shape
        assert_equal(c, (2, 0))
        assert_equal(d, (3, 2, 0))

    def test_kroncompare(self):
        from numpy.random import randint

        reps = [(2,), (1, 2), (2, 1), (2, 2), (2, 3, 2), (3, 2)]
        shape = [(3,), (2, 3), (3, 4, 3), (3, 2, 3), (4, 3, 2, 4), (2, 2)]
        for s in shape:
            b = randint(0, 10, size=s)
            for r in reps:
                a = np.ones(r, b.dtype)
                large = tile(b, r)
                klarge = kron(a, b)
                assert_equal(large, klarge)


class TestMayShareMemory:
    def test_basic(self):
        d = np.ones((50, 60))
        d2 = np.ones((30, 60, 6))
        assert_(np.may_share_memory(d, d))
        assert_(np.may_share_memory(d, d[::-1]))
        assert_(np.may_share_memory(d, d[::2]))
        assert_(np.may_share_memory(d, d[1:, ::-1]))

        assert_(not np.may_share_memory(d[::-1], d2))
        assert_(not np.may_share_memory(d[::2], d2))
        assert_(not np.may_share_memory(d[1:, ::-1], d2))
        assert_(np.may_share_memory(d2[1:, ::-1], d2))


# Utility
def compare_results(res, desired):
    """Compare lists of arrays."""
    for x, y in zip(res, desired, strict=False):
        assert_array_equal(x, y)

# === NexusCore/openenv\Lib\site-packages\openai\lib\_validators.py ===
# pyright: basic
from __future__ import annotations

import os
import sys
from typing import Any, TypeVar, Callable, Optional, NamedTuple
from typing_extensions import TypeAlias

from .._extras import pandas as pd


class Remediation(NamedTuple):
    name: str
    immediate_msg: Optional[str] = None
    necessary_msg: Optional[str] = None
    necessary_fn: Optional[Callable[[Any], Any]] = None
    optional_msg: Optional[str] = None
    optional_fn: Optional[Callable[[Any], Any]] = None
    error_msg: Optional[str] = None


OptionalDataFrameT = TypeVar("OptionalDataFrameT", bound="Optional[pd.DataFrame]")


def num_examples_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will only print out the number of examples and recommend to the user to increase the number of examples if less than 100.
    """
    MIN_EXAMPLES = 100
    optional_suggestion = (
        ""
        if len(df) >= MIN_EXAMPLES
        else ". In general, we recommend having at least a few hundred examples. We've found that performance tends to linearly increase for every doubling of the number of examples"
    )
    immediate_msg = f"\n- Your file contains {len(df)} prompt-completion pairs{optional_suggestion}"
    return Remediation(name="num_examples", immediate_msg=immediate_msg)


def necessary_column_validator(df: pd.DataFrame, necessary_column: str) -> Remediation:
    """
    This validator will ensure that the necessary column is present in the dataframe.
    """

    def lower_case_column(df: pd.DataFrame, column: Any) -> pd.DataFrame:
        cols = [c for c in df.columns if str(c).lower() == column]
        df.rename(columns={cols[0]: column.lower()}, inplace=True)
        return df

    immediate_msg = None
    necessary_fn = None
    necessary_msg = None
    error_msg = None

    if necessary_column not in df.columns:
        if necessary_column in [str(c).lower() for c in df.columns]:

            def lower_case_column_creator(df: pd.DataFrame) -> pd.DataFrame:
                return lower_case_column(df, necessary_column)

            necessary_fn = lower_case_column_creator
            immediate_msg = f"\n- The `{necessary_column}` column/key should be lowercase"
            necessary_msg = f"Lower case column name to `{necessary_column}`"
        else:
            error_msg = f"`{necessary_column}` column/key is missing. Please make sure you name your columns/keys appropriately, then retry"

    return Remediation(
        name="necessary_column",
        immediate_msg=immediate_msg,
        necessary_msg=necessary_msg,
        necessary_fn=necessary_fn,
        error_msg=error_msg,
    )


def additional_column_validator(df: pd.DataFrame, fields: list[str] = ["prompt", "completion"]) -> Remediation:
    """
    This validator will remove additional columns from the dataframe.
    """
    additional_columns = []
    necessary_msg = None
    immediate_msg = None
    necessary_fn = None  # type: ignore

    if len(df.columns) > 2:
        additional_columns = [c for c in df.columns if c not in fields]
        warn_message = ""
        for ac in additional_columns:
            dups = [c for c in additional_columns if ac in c]
            if len(dups) > 0:
                warn_message += f"\n  WARNING: Some of the additional columns/keys contain `{ac}` in their name. These will be ignored, and the column/key `{ac}` will be used instead. This could also result from a duplicate column/key in the provided file."
        immediate_msg = f"\n- The input file should contain exactly two columns/keys per row. Additional columns/keys present are: {additional_columns}{warn_message}"
        necessary_msg = f"Remove additional columns/keys: {additional_columns}"

        def necessary_fn(x: Any) -> Any:
            return x[fields]

    return Remediation(
        name="additional_column",
        immediate_msg=immediate_msg,
        necessary_msg=necessary_msg,
        necessary_fn=necessary_fn,
    )


def non_empty_field_validator(df: pd.DataFrame, field: str = "completion") -> Remediation:
    """
    This validator will ensure that no completion is empty.
    """
    necessary_msg = None
    necessary_fn = None  # type: ignore
    immediate_msg = None

    if df[field].apply(lambda x: x == "").any() or df[field].isnull().any():
        empty_rows = (df[field] == "") | (df[field].isnull())
        empty_indexes = df.reset_index().index[empty_rows].tolist()
        immediate_msg = f"\n- `{field}` column/key should not contain empty strings. These are rows: {empty_indexes}"

        def necessary_fn(x: Any) -> Any:
            return x[x[field] != ""].dropna(subset=[field])

        necessary_msg = f"Remove {len(empty_indexes)} rows with empty {field}s"

    return Remediation(
        name=f"empty_{field}",
        immediate_msg=immediate_msg,
        necessary_msg=necessary_msg,
        necessary_fn=necessary_fn,
    )


def duplicated_rows_validator(df: pd.DataFrame, fields: list[str] = ["prompt", "completion"]) -> Remediation:
    """
    This validator will suggest to the user to remove duplicate rows if they exist.
    """
    duplicated_rows = df.duplicated(subset=fields)
    duplicated_indexes = df.reset_index().index[duplicated_rows].tolist()
    immediate_msg = None
    optional_msg = None
    optional_fn = None  # type: ignore

    if len(duplicated_indexes) > 0:
        immediate_msg = f"\n- There are {len(duplicated_indexes)} duplicated {'-'.join(fields)} sets. These are rows: {duplicated_indexes}"
        optional_msg = f"Remove {len(duplicated_indexes)} duplicate rows"

        def optional_fn(x: Any) -> Any:
            return x.drop_duplicates(subset=fields)

    return Remediation(
        name="duplicated_rows",
        immediate_msg=immediate_msg,
        optional_msg=optional_msg,
        optional_fn=optional_fn,
    )


def long_examples_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will suggest to the user to remove examples that are too long.
    """
    immediate_msg = None
    optional_msg = None
    optional_fn = None  # type: ignore

    ft_type = infer_task_type(df)
    if ft_type != "open-ended generation":

        def get_long_indexes(d: pd.DataFrame) -> Any:
            long_examples = d.apply(lambda x: len(x.prompt) + len(x.completion) > 10000, axis=1)
            return d.reset_index().index[long_examples].tolist()

        long_indexes = get_long_indexes(df)

        if len(long_indexes) > 0:
            immediate_msg = f"\n- There are {len(long_indexes)} examples that are very long. These are rows: {long_indexes}\nFor conditional generation, and for classification the examples shouldn't be longer than 2048 tokens."
            optional_msg = f"Remove {len(long_indexes)} long examples"

            def optional_fn(x: Any) -> Any:
                long_indexes_to_drop = get_long_indexes(x)
                if long_indexes != long_indexes_to_drop:
                    sys.stdout.write(
                        f"The indices of the long examples has changed as a result of a previously applied recommendation.\nThe {len(long_indexes_to_drop)} long examples to be dropped are now at the following indices: {long_indexes_to_drop}\n"
                    )
                return x.drop(long_indexes_to_drop)

    return Remediation(
        name="long_examples",
        immediate_msg=immediate_msg,
        optional_msg=optional_msg,
        optional_fn=optional_fn,
    )


def common_prompt_suffix_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will suggest to add a common suffix to the prompt if one doesn't already exist in case of classification or conditional generation.
    """
    error_msg = None
    immediate_msg = None
    optional_msg = None
    optional_fn = None  # type: ignore

    # Find a suffix which is not contained within the prompt otherwise
    suggested_suffix = "\n\n### =>\n\n"
    suffix_options = [
        " ->",
        "\n\n###\n\n",
        "\n\n===\n\n",
        "\n\n---\n\n",
        "\n\n===>\n\n",
        "\n\n--->\n\n",
    ]
    for suffix_option in suffix_options:
        if suffix_option == " ->":
            if df.prompt.str.contains("\n").any():
                continue
        if df.prompt.str.contains(suffix_option, regex=False).any():
            continue
        suggested_suffix = suffix_option
        break
    display_suggested_suffix = suggested_suffix.replace("\n", "\\n")

    ft_type = infer_task_type(df)
    if ft_type == "open-ended generation":
        return Remediation(name="common_suffix")

    def add_suffix(x: Any, suffix: Any) -> Any:
        x["prompt"] += suffix
        return x

    common_suffix = get_common_xfix(df.prompt, xfix="suffix")
    if (df.prompt == common_suffix).all():
        error_msg = f"All prompts are identical: `{common_suffix}`\nConsider leaving the prompts blank if you want to do open-ended generation, otherwise ensure prompts are different"
        return Remediation(name="common_suffix", error_msg=error_msg)

    if common_suffix != "":
        common_suffix_new_line_handled = common_suffix.replace("\n", "\\n")
        immediate_msg = f"\n- All prompts end with suffix `{common_suffix_new_line_handled}`"
        if len(common_suffix) > 10:
            immediate_msg += f". This suffix seems very long. Consider replacing with a shorter suffix, such as `{display_suggested_suffix}`"
        if df.prompt.str[: -len(common_suffix)].str.contains(common_suffix, regex=False).any():
            immediate_msg += f"\n  WARNING: Some of your prompts contain the suffix `{common_suffix}` more than once. We strongly suggest that you review your prompts and add a unique suffix"

    else:
        immediate_msg = "\n- Your data does not contain a common separator at the end of your prompts. Having a separator string appended to the end of the prompt makes it clearer to the fine-tuned model where the completion should begin. See https://platform.openai.com/docs/guides/fine-tuning/preparing-your-dataset for more detail and examples. If you intend to do open-ended generation, then you should leave the prompts empty"

    if common_suffix == "":
        optional_msg = f"Add a suffix separator `{display_suggested_suffix}` to all prompts"

        def optional_fn(x: Any) -> Any:
            return add_suffix(x, suggested_suffix)

    return Remediation(
        name="common_completion_suffix",
        immediate_msg=immediate_msg,
        optional_msg=optional_msg,
        optional_fn=optional_fn,
        error_msg=error_msg,
    )


def common_prompt_prefix_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will suggest to remove a common prefix from the prompt if a long one exist.
    """
    MAX_PREFIX_LEN = 12

    immediate_msg = None
    optional_msg = None
    optional_fn = None  # type: ignore

    common_prefix = get_common_xfix(df.prompt, xfix="prefix")
    if common_prefix == "":
        return Remediation(name="common_prefix")

    def remove_common_prefix(x: Any, prefix: Any) -> Any:
        x["prompt"] = x["prompt"].str[len(prefix) :]
        return x

    if (df.prompt == common_prefix).all():
        # already handled by common_suffix_validator
        return Remediation(name="common_prefix")

    if common_prefix != "":
        immediate_msg = f"\n- All prompts start with prefix `{common_prefix}`"
        if MAX_PREFIX_LEN < len(common_prefix):
            immediate_msg += ". Fine-tuning doesn't require the instruction specifying the task, or a few-shot example scenario. Most of the time you should only add the input data into the prompt, and the desired output into the completion"
            optional_msg = f"Remove prefix `{common_prefix}` from all prompts"

            def optional_fn(x: Any) -> Any:
                return remove_common_prefix(x, common_prefix)

    return Remediation(
        name="common_prompt_prefix",
        immediate_msg=immediate_msg,
        optional_msg=optional_msg,
        optional_fn=optional_fn,
    )


def common_completion_prefix_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will suggest to remove a common prefix from the completion if a long one exist.
    """
    MAX_PREFIX_LEN = 5

    common_prefix = get_common_xfix(df.completion, xfix="prefix")
    ws_prefix = len(common_prefix) > 0 and common_prefix[0] == " "
    if len(common_prefix) < MAX_PREFIX_LEN:
        return Remediation(name="common_prefix")

    def remove_common_prefix(x: Any, prefix: Any, ws_prefix: Any) -> Any:
        x["completion"] = x["completion"].str[len(prefix) :]
        if ws_prefix:
            # keep the single whitespace as prefix
            x["completion"] = f" {x['completion']}"
        return x

    if (df.completion == common_prefix).all():
        # already handled by common_suffix_validator
        return Remediation(name="common_prefix")

    immediate_msg = f"\n- All completions start with prefix `{common_prefix}`. Most of the time you should only add the output data into the completion, without any prefix"
    optional_msg = f"Remove prefix `{common_prefix}` from all completions"

    def optional_fn(x: Any) -> Any:
        return remove_common_prefix(x, common_prefix, ws_prefix)

    return Remediation(
        name="common_completion_prefix",
        immediate_msg=immediate_msg,
        optional_msg=optional_msg,
        optional_fn=optional_fn,
    )


def common_completion_suffix_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will suggest to add a common suffix to the completion if one doesn't already exist in case of classification or conditional generation.
    """
    error_msg = None
    immediate_msg = None
    optional_msg = None
    optional_fn = None  # type: ignore

    ft_type = infer_task_type(df)
    if ft_type == "open-ended generation" or ft_type == "classification":
        return Remediation(name="common_suffix")

    common_suffix = get_common_xfix(df.completion, xfix="suffix")
    if (df.completion == common_suffix).all():
        error_msg = f"All completions are identical: `{common_suffix}`\nEnsure completions are different, otherwise the model will just repeat `{common_suffix}`"
        return Remediation(name="common_suffix", error_msg=error_msg)

    # Find a suffix which is not contained within the completion otherwise
    suggested_suffix = " [END]"
    suffix_options = [
        "\n",
        ".",
        " END",
        "***",
        "+++",
        "&&&",
        "$$$",
        "@@@",
        "%%%",
    ]
    for suffix_option in suffix_options:
        if df.completion.str.contains(suffix_option, regex=False).any():
            continue
        suggested_suffix = suffix_option
        break
    display_suggested_suffix = suggested_suffix.replace("\n", "\\n")

    def add_suffix(x: Any, suffix: Any) -> Any:
        x["completion"] += suffix
        return x

    if common_suffix != "":
        common_suffix_new_line_handled = common_suffix.replace("\n", "\\n")
        immediate_msg = f"\n- All completions end with suffix `{common_suffix_new_line_handled}`"
        if len(common_suffix) > 10:
            immediate_msg += f". This suffix seems very long. Consider replacing with a shorter suffix, such as `{display_suggested_suffix}`"
        if df.completion.str[: -len(common_suffix)].str.contains(common_suffix, regex=False).any():
            immediate_msg += f"\n  WARNING: Some of your completions contain the suffix `{common_suffix}` more than once. We suggest that you review your completions and add a unique ending"

    else:
        immediate_msg = "\n- Your data does not contain a common ending at the end of your completions. Having a common ending string appended to the end of the completion makes it clearer to the fine-tuned model where the completion should end. See https://platform.openai.com/docs/guides/fine-tuning/preparing-your-dataset for more detail and examples."

    if common_suffix == "":
        optional_msg = f"Add a suffix ending `{display_suggested_suffix}` to all completions"

        def optional_fn(x: Any) -> Any:
            return add_suffix(x, suggested_suffix)

    return Remediation(
        name="common_completion_suffix",
        immediate_msg=immediate_msg,
        optional_msg=optional_msg,
        optional_fn=optional_fn,
        error_msg=error_msg,
    )


def completions_space_start_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will suggest to add a space at the start of the completion if it doesn't already exist. This helps with tokenization.
    """

    def add_space_start(x: Any) -> Any:
        x["completion"] = x["completion"].apply(lambda s: ("" if s.startswith(" ") else " ") + s)
        return x

    optional_msg = None
    optional_fn = None
    immediate_msg = None

    if df.completion.str[:1].nunique() != 1 or df.completion.values[0][0] != " ":
        immediate_msg = "\n- The completion should start with a whitespace character (` `). This tends to produce better results due to the tokenization we use. See https://platform.openai.com/docs/guides/fine-tuning/preparing-your-dataset for more details"
        optional_msg = "Add a whitespace character to the beginning of the completion"
        optional_fn = add_space_start
    return Remediation(
        name="completion_space_start",
        immediate_msg=immediate_msg,
        optional_msg=optional_msg,
        optional_fn=optional_fn,
    )


def lower_case_validator(df: pd.DataFrame, column: Any) -> Remediation | None:
    """
    This validator will suggest to lowercase the column values, if more than a third of letters are uppercase.
    """

    def lower_case(x: Any) -> Any:
        x[column] = x[column].str.lower()
        return x

    count_upper = df[column].apply(lambda x: sum(1 for c in x if c.isalpha() and c.isupper())).sum()
    count_lower = df[column].apply(lambda x: sum(1 for c in x if c.isalpha() and c.islower())).sum()

    if count_upper * 2 > count_lower:
        return Remediation(
            name="lower_case",
            immediate_msg=f"\n- More than a third of your `{column}` column/key is uppercase. Uppercase {column}s tends to perform worse than a mixture of case encountered in normal language. We recommend to lower case the data if that makes sense in your domain. See https://platform.openai.com/docs/guides/fine-tuning/preparing-your-dataset for more details",
            optional_msg=f"Lowercase all your data in column/key `{column}`",
            optional_fn=lower_case,
        )
    return None


def read_any_format(
    fname: str, fields: list[str] = ["prompt", "completion"]
) -> tuple[pd.DataFrame | None, Remediation]:
    """
    This function will read a file saved in .csv, .json, .txt, .xlsx or .tsv format using pandas.
     - for .xlsx it will read the first sheet
     - for .txt it will assume completions and split on newline
    """
    remediation = None
    necessary_msg = None
    immediate_msg = None
    error_msg = None
    df = None

    if os.path.isfile(fname):
        try:
            if fname.lower().endswith(".csv") or fname.lower().endswith(".tsv"):
                file_extension_str, separator = ("CSV", ",") if fname.lower().endswith(".csv") else ("TSV", "\t")
                immediate_msg = (
                    f"\n- Based on your file extension, your file is formatted as a {file_extension_str} file"
                )
                necessary_msg = f"Your format `{file_extension_str}` will be converted to `JSONL`"
                df = pd.read_csv(fname, sep=separator, dtype=str).fillna("")
            elif fname.lower().endswith(".xlsx"):
                immediate_msg = "\n- Based on your file extension, your file is formatted as an Excel file"
                necessary_msg = "Your format `XLSX` will be converted to `JSONL`"
                xls = pd.ExcelFile(fname)
                sheets = xls.sheet_names
                if len(sheets) > 1:
                    immediate_msg += "\n- Your Excel file contains more than one sheet. Please either save as csv or ensure all data is present in the first sheet. WARNING: Reading only the first sheet..."
                df = pd.read_excel(fname, dtype=str).fillna("")
            elif fname.lower().endswith(".txt"):
                immediate_msg = "\n- Based on your file extension, you provided a text file"
                necessary_msg = "Your format `TXT` will be converted to `JSONL`"
                with open(fname, "r") as f:
                    content = f.read()
                    df = pd.DataFrame(
                        [["", line] for line in content.split("\n")],
                        columns=fields,
                        dtype=str,
                    ).fillna("")
            elif fname.lower().endswith(".jsonl"):
                df = pd.read_json(fname, lines=True, dtype=str).fillna("")  # type: ignore
                if len(df) == 1:  # type: ignore
                    # this is NOT what we expect for a .jsonl file
                    immediate_msg = "\n- Your JSONL file appears to be in a JSON format. Your file will be converted to JSONL format"
                    necessary_msg = "Your format `JSON` will be converted to `JSONL`"
                    df = pd.read_json(fname, dtype=str).fillna("")  # type: ignore
                else:
                    pass  # this is what we expect for a .jsonl file
            elif fname.lower().endswith(".json"):
                try:
                    # to handle case where .json file is actually a .jsonl file
                    df = pd.read_json(fname, lines=True, dtype=str).fillna("")  # type: ignore
                    if len(df) == 1:  # type: ignore
                        # this code path corresponds to a .json file that has one line
                        df = pd.read_json(fname, dtype=str).fillna("")  # type: ignore
                    else:
                        # this is NOT what we expect for a .json file
                        immediate_msg = "\n- Your JSON file appears to be in a JSONL format. Your file will be converted to JSONL format"
                        necessary_msg = "Your format `JSON` will be converted to `JSONL`"
                except ValueError:
                    # this code path corresponds to a .json file that has multiple lines (i.e. it is indented)
                    df = pd.read_json(fname, dtype=str).fillna("")  # type: ignore
            else:
                error_msg = (
                    "Your file must have one of the following extensions: .CSV, .TSV, .XLSX, .TXT, .JSON or .JSONL"
                )
                if "." in fname:
                    error_msg += f" Your file `{fname}` ends with the extension `.{fname.split('.')[-1]}` which is not supported."
                else:
                    error_msg += f" Your file `{fname}` is missing a file extension."

        except (ValueError, TypeError):
            file_extension_str = fname.split(".")[-1].upper()
            error_msg = f"Your file `{fname}` does not appear to be in valid {file_extension_str} format. Please ensure your file is formatted as a valid {file_extension_str} file."

    else:
        error_msg = f"File {fname} does not exist."

    remediation = Remediation(
        name="read_any_format",
        necessary_msg=necessary_msg,
        immediate_msg=immediate_msg,
        error_msg=error_msg,
    )
    return df, remediation


def format_inferrer_validator(df: pd.DataFrame) -> Remediation:
    """
    This validator will infer the likely fine-tuning format of the data, and display it to the user if it is classification.
    It will also suggest to use ada and explain train/validation split benefits.
    """
    ft_type = infer_task_type(df)
    immediate_msg = None
    if ft_type == "classification":
        immediate_msg = f"\n- Based on your data it seems like you're trying to fine-tune a model for {ft_type}\n- For classification, we recommend you try one of the faster and cheaper models, such as `ada`\n- For classification, you can estimate the expected model performance by keeping a held out dataset, which is not used for training"
    return Remediation(name="num_examples", immediate_msg=immediate_msg)


def apply_necessary_remediation(df: OptionalDataFrameT, remediation: Remediation) -> OptionalDataFrameT:
    """
    This function will apply a necessary remediation to a dataframe, or print an error message if one exists.
    """
    if remediation.error_msg is not None:
        sys.stderr.write(f"\n\nERROR in {remediation.name} validator: {remediation.error_msg}\n\nAborting...")
        sys.exit(1)
    if remediation.immediate_msg is not None:
        sys.stdout.write(remediation.immediate_msg)
    if remediation.necessary_fn is not None:
        df = remediation.necessary_fn(df)
    return df


def accept_suggestion(input_text: str, auto_accept: bool) -> bool:
    sys.stdout.write(input_text)
    if auto_accept:
        sys.stdout.write("Y\n")
        return True
    return input().lower() != "n"


def apply_optional_remediation(
    df: pd.DataFrame, remediation: Remediation, auto_accept: bool
) -> tuple[pd.DataFrame, bool]:
    """
    This function will apply an optional remediation to a dataframe, based on the user input.
    """
    optional_applied = False
    input_text = f"- [Recommended] {remediation.optional_msg} [Y/n]: "
    if remediation.optional_msg is not None:
        if accept_suggestion(input_text, auto_accept):
            assert remediation.optional_fn is not None
            df = remediation.optional_fn(df)
            optional_applied = True
    if remediation.necessary_msg is not None:
        sys.stdout.write(f"- [Necessary] {remediation.necessary_msg}\n")
    return df, optional_applied


def estimate_fine_tuning_time(df: pd.DataFrame) -> None:
    """
    Estimate the time it'll take to fine-tune the dataset
    """
    ft_format = infer_task_type(df)
    expected_time = 1.0
    if ft_format == "classification":
        num_examples = len(df)
        expected_time = num_examples * 1.44
    else:
        size = df.memory_usage(index=True).sum()
        expected_time = size * 0.0515

    def format_time(time: float) -> str:
        if time < 60:
            return f"{round(time, 2)} seconds"
        elif time < 3600:
            return f"{round(time / 60, 2)} minutes"
        elif time < 86400:
            return f"{round(time / 3600, 2)} hours"
        else:
            return f"{round(time / 86400, 2)} days"

    time_string = format_time(expected_time + 140)
    sys.stdout.write(
        f"Once your model starts training, it'll approximately take {time_string} to train a `curie` model, and less for `ada` and `babbage`. Queue will approximately take half an hour per job ahead of you.\n"
    )


def get_outfnames(fname: str, split: bool) -> list[str]:
    suffixes = ["_train", "_valid"] if split else [""]
    i = 0
    while True:
        index_suffix = f" ({i})" if i > 0 else ""
        candidate_fnames = [f"{os.path.splitext(fname)[0]}_prepared{suffix}{index_suffix}.jsonl" for suffix in suffixes]
        if not any(os.path.isfile(f) for f in candidate_fnames):
            return candidate_fnames
        i += 1


def get_classification_hyperparams(df: pd.DataFrame) -> tuple[int, object]:
    n_classes = df.completion.nunique()
    pos_class = None
    if n_classes == 2:
        pos_class = df.completion.value_counts().index[0]
    return n_classes, pos_class


def write_out_file(df: pd.DataFrame, fname: str, any_remediations: bool, auto_accept: bool) -> None:
    """
    This function will write out a dataframe to a file, if the user would like to proceed, and also offer a fine-tuning command with the newly created file.
    For classification it will optionally ask the user if they would like to split the data into train/valid files, and modify the suggested command to include the valid set.
    """
    ft_format = infer_task_type(df)
    common_prompt_suffix = get_common_xfix(df.prompt, xfix="suffix")
    common_completion_suffix = get_common_xfix(df.completion, xfix="suffix")

    split = False
    input_text = "- [Recommended] Would you like to split into training and validation set? [Y/n]: "
    if ft_format == "classification":
        if accept_suggestion(input_text, auto_accept):
            split = True

    additional_params = ""
    common_prompt_suffix_new_line_handled = common_prompt_suffix.replace("\n", "\\n")
    common_completion_suffix_new_line_handled = common_completion_suffix.replace("\n", "\\n")
    optional_ending_string = (
        f' Make sure to include `stop=["{common_completion_suffix_new_line_handled}"]` so that the generated texts ends at the expected place.'
        if len(common_completion_suffix_new_line_handled) > 0
        else ""
    )

    input_text = "\n\nYour data will be written to a new JSONL file. Proceed [Y/n]: "

    if not any_remediations and not split:
        sys.stdout.write(
            f'\nYou can use your file for fine-tuning:\n> openai api fine_tunes.create -t "{fname}"{additional_params}\n\nAfter you’ve fine-tuned a model, remember that your prompt has to end with the indicator string `{common_prompt_suffix_new_line_handled}` for the model to start generating completions, rather than continuing with the prompt.{optional_ending_string}\n'
        )
        estimate_fine_tuning_time(df)

    elif accept_suggestion(input_text, auto_accept):
        fnames = get_outfnames(fname, split)
        if split:
            assert len(fnames) == 2 and "train" in fnames[0] and "valid" in fnames[1]
            MAX_VALID_EXAMPLES = 1000
            n_train = max(len(df) - MAX_VALID_EXAMPLES, int(len(df) * 0.8))
            df_train = df.sample(n=n_train, random_state=42)
            df_valid = df.drop(df_train.index)
            df_train[["prompt", "completion"]].to_json(  # type: ignore
                fnames[0], lines=True, orient="records", force_ascii=False, indent=None
            )
            df_valid[["prompt", "completion"]].to_json(
                fnames[1], lines=True, orient="records", force_ascii=False, indent=None
            )

            n_classes, pos_class = get_classification_hyperparams(df)
            additional_params += " --compute_classification_metrics"
            if n_classes == 2:
                additional_params += f' --classification_positive_class "{pos_class}"'
            else:
                additional_params += f" --classification_n_classes {n_classes}"
        else:
            assert len(fnames) == 1
            df[["prompt", "completion"]].to_json(
                fnames[0], lines=True, orient="records", force_ascii=False, indent=None
            )

        # Add -v VALID_FILE if we split the file into train / valid
        files_string = ("s" if split else "") + " to `" + ("` and `".join(fnames))
        valid_string = f' -v "{fnames[1]}"' if split else ""
        separator_reminder = (
            ""
            if len(common_prompt_suffix_new_line_handled) == 0
            else f"After you’ve fine-tuned a model, remember that your prompt has to end with the indicator string `{common_prompt_suffix_new_line_handled}` for the model to start generating completions, rather than continuing with the prompt."
        )
        sys.stdout.write(
            f'\nWrote modified file{files_string}`\nFeel free to take a look!\n\nNow use that file when fine-tuning:\n> openai api fine_tunes.create -t "{fnames[0]}"{valid_string}{additional_params}\n\n{separator_reminder}{optional_ending_string}\n'
        )
        estimate_fine_tuning_time(df)
    else:
        sys.stdout.write("Aborting... did not write the file\n")


def infer_task_type(df: pd.DataFrame) -> str:
    """
    Infer the likely fine-tuning task type from the data
    """
    CLASSIFICATION_THRESHOLD = 3  # min_average instances of each class
    if sum(df.prompt.str.len()) == 0:
        return "open-ended generation"

    if len(df.completion.unique()) < len(df) / CLASSIFICATION_THRESHOLD:
        return "classification"

    return "conditional generation"


def get_common_xfix(series: Any, xfix: str = "suffix") -> str:
    """
    Finds the longest common suffix or prefix of all the values in a series
    """
    common_xfix = ""
    while True:
        common_xfixes = (
            series.str[-(len(common_xfix) + 1) :] if xfix == "suffix" else series.str[: len(common_xfix) + 1]
        )  # first few or last few characters
        if common_xfixes.nunique() != 1:  # we found the character at which we don't have a unique xfix anymore
            break
        elif common_xfix == common_xfixes.values[0]:  # the entire first row is a prefix of every other row
            break
        else:  # the first or last few characters are still common across all rows - let's try to add one more
            common_xfix = common_xfixes.values[0]
    return common_xfix


Validator: TypeAlias = "Callable[[pd.DataFrame], Remediation | None]"


def get_validators() -> list[Validator]:
    return [
        num_examples_validator,
        lambda x: necessary_column_validator(x, "prompt"),
        lambda x: necessary_column_validator(x, "completion"),
        additional_column_validator,
        non_empty_field_validator,
        format_inferrer_validator,
        duplicated_rows_validator,
        long_examples_validator,
        lambda x: lower_case_validator(x, "prompt"),
        lambda x: lower_case_validator(x, "completion"),
        common_prompt_suffix_validator,
        common_prompt_prefix_validator,
        common_completion_prefix_validator,
        common_completion_suffix_validator,
        completions_space_start_validator,
    ]


def apply_validators(
    df: pd.DataFrame,
    fname: str,
    remediation: Remediation | None,
    validators: list[Validator],
    auto_accept: bool,
    write_out_file_func: Callable[..., Any],
) -> None:
    optional_remediations: list[Remediation] = []
    if remediation is not None:
        optional_remediations.append(remediation)
    for validator in validators:
        remediation = validator(df)
        if remediation is not None:
            optional_remediations.append(remediation)
            df = apply_necessary_remediation(df, remediation)

    any_optional_or_necessary_remediations = any(
        [
            remediation
            for remediation in optional_remediations
            if remediation.optional_msg is not None or remediation.necessary_msg is not None
        ]
    )
    any_necessary_applied = any(
        [remediation for remediation in optional_remediations if remediation.necessary_msg is not None]
    )
    any_optional_applied = False

    if any_optional_or_necessary_remediations:
        sys.stdout.write("\n\nBased on the analysis we will perform the following actions:\n")
        for remediation in optional_remediations:
            df, optional_applied = apply_optional_remediation(df, remediation, auto_accept)
            any_optional_applied = any_optional_applied or optional_applied
    else:
        sys.stdout.write("\n\nNo remediations found.\n")

    any_optional_or_necessary_applied = any_optional_applied or any_necessary_applied

    write_out_file_func(df, fname, any_optional_or_necessary_applied, auto_accept)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_utils_impl.py ===
import functools
import os
import platform
import sys
import textwrap
import types
import warnings

import numpy as np
from numpy._core import ndarray
from numpy._utils import set_module

__all__ = [
    'get_include', 'info', 'show_runtime'
]


@set_module('numpy')
def show_runtime():
    """
    Print information about various resources in the system
    including available intrinsic support and BLAS/LAPACK library
    in use

    .. versionadded:: 1.24.0

    See Also
    --------
    show_config : Show libraries in the system on which NumPy was built.

    Notes
    -----
    1. Information is derived with the help of `threadpoolctl <https://pypi.org/project/threadpoolctl/>`_
       library if available.
    2. SIMD related information is derived from ``__cpu_features__``,
       ``__cpu_baseline__`` and ``__cpu_dispatch__``

    """
    from pprint import pprint

    from numpy._core._multiarray_umath import (
        __cpu_baseline__,
        __cpu_dispatch__,
        __cpu_features__,
    )
    config_found = [{
        "numpy_version": np.__version__,
        "python": sys.version,
        "uname": platform.uname(),
        }]
    features_found, features_not_found = [], []
    for feature in __cpu_dispatch__:
        if __cpu_features__[feature]:
            features_found.append(feature)
        else:
            features_not_found.append(feature)
    config_found.append({
        "simd_extensions": {
            "baseline": __cpu_baseline__,
            "found": features_found,
            "not_found": features_not_found
        }
    })
    try:
        from threadpoolctl import threadpool_info
        config_found.extend(threadpool_info())
    except ImportError:
        print("WARNING: `threadpoolctl` not found in system!"
              " Install it by `pip install threadpoolctl`."
              " Once installed, try `np.show_runtime` again"
              " for more detailed build information")
    pprint(config_found)


@set_module('numpy')
def get_include():
    """
    Return the directory that contains the NumPy \\*.h header files.

    Extension modules that need to compile against NumPy may need to use this
    function to locate the appropriate include directory.

    Notes
    -----
    When using ``setuptools``, for example in ``setup.py``::

        import numpy as np
        ...
        Extension('extension_name', ...
                  include_dirs=[np.get_include()])
        ...

    Note that a CLI tool ``numpy-config`` was introduced in NumPy 2.0, using
    that is likely preferred for build systems other than ``setuptools``::

        $ numpy-config --cflags
        -I/path/to/site-packages/numpy/_core/include

        # Or rely on pkg-config:
        $ export PKG_CONFIG_PATH=$(numpy-config --pkgconfigdir)
        $ pkg-config --cflags
        -I/path/to/site-packages/numpy/_core/include

    Examples
    --------
    >>> np.get_include()
    '.../site-packages/numpy/core/include'  # may vary

    """
    import numpy
    if numpy.show_config is None:
        # running from numpy source directory
        d = os.path.join(os.path.dirname(numpy.__file__), '_core', 'include')
    else:
        # using installed numpy core headers
        import numpy._core as _core
        d = os.path.join(os.path.dirname(_core.__file__), 'include')
    return d


class _Deprecate:
    """
    Decorator class to deprecate old functions.

    Refer to `deprecate` for details.

    See Also
    --------
    deprecate

    """

    def __init__(self, old_name=None, new_name=None, message=None):
        self.old_name = old_name
        self.new_name = new_name
        self.message = message

    def __call__(self, func, *args, **kwargs):
        """
        Decorator call.  Refer to ``decorate``.

        """
        old_name = self.old_name
        new_name = self.new_name
        message = self.message

        if old_name is None:
            old_name = func.__name__
        if new_name is None:
            depdoc = f"`{old_name}` is deprecated!"
        else:
            depdoc = f"`{old_name}` is deprecated, use `{new_name}` instead!"

        if message is not None:
            depdoc += "\n" + message

        @functools.wraps(func)
        def newfunc(*args, **kwds):
            warnings.warn(depdoc, DeprecationWarning, stacklevel=2)
            return func(*args, **kwds)

        newfunc.__name__ = old_name
        doc = func.__doc__
        if doc is None:
            doc = depdoc
        else:
            lines = doc.expandtabs().split('\n')
            indent = _get_indent(lines[1:])
            if lines[0].lstrip():
                # Indent the original first line to let inspect.cleandoc()
                # dedent the docstring despite the deprecation notice.
                doc = indent * ' ' + doc
            else:
                # Remove the same leading blank lines as cleandoc() would.
                skip = len(lines[0]) + 1
                for line in lines[1:]:
                    if len(line) > indent:
                        break
                    skip += len(line) + 1
                doc = doc[skip:]
            depdoc = textwrap.indent(depdoc, ' ' * indent)
            doc = f'{depdoc}\n\n{doc}'
        newfunc.__doc__ = doc

        return newfunc


def _get_indent(lines):
    """
    Determines the leading whitespace that could be removed from all the lines.
    """
    indent = sys.maxsize
    for line in lines:
        content = len(line.lstrip())
        if content:
            indent = min(indent, len(line) - content)
    if indent == sys.maxsize:
        indent = 0
    return indent


def deprecate(*args, **kwargs):
    """
    Issues a DeprecationWarning, adds warning to `old_name`'s
    docstring, rebinds ``old_name.__name__`` and returns the new
    function object.

    This function may also be used as a decorator.

    .. deprecated:: 2.0
        Use `~warnings.warn` with :exc:`DeprecationWarning` instead.

    Parameters
    ----------
    func : function
        The function to be deprecated.
    old_name : str, optional
        The name of the function to be deprecated. Default is None, in
        which case the name of `func` is used.
    new_name : str, optional
        The new name for the function. Default is None, in which case the
        deprecation message is that `old_name` is deprecated. If given, the
        deprecation message is that `old_name` is deprecated and `new_name`
        should be used instead.
    message : str, optional
        Additional explanation of the deprecation.  Displayed in the
        docstring after the warning.

    Returns
    -------
    old_func : function
        The deprecated function.

    Examples
    --------
    Note that ``olduint`` returns a value after printing Deprecation
    Warning:

    >>> olduint = np.lib.utils.deprecate(np.uint)
    DeprecationWarning: `uint64` is deprecated! # may vary
    >>> olduint(6)
    6

    """
    # Deprecate may be run as a function or as a decorator
    # If run as a function, we initialise the decorator class
    # and execute its __call__ method.

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`deprecate` is deprecated, "
        "use `warn` with `DeprecationWarning` instead. "
        "(deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    if args:
        fn = args[0]
        args = args[1:]

        return _Deprecate(*args, **kwargs)(fn)
    else:
        return _Deprecate(*args, **kwargs)


def deprecate_with_doc(msg):
    """
    Deprecates a function and includes the deprecation in its docstring.

    .. deprecated:: 2.0
        Use `~warnings.warn` with :exc:`DeprecationWarning` instead.

    This function is used as a decorator. It returns an object that can be
    used to issue a DeprecationWarning, by passing the to-be decorated
    function as argument, this adds warning to the to-be decorated function's
    docstring and returns the new function object.

    See Also
    --------
    deprecate : Decorate a function such that it issues a
                :exc:`DeprecationWarning`

    Parameters
    ----------
    msg : str
        Additional explanation of the deprecation. Displayed in the
        docstring after the warning.

    Returns
    -------
    obj : object

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`deprecate` is deprecated, "
        "use `warn` with `DeprecationWarning` instead. "
        "(deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    return _Deprecate(message=msg)


#-----------------------------------------------------------------------------


# NOTE:  pydoc defines a help function which works similarly to this
#  except it uses a pager to take over the screen.

# combine name and arguments and split to multiple lines of width
# characters.  End lines on a comma and begin argument list indented with
# the rest of the arguments.
def _split_line(name, arguments, width):
    firstwidth = len(name)
    k = firstwidth
    newstr = name
    sepstr = ", "
    arglist = arguments.split(sepstr)
    for argument in arglist:
        if k == firstwidth:
            addstr = ""
        else:
            addstr = sepstr
        k = k + len(argument) + len(addstr)
        if k > width:
            k = firstwidth + 1 + len(argument)
            newstr = newstr + ",\n" + " " * (firstwidth + 2) + argument
        else:
            newstr = newstr + addstr + argument
    return newstr


_namedict = None
_dictlist = None

# Traverse all module directories underneath globals
# to see if something is defined
def _makenamedict(module='numpy'):
    module = __import__(module, globals(), locals(), [])
    thedict = {module.__name__: module.__dict__}
    dictlist = [module.__name__]
    totraverse = [module.__dict__]
    while True:
        if len(totraverse) == 0:
            break
        thisdict = totraverse.pop(0)
        for x in thisdict.keys():
            if isinstance(thisdict[x], types.ModuleType):
                modname = thisdict[x].__name__
                if modname not in dictlist:
                    moddict = thisdict[x].__dict__
                    dictlist.append(modname)
                    totraverse.append(moddict)
                    thedict[modname] = moddict
    return thedict, dictlist


def _info(obj, output=None):
    """Provide information about ndarray obj.

    Parameters
    ----------
    obj : ndarray
        Must be ndarray, not checked.
    output
        Where printed output goes.

    Notes
    -----
    Copied over from the numarray module prior to its removal.
    Adapted somewhat as only numpy is an option now.

    Called by info.

    """
    extra = ""
    tic = ""
    bp = lambda x: x
    cls = getattr(obj, '__class__', type(obj))
    nm = getattr(cls, '__name__', cls)
    strides = obj.strides
    endian = obj.dtype.byteorder

    if output is None:
        output = sys.stdout

    print("class: ", nm, file=output)
    print("shape: ", obj.shape, file=output)
    print("strides: ", strides, file=output)
    print("itemsize: ", obj.itemsize, file=output)
    print("aligned: ", bp(obj.flags.aligned), file=output)
    print("contiguous: ", bp(obj.flags.contiguous), file=output)
    print("fortran: ", obj.flags.fortran, file=output)
    print(
        f"data pointer: {hex(obj.ctypes._as_parameter_.value)}{extra}",
        file=output
        )
    print("byteorder: ", end=' ', file=output)
    if endian in ['|', '=']:
        print(f"{tic}{sys.byteorder}{tic}", file=output)
        byteswap = False
    elif endian == '>':
        print(f"{tic}big{tic}", file=output)
        byteswap = sys.byteorder != "big"
    else:
        print(f"{tic}little{tic}", file=output)
        byteswap = sys.byteorder != "little"
    print("byteswap: ", bp(byteswap), file=output)
    print(f"type: {obj.dtype}", file=output)


@set_module('numpy')
def info(object=None, maxwidth=76, output=None, toplevel='numpy'):
    """
    Get help information for an array, function, class, or module.

    Parameters
    ----------
    object : object or str, optional
        Input object or name to get information about. If `object` is
        an `ndarray` instance, information about the array is printed.
        If `object` is a numpy object, its docstring is given. If it is
        a string, available modules are searched for matching objects.
        If None, information about `info` itself is returned.
    maxwidth : int, optional
        Printing width.
    output : file like object, optional
        File like object that the output is written to, default is
        ``None``, in which case ``sys.stdout`` will be used.
        The object has to be opened in 'w' or 'a' mode.
    toplevel : str, optional
        Start search at this level.

    Notes
    -----
    When used interactively with an object, ``np.info(obj)`` is equivalent
    to ``help(obj)`` on the Python prompt or ``obj?`` on the IPython
    prompt.

    Examples
    --------
    >>> np.info(np.polyval) # doctest: +SKIP
       polyval(p, x)
         Evaluate the polynomial p at x.
         ...

    When using a string for `object` it is possible to get multiple results.

    >>> np.info('fft') # doctest: +SKIP
         *** Found in numpy ***
    Core FFT routines
    ...
         *** Found in numpy.fft ***
     fft(a, n=None, axis=-1)
    ...
         *** Repeat reference found in numpy.fft.fftpack ***
         *** Total of 3 references found. ***

    When the argument is an array, information about the array is printed.

    >>> a = np.array([[1 + 2j, 3, -4], [-5j, 6, 0]], dtype=np.complex64)
    >>> np.info(a)
    class:  ndarray
    shape:  (2, 3)
    strides:  (24, 8)
    itemsize:  8
    aligned:  True
    contiguous:  True
    fortran:  False
    data pointer: 0x562b6e0d2860  # may vary
    byteorder:  little
    byteswap:  False
    type: complex64

    """
    global _namedict, _dictlist
    # Local import to speed up numpy's import time.
    import inspect
    import pydoc

    if (hasattr(object, '_ppimport_importer') or
           hasattr(object, '_ppimport_module')):
        object = object._ppimport_module
    elif hasattr(object, '_ppimport_attr'):
        object = object._ppimport_attr

    if output is None:
        output = sys.stdout

    if object is None:
        info(info)
    elif isinstance(object, ndarray):
        _info(object, output=output)
    elif isinstance(object, str):
        if _namedict is None:
            _namedict, _dictlist = _makenamedict(toplevel)
        numfound = 0
        objlist = []
        for namestr in _dictlist:
            try:
                obj = _namedict[namestr][object]
                if id(obj) in objlist:
                    print(f"\n     *** Repeat reference found in {namestr} *** ",
                          file=output
                          )
                else:
                    objlist.append(id(obj))
                    print(f"     *** Found in {namestr} ***", file=output)
                    info(obj)
                    print("-" * maxwidth, file=output)
                numfound += 1
            except KeyError:
                pass
        if numfound == 0:
            print(f"Help for {object} not found.", file=output)
        else:
            print("\n     "
                  "*** Total of %d references found. ***" % numfound,
                  file=output
                  )

    elif inspect.isfunction(object) or inspect.ismethod(object):
        name = object.__name__
        try:
            arguments = str(inspect.signature(object))
        except Exception:
            arguments = "()"

        if len(name + arguments) > maxwidth:
            argstr = _split_line(name, arguments, maxwidth)
        else:
            argstr = name + arguments

        print(" " + argstr + "\n", file=output)
        print(inspect.getdoc(object), file=output)

    elif inspect.isclass(object):
        name = object.__name__
        try:
            arguments = str(inspect.signature(object))
        except Exception:
            arguments = "()"

        if len(name + arguments) > maxwidth:
            argstr = _split_line(name, arguments, maxwidth)
        else:
            argstr = name + arguments

        print(" " + argstr + "\n", file=output)
        doc1 = inspect.getdoc(object)
        if doc1 is None:
            if hasattr(object, '__init__'):
                print(inspect.getdoc(object.__init__), file=output)
        else:
            print(inspect.getdoc(object), file=output)

        methods = pydoc.allmethods(object)

        public_methods = [meth for meth in methods if meth[0] != '_']
        if public_methods:
            print("\n\nMethods:\n", file=output)
            for meth in public_methods:
                thisobj = getattr(object, meth, None)
                if thisobj is not None:
                    methstr, other = pydoc.splitdoc(
                            inspect.getdoc(thisobj) or "None"
                            )
                print(f"  {meth}  --  {methstr}", file=output)

    elif hasattr(object, '__doc__'):
        print(inspect.getdoc(object), file=output)


def safe_eval(source):
    """
    Protected string evaluation.

    .. deprecated:: 2.0
        Use `ast.literal_eval` instead.

    Evaluate a string containing a Python literal expression without
    allowing the execution of arbitrary non-literal code.

    .. warning::

        This function is identical to :py:meth:`ast.literal_eval` and
        has the same security implications.  It may not always be safe
        to evaluate large input strings.

    Parameters
    ----------
    source : str
        The string to evaluate.

    Returns
    -------
    obj : object
       The result of evaluating `source`.

    Raises
    ------
    SyntaxError
        If the code has invalid Python syntax, or if it contains
        non-literal code.

    Examples
    --------
    >>> np.safe_eval('1')
    1
    >>> np.safe_eval('[1, 2, 3]')
    [1, 2, 3]
    >>> np.safe_eval('{"foo": ("bar", 10.0)}')
    {'foo': ('bar', 10.0)}

    >>> np.safe_eval('import os')
    Traceback (most recent call last):
      ...
    SyntaxError: invalid syntax

    >>> np.safe_eval('open("/home/user/.ssh/id_dsa").read()')
    Traceback (most recent call last):
      ...
    ValueError: malformed node or string: <_ast.Call object at 0x...>

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`safe_eval` is deprecated. Use `ast.literal_eval` instead. "
        "Be aware of security implications, such as memory exhaustion "
        "based attacks (deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    # Local import to speed up numpy's import time.
    import ast
    return ast.literal_eval(source)


def _median_nancheck(data, result, axis):
    """
    Utility function to check median result from data for NaN values at the end
    and return NaN in that case. Input result can also be a MaskedArray.

    Parameters
    ----------
    data : array
        Sorted input data to median function
    result : Array or MaskedArray
        Result of median function.
    axis : int
        Axis along which the median was computed.

    Returns
    -------
    result : scalar or ndarray
        Median or NaN in axes which contained NaN in the input.  If the input
        was an array, NaN will be inserted in-place.  If a scalar, either the
        input itself or a scalar NaN.
    """
    if data.size == 0:
        return result
    potential_nans = data.take(-1, axis=axis)
    n = np.isnan(potential_nans)
    # masked NaN values are ok, although for masked the copyto may fail for
    # unmasked ones (this was always broken) when the result is a scalar.
    if np.ma.isMaskedArray(n):
        n = n.filled(False)

    if not n.any():
        return result

    # Without given output, it is possible that the current result is a
    # numpy scalar, which is not writeable.  If so, just return nan.
    if isinstance(result, np.generic):
        return potential_nans

    # Otherwise copy NaNs (if there are any)
    np.copyto(result, potential_nans, where=n)
    return result

def _opt_info():
    """
    Returns a string containing the CPU features supported
    by the current build.

    The format of the string can be explained as follows:
        - Dispatched features supported by the running machine end with `*`.
        - Dispatched features not supported by the running machine
          end with `?`.
        - Remaining features represent the baseline.

    Returns:
        str: A formatted string indicating the supported CPU features.
    """
    from numpy._core._multiarray_umath import (
        __cpu_baseline__,
        __cpu_dispatch__,
        __cpu_features__,
    )

    if len(__cpu_baseline__) == 0 and len(__cpu_dispatch__) == 0:
        return ''

    enabled_features = ' '.join(__cpu_baseline__)
    for feature in __cpu_dispatch__:
        if __cpu_features__[feature]:
            enabled_features += f" {feature}*"
        else:
            enabled_features += f" {feature}?"

    return enabled_features

def drop_metadata(dtype, /):
    """
    Returns the dtype unchanged if it contained no metadata or a copy of the
    dtype if it (or any of its structure dtypes) contained metadata.

    This utility is used by `np.save` and `np.savez` to drop metadata before
    saving.

    .. note::

        Due to its limitation this function may move to a more appropriate
        home or change in the future and is considered semi-public API only.

    .. warning::

        This function does not preserve more strange things like record dtypes
        and user dtypes may simply return the wrong thing.  If you need to be
        sure about the latter, check the result with:
        ``np.can_cast(new_dtype, dtype, casting="no")``.

    """
    if dtype.fields is not None:
        found_metadata = dtype.metadata is not None

        names = []
        formats = []
        offsets = []
        titles = []
        for name, field in dtype.fields.items():
            field_dt = drop_metadata(field[0])
            if field_dt is not field[0]:
                found_metadata = True

            names.append(name)
            formats.append(field_dt)
            offsets.append(field[1])
            titles.append(None if len(field) < 3 else field[2])

        if not found_metadata:
            return dtype

        structure = {
            'names': names, 'formats': formats, 'offsets': offsets, 'titles': titles,
            'itemsize': dtype.itemsize}

        # NOTE: Could pass (dtype.type, structure) to preserve record dtypes...
        return np.dtype(structure, align=dtype.isalignedstruct)
    elif dtype.subdtype is not None:
        # subarray dtype
        subdtype, shape = dtype.subdtype
        new_subdtype = drop_metadata(subdtype)
        if dtype.metadata is None and new_subdtype is subdtype:
            return dtype

        return np.dtype((new_subdtype, shape))
    else:
        # Normal unstructured dtype
        if dtype.metadata is None:
            return dtype
        # Note that `dt.str` doesn't round-trip e.g. for user-dtypes.
        return np.dtype(dtype.str)

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\chat\_completions.py ===
from __future__ import annotations

import inspect
from types import TracebackType
from typing import TYPE_CHECKING, Any, Generic, Callable, Iterable, Awaitable, AsyncIterator, cast
from typing_extensions import Self, Iterator, assert_never

from jiter import from_json

from ._types import ParsedChoiceSnapshot, ParsedChatCompletionSnapshot, ParsedChatCompletionMessageSnapshot
from ._events import (
    ChunkEvent,
    ContentDoneEvent,
    RefusalDoneEvent,
    ContentDeltaEvent,
    RefusalDeltaEvent,
    LogprobsContentDoneEvent,
    LogprobsRefusalDoneEvent,
    ChatCompletionStreamEvent,
    LogprobsContentDeltaEvent,
    LogprobsRefusalDeltaEvent,
    FunctionToolCallArgumentsDoneEvent,
    FunctionToolCallArgumentsDeltaEvent,
)
from .._deltas import accumulate_delta
from ...._types import NOT_GIVEN, IncEx, NotGiven
from ...._utils import is_given, consume_sync_iterator, consume_async_iterator
from ...._compat import model_dump
from ...._models import build, construct_type
from ..._parsing import (
    ResponseFormatT,
    has_parseable_input,
    maybe_parse_content,
    parse_chat_completion,
    get_input_tool_by_name,
    solve_response_format_t,
    parse_function_tool_arguments,
)
from ...._streaming import Stream, AsyncStream
from ....types.chat import ChatCompletionChunk, ParsedChatCompletion, ChatCompletionToolParam
from ...._exceptions import LengthFinishReasonError, ContentFilterFinishReasonError
from ....types.chat.chat_completion import ChoiceLogprobs
from ....types.chat.chat_completion_chunk import Choice as ChoiceChunk
from ....types.chat.completion_create_params import ResponseFormat as ResponseFormatParam


class ChatCompletionStream(Generic[ResponseFormatT]):
    """Wrapper over the Chat Completions streaming API that adds helpful
    events such as `content.done`, supports automatically parsing
    responses & tool calls and accumulates a `ChatCompletion` object
    from each individual chunk.

    https://platform.openai.com/docs/api-reference/streaming
    """

    def __init__(
        self,
        *,
        raw_stream: Stream[ChatCompletionChunk],
        response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
        input_tools: Iterable[ChatCompletionToolParam] | NotGiven,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ChatCompletionStreamState(response_format=response_format, input_tools=input_tools)

    def __next__(self) -> ChatCompletionStreamEvent[ResponseFormatT]:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[ChatCompletionStreamEvent[ResponseFormatT]]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self._response.close()

    def get_final_completion(self) -> ParsedChatCompletion[ResponseFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedChatCompletion` object.

        If you passed a class type to `.stream()`, the `completion.choices[0].message.parsed`
        property will be the content deserialised into that class, if there was any content returned
        by the API.
        """
        self.until_done()
        return self._state.get_final_completion()

    def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        consume_sync_iterator(self)
        return self

    @property
    def current_completion_snapshot(self) -> ParsedChatCompletionSnapshot:
        return self._state.current_completion_snapshot

    def __stream__(self) -> Iterator[ChatCompletionStreamEvent[ResponseFormatT]]:
        for sse_event in self._raw_stream:
            if not _is_valid_chat_completion_chunk_weak(sse_event):
                continue
            events_to_fire = self._state.handle_chunk(sse_event)
            for event in events_to_fire:
                yield event


class ChatCompletionStreamManager(Generic[ResponseFormatT]):
    """Context manager over a `ChatCompletionStream` that is returned by `.stream()`.

    This context manager ensures the response cannot be leaked if you don't read
    the stream to completion.

    Usage:
    ```py
    with client.beta.chat.completions.stream(...) as stream:
        for event in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[ChatCompletionChunk]],
        *,
        response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
        input_tools: Iterable[ChatCompletionToolParam] | NotGiven,
    ) -> None:
        self.__stream: ChatCompletionStream[ResponseFormatT] | None = None
        self.__api_request = api_request
        self.__response_format = response_format
        self.__input_tools = input_tools

    def __enter__(self) -> ChatCompletionStream[ResponseFormatT]:
        raw_stream = self.__api_request()

        self.__stream = ChatCompletionStream(
            raw_stream=raw_stream,
            response_format=self.__response_format,
            input_tools=self.__input_tools,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncChatCompletionStream(Generic[ResponseFormatT]):
    """Wrapper over the Chat Completions streaming API that adds helpful
    events such as `content.done`, supports automatically parsing
    responses & tool calls and accumulates a `ChatCompletion` object
    from each individual chunk.

    https://platform.openai.com/docs/api-reference/streaming
    """

    def __init__(
        self,
        *,
        raw_stream: AsyncStream[ChatCompletionChunk],
        response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
        input_tools: Iterable[ChatCompletionToolParam] | NotGiven,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ChatCompletionStreamState(response_format=response_format, input_tools=input_tools)

    async def __anext__(self) -> ChatCompletionStreamEvent[ResponseFormatT]:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[ChatCompletionStreamEvent[ResponseFormatT]]:
        async for item in self._iterator:
            yield item

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self._response.aclose()

    async def get_final_completion(self) -> ParsedChatCompletion[ResponseFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedChatCompletion` object.

        If you passed a class type to `.stream()`, the `completion.choices[0].message.parsed`
        property will be the content deserialised into that class, if there was any content returned
        by the API.
        """
        await self.until_done()
        return self._state.get_final_completion()

    async def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        await consume_async_iterator(self)
        return self

    @property
    def current_completion_snapshot(self) -> ParsedChatCompletionSnapshot:
        return self._state.current_completion_snapshot

    async def __stream__(self) -> AsyncIterator[ChatCompletionStreamEvent[ResponseFormatT]]:
        async for sse_event in self._raw_stream:
            if not _is_valid_chat_completion_chunk_weak(sse_event):
                continue
            events_to_fire = self._state.handle_chunk(sse_event)
            for event in events_to_fire:
                yield event


class AsyncChatCompletionStreamManager(Generic[ResponseFormatT]):
    """Context manager over a `AsyncChatCompletionStream` that is returned by `.stream()`.

    This context manager ensures the response cannot be leaked if you don't read
    the stream to completion.

    Usage:
    ```py
    async with client.beta.chat.completions.stream(...) as stream:
        for event in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[ChatCompletionChunk]],
        *,
        response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
        input_tools: Iterable[ChatCompletionToolParam] | NotGiven,
    ) -> None:
        self.__stream: AsyncChatCompletionStream[ResponseFormatT] | None = None
        self.__api_request = api_request
        self.__response_format = response_format
        self.__input_tools = input_tools

    async def __aenter__(self) -> AsyncChatCompletionStream[ResponseFormatT]:
        raw_stream = await self.__api_request

        self.__stream = AsyncChatCompletionStream(
            raw_stream=raw_stream,
            response_format=self.__response_format,
            input_tools=self.__input_tools,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


class ChatCompletionStreamState(Generic[ResponseFormatT]):
    """Helper class for manually accumulating `ChatCompletionChunk`s into a final `ChatCompletion` object.

    This is useful in cases where you can't always use the `.stream()` method, e.g.

    ```py
    from openai.lib.streaming.chat import ChatCompletionStreamState

    state = ChatCompletionStreamState()

    stream = client.chat.completions.create(..., stream=True)
    for chunk in response:
        state.handle_chunk(chunk)

        # can also access the accumulated `ChatCompletion` mid-stream
        state.current_completion_snapshot

    print(state.get_final_completion())
    ```
    """

    def __init__(
        self,
        *,
        input_tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven = NOT_GIVEN,
    ) -> None:
        self.__current_completion_snapshot: ParsedChatCompletionSnapshot | None = None
        self.__choice_event_states: list[ChoiceEventState] = []

        self._input_tools = [tool for tool in input_tools] if is_given(input_tools) else []
        self._response_format = response_format
        self._rich_response_format: type | NotGiven = response_format if inspect.isclass(response_format) else NOT_GIVEN

    def get_final_completion(self) -> ParsedChatCompletion[ResponseFormatT]:
        """Parse the final completion object.

        Note this does not provide any guarantees that the stream has actually finished, you must
        only call this method when the stream is finished.
        """
        return parse_chat_completion(
            chat_completion=self.current_completion_snapshot,
            response_format=self._rich_response_format,
            input_tools=self._input_tools,
        )

    @property
    def current_completion_snapshot(self) -> ParsedChatCompletionSnapshot:
        assert self.__current_completion_snapshot is not None
        return self.__current_completion_snapshot

    def handle_chunk(self, chunk: ChatCompletionChunk) -> Iterable[ChatCompletionStreamEvent[ResponseFormatT]]:
        """Accumulate a new chunk into the snapshot and returns an iterable of events to yield."""
        self.__current_completion_snapshot = self._accumulate_chunk(chunk)

        return self._build_events(
            chunk=chunk,
            completion_snapshot=self.__current_completion_snapshot,
        )

    def _get_choice_state(self, choice: ChoiceChunk) -> ChoiceEventState:
        try:
            return self.__choice_event_states[choice.index]
        except IndexError:
            choice_state = ChoiceEventState(input_tools=self._input_tools)
            self.__choice_event_states.append(choice_state)
            return choice_state

    def _accumulate_chunk(self, chunk: ChatCompletionChunk) -> ParsedChatCompletionSnapshot:
        completion_snapshot = self.__current_completion_snapshot

        if completion_snapshot is None:
            return _convert_initial_chunk_into_snapshot(chunk)

        for choice in chunk.choices:
            try:
                choice_snapshot = completion_snapshot.choices[choice.index]
                previous_tool_calls = choice_snapshot.message.tool_calls or []

                choice_snapshot.message = cast(
                    ParsedChatCompletionMessageSnapshot,
                    construct_type(
                        type_=ParsedChatCompletionMessageSnapshot,
                        value=accumulate_delta(
                            cast(
                                "dict[object, object]",
                                model_dump(
                                    choice_snapshot.message,
                                    # we don't want to serialise / deserialise our custom properties
                                    # as they won't appear in the delta and we don't want to have to
                                    # continuosly reparse the content
                                    exclude=cast(
                                        # cast required as mypy isn't smart enough to infer `True` here to `Literal[True]`
                                        IncEx,
                                        {
                                            "parsed": True,
                                            "tool_calls": {
                                                idx: {"function": {"parsed_arguments": True}}
                                                for idx, _ in enumerate(choice_snapshot.message.tool_calls or [])
                                            },
                                        },
                                    ),
                                ),
                            ),
                            cast("dict[object, object]", choice.delta.to_dict()),
                        ),
                    ),
                )

                # ensure tools that have already been parsed are added back into the newly
                # constructed message snapshot
                for tool_index, prev_tool in enumerate(previous_tool_calls):
                    new_tool = (choice_snapshot.message.tool_calls or [])[tool_index]

                    if prev_tool.type == "function":
                        assert new_tool.type == "function"
                        new_tool.function.parsed_arguments = prev_tool.function.parsed_arguments
                    elif TYPE_CHECKING:  # type: ignore[unreachable]
                        assert_never(prev_tool)
            except IndexError:
                choice_snapshot = cast(
                    ParsedChoiceSnapshot,
                    construct_type(
                        type_=ParsedChoiceSnapshot,
                        value={
                            **choice.model_dump(exclude_unset=True, exclude={"delta"}),
                            "message": choice.delta.to_dict(),
                        },
                    ),
                )
                completion_snapshot.choices.append(choice_snapshot)

            if choice.finish_reason:
                choice_snapshot.finish_reason = choice.finish_reason

                if has_parseable_input(response_format=self._response_format, input_tools=self._input_tools):
                    if choice.finish_reason == "length":
                        # at the time of writing, `.usage` will always be `None` but
                        # we include it here in case that is changed in the future
                        raise LengthFinishReasonError(completion=completion_snapshot)

                    if choice.finish_reason == "content_filter":
                        raise ContentFilterFinishReasonError()

            if (
                choice_snapshot.message.content
                and not choice_snapshot.message.refusal
                and is_given(self._rich_response_format)
                # partial parsing fails on white-space
                and choice_snapshot.message.content.lstrip()
            ):
                choice_snapshot.message.parsed = from_json(
                    bytes(choice_snapshot.message.content, "utf-8"),
                    partial_mode=True,
                )

            for tool_call_chunk in choice.delta.tool_calls or []:
                tool_call_snapshot = (choice_snapshot.message.tool_calls or [])[tool_call_chunk.index]

                if tool_call_snapshot.type == "function":
                    input_tool = get_input_tool_by_name(
                        input_tools=self._input_tools, name=tool_call_snapshot.function.name
                    )

                    if (
                        input_tool
                        and input_tool.get("function", {}).get("strict")
                        and tool_call_snapshot.function.arguments
                    ):
                        tool_call_snapshot.function.parsed_arguments = from_json(
                            bytes(tool_call_snapshot.function.arguments, "utf-8"),
                            partial_mode=True,
                        )
                elif TYPE_CHECKING:  # type: ignore[unreachable]
                    assert_never(tool_call_snapshot)

            if choice.logprobs is not None:
                if choice_snapshot.logprobs is None:
                    choice_snapshot.logprobs = build(
                        ChoiceLogprobs,
                        content=choice.logprobs.content,
                        refusal=choice.logprobs.refusal,
                    )
                else:
                    if choice.logprobs.content:
                        if choice_snapshot.logprobs.content is None:
                            choice_snapshot.logprobs.content = []

                        choice_snapshot.logprobs.content.extend(choice.logprobs.content)

                    if choice.logprobs.refusal:
                        if choice_snapshot.logprobs.refusal is None:
                            choice_snapshot.logprobs.refusal = []

                        choice_snapshot.logprobs.refusal.extend(choice.logprobs.refusal)

        completion_snapshot.usage = chunk.usage
        completion_snapshot.system_fingerprint = chunk.system_fingerprint

        return completion_snapshot

    def _build_events(
        self,
        *,
        chunk: ChatCompletionChunk,
        completion_snapshot: ParsedChatCompletionSnapshot,
    ) -> list[ChatCompletionStreamEvent[ResponseFormatT]]:
        events_to_fire: list[ChatCompletionStreamEvent[ResponseFormatT]] = []

        events_to_fire.append(
            build(ChunkEvent, type="chunk", chunk=chunk, snapshot=completion_snapshot),
        )

        for choice in chunk.choices:
            choice_state = self._get_choice_state(choice)
            choice_snapshot = completion_snapshot.choices[choice.index]

            if choice.delta.content is not None and choice_snapshot.message.content is not None:
                events_to_fire.append(
                    build(
                        ContentDeltaEvent,
                        type="content.delta",
                        delta=choice.delta.content,
                        snapshot=choice_snapshot.message.content,
                        parsed=choice_snapshot.message.parsed,
                    )
                )

            if choice.delta.refusal is not None and choice_snapshot.message.refusal is not None:
                events_to_fire.append(
                    build(
                        RefusalDeltaEvent,
                        type="refusal.delta",
                        delta=choice.delta.refusal,
                        snapshot=choice_snapshot.message.refusal,
                    )
                )

            if choice.delta.tool_calls:
                tool_calls = choice_snapshot.message.tool_calls
                assert tool_calls is not None

                for tool_call_delta in choice.delta.tool_calls:
                    tool_call = tool_calls[tool_call_delta.index]

                    if tool_call.type == "function":
                        assert tool_call_delta.function is not None
                        events_to_fire.append(
                            build(
                                FunctionToolCallArgumentsDeltaEvent,
                                type="tool_calls.function.arguments.delta",
                                name=tool_call.function.name,
                                index=tool_call_delta.index,
                                arguments=tool_call.function.arguments,
                                parsed_arguments=tool_call.function.parsed_arguments,
                                arguments_delta=tool_call_delta.function.arguments or "",
                            )
                        )
                    elif TYPE_CHECKING:  # type: ignore[unreachable]
                        assert_never(tool_call)

            if choice.logprobs is not None and choice_snapshot.logprobs is not None:
                if choice.logprobs.content and choice_snapshot.logprobs.content:
                    events_to_fire.append(
                        build(
                            LogprobsContentDeltaEvent,
                            type="logprobs.content.delta",
                            content=choice.logprobs.content,
                            snapshot=choice_snapshot.logprobs.content,
                        ),
                    )

                if choice.logprobs.refusal and choice_snapshot.logprobs.refusal:
                    events_to_fire.append(
                        build(
                            LogprobsRefusalDeltaEvent,
                            type="logprobs.refusal.delta",
                            refusal=choice.logprobs.refusal,
                            snapshot=choice_snapshot.logprobs.refusal,
                        ),
                    )

            events_to_fire.extend(
                choice_state.get_done_events(
                    choice_chunk=choice,
                    choice_snapshot=choice_snapshot,
                    response_format=self._response_format,
                )
            )

        return events_to_fire


class ChoiceEventState:
    def __init__(self, *, input_tools: list[ChatCompletionToolParam]) -> None:
        self._input_tools = input_tools

        self._content_done = False
        self._refusal_done = False
        self._logprobs_content_done = False
        self._logprobs_refusal_done = False
        self._done_tool_calls: set[int] = set()
        self.__current_tool_call_index: int | None = None

    def get_done_events(
        self,
        *,
        choice_chunk: ChoiceChunk,
        choice_snapshot: ParsedChoiceSnapshot,
        response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
    ) -> list[ChatCompletionStreamEvent[ResponseFormatT]]:
        events_to_fire: list[ChatCompletionStreamEvent[ResponseFormatT]] = []

        if choice_snapshot.finish_reason:
            events_to_fire.extend(
                self._content_done_events(choice_snapshot=choice_snapshot, response_format=response_format)
            )

            if (
                self.__current_tool_call_index is not None
                and self.__current_tool_call_index not in self._done_tool_calls
            ):
                self._add_tool_done_event(
                    events_to_fire=events_to_fire,
                    choice_snapshot=choice_snapshot,
                    tool_index=self.__current_tool_call_index,
                )

        for tool_call in choice_chunk.delta.tool_calls or []:
            if self.__current_tool_call_index != tool_call.index:
                events_to_fire.extend(
                    self._content_done_events(choice_snapshot=choice_snapshot, response_format=response_format)
                )

                if self.__current_tool_call_index is not None:
                    self._add_tool_done_event(
                        events_to_fire=events_to_fire,
                        choice_snapshot=choice_snapshot,
                        tool_index=self.__current_tool_call_index,
                    )

            self.__current_tool_call_index = tool_call.index

        return events_to_fire

    def _content_done_events(
        self,
        *,
        choice_snapshot: ParsedChoiceSnapshot,
        response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
    ) -> list[ChatCompletionStreamEvent[ResponseFormatT]]:
        events_to_fire: list[ChatCompletionStreamEvent[ResponseFormatT]] = []

        if choice_snapshot.message.content and not self._content_done:
            self._content_done = True

            parsed = maybe_parse_content(
                response_format=response_format,
                message=choice_snapshot.message,
            )

            # update the parsed content to now use the richer `response_format`
            # as opposed to the raw JSON-parsed object as the content is now
            # complete and can be fully validated.
            choice_snapshot.message.parsed = parsed

            events_to_fire.append(
                build(
                    # we do this dance so that when the `ContentDoneEvent` instance
                    # is printed at runtime the class name will include the solved
                    # type variable, e.g. `ContentDoneEvent[MyModelType]`
                    cast(  # pyright: ignore[reportUnnecessaryCast]
                        "type[ContentDoneEvent[ResponseFormatT]]",
                        cast(Any, ContentDoneEvent)[solve_response_format_t(response_format)],
                    ),
                    type="content.done",
                    content=choice_snapshot.message.content,
                    parsed=parsed,
                ),
            )

        if choice_snapshot.message.refusal is not None and not self._refusal_done:
            self._refusal_done = True
            events_to_fire.append(
                build(RefusalDoneEvent, type="refusal.done", refusal=choice_snapshot.message.refusal),
            )

        if (
            choice_snapshot.logprobs is not None
            and choice_snapshot.logprobs.content is not None
            and not self._logprobs_content_done
        ):
            self._logprobs_content_done = True
            events_to_fire.append(
                build(LogprobsContentDoneEvent, type="logprobs.content.done", content=choice_snapshot.logprobs.content),
            )

        if (
            choice_snapshot.logprobs is not None
            and choice_snapshot.logprobs.refusal is not None
            and not self._logprobs_refusal_done
        ):
            self._logprobs_refusal_done = True
            events_to_fire.append(
                build(LogprobsRefusalDoneEvent, type="logprobs.refusal.done", refusal=choice_snapshot.logprobs.refusal),
            )

        return events_to_fire

    def _add_tool_done_event(
        self,
        *,
        events_to_fire: list[ChatCompletionStreamEvent[ResponseFormatT]],
        choice_snapshot: ParsedChoiceSnapshot,
        tool_index: int,
    ) -> None:
        if tool_index in self._done_tool_calls:
            return

        self._done_tool_calls.add(tool_index)

        assert choice_snapshot.message.tool_calls is not None
        tool_call_snapshot = choice_snapshot.message.tool_calls[tool_index]

        if tool_call_snapshot.type == "function":
            parsed_arguments = parse_function_tool_arguments(
                input_tools=self._input_tools, function=tool_call_snapshot.function
            )

            # update the parsed content to potentially use a richer type
            # as opposed to the raw JSON-parsed object as the content is now
            # complete and can be fully validated.
            tool_call_snapshot.function.parsed_arguments = parsed_arguments

            events_to_fire.append(
                build(
                    FunctionToolCallArgumentsDoneEvent,
                    type="tool_calls.function.arguments.done",
                    index=tool_index,
                    name=tool_call_snapshot.function.name,
                    arguments=tool_call_snapshot.function.arguments,
                    parsed_arguments=parsed_arguments,
                )
            )
        elif TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(tool_call_snapshot)


def _convert_initial_chunk_into_snapshot(chunk: ChatCompletionChunk) -> ParsedChatCompletionSnapshot:
    data = chunk.to_dict()
    choices = cast("list[object]", data["choices"])

    for choice in chunk.choices:
        choices[choice.index] = {
            **choice.model_dump(exclude_unset=True, exclude={"delta"}),
            "message": choice.delta.to_dict(),
        }

    return cast(
        ParsedChatCompletionSnapshot,
        construct_type(
            type_=ParsedChatCompletionSnapshot,
            value={
                "system_fingerprint": None,
                **data,
                "object": "chat.completion",
            },
        ),
    )


def _is_valid_chat_completion_chunk_weak(sse_event: ChatCompletionChunk) -> bool:
    # Although the _raw_stream is always supposed to contain only objects adhering to ChatCompletionChunk schema,
    # this is broken by the Azure OpenAI in case of Asynchronous Filter enabled.
    # An easy filter is to check for the "object" property:
    # - should be "chat.completion.chunk" for a ChatCompletionChunk;
    # - is an empty string for Asynchronous Filter events.
    return sse_event.object == "chat.completion.chunk"  # type: ignore # pylance reports this as a useless check

# === NexusCore/exported_projects\app_20250703_223016\app\routes\image_crawler_route.py ===
from flask import Blueprint, render_template, request
from app.utils.image_crawler import crawl_images

bp = Blueprint('image_crawler', __name__)

@bp.route('/image_crawler', methods=['GET', 'POST'])
def image_crawler():
    message = ''
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        use_bing = request.form.get('use_bing') == 'on'
        use_google = request.form.get('use_google') == 'on'
        engines = []
        if use_bing:
            engines.append('bing')
        if use_google:
            engines.append('google')
        if keyword and engines:
            save_dir = crawl_images(keyword, max_num=50, engines=engines)
            message = f"「{keyword}」の画像を {', '.join(engines)} で収集し、{save_dir} に保存しました。"
        elif not engines:
            message = "検索エンジンを1つ以上選択してください。"
    return render_template('image_crawler.html', message=message)

# === NexusCore/exported_projects\project_export_m73owrzi\app\routes\image_crawler_route.py ===
from flask import Blueprint, render_template, request
from app.utils.image_crawler import crawl_images

bp = Blueprint('image_crawler', __name__)

@bp.route('/image_crawler', methods=['GET', 'POST'])
def image_crawler():
    message = ''
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        use_bing = request.form.get('use_bing') == 'on'
        use_google = request.form.get('use_google') == 'on'
        engines = []
        if use_bing:
            engines.append('bing')
        if use_google:
            engines.append('google')
        if keyword and engines:
            save_dir = crawl_images(keyword, max_num=50, engines=engines)
            message = f"「{keyword}」の画像を {', '.join(engines)} で収集し、{save_dir} に保存しました。"
        elif not engines:
            message = "検索エンジンを1つ以上選択してください。"
    return render_template('image_crawler.html', message=message)

# === NexusCore/exported_projects\project_export_xb_l70t8\app\routes\image_crawler_route.py ===
from flask import Blueprint, render_template, request
from app.utils.image_crawler import crawl_images

bp = Blueprint('image_crawler', __name__)

@bp.route('/image_crawler', methods=['GET', 'POST'])
def image_crawler():
    message = ''
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        use_bing = request.form.get('use_bing') == 'on'
        use_google = request.form.get('use_google') == 'on'
        engines = []
        if use_bing:
            engines.append('bing')
        if use_google:
            engines.append('google')
        if keyword and engines:
            save_dir = crawl_images(keyword, max_num=50, engines=engines)
            message = f"「{keyword}」の画像を {', '.join(engines)} で収集し、{save_dir} に保存しました。"
        elif not engines:
            message = "検索エンジンを1つ以上選択してください。"
    return render_template('image_crawler.html', message=message)

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\routes\image_crawler_route.py ===
from flask import Blueprint, render_template, request
from app.utils.image_crawler import crawl_images

bp = Blueprint('image_crawler', __name__)

@bp.route('/image_crawler', methods=['GET', 'POST'])
def image_crawler():
    message = ''
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        use_bing = request.form.get('use_bing') == 'on'
        use_google = request.form.get('use_google') == 'on'
        engines = []
        if use_bing:
            engines.append('bing')
        if use_google:
            engines.append('google')
        if keyword and engines:
            save_dir = crawl_images(keyword, max_num=50, engines=engines)
            message = f"「{keyword}」の画像を {', '.join(engines)} で収集し、{save_dir} に保存しました。"
        elif not engines:
            message = "検索エンジンを1つ以上選択してください。"
    return render_template('image_crawler.html', message=message)

# === NexusCore/src\modules\chat_handler.py ===
# src/modules/chat_handler.py

from openai import OpenAI
from dotenv import load_dotenv
import os

# .envからAPIキーを読み込む
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# チャット履歴を元にGPT応答を取得
def handle_chat(message: str, history: list) -> tuple[str, list]:
    try:
        history.append({"role": "user", "content": message})
        response = client.chat.completions.create(
            model="gpt-4",
            messages=history
        )
        assistant_msg = response.choices[0].message.content
        history.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg, history
    except Exception as e:
        return f"❌ エラー: {e}", history

# === NexusCore/src\modules\history_viewer.py ===
# modules/history_viewer.py

import os
import json

def load_history(directory="patch_history"):
    entries = []
    for file in sorted(os.listdir(directory), reverse=True):
        if file.endswith(".json"):
            with open(os.path.join(directory, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                entries.append({
                    "time": data["timestamp"],
                    "result": "✅ Success" if "failed" not in data.get("test_log", "") else "❌ Failed",
                    "reason": data.get("reason", "")[:200] + "...",
                })
    return entries

def format_history_markdown(entries):
    md = "# 🧾 修正履歴一覧\n"
    for e in entries:
        md += f"### {e['time']} - {e['result']}\n- {e['reason']}\n\n"
    return md

# === NexusCore/src\sandbox_logs\repair_20250713_131833_fixed.py ===
元のコードには、Pythonの文法エラーがあります。Pythonは英語ベースのプログラミング言語であり、日本語のコメントや文字列以外の場所で日本語を使用するとエラーが発生します。そのため、日本語の部分を削除または英語のコメントに変更する必要があります。

また、関数addの中でaとbを引き算していますが、関数名から推測するに加算が意図されていると思われます。そのため、その部分も修正します。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージからは、pytest形式のユニットテストが期待されているようです。そのため、適切なテストケースも追加すると以下のようになります。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/src\sandbox_logs\repair_20250713_131843_original.py ===
元のコードには、Pythonの文法エラーがあります。Pythonは英語ベースのプログラミング言語であり、日本語のコメントや文字列以外の場所で日本語を使用するとエラーが発生します。そのため、日本語の部分を削除または英語のコメントに変更する必要があります。

また、関数addの中でaとbを引き算していますが、関数名から推測するに加算が意図されていると思われます。そのため、その部分も修正します。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージからは、pytest形式のユニットテストが期待されているようです。そのため、適切なテストケースも追加すると以下のようになります。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/openenv\Lib\site-packages\win32\lib\ntsecuritycon.py ===
# Hacked from winnt.h

DELETE = 65536
READ_CONTROL = 131072
WRITE_DAC = 262144
WRITE_OWNER = 524288
SYNCHRONIZE = 1048576
STANDARD_RIGHTS_REQUIRED = 983040
STANDARD_RIGHTS_READ = READ_CONTROL
STANDARD_RIGHTS_WRITE = READ_CONTROL
STANDARD_RIGHTS_EXECUTE = READ_CONTROL
STANDARD_RIGHTS_ALL = 2031616
SPECIFIC_RIGHTS_ALL = 65535
ACCESS_SYSTEM_SECURITY = 16777216
MAXIMUM_ALLOWED = 33554432
GENERIC_READ = -2147483648
GENERIC_WRITE = 1073741824
GENERIC_EXECUTE = 536870912
GENERIC_ALL = 268435456

# file security permissions
FILE_READ_DATA = 1
FILE_LIST_DIRECTORY = 1
FILE_WRITE_DATA = 2
FILE_ADD_FILE = 2
FILE_APPEND_DATA = 4
FILE_ADD_SUBDIRECTORY = 4
FILE_CREATE_PIPE_INSTANCE = 4
FILE_READ_EA = 8
FILE_WRITE_EA = 16
FILE_EXECUTE = 32
FILE_TRAVERSE = 32
FILE_DELETE_CHILD = 64
FILE_READ_ATTRIBUTES = 128
FILE_WRITE_ATTRIBUTES = 256
FILE_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 511
FILE_GENERIC_READ = (
    STANDARD_RIGHTS_READ
    | FILE_READ_DATA
    | FILE_READ_ATTRIBUTES
    | FILE_READ_EA
    | SYNCHRONIZE
)
FILE_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | FILE_WRITE_DATA
    | FILE_WRITE_ATTRIBUTES
    | FILE_WRITE_EA
    | FILE_APPEND_DATA
    | SYNCHRONIZE
)
FILE_GENERIC_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE | FILE_READ_ATTRIBUTES | FILE_EXECUTE | SYNCHRONIZE
)


SECURITY_NULL_SID_AUTHORITY = (0, 0, 0, 0, 0, 0)
SECURITY_WORLD_SID_AUTHORITY = (0, 0, 0, 0, 0, 1)
SECURITY_LOCAL_SID_AUTHORITY = (0, 0, 0, 0, 0, 2)
SECURITY_CREATOR_SID_AUTHORITY = (0, 0, 0, 0, 0, 3)
SECURITY_NON_UNIQUE_AUTHORITY = (0, 0, 0, 0, 0, 4)
SECURITY_RESOURCE_MANAGER_AUTHORITY = (0, 0, 0, 0, 0, 9)

SECURITY_NULL_RID = 0
SECURITY_WORLD_RID = 0
SECURITY_LOCAL_RID = 0x00000000

SECURITY_CREATOR_OWNER_RID = 0
SECURITY_CREATOR_GROUP_RID = 1

SECURITY_CREATOR_OWNER_SERVER_RID = 2
SECURITY_CREATOR_GROUP_SERVER_RID = 3
SECURITY_CREATOR_OWNER_RIGHTS_RID = 4

# NT well-known SIDs
SECURITY_NT_AUTHORITY = (0, 0, 0, 0, 0, 5)

SECURITY_DIALUP_RID = 1
SECURITY_NETWORK_RID = 2
SECURITY_BATCH_RID = 3
SECURITY_INTERACTIVE_RID = 4
SECURITY_SERVICE_RID = 6
SECURITY_ANONYMOUS_LOGON_RID = 7
SECURITY_PROXY_RID = 8
SECURITY_SERVER_LOGON_RID = 9

SECURITY_LOGON_IDS_RID = 5
SECURITY_LOGON_IDS_RID_COUNT = 3

SECURITY_LOCAL_SYSTEM_RID = 18

SECURITY_NT_NON_UNIQUE = 21

SECURITY_BUILTIN_DOMAIN_RID = 32

# well-known domain relative sub-authority values (RIDs)...
DOMAIN_USER_RID_ADMIN = 500
DOMAIN_USER_RID_GUEST = 501
DOMAIN_USER_RID_KRBTGT = 502
DOMAIN_USER_RID_MAX = 999

# well-known groups ...
DOMAIN_GROUP_RID_ADMINS = 512
DOMAIN_GROUP_RID_USERS = 513
DOMAIN_GROUP_RID_GUESTS = 514
DOMAIN_GROUP_RID_COMPUTERS = 515
DOMAIN_GROUP_RID_CONTROLLERS = 516
DOMAIN_GROUP_RID_CERT_ADMINS = 517
DOMAIN_GROUP_RID_SCHEMA_ADMINS = 518
DOMAIN_GROUP_RID_ENTERPRISE_ADMINS = 519
DOMAIN_GROUP_RID_POLICY_ADMINS = 520
DOMAIN_GROUP_RID_READONLY_CONTROLLERS = 521

# well-known aliases ...
DOMAIN_ALIAS_RID_ADMINS = 544
DOMAIN_ALIAS_RID_USERS = 545
DOMAIN_ALIAS_RID_GUESTS = 546
DOMAIN_ALIAS_RID_POWER_USERS = 547
DOMAIN_ALIAS_RID_ACCOUNT_OPS = 548
DOMAIN_ALIAS_RID_SYSTEM_OPS = 549
DOMAIN_ALIAS_RID_PRINT_OPS = 550
DOMAIN_ALIAS_RID_BACKUP_OPS = 551
DOMAIN_ALIAS_RID_REPLICATOR = 552
DOMAIN_ALIAS_RID_RAS_SERVERS = 553
DOMAIN_ALIAS_RID_PREW2KCOMPACCESS = 554
DOMAIN_ALIAS_RID_REMOTE_DESKTOP_USERS = 555
DOMAIN_ALIAS_RID_NETWORK_CONFIGURATION_OPS = 556
DOMAIN_ALIAS_RID_INCOMING_FOREST_TRUST_BUILDERS = 557
DOMAIN_ALIAS_RID_MONITORING_USERS = 558
DOMAIN_ALIAS_RID_LOGGING_USERS = 559
DOMAIN_ALIAS_RID_AUTHORIZATIONACCESS = 560
DOMAIN_ALIAS_RID_TS_LICENSE_SERVERS = 561
DOMAIN_ALIAS_RID_DCOM_USERS = 562
DOMAIN_ALIAS_RID_IUSERS = 568
DOMAIN_ALIAS_RID_CRYPTO_OPERATORS = 569
DOMAIN_ALIAS_RID_CACHEABLE_PRINCIPALS_GROUP = 571
DOMAIN_ALIAS_RID_NON_CACHEABLE_PRINCIPALS_GROUP = 572
DOMAIN_ALIAS_RID_EVENT_LOG_READERS_GROUP = 573

SECURITY_MANDATORY_LABEL_AUTHORITY = (0, 0, 0, 0, 0, 16)
SECURITY_MANDATORY_UNTRUSTED_RID = 0x00000000
SECURITY_MANDATORY_LOW_RID = 0x00001000
SECURITY_MANDATORY_MEDIUM_RID = 0x00002000
SECURITY_MANDATORY_HIGH_RID = 0x00003000
SECURITY_MANDATORY_SYSTEM_RID = 0x00004000
SECURITY_MANDATORY_PROTECTED_PROCESS_RID = 0x00005000
SECURITY_MANDATORY_MAXIMUM_USER_RID = SECURITY_MANDATORY_SYSTEM_RID

SYSTEM_LUID = (999, 0)
ANONYMOUS_LOGON_LUID = (998, 0)
LOCALSERVICE_LUID = (997, 0)
NETWORKSERVICE_LUID = (996, 0)
IUSER_LUID = (995, 0)

# Group attributes

SE_GROUP_MANDATORY = 1
SE_GROUP_ENABLED_BY_DEFAULT = 2
SE_GROUP_ENABLED = 4
SE_GROUP_OWNER = 8
SE_GROUP_USE_FOR_DENY_ONLY = 16
SE_GROUP_INTEGRITY = 32
SE_GROUP_INTEGRITY_ENABLED = 64
SE_GROUP_RESOURCE = 536870912
SE_GROUP_LOGON_ID = -1073741824


# User attributes
# (None yet defined.)

# ACE types
ACCESS_MIN_MS_ACE_TYPE = 0
ACCESS_ALLOWED_ACE_TYPE = 0
ACCESS_DENIED_ACE_TYPE = 1
SYSTEM_AUDIT_ACE_TYPE = 2
SYSTEM_ALARM_ACE_TYPE = 3
ACCESS_MAX_MS_V2_ACE_TYPE = 3
ACCESS_ALLOWED_COMPOUND_ACE_TYPE = 4
ACCESS_MAX_MS_V3_ACE_TYPE = 4
ACCESS_MIN_MS_OBJECT_ACE_TYPE = 5
ACCESS_ALLOWED_OBJECT_ACE_TYPE = 5
ACCESS_DENIED_OBJECT_ACE_TYPE = 6
SYSTEM_AUDIT_OBJECT_ACE_TYPE = 7
SYSTEM_ALARM_OBJECT_ACE_TYPE = 8
ACCESS_MAX_MS_OBJECT_ACE_TYPE = 8
ACCESS_MAX_MS_V4_ACE_TYPE = 8
ACCESS_MAX_MS_ACE_TYPE = 8
ACCESS_ALLOWED_CALLBACK_ACE_TYPE = 9
ACCESS_DENIED_CALLBACK_ACE_TYPE = 10
ACCESS_ALLOWED_CALLBACK_OBJECT_ACE_TYPE = 11
ACCESS_DENIED_CALLBACK_OBJECT_ACE_TYPE = 12
SYSTEM_AUDIT_CALLBACK_ACE_TYPE = 13
SYSTEM_ALARM_CALLBACK_ACE_TYPE = 14
SYSTEM_AUDIT_CALLBACK_OBJECT_ACE_TYPE = 15
SYSTEM_ALARM_CALLBACK_OBJECT_ACE_TYPE = 16
SYSTEM_MANDATORY_LABEL_ACE_TYPE = 17
ACCESS_MAX_MS_V5_ACE_TYPE = 17

#  The following are the inherit flags that go into the AceFlags field
#  of an Ace header.

OBJECT_INHERIT_ACE = 1
CONTAINER_INHERIT_ACE = 2
NO_PROPAGATE_INHERIT_ACE = 4
INHERIT_ONLY_ACE = 8
VALID_INHERIT_FLAGS = 15


SUCCESSFUL_ACCESS_ACE_FLAG = 64
FAILED_ACCESS_ACE_FLAG = 128

SE_OWNER_DEFAULTED = 1
SE_GROUP_DEFAULTED = 2
SE_DACL_PRESENT = 4
SE_DACL_DEFAULTED = 8
SE_SACL_PRESENT = 16
SE_SACL_DEFAULTED = 32
SE_SELF_RELATIVE = 32768


SE_PRIVILEGE_ENABLED_BY_DEFAULT = 1
SE_PRIVILEGE_ENABLED = 2
SE_PRIVILEGE_USED_FOR_ACCESS = -2147483648

PRIVILEGE_SET_ALL_NECESSARY = 1

#               NT Defined Privileges

SE_CREATE_TOKEN_NAME = "SeCreateTokenPrivilege"
SE_ASSIGNPRIMARYTOKEN_NAME = "SeAssignPrimaryTokenPrivilege"
SE_LOCK_MEMORY_NAME = "SeLockMemoryPrivilege"
SE_INCREASE_QUOTA_NAME = "SeIncreaseQuotaPrivilege"
SE_UNSOLICITED_INPUT_NAME = "SeUnsolicitedInputPrivilege"
SE_MACHINE_ACCOUNT_NAME = "SeMachineAccountPrivilege"
SE_TCB_NAME = "SeTcbPrivilege"
SE_SECURITY_NAME = "SeSecurityPrivilege"
SE_TAKE_OWNERSHIP_NAME = "SeTakeOwnershipPrivilege"
SE_LOAD_DRIVER_NAME = "SeLoadDriverPrivilege"
SE_SYSTEM_PROFILE_NAME = "SeSystemProfilePrivilege"
SE_SYSTEMTIME_NAME = "SeSystemtimePrivilege"
SE_PROF_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"
SE_INC_BASE_PRIORITY_NAME = "SeIncreaseBasePriorityPrivilege"
SE_CREATE_PAGEFILE_NAME = "SeCreatePagefilePrivilege"
SE_CREATE_PERMANENT_NAME = "SeCreatePermanentPrivilege"
SE_BACKUP_NAME = "SeBackupPrivilege"
SE_RESTORE_NAME = "SeRestorePrivilege"
SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
SE_DEBUG_NAME = "SeDebugPrivilege"
SE_AUDIT_NAME = "SeAuditPrivilege"
SE_SYSTEM_ENVIRONMENT_NAME = "SeSystemEnvironmentPrivilege"
SE_CHANGE_NOTIFY_NAME = "SeChangeNotifyPrivilege"
SE_REMOTE_SHUTDOWN_NAME = "SeRemoteShutdownPrivilege"


# Enum SECURITY_IMPERSONATION_LEVEL:
SecurityAnonymous = 0
SecurityIdentification = 1
SecurityImpersonation = 2
SecurityDelegation = 3

SECURITY_MAX_IMPERSONATION_LEVEL = SecurityDelegation

DEFAULT_IMPERSONATION_LEVEL = SecurityImpersonation

TOKEN_ASSIGN_PRIMARY = 1
TOKEN_DUPLICATE = 2
TOKEN_IMPERSONATE = 4
TOKEN_QUERY = 8
TOKEN_QUERY_SOURCE = 16
TOKEN_ADJUST_PRIVILEGES = 32
TOKEN_ADJUST_GROUPS = 64
TOKEN_ADJUST_DEFAULT = 128

TOKEN_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TOKEN_ASSIGN_PRIMARY
    | TOKEN_DUPLICATE
    | TOKEN_IMPERSONATE
    | TOKEN_QUERY
    | TOKEN_QUERY_SOURCE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)


TOKEN_READ = STANDARD_RIGHTS_READ | TOKEN_QUERY


TOKEN_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)

TOKEN_EXECUTE = STANDARD_RIGHTS_EXECUTE

SidTypeUser = 1
SidTypeGroup = 2
SidTypeDomain = 3
SidTypeAlias = 4
SidTypeWellKnownGroup = 5
SidTypeDeletedAccount = 6
SidTypeInvalid = 7
SidTypeUnknown = 8
SidTypeComputer = 9
SidTypeLabel = 10

# Token types
TokenPrimary = 1
TokenImpersonation = 2

# TOKEN_INFORMATION_CLASS, used with Get/SetTokenInformation
TokenUser = 1
TokenGroups = 2
TokenPrivileges = 3
TokenOwner = 4
TokenPrimaryGroup = 5
TokenDefaultDacl = 6
TokenSource = 7
TokenType = 8
TokenImpersonationLevel = 9
TokenStatistics = 10
TokenRestrictedSids = 11
TokenSessionId = 12
TokenGroupsAndPrivileges = 13
TokenSessionReference = 14
TokenSandBoxInert = 15
TokenAuditPolicy = 16
TokenOrigin = 17
TokenElevationType = 18
TokenLinkedToken = 19
TokenElevation = 20
TokenHasRestrictions = 21
TokenAccessInformation = 22
TokenVirtualizationAllowed = 23
TokenVirtualizationEnabled = 24
TokenIntegrityLevel = 25
TokenUIAccess = 26
TokenMandatoryPolicy = 27
TokenLogonSid = 28

# DirectoryService related constants.
# Generated by h2py from NtDsAPI.h
DS_BEHAVIOR_WIN2000 = 0
DS_BEHAVIOR_WIN2003_WITH_MIXED_DOMAINS = 1
DS_BEHAVIOR_WIN2003 = 2
DS_SYNCED_EVENT_NAME = "NTDSInitialSyncsCompleted"
ACTRL_DS_OPEN = 0x00000000
ACTRL_DS_CREATE_CHILD = 0x00000001
ACTRL_DS_DELETE_CHILD = 0x00000002
ACTRL_DS_LIST = 0x00000004
ACTRL_DS_SELF = 0x00000008
ACTRL_DS_READ_PROP = 0x00000010
ACTRL_DS_WRITE_PROP = 0x00000020
ACTRL_DS_DELETE_TREE = 0x00000040
ACTRL_DS_LIST_OBJECT = 0x00000080
ACTRL_DS_CONTROL_ACCESS = 0x00000100
NTDSAPI_BIND_ALLOW_DELEGATION = 0x00000001
DS_REPSYNC_ASYNCHRONOUS_OPERATION = 0x00000001
DS_REPSYNC_WRITEABLE = 0x00000002
DS_REPSYNC_PERIODIC = 0x00000004
DS_REPSYNC_INTERSITE_MESSAGING = 0x00000008
DS_REPSYNC_ALL_SOURCES = 0x00000010
DS_REPSYNC_FULL = 0x00000020
DS_REPSYNC_URGENT = 0x00000040
DS_REPSYNC_NO_DISCARD = 0x00000080
DS_REPSYNC_FORCE = 0x00000100
DS_REPSYNC_ADD_REFERENCE = 0x00000200
DS_REPSYNC_NEVER_COMPLETED = 0x00000400
DS_REPSYNC_TWO_WAY = 0x00000800
DS_REPSYNC_NEVER_NOTIFY = 0x00001000
DS_REPSYNC_INITIAL = 0x00002000
DS_REPSYNC_USE_COMPRESSION = 0x00004000
DS_REPSYNC_ABANDONED = 0x00008000
DS_REPSYNC_INITIAL_IN_PROGRESS = 0x00010000
DS_REPSYNC_PARTIAL_ATTRIBUTE_SET = 0x00020000
DS_REPSYNC_REQUEUE = 0x00040000
DS_REPSYNC_NOTIFICATION = 0x00080000
DS_REPSYNC_ASYNCHRONOUS_REPLICA = 0x00100000
DS_REPSYNC_CRITICAL = 0x00200000
DS_REPSYNC_FULL_IN_PROGRESS = 0x00400000
DS_REPSYNC_PREEMPTED = 0x00800000
DS_REPADD_ASYNCHRONOUS_OPERATION = 0x00000001
DS_REPADD_WRITEABLE = 0x00000002
DS_REPADD_INITIAL = 0x00000004
DS_REPADD_PERIODIC = 0x00000008
DS_REPADD_INTERSITE_MESSAGING = 0x00000010
DS_REPADD_ASYNCHRONOUS_REPLICA = 0x00000020
DS_REPADD_DISABLE_NOTIFICATION = 0x00000040
DS_REPADD_DISABLE_PERIODIC = 0x00000080
DS_REPADD_USE_COMPRESSION = 0x00000100
DS_REPADD_NEVER_NOTIFY = 0x00000200
DS_REPADD_TWO_WAY = 0x00000400
DS_REPADD_CRITICAL = 0x00000800
DS_REPDEL_ASYNCHRONOUS_OPERATION = 0x00000001
DS_REPDEL_WRITEABLE = 0x00000002
DS_REPDEL_INTERSITE_MESSAGING = 0x00000004
DS_REPDEL_IGNORE_ERRORS = 0x00000008
DS_REPDEL_LOCAL_ONLY = 0x00000010
DS_REPDEL_NO_SOURCE = 0x00000020
DS_REPDEL_REF_OK = 0x00000040
DS_REPMOD_ASYNCHRONOUS_OPERATION = 0x00000001
DS_REPMOD_WRITEABLE = 0x00000002
DS_REPMOD_UPDATE_FLAGS = 0x00000001
DS_REPMOD_UPDATE_ADDRESS = 0x00000002
DS_REPMOD_UPDATE_SCHEDULE = 0x00000004
DS_REPMOD_UPDATE_RESULT = 0x00000008
DS_REPMOD_UPDATE_TRANSPORT = 0x00000010
DS_REPUPD_ASYNCHRONOUS_OPERATION = 0x00000001
DS_REPUPD_WRITEABLE = 0x00000002
DS_REPUPD_ADD_REFERENCE = 0x00000004
DS_REPUPD_DELETE_REFERENCE = 0x00000008
DS_INSTANCETYPE_IS_NC_HEAD = 0x00000001
DS_INSTANCETYPE_NC_IS_WRITEABLE = 0x00000004
DS_INSTANCETYPE_NC_COMING = 0x00000010
DS_INSTANCETYPE_NC_GOING = 0x00000020
NTDSDSA_OPT_IS_GC = 1 << 0
NTDSDSA_OPT_DISABLE_INBOUND_REPL = 1 << 1
NTDSDSA_OPT_DISABLE_OUTBOUND_REPL = 1 << 2
NTDSDSA_OPT_DISABLE_NTDSCONN_XLATE = 1 << 3
NTDSCONN_OPT_IS_GENERATED = 1 << 0
NTDSCONN_OPT_TWOWAY_SYNC = 1 << 1
NTDSCONN_OPT_OVERRIDE_NOTIFY_DEFAULT = 1 << 2
NTDSCONN_OPT_USE_NOTIFY = 1 << 3
NTDSCONN_OPT_DISABLE_INTERSITE_COMPRESSION = 1 << 4
NTDSCONN_OPT_USER_OWNED_SCHEDULE = 1 << 5
NTDSCONN_KCC_NO_REASON = 0
NTDSCONN_KCC_GC_TOPOLOGY = 1 << 0
NTDSCONN_KCC_RING_TOPOLOGY = 1 << 1
NTDSCONN_KCC_MINIMIZE_HOPS_TOPOLOGY = 1 << 2
NTDSCONN_KCC_STALE_SERVERS_TOPOLOGY = 1 << 3
NTDSCONN_KCC_OSCILLATING_CONNECTION_TOPOLOGY = 1 << 4
NTDSCONN_KCC_INTERSITE_GC_TOPOLOGY = 1 << 5
NTDSCONN_KCC_INTERSITE_TOPOLOGY = 1 << 6
NTDSCONN_KCC_SERVER_FAILOVER_TOPOLOGY = 1 << 7
NTDSCONN_KCC_SITE_FAILOVER_TOPOLOGY = 1 << 8
NTDSCONN_KCC_REDUNDANT_SERVER_TOPOLOGY = 1 << 9
FRSCONN_PRIORITY_MASK = 0x70000000
FRSCONN_MAX_PRIORITY = 0x8
NTDSCONN_OPT_IGNORE_SCHEDULE_MASK = -2147483648

NTDSSETTINGS_OPT_IS_AUTO_TOPOLOGY_DISABLED = 1 << 0
NTDSSETTINGS_OPT_IS_TOPL_CLEANUP_DISABLED = 1 << 1
NTDSSETTINGS_OPT_IS_TOPL_MIN_HOPS_DISABLED = 1 << 2
NTDSSETTINGS_OPT_IS_TOPL_DETECT_STALE_DISABLED = 1 << 3
NTDSSETTINGS_OPT_IS_INTER_SITE_AUTO_TOPOLOGY_DISABLED = 1 << 4
NTDSSETTINGS_OPT_IS_GROUP_CACHING_ENABLED = 1 << 5
NTDSSETTINGS_OPT_FORCE_KCC_WHISTLER_BEHAVIOR = 1 << 6
NTDSSETTINGS_OPT_FORCE_KCC_W2K_ELECTION = 1 << 7
NTDSSETTINGS_OPT_IS_RAND_BH_SELECTION_DISABLED = 1 << 8
NTDSSETTINGS_OPT_IS_SCHEDULE_HASHING_ENABLED = 1 << 9
NTDSSETTINGS_OPT_IS_REDUNDANT_SERVER_TOPOLOGY_ENABLED = 1 << 10
NTDSSETTINGS_DEFAULT_SERVER_REDUNDANCY = 2
NTDSTRANSPORT_OPT_IGNORE_SCHEDULES = 1 << 0
NTDSTRANSPORT_OPT_BRIDGES_REQUIRED = 1 << 1
NTDSSITECONN_OPT_USE_NOTIFY = 1 << 0
NTDSSITECONN_OPT_TWOWAY_SYNC = 1 << 1
NTDSSITECONN_OPT_DISABLE_COMPRESSION = 1 << 2
NTDSSITELINK_OPT_USE_NOTIFY = 1 << 0
NTDSSITELINK_OPT_TWOWAY_SYNC = 1 << 1
NTDSSITELINK_OPT_DISABLE_COMPRESSION = 1 << 2
GUID_USERS_CONTAINER_A = "a9d1ca15768811d1aded00c04fd8d5cd"
GUID_COMPUTRS_CONTAINER_A = "aa312825768811d1aded00c04fd8d5cd"
GUID_SYSTEMS_CONTAINER_A = "ab1d30f3768811d1aded00c04fd8d5cd"
GUID_DOMAIN_CONTROLLERS_CONTAINER_A = "a361b2ffffd211d1aa4b00c04fd7d83a"
GUID_INFRASTRUCTURE_CONTAINER_A = "2fbac1870ade11d297c400c04fd8d5cd"
GUID_DELETED_OBJECTS_CONTAINER_A = "18e2ea80684f11d2b9aa00c04f79f805"
GUID_LOSTANDFOUND_CONTAINER_A = "ab8153b7768811d1aded00c04fd8d5cd"
GUID_FOREIGNSECURITYPRINCIPALS_CONTAINER_A = "22b70c67d56e4efb91e9300fca3dc1aa"
GUID_PROGRAM_DATA_CONTAINER_A = "09460c08ae1e4a4ea0f64aee7daa1e5a"
GUID_MICROSOFT_PROGRAM_DATA_CONTAINER_A = "f4be92a4c777485e878e9421d53087db"
GUID_NTDS_QUOTAS_CONTAINER_A = "6227f0af1fc2410d8e3bb10615bb5b0f"
GUID_USERS_CONTAINER_BYTE = (
    "\xa9\xd1\xca\x15\x76\x88\x11\xd1\xad\xed\x00\xc0\x4f\xd8\xd5\xcd"
)
GUID_COMPUTRS_CONTAINER_BYTE = (
    "\xaa\x31\x28\x25\x76\x88\x11\xd1\xad\xed\x00\xc0\x4f\xd8\xd5\xcd"
)
GUID_SYSTEMS_CONTAINER_BYTE = (
    "\xab\x1d\x30\xf3\x76\x88\x11\xd1\xad\xed\x00\xc0\x4f\xd8\xd5\xcd"
)
GUID_DOMAIN_CONTROLLERS_CONTAINER_BYTE = (
    "\xa3\x61\xb2\xff\xff\xd2\x11\xd1\xaa\x4b\x00\xc0\x4f\xd7\xd8\x3a"
)
GUID_INFRASTRUCTURE_CONTAINER_BYTE = (
    "\x2f\xba\xc1\x87\x0a\xde\x11\xd2\x97\xc4\x00\xc0\x4f\xd8\xd5\xcd"
)
GUID_DELETED_OBJECTS_CONTAINER_BYTE = (
    "\x18\xe2\xea\x80\x68\x4f\x11\xd2\xb9\xaa\x00\xc0\x4f\x79\xf8\x05"
)
GUID_LOSTANDFOUND_CONTAINER_BYTE = (
    "\xab\x81\x53\xb7\x76\x88\x11\xd1\xad\xed\x00\xc0\x4f\xd8\xd5\xcd"
)
GUID_FOREIGNSECURITYPRINCIPALS_CONTAINER_BYTE = (
    "\x22\xb7\x0c\x67\xd5\x6e\x4e\xfb\x91\xe9\x30\x0f\xca\x3d\xc1\xaa"
)
GUID_PROGRAM_DATA_CONTAINER_BYTE = (
    "\x09\x46\x0c\x08\xae\x1e\x4a\x4e\xa0\xf6\x4a\xee\x7d\xaa\x1e\x5a"
)
GUID_MICROSOFT_PROGRAM_DATA_CONTAINER_BYTE = (
    "\xf4\xbe\x92\xa4\xc7\x77\x48\x5e\x87\x8e\x94\x21\xd5\x30\x87\xdb"
)
GUID_NTDS_QUOTAS_CONTAINER_BYTE = (
    "\x62\x27\xf0\xaf\x1f\xc2\x41\x0d\x8e\x3b\xb1\x06\x15\xbb\x5b\x0f"
)
DS_REPSYNCALL_NO_OPTIONS = 0x00000000
DS_REPSYNCALL_ABORT_IF_SERVER_UNAVAILABLE = 0x00000001
DS_REPSYNCALL_SYNC_ADJACENT_SERVERS_ONLY = 0x00000002
DS_REPSYNCALL_ID_SERVERS_BY_DN = 0x00000004
DS_REPSYNCALL_DO_NOT_SYNC = 0x00000008
DS_REPSYNCALL_SKIP_INITIAL_CHECK = 0x00000010
DS_REPSYNCALL_PUSH_CHANGES_OUTWARD = 0x00000020
DS_REPSYNCALL_CROSS_SITE_BOUNDARIES = 0x00000040
DS_LIST_DSA_OBJECT_FOR_SERVER = 0
DS_LIST_DNS_HOST_NAME_FOR_SERVER = 1
DS_LIST_ACCOUNT_OBJECT_FOR_SERVER = 2
DS_ROLE_SCHEMA_OWNER = 0
DS_ROLE_DOMAIN_OWNER = 1
DS_ROLE_PDC_OWNER = 2
DS_ROLE_RID_OWNER = 3
DS_ROLE_INFRASTRUCTURE_OWNER = 4
DS_SCHEMA_GUID_NOT_FOUND = 0
DS_SCHEMA_GUID_ATTR = 1
DS_SCHEMA_GUID_ATTR_SET = 2
DS_SCHEMA_GUID_CLASS = 3
DS_SCHEMA_GUID_CONTROL_RIGHT = 4
DS_KCC_FLAG_ASYNC_OP = 1 << 0
DS_KCC_FLAG_DAMPED = 1 << 1
DS_EXIST_ADVISORY_MODE = 0x1
DS_REPL_INFO_FLAG_IMPROVE_LINKED_ATTRS = 0x00000001
DS_REPL_NBR_WRITEABLE = 0x00000010
DS_REPL_NBR_SYNC_ON_STARTUP = 0x00000020
DS_REPL_NBR_DO_SCHEDULED_SYNCS = 0x00000040
DS_REPL_NBR_USE_ASYNC_INTERSITE_TRANSPORT = 0x00000080
DS_REPL_NBR_TWO_WAY_SYNC = 0x00000200
DS_REPL_NBR_RETURN_OBJECT_PARENTS = 0x00000800
DS_REPL_NBR_FULL_SYNC_IN_PROGRESS = 0x00010000
DS_REPL_NBR_FULL_SYNC_NEXT_PACKET = 0x00020000
DS_REPL_NBR_NEVER_SYNCED = 0x00200000
DS_REPL_NBR_PREEMPTED = 0x01000000
DS_REPL_NBR_IGNORE_CHANGE_NOTIFICATIONS = 0x04000000
DS_REPL_NBR_DISABLE_SCHEDULED_SYNC = 0x08000000
DS_REPL_NBR_COMPRESS_CHANGES = 0x10000000
DS_REPL_NBR_NO_CHANGE_NOTIFICATIONS = 0x20000000
DS_REPL_NBR_PARTIAL_ATTRIBUTE_SET = 0x40000000
DS_REPL_NBR_MODIFIABLE_MASK = (
    DS_REPL_NBR_SYNC_ON_STARTUP
    | DS_REPL_NBR_DO_SCHEDULED_SYNCS
    | DS_REPL_NBR_TWO_WAY_SYNC
    | DS_REPL_NBR_IGNORE_CHANGE_NOTIFICATIONS
    | DS_REPL_NBR_DISABLE_SCHEDULED_SYNC
    | DS_REPL_NBR_COMPRESS_CHANGES
    | DS_REPL_NBR_NO_CHANGE_NOTIFICATIONS
)

# from enum DS_NAME_FORMAT
DS_UNKNOWN_NAME = 0
DS_FQDN_1779_NAME = 1
DS_NT4_ACCOUNT_NAME = 2
DS_DISPLAY_NAME = 3
DS_UNIQUE_ID_NAME = 6
DS_CANONICAL_NAME = 7
DS_USER_PRINCIPAL_NAME = 8
DS_CANONICAL_NAME_EX = 9
DS_SERVICE_PRINCIPAL_NAME = 10
DS_SID_OR_SID_HISTORY_NAME = 11
DS_DNS_DOMAIN_NAME = 12

DS_DOMAIN_SIMPLE_NAME = DS_USER_PRINCIPAL_NAME
DS_ENTERPRISE_SIMPLE_NAME = DS_USER_PRINCIPAL_NAME

# from enum DS_NAME_FLAGS
DS_NAME_NO_FLAGS = 0x0
DS_NAME_FLAG_SYNTACTICAL_ONLY = 0x1
DS_NAME_FLAG_EVAL_AT_DC = 0x2
DS_NAME_FLAG_GCVERIFY = 0x4
DS_NAME_FLAG_TRUST_REFERRAL = 0x8

# from enum DS_NAME_ERROR
DS_NAME_NO_ERROR = 0
DS_NAME_ERROR_RESOLVING = 1
DS_NAME_ERROR_NOT_FOUND = 2
DS_NAME_ERROR_NOT_UNIQUE = 3
DS_NAME_ERROR_NO_MAPPING = 4
DS_NAME_ERROR_DOMAIN_ONLY = 5
DS_NAME_ERROR_NO_SYNTACTICAL_MAPPING = 6
DS_NAME_ERROR_TRUST_REFERRAL = 7


# from enum DS_SPN_NAME_TYPE
DS_SPN_DNS_HOST = 0
DS_SPN_DN_HOST = 1
DS_SPN_NB_HOST = 2
DS_SPN_DOMAIN = 3
DS_SPN_NB_DOMAIN = 4
DS_SPN_SERVICE = 5

# from enum DS_SPN_WRITE_OP
DS_SPN_ADD_SPN_OP = 0
DS_SPN_REPLACE_SPN_OP = 1
DS_SPN_DELETE_SPN_OP = 2

# Generated by h2py from DsGetDC.h
DS_FORCE_REDISCOVERY = 0x00000001
DS_DIRECTORY_SERVICE_REQUIRED = 0x00000010
DS_DIRECTORY_SERVICE_PREFERRED = 0x00000020
DS_GC_SERVER_REQUIRED = 0x00000040
DS_PDC_REQUIRED = 0x00000080
DS_BACKGROUND_ONLY = 0x00000100
DS_IP_REQUIRED = 0x00000200
DS_KDC_REQUIRED = 0x00000400
DS_TIMESERV_REQUIRED = 0x00000800
DS_WRITABLE_REQUIRED = 0x00001000
DS_GOOD_TIMESERV_PREFERRED = 0x00002000
DS_AVOID_SELF = 0x00004000
DS_ONLY_LDAP_NEEDED = 0x00008000
DS_IS_FLAT_NAME = 0x00010000
DS_IS_DNS_NAME = 0x00020000
DS_RETURN_DNS_NAME = 0x40000000
DS_RETURN_FLAT_NAME = -2147483648
DSGETDC_VALID_FLAGS = (
    DS_FORCE_REDISCOVERY
    | DS_DIRECTORY_SERVICE_REQUIRED
    | DS_DIRECTORY_SERVICE_PREFERRED
    | DS_GC_SERVER_REQUIRED
    | DS_PDC_REQUIRED
    | DS_BACKGROUND_ONLY
    | DS_IP_REQUIRED
    | DS_KDC_REQUIRED
    | DS_TIMESERV_REQUIRED
    | DS_WRITABLE_REQUIRED
    | DS_GOOD_TIMESERV_PREFERRED
    | DS_AVOID_SELF
    | DS_ONLY_LDAP_NEEDED
    | DS_IS_FLAT_NAME
    | DS_IS_DNS_NAME
    | DS_RETURN_FLAT_NAME
    | DS_RETURN_DNS_NAME
)
DS_INET_ADDRESS = 1
DS_NETBIOS_ADDRESS = 2
DS_PDC_FLAG = 0x00000001
DS_GC_FLAG = 0x00000004
DS_LDAP_FLAG = 0x00000008
DS_DS_FLAG = 0x00000010
DS_KDC_FLAG = 0x00000020
DS_TIMESERV_FLAG = 0x00000040
DS_CLOSEST_FLAG = 0x00000080
DS_WRITABLE_FLAG = 0x00000100
DS_GOOD_TIMESERV_FLAG = 0x00000200
DS_NDNC_FLAG = 0x00000400
DS_PING_FLAGS = 0x0000FFFF
DS_DNS_CONTROLLER_FLAG = 0x20000000
DS_DNS_DOMAIN_FLAG = 0x40000000
DS_DNS_FOREST_FLAG = -2147483648
DS_DOMAIN_IN_FOREST = 0x0001
DS_DOMAIN_DIRECT_OUTBOUND = 0x0002
DS_DOMAIN_TREE_ROOT = 0x0004
DS_DOMAIN_PRIMARY = 0x0008
DS_DOMAIN_NATIVE_MODE = 0x0010
DS_DOMAIN_DIRECT_INBOUND = 0x0020
DS_DOMAIN_VALID_FLAGS = (
    DS_DOMAIN_IN_FOREST
    | DS_DOMAIN_DIRECT_OUTBOUND
    | DS_DOMAIN_TREE_ROOT
    | DS_DOMAIN_PRIMARY
    | DS_DOMAIN_NATIVE_MODE
    | DS_DOMAIN_DIRECT_INBOUND
)
DS_GFTI_UPDATE_TDO = 0x1
DS_GFTI_VALID_FLAGS = 0x1
DS_ONLY_DO_SITE_NAME = 0x01
DS_NOTIFY_AFTER_SITE_RECORDS = 0x02
DS_OPEN_VALID_OPTION_FLAGS = DS_ONLY_DO_SITE_NAME | DS_NOTIFY_AFTER_SITE_RECORDS
DS_OPEN_VALID_FLAGS = (
    DS_FORCE_REDISCOVERY
    | DS_ONLY_LDAP_NEEDED
    | DS_KDC_REQUIRED
    | DS_PDC_REQUIRED
    | DS_GC_SERVER_REQUIRED
    | DS_WRITABLE_REQUIRED
)

## from aclui.h
# SI_OBJECT_INFO.dwFlags
SI_EDIT_PERMS = 0x00000000
SI_EDIT_OWNER = 0x00000001
SI_EDIT_AUDITS = 0x00000002
SI_CONTAINER = 0x00000004
SI_READONLY = 0x00000008
SI_ADVANCED = 0x00000010
SI_RESET = 0x00000020
SI_OWNER_READONLY = 0x00000040
SI_EDIT_PROPERTIES = 0x00000080
SI_OWNER_RECURSE = 0x00000100
SI_NO_ACL_PROTECT = 0x00000200
SI_NO_TREE_APPLY = 0x00000400
SI_PAGE_TITLE = 0x00000800
SI_SERVER_IS_DC = 0x00001000
SI_RESET_DACL_TREE = 0x00004000
SI_RESET_SACL_TREE = 0x00008000
SI_OBJECT_GUID = 0x00010000
SI_EDIT_EFFECTIVE = 0x00020000
SI_RESET_DACL = 0x00040000
SI_RESET_SACL = 0x00080000
SI_RESET_OWNER = 0x00100000
SI_NO_ADDITIONAL_PERMISSION = 0x00200000
SI_MAY_WRITE = 0x10000000
SI_EDIT_ALL = SI_EDIT_PERMS | SI_EDIT_OWNER | SI_EDIT_AUDITS
SI_AUDITS_ELEVATION_REQUIRED = 0x02000000
SI_VIEW_ONLY = 0x00400000
SI_OWNER_ELEVATION_REQUIRED = 0x04000000
SI_PERMS_ELEVATION_REQUIRED = 0x01000000

# SI_ACCESS.dwFlags
SI_ACCESS_SPECIFIC = 0x00010000
SI_ACCESS_GENERAL = 0x00020000
SI_ACCESS_CONTAINER = 0x00040000
SI_ACCESS_PROPERTY = 0x00080000

# SI_PAGE_TYPE enum
SI_PAGE_PERM = 0
SI_PAGE_ADVPERM = 1
SI_PAGE_AUDIT = 2
SI_PAGE_OWNER = 3
SI_PAGE_EFFECTIVE = 4

CFSTR_ACLUI_SID_INFO_LIST = "CFSTR_ACLUI_SID_INFO_LIST"
PSPCB_SI_INITDIALOG = 1025  ## WM_USER+1

# === NexusCore/exported_projects\app_20250703_223016\app\models_backup.py ===
# app/models.py
from app import db # app/__init__.py で定義されたdbオブジェクトをインポート

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60))
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit_margin = db.Column(db.Float) # これは手動で更新するか、calculate_profitで計算後に保存

    def calculate_profit(self):
        # 手数料15%仮定。必要であれば、config.py などで設定できるようにしても良い
        # shipping_costは別途考慮が必要な場合、引数で渡すか、Productモデルに含める
        return self.selling_price - self.purchase_price - (self.selling_price * 0.15)

    def __repr__(self):
        return f"<Product {self.name}>"

# === NexusCore/exported_projects\app_20250703_223016\app\__init__.py ===
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    from app.routes.image_crawler_route import bp as image_crawler_bp
    app.register_blueprint(image_crawler_bp)
    
    return app

# === NexusCore/exported_projects\project_export_m73owrzi\app\models_backup.py ===
# app/models.py
from app import db # app/__init__.py で定義されたdbオブジェクトをインポート

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60))
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit_margin = db.Column(db.Float) # これは手動で更新するか、calculate_profitで計算後に保存

    def calculate_profit(self):
        # 手数料15%仮定。必要であれば、config.py などで設定できるようにしても良い
        # shipping_costは別途考慮が必要な場合、引数で渡すか、Productモデルに含める
        return self.selling_price - self.purchase_price - (self.selling_price * 0.15)

    def __repr__(self):
        return f"<Product {self.name}>"

# === NexusCore/exported_projects\project_export_m73owrzi\app\__init__.py ===
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    from app.routes.image_crawler_route import bp as image_crawler_bp
    app.register_blueprint(image_crawler_bp)
    
    return app

# === NexusCore/exported_projects\project_export_xb_l70t8\app\models_backup.py ===
# app/models.py
from app import db # app/__init__.py で定義されたdbオブジェクトをインポート

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60))
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit_margin = db.Column(db.Float) # これは手動で更新するか、calculate_profitで計算後に保存

    def calculate_profit(self):
        # 手数料15%仮定。必要であれば、config.py などで設定できるようにしても良い
        # shipping_costは別途考慮が必要な場合、引数で渡すか、Productモデルに含める
        return self.selling_price - self.purchase_price - (self.selling_price * 0.15)

    def __repr__(self):
        return f"<Product {self.name}>"

# === NexusCore/exported_projects\project_export_xb_l70t8\app\__init__.py ===
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    from app.routes.image_crawler_route import bp as image_crawler_bp
    app.register_blueprint(image_crawler_bp)
    
    return app

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\models_backup.py ===
# app/models.py
from app import db # app/__init__.py で定義されたdbオブジェクトをインポート

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60))
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit_margin = db.Column(db.Float) # これは手動で更新するか、calculate_profitで計算後に保存

    def calculate_profit(self):
        # 手数料15%仮定。必要であれば、config.py などで設定できるようにしても良い
        # shipping_costは別途考慮が必要な場合、引数で渡すか、Productモデルに含める
        return self.selling_price - self.purchase_price - (self.selling_price * 0.15)

    def __repr__(self):
        return f"<Product {self.name}>"

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\__init__.py ===
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    from app.routes.image_crawler_route import bp as image_crawler_bp
    app.register_blueprint(image_crawler_bp)
    
    return app

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_datasource.py ===
"""A file interface for handling local and remote data files.

The goal of datasource is to abstract some of the file system operations
when dealing with data files so the researcher doesn't have to know all the
low-level details.  Through datasource, a researcher can obtain and use a
file with one function call, regardless of location of the file.

DataSource is meant to augment standard python libraries, not replace them.
It should work seamlessly with standard file IO operations and the os
module.

DataSource files can originate locally or remotely:

- local files : '/home/guido/src/local/data.txt'
- URLs (http, ftp, ...) : 'http://www.scipy.org/not/real/data.txt'

DataSource files can also be compressed or uncompressed.  Currently only
gzip, bz2 and xz are supported.

Example::

    >>> # Create a DataSource, use os.curdir (default) for local storage.
    >>> from numpy import DataSource
    >>> ds = DataSource()
    >>>
    >>> # Open a remote file.
    >>> # DataSource downloads the file, stores it locally in:
    >>> #     './www.google.com/index.html'
    >>> # opens the file and returns a file object.
    >>> fp = ds.open('http://www.google.com/') # doctest: +SKIP
    >>>
    >>> # Use the file as you normally would
    >>> fp.read() # doctest: +SKIP
    >>> fp.close() # doctest: +SKIP

"""
import os

from numpy._utils import set_module

_open = open


def _check_mode(mode, encoding, newline):
    """Check mode and that encoding and newline are compatible.

    Parameters
    ----------
    mode : str
        File open mode.
    encoding : str
        File encoding.
    newline : str
        Newline for text files.

    """
    if "t" in mode:
        if "b" in mode:
            raise ValueError(f"Invalid mode: {mode!r}")
    else:
        if encoding is not None:
            raise ValueError("Argument 'encoding' not supported in binary mode")
        if newline is not None:
            raise ValueError("Argument 'newline' not supported in binary mode")


# Using a class instead of a module-level dictionary
# to reduce the initial 'import numpy' overhead by
# deferring the import of lzma, bz2 and gzip until needed

# TODO: .zip support, .tar support?
class _FileOpeners:
    """
    Container for different methods to open (un-)compressed files.

    `_FileOpeners` contains a dictionary that holds one method for each
    supported file format. Attribute lookup is implemented in such a way
    that an instance of `_FileOpeners` itself can be indexed with the keys
    of that dictionary. Currently uncompressed files as well as files
    compressed with ``gzip``, ``bz2`` or ``xz`` compression are supported.

    Notes
    -----
    `_file_openers`, an instance of `_FileOpeners`, is made available for
    use in the `_datasource` module.

    Examples
    --------
    >>> import gzip
    >>> np.lib._datasource._file_openers.keys()
    [None, '.bz2', '.gz', '.xz', '.lzma']
    >>> np.lib._datasource._file_openers['.gz'] is gzip.open
    True

    """

    def __init__(self):
        self._loaded = False
        self._file_openers = {None: open}

    def _load(self):
        if self._loaded:
            return

        try:
            import bz2
            self._file_openers[".bz2"] = bz2.open
        except ImportError:
            pass

        try:
            import gzip
            self._file_openers[".gz"] = gzip.open
        except ImportError:
            pass

        try:
            import lzma
            self._file_openers[".xz"] = lzma.open
            self._file_openers[".lzma"] = lzma.open
        except (ImportError, AttributeError):
            # There are incompatible backports of lzma that do not have the
            # lzma.open attribute, so catch that as well as ImportError.
            pass

        self._loaded = True

    def keys(self):
        """
        Return the keys of currently supported file openers.

        Parameters
        ----------
        None

        Returns
        -------
        keys : list
            The keys are None for uncompressed files and the file extension
            strings (i.e. ``'.gz'``, ``'.xz'``) for supported compression
            methods.

        """
        self._load()
        return list(self._file_openers.keys())

    def __getitem__(self, key):
        self._load()
        return self._file_openers[key]


_file_openers = _FileOpeners()

def open(path, mode='r', destpath=os.curdir, encoding=None, newline=None):
    """
    Open `path` with `mode` and return the file object.

    If ``path`` is an URL, it will be downloaded, stored in the
    `DataSource` `destpath` directory and opened from there.

    Parameters
    ----------
    path : str or pathlib.Path
        Local file path or URL to open.
    mode : str, optional
        Mode to open `path`. Mode 'r' for reading, 'w' for writing, 'a' to
        append. Available modes depend on the type of object specified by
        path.  Default is 'r'.
    destpath : str, optional
        Path to the directory where the source file gets downloaded to for
        use.  If `destpath` is None, a temporary directory will be created.
        The default path is the current directory.
    encoding : {None, str}, optional
        Open text file with given encoding. The default encoding will be
        what `open` uses.
    newline : {None, str}, optional
        Newline to use when reading text file.

    Returns
    -------
    out : file object
        The opened file.

    Notes
    -----
    This is a convenience function that instantiates a `DataSource` and
    returns the file object from ``DataSource.open(path)``.

    """

    ds = DataSource(destpath)
    return ds.open(path, mode, encoding=encoding, newline=newline)


@set_module('numpy.lib.npyio')
class DataSource:
    """
    DataSource(destpath='.')

    A generic data source file (file, http, ftp, ...).

    DataSources can be local files or remote files/URLs.  The files may
    also be compressed or uncompressed. DataSource hides some of the
    low-level details of downloading the file, allowing you to simply pass
    in a valid file path (or URL) and obtain a file object.

    Parameters
    ----------
    destpath : str or None, optional
        Path to the directory where the source file gets downloaded to for
        use.  If `destpath` is None, a temporary directory will be created.
        The default path is the current directory.

    Notes
    -----
    URLs require a scheme string (``http://``) to be used, without it they
    will fail::

        >>> repos = np.lib.npyio.DataSource()
        >>> repos.exists('www.google.com/index.html')
        False
        >>> repos.exists('http://www.google.com/index.html')
        True

    Temporary directories are deleted when the DataSource is deleted.

    Examples
    --------
    ::

        >>> ds = np.lib.npyio.DataSource('/home/guido')
        >>> urlname = 'http://www.google.com/'
        >>> gfile = ds.open('http://www.google.com/')
        >>> ds.abspath(urlname)
        '/home/guido/www.google.com/index.html'

        >>> ds = np.lib.npyio.DataSource(None)  # use with temporary file
        >>> ds.open('/home/guido/foobar.txt')
        <open file '/home/guido.foobar.txt', mode 'r' at 0x91d4430>
        >>> ds.abspath('/home/guido/foobar.txt')
        '/tmp/.../home/guido/foobar.txt'

    """

    def __init__(self, destpath=os.curdir):
        """Create a DataSource with a local path at destpath."""
        if destpath:
            self._destpath = os.path.abspath(destpath)
            self._istmpdest = False
        else:
            import tempfile  # deferring import to improve startup time
            self._destpath = tempfile.mkdtemp()
            self._istmpdest = True

    def __del__(self):
        # Remove temp directories
        if hasattr(self, '_istmpdest') and self._istmpdest:
            import shutil

            shutil.rmtree(self._destpath)

    def _iszip(self, filename):
        """Test if the filename is a zip file by looking at the file extension.

        """
        fname, ext = os.path.splitext(filename)
        return ext in _file_openers.keys()

    def _iswritemode(self, mode):
        """Test if the given mode will open a file for writing."""

        # Currently only used to test the bz2 files.
        _writemodes = ("w", "+")
        return any(c in _writemodes for c in mode)

    def _splitzipext(self, filename):
        """Split zip extension from filename and return filename.

        Returns
        -------
        base, zip_ext : {tuple}

        """

        if self._iszip(filename):
            return os.path.splitext(filename)
        else:
            return filename, None

    def _possible_names(self, filename):
        """Return a tuple containing compressed filename variations."""
        names = [filename]
        if not self._iszip(filename):
            for zipext in _file_openers.keys():
                if zipext:
                    names.append(filename + zipext)
        return names

    def _isurl(self, path):
        """Test if path is a net location.  Tests the scheme and netloc."""

        # We do this here to reduce the 'import numpy' initial import time.
        from urllib.parse import urlparse

        # BUG : URLs require a scheme string ('http://') to be used.
        #       www.google.com will fail.
        #       Should we prepend the scheme for those that don't have it and
        #       test that also?  Similar to the way we append .gz and test for
        #       for compressed versions of files.

        scheme, netloc, upath, uparams, uquery, ufrag = urlparse(path)
        return bool(scheme and netloc)

    def _cache(self, path):
        """Cache the file specified by path.

        Creates a copy of the file in the datasource cache.

        """
        # We import these here because importing them is slow and
        # a significant fraction of numpy's total import time.
        import shutil
        from urllib.request import urlopen

        upath = self.abspath(path)

        # ensure directory exists
        if not os.path.exists(os.path.dirname(upath)):
            os.makedirs(os.path.dirname(upath))

        # TODO: Doesn't handle compressed files!
        if self._isurl(path):
            with urlopen(path) as openedurl:
                with _open(upath, 'wb') as f:
                    shutil.copyfileobj(openedurl, f)
        else:
            shutil.copyfile(path, upath)
        return upath

    def _findfile(self, path):
        """Searches for ``path`` and returns full path if found.

        If path is an URL, _findfile will cache a local copy and return the
        path to the cached file.  If path is a local file, _findfile will
        return a path to that local file.

        The search will include possible compressed versions of the file
        and return the first occurrence found.

        """

        # Build list of possible local file paths
        if not self._isurl(path):
            # Valid local paths
            filelist = self._possible_names(path)
            # Paths in self._destpath
            filelist += self._possible_names(self.abspath(path))
        else:
            # Cached URLs in self._destpath
            filelist = self._possible_names(self.abspath(path))
            # Remote URLs
            filelist = filelist + self._possible_names(path)

        for name in filelist:
            if self.exists(name):
                if self._isurl(name):
                    name = self._cache(name)
                return name
        return None

    def abspath(self, path):
        """
        Return absolute path of file in the DataSource directory.

        If `path` is an URL, then `abspath` will return either the location
        the file exists locally or the location it would exist when opened
        using the `open` method.

        Parameters
        ----------
        path : str or pathlib.Path
            Can be a local file or a remote URL.

        Returns
        -------
        out : str
            Complete path, including the `DataSource` destination directory.

        Notes
        -----
        The functionality is based on `os.path.abspath`.

        """
        # We do this here to reduce the 'import numpy' initial import time.
        from urllib.parse import urlparse

        # TODO:  This should be more robust.  Handles case where path includes
        #        the destpath, but not other sub-paths. Failing case:
        #        path = /home/guido/datafile.txt
        #        destpath = /home/alex/
        #        upath = self.abspath(path)
        #        upath == '/home/alex/home/guido/datafile.txt'

        # handle case where path includes self._destpath
        splitpath = path.split(self._destpath, 2)
        if len(splitpath) > 1:
            path = splitpath[1]
        scheme, netloc, upath, uparams, uquery, ufrag = urlparse(path)
        netloc = self._sanitize_relative_path(netloc)
        upath = self._sanitize_relative_path(upath)
        return os.path.join(self._destpath, netloc, upath)

    def _sanitize_relative_path(self, path):
        """Return a sanitised relative path for which
        os.path.abspath(os.path.join(base, path)).startswith(base)
        """
        last = None
        path = os.path.normpath(path)
        while path != last:
            last = path
            # Note: os.path.join treats '/' as os.sep on Windows
            path = path.lstrip(os.sep).lstrip('/')
            path = path.lstrip(os.pardir).removeprefix('..')
            drive, path = os.path.splitdrive(path)  # for Windows
        return path

    def exists(self, path):
        """
        Test if path exists.

        Test if `path` exists as (and in this order):

        - a local file.
        - a remote URL that has been downloaded and stored locally in the
          `DataSource` directory.
        - a remote URL that has not been downloaded, but is valid and
          accessible.

        Parameters
        ----------
        path : str or pathlib.Path
            Can be a local file or a remote URL.

        Returns
        -------
        out : bool
            True if `path` exists.

        Notes
        -----
        When `path` is an URL, `exists` will return True if it's either
        stored locally in the `DataSource` directory, or is a valid remote
        URL.  `DataSource` does not discriminate between the two, the file
        is accessible if it exists in either location.

        """

        # First test for local path
        if os.path.exists(path):
            return True

        # We import this here because importing urllib is slow and
        # a significant fraction of numpy's total import time.
        from urllib.error import URLError
        from urllib.request import urlopen

        # Test cached url
        upath = self.abspath(path)
        if os.path.exists(upath):
            return True

        # Test remote url
        if self._isurl(path):
            try:
                netfile = urlopen(path)
                netfile.close()
                del netfile
                return True
            except URLError:
                return False
        return False

    def open(self, path, mode='r', encoding=None, newline=None):
        """
        Open and return file-like object.

        If `path` is an URL, it will be downloaded, stored in the
        `DataSource` directory and opened from there.

        Parameters
        ----------
        path : str or pathlib.Path
            Local file path or URL to open.
        mode : {'r', 'w', 'a'}, optional
            Mode to open `path`.  Mode 'r' for reading, 'w' for writing,
            'a' to append. Available modes depend on the type of object
            specified by `path`. Default is 'r'.
        encoding : {None, str}, optional
            Open text file with given encoding. The default encoding will be
            what `open` uses.
        newline : {None, str}, optional
            Newline to use when reading text file.

        Returns
        -------
        out : file object
            File object.

        """

        # TODO: There is no support for opening a file for writing which
        #       doesn't exist yet (creating a file).  Should there be?

        # TODO: Add a ``subdir`` parameter for specifying the subdirectory
        #       used to store URLs in self._destpath.

        if self._isurl(path) and self._iswritemode(mode):
            raise ValueError("URLs are not writeable")

        # NOTE: _findfile will fail on a new file opened for writing.
        found = self._findfile(path)
        if found:
            _fname, ext = self._splitzipext(found)
            if ext == 'bz2':
                mode.replace("+", "")
            return _file_openers[ext](found, mode=mode,
                                      encoding=encoding, newline=newline)
        else:
            raise FileNotFoundError(f"{path} not found.")


class Repository (DataSource):
    """
    Repository(baseurl, destpath='.')

    A data repository where multiple DataSource's share a base
    URL/directory.

    `Repository` extends `DataSource` by prepending a base URL (or
    directory) to all the files it handles. Use `Repository` when you will
    be working with multiple files from one base URL.  Initialize
    `Repository` with the base URL, then refer to each file by its filename
    only.

    Parameters
    ----------
    baseurl : str
        Path to the local directory or remote location that contains the
        data files.
    destpath : str or None, optional
        Path to the directory where the source file gets downloaded to for
        use.  If `destpath` is None, a temporary directory will be created.
        The default path is the current directory.

    Examples
    --------
    To analyze all files in the repository, do something like this
    (note: this is not self-contained code)::

        >>> repos = np.lib._datasource.Repository('/home/user/data/dir/')
        >>> for filename in filelist:
        ...     fp = repos.open(filename)
        ...     fp.analyze()
        ...     fp.close()

    Similarly you could use a URL for a repository::

        >>> repos = np.lib._datasource.Repository('http://www.xyz.edu/data')

    """

    def __init__(self, baseurl, destpath=os.curdir):
        """Create a Repository with a shared url or directory of baseurl."""
        DataSource.__init__(self, destpath=destpath)
        self._baseurl = baseurl

    def __del__(self):
        DataSource.__del__(self)

    def _fullpath(self, path):
        """Return complete path for path.  Prepends baseurl if necessary."""
        splitpath = path.split(self._baseurl, 2)
        if len(splitpath) == 1:
            result = os.path.join(self._baseurl, path)
        else:
            result = path    # path contains baseurl already
        return result

    def _findfile(self, path):
        """Extend DataSource method to prepend baseurl to ``path``."""
        return DataSource._findfile(self, self._fullpath(path))

    def abspath(self, path):
        """
        Return absolute path of file in the Repository directory.

        If `path` is an URL, then `abspath` will return either the location
        the file exists locally or the location it would exist when opened
        using the `open` method.

        Parameters
        ----------
        path : str or pathlib.Path
            Can be a local file or a remote URL. This may, but does not
            have to, include the `baseurl` with which the `Repository` was
            initialized.

        Returns
        -------
        out : str
            Complete path, including the `DataSource` destination directory.

        """
        return DataSource.abspath(self, self._fullpath(path))

    def exists(self, path):
        """
        Test if path exists prepending Repository base URL to path.

        Test if `path` exists as (and in this order):

        - a local file.
        - a remote URL that has been downloaded and stored locally in the
          `DataSource` directory.
        - a remote URL that has not been downloaded, but is valid and
          accessible.

        Parameters
        ----------
        path : str or pathlib.Path
            Can be a local file or a remote URL. This may, but does not
            have to, include the `baseurl` with which the `Repository` was
            initialized.

        Returns
        -------
        out : bool
            True if `path` exists.

        Notes
        -----
        When `path` is an URL, `exists` will return True if it's either
        stored locally in the `DataSource` directory, or is a valid remote
        URL.  `DataSource` does not discriminate between the two, the file
        is accessible if it exists in either location.

        """
        return DataSource.exists(self, self._fullpath(path))

    def open(self, path, mode='r', encoding=None, newline=None):
        """
        Open and return file-like object prepending Repository base URL.

        If `path` is an URL, it will be downloaded, stored in the
        DataSource directory and opened from there.

        Parameters
        ----------
        path : str or pathlib.Path
            Local file path or URL to open. This may, but does not have to,
            include the `baseurl` with which the `Repository` was
            initialized.
        mode : {'r', 'w', 'a'}, optional
            Mode to open `path`.  Mode 'r' for reading, 'w' for writing,
            'a' to append. Available modes depend on the type of object
            specified by `path`. Default is 'r'.
        encoding : {None, str}, optional
            Open text file with given encoding. The default encoding will be
            what `open` uses.
        newline : {None, str}, optional
            Newline to use when reading text file.

        Returns
        -------
        out : file object
            File object.

        """
        return DataSource.open(self, self._fullpath(path), mode,
                               encoding=encoding, newline=newline)

    def listdir(self):
        """
        List files in the source Repository.

        Returns
        -------
        files : list of str or pathlib.Path
            List of file names (not containing a directory part).

        Notes
        -----
        Does not currently work for remote repositories.

        """
        if self._isurl(self._baseurl):
            raise NotImplementedError(
                  "Directory listing of URLs, not supported yet.")
        else:
            return os.listdir(self._baseurl)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_type_check_impl.py ===
"""Automatically adapted for numpy Sep 19, 2005 by convertcode.py

"""
import functools

__all__ = ['iscomplexobj', 'isrealobj', 'imag', 'iscomplex',
           'isreal', 'nan_to_num', 'real', 'real_if_close',
           'typename', 'mintypecode',
           'common_type']

import numpy._core.numeric as _nx
from numpy._core import getlimits, overrides
from numpy._core.numeric import asanyarray, asarray, isnan, zeros
from numpy._utils import set_module

from ._ufunclike_impl import isneginf, isposinf

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


_typecodes_by_elsize = 'GDFgdfQqLlIiHhBb?'


@set_module('numpy')
def mintypecode(typechars, typeset='GDFgdf', default='d'):
    """
    Return the character for the minimum-size type to which given types can
    be safely cast.

    The returned type character must represent the smallest size dtype such
    that an array of the returned type can handle the data from an array of
    all types in `typechars` (or if `typechars` is an array, then its
    dtype.char).

    Parameters
    ----------
    typechars : list of str or array_like
        If a list of strings, each string should represent a dtype.
        If array_like, the character representation of the array dtype is used.
    typeset : str or list of str, optional
        The set of characters that the returned character is chosen from.
        The default set is 'GDFgdf'.
    default : str, optional
        The default character, this is returned if none of the characters in
        `typechars` matches a character in `typeset`.

    Returns
    -------
    typechar : str
        The character representing the minimum-size type that was found.

    See Also
    --------
    dtype

    Examples
    --------
    >>> import numpy as np
    >>> np.mintypecode(['d', 'f', 'S'])
    'd'
    >>> x = np.array([1.1, 2-3.j])
    >>> np.mintypecode(x)
    'D'

    >>> np.mintypecode('abceh', default='G')
    'G'

    """
    typecodes = ((isinstance(t, str) and t) or asarray(t).dtype.char
                 for t in typechars)
    intersection = {t for t in typecodes if t in typeset}
    if not intersection:
        return default
    if 'F' in intersection and 'd' in intersection:
        return 'D'
    return min(intersection, key=_typecodes_by_elsize.index)


def _real_dispatcher(val):
    return (val,)


@array_function_dispatch(_real_dispatcher)
def real(val):
    """
    Return the real part of the complex argument.

    Parameters
    ----------
    val : array_like
        Input array.

    Returns
    -------
    out : ndarray or scalar
        The real component of the complex argument. If `val` is real, the type
        of `val` is used for the output.  If `val` has complex elements, the
        returned type is float.

    See Also
    --------
    real_if_close, imag, angle

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1+2j, 3+4j, 5+6j])
    >>> a.real
    array([1.,  3.,  5.])
    >>> a.real = 9
    >>> a
    array([9.+2.j,  9.+4.j,  9.+6.j])
    >>> a.real = np.array([9, 8, 7])
    >>> a
    array([9.+2.j,  8.+4.j,  7.+6.j])
    >>> np.real(1 + 1j)
    1.0

    """
    try:
        return val.real
    except AttributeError:
        return asanyarray(val).real


def _imag_dispatcher(val):
    return (val,)


@array_function_dispatch(_imag_dispatcher)
def imag(val):
    """
    Return the imaginary part of the complex argument.

    Parameters
    ----------
    val : array_like
        Input array.

    Returns
    -------
    out : ndarray or scalar
        The imaginary component of the complex argument. If `val` is real,
        the type of `val` is used for the output.  If `val` has complex
        elements, the returned type is float.

    See Also
    --------
    real, angle, real_if_close

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1+2j, 3+4j, 5+6j])
    >>> a.imag
    array([2.,  4.,  6.])
    >>> a.imag = np.array([8, 10, 12])
    >>> a
    array([1. +8.j,  3.+10.j,  5.+12.j])
    >>> np.imag(1 + 1j)
    1.0

    """
    try:
        return val.imag
    except AttributeError:
        return asanyarray(val).imag


def _is_type_dispatcher(x):
    return (x,)


@array_function_dispatch(_is_type_dispatcher)
def iscomplex(x):
    """
    Returns a bool array, where True if input element is complex.

    What is tested is whether the input has a non-zero imaginary part, not if
    the input type is complex.

    Parameters
    ----------
    x : array_like
        Input array.

    Returns
    -------
    out : ndarray of bools
        Output array.

    See Also
    --------
    isreal
    iscomplexobj : Return True if x is a complex type or an array of complex
                   numbers.

    Examples
    --------
    >>> import numpy as np
    >>> np.iscomplex([1+1j, 1+0j, 4.5, 3, 2, 2j])
    array([ True, False, False, False, False,  True])

    """
    ax = asanyarray(x)
    if issubclass(ax.dtype.type, _nx.complexfloating):
        return ax.imag != 0
    res = zeros(ax.shape, bool)
    return res[()]   # convert to scalar if needed


@array_function_dispatch(_is_type_dispatcher)
def isreal(x):
    """
    Returns a bool array, where True if input element is real.

    If element has complex type with zero imaginary part, the return value
    for that element is True.

    Parameters
    ----------
    x : array_like
        Input array.

    Returns
    -------
    out : ndarray, bool
        Boolean array of same shape as `x`.

    Notes
    -----
    `isreal` may behave unexpectedly for string or object arrays (see examples)

    See Also
    --------
    iscomplex
    isrealobj : Return True if x is not a complex type.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1+1j, 1+0j, 4.5, 3, 2, 2j], dtype=complex)
    >>> np.isreal(a)
    array([False,  True,  True,  True,  True, False])

    The function does not work on string arrays.

    >>> a = np.array([2j, "a"], dtype="U")
    >>> np.isreal(a)  # Warns about non-elementwise comparison
    False

    Returns True for all elements in input array of ``dtype=object`` even if
    any of the elements is complex.

    >>> a = np.array([1, "2", 3+4j], dtype=object)
    >>> np.isreal(a)
    array([ True,  True,  True])

    isreal should not be used with object arrays

    >>> a = np.array([1+2j, 2+1j], dtype=object)
    >>> np.isreal(a)
    array([ True,  True])

    """
    return imag(x) == 0


@array_function_dispatch(_is_type_dispatcher)
def iscomplexobj(x):
    """
    Check for a complex type or an array of complex numbers.

    The type of the input is checked, not the value. Even if the input
    has an imaginary part equal to zero, `iscomplexobj` evaluates to True.

    Parameters
    ----------
    x : any
        The input can be of any type and shape.

    Returns
    -------
    iscomplexobj : bool
        The return value, True if `x` is of a complex type or has at least
        one complex element.

    See Also
    --------
    isrealobj, iscomplex

    Examples
    --------
    >>> import numpy as np
    >>> np.iscomplexobj(1)
    False
    >>> np.iscomplexobj(1+0j)
    True
    >>> np.iscomplexobj([3, 1+0j, True])
    True

    """
    try:
        dtype = x.dtype
        type_ = dtype.type
    except AttributeError:
        type_ = asarray(x).dtype.type
    return issubclass(type_, _nx.complexfloating)


@array_function_dispatch(_is_type_dispatcher)
def isrealobj(x):
    """
    Return True if x is a not complex type or an array of complex numbers.

    The type of the input is checked, not the value. So even if the input
    has an imaginary part equal to zero, `isrealobj` evaluates to False
    if the data type is complex.

    Parameters
    ----------
    x : any
        The input can be of any type and shape.

    Returns
    -------
    y : bool
        The return value, False if `x` is of a complex type.

    See Also
    --------
    iscomplexobj, isreal

    Notes
    -----
    The function is only meant for arrays with numerical values but it
    accepts all other objects. Since it assumes array input, the return
    value of other objects may be True.

    >>> np.isrealobj('A string')
    True
    >>> np.isrealobj(False)
    True
    >>> np.isrealobj(None)
    True

    Examples
    --------
    >>> import numpy as np
    >>> np.isrealobj(1)
    True
    >>> np.isrealobj(1+0j)
    False
    >>> np.isrealobj([3, 1+0j, True])
    False

    """
    return not iscomplexobj(x)

#-----------------------------------------------------------------------------

def _getmaxmin(t):
    from numpy._core import getlimits
    f = getlimits.finfo(t)
    return f.max, f.min


def _nan_to_num_dispatcher(x, copy=None, nan=None, posinf=None, neginf=None):
    return (x,)


@array_function_dispatch(_nan_to_num_dispatcher)
def nan_to_num(x, copy=True, nan=0.0, posinf=None, neginf=None):
    """
    Replace NaN with zero and infinity with large finite numbers (default
    behaviour) or with the numbers defined by the user using the `nan`,
    `posinf` and/or `neginf` keywords.

    If `x` is inexact, NaN is replaced by zero or by the user defined value in
    `nan` keyword, infinity is replaced by the largest finite floating point
    values representable by ``x.dtype`` or by the user defined value in
    `posinf` keyword and -infinity is replaced by the most negative finite
    floating point values representable by ``x.dtype`` or by the user defined
    value in `neginf` keyword.

    For complex dtypes, the above is applied to each of the real and
    imaginary components of `x` separately.

    If `x` is not inexact, then no replacements are made.

    Parameters
    ----------
    x : scalar or array_like
        Input data.
    copy : bool, optional
        Whether to create a copy of `x` (True) or to replace values
        in-place (False). The in-place operation only occurs if
        casting to an array does not require a copy.
        Default is True.
    nan : int, float, optional
        Value to be used to fill NaN values. If no value is passed
        then NaN values will be replaced with 0.0.
    posinf : int, float, optional
        Value to be used to fill positive infinity values. If no value is
        passed then positive infinity values will be replaced with a very
        large number.
    neginf : int, float, optional
        Value to be used to fill negative infinity values. If no value is
        passed then negative infinity values will be replaced with a very
        small (or negative) number.

    Returns
    -------
    out : ndarray
        `x`, with the non-finite values replaced. If `copy` is False, this may
        be `x` itself.

    See Also
    --------
    isinf : Shows which elements are positive or negative infinity.
    isneginf : Shows which elements are negative infinity.
    isposinf : Shows which elements are positive infinity.
    isnan : Shows which elements are Not a Number (NaN).
    isfinite : Shows which elements are finite (not NaN, not infinity)

    Notes
    -----
    NumPy uses the IEEE Standard for Binary Floating-Point for Arithmetic
    (IEEE 754). This means that Not a Number is not equivalent to infinity.

    Examples
    --------
    >>> import numpy as np
    >>> np.nan_to_num(np.inf)
    1.7976931348623157e+308
    >>> np.nan_to_num(-np.inf)
    -1.7976931348623157e+308
    >>> np.nan_to_num(np.nan)
    0.0
    >>> x = np.array([np.inf, -np.inf, np.nan, -128, 128])
    >>> np.nan_to_num(x)
    array([ 1.79769313e+308, -1.79769313e+308,  0.00000000e+000, # may vary
           -1.28000000e+002,  1.28000000e+002])
    >>> np.nan_to_num(x, nan=-9999, posinf=33333333, neginf=33333333)
    array([ 3.3333333e+07,  3.3333333e+07, -9.9990000e+03,
           -1.2800000e+02,  1.2800000e+02])
    >>> y = np.array([complex(np.inf, np.nan), np.nan, complex(np.nan, np.inf)])
    array([  1.79769313e+308,  -1.79769313e+308,   0.00000000e+000, # may vary
         -1.28000000e+002,   1.28000000e+002])
    >>> np.nan_to_num(y)
    array([  1.79769313e+308 +0.00000000e+000j, # may vary
             0.00000000e+000 +0.00000000e+000j,
             0.00000000e+000 +1.79769313e+308j])
    >>> np.nan_to_num(y, nan=111111, posinf=222222)
    array([222222.+111111.j, 111111.     +0.j, 111111.+222222.j])
    """
    x = _nx.array(x, subok=True, copy=copy)
    xtype = x.dtype.type

    isscalar = (x.ndim == 0)

    if not issubclass(xtype, _nx.inexact):
        return x[()] if isscalar else x

    iscomplex = issubclass(xtype, _nx.complexfloating)

    dest = (x.real, x.imag) if iscomplex else (x,)
    maxf, minf = _getmaxmin(x.real.dtype)
    if posinf is not None:
        maxf = posinf
    if neginf is not None:
        minf = neginf
    for d in dest:
        idx_nan = isnan(d)
        idx_posinf = isposinf(d)
        idx_neginf = isneginf(d)
        _nx.copyto(d, nan, where=idx_nan)
        _nx.copyto(d, maxf, where=idx_posinf)
        _nx.copyto(d, minf, where=idx_neginf)
    return x[()] if isscalar else x

#-----------------------------------------------------------------------------

def _real_if_close_dispatcher(a, tol=None):
    return (a,)


@array_function_dispatch(_real_if_close_dispatcher)
def real_if_close(a, tol=100):
    """
    If input is complex with all imaginary parts close to zero, return
    real parts.

    "Close to zero" is defined as `tol` * (machine epsilon of the type for
    `a`).

    Parameters
    ----------
    a : array_like
        Input array.
    tol : float
        Tolerance in machine epsilons for the complex part of the elements
        in the array. If the tolerance is <=1, then the absolute tolerance
        is used.

    Returns
    -------
    out : ndarray
        If `a` is real, the type of `a` is used for the output.  If `a`
        has complex elements, the returned type is float.

    See Also
    --------
    real, imag, angle

    Notes
    -----
    Machine epsilon varies from machine to machine and between data types
    but Python floats on most platforms have a machine epsilon equal to
    2.2204460492503131e-16.  You can use 'np.finfo(float).eps' to print
    out the machine epsilon for floats.

    Examples
    --------
    >>> import numpy as np
    >>> np.finfo(float).eps
    2.2204460492503131e-16 # may vary

    >>> np.real_if_close([2.1 + 4e-14j, 5.2 + 3e-15j], tol=1000)
    array([2.1, 5.2])
    >>> np.real_if_close([2.1 + 4e-13j, 5.2 + 3e-15j], tol=1000)
    array([2.1+4.e-13j, 5.2 + 3e-15j])

    """
    a = asanyarray(a)
    type_ = a.dtype.type
    if not issubclass(type_, _nx.complexfloating):
        return a
    if tol > 1:
        f = getlimits.finfo(type_)
        tol = f.eps * tol
    if _nx.all(_nx.absolute(a.imag) < tol):
        a = a.real
    return a


#-----------------------------------------------------------------------------

_namefromtype = {'S1': 'character',
                 '?': 'bool',
                 'b': 'signed char',
                 'B': 'unsigned char',
                 'h': 'short',
                 'H': 'unsigned short',
                 'i': 'integer',
                 'I': 'unsigned integer',
                 'l': 'long integer',
                 'L': 'unsigned long integer',
                 'q': 'long long integer',
                 'Q': 'unsigned long long integer',
                 'f': 'single precision',
                 'd': 'double precision',
                 'g': 'long precision',
                 'F': 'complex single precision',
                 'D': 'complex double precision',
                 'G': 'complex long double precision',
                 'S': 'string',
                 'U': 'unicode',
                 'V': 'void',
                 'O': 'object'
                 }

@set_module('numpy')
def typename(char):
    """
    Return a description for the given data type code.

    Parameters
    ----------
    char : str
        Data type code.

    Returns
    -------
    out : str
        Description of the input data type code.

    See Also
    --------
    dtype

    Examples
    --------
    >>> import numpy as np
    >>> typechars = ['S1', '?', 'B', 'D', 'G', 'F', 'I', 'H', 'L', 'O', 'Q',
    ...              'S', 'U', 'V', 'b', 'd', 'g', 'f', 'i', 'h', 'l', 'q']
    >>> for typechar in typechars:
    ...     print(typechar, ' : ', np.typename(typechar))
    ...
    S1  :  character
    ?  :  bool
    B  :  unsigned char
    D  :  complex double precision
    G  :  complex long double precision
    F  :  complex single precision
    I  :  unsigned integer
    H  :  unsigned short
    L  :  unsigned long integer
    O  :  object
    Q  :  unsigned long long integer
    S  :  string
    U  :  unicode
    V  :  void
    b  :  signed char
    d  :  double precision
    g  :  long precision
    f  :  single precision
    i  :  integer
    h  :  short
    l  :  long integer
    q  :  long long integer

    """
    return _namefromtype[char]

#-----------------------------------------------------------------------------


#determine the "minimum common type" for a group of arrays.
array_type = [[_nx.float16, _nx.float32, _nx.float64, _nx.longdouble],
              [None, _nx.complex64, _nx.complex128, _nx.clongdouble]]
array_precision = {_nx.float16: 0,
                   _nx.float32: 1,
                   _nx.float64: 2,
                   _nx.longdouble: 3,
                   _nx.complex64: 1,
                   _nx.complex128: 2,
                   _nx.clongdouble: 3}


def _common_type_dispatcher(*arrays):
    return arrays


@array_function_dispatch(_common_type_dispatcher)
def common_type(*arrays):
    """
    Return a scalar type which is common to the input arrays.

    The return type will always be an inexact (i.e. floating point) scalar
    type, even if all the arrays are integer arrays. If one of the inputs is
    an integer array, the minimum precision type that is returned is a
    64-bit floating point dtype.

    All input arrays except int64 and uint64 can be safely cast to the
    returned dtype without loss of information.

    Parameters
    ----------
    array1, array2, ... : ndarrays
        Input arrays.

    Returns
    -------
    out : data type code
        Data type code.

    See Also
    --------
    dtype, mintypecode

    Examples
    --------
    >>> np.common_type(np.arange(2, dtype=np.float32))
    <class 'numpy.float32'>
    >>> np.common_type(np.arange(2, dtype=np.float32), np.arange(2))
    <class 'numpy.float64'>
    >>> np.common_type(np.arange(4), np.array([45, 6.j]), np.array([45.0]))
    <class 'numpy.complex128'>

    """
    is_complex = False
    precision = 0
    for a in arrays:
        t = a.dtype.type
        if iscomplexobj(a):
            is_complex = True
        if issubclass(t, _nx.integer):
            p = 2  # array_precision[_nx.double]
        else:
            p = array_precision.get(t)
            if p is None:
                raise TypeError("can't get common type for non-numeric array")
        precision = max(precision, p)
    if is_complex:
        return array_type[1][precision]
    else:
        return array_type[0][precision]

# === NexusCore/openenv\Lib\site-packages\IPython\lib\display.py ===
"""Various display related classes.

Authors : MinRK, gregcaporaso, dannystaple
"""
from html import escape as html_escape
from os.path import exists, isfile, splitext, abspath, join, isdir
from os import walk, sep, fsdecode

from IPython.core.display import DisplayObject, TextDisplayObject

from typing import Tuple, Iterable, Optional

__all__ = ['Audio', 'IFrame', 'YouTubeVideo', 'VimeoVideo', 'ScribdDocument',
           'FileLink', 'FileLinks', 'Code']


class Audio(DisplayObject):
    """Create an audio object.

    When this object is returned by an input cell or passed to the
    display function, it will result in Audio controls being displayed
    in the frontend (only works in the notebook).

    Parameters
    ----------
    data : numpy array, list, unicode, str or bytes
        Can be one of

          * Numpy 1d array containing the desired waveform (mono)
          * Numpy 2d array containing waveforms for each channel.
            Shape=(NCHAN, NSAMPLES). For the standard channel order, see
            http://msdn.microsoft.com/en-us/library/windows/hardware/dn653308(v=vs.85).aspx
          * List of float or integer representing the waveform (mono)
          * String containing the filename
          * Bytestring containing raw PCM data or
          * URL pointing to a file on the web.

        If the array option is used, the waveform will be normalized.

        If a filename or url is used, the format support will be browser
        dependent.
    url : unicode
        A URL to download the data from.
    filename : unicode
        Path to a local file to load the data from.
    embed : boolean
        Should the audio data be embedded using a data URI (True) or should
        the original source be referenced. Set this to True if you want the
        audio to playable later with no internet connection in the notebook.

        Default is `True`, unless the keyword argument `url` is set, then
        default value is `False`.
    rate : integer
        The sampling rate of the raw data.
        Only required when data parameter is being used as an array
    autoplay : bool
        Set to True if the audio should immediately start playing.
        Default is `False`.
    normalize : bool
        Whether audio should be normalized (rescaled) to the maximum possible
        range. Default is `True`. When set to `False`, `data` must be between
        -1 and 1 (inclusive), otherwise an error is raised.
        Applies only when `data` is a list or array of samples; other types of
        audio are never normalized.

    Examples
    --------

    >>> import pytest
    >>> np = pytest.importorskip("numpy")

    Generate a sound

    >>> import numpy as np
    >>> framerate = 44100
    >>> t = np.linspace(0,5,framerate*5)
    >>> data = np.sin(2*np.pi*220*t) + np.sin(2*np.pi*224*t)
    >>> Audio(data, rate=framerate)
    <IPython.lib.display.Audio object>

    Can also do stereo or more channels

    >>> dataleft = np.sin(2*np.pi*220*t)
    >>> dataright = np.sin(2*np.pi*224*t)
    >>> Audio([dataleft, dataright], rate=framerate)
    <IPython.lib.display.Audio object>

    From URL:

    >>> Audio("http://www.nch.com.au/acm/8k16bitpcm.wav")  # doctest: +SKIP
    >>> Audio(url="http://www.w3schools.com/html/horse.ogg")  # doctest: +SKIP

    From a File:

    >>> Audio('IPython/lib/tests/test.wav')  # doctest: +SKIP
    >>> Audio(filename='IPython/lib/tests/test.wav')  # doctest: +SKIP

    From Bytes:

    >>> Audio(b'RAW_WAV_DATA..')  # doctest: +SKIP
    >>> Audio(data=b'RAW_WAV_DATA..')  # doctest: +SKIP

    See Also
    --------
    ipywidgets.Audio

         Audio widget with more more flexibility and options.

    """
    _read_flags = 'rb'

    def __init__(self, data=None, filename=None, url=None, embed=None, rate=None, autoplay=False, normalize=True, *,
                 element_id=None):
        if filename is None and url is None and data is None:
            raise ValueError("No audio data found. Expecting filename, url, or data.")
        if embed is False and url is None:
            raise ValueError("No url found. Expecting url when embed=False")

        if url is not None and embed is not True:
            self.embed = False
        else:
            self.embed = True
        self.autoplay = autoplay
        self.element_id = element_id
        super(Audio, self).__init__(data=data, url=url, filename=filename)

        if self.data is not None and not isinstance(self.data, bytes):
            if rate is None:
                raise ValueError("rate must be specified when data is a numpy array or list of audio samples.")
            self.data = Audio._make_wav(data, rate, normalize)

    def reload(self):
        """Reload the raw data from file or URL."""
        import mimetypes
        if self.embed:
            super(Audio, self).reload()

        if self.filename is not None:
            self.mimetype = mimetypes.guess_type(self.filename)[0]
        elif self.url is not None:
            self.mimetype = mimetypes.guess_type(self.url)[0]
        else:
            self.mimetype = "audio/wav"

    @staticmethod
    def _make_wav(data, rate, normalize):
        """ Transform a numpy array to a PCM bytestring """
        from io import BytesIO
        import wave

        try:
            scaled, nchan = Audio._validate_and_normalize_with_numpy(data, normalize)
        except ImportError:
            scaled, nchan = Audio._validate_and_normalize_without_numpy(data, normalize)

        fp = BytesIO()
        waveobj = wave.open(fp,mode='wb')
        waveobj.setnchannels(nchan)
        waveobj.setframerate(rate)
        waveobj.setsampwidth(2)
        waveobj.setcomptype('NONE','NONE')
        waveobj.writeframes(scaled)
        val = fp.getvalue()
        waveobj.close()

        return val

    @staticmethod
    def _validate_and_normalize_with_numpy(data, normalize) -> Tuple[bytes, int]:
        import numpy as np

        data = np.array(data, dtype=float)
        if len(data.shape) == 1:
            nchan = 1
        elif len(data.shape) == 2:
            # In wave files,channels are interleaved. E.g.,
            # "L1R1L2R2..." for stereo. See
            # http://msdn.microsoft.com/en-us/library/windows/hardware/dn653308(v=vs.85).aspx
            # for channel ordering
            nchan = data.shape[0]
            data = data.T.ravel()
        else:
            raise ValueError('Array audio input must be a 1D or 2D array')
        
        max_abs_value = np.max(np.abs(data))
        normalization_factor = Audio._get_normalization_factor(max_abs_value, normalize)
        scaled = data / normalization_factor * 32767
        return scaled.astype("<h").tobytes(), nchan

    @staticmethod
    def _validate_and_normalize_without_numpy(data, normalize):
        import array
        import sys

        data = array.array('f', data)

        try:
            max_abs_value = float(max([abs(x) for x in data]))
        except TypeError as e:
            raise TypeError('Only lists of mono audio are '
                'supported if numpy is not installed') from e

        normalization_factor = Audio._get_normalization_factor(max_abs_value, normalize)
        scaled = array.array('h', [int(x / normalization_factor * 32767) for x in data])
        if sys.byteorder == 'big':
            scaled.byteswap()
        nchan = 1
        return scaled.tobytes(), nchan

    @staticmethod
    def _get_normalization_factor(max_abs_value, normalize):
        if not normalize and max_abs_value > 1:
            raise ValueError('Audio data must be between -1 and 1 when normalize=False.')
        return max_abs_value if normalize else 1

    def _data_and_metadata(self):
        """shortcut for returning metadata with url information, if defined"""
        md = {}
        if self.url:
            md['url'] = self.url
        if md:
            return self.data, md
        else:
            return self.data

    def _repr_html_(self):
        src = """
                <audio {element_id} controls="controls" {autoplay}>
                    <source src="{src}" type="{type}" />
                    Your browser does not support the audio element.
                </audio>
              """
        return src.format(src=self.src_attr(), type=self.mimetype, autoplay=self.autoplay_attr(),
                          element_id=self.element_id_attr())

    def src_attr(self):
        import base64
        if self.embed and (self.data is not None):
            data = base64=base64.b64encode(self.data).decode('ascii')
            return """data:{type};base64,{base64}""".format(type=self.mimetype,
                                                            base64=data)
        elif self.url is not None:
            return self.url
        else:
            return ""

    def autoplay_attr(self):
        if(self.autoplay):
            return 'autoplay="autoplay"'
        else:
            return ''
    
    def element_id_attr(self):
        if (self.element_id):
            return 'id="{element_id}"'.format(element_id=self.element_id)
        else:
            return ''

class IFrame:
    """
    Generic class to embed an iframe in an IPython notebook
    """

    iframe = """
        <iframe
            width="{width}"
            height="{height}"
            src="{src}{params}"
            frameborder="0"
            allowfullscreen
            {extras}
        ></iframe>
        """

    def __init__(
        self, src, width, height, extras: Optional[Iterable[str]] = None, **kwargs
    ):
        if extras is None:
            extras = []

        self.src = src
        self.width = width
        self.height = height
        self.extras = extras
        self.params = kwargs

    def _repr_html_(self):
        """return the embed iframe"""
        if self.params:
            from urllib.parse import urlencode
            params = "?" + urlencode(self.params)
        else:
            params = ""
        return self.iframe.format(
            src=self.src,
            width=self.width,
            height=self.height,
            params=params,
            extras=" ".join(self.extras),
        )


class YouTubeVideo(IFrame):
    """Class for embedding a YouTube Video in an IPython session, based on its video id.

    e.g. to embed the video from https://www.youtube.com/watch?v=foo , you would
    do::

        vid = YouTubeVideo("foo")
        display(vid)

    To start from 30 seconds::

        vid = YouTubeVideo("abc", start=30)
        display(vid)

    To calculate seconds from time as hours, minutes, seconds use
    :class:`datetime.timedelta`::

        start=int(timedelta(hours=1, minutes=46, seconds=40).total_seconds())

    Other parameters can be provided as documented at
    https://developers.google.com/youtube/player_parameters#Parameters
    
    When converting the notebook using nbconvert, a jpeg representation of the video
    will be inserted in the document.
    """

    def __init__(self, id, width=400, height=300, allow_autoplay=False, **kwargs):
        self.id=id
        src = "https://www.youtube.com/embed/{0}".format(id)
        if allow_autoplay:
            extras = list(kwargs.get("extras", [])) + ['allow="autoplay"']
            kwargs.update(autoplay=1, extras=extras)
        super(YouTubeVideo, self).__init__(src, width, height, **kwargs)

    def _repr_jpeg_(self):
        # Deferred import
        from urllib.request import urlopen

        try:
            return urlopen("https://img.youtube.com/vi/{id}/hqdefault.jpg".format(id=self.id)).read()
        except IOError:
            return None

class VimeoVideo(IFrame):
    """
    Class for embedding a Vimeo video in an IPython session, based on its video id.
    """

    def __init__(self, id, width=400, height=300, **kwargs):
        src="https://player.vimeo.com/video/{0}".format(id)
        super(VimeoVideo, self).__init__(src, width, height, **kwargs)

class ScribdDocument(IFrame):
    """
    Class for embedding a Scribd document in an IPython session

    Use the start_page params to specify a starting point in the document
    Use the view_mode params to specify display type one off scroll | slideshow | book

    e.g to Display Wes' foundational paper about PANDAS in book mode from page 3

    ScribdDocument(71048089, width=800, height=400, start_page=3, view_mode="book")
    """

    def __init__(self, id, width=400, height=300, **kwargs):
        src="https://www.scribd.com/embeds/{0}/content".format(id)
        super(ScribdDocument, self).__init__(src, width, height, **kwargs)

class FileLink:
    """Class for embedding a local file link in an IPython session, based on path

    e.g. to embed a link that was generated in the IPython notebook as my/data.txt

    you would do::

        local_file = FileLink("my/data.txt")
        display(local_file)

    or in the HTML notebook, just::

        FileLink("my/data.txt")
    """

    html_link_str = "<a href='%s' target='_blank'>%s</a>"

    def __init__(self,
                 path,
                 url_prefix='',
                 result_html_prefix='',
                 result_html_suffix='<br>'):
        """
        Parameters
        ----------
        path : str
            path to the file or directory that should be formatted
        url_prefix : str
            prefix to be prepended to all files to form a working link [default:
            '']
        result_html_prefix : str
            text to append to beginning to link [default: '']
        result_html_suffix : str
            text to append at the end of link [default: '<br>']
        """
        if isdir(path):
            raise ValueError("Cannot display a directory using FileLink. "
              "Use FileLinks to display '%s'." % path)
        self.path = fsdecode(path)
        self.url_prefix = url_prefix
        self.result_html_prefix = result_html_prefix
        self.result_html_suffix = result_html_suffix

    def _format_path(self):
        fp = ''.join([self.url_prefix, html_escape(self.path)])
        return ''.join([self.result_html_prefix,
                        self.html_link_str % \
                            (fp, html_escape(self.path, quote=False)),
                        self.result_html_suffix])

    def _repr_html_(self):
        """return html link to file
        """
        if not exists(self.path):
            return ("Path (<tt>%s</tt>) doesn't exist. "
                    "It may still be in the process of "
                    "being generated, or you may have the "
                    "incorrect path." % self.path)

        return self._format_path()

    def __repr__(self):
        """return absolute path to file
        """
        return abspath(self.path)

class FileLinks(FileLink):
    """Class for embedding local file links in an IPython session, based on path

    e.g. to embed links to files that were generated in the IPython notebook
    under ``my/data``, you would do::

        local_files = FileLinks("my/data")
        display(local_files)

    or in the HTML notebook, just::

        FileLinks("my/data")
    """
    def __init__(self,
                 path,
                 url_prefix='',
                 included_suffixes=None,
                 result_html_prefix='',
                 result_html_suffix='<br>',
                 notebook_display_formatter=None,
                 terminal_display_formatter=None,
                 recursive=True):
        """
        See :class:`FileLink` for the ``path``, ``url_prefix``,
        ``result_html_prefix`` and ``result_html_suffix`` parameters.

        included_suffixes : list
          Filename suffixes to include when formatting output [default: include
          all files]

        notebook_display_formatter : function
          Used to format links for display in the notebook. See discussion of
          formatter functions below.

        terminal_display_formatter : function
          Used to format links for display in the terminal. See discussion of
          formatter functions below.

        Formatter functions must be of the form::

            f(dirname, fnames, included_suffixes)

        dirname : str
          The name of a directory
        fnames : list
          The files in that directory
        included_suffixes : list
          The file suffixes that should be included in the output (passing None
          meansto include all suffixes in the output in the built-in formatters)
        recursive : boolean
          Whether to recurse into subdirectories. Default is True.

        The function should return a list of lines that will be printed in the
        notebook (if passing notebook_display_formatter) or the terminal (if
        passing terminal_display_formatter). This function is iterated over for
        each directory in self.path. Default formatters are in place, can be
        passed here to support alternative formatting.

        """
        if isfile(path):
            raise ValueError("Cannot display a file using FileLinks. "
              "Use FileLink to display '%s'." % path)
        self.included_suffixes = included_suffixes
        # remove trailing slashes for more consistent output formatting
        path = path.rstrip('/')

        self.path = path
        self.url_prefix = url_prefix
        self.result_html_prefix = result_html_prefix
        self.result_html_suffix = result_html_suffix

        self.notebook_display_formatter = \
             notebook_display_formatter or self._get_notebook_display_formatter()
        self.terminal_display_formatter = \
             terminal_display_formatter or self._get_terminal_display_formatter()

        self.recursive = recursive

    def _get_display_formatter(
        self, dirname_output_format, fname_output_format, fp_format, fp_cleaner=None
    ):
        """generate built-in formatter function

        this is used to define both the notebook and terminal built-in
         formatters as they only differ by some wrapper text for each entry

        dirname_output_format: string to use for formatting directory
         names, dirname will be substituted for a single "%s" which
         must appear in this string
        fname_output_format: string to use for formatting file names,
         if a single "%s" appears in the string, fname will be substituted
         if two "%s" appear in the string, the path to fname will be
          substituted for the first and fname will be substituted for the
          second
        fp_format: string to use for formatting filepaths, must contain
         exactly two "%s" and the dirname will be substituted for the first
         and fname will be substituted for the second
        """
        def f(dirname, fnames, included_suffixes=None):
            result = []
            # begin by figuring out which filenames, if any,
            # are going to be displayed
            display_fnames = []
            for fname in fnames:
                if (isfile(join(dirname,fname)) and
                       (included_suffixes is None or
                        splitext(fname)[1] in included_suffixes)):
                      display_fnames.append(fname)

            if len(display_fnames) == 0:
                # if there are no filenames to display, don't print anything
                # (not even the directory name)
                pass
            else:
                # otherwise print the formatted directory name followed by
                # the formatted filenames
                dirname_output_line = dirname_output_format % dirname
                result.append(dirname_output_line)
                for fname in display_fnames:
                    fp = fp_format % (dirname,fname)
                    if fp_cleaner is not None:
                        fp = fp_cleaner(fp)
                    try:
                        # output can include both a filepath and a filename...
                        fname_output_line = fname_output_format % (fp, fname)
                    except TypeError:
                        # ... or just a single filepath
                        fname_output_line = fname_output_format % fname
                    result.append(fname_output_line)
            return result
        return f

    def _get_notebook_display_formatter(self,
                                        spacer="&nbsp;&nbsp;"):
        """ generate function to use for notebook formatting
        """
        dirname_output_format = \
         self.result_html_prefix + "%s/" + self.result_html_suffix
        fname_output_format = \
         self.result_html_prefix + spacer + self.html_link_str + self.result_html_suffix
        fp_format = self.url_prefix + '%s/%s'
        if sep == "\\":
            # Working on a platform where the path separator is "\", so
            # must convert these to "/" for generating a URI
            def fp_cleaner(fp):
                # Replace all occurrences of backslash ("\") with a forward
                # slash ("/") - this is necessary on windows when a path is
                # provided as input, but we must link to a URI
                return fp.replace('\\','/')
        else:
            fp_cleaner = None

        return self._get_display_formatter(dirname_output_format,
                                           fname_output_format,
                                           fp_format,
                                           fp_cleaner)

    def _get_terminal_display_formatter(self,
                                        spacer="  "):
        """ generate function to use for terminal formatting
        """
        dirname_output_format = "%s/"
        fname_output_format = spacer + "%s"
        fp_format = '%s/%s'

        return self._get_display_formatter(dirname_output_format,
                                           fname_output_format,
                                           fp_format)

    def _format_path(self):
        result_lines = []
        if self.recursive:
            walked_dir = list(walk(self.path))
        else:
            walked_dir = [next(walk(self.path))]
        walked_dir.sort()
        for dirname, subdirs, fnames in walked_dir:
            result_lines += self.notebook_display_formatter(dirname, fnames, self.included_suffixes)
        return '\n'.join(result_lines)

    def __repr__(self):
        """return newline-separated absolute paths
        """
        result_lines = []
        if self.recursive:
            walked_dir = list(walk(self.path))
        else:
            walked_dir = [next(walk(self.path))]
        walked_dir.sort()
        for dirname, subdirs, fnames in walked_dir:
            result_lines += self.terminal_display_formatter(dirname, fnames, self.included_suffixes)
        return '\n'.join(result_lines)


class Code(TextDisplayObject):
    """Display syntax-highlighted source code.

    This uses Pygments to highlight the code for HTML and Latex output.

    Parameters
    ----------
    data : str
        The code as a string
    url : str
        A URL to fetch the code from
    filename : str
        A local filename to load the code from
    language : str
        The short name of a Pygments lexer to use for highlighting.
        If not specified, it will guess the lexer based on the filename
        or the code. Available lexers: http://pygments.org/docs/lexers/
    """
    def __init__(self, data=None, url=None, filename=None, language=None):
        self.language = language
        super().__init__(data=data, url=url, filename=filename)

    def _get_lexer(self):
        if self.language:
            from pygments.lexers import get_lexer_by_name
            return get_lexer_by_name(self.language)
        elif self.filename:
            from pygments.lexers import get_lexer_for_filename
            return get_lexer_for_filename(self.filename)
        else:
            from pygments.lexers import guess_lexer
            return guess_lexer(self.data)

    def __repr__(self):
        return self.data

    def _repr_html_(self):
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        fmt = HtmlFormatter()
        style = '<style>{}</style>'.format(fmt.get_style_defs('.output_html'))
        return style + highlight(self.data, self._get_lexer(), fmt)

    def _repr_latex_(self):
        from pygments import highlight
        from pygments.formatters import LatexFormatter
        return highlight(self.data, self._get_lexer(), LatexFormatter())