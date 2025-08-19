
# === NexusCore/openenv\Lib\site-packages\IPython\lib\deepreload.py ===
# -*- coding: utf-8 -*-
"""
Provides a reload() function that acts recursively.

Python's normal :func:`python:reload` function only reloads the module that it's
passed. The :func:`reload` function in this module also reloads everything
imported from that module, which is useful when you're changing files deep
inside a package.

To use this as your default reload function, type this::

    import builtins
    from IPython.lib import deepreload
    builtins.reload = deepreload.reload

A reference to the original :func:`python:reload` is stored in this module as
:data:`original_reload`, so you can restore it later.

This code is almost entirely based on knee.py, which is a Python
re-implementation of hierarchical module import.
"""
#*****************************************************************************
#       Copyright (C) 2001 Nathaniel Gray <n8gray@caltech.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import builtins as builtin_mod
from contextlib import contextmanager
import importlib
import sys

from types import ModuleType
from warnings import warn
import types

original_import = builtin_mod.__import__

@contextmanager
def replace_import_hook(new_import):
    saved_import = builtin_mod.__import__
    builtin_mod.__import__ = new_import
    try:
        yield
    finally:
        builtin_mod.__import__ = saved_import

def get_parent(globals, level):
    """
    parent, name = get_parent(globals, level)

    Return the package that an import is being performed in.  If globals comes
    from the module foo.bar.bat (not itself a package), this returns the
    sys.modules entry for foo.bar.  If globals is from a package's __init__.py,
    the package's entry in sys.modules is returned.

    If globals doesn't come from a package or a module in a package, or a
    corresponding entry is not found in sys.modules, None is returned.
    """
    orig_level = level

    if not level or not isinstance(globals, dict):
        return None, ''

    pkgname = globals.get('__package__', None)

    if pkgname is not None:
        # __package__ is set, so use it
        if not hasattr(pkgname, 'rindex'):
            raise ValueError('__package__ set to non-string')
        if len(pkgname) == 0:
            if level > 0:
                raise ValueError('Attempted relative import in non-package')
            return None, ''
        name = pkgname
    else:
        # __package__ not set, so figure it out and set it
        if '__name__' not in globals:
            return None, ''
        modname = globals['__name__']

        if '__path__' in globals:
            # __path__ is set, so modname is already the package name
            globals['__package__'] = name = modname
        else:
            # Normal module, so work out the package name if any
            lastdot = modname.rfind('.')
            if lastdot < 0 < level:
                raise ValueError("Attempted relative import in non-package")
            if lastdot < 0:
                globals['__package__'] = None
                return None, ''
            globals['__package__'] = name = modname[:lastdot]

    dot = len(name)
    for x in range(level, 1, -1):
        try:
            dot = name.rindex('.', 0, dot)
        except ValueError as e:
            raise ValueError("attempted relative import beyond top-level "
                             "package") from e
    name = name[:dot]

    try:
        parent = sys.modules[name]
    except BaseException as e:
        if orig_level < 1:
            warn("Parent module '%.200s' not found while handling absolute "
                 "import" % name)
            parent = None
        else:
            raise SystemError("Parent module '%.200s' not loaded, cannot "
                              "perform relative import" % name) from e

    # We expect, but can't guarantee, if parent != None, that:
    # - parent.__name__ == name
    # - parent.__dict__ is globals
    # If this is violated...  Who cares?
    return parent, name

def load_next(mod, altmod, name, buf):
    """
    mod, name, buf = load_next(mod, altmod, name, buf)

    altmod is either None or same as mod
    """

    if len(name) == 0:
        # completely empty module name should only happen in
        # 'from . import' (or '__import__("")')
        return mod, None, buf

    dot = name.find('.')
    if dot == 0:
        raise ValueError('Empty module name')

    if dot < 0:
        subname = name
        next = None
    else:
        subname = name[:dot]
        next = name[dot+1:]

    if buf != '':
        buf += '.'
    buf += subname

    result = import_submodule(mod, subname, buf)
    if result is None and mod != altmod:
        result = import_submodule(altmod, subname, subname)
        if result is not None:
            buf = subname

    if result is None:
        raise ImportError("No module named %.200s" % name)

    return result, next, buf


# Need to keep track of what we've already reloaded to prevent cyclic evil
found_now = {}

def import_submodule(mod, subname, fullname):
    """m = import_submodule(mod, subname, fullname)"""
    # Require:
    # if mod == None: subname == fullname
    # else: mod.__name__ + "." + subname == fullname

    global found_now
    if fullname in found_now and fullname in sys.modules:
        m = sys.modules[fullname]
    else:
        print('Reloading', fullname)
        found_now[fullname] = 1
        oldm = sys.modules.get(fullname, None)
        try:
            if oldm is not None:
                m = importlib.reload(oldm)
            else:
                m = importlib.import_module(subname, mod)
        except:
            # load_module probably removed name from modules because of
            # the error.  Put back the original module object.
            if oldm:
                sys.modules[fullname] = oldm
            raise

        add_submodule(mod, m, fullname, subname)

    return m

def add_submodule(mod, submod, fullname, subname):
    """mod.{subname} = submod"""
    if mod is None:
        return #Nothing to do here.

    if submod is None:
        submod = sys.modules[fullname]

    setattr(mod, subname, submod)

    return

def ensure_fromlist(mod, fromlist, buf, recursive):
    """Handle 'from module import a, b, c' imports."""
    if not hasattr(mod, '__path__'):
        return
    for item in fromlist:
        if not hasattr(item, 'rindex'):
            raise TypeError("Item in ``from list'' not a string")
        if item == '*':
            if recursive:
                continue # avoid endless recursion
            try:
                all = mod.__all__
            except AttributeError:
                pass
            else:
                ret = ensure_fromlist(mod, all, buf, 1)
                if not ret:
                    return 0
        elif not hasattr(mod, item):
            import_submodule(mod, item, buf + '.' + item)

def deep_import_hook(name, globals=None, locals=None, fromlist=None, level=-1):
    """Replacement for __import__()"""
    parent, buf = get_parent(globals, level)

    head, name, buf = load_next(parent, None if level < 0 else parent, name, buf)

    tail = head
    while name:
        tail, name, buf = load_next(tail, tail, name, buf)

    # If tail is None, both get_parent and load_next found
    # an empty module name: someone called __import__("") or
    # doctored faulty bytecode
    if tail is None:
        raise ValueError('Empty module name')

    if not fromlist:
        return head

    ensure_fromlist(tail, fromlist, buf, 0)
    return tail

modules_reloading = {}

def deep_reload_hook(m):
    """Replacement for reload()."""
    # Hardcode this one  as it would raise a NotImplementedError from the
    # bowels of Python and screw up the import machinery after.
    # unlike other imports the `exclude` list already in place is not enough.

    if m is types:
        return m
    if not isinstance(m, ModuleType):
        raise TypeError("reload() argument must be module")

    name = m.__name__

    if name not in sys.modules:
        raise ImportError("reload(): module %.200s not in sys.modules" % name)

    global modules_reloading
    try:
        return modules_reloading[name]
    except:
        modules_reloading[name] = m

    try:
        newm = importlib.reload(m)
    except:
        sys.modules[name] = m
        raise
    finally:
        modules_reloading.clear()
    return newm

# Save the original hooks
original_reload = importlib.reload

# Replacement for reload()
def reload(
    module,
    exclude=(
        *sys.builtin_module_names,
        "sys",
        "os.path",
        "builtins",
        "__main__",
        "numpy",
        "numpy._globals",
    ),
):
    """Recursively reload all modules used in the given module.  Optionally
    takes a list of modules to exclude from reloading.  The default exclude
    list contains modules listed in sys.builtin_module_names with additional
    sys, os.path, builtins and __main__, to prevent, e.g., resetting
    display, exception, and io hooks.
    """
    global found_now
    for i in exclude:
        found_now[i] = 1
    try:
        with replace_import_hook(deep_import_hook):
            return deep_reload_hook(module)
    finally:
        found_now = {}

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\lib\deepreload.py ===
# -*- coding: utf-8 -*-
"""
Provides a reload() function that acts recursively.

Python's normal :func:`python:reload` function only reloads the module that it's
passed. The :func:`reload` function in this module also reloads everything
imported from that module, which is useful when you're changing files deep
inside a package.

To use this as your default reload function, type this::

    import builtins
    from IPython.lib import deepreload
    builtins.reload = deepreload.reload

A reference to the original :func:`python:reload` is stored in this module as
:data:`original_reload`, so you can restore it later.

This code is almost entirely based on knee.py, which is a Python
re-implementation of hierarchical module import.
"""
#*****************************************************************************
#       Copyright (C) 2001 Nathaniel Gray <n8gray@caltech.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import builtins as builtin_mod
from contextlib import contextmanager
import importlib
import sys

from types import ModuleType
from warnings import warn
import types

original_import = builtin_mod.__import__

@contextmanager
def replace_import_hook(new_import):
    saved_import = builtin_mod.__import__
    builtin_mod.__import__ = new_import
    try:
        yield
    finally:
        builtin_mod.__import__ = saved_import

def get_parent(globals, level):
    """
    parent, name = get_parent(globals, level)

    Return the package that an import is being performed in.  If globals comes
    from the module foo.bar.bat (not itself a package), this returns the
    sys.modules entry for foo.bar.  If globals is from a package's __init__.py,
    the package's entry in sys.modules is returned.

    If globals doesn't come from a package or a module in a package, or a
    corresponding entry is not found in sys.modules, None is returned.
    """
    orig_level = level

    if not level or not isinstance(globals, dict):
        return None, ''

    pkgname = globals.get('__package__', None)

    if pkgname is not None:
        # __package__ is set, so use it
        if not hasattr(pkgname, 'rindex'):
            raise ValueError('__package__ set to non-string')
        if len(pkgname) == 0:
            if level > 0:
                raise ValueError('Attempted relative import in non-package')
            return None, ''
        name = pkgname
    else:
        # __package__ not set, so figure it out and set it
        if '__name__' not in globals:
            return None, ''
        modname = globals['__name__']

        if '__path__' in globals:
            # __path__ is set, so modname is already the package name
            globals['__package__'] = name = modname
        else:
            # Normal module, so work out the package name if any
            lastdot = modname.rfind('.')
            if lastdot < 0 < level:
                raise ValueError("Attempted relative import in non-package")
            if lastdot < 0:
                globals['__package__'] = None
                return None, ''
            globals['__package__'] = name = modname[:lastdot]

    dot = len(name)
    for x in range(level, 1, -1):
        try:
            dot = name.rindex('.', 0, dot)
        except ValueError as e:
            raise ValueError("attempted relative import beyond top-level "
                             "package") from e
    name = name[:dot]

    try:
        parent = sys.modules[name]
    except BaseException as e:
        if orig_level < 1:
            warn("Parent module '%.200s' not found while handling absolute "
                 "import" % name)
            parent = None
        else:
            raise SystemError("Parent module '%.200s' not loaded, cannot "
                              "perform relative import" % name) from e

    # We expect, but can't guarantee, if parent != None, that:
    # - parent.__name__ == name
    # - parent.__dict__ is globals
    # If this is violated...  Who cares?
    return parent, name

def load_next(mod, altmod, name, buf):
    """
    mod, name, buf = load_next(mod, altmod, name, buf)

    altmod is either None or same as mod
    """

    if len(name) == 0:
        # completely empty module name should only happen in
        # 'from . import' (or '__import__("")')
        return mod, None, buf

    dot = name.find('.')
    if dot == 0:
        raise ValueError('Empty module name')

    if dot < 0:
        subname = name
        next = None
    else:
        subname = name[:dot]
        next = name[dot+1:]

    if buf != '':
        buf += '.'
    buf += subname

    result = import_submodule(mod, subname, buf)
    if result is None and mod != altmod:
        result = import_submodule(altmod, subname, subname)
        if result is not None:
            buf = subname

    if result is None:
        raise ImportError("No module named %.200s" % name)

    return result, next, buf


# Need to keep track of what we've already reloaded to prevent cyclic evil
found_now = {}

def import_submodule(mod, subname, fullname):
    """m = import_submodule(mod, subname, fullname)"""
    # Require:
    # if mod == None: subname == fullname
    # else: mod.__name__ + "." + subname == fullname

    global found_now
    if fullname in found_now and fullname in sys.modules:
        m = sys.modules[fullname]
    else:
        print('Reloading', fullname)
        found_now[fullname] = 1
        oldm = sys.modules.get(fullname, None)
        try:
            if oldm is not None:
                m = importlib.reload(oldm)
            else:
                m = importlib.import_module(subname, mod)
        except:
            # load_module probably removed name from modules because of
            # the error.  Put back the original module object.
            if oldm:
                sys.modules[fullname] = oldm
            raise

        add_submodule(mod, m, fullname, subname)

    return m

def add_submodule(mod, submod, fullname, subname):
    """mod.{subname} = submod"""
    if mod is None:
        return #Nothing to do here.

    if submod is None:
        submod = sys.modules[fullname]

    setattr(mod, subname, submod)

    return

def ensure_fromlist(mod, fromlist, buf, recursive):
    """Handle 'from module import a, b, c' imports."""
    if not hasattr(mod, '__path__'):
        return
    for item in fromlist:
        if not hasattr(item, 'rindex'):
            raise TypeError("Item in ``from list'' not a string")
        if item == '*':
            if recursive:
                continue # avoid endless recursion
            try:
                all = mod.__all__
            except AttributeError:
                pass
            else:
                ret = ensure_fromlist(mod, all, buf, 1)
                if not ret:
                    return 0
        elif not hasattr(mod, item):
            import_submodule(mod, item, buf + '.' + item)

def deep_import_hook(name, globals=None, locals=None, fromlist=None, level=-1):
    """Replacement for __import__()"""
    parent, buf = get_parent(globals, level)

    head, name, buf = load_next(parent, None if level < 0 else parent, name, buf)

    tail = head
    while name:
        tail, name, buf = load_next(tail, tail, name, buf)

    # If tail is None, both get_parent and load_next found
    # an empty module name: someone called __import__("") or
    # doctored faulty bytecode
    if tail is None:
        raise ValueError('Empty module name')

    if not fromlist:
        return head

    ensure_fromlist(tail, fromlist, buf, 0)
    return tail

modules_reloading = {}

def deep_reload_hook(m):
    """Replacement for reload()."""
    # Hardcode this one  as it would raise a NotImplementedError from the
    # bowels of Python and screw up the import machinery after.
    # unlike other imports the `exclude` list already in place is not enough.

    if m is types:
        return m
    if not isinstance(m, ModuleType):
        raise TypeError("reload() argument must be module")

    name = m.__name__

    if name not in sys.modules:
        raise ImportError("reload(): module %.200s not in sys.modules" % name)

    global modules_reloading
    try:
        return modules_reloading[name]
    except:
        modules_reloading[name] = m

    try:
        newm = importlib.reload(m)
    except:
        sys.modules[name] = m
        raise
    finally:
        modules_reloading.clear()
    return newm

# Save the original hooks
original_reload = importlib.reload

# Replacement for reload()
def reload(
    module,
    exclude=(
        *sys.builtin_module_names,
        "sys",
        "os.path",
        "builtins",
        "__main__",
        "numpy",
        "numpy._globals",
    ),
):
    """Recursively reload all modules used in the given module.  Optionally
    takes a list of modules to exclude from reloading.  The default exclude
    list contains modules listed in sys.builtin_module_names with additional
    sys, os.path, builtins and __main__, to prevent, e.g., resetting
    display, exception, and io hooks.
    """
    global found_now
    for i in exclude:
        found_now[i] = 1
    try:
        with replace_import_hook(deep_import_hook):
            return deep_reload_hook(module)
    finally:
        found_now = {}

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_user_array_impl.py ===
"""
Container class for backward compatibility with NumArray.

The user_array.container class exists for backward compatibility with NumArray
and is not meant to be used in new code. If you need to create an array
container class, we recommend either creating a class that wraps an ndarray
or subclasses ndarray.

"""
from numpy._core import (
    absolute,
    add,
    arange,
    array,
    asarray,
    bitwise_and,
    bitwise_or,
    bitwise_xor,
    divide,
    equal,
    greater,
    greater_equal,
    invert,
    left_shift,
    less,
    less_equal,
    multiply,
    not_equal,
    power,
    remainder,
    reshape,
    right_shift,
    shape,
    sin,
    sqrt,
    subtract,
    transpose,
)
from numpy._core.overrides import set_module


@set_module("numpy.lib.user_array")
class container:
    """
    container(data, dtype=None, copy=True)

    Standard container-class for easy multiple-inheritance.

    Methods
    -------
    copy
    byteswap
    astype

    """
    def __init__(self, data, dtype=None, copy=True):
        self.array = array(data, dtype, copy=copy)

    def __repr__(self):
        if self.ndim > 0:
            return self.__class__.__name__ + repr(self.array)[len("array"):]
        else:
            return self.__class__.__name__ + "(" + repr(self.array) + ")"

    def __array__(self, t=None):
        if t:
            return self.array.astype(t)
        return self.array

    # Array as sequence
    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        return self._rc(self.array[index])

    def __setitem__(self, index, value):
        self.array[index] = asarray(value, self.dtype)

    def __abs__(self):
        return self._rc(absolute(self.array))

    def __neg__(self):
        return self._rc(-self.array)

    def __add__(self, other):
        return self._rc(self.array + asarray(other))

    __radd__ = __add__

    def __iadd__(self, other):
        add(self.array, other, self.array)
        return self

    def __sub__(self, other):
        return self._rc(self.array - asarray(other))

    def __rsub__(self, other):
        return self._rc(asarray(other) - self.array)

    def __isub__(self, other):
        subtract(self.array, other, self.array)
        return self

    def __mul__(self, other):
        return self._rc(multiply(self.array, asarray(other)))

    __rmul__ = __mul__

    def __imul__(self, other):
        multiply(self.array, other, self.array)
        return self

    def __mod__(self, other):
        return self._rc(remainder(self.array, other))

    def __rmod__(self, other):
        return self._rc(remainder(other, self.array))

    def __imod__(self, other):
        remainder(self.array, other, self.array)
        return self

    def __divmod__(self, other):
        return (self._rc(divide(self.array, other)),
                self._rc(remainder(self.array, other)))

    def __rdivmod__(self, other):
        return (self._rc(divide(other, self.array)),
                self._rc(remainder(other, self.array)))

    def __pow__(self, other):
        return self._rc(power(self.array, asarray(other)))

    def __rpow__(self, other):
        return self._rc(power(asarray(other), self.array))

    def __ipow__(self, other):
        power(self.array, other, self.array)
        return self

    def __lshift__(self, other):
        return self._rc(left_shift(self.array, other))

    def __rshift__(self, other):
        return self._rc(right_shift(self.array, other))

    def __rlshift__(self, other):
        return self._rc(left_shift(other, self.array))

    def __rrshift__(self, other):
        return self._rc(right_shift(other, self.array))

    def __ilshift__(self, other):
        left_shift(self.array, other, self.array)
        return self

    def __irshift__(self, other):
        right_shift(self.array, other, self.array)
        return self

    def __and__(self, other):
        return self._rc(bitwise_and(self.array, other))

    def __rand__(self, other):
        return self._rc(bitwise_and(other, self.array))

    def __iand__(self, other):
        bitwise_and(self.array, other, self.array)
        return self

    def __xor__(self, other):
        return self._rc(bitwise_xor(self.array, other))

    def __rxor__(self, other):
        return self._rc(bitwise_xor(other, self.array))

    def __ixor__(self, other):
        bitwise_xor(self.array, other, self.array)
        return self

    def __or__(self, other):
        return self._rc(bitwise_or(self.array, other))

    def __ror__(self, other):
        return self._rc(bitwise_or(other, self.array))

    def __ior__(self, other):
        bitwise_or(self.array, other, self.array)
        return self

    def __pos__(self):
        return self._rc(self.array)

    def __invert__(self):
        return self._rc(invert(self.array))

    def _scalarfunc(self, func):
        if self.ndim == 0:
            return func(self[0])
        else:
            raise TypeError(
                "only rank-0 arrays can be converted to Python scalars.")

    def __complex__(self):
        return self._scalarfunc(complex)

    def __float__(self):
        return self._scalarfunc(float)

    def __int__(self):
        return self._scalarfunc(int)

    def __hex__(self):
        return self._scalarfunc(hex)

    def __oct__(self):
        return self._scalarfunc(oct)

    def __lt__(self, other):
        return self._rc(less(self.array, other))

    def __le__(self, other):
        return self._rc(less_equal(self.array, other))

    def __eq__(self, other):
        return self._rc(equal(self.array, other))

    def __ne__(self, other):
        return self._rc(not_equal(self.array, other))

    def __gt__(self, other):
        return self._rc(greater(self.array, other))

    def __ge__(self, other):
        return self._rc(greater_equal(self.array, other))

    def copy(self):
        ""
        return self._rc(self.array.copy())

    def tobytes(self):
        ""
        return self.array.tobytes()

    def byteswap(self):
        ""
        return self._rc(self.array.byteswap())

    def astype(self, typecode):
        ""
        return self._rc(self.array.astype(typecode))

    def _rc(self, a):
        if len(shape(a)) == 0:
            return a
        else:
            return self.__class__(a)

    def __array_wrap__(self, *args):
        return self.__class__(args[0])

    def __setattr__(self, attr, value):
        if attr == 'array':
            object.__setattr__(self, attr, value)
            return
        try:
            self.array.__setattr__(attr, value)
        except AttributeError:
            object.__setattr__(self, attr, value)

    # Only called after other approaches fail.
    def __getattr__(self, attr):
        if (attr == 'array'):
            return object.__getattribute__(self, attr)
        return self.array.__getattribute__(attr)


#############################################################
# Test of class container
#############################################################
if __name__ == '__main__':
    temp = reshape(arange(10000), (100, 100))

    ua = container(temp)
    # new object created begin test
    print(dir(ua))
    print(shape(ua), ua.shape)  # I have changed Numeric.py

    ua_small = ua[:3, :5]
    print(ua_small)
    # this did not change ua[0,0], which is not normal behavior
    ua_small[0, 0] = 10
    print(ua_small[0, 0], ua[0, 0])
    print(sin(ua_small) / 3. * 6. + sqrt(ua_small ** 2))
    print(less(ua_small, 103), type(less(ua_small, 103)))
    print(type(ua_small * reshape(arange(15), shape(ua_small))))
    print(reshape(ua_small, (5, 3)))
    print(transpose(ua_small))

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_user_array_impl.py ===
"""
Container class for backward compatibility with NumArray.

The user_array.container class exists for backward compatibility with NumArray
and is not meant to be used in new code. If you need to create an array
container class, we recommend either creating a class that wraps an ndarray
or subclasses ndarray.

"""
from numpy._core import (
    absolute,
    add,
    arange,
    array,
    asarray,
    bitwise_and,
    bitwise_or,
    bitwise_xor,
    divide,
    equal,
    greater,
    greater_equal,
    invert,
    left_shift,
    less,
    less_equal,
    multiply,
    not_equal,
    power,
    remainder,
    reshape,
    right_shift,
    shape,
    sin,
    sqrt,
    subtract,
    transpose,
)
from numpy._core.overrides import set_module


@set_module("numpy.lib.user_array")
class container:
    """
    container(data, dtype=None, copy=True)

    Standard container-class for easy multiple-inheritance.

    Methods
    -------
    copy
    byteswap
    astype

    """
    def __init__(self, data, dtype=None, copy=True):
        self.array = array(data, dtype, copy=copy)

    def __repr__(self):
        if self.ndim > 0:
            return self.__class__.__name__ + repr(self.array)[len("array"):]
        else:
            return self.__class__.__name__ + "(" + repr(self.array) + ")"

    def __array__(self, t=None):
        if t:
            return self.array.astype(t)
        return self.array

    # Array as sequence
    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        return self._rc(self.array[index])

    def __setitem__(self, index, value):
        self.array[index] = asarray(value, self.dtype)

    def __abs__(self):
        return self._rc(absolute(self.array))

    def __neg__(self):
        return self._rc(-self.array)

    def __add__(self, other):
        return self._rc(self.array + asarray(other))

    __radd__ = __add__

    def __iadd__(self, other):
        add(self.array, other, self.array)
        return self

    def __sub__(self, other):
        return self._rc(self.array - asarray(other))

    def __rsub__(self, other):
        return self._rc(asarray(other) - self.array)

    def __isub__(self, other):
        subtract(self.array, other, self.array)
        return self

    def __mul__(self, other):
        return self._rc(multiply(self.array, asarray(other)))

    __rmul__ = __mul__

    def __imul__(self, other):
        multiply(self.array, other, self.array)
        return self

    def __mod__(self, other):
        return self._rc(remainder(self.array, other))

    def __rmod__(self, other):
        return self._rc(remainder(other, self.array))

    def __imod__(self, other):
        remainder(self.array, other, self.array)
        return self

    def __divmod__(self, other):
        return (self._rc(divide(self.array, other)),
                self._rc(remainder(self.array, other)))

    def __rdivmod__(self, other):
        return (self._rc(divide(other, self.array)),
                self._rc(remainder(other, self.array)))

    def __pow__(self, other):
        return self._rc(power(self.array, asarray(other)))

    def __rpow__(self, other):
        return self._rc(power(asarray(other), self.array))

    def __ipow__(self, other):
        power(self.array, other, self.array)
        return self

    def __lshift__(self, other):
        return self._rc(left_shift(self.array, other))

    def __rshift__(self, other):
        return self._rc(right_shift(self.array, other))

    def __rlshift__(self, other):
        return self._rc(left_shift(other, self.array))

    def __rrshift__(self, other):
        return self._rc(right_shift(other, self.array))

    def __ilshift__(self, other):
        left_shift(self.array, other, self.array)
        return self

    def __irshift__(self, other):
        right_shift(self.array, other, self.array)
        return self

    def __and__(self, other):
        return self._rc(bitwise_and(self.array, other))

    def __rand__(self, other):
        return self._rc(bitwise_and(other, self.array))

    def __iand__(self, other):
        bitwise_and(self.array, other, self.array)
        return self

    def __xor__(self, other):
        return self._rc(bitwise_xor(self.array, other))

    def __rxor__(self, other):
        return self._rc(bitwise_xor(other, self.array))

    def __ixor__(self, other):
        bitwise_xor(self.array, other, self.array)
        return self

    def __or__(self, other):
        return self._rc(bitwise_or(self.array, other))

    def __ror__(self, other):
        return self._rc(bitwise_or(other, self.array))

    def __ior__(self, other):
        bitwise_or(self.array, other, self.array)
        return self

    def __pos__(self):
        return self._rc(self.array)

    def __invert__(self):
        return self._rc(invert(self.array))

    def _scalarfunc(self, func):
        if self.ndim == 0:
            return func(self[0])
        else:
            raise TypeError(
                "only rank-0 arrays can be converted to Python scalars.")

    def __complex__(self):
        return self._scalarfunc(complex)

    def __float__(self):
        return self._scalarfunc(float)

    def __int__(self):
        return self._scalarfunc(int)

    def __hex__(self):
        return self._scalarfunc(hex)

    def __oct__(self):
        return self._scalarfunc(oct)

    def __lt__(self, other):
        return self._rc(less(self.array, other))

    def __le__(self, other):
        return self._rc(less_equal(self.array, other))

    def __eq__(self, other):
        return self._rc(equal(self.array, other))

    def __ne__(self, other):
        return self._rc(not_equal(self.array, other))

    def __gt__(self, other):
        return self._rc(greater(self.array, other))

    def __ge__(self, other):
        return self._rc(greater_equal(self.array, other))

    def copy(self):
        ""
        return self._rc(self.array.copy())

    def tobytes(self):
        ""
        return self.array.tobytes()

    def byteswap(self):
        ""
        return self._rc(self.array.byteswap())

    def astype(self, typecode):
        ""
        return self._rc(self.array.astype(typecode))

    def _rc(self, a):
        if len(shape(a)) == 0:
            return a
        else:
            return self.__class__(a)

    def __array_wrap__(self, *args):
        return self.__class__(args[0])

    def __setattr__(self, attr, value):
        if attr == 'array':
            object.__setattr__(self, attr, value)
            return
        try:
            self.array.__setattr__(attr, value)
        except AttributeError:
            object.__setattr__(self, attr, value)

    # Only called after other approaches fail.
    def __getattr__(self, attr):
        if (attr == 'array'):
            return object.__getattribute__(self, attr)
        return self.array.__getattribute__(attr)


#############################################################
# Test of class container
#############################################################
if __name__ == '__main__':
    temp = reshape(arange(10000), (100, 100))

    ua = container(temp)
    # new object created begin test
    print(dir(ua))
    print(shape(ua), ua.shape)  # I have changed Numeric.py

    ua_small = ua[:3, :5]
    print(ua_small)
    # this did not change ua[0,0], which is not normal behavior
    ua_small[0, 0] = 10
    print(ua_small[0, 0], ua[0, 0])
    print(sin(ua_small) / 3. * 6. + sqrt(ua_small ** 2))
    print(less(ua_small, 103), type(less(ua_small, 103)))
    print(type(ua_small * reshape(arange(15), shape(ua_small))))
    print(reshape(ua_small, (5, 3)))
    print(transpose(ua_small))

# === NexusCore/openenv\Lib\site-packages\win32\lib\netbios.py ===
from __future__ import annotations

import struct
from collections.abc import Iterable

import win32wnet

# Constants generated by h2py from nb30.h
NCBNAMSZ = 16
MAX_LANA = 254
NAME_FLAGS_MASK = 0x87
GROUP_NAME = 0x80
UNIQUE_NAME = 0x00
REGISTERING = 0x00
REGISTERED = 0x04
DEREGISTERED = 0x05
DUPLICATE = 0x06
DUPLICATE_DEREG = 0x07
LISTEN_OUTSTANDING = 0x01
CALL_PENDING = 0x02
SESSION_ESTABLISHED = 0x03
HANGUP_PENDING = 0x04
HANGUP_COMPLETE = 0x05
SESSION_ABORTED = 0x06
ALL_TRANSPORTS = "M\0\0\0"
MS_NBF = "MNBF"
NCBCALL = 0x10
NCBLISTEN = 0x11
NCBHANGUP = 0x12
NCBSEND = 0x14
NCBRECV = 0x15
NCBRECVANY = 0x16
NCBCHAINSEND = 0x17
NCBDGSEND = 0x20
NCBDGRECV = 0x21
NCBDGSENDBC = 0x22
NCBDGRECVBC = 0x23
NCBADDNAME = 0x30
NCBDELNAME = 0x31
NCBRESET = 0x32
NCBASTAT = 0x33
NCBSSTAT = 0x34
NCBCANCEL = 0x35
NCBADDGRNAME = 0x36
NCBENUM = 0x37
NCBUNLINK = 0x70
NCBSENDNA = 0x71
NCBCHAINSENDNA = 0x72
NCBLANSTALERT = 0x73
NCBACTION = 0x77
NCBFINDNAME = 0x78
NCBTRACE = 0x79
ASYNCH = 0x80
NRC_GOODRET = 0x00
NRC_BUFLEN = 0x01
NRC_ILLCMD = 0x03
NRC_CMDTMO = 0x05
NRC_INCOMP = 0x06
NRC_BADDR = 0x07
NRC_SNUMOUT = 0x08
NRC_NORES = 0x09
NRC_SCLOSED = 0x0A
NRC_CMDCAN = 0x0B
NRC_DUPNAME = 0x0D
NRC_NAMTFUL = 0x0E
NRC_ACTSES = 0x0F
NRC_LOCTFUL = 0x11
NRC_REMTFUL = 0x12
NRC_ILLNN = 0x13
NRC_NOCALL = 0x14
NRC_NOWILD = 0x15
NRC_INUSE = 0x16
NRC_NAMERR = 0x17
NRC_SABORT = 0x18
NRC_NAMCONF = 0x19
NRC_IFBUSY = 0x21
NRC_TOOMANY = 0x22
NRC_BRIDGE = 0x23
NRC_CANOCCR = 0x24
NRC_CANCEL = 0x26
NRC_DUPENV = 0x30
NRC_ENVNOTDEF = 0x34
NRC_OSRESNOTAV = 0x35
NRC_MAXAPPS = 0x36
NRC_NOSAPS = 0x37
NRC_NORESOURCES = 0x38
NRC_INVADDRESS = 0x39
NRC_INVDDID = 0x3B
NRC_LOCKFAIL = 0x3C
NRC_OPENERR = 0x3F
NRC_SYSTEM = 0x40
NRC_PENDING = 0xFF


UCHAR = "B"
WORD = "H"
DWORD = "I"
USHORT = "H"
ULONG = "I"

ADAPTER_STATUS_ITEMS = [
    ("6s", "adapter_address"),
    (UCHAR, "rev_major"),
    (UCHAR, "reserved0"),
    (UCHAR, "adapter_type"),
    (UCHAR, "rev_minor"),
    (WORD, "duration"),
    (WORD, "frmr_recv"),
    (WORD, "frmr_xmit"),
    (WORD, "iframe_recv_err"),
    (WORD, "xmit_aborts"),
    (DWORD, "xmit_success"),
    (DWORD, "recv_success"),
    (WORD, "iframe_xmit_err"),
    (WORD, "recv_buff_unavail"),
    (WORD, "t1_timeouts"),
    (WORD, "ti_timeouts"),
    (DWORD, "reserved1"),
    (WORD, "free_ncbs"),
    (WORD, "max_cfg_ncbs"),
    (WORD, "max_ncbs"),
    (WORD, "xmit_buf_unavail"),
    (WORD, "max_dgram_size"),
    (WORD, "pending_sess"),
    (WORD, "max_cfg_sess"),
    (WORD, "max_sess"),
    (WORD, "max_sess_pkt_size"),
    (WORD, "name_count"),
]

NAME_BUFFER_ITEMS = [
    (str(NCBNAMSZ) + "s", "name"),
    (UCHAR, "name_num"),
    (UCHAR, "name_flags"),
]

SESSION_HEADER_ITEMS = [
    (UCHAR, "sess_name"),
    (UCHAR, "num_sess"),
    (UCHAR, "rcv_dg_outstanding"),
    (UCHAR, "rcv_any_outstanding"),
]

SESSION_BUFFER_ITEMS = [
    (UCHAR, "lsn"),
    (UCHAR, "state"),
    (str(NCBNAMSZ) + "s", "local_name"),
    (str(NCBNAMSZ) + "s", "remote_name"),
    (UCHAR, "rcvs_outstanding"),
    (UCHAR, "sends_outstanding"),
]

LANA_ENUM_ITEMS = [
    ("B", "length"),  # Number of valid entries in lana[]
    (str(MAX_LANA + 1) + "s", "lana"),
]

FIND_NAME_HEADER_ITEMS = [
    (WORD, "node_count"),
    (UCHAR, "reserved"),
    (UCHAR, "unique_group"),
]

FIND_NAME_BUFFER_ITEMS = [
    (UCHAR, "length"),
    (UCHAR, "access_control"),
    (UCHAR, "frame_control"),
    ("6s", "destination_addr"),
    ("6s", "source_addr"),
    ("18s", "routing_info"),
]

ACTION_HEADER_ITEMS = [
    (ULONG, "transport_id"),
    (USHORT, "action_code"),
    (USHORT, "reserved"),
]

del UCHAR, WORD, DWORD, USHORT, ULONG

NCB = win32wnet.NCB


def Netbios(ncb):
    ob = ncb.Buffer
    is_ours = hasattr(ob, "_pack")
    if is_ours:
        ob._pack()
    try:
        return win32wnet.Netbios(ncb)
    finally:
        if is_ours:
            ob._unpack()


class NCBStruct:
    def __init__(self, items: Iterable[tuple[str, str]]) -> None:
        self._format = "".join([item[0] for item in items])
        self._items = items
        self._buffer_ = win32wnet.NCBBuffer(struct.calcsize(self._format))

        for format, name in self._items:
            if len(format) == 1:
                if format == "c":
                    val: bytes | int = b"\0"
                else:
                    val = 0
            else:
                l = int(format[:-1])
                val = b"\0" * l
            self.__dict__[name] = val

    def _pack(self):
        vals = [self.__dict__.get(name) for format, name in self._items]

        self._buffer_[:] = struct.pack(self._format, *vals)

    def _unpack(self):
        items = struct.unpack(self._format, self._buffer_)
        assert len(items) == len(self._items), "unexpected number of items to unpack!"
        for (format, name), val in zip(self._items, items):
            self.__dict__[name] = val

    def __setattr__(self, attr, val):
        if attr not in self.__dict__ and attr[0] != "_":
            for format, attr_name in self._items:
                if attr == attr_name:
                    break
            else:
                raise AttributeError(attr)
        self.__dict__[attr] = val


def ADAPTER_STATUS():
    return NCBStruct(ADAPTER_STATUS_ITEMS)


def NAME_BUFFER():
    return NCBStruct(NAME_BUFFER_ITEMS)


def SESSION_HEADER():
    return NCBStruct(SESSION_HEADER_ITEMS)


def SESSION_BUFFER():
    return NCBStruct(SESSION_BUFFER_ITEMS)


def LANA_ENUM():
    return NCBStruct(LANA_ENUM_ITEMS)


def FIND_NAME_HEADER():
    return NCBStruct(FIND_NAME_HEADER_ITEMS)


def FIND_NAME_BUFFER():
    return NCBStruct(FIND_NAME_BUFFER_ITEMS)


def ACTION_HEADER():
    return NCBStruct(ACTION_HEADER_ITEMS)


if __name__ == "__main__":
    # code ported from "HOWTO: Get the MAC Address for an Ethernet Adapter"
    # MS KB ID: Q118623
    ncb = NCB()
    ncb.Command = NCBENUM
    la_enum = LANA_ENUM()
    ncb.Buffer = la_enum
    rc = Netbios(ncb)
    if rc != 0:
        raise RuntimeError("Unexpected result %d" % (rc,))
    for i in range(la_enum.length):
        ncb.Reset()
        ncb.Command = NCBRESET
        ncb.Lana_num = la_enum.lana[i]
        rc = Netbios(ncb)
        if rc != 0:
            raise RuntimeError("Unexpected result %d" % (rc,))
        ncb.Reset()
        ncb.Command = NCBASTAT
        ncb.Lana_num = la_enum.lana[i]
        ncb.Callname = b"*               "
        adapter = ADAPTER_STATUS()
        ncb.Buffer = adapter
        Netbios(ncb)
        print("Adapter address:", end=" ")
        for ch in adapter.adapter_address:
            print(f"{ch:02x}", end=" ")
        print()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\netbios.py ===
from __future__ import annotations

import struct
from collections.abc import Iterable

import win32wnet

# Constants generated by h2py from nb30.h
NCBNAMSZ = 16
MAX_LANA = 254
NAME_FLAGS_MASK = 0x87
GROUP_NAME = 0x80
UNIQUE_NAME = 0x00
REGISTERING = 0x00
REGISTERED = 0x04
DEREGISTERED = 0x05
DUPLICATE = 0x06
DUPLICATE_DEREG = 0x07
LISTEN_OUTSTANDING = 0x01
CALL_PENDING = 0x02
SESSION_ESTABLISHED = 0x03
HANGUP_PENDING = 0x04
HANGUP_COMPLETE = 0x05
SESSION_ABORTED = 0x06
ALL_TRANSPORTS = "M\0\0\0"
MS_NBF = "MNBF"
NCBCALL = 0x10
NCBLISTEN = 0x11
NCBHANGUP = 0x12
NCBSEND = 0x14
NCBRECV = 0x15
NCBRECVANY = 0x16
NCBCHAINSEND = 0x17
NCBDGSEND = 0x20
NCBDGRECV = 0x21
NCBDGSENDBC = 0x22
NCBDGRECVBC = 0x23
NCBADDNAME = 0x30
NCBDELNAME = 0x31
NCBRESET = 0x32
NCBASTAT = 0x33
NCBSSTAT = 0x34
NCBCANCEL = 0x35
NCBADDGRNAME = 0x36
NCBENUM = 0x37
NCBUNLINK = 0x70
NCBSENDNA = 0x71
NCBCHAINSENDNA = 0x72
NCBLANSTALERT = 0x73
NCBACTION = 0x77
NCBFINDNAME = 0x78
NCBTRACE = 0x79
ASYNCH = 0x80
NRC_GOODRET = 0x00
NRC_BUFLEN = 0x01
NRC_ILLCMD = 0x03
NRC_CMDTMO = 0x05
NRC_INCOMP = 0x06
NRC_BADDR = 0x07
NRC_SNUMOUT = 0x08
NRC_NORES = 0x09
NRC_SCLOSED = 0x0A
NRC_CMDCAN = 0x0B
NRC_DUPNAME = 0x0D
NRC_NAMTFUL = 0x0E
NRC_ACTSES = 0x0F
NRC_LOCTFUL = 0x11
NRC_REMTFUL = 0x12
NRC_ILLNN = 0x13
NRC_NOCALL = 0x14
NRC_NOWILD = 0x15
NRC_INUSE = 0x16
NRC_NAMERR = 0x17
NRC_SABORT = 0x18
NRC_NAMCONF = 0x19
NRC_IFBUSY = 0x21
NRC_TOOMANY = 0x22
NRC_BRIDGE = 0x23
NRC_CANOCCR = 0x24
NRC_CANCEL = 0x26
NRC_DUPENV = 0x30
NRC_ENVNOTDEF = 0x34
NRC_OSRESNOTAV = 0x35
NRC_MAXAPPS = 0x36
NRC_NOSAPS = 0x37
NRC_NORESOURCES = 0x38
NRC_INVADDRESS = 0x39
NRC_INVDDID = 0x3B
NRC_LOCKFAIL = 0x3C
NRC_OPENERR = 0x3F
NRC_SYSTEM = 0x40
NRC_PENDING = 0xFF


UCHAR = "B"
WORD = "H"
DWORD = "I"
USHORT = "H"
ULONG = "I"

ADAPTER_STATUS_ITEMS = [
    ("6s", "adapter_address"),
    (UCHAR, "rev_major"),
    (UCHAR, "reserved0"),
    (UCHAR, "adapter_type"),
    (UCHAR, "rev_minor"),
    (WORD, "duration"),
    (WORD, "frmr_recv"),
    (WORD, "frmr_xmit"),
    (WORD, "iframe_recv_err"),
    (WORD, "xmit_aborts"),
    (DWORD, "xmit_success"),
    (DWORD, "recv_success"),
    (WORD, "iframe_xmit_err"),
    (WORD, "recv_buff_unavail"),
    (WORD, "t1_timeouts"),
    (WORD, "ti_timeouts"),
    (DWORD, "reserved1"),
    (WORD, "free_ncbs"),
    (WORD, "max_cfg_ncbs"),
    (WORD, "max_ncbs"),
    (WORD, "xmit_buf_unavail"),
    (WORD, "max_dgram_size"),
    (WORD, "pending_sess"),
    (WORD, "max_cfg_sess"),
    (WORD, "max_sess"),
    (WORD, "max_sess_pkt_size"),
    (WORD, "name_count"),
]

NAME_BUFFER_ITEMS = [
    (str(NCBNAMSZ) + "s", "name"),
    (UCHAR, "name_num"),
    (UCHAR, "name_flags"),
]

SESSION_HEADER_ITEMS = [
    (UCHAR, "sess_name"),
    (UCHAR, "num_sess"),
    (UCHAR, "rcv_dg_outstanding"),
    (UCHAR, "rcv_any_outstanding"),
]

SESSION_BUFFER_ITEMS = [
    (UCHAR, "lsn"),
    (UCHAR, "state"),
    (str(NCBNAMSZ) + "s", "local_name"),
    (str(NCBNAMSZ) + "s", "remote_name"),
    (UCHAR, "rcvs_outstanding"),
    (UCHAR, "sends_outstanding"),
]

LANA_ENUM_ITEMS = [
    ("B", "length"),  # Number of valid entries in lana[]
    (str(MAX_LANA + 1) + "s", "lana"),
]

FIND_NAME_HEADER_ITEMS = [
    (WORD, "node_count"),
    (UCHAR, "reserved"),
    (UCHAR, "unique_group"),
]

FIND_NAME_BUFFER_ITEMS = [
    (UCHAR, "length"),
    (UCHAR, "access_control"),
    (UCHAR, "frame_control"),
    ("6s", "destination_addr"),
    ("6s", "source_addr"),
    ("18s", "routing_info"),
]

ACTION_HEADER_ITEMS = [
    (ULONG, "transport_id"),
    (USHORT, "action_code"),
    (USHORT, "reserved"),
]

del UCHAR, WORD, DWORD, USHORT, ULONG

NCB = win32wnet.NCB


def Netbios(ncb):
    ob = ncb.Buffer
    is_ours = hasattr(ob, "_pack")
    if is_ours:
        ob._pack()
    try:
        return win32wnet.Netbios(ncb)
    finally:
        if is_ours:
            ob._unpack()


class NCBStruct:
    def __init__(self, items: Iterable[tuple[str, str]]) -> None:
        self._format = "".join([item[0] for item in items])
        self._items = items
        self._buffer_ = win32wnet.NCBBuffer(struct.calcsize(self._format))

        for format, name in self._items:
            if len(format) == 1:
                if format == "c":
                    val: bytes | int = b"\0"
                else:
                    val = 0
            else:
                l = int(format[:-1])
                val = b"\0" * l
            self.__dict__[name] = val

    def _pack(self):
        vals = [self.__dict__.get(name) for format, name in self._items]

        self._buffer_[:] = struct.pack(self._format, *vals)

    def _unpack(self):
        items = struct.unpack(self._format, self._buffer_)
        assert len(items) == len(self._items), "unexpected number of items to unpack!"
        for (format, name), val in zip(self._items, items):
            self.__dict__[name] = val

    def __setattr__(self, attr, val):
        if attr not in self.__dict__ and attr[0] != "_":
            for format, attr_name in self._items:
                if attr == attr_name:
                    break
            else:
                raise AttributeError(attr)
        self.__dict__[attr] = val


def ADAPTER_STATUS():
    return NCBStruct(ADAPTER_STATUS_ITEMS)


def NAME_BUFFER():
    return NCBStruct(NAME_BUFFER_ITEMS)


def SESSION_HEADER():
    return NCBStruct(SESSION_HEADER_ITEMS)


def SESSION_BUFFER():
    return NCBStruct(SESSION_BUFFER_ITEMS)


def LANA_ENUM():
    return NCBStruct(LANA_ENUM_ITEMS)


def FIND_NAME_HEADER():
    return NCBStruct(FIND_NAME_HEADER_ITEMS)


def FIND_NAME_BUFFER():
    return NCBStruct(FIND_NAME_BUFFER_ITEMS)


def ACTION_HEADER():
    return NCBStruct(ACTION_HEADER_ITEMS)


if __name__ == "__main__":
    # code ported from "HOWTO: Get the MAC Address for an Ethernet Adapter"
    # MS KB ID: Q118623
    ncb = NCB()
    ncb.Command = NCBENUM
    la_enum = LANA_ENUM()
    ncb.Buffer = la_enum
    rc = Netbios(ncb)
    if rc != 0:
        raise RuntimeError("Unexpected result %d" % (rc,))
    for i in range(la_enum.length):
        ncb.Reset()
        ncb.Command = NCBRESET
        ncb.Lana_num = la_enum.lana[i]
        rc = Netbios(ncb)
        if rc != 0:
            raise RuntimeError("Unexpected result %d" % (rc,))
        ncb.Reset()
        ncb.Command = NCBASTAT
        ncb.Lana_num = la_enum.lana[i]
        ncb.Callname = b"*               "
        adapter = ADAPTER_STATUS()
        ncb.Buffer = adapter
        Netbios(ncb)
        print("Adapter address:", end=" ")
        for ch in adapter.adapter_address:
            print(f"{ch:02x}", end=" ")
        print()

# === NexusCore/exported_projects\app_20250703_223016\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/exported_projects\project_export_m73owrzi\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/exported_projects\project_export_xb_l70t8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/src\sandbox_logs\repair_20250713_142257_fixed.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/src\sandbox_logs\repair_20250713_142312_original.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/src\sandbox_logs\repair_20250713_213522_original.py ===
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# === NexusCore/src\__init__.py ===

# === NexusCore/exported_projects\app_20250703_223016\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_m73owrzi\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_xb_l70t8\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\routes\__init__.py ===

# === NexusCore/healing_sandbox\app\__init__.py ===

# === NexusCore/healing_sandbox\src\__init__.py ===

# === NexusCore/healing_sandbox\src\agents\__init__.py ===

# === NexusCore/policy_test_sandbox\app\__init__.py ===

# === NexusCore/quality_loop_test_sandbox\app\__init__.py ===

# === NexusCore/src\agents\__init__.py ===

# === NexusCore/src\code_interpreter\__init__.py ===

# === NexusCore/src\core\__init__.py ===

# === NexusCore/src\gradio_app\__init__.py ===

# === NexusCore/src\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\src\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\src\agents\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\policy_test_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\quality_loop_test_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\workspace\default_project\app\__init__.py ===

# === NexusCore/workspace\default_project\app\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\types\llms\triton.py ===


# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\types\llms\triton.py ===


# === NexusCore/evaluation\evalplus\evalplus\perf\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\typing_inspection\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anyio\streams\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anyio\_backends\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anyio\_core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_concurrency_analyser\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\_debug_adapter\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\fontTools\colorLib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\gitdb\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\auth\crypt\_helpers.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\compiler\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\pyext\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\testdata\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\util\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\greenlet\platform\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\html2image\browsers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\httpcore\_backends\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_generated\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_mcp\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\importlib_metadata\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\computer_use\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\llm\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\ai\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\browser\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\calendar\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\clipboard\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\contacts\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\display\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\files\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\keyboard\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\mail\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\mouse\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\os\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\sms\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\terminal\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\vision\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\terminal\languages\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\ipykernel\pylab\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\sphinxext\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\extensions\deduperreload\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\testing\plugin\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\joblib\externals\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\joblib\test\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\joblib\test\data\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\images\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\test_httpx.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\response_header_helpers.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\router_utils\response_headers.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\llms\mistral\mistral_embedding_transformation.py ===

# === NexusCore/openenv\Lib\site-packages\markdown_it\cli\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\markdown_it\common\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\matplotlib\sphinxext\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\qt_editor\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\tbl\api.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\lm\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\translate\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\_pyinstaller\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\testing\_private\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\parso\python\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\contrib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pydantic\deprecated\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pyparsing\tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pyreadline3\lineeditor\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\dialogs\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\docking\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\mfc\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\editor\color\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\backports\tarfile\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\importlib_metadata\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\inflect\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\zipp\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\smmap\test\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\sniffio\_tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\tornado\platform\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\tornado\test\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_tests\tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\urllib3\contrib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\webdriver_manager\core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\webdriver_manager\drivers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\win32com\demos\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\win32com\servers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\server\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\zipp\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\zmq\log\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\zmq\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\evaluation\evalplus\evalplus\perf\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\typing_inspection\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anyio\streams\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anyio\_backends\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anyio\_core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\_debug_adapter\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\fontTools\colorLib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\fsspec\implementations\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\gitdb\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\auth\crypt\_helpers.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\compiler\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\pyext\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\testdata\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\util\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\greenlet\platform\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\html2image\browsers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\httpcore\_backends\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\_generated\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\_mcp\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\importlib_metadata\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\computer_use\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\terminal_interface\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\llm\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\ai\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\browser\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\calendar\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\clipboard\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\contacts\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\display\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\files\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\keyboard\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\mail\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\mouse\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\os\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\sms\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\terminal\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\vision\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\terminal\languages\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\ipykernel\pylab\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\sphinxext\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\terminal\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\extensions\deduperreload\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\testing\plugin\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\joblib\externals\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\joblib\test\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\joblib\test\data\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\images\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\integrations\test_httpx.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\litellm_core_utils\response_header_helpers.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\router_utils\response_headers.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\llms\mistral\mistral_embedding_transformation.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\markdown_it\cli\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\markdown_it\common\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\matplotlib\sphinxext\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\matplotlib\backends\qt_editor\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\tbl\api.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\lm\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\translate\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\_pyinstaller\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\testing\_private\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\parso\python\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\playwright\_impl\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\prompt_toolkit\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pydantic\deprecated\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pydantic\_internal\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pyparsing\tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pyreadline3\lineeditor\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\dialogs\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\docking\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\framework\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\mfc\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\framework\editor\color\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\backports\tarfile\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\importlib_metadata\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\inflect\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\zipp\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\smmap\test\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\sniffio\_tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\tornado\platform\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\tornado\test\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_core\_tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_tests\tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\webdriver_manager\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\webdriver_manager\drivers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32com\demos\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32com\servers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32comext\axscript\server\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\zipp\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\zmq\log\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\zmq\utils\__init__.py ===

# === NexusCore/tests\__init__.py ===

# === NexusCore/healing_sandbox\tests\__init__.py ===

# === NexusCore/my-crm-app\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\blessed\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\docs\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\jsonschema\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\jsonschema_specifications\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\fft\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\linalg\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\ma\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\matrixlib\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\random\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\random\tests\data\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\testing\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\typing\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pkg_resources\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\referencing\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\tests\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\tests\config\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\tests\integration\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\tests\test_versionpredicate.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\tests\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\traitlets\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\websocket\tests\__init__.py ===

# === NexusCore/policy_test_sandbox\tests\__init__.py ===

# === NexusCore/quality_loop_test_sandbox\tests\__init__.py ===

# === NexusCore/sandbox_repo\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\blessed\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\docs\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\jsonschema\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\jsonschema_specifications\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\fft\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\linalg\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\ma\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\matrixlib\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\polynomial\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\random\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\random\tests\data\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\testing\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\typing\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pkg_resources\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\referencing\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\config\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\integration\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_distutils\tests\test_versionpredicate.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_distutils\tests\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\traitlets\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\websocket\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\policy_test_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\quality_loop_test_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\sandbox_repo\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\workspace\default_project\tests\__init__.py ===

# === NexusCore/workspace\default_project\tests\__init__.py ===