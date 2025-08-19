
# === NexusCore/tools\exports\export_20250803_114325\combined_68.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\_core\strings.py ===
"""
This module contains a set of functions for vectorized string
operations.
"""

import functools
import sys

import numpy as np
from numpy import (
    add,
    equal,
    greater,
    greater_equal,
    less,
    less_equal,
    not_equal,
)
from numpy import (
    multiply as _multiply_ufunc,
)
from numpy._core.multiarray import _vec_string
from numpy._core.overrides import array_function_dispatch, set_module
from numpy._core.umath import (
    _center,
    _expandtabs,
    _expandtabs_length,
    _ljust,
    _lstrip_chars,
    _lstrip_whitespace,
    _partition,
    _partition_index,
    _replace,
    _rjust,
    _rpartition,
    _rpartition_index,
    _rstrip_chars,
    _rstrip_whitespace,
    _slice,
    _strip_chars,
    _strip_whitespace,
    _zfill,
    isalnum,
    isalpha,
    isdecimal,
    isdigit,
    islower,
    isnumeric,
    isspace,
    istitle,
    isupper,
    str_len,
)
from numpy._core.umath import (
    count as _count_ufunc,
)
from numpy._core.umath import (
    endswith as _endswith_ufunc,
)
from numpy._core.umath import (
    find as _find_ufunc,
)
from numpy._core.umath import (
    index as _index_ufunc,
)
from numpy._core.umath import (
    rfind as _rfind_ufunc,
)
from numpy._core.umath import (
    rindex as _rindex_ufunc,
)
from numpy._core.umath import (
    startswith as _startswith_ufunc,
)


def _override___module__():
    for ufunc in [
        isalnum, isalpha, isdecimal, isdigit, islower, isnumeric, isspace,
        istitle, isupper, str_len,
    ]:
        ufunc.__module__ = "numpy.strings"
        ufunc.__qualname__ = ufunc.__name__


_override___module__()


__all__ = [
    # UFuncs
    "equal", "not_equal", "less", "less_equal", "greater", "greater_equal",
    "add", "multiply", "isalpha", "isdigit", "isspace", "isalnum", "islower",
    "isupper", "istitle", "isdecimal", "isnumeric", "str_len", "find",
    "rfind", "index", "rindex", "count", "startswith", "endswith", "lstrip",
    "rstrip", "strip", "replace", "expandtabs", "center", "ljust", "rjust",
    "zfill", "partition", "rpartition", "slice",

    # _vec_string - Will gradually become ufuncs as well
    "upper", "lower", "swapcase", "capitalize", "title",

    # _vec_string - Will probably not become ufuncs
    "mod", "decode", "encode", "translate",

    # Removed from namespace until behavior has been crystallized
    # "join", "split", "rsplit", "splitlines",
]


MAX = np.iinfo(np.int64).max

array_function_dispatch = functools.partial(
    array_function_dispatch, module='numpy.strings')


def _get_num_chars(a):
    """
    Helper function that returns the number of characters per field in
    a string or unicode array.  This is to abstract out the fact that
    for a unicode array this is itemsize / 4.
    """
    if issubclass(a.dtype.type, np.str_):
        return a.itemsize // 4
    return a.itemsize


def _to_bytes_or_str_array(result, output_dtype_like):
    """
    Helper function to cast a result back into an array
    with the appropriate dtype if an object array must be used
    as an intermediary.
    """
    output_dtype_like = np.asarray(output_dtype_like)
    if result.size == 0:
        # Calling asarray & tolist in an empty array would result
        # in losing shape information
        return result.astype(output_dtype_like.dtype)
    ret = np.asarray(result.tolist())
    if isinstance(output_dtype_like.dtype, np.dtypes.StringDType):
        return ret.astype(type(output_dtype_like.dtype))
    return ret.astype(type(output_dtype_like.dtype)(_get_num_chars(ret)))


def _clean_args(*args):
    """
    Helper function for delegating arguments to Python string
    functions.

    Many of the Python string operations that have optional arguments
    do not use 'None' to indicate a default value.  In these cases,
    we need to remove all None arguments, and those following them.
    """
    newargs = []
    for chk in args:
        if chk is None:
            break
        newargs.append(chk)
    return newargs


def _multiply_dispatcher(a, i):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_multiply_dispatcher)
def multiply(a, i):
    """
    Return (a * i), that is string multiple concatenation,
    element-wise.

    Values in ``i`` of less than 0 are treated as 0 (which yields an
    empty string).

    Parameters
    ----------
    a : array_like, with ``StringDType``, ``bytes_`` or ``str_`` dtype

    i : array_like, with any integer dtype

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["a", "b", "c"])
    >>> np.strings.multiply(a, 3)
    array(['aaa', 'bbb', 'ccc'], dtype='<U3')
    >>> i = np.array([1, 2, 3])
    >>> np.strings.multiply(a, i)
    array(['a', 'bb', 'ccc'], dtype='<U3')
    >>> np.strings.multiply(np.array(['a']), i)
    array(['a', 'aa', 'aaa'], dtype='<U3')
    >>> a = np.array(['a', 'b', 'c', 'd', 'e', 'f']).reshape((2, 3))
    >>> np.strings.multiply(a, 3)
    array([['aaa', 'bbb', 'ccc'],
           ['ddd', 'eee', 'fff']], dtype='<U3')
    >>> np.strings.multiply(a, i)
    array([['a', 'bb', 'ccc'],
           ['d', 'ee', 'fff']], dtype='<U3')

    """
    a = np.asanyarray(a)

    i = np.asanyarray(i)
    if not np.issubdtype(i.dtype, np.integer):
        raise TypeError(f"unsupported type {i.dtype} for operand 'i'")
    i = np.maximum(i, 0)

    # delegate to stringdtype loops that also do overflow checking
    if a.dtype.char == "T":
        return a * i

    a_len = str_len(a)

    # Ensure we can do a_len * i without overflow.
    if np.any(a_len > sys.maxsize / np.maximum(i, 1)):
        raise OverflowError("Overflow encountered in string multiply")

    buffersizes = a_len * i
    out_dtype = f"{a.dtype.char}{buffersizes.max()}"
    out = np.empty_like(a, shape=buffersizes.shape, dtype=out_dtype)
    return _multiply_ufunc(a, i, out=out)


def _mod_dispatcher(a, values):
    return (a, values)


@set_module("numpy.strings")
@array_function_dispatch(_mod_dispatcher)
def mod(a, values):
    """
    Return (a % i), that is pre-Python 2.6 string formatting
    (interpolation), element-wise for a pair of array_likes of str
    or unicode.

    Parameters
    ----------
    a : array_like, with `np.bytes_` or `np.str_` dtype

    values : array_like of values
       These values will be element-wise interpolated into the string.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["NumPy is a %s library"])
    >>> np.strings.mod(a, values=["Python"])
    array(['NumPy is a Python library'], dtype='<U25')

    >>> a = np.array([b'%d bytes', b'%d bits'])
    >>> values = np.array([8, 64])
    >>> np.strings.mod(a, values)
    array([b'8 bytes', b'64 bits'], dtype='|S7')

    """
    return _to_bytes_or_str_array(
        _vec_string(a, np.object_, '__mod__', (values,)), a)


@set_module("numpy.strings")
def find(a, sub, start=0, end=None):
    """
    For each element, return the lowest index in the string where
    substring ``sub`` is found, such that ``sub`` is contained in the
    range [``start``, ``end``).

    Parameters
    ----------
    a : array_like, with ``StringDType``, ``bytes_`` or ``str_`` dtype

    sub : array_like, with `np.bytes_` or `np.str_` dtype
        The substring to search for.

    start, end : array_like, with any integer dtype
        The range to look in, interpreted as in slice notation.

    Returns
    -------
    y : ndarray
        Output array of ints

    See Also
    --------
    str.find

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["NumPy is a Python library"])
    >>> np.strings.find(a, "Python")
    array([11])

    """
    end = end if end is not None else MAX
    return _find_ufunc(a, sub, start, end)


@set_module("numpy.strings")
def rfind(a, sub, start=0, end=None):
    """
    For each element, return the highest index in the string where
    substring ``sub`` is found, such that ``sub`` is contained in the
    range [``start``, ``end``).

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    sub : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        The substring to search for.

    start, end : array_like, with any integer dtype
        The range to look in, interpreted as in slice notation.

    Returns
    -------
    y : ndarray
        Output array of ints

    See Also
    --------
    str.rfind

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["Computer Science"])
    >>> np.strings.rfind(a, "Science", start=0, end=None)
    array([9])
    >>> np.strings.rfind(a, "Science", start=0, end=8)
    array([-1])
    >>> b = np.array(["Computer Science", "Science"])
    >>> np.strings.rfind(b, "Science", start=0, end=None)
    array([9, 0])

    """
    end = end if end is not None else MAX
    return _rfind_ufunc(a, sub, start, end)


@set_module("numpy.strings")
def index(a, sub, start=0, end=None):
    """
    Like `find`, but raises :exc:`ValueError` when the substring is not found.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    sub : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    start, end : array_like, with any integer dtype, optional

    Returns
    -------
    out : ndarray
        Output array of ints.

    See Also
    --------
    find, str.index

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["Computer Science"])
    >>> np.strings.index(a, "Science", start=0, end=None)
    array([9])

    """
    end = end if end is not None else MAX
    return _index_ufunc(a, sub, start, end)


@set_module("numpy.strings")
def rindex(a, sub, start=0, end=None):
    """
    Like `rfind`, but raises :exc:`ValueError` when the substring `sub` is
    not found.

    Parameters
    ----------
    a : array-like, with `np.bytes_` or `np.str_` dtype

    sub : array-like, with `np.bytes_` or `np.str_` dtype

    start, end : array-like, with any integer dtype, optional

    Returns
    -------
    out : ndarray
        Output array of ints.

    See Also
    --------
    rfind, str.rindex

    Examples
    --------
    >>> a = np.array(["Computer Science"])
    >>> np.strings.rindex(a, "Science", start=0, end=None)
    array([9])

    """
    end = end if end is not None else MAX
    return _rindex_ufunc(a, sub, start, end)


@set_module("numpy.strings")
def count(a, sub, start=0, end=None):
    """
    Returns an array with the number of non-overlapping occurrences of
    substring ``sub`` in the range [``start``, ``end``).

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    sub : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
       The substring to search for.

    start, end : array_like, with any integer dtype
        The range to look in, interpreted as in slice notation.

    Returns
    -------
    y : ndarray
        Output array of ints

    See Also
    --------
    str.count

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> c
    array(['aAaAaA', '  aA  ', 'abBABba'], dtype='<U7')
    >>> np.strings.count(c, 'A')
    array([3, 1, 1])
    >>> np.strings.count(c, 'aA')
    array([3, 1, 0])
    >>> np.strings.count(c, 'A', start=1, end=4)
    array([2, 1, 1])
    >>> np.strings.count(c, 'A', start=1, end=3)
    array([1, 0, 0])

    """
    end = end if end is not None else MAX
    return _count_ufunc(a, sub, start, end)


@set_module("numpy.strings")
def startswith(a, prefix, start=0, end=None):
    """
    Returns a boolean array which is `True` where the string element
    in ``a`` starts with ``prefix``, otherwise `False`.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    prefix : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    start, end : array_like, with any integer dtype
        With ``start``, test beginning at that position. With ``end``,
        stop comparing at that position.

    Returns
    -------
    out : ndarray
        Output array of bools

    See Also
    --------
    str.startswith

    Examples
    --------
    >>> import numpy as np
    >>> s = np.array(['foo', 'bar'])
    >>> s
    array(['foo', 'bar'], dtype='<U3')
    >>> np.strings.startswith(s, 'fo')
    array([True,  False])
    >>> np.strings.startswith(s, 'o', start=1, end=2)
    array([True,  False])

    """
    end = end if end is not None else MAX
    return _startswith_ufunc(a, prefix, start, end)


@set_module("numpy.strings")
def endswith(a, suffix, start=0, end=None):
    """
    Returns a boolean array which is `True` where the string element
    in ``a`` ends with ``suffix``, otherwise `False`.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    suffix : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    start, end : array_like, with any integer dtype
        With ``start``, test beginning at that position. With ``end``,
        stop comparing at that position.

    Returns
    -------
    out : ndarray
        Output array of bools

    See Also
    --------
    str.endswith

    Examples
    --------
    >>> import numpy as np
    >>> s = np.array(['foo', 'bar'])
    >>> s
    array(['foo', 'bar'], dtype='<U3')
    >>> np.strings.endswith(s, 'ar')
    array([False,  True])
    >>> np.strings.endswith(s, 'a', start=1, end=2)
    array([False,  True])

    """
    end = end if end is not None else MAX
    return _endswith_ufunc(a, suffix, start, end)


def _code_dispatcher(a, encoding=None, errors=None):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_code_dispatcher)
def decode(a, encoding=None, errors=None):
    r"""
    Calls :meth:`bytes.decode` element-wise.

    The set of available codecs comes from the Python standard library,
    and may be extended at runtime.  For more information, see the
    :mod:`codecs` module.

    Parameters
    ----------
    a : array_like, with ``bytes_`` dtype

    encoding : str, optional
       The name of an encoding

    errors : str, optional
       Specifies how to handle encoding errors

    Returns
    -------
    out : ndarray

    See Also
    --------
    :py:meth:`bytes.decode`

    Notes
    -----
    The type of the result will depend on the encoding specified.

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array([b'\x81\xc1\x81\xc1\x81\xc1', b'@@\x81\xc1@@',
    ...               b'\x81\x82\xc2\xc1\xc2\x82\x81'])
    >>> c
    array([b'\x81\xc1\x81\xc1\x81\xc1', b'@@\x81\xc1@@',
           b'\x81\x82\xc2\xc1\xc2\x82\x81'], dtype='|S7')
    >>> np.strings.decode(c, encoding='cp037')
    array(['aAaAaA', '  aA  ', 'abBABba'], dtype='<U7')

    """
    return _to_bytes_or_str_array(
        _vec_string(a, np.object_, 'decode', _clean_args(encoding, errors)),
        np.str_(''))


@set_module("numpy.strings")
@array_function_dispatch(_code_dispatcher)
def encode(a, encoding=None, errors=None):
    """
    Calls :meth:`str.encode` element-wise.

    The set of available codecs comes from the Python standard library,
    and may be extended at runtime. For more information, see the
    :mod:`codecs` module.

    Parameters
    ----------
    a : array_like, with ``StringDType`` or ``str_`` dtype

    encoding : str, optional
       The name of an encoding

    errors : str, optional
       Specifies how to handle encoding errors

    Returns
    -------
    out : ndarray

    See Also
    --------
    str.encode

    Notes
    -----
    The type of the result will depend on the encoding specified.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> np.strings.encode(a, encoding='cp037')
    array([b'\x81\xc1\x81\xc1\x81\xc1', b'@@\x81\xc1@@',
       b'\x81\x82\xc2\xc1\xc2\x82\x81'], dtype='|S7')

    """
    return _to_bytes_or_str_array(
        _vec_string(a, np.object_, 'encode', _clean_args(encoding, errors)),
        np.bytes_(b''))


def _expandtabs_dispatcher(a, tabsize=None):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_expandtabs_dispatcher)
def expandtabs(a, tabsize=8):
    """
    Return a copy of each string element where all tab characters are
    replaced by one or more spaces.

    Calls :meth:`str.expandtabs` element-wise.

    Return a copy of each string element where all tab characters are
    replaced by one or more spaces, depending on the current column
    and the given `tabsize`. The column number is reset to zero after
    each newline occurring in the string. This doesn't understand other
    non-printing characters or escape sequences.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array
    tabsize : int, optional
        Replace tabs with `tabsize` number of spaces.  If not given defaults
        to 8 spaces.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input type

    See Also
    --------
    str.expandtabs

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['\t\tHello\tworld'])
    >>> np.strings.expandtabs(a, tabsize=4)  # doctest: +SKIP
    array(['        Hello   world'], dtype='<U21')  # doctest: +SKIP

    """
    a = np.asanyarray(a)
    tabsize = np.asanyarray(tabsize)

    if a.dtype.char == "T":
        return _expandtabs(a, tabsize)

    buffersizes = _expandtabs_length(a, tabsize)
    out_dtype = f"{a.dtype.char}{buffersizes.max()}"
    out = np.empty_like(a, shape=buffersizes.shape, dtype=out_dtype)
    return _expandtabs(a, tabsize, out=out)


def _just_dispatcher(a, width, fillchar=None):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_just_dispatcher)
def center(a, width, fillchar=' '):
    """
    Return a copy of `a` with its elements centered in a string of
    length `width`.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    width : array_like, with any integer dtype
        The length of the resulting strings, unless ``width < str_len(a)``.
    fillchar : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Optional padding character to use (default is space).

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.center

    Notes
    -----
    While it is possible for ``a`` and ``fillchar`` to have different dtypes,
    passing a non-ASCII character in ``fillchar`` when ``a`` is of dtype "S"
    is not allowed, and a ``ValueError`` is raised.

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['a1b2','1b2a','b2a1','2a1b']); c
    array(['a1b2', '1b2a', 'b2a1', '2a1b'], dtype='<U4')
    >>> np.strings.center(c, width=9)
    array(['   a1b2  ', '   1b2a  ', '   b2a1  ', '   2a1b  '], dtype='<U9')
    >>> np.strings.center(c, width=9, fillchar='*')
    array(['***a1b2**', '***1b2a**', '***b2a1**', '***2a1b**'], dtype='<U9')
    >>> np.strings.center(c, width=1)
    array(['a1b2', '1b2a', 'b2a1', '2a1b'], dtype='<U4')

    """
    width = np.asanyarray(width)

    if not np.issubdtype(width.dtype, np.integer):
        raise TypeError(f"unsupported type {width.dtype} for operand 'width'")

    a = np.asanyarray(a)
    fillchar = np.asanyarray(fillchar)

    if np.any(str_len(fillchar) != 1):
        raise TypeError(
            "The fill character must be exactly one character long")

    if np.result_type(a, fillchar).char == "T":
        return _center(a, width, fillchar)

    fillchar = fillchar.astype(a.dtype, copy=False)
    width = np.maximum(str_len(a), width)
    out_dtype = f"{a.dtype.char}{width.max()}"
    shape = np.broadcast_shapes(a.shape, width.shape, fillchar.shape)
    out = np.empty_like(a, shape=shape, dtype=out_dtype)

    return _center(a, width, fillchar, out=out)


@set_module("numpy.strings")
@array_function_dispatch(_just_dispatcher)
def ljust(a, width, fillchar=' '):
    """
    Return an array with the elements of `a` left-justified in a
    string of length `width`.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    width : array_like, with any integer dtype
        The length of the resulting strings, unless ``width < str_len(a)``.
    fillchar : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Optional character to use for padding (default is space).

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.ljust

    Notes
    -----
    While it is possible for ``a`` and ``fillchar`` to have different dtypes,
    passing a non-ASCII character in ``fillchar`` when ``a`` is of dtype "S"
    is not allowed, and a ``ValueError`` is raised.

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> np.strings.ljust(c, width=3)
    array(['aAaAaA', '  aA  ', 'abBABba'], dtype='<U7')
    >>> np.strings.ljust(c, width=9)
    array(['aAaAaA   ', '  aA     ', 'abBABba  '], dtype='<U9')

    """
    width = np.asanyarray(width)
    if not np.issubdtype(width.dtype, np.integer):
        raise TypeError(f"unsupported type {width.dtype} for operand 'width'")

    a = np.asanyarray(a)
    fillchar = np.asanyarray(fillchar)

    if np.any(str_len(fillchar) != 1):
        raise TypeError(
            "The fill character must be exactly one character long")

    if np.result_type(a, fillchar).char == "T":
        return _ljust(a, width, fillchar)

    fillchar = fillchar.astype(a.dtype, copy=False)
    width = np.maximum(str_len(a), width)
    shape = np.broadcast_shapes(a.shape, width.shape, fillchar.shape)
    out_dtype = f"{a.dtype.char}{width.max()}"
    out = np.empty_like(a, shape=shape, dtype=out_dtype)

    return _ljust(a, width, fillchar, out=out)


@set_module("numpy.strings")
@array_function_dispatch(_just_dispatcher)
def rjust(a, width, fillchar=' '):
    """
    Return an array with the elements of `a` right-justified in a
    string of length `width`.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    width : array_like, with any integer dtype
        The length of the resulting strings, unless ``width < str_len(a)``.
    fillchar : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Optional padding character to use (default is space).

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.rjust

    Notes
    -----
    While it is possible for ``a`` and ``fillchar`` to have different dtypes,
    passing a non-ASCII character in ``fillchar`` when ``a`` is of dtype "S"
    is not allowed, and a ``ValueError`` is raised.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> np.strings.rjust(a, width=3)
    array(['aAaAaA', '  aA  ', 'abBABba'], dtype='<U7')
    >>> np.strings.rjust(a, width=9)
    array(['   aAaAaA', '     aA  ', '  abBABba'], dtype='<U9')

    """
    width = np.asanyarray(width)
    if not np.issubdtype(width.dtype, np.integer):
        raise TypeError(f"unsupported type {width.dtype} for operand 'width'")

    a = np.asanyarray(a)
    fillchar = np.asanyarray(fillchar)

    if np.any(str_len(fillchar) != 1):
        raise TypeError(
            "The fill character must be exactly one character long")

    if np.result_type(a, fillchar).char == "T":
        return _rjust(a, width, fillchar)

    fillchar = fillchar.astype(a.dtype, copy=False)
    width = np.maximum(str_len(a), width)
    shape = np.broadcast_shapes(a.shape, width.shape, fillchar.shape)
    out_dtype = f"{a.dtype.char}{width.max()}"
    out = np.empty_like(a, shape=shape, dtype=out_dtype)

    return _rjust(a, width, fillchar, out=out)


def _zfill_dispatcher(a, width):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_zfill_dispatcher)
def zfill(a, width):
    """
    Return the numeric string left-filled with zeros. A leading
    sign prefix (``+``/``-``) is handled by inserting the padding
    after the sign character rather than before.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    width : array_like, with any integer dtype
        Width of string to left-fill elements in `a`.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input type

    See Also
    --------
    str.zfill

    Examples
    --------
    >>> import numpy as np
    >>> np.strings.zfill(['1', '-1', '+1'], 3)
    array(['001', '-01', '+01'], dtype='<U3')

    """
    width = np.asanyarray(width)
    if not np.issubdtype(width.dtype, np.integer):
        raise TypeError(f"unsupported type {width.dtype} for operand 'width'")

    a = np.asanyarray(a)

    if a.dtype.char == "T":
        return _zfill(a, width)

    width = np.maximum(str_len(a), width)
    shape = np.broadcast_shapes(a.shape, width.shape)
    out_dtype = f"{a.dtype.char}{width.max()}"
    out = np.empty_like(a, shape=shape, dtype=out_dtype)
    return _zfill(a, width, out=out)


@set_module("numpy.strings")
def lstrip(a, chars=None):
    """
    For each element in `a`, return a copy with the leading characters
    removed.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
    chars : scalar with the same dtype as ``a``, optional
       The ``chars`` argument is a string specifying the set of
       characters to be removed. If ``None``, the ``chars``
       argument defaults to removing whitespace. The ``chars`` argument
       is not a prefix or suffix; rather, all combinations of its
       values are stripped.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.lstrip

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> c
    array(['aAaAaA', '  aA  ', 'abBABba'], dtype='<U7')
    # The 'a' variable is unstripped from c[1] because of leading whitespace.
    >>> np.strings.lstrip(c, 'a')
    array(['AaAaA', '  aA  ', 'bBABba'], dtype='<U7')
    >>> np.strings.lstrip(c, 'A') # leaves c unchanged
    array(['aAaAaA', '  aA  ', 'abBABba'], dtype='<U7')
    >>> (np.strings.lstrip(c, ' ') == np.strings.lstrip(c, '')).all()
    np.False_
    >>> (np.strings.lstrip(c, ' ') == np.strings.lstrip(c)).all()
    np.True_

    """
    if chars is None:
        return _lstrip_whitespace(a)
    return _lstrip_chars(a, chars)


@set_module("numpy.strings")
def rstrip(a, chars=None):
    """
    For each element in `a`, return a copy with the trailing characters
    removed.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
    chars : scalar with the same dtype as ``a``, optional
       The ``chars`` argument is a string specifying the set of
       characters to be removed. If ``None``, the ``chars``
       argument defaults to removing whitespace. The ``chars`` argument
       is not a prefix or suffix; rather, all combinations of its
       values are stripped.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.rstrip

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['aAaAaA', 'abBABba'])
    >>> c
    array(['aAaAaA', 'abBABba'], dtype='<U7')
    >>> np.strings.rstrip(c, 'a')
    array(['aAaAaA', 'abBABb'], dtype='<U7')
    >>> np.strings.rstrip(c, 'A')
    array(['aAaAa', 'abBABba'], dtype='<U7')

    """
    if chars is None:
        return _rstrip_whitespace(a)
    return _rstrip_chars(a, chars)


@set_module("numpy.strings")
def strip(a, chars=None):
    """
    For each element in `a`, return a copy with the leading and
    trailing characters removed.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
    chars : scalar with the same dtype as ``a``, optional
       The ``chars`` argument is a string specifying the set of
       characters to be removed. If ``None``, the ``chars``
       argument defaults to removing whitespace. The ``chars`` argument
       is not a prefix or suffix; rather, all combinations of its
       values are stripped.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.strip

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> c
    array(['aAaAaA', '  aA  ', 'abBABba'], dtype='<U7')
    >>> np.strings.strip(c)
    array(['aAaAaA', 'aA', 'abBABba'], dtype='<U7')
    # 'a' unstripped from c[1] because of leading whitespace.
    >>> np.strings.strip(c, 'a')
    array(['AaAaA', '  aA  ', 'bBABb'], dtype='<U7')
    # 'A' unstripped from c[1] because of trailing whitespace.
    >>> np.strings.strip(c, 'A')
    array(['aAaAa', '  aA  ', 'abBABba'], dtype='<U7')

    """
    if chars is None:
        return _strip_whitespace(a)
    return _strip_chars(a, chars)


def _unary_op_dispatcher(a):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_unary_op_dispatcher)
def upper(a):
    """
    Return an array with the elements converted to uppercase.

    Calls :meth:`str.upper` element-wise.

    For 8-bit strings, this method is locale-dependent.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.upper

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['a1b c', '1bca', 'bca1']); c
    array(['a1b c', '1bca', 'bca1'], dtype='<U5')
    >>> np.strings.upper(c)
    array(['A1B C', '1BCA', 'BCA1'], dtype='<U5')

    """
    a_arr = np.asarray(a)
    return _vec_string(a_arr, a_arr.dtype, 'upper')


@set_module("numpy.strings")
@array_function_dispatch(_unary_op_dispatcher)
def lower(a):
    """
    Return an array with the elements converted to lowercase.

    Call :meth:`str.lower` element-wise.

    For 8-bit strings, this method is locale-dependent.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.lower

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['A1B C', '1BCA', 'BCA1']); c
    array(['A1B C', '1BCA', 'BCA1'], dtype='<U5')
    >>> np.strings.lower(c)
    array(['a1b c', '1bca', 'bca1'], dtype='<U5')

    """
    a_arr = np.asarray(a)
    return _vec_string(a_arr, a_arr.dtype, 'lower')


@set_module("numpy.strings")
@array_function_dispatch(_unary_op_dispatcher)
def swapcase(a):
    """
    Return element-wise a copy of the string with
    uppercase characters converted to lowercase and vice versa.

    Calls :meth:`str.swapcase` element-wise.

    For 8-bit strings, this method is locale-dependent.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.swapcase

    Examples
    --------
    >>> import numpy as np
    >>> c=np.array(['a1B c','1b Ca','b Ca1','cA1b'],'S5'); c
    array(['a1B c', '1b Ca', 'b Ca1', 'cA1b'],
        dtype='|S5')
    >>> np.strings.swapcase(c)
    array(['A1b C', '1B cA', 'B cA1', 'Ca1B'],
        dtype='|S5')

    """
    a_arr = np.asarray(a)
    return _vec_string(a_arr, a_arr.dtype, 'swapcase')


@set_module("numpy.strings")
@array_function_dispatch(_unary_op_dispatcher)
def capitalize(a):
    """
    Return a copy of ``a`` with only the first character of each element
    capitalized.

    Calls :meth:`str.capitalize` element-wise.

    For byte strings, this method is locale-dependent.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array of strings to capitalize.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.capitalize

    Examples
    --------
    >>> import numpy as np
    >>> c = np.array(['a1b2','1b2a','b2a1','2a1b'],'S4'); c
    array(['a1b2', '1b2a', 'b2a1', '2a1b'],
        dtype='|S4')
    >>> np.strings.capitalize(c)
    array(['A1b2', '1b2a', 'B2a1', '2a1b'],
        dtype='|S4')

    """
    a_arr = np.asarray(a)
    return _vec_string(a_arr, a_arr.dtype, 'capitalize')


@set_module("numpy.strings")
@array_function_dispatch(_unary_op_dispatcher)
def title(a):
    """
    Return element-wise title cased version of string or unicode.

    Title case words start with uppercase characters, all remaining cased
    characters are lowercase.

    Calls :meth:`str.title` element-wise.

    For 8-bit strings, this method is locale-dependent.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.title

    Examples
    --------
    >>> import numpy as np
    >>> c=np.array(['a1b c','1b ca','b ca1','ca1b'],'S5'); c
    array(['a1b c', '1b ca', 'b ca1', 'ca1b'],
        dtype='|S5')
    >>> np.strings.title(c)
    array(['A1B C', '1B Ca', 'B Ca1', 'Ca1B'],
        dtype='|S5')

    """
    a_arr = np.asarray(a)
    return _vec_string(a_arr, a_arr.dtype, 'title')


def _replace_dispatcher(a, old, new, count=None):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_replace_dispatcher)
def replace(a, old, new, count=-1):
    """
    For each element in ``a``, return a copy of the string with
    occurrences of substring ``old`` replaced by ``new``.

    Parameters
    ----------
    a : array_like, with ``bytes_`` or ``str_`` dtype

    old, new : array_like, with ``bytes_`` or ``str_`` dtype

    count : array_like, with ``int_`` dtype
        If the optional argument ``count`` is given, only the first
        ``count`` occurrences are replaced.

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.replace

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["That is a mango", "Monkeys eat mangos"])
    >>> np.strings.replace(a, 'mango', 'banana')
    array(['That is a banana', 'Monkeys eat bananas'], dtype='<U19')

    >>> a = np.array(["The dish is fresh", "This is it"])
    >>> np.strings.replace(a, 'is', 'was')
    array(['The dwash was fresh', 'Thwas was it'], dtype='<U19')

    """
    count = np.asanyarray(count)
    if not np.issubdtype(count.dtype, np.integer):
        raise TypeError(f"unsupported type {count.dtype} for operand 'count'")

    arr = np.asanyarray(a)
    old_dtype = getattr(old, 'dtype', None)
    old = np.asanyarray(old)
    new_dtype = getattr(new, 'dtype', None)
    new = np.asanyarray(new)

    if np.result_type(arr, old, new).char == "T":
        return _replace(arr, old, new, count)

    a_dt = arr.dtype
    old = old.astype(old_dtype or a_dt, copy=False)
    new = new.astype(new_dtype or a_dt, copy=False)
    max_int64 = np.iinfo(np.int64).max
    counts = _count_ufunc(arr, old, 0, max_int64)
    counts = np.where(count < 0, counts, np.minimum(counts, count))
    buffersizes = str_len(arr) + counts * (str_len(new) - str_len(old))
    out_dtype = f"{arr.dtype.char}{buffersizes.max()}"
    out = np.empty_like(arr, shape=buffersizes.shape, dtype=out_dtype)

    return _replace(arr, old, new, counts, out=out)


def _join_dispatcher(sep, seq):
    return (sep, seq)


@array_function_dispatch(_join_dispatcher)
def _join(sep, seq):
    """
    Return a string which is the concatenation of the strings in the
    sequence `seq`.

    Calls :meth:`str.join` element-wise.

    Parameters
    ----------
    sep : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
    seq : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input types

    See Also
    --------
    str.join

    Examples
    --------
    >>> import numpy as np
    >>> np.strings.join('-', 'osd')  # doctest: +SKIP
    array('o-s-d', dtype='<U5')  # doctest: +SKIP

    >>> np.strings.join(['-', '.'], ['ghc', 'osd'])  # doctest: +SKIP
    array(['g-h-c', 'o.s.d'], dtype='<U5')  # doctest: +SKIP

    """
    return _to_bytes_or_str_array(
        _vec_string(sep, np.object_, 'join', (seq,)), seq)


def _split_dispatcher(a, sep=None, maxsplit=None):
    return (a,)


@array_function_dispatch(_split_dispatcher)
def _split(a, sep=None, maxsplit=None):
    """
    For each element in `a`, return a list of the words in the
    string, using `sep` as the delimiter string.

    Calls :meth:`str.split` element-wise.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    sep : str or unicode, optional
       If `sep` is not specified or None, any whitespace string is a
       separator.

    maxsplit : int, optional
        If `maxsplit` is given, at most `maxsplit` splits are done.

    Returns
    -------
    out : ndarray
        Array of list objects

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array("Numpy is nice!")
    >>> np.strings.split(x, " ")  # doctest: +SKIP
    array(list(['Numpy', 'is', 'nice!']), dtype=object)  # doctest: +SKIP

    >>> np.strings.split(x, " ", 1)  # doctest: +SKIP
    array(list(['Numpy', 'is nice!']), dtype=object)  # doctest: +SKIP

    See Also
    --------
    str.split, rsplit

    """
    # This will return an array of lists of different sizes, so we
    # leave it as an object array
    return _vec_string(
        a, np.object_, 'split', [sep] + _clean_args(maxsplit))


@array_function_dispatch(_split_dispatcher)
def _rsplit(a, sep=None, maxsplit=None):
    """
    For each element in `a`, return a list of the words in the
    string, using `sep` as the delimiter string.

    Calls :meth:`str.rsplit` element-wise.

    Except for splitting from the right, `rsplit`
    behaves like `split`.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    sep : str or unicode, optional
        If `sep` is not specified or None, any whitespace string
        is a separator.
    maxsplit : int, optional
        If `maxsplit` is given, at most `maxsplit` splits are done,
        the rightmost ones.

    Returns
    -------
    out : ndarray
        Array of list objects

    See Also
    --------
    str.rsplit, split

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['aAaAaA', 'abBABba'])
    >>> np.strings.rsplit(a, 'A')  # doctest: +SKIP
    array([list(['a', 'a', 'a', '']),  # doctest: +SKIP
           list(['abB', 'Bba'])], dtype=object)  # doctest: +SKIP

    """
    # This will return an array of lists of different sizes, so we
    # leave it as an object array
    return _vec_string(
        a, np.object_, 'rsplit', [sep] + _clean_args(maxsplit))


def _splitlines_dispatcher(a, keepends=None):
    return (a,)


@array_function_dispatch(_splitlines_dispatcher)
def _splitlines(a, keepends=None):
    """
    For each element in `a`, return a list of the lines in the
    element, breaking at line boundaries.

    Calls :meth:`str.splitlines` element-wise.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype

    keepends : bool, optional
        Line breaks are not included in the resulting list unless
        keepends is given and true.

    Returns
    -------
    out : ndarray
        Array of list objects

    See Also
    --------
    str.splitlines

    Examples
    --------
    >>> np.char.splitlines("first line\\nsecond line")
    array(list(['first line', 'second line']), dtype=object)
    >>> a = np.array(["first\\nsecond", "third\\nfourth"])
    >>> np.char.splitlines(a)
    array([list(['first', 'second']), list(['third', 'fourth'])], dtype=object)

    """
    return _vec_string(
        a, np.object_, 'splitlines', _clean_args(keepends))


def _partition_dispatcher(a, sep):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_partition_dispatcher)
def partition(a, sep):
    """
    Partition each element in ``a`` around ``sep``.

    For each element in ``a``, split the element at the first
    occurrence of ``sep``, and return a 3-tuple containing the part
    before the separator, the separator itself, and the part after
    the separator. If the separator is not found, the first item of
    the tuple will contain the whole string, and the second and third
    ones will be the empty string.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array
    sep : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Separator to split each string element in ``a``.

    Returns
    -------
    out : 3-tuple:
        - array with ``StringDType``, ``bytes_`` or ``str_`` dtype with the
          part before the separator
        - array with ``StringDType``, ``bytes_`` or ``str_`` dtype with the
          separator
        - array with ``StringDType``, ``bytes_`` or ``str_`` dtype with the
          part after the separator

    See Also
    --------
    str.partition

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array(["Numpy is nice!"])
    >>> np.strings.partition(x, " ")
    (array(['Numpy'], dtype='<U5'),
     array([' '], dtype='<U1'),
     array(['is nice!'], dtype='<U8'))

    """
    a = np.asanyarray(a)
    sep = np.asanyarray(sep)

    if np.result_type(a, sep).char == "T":
        return _partition(a, sep)

    sep = sep.astype(a.dtype, copy=False)
    pos = _find_ufunc(a, sep, 0, MAX)
    a_len = str_len(a)
    sep_len = str_len(sep)

    not_found = pos < 0
    buffersizes1 = np.where(not_found, a_len, pos)
    buffersizes3 = np.where(not_found, 0, a_len - pos - sep_len)

    out_dtype = ",".join([f"{a.dtype.char}{n}" for n in (
        buffersizes1.max(),
        1 if np.all(not_found) else sep_len.max(),
        buffersizes3.max(),
    )])
    shape = np.broadcast_shapes(a.shape, sep.shape)
    out = np.empty_like(a, shape=shape, dtype=out_dtype)
    return _partition_index(a, sep, pos, out=(out["f0"], out["f1"], out["f2"]))


@set_module("numpy.strings")
@array_function_dispatch(_partition_dispatcher)
def rpartition(a, sep):
    """
    Partition (split) each element around the right-most separator.

    For each element in ``a``, split the element at the last
    occurrence of ``sep``, and return a 3-tuple containing the part
    before the separator, the separator itself, and the part after
    the separator. If the separator is not found, the third item of
    the tuple will contain the whole string, and the first and second
    ones will be the empty string.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array
    sep : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Separator to split each string element in ``a``.

    Returns
    -------
    out : 3-tuple:
        - array with ``StringDType``, ``bytes_`` or ``str_`` dtype with the
          part before the separator
        - array with ``StringDType``, ``bytes_`` or ``str_`` dtype with the
          separator
        - array with ``StringDType``, ``bytes_`` or ``str_`` dtype with the
          part after the separator

    See Also
    --------
    str.rpartition

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['aAaAaA', '  aA  ', 'abBABba'])
    >>> np.strings.rpartition(a, 'A')
    (array(['aAaAa', '  a', 'abB'], dtype='<U5'),
     array(['A', 'A', 'A'], dtype='<U1'),
     array(['', '  ', 'Bba'], dtype='<U3'))

    """
    a = np.asanyarray(a)
    sep = np.asanyarray(sep)

    if np.result_type(a, sep).char == "T":
        return _rpartition(a, sep)

    sep = sep.astype(a.dtype, copy=False)
    pos = _rfind_ufunc(a, sep, 0, MAX)
    a_len = str_len(a)
    sep_len = str_len(sep)

    not_found = pos < 0
    buffersizes1 = np.where(not_found, 0, pos)
    buffersizes3 = np.where(not_found, a_len, a_len - pos - sep_len)

    out_dtype = ",".join([f"{a.dtype.char}{n}" for n in (
        buffersizes1.max(),
        1 if np.all(not_found) else sep_len.max(),
        buffersizes3.max(),
    )])
    shape = np.broadcast_shapes(a.shape, sep.shape)
    out = np.empty_like(a, shape=shape, dtype=out_dtype)
    return _rpartition_index(
        a, sep, pos, out=(out["f0"], out["f1"], out["f2"]))


def _translate_dispatcher(a, table, deletechars=None):
    return (a,)


@set_module("numpy.strings")
@array_function_dispatch(_translate_dispatcher)
def translate(a, table, deletechars=None):
    """
    For each element in `a`, return a copy of the string where all
    characters occurring in the optional argument `deletechars` are
    removed, and the remaining characters have been mapped through the
    given translation table.

    Calls :meth:`str.translate` element-wise.

    Parameters
    ----------
    a : array-like, with `np.bytes_` or `np.str_` dtype

    table : str of length 256

    deletechars : str

    Returns
    -------
    out : ndarray
        Output array of str or unicode, depending on input type

    See Also
    --------
    str.translate

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['a1b c', '1bca', 'bca1'])
    >>> table = a[0].maketrans('abc', '123')
    >>> deletechars = ' '
    >>> np.char.translate(a, table, deletechars)
    array(['112 3', '1231', '2311'], dtype='<U5')

    """
    a_arr = np.asarray(a)
    if issubclass(a_arr.dtype.type, np.str_):
        return _vec_string(
            a_arr, a_arr.dtype, 'translate', (table,))
    else:
        return _vec_string(
            a_arr,
            a_arr.dtype,
            'translate',
            [table] + _clean_args(deletechars)
        )

@set_module("numpy.strings")
def slice(a, start=None, stop=None, step=None, /):
    """
    Slice the strings in `a` by slices specified by `start`, `stop`, `step`.
    Like in the regular Python `slice` object, if only `start` is
    specified then it is interpreted as the `stop`.

    Parameters
    ----------
    a : array-like, with ``StringDType``, ``bytes_``, or ``str_`` dtype
        Input array

    start : None, an integer or an array of integers
        The start of the slice, broadcasted to `a`'s shape

    stop : None, an integer or an array of integers
        The end of the slice, broadcasted to `a`'s shape

    step : None, an integer or an array of integers
        The step for the slice, broadcasted to `a`'s shape

    Returns
    -------
    out : ndarray
        Output array of ``StringDType``, ``bytes_`` or ``str_`` dtype,
        depending on input type

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(['hello', 'world'])
    >>> np.strings.slice(a, 2)
    array(['he', 'wo'], dtype='<U5')

    >>> np.strings.slice(a, 1, 5, 2)
    array(['el', 'ol'], dtype='<U5')

    One can specify different start/stop/step for different array entries:

    >>> np.strings.slice(a, np.array([1, 2]), np.array([4, 5]))
    array(['ell', 'rld'], dtype='<U5')

    Negative slices have the same meaning as in regular Python:

    >>> b = np.array(['hello world', 'γεια σου κόσμε', '你好世界', '👋 🌍'],
    ...              dtype=np.dtypes.StringDType())
    >>> np.strings.slice(b, -2)
    array(['hello wor', 'γεια σου κόσ', '你好', '👋'], dtype=StringDType())

    >>> np.strings.slice(b, [3, -10, 2, -3], [-1, -2, -1, 3])
    array(['lo worl', ' σου κόσ', '世', '👋 🌍'], dtype=StringDType())

    >>> np.strings.slice(b, None, None, -1)
    array(['dlrow olleh', 'εμσόκ υοσ αιεγ', '界世好你', '🌍 👋'],
          dtype=StringDType())

    """
    # Just like in the construction of a regular slice object, if only start
    # is specified then start will become stop, see logic in slice_new.
    if stop is None:
        stop = start
        start = None

    # adjust start, stop, step to be integers, see logic in PySlice_Unpack
    if step is None:
        step = 1
    step = np.asanyarray(step)
    if not np.issubdtype(step.dtype, np.integer):
        raise TypeError(f"unsupported type {step.dtype} for operand 'step'")
    if np.any(step == 0):
        raise ValueError("slice step cannot be zero")

    if start is None:
        start = np.where(step < 0, np.iinfo(np.intp).max, 0)

    if stop is None:
        stop = np.where(step < 0, np.iinfo(np.intp).min, np.iinfo(np.intp).max)

    return _slice(a, start, stop, step)

# === NexusCore/openenv\Lib\site-packages\aiohttp\connector.py ===
import asyncio
import functools
import random
import socket
import sys
import traceback
import warnings
from collections import OrderedDict, defaultdict, deque
from contextlib import suppress
from http import HTTPStatus
from itertools import chain, cycle, islice
from time import monotonic
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

import aiohappyeyeballs
from aiohappyeyeballs import AddrInfoType, SocketFactoryType

from . import hdrs, helpers
from .abc import AbstractResolver, ResolveResult
from .client_exceptions import (
    ClientConnectionError,
    ClientConnectorCertificateError,
    ClientConnectorDNSError,
    ClientConnectorError,
    ClientConnectorSSLError,
    ClientHttpProxyError,
    ClientProxyConnectionError,
    ServerFingerprintMismatch,
    UnixClientConnectorError,
    cert_errors,
    ssl_errors,
)
from .client_proto import ResponseHandler
from .client_reqrep import ClientRequest, Fingerprint, _merge_ssl_params
from .helpers import (
    _SENTINEL,
    ceil_timeout,
    is_ip_address,
    noop,
    sentinel,
    set_exception,
    set_result,
)
from .log import client_logger
from .resolver import DefaultResolver

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
else:
    Buffer = Union[bytes, bytearray, "memoryview[int]", "memoryview[bytes]"]

if TYPE_CHECKING:
    import ssl

    SSLContext = ssl.SSLContext
else:
    try:
        import ssl

        SSLContext = ssl.SSLContext
    except ImportError:  # pragma: no cover
        ssl = None  # type: ignore[assignment]
        SSLContext = object  # type: ignore[misc,assignment]

EMPTY_SCHEMA_SET = frozenset({""})
HTTP_SCHEMA_SET = frozenset({"http", "https"})
WS_SCHEMA_SET = frozenset({"ws", "wss"})

HTTP_AND_EMPTY_SCHEMA_SET = HTTP_SCHEMA_SET | EMPTY_SCHEMA_SET
HIGH_LEVEL_SCHEMA_SET = HTTP_AND_EMPTY_SCHEMA_SET | WS_SCHEMA_SET

NEEDS_CLEANUP_CLOSED = (3, 13, 0) <= sys.version_info < (
    3,
    13,
    1,
) or sys.version_info < (3, 12, 7)
# Cleanup closed is no longer needed after https://github.com/python/cpython/pull/118960
# which first appeared in Python 3.12.7 and 3.13.1


__all__ = (
    "BaseConnector",
    "TCPConnector",
    "UnixConnector",
    "NamedPipeConnector",
    "AddrInfoType",
    "SocketFactoryType",
)


if TYPE_CHECKING:
    from .client import ClientTimeout
    from .client_reqrep import ConnectionKey
    from .tracing import Trace


class _DeprecationWaiter:
    __slots__ = ("_awaitable", "_awaited")

    def __init__(self, awaitable: Awaitable[Any]) -> None:
        self._awaitable = awaitable
        self._awaited = False

    def __await__(self) -> Any:
        self._awaited = True
        return self._awaitable.__await__()

    def __del__(self) -> None:
        if not self._awaited:
            warnings.warn(
                "Connector.close() is a coroutine, "
                "please use await connector.close()",
                DeprecationWarning,
            )


async def _wait_for_close(waiters: List[Awaitable[object]]) -> None:
    """Wait for all waiters to finish closing."""
    results = await asyncio.gather(*waiters, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            client_logger.debug("Error while closing connector: %r", res)


class Connection:

    _source_traceback = None

    def __init__(
        self,
        connector: "BaseConnector",
        key: "ConnectionKey",
        protocol: ResponseHandler,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._key = key
        self._connector = connector
        self._loop = loop
        self._protocol: Optional[ResponseHandler] = protocol
        self._callbacks: List[Callable[[], None]] = []

        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

    def __repr__(self) -> str:
        return f"Connection<{self._key}>"

    def __del__(self, _warnings: Any = warnings) -> None:
        if self._protocol is not None:
            kwargs = {"source": self}
            _warnings.warn(f"Unclosed connection {self!r}", ResourceWarning, **kwargs)
            if self._loop.is_closed():
                return

            self._connector._release(self._key, self._protocol, should_close=True)

            context = {"client_connection": self, "message": "Unclosed connection"}
            if self._source_traceback is not None:
                context["source_traceback"] = self._source_traceback
            self._loop.call_exception_handler(context)

    def __bool__(self) -> Literal[True]:
        """Force subclasses to not be falsy, to make checks simpler."""
        return True

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        warnings.warn(
            "connector.loop property is deprecated", DeprecationWarning, stacklevel=2
        )
        return self._loop

    @property
    def transport(self) -> Optional[asyncio.Transport]:
        if self._protocol is None:
            return None
        return self._protocol.transport

    @property
    def protocol(self) -> Optional[ResponseHandler]:
        return self._protocol

    def add_callback(self, callback: Callable[[], None]) -> None:
        if callback is not None:
            self._callbacks.append(callback)

    def _notify_release(self) -> None:
        callbacks, self._callbacks = self._callbacks[:], []

        for cb in callbacks:
            with suppress(Exception):
                cb()

    def close(self) -> None:
        self._notify_release()

        if self._protocol is not None:
            self._connector._release(self._key, self._protocol, should_close=True)
            self._protocol = None

    def release(self) -> None:
        self._notify_release()

        if self._protocol is not None:
            self._connector._release(self._key, self._protocol)
            self._protocol = None

    @property
    def closed(self) -> bool:
        return self._protocol is None or not self._protocol.is_connected()


class _TransportPlaceholder:
    """placeholder for BaseConnector.connect function"""

    __slots__ = ("closed", "transport")

    def __init__(self, closed_future: asyncio.Future[Optional[Exception]]) -> None:
        """Initialize a placeholder for a transport."""
        self.closed = closed_future
        self.transport = None

    def close(self) -> None:
        """Close the placeholder."""

    def abort(self) -> None:
        """Abort the placeholder (does nothing)."""


class BaseConnector:
    """Base connector class.

    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    enable_cleanup_closed - Enables clean-up closed ssl transports.
                            Disabled by default.
    timeout_ceil_threshold - Trigger ceiling of timeout values when
                             it's above timeout_ceil_threshold.
    loop - Optional event loop.
    """

    _closed = True  # prevent AttributeError in __del__ if ctor was failed
    _source_traceback = None

    # abort transport after 2 seconds (cleanup broken connections)
    _cleanup_closed_period = 2.0

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET

    def __init__(
        self,
        *,
        keepalive_timeout: Union[object, None, float] = sentinel,
        force_close: bool = False,
        limit: int = 100,
        limit_per_host: int = 0,
        enable_cleanup_closed: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        timeout_ceil_threshold: float = 5,
    ) -> None:

        if force_close:
            if keepalive_timeout is not None and keepalive_timeout is not sentinel:
                raise ValueError(
                    "keepalive_timeout cannot be set if force_close is True"
                )
        else:
            if keepalive_timeout is sentinel:
                keepalive_timeout = 15.0

        loop = loop or asyncio.get_running_loop()
        self._timeout_ceil_threshold = timeout_ceil_threshold

        self._closed = False
        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

        # Connection pool of reusable connections.
        # We use a deque to store connections because it has O(1) popleft()
        # and O(1) append() operations to implement a FIFO queue.
        self._conns: DefaultDict[
            ConnectionKey, Deque[Tuple[ResponseHandler, float]]
        ] = defaultdict(deque)
        self._limit = limit
        self._limit_per_host = limit_per_host
        self._acquired: Set[ResponseHandler] = set()
        self._acquired_per_host: DefaultDict[ConnectionKey, Set[ResponseHandler]] = (
            defaultdict(set)
        )
        self._keepalive_timeout = cast(float, keepalive_timeout)
        self._force_close = force_close

        # {host_key: FIFO list of waiters}
        # The FIFO is implemented with an OrderedDict with None keys because
        # python does not have an ordered set.
        self._waiters: DefaultDict[
            ConnectionKey, OrderedDict[asyncio.Future[None], None]
        ] = defaultdict(OrderedDict)

        self._loop = loop
        self._factory = functools.partial(ResponseHandler, loop=loop)

        # start keep-alive connection cleanup task
        self._cleanup_handle: Optional[asyncio.TimerHandle] = None

        # start cleanup closed transports task
        self._cleanup_closed_handle: Optional[asyncio.TimerHandle] = None

        if enable_cleanup_closed and not NEEDS_CLEANUP_CLOSED:
            warnings.warn(
                "enable_cleanup_closed ignored because "
                "https://github.com/python/cpython/pull/118960 is fixed "
                f"in Python version {sys.version_info}",
                DeprecationWarning,
                stacklevel=2,
            )
            enable_cleanup_closed = False

        self._cleanup_closed_disabled = not enable_cleanup_closed
        self._cleanup_closed_transports: List[Optional[asyncio.Transport]] = []
        self._placeholder_future: asyncio.Future[Optional[Exception]] = (
            loop.create_future()
        )
        self._placeholder_future.set_result(None)
        self._cleanup_closed()

    def __del__(self, _warnings: Any = warnings) -> None:
        if self._closed:
            return
        if not self._conns:
            return

        conns = [repr(c) for c in self._conns.values()]

        self._close()

        kwargs = {"source": self}
        _warnings.warn(f"Unclosed connector {self!r}", ResourceWarning, **kwargs)
        context = {
            "connector": self,
            "connections": conns,
            "message": "Unclosed connector",
        }
        if self._source_traceback is not None:
            context["source_traceback"] = self._source_traceback
        self._loop.call_exception_handler(context)

    def __enter__(self) -> "BaseConnector":
        warnings.warn(
            '"with Connector():" is deprecated, '
            'use "async with Connector():" instead',
            DeprecationWarning,
        )
        return self

    def __exit__(self, *exc: Any) -> None:
        self._close()

    async def __aenter__(self) -> "BaseConnector":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_value: Optional[BaseException] = None,
        exc_traceback: Optional[TracebackType] = None,
    ) -> None:
        await self.close()

    @property
    def force_close(self) -> bool:
        """Ultimately close connection on releasing if True."""
        return self._force_close

    @property
    def limit(self) -> int:
        """The total number for simultaneous connections.

        If limit is 0 the connector has no limit.
        The default limit size is 100.
        """
        return self._limit

    @property
    def limit_per_host(self) -> int:
        """The limit for simultaneous connections to the same endpoint.

        Endpoints are the same if they are have equal
        (host, port, is_ssl) triple.
        """
        return self._limit_per_host

    def _cleanup(self) -> None:
        """Cleanup unused transports."""
        if self._cleanup_handle:
            self._cleanup_handle.cancel()
            # _cleanup_handle should be unset, otherwise _release() will not
            # recreate it ever!
            self._cleanup_handle = None

        now = monotonic()
        timeout = self._keepalive_timeout

        if self._conns:
            connections = defaultdict(deque)
            deadline = now - timeout
            for key, conns in self._conns.items():
                alive: Deque[Tuple[ResponseHandler, float]] = deque()
                for proto, use_time in conns:
                    if proto.is_connected() and use_time - deadline >= 0:
                        alive.append((proto, use_time))
                        continue
                    transport = proto.transport
                    proto.close()
                    if not self._cleanup_closed_disabled and key.is_ssl:
                        self._cleanup_closed_transports.append(transport)

                if alive:
                    connections[key] = alive

            self._conns = connections

        if self._conns:
            self._cleanup_handle = helpers.weakref_handle(
                self,
                "_cleanup",
                timeout,
                self._loop,
                timeout_ceil_threshold=self._timeout_ceil_threshold,
            )

    def _cleanup_closed(self) -> None:
        """Double confirmation for transport close.

        Some broken ssl servers may leave socket open without proper close.
        """
        if self._cleanup_closed_handle:
            self._cleanup_closed_handle.cancel()

        for transport in self._cleanup_closed_transports:
            if transport is not None:
                transport.abort()

        self._cleanup_closed_transports = []

        if not self._cleanup_closed_disabled:
            self._cleanup_closed_handle = helpers.weakref_handle(
                self,
                "_cleanup_closed",
                self._cleanup_closed_period,
                self._loop,
                timeout_ceil_threshold=self._timeout_ceil_threshold,
            )

    def close(self, *, abort_ssl: bool = False) -> Awaitable[None]:
        """Close all opened transports.

        :param abort_ssl: If True, SSL connections will be aborted immediately
                         without performing the shutdown handshake. This provides
                         faster cleanup at the cost of less graceful disconnection.
        """
        if not (waiters := self._close(abort_ssl=abort_ssl)):
            # If there are no connections to close, we can return a noop
            # awaitable to avoid scheduling a task on the event loop.
            return _DeprecationWaiter(noop())
        coro = _wait_for_close(waiters)
        if sys.version_info >= (3, 12):
            # Optimization for Python 3.12, try to close connections
            # immediately to avoid having to schedule the task on the event loop.
            task = asyncio.Task(coro, loop=self._loop, eager_start=True)
        else:
            task = self._loop.create_task(coro)
        return _DeprecationWaiter(task)

    def _close(self, *, abort_ssl: bool = False) -> List[Awaitable[object]]:
        waiters: List[Awaitable[object]] = []

        if self._closed:
            return waiters

        self._closed = True

        try:
            if self._loop.is_closed():
                return waiters

            # cancel cleanup task
            if self._cleanup_handle:
                self._cleanup_handle.cancel()

            # cancel cleanup close task
            if self._cleanup_closed_handle:
                self._cleanup_closed_handle.cancel()

            for data in self._conns.values():
                for proto, _ in data:
                    if (
                        abort_ssl
                        and proto.transport
                        and proto.transport.get_extra_info("sslcontext") is not None
                    ):
                        proto.abort()
                    else:
                        proto.close()
                    if closed := proto.closed:
                        waiters.append(closed)

            for proto in self._acquired:
                if (
                    abort_ssl
                    and proto.transport
                    and proto.transport.get_extra_info("sslcontext") is not None
                ):
                    proto.abort()
                else:
                    proto.close()
                if closed := proto.closed:
                    waiters.append(closed)

            for transport in self._cleanup_closed_transports:
                if transport is not None:
                    transport.abort()

            return waiters

        finally:
            self._conns.clear()
            self._acquired.clear()
            for keyed_waiters in self._waiters.values():
                for keyed_waiter in keyed_waiters:
                    keyed_waiter.cancel()
            self._waiters.clear()
            self._cleanup_handle = None
            self._cleanup_closed_transports.clear()
            self._cleanup_closed_handle = None

    @property
    def closed(self) -> bool:
        """Is connector closed.

        A readonly property.
        """
        return self._closed

    def _available_connections(self, key: "ConnectionKey") -> int:
        """
        Return number of available connections.

        The limit, limit_per_host and the connection key are taken into account.

        If it returns less than 1 means that there are no connections
        available.
        """
        # check total available connections
        # If there are no limits, this will always return 1
        total_remain = 1

        if self._limit and (total_remain := self._limit - len(self._acquired)) <= 0:
            return total_remain

        # check limit per host
        if host_remain := self._limit_per_host:
            if acquired := self._acquired_per_host.get(key):
                host_remain -= len(acquired)
            if total_remain > host_remain:
                return host_remain

        return total_remain

    async def connect(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> Connection:
        """Get from pool or create new connection."""
        key = req.connection_key
        if (conn := await self._get(key, traces)) is not None:
            # If we do not have to wait and we can get a connection from the pool
            # we can avoid the timeout ceil logic and directly return the connection
            return conn

        async with ceil_timeout(timeout.connect, timeout.ceil_threshold):
            if self._available_connections(key) <= 0:
                await self._wait_for_available_connection(key, traces)
                if (conn := await self._get(key, traces)) is not None:
                    return conn

            placeholder = cast(
                ResponseHandler, _TransportPlaceholder(self._placeholder_future)
            )
            self._acquired.add(placeholder)
            if self._limit_per_host:
                self._acquired_per_host[key].add(placeholder)

            try:
                # Traces are done inside the try block to ensure that the
                # that the placeholder is still cleaned up if an exception
                # is raised.
                if traces:
                    for trace in traces:
                        await trace.send_connection_create_start()
                proto = await self._create_connection(req, traces, timeout)
                if traces:
                    for trace in traces:
                        await trace.send_connection_create_end()
            except BaseException:
                self._release_acquired(key, placeholder)
                raise
            else:
                if self._closed:
                    proto.close()
                    raise ClientConnectionError("Connector is closed.")

        # The connection was successfully created, drop the placeholder
        # and add the real connection to the acquired set. There should
        # be no awaits after the proto is added to the acquired set
        # to ensure that the connection is not left in the acquired set
        # on cancellation.
        self._acquired.remove(placeholder)
        self._acquired.add(proto)
        if self._limit_per_host:
            acquired_per_host = self._acquired_per_host[key]
            acquired_per_host.remove(placeholder)
            acquired_per_host.add(proto)
        return Connection(self, key, proto, self._loop)

    async def _wait_for_available_connection(
        self, key: "ConnectionKey", traces: List["Trace"]
    ) -> None:
        """Wait for an available connection slot."""
        # We loop here because there is a race between
        # the connection limit check and the connection
        # being acquired. If the connection is acquired
        # between the check and the await statement, we
        # need to loop again to check if the connection
        # slot is still available.
        attempts = 0
        while True:
            fut: asyncio.Future[None] = self._loop.create_future()
            keyed_waiters = self._waiters[key]
            keyed_waiters[fut] = None
            if attempts:
                # If we have waited before, we need to move the waiter
                # to the front of the queue as otherwise we might get
                # starved and hit the timeout.
                keyed_waiters.move_to_end(fut, last=False)

            try:
                # Traces happen in the try block to ensure that the
                # the waiter is still cleaned up if an exception is raised.
                if traces:
                    for trace in traces:
                        await trace.send_connection_queued_start()
                await fut
                if traces:
                    for trace in traces:
                        await trace.send_connection_queued_end()
            finally:
                # pop the waiter from the queue if its still
                # there and not already removed by _release_waiter
                keyed_waiters.pop(fut, None)
                if not self._waiters.get(key, True):
                    del self._waiters[key]

            if self._available_connections(key) > 0:
                break
            attempts += 1

    async def _get(
        self, key: "ConnectionKey", traces: List["Trace"]
    ) -> Optional[Connection]:
        """Get next reusable connection for the key or None.

        The connection will be marked as acquired.
        """
        if (conns := self._conns.get(key)) is None:
            return None

        t1 = monotonic()
        while conns:
            proto, t0 = conns.popleft()
            # We will we reuse the connection if its connected and
            # the keepalive timeout has not been exceeded
            if proto.is_connected() and t1 - t0 <= self._keepalive_timeout:
                if not conns:
                    # The very last connection was reclaimed: drop the key
                    del self._conns[key]
                self._acquired.add(proto)
                if self._limit_per_host:
                    self._acquired_per_host[key].add(proto)
                if traces:
                    for trace in traces:
                        try:
                            await trace.send_connection_reuseconn()
                        except BaseException:
                            self._release_acquired(key, proto)
                            raise
                return Connection(self, key, proto, self._loop)

            # Connection cannot be reused, close it
            transport = proto.transport
            proto.close()
            # only for SSL transports
            if not self._cleanup_closed_disabled and key.is_ssl:
                self._cleanup_closed_transports.append(transport)

        # No more connections: drop the key
        del self._conns[key]
        return None

    def _release_waiter(self) -> None:
        """
        Iterates over all waiters until one to be released is found.

        The one to be released is not finished and
        belongs to a host that has available connections.
        """
        if not self._waiters:
            return

        # Having the dict keys ordered this avoids to iterate
        # at the same order at each call.
        queues = list(self._waiters)
        random.shuffle(queues)

        for key in queues:
            if self._available_connections(key) < 1:
                continue

            waiters = self._waiters[key]
            while waiters:
                waiter, _ = waiters.popitem(last=False)
                if not waiter.done():
                    waiter.set_result(None)
                    return

    def _release_acquired(self, key: "ConnectionKey", proto: ResponseHandler) -> None:
        """Release acquired connection."""
        if self._closed:
            # acquired connection is already released on connector closing
            return

        self._acquired.discard(proto)
        if self._limit_per_host and (conns := self._acquired_per_host.get(key)):
            conns.discard(proto)
            if not conns:
                del self._acquired_per_host[key]
        self._release_waiter()

    def _release(
        self,
        key: "ConnectionKey",
        protocol: ResponseHandler,
        *,
        should_close: bool = False,
    ) -> None:
        if self._closed:
            # acquired connection is already released on connector closing
            return

        self._release_acquired(key, protocol)

        if self._force_close or should_close or protocol.should_close:
            transport = protocol.transport
            protocol.close()

            if key.is_ssl and not self._cleanup_closed_disabled:
                self._cleanup_closed_transports.append(transport)
            return

        self._conns[key].append((protocol, monotonic()))

        if self._cleanup_handle is None:
            self._cleanup_handle = helpers.weakref_handle(
                self,
                "_cleanup",
                self._keepalive_timeout,
                self._loop,
                timeout_ceil_threshold=self._timeout_ceil_threshold,
            )

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        raise NotImplementedError()


class _DNSCacheTable:
    def __init__(self, ttl: Optional[float] = None) -> None:
        self._addrs_rr: Dict[Tuple[str, int], Tuple[Iterator[ResolveResult], int]] = {}
        self._timestamps: Dict[Tuple[str, int], float] = {}
        self._ttl = ttl

    def __contains__(self, host: object) -> bool:
        return host in self._addrs_rr

    def add(self, key: Tuple[str, int], addrs: List[ResolveResult]) -> None:
        self._addrs_rr[key] = (cycle(addrs), len(addrs))

        if self._ttl is not None:
            self._timestamps[key] = monotonic()

    def remove(self, key: Tuple[str, int]) -> None:
        self._addrs_rr.pop(key, None)

        if self._ttl is not None:
            self._timestamps.pop(key, None)

    def clear(self) -> None:
        self._addrs_rr.clear()
        self._timestamps.clear()

    def next_addrs(self, key: Tuple[str, int]) -> List[ResolveResult]:
        loop, length = self._addrs_rr[key]
        addrs = list(islice(loop, length))
        # Consume one more element to shift internal state of `cycle`
        next(loop)
        return addrs

    def expired(self, key: Tuple[str, int]) -> bool:
        if self._ttl is None:
            return False

        return self._timestamps[key] + self._ttl < monotonic()


def _make_ssl_context(verified: bool) -> SSLContext:
    """Create SSL context.

    This method is not async-friendly and should be called from a thread
    because it will load certificates from disk and do other blocking I/O.
    """
    if ssl is None:
        # No ssl support
        return None
    if verified:
        sslcontext = ssl.create_default_context()
    else:
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        sslcontext.options |= ssl.OP_NO_SSLv2
        sslcontext.options |= ssl.OP_NO_SSLv3
        sslcontext.check_hostname = False
        sslcontext.verify_mode = ssl.CERT_NONE
        sslcontext.options |= ssl.OP_NO_COMPRESSION
        sslcontext.set_default_verify_paths()
    sslcontext.set_alpn_protocols(("http/1.1",))
    return sslcontext


# The default SSLContext objects are created at import time
# since they do blocking I/O to load certificates from disk,
# and imports should always be done before the event loop starts
# or in a thread.
_SSL_CONTEXT_VERIFIED = _make_ssl_context(True)
_SSL_CONTEXT_UNVERIFIED = _make_ssl_context(False)


class TCPConnector(BaseConnector):
    """TCP connector.

    verify_ssl - Set to True to check ssl certifications.
    fingerprint - Pass the binary sha256
        digest of the expected certificate in DER format to verify
        that the certificate the server presents matches. See also
        https://en.wikipedia.org/wiki/HTTP_Public_Key_Pinning
    resolver - Enable DNS lookups and use this
        resolver
    use_dns_cache - Use memory cache for DNS lookups.
    ttl_dns_cache - Max seconds having cached a DNS entry, None forever.
    family - socket address family
    local_addr - local tuple of (host, port) to bind socket to

    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    enable_cleanup_closed - Enables clean-up closed ssl transports.
                            Disabled by default.
    happy_eyeballs_delay - This is the “Connection Attempt Delay”
                           as defined in RFC 8305. To disable
                           the happy eyeballs algorithm, set to None.
    interleave - “First Address Family Count” as defined in RFC 8305
    loop - Optional event loop.
    socket_factory - A SocketFactoryType function that, if supplied,
                     will be used to create sockets given an
                     AddrInfoType.
    ssl_shutdown_timeout - DEPRECATED. Will be removed in aiohttp 4.0.
                           Grace period for SSL shutdown handshake on TLS
                           connections. Default is 0 seconds (immediate abort).
                           This parameter allowed for a clean SSL shutdown by
                           notifying the remote peer of connection closure,
                           while avoiding excessive delays during connector cleanup.
                           Note: Only takes effect on Python 3.11+.
    """

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET | frozenset({"tcp"})

    def __init__(
        self,
        *,
        verify_ssl: bool = True,
        fingerprint: Optional[bytes] = None,
        use_dns_cache: bool = True,
        ttl_dns_cache: Optional[int] = 10,
        family: socket.AddressFamily = socket.AddressFamily.AF_UNSPEC,
        ssl_context: Optional[SSLContext] = None,
        ssl: Union[bool, Fingerprint, SSLContext] = True,
        local_addr: Optional[Tuple[str, int]] = None,
        resolver: Optional[AbstractResolver] = None,
        keepalive_timeout: Union[None, float, object] = sentinel,
        force_close: bool = False,
        limit: int = 100,
        limit_per_host: int = 0,
        enable_cleanup_closed: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        timeout_ceil_threshold: float = 5,
        happy_eyeballs_delay: Optional[float] = 0.25,
        interleave: Optional[int] = None,
        socket_factory: Optional[SocketFactoryType] = None,
        ssl_shutdown_timeout: Union[_SENTINEL, None, float] = sentinel,
    ):
        super().__init__(
            keepalive_timeout=keepalive_timeout,
            force_close=force_close,
            limit=limit,
            limit_per_host=limit_per_host,
            enable_cleanup_closed=enable_cleanup_closed,
            loop=loop,
            timeout_ceil_threshold=timeout_ceil_threshold,
        )

        self._ssl = _merge_ssl_params(ssl, verify_ssl, ssl_context, fingerprint)

        self._resolver: AbstractResolver
        if resolver is None:
            self._resolver = DefaultResolver(loop=self._loop)
            self._resolver_owner = True
        else:
            self._resolver = resolver
            self._resolver_owner = False

        self._use_dns_cache = use_dns_cache
        self._cached_hosts = _DNSCacheTable(ttl=ttl_dns_cache)
        self._throttle_dns_futures: Dict[
            Tuple[str, int], Set["asyncio.Future[None]"]
        ] = {}
        self._family = family
        self._local_addr_infos = aiohappyeyeballs.addr_to_addr_infos(local_addr)
        self._happy_eyeballs_delay = happy_eyeballs_delay
        self._interleave = interleave
        self._resolve_host_tasks: Set["asyncio.Task[List[ResolveResult]]"] = set()
        self._socket_factory = socket_factory
        self._ssl_shutdown_timeout: Optional[float]
        # Handle ssl_shutdown_timeout with warning for Python < 3.11
        if ssl_shutdown_timeout is sentinel:
            self._ssl_shutdown_timeout = 0
        else:
            # Deprecation warning for ssl_shutdown_timeout parameter
            warnings.warn(
                "The ssl_shutdown_timeout parameter is deprecated and will be removed in aiohttp 4.0",
                DeprecationWarning,
                stacklevel=2,
            )
            if (
                sys.version_info < (3, 11)
                and ssl_shutdown_timeout is not None
                and ssl_shutdown_timeout != 0
            ):
                warnings.warn(
                    f"ssl_shutdown_timeout={ssl_shutdown_timeout} is ignored on Python < 3.11; "
                    "only ssl_shutdown_timeout=0 is supported. The timeout will be ignored.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            self._ssl_shutdown_timeout = ssl_shutdown_timeout

    def _close(self, *, abort_ssl: bool = False) -> List[Awaitable[object]]:
        """Close all ongoing DNS calls."""
        for fut in chain.from_iterable(self._throttle_dns_futures.values()):
            fut.cancel()

        waiters = super()._close(abort_ssl=abort_ssl)

        for t in self._resolve_host_tasks:
            t.cancel()
            waiters.append(t)

        return waiters

    async def close(self, *, abort_ssl: bool = False) -> None:
        """
        Close all opened transports.

        :param abort_ssl: If True, SSL connections will be aborted immediately
                         without performing the shutdown handshake. If False (default),
                         the behavior is determined by ssl_shutdown_timeout:
                         - If ssl_shutdown_timeout=0: connections are aborted
                         - If ssl_shutdown_timeout>0: graceful shutdown is performed
        """
        if self._resolver_owner:
            await self._resolver.close()
        # Use abort_ssl param if explicitly set, otherwise use ssl_shutdown_timeout default
        await super().close(abort_ssl=abort_ssl or self._ssl_shutdown_timeout == 0)

    @property
    def family(self) -> int:
        """Socket family like AF_INET."""
        return self._family

    @property
    def use_dns_cache(self) -> bool:
        """True if local DNS caching is enabled."""
        return self._use_dns_cache

    def clear_dns_cache(
        self, host: Optional[str] = None, port: Optional[int] = None
    ) -> None:
        """Remove specified host/port or clear all dns local cache."""
        if host is not None and port is not None:
            self._cached_hosts.remove((host, port))
        elif host is not None or port is not None:
            raise ValueError("either both host and port or none of them are allowed")
        else:
            self._cached_hosts.clear()

    async def _resolve_host(
        self, host: str, port: int, traces: Optional[Sequence["Trace"]] = None
    ) -> List[ResolveResult]:
        """Resolve host and return list of addresses."""
        if is_ip_address(host):
            return [
                {
                    "hostname": host,
                    "host": host,
                    "port": port,
                    "family": self._family,
                    "proto": 0,
                    "flags": 0,
                }
            ]

        if not self._use_dns_cache:

            if traces:
                for trace in traces:
                    await trace.send_dns_resolvehost_start(host)

            res = await self._resolver.resolve(host, port, family=self._family)

            if traces:
                for trace in traces:
                    await trace.send_dns_resolvehost_end(host)

            return res

        key = (host, port)
        if key in self._cached_hosts and not self._cached_hosts.expired(key):
            # get result early, before any await (#4014)
            result = self._cached_hosts.next_addrs(key)

            if traces:
                for trace in traces:
                    await trace.send_dns_cache_hit(host)
            return result

        futures: Set["asyncio.Future[None]"]
        #
        # If multiple connectors are resolving the same host, we wait
        # for the first one to resolve and then use the result for all of them.
        # We use a throttle to ensure that we only resolve the host once
        # and then use the result for all the waiters.
        #
        if key in self._throttle_dns_futures:
            # get futures early, before any await (#4014)
            futures = self._throttle_dns_futures[key]
            future: asyncio.Future[None] = self._loop.create_future()
            futures.add(future)
            if traces:
                for trace in traces:
                    await trace.send_dns_cache_hit(host)
            try:
                await future
            finally:
                futures.discard(future)
            return self._cached_hosts.next_addrs(key)

        # update dict early, before any await (#4014)
        self._throttle_dns_futures[key] = futures = set()
        # In this case we need to create a task to ensure that we can shield
        # the task from cancellation as cancelling this lookup should not cancel
        # the underlying lookup or else the cancel event will get broadcast to
        # all the waiters across all connections.
        #
        coro = self._resolve_host_with_throttle(key, host, port, futures, traces)
        loop = asyncio.get_running_loop()
        if sys.version_info >= (3, 12):
            # Optimization for Python 3.12, try to send immediately
            resolved_host_task = asyncio.Task(coro, loop=loop, eager_start=True)
        else:
            resolved_host_task = loop.create_task(coro)

        if not resolved_host_task.done():
            self._resolve_host_tasks.add(resolved_host_task)
            resolved_host_task.add_done_callback(self._resolve_host_tasks.discard)

        try:
            return await asyncio.shield(resolved_host_task)
        except asyncio.CancelledError:

            def drop_exception(fut: "asyncio.Future[List[ResolveResult]]") -> None:
                with suppress(Exception, asyncio.CancelledError):
                    fut.result()

            resolved_host_task.add_done_callback(drop_exception)
            raise

    async def _resolve_host_with_throttle(
        self,
        key: Tuple[str, int],
        host: str,
        port: int,
        futures: Set["asyncio.Future[None]"],
        traces: Optional[Sequence["Trace"]],
    ) -> List[ResolveResult]:
        """Resolve host and set result for all waiters.

        This method must be run in a task and shielded from cancellation
        to avoid cancelling the underlying lookup.
        """
        try:
            if traces:
                for trace in traces:
                    await trace.send_dns_cache_miss(host)

                for trace in traces:
                    await trace.send_dns_resolvehost_start(host)

            addrs = await self._resolver.resolve(host, port, family=self._family)
            if traces:
                for trace in traces:
                    await trace.send_dns_resolvehost_end(host)

            self._cached_hosts.add(key, addrs)
            for fut in futures:
                set_result(fut, None)
        except BaseException as e:
            # any DNS exception is set for the waiters to raise the same exception.
            # This coro is always run in task that is shielded from cancellation so
            # we should never be propagating cancellation here.
            for fut in futures:
                set_exception(fut, e)
            raise
        finally:
            self._throttle_dns_futures.pop(key)

        return self._cached_hosts.next_addrs(key)

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        """Create connection.

        Has same keyword arguments as BaseEventLoop.create_connection.
        """
        if req.proxy:
            _, proto = await self._create_proxy_connection(req, traces, timeout)
        else:
            _, proto = await self._create_direct_connection(req, traces, timeout)

        return proto

    def _get_ssl_context(self, req: ClientRequest) -> Optional[SSLContext]:
        """Logic to get the correct SSL context

        0. if req.ssl is false, return None

        1. if ssl_context is specified in req, use it
        2. if _ssl_context is specified in self, use it
        3. otherwise:
            1. if verify_ssl is not specified in req, use self.ssl_context
               (will generate a default context according to self.verify_ssl)
            2. if verify_ssl is True in req, generate a default SSL context
            3. if verify_ssl is False in req, generate a SSL context that
               won't verify
        """
        if not req.is_ssl():
            return None

        if ssl is None:  # pragma: no cover
            raise RuntimeError("SSL is not supported.")
        sslcontext = req.ssl
        if isinstance(sslcontext, ssl.SSLContext):
            return sslcontext
        if sslcontext is not True:
            # not verified or fingerprinted
            return _SSL_CONTEXT_UNVERIFIED
        sslcontext = self._ssl
        if isinstance(sslcontext, ssl.SSLContext):
            return sslcontext
        if sslcontext is not True:
            # not verified or fingerprinted
            return _SSL_CONTEXT_UNVERIFIED
        return _SSL_CONTEXT_VERIFIED

    def _get_fingerprint(self, req: ClientRequest) -> Optional["Fingerprint"]:
        ret = req.ssl
        if isinstance(ret, Fingerprint):
            return ret
        ret = self._ssl
        if isinstance(ret, Fingerprint):
            return ret
        return None

    async def _wrap_create_connection(
        self,
        *args: Any,
        addr_infos: List[AddrInfoType],
        req: ClientRequest,
        timeout: "ClientTimeout",
        client_error: Type[Exception] = ClientConnectorError,
        **kwargs: Any,
    ) -> Tuple[asyncio.Transport, ResponseHandler]:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                sock = await aiohappyeyeballs.start_connection(
                    addr_infos=addr_infos,
                    local_addr_infos=self._local_addr_infos,
                    happy_eyeballs_delay=self._happy_eyeballs_delay,
                    interleave=self._interleave,
                    loop=self._loop,
                    socket_factory=self._socket_factory,
                )
                # Add ssl_shutdown_timeout for Python 3.11+ when SSL is used
                if (
                    kwargs.get("ssl")
                    and self._ssl_shutdown_timeout
                    and sys.version_info >= (3, 11)
                ):
                    kwargs["ssl_shutdown_timeout"] = self._ssl_shutdown_timeout
                return await self._loop.create_connection(*args, **kwargs, sock=sock)
        except cert_errors as exc:
            raise ClientConnectorCertificateError(req.connection_key, exc) from exc
        except ssl_errors as exc:
            raise ClientConnectorSSLError(req.connection_key, exc) from exc
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise client_error(req.connection_key, exc) from exc

    async def _wrap_existing_connection(
        self,
        *args: Any,
        req: ClientRequest,
        timeout: "ClientTimeout",
        client_error: Type[Exception] = ClientConnectorError,
        **kwargs: Any,
    ) -> Tuple[asyncio.Transport, ResponseHandler]:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                return await self._loop.create_connection(*args, **kwargs)
        except cert_errors as exc:
            raise ClientConnectorCertificateError(req.connection_key, exc) from exc
        except ssl_errors as exc:
            raise ClientConnectorSSLError(req.connection_key, exc) from exc
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise client_error(req.connection_key, exc) from exc

    def _fail_on_no_start_tls(self, req: "ClientRequest") -> None:
        """Raise a :py:exc:`RuntimeError` on missing ``start_tls()``.

        It is necessary for TLS-in-TLS so that it is possible to
        send HTTPS queries through HTTPS proxies.

        This doesn't affect regular HTTP requests, though.
        """
        if not req.is_ssl():
            return

        proxy_url = req.proxy
        assert proxy_url is not None
        if proxy_url.scheme != "https":
            return

        self._check_loop_for_start_tls()

    def _check_loop_for_start_tls(self) -> None:
        try:
            self._loop.start_tls
        except AttributeError as attr_exc:
            raise RuntimeError(
                "An HTTPS request is being sent through an HTTPS proxy. "
                "This needs support for TLS in TLS but it is not implemented "
                "in your runtime for the stdlib asyncio.\n\n"
                "Please upgrade to Python 3.11 or higher. For more details, "
                "please see:\n"
                "* https://bugs.python.org/issue37179\n"
                "* https://github.com/python/cpython/pull/28073\n"
                "* https://docs.aiohttp.org/en/stable/"
                "client_advanced.html#proxy-support\n"
                "* https://github.com/aio-libs/aiohttp/discussions/6044\n",
            ) from attr_exc

    def _loop_supports_start_tls(self) -> bool:
        try:
            self._check_loop_for_start_tls()
        except RuntimeError:
            return False
        else:
            return True

    def _warn_about_tls_in_tls(
        self,
        underlying_transport: asyncio.Transport,
        req: ClientRequest,
    ) -> None:
        """Issue a warning if the requested URL has HTTPS scheme."""
        if req.request_info.url.scheme != "https":
            return

        # Check if uvloop is being used, which supports TLS in TLS,
        # otherwise assume that asyncio's native transport is being used.
        if type(underlying_transport).__module__.startswith("uvloop"):
            return

        # Support in asyncio was added in Python 3.11 (bpo-44011)
        asyncio_supports_tls_in_tls = sys.version_info >= (3, 11) or getattr(
            underlying_transport,
            "_start_tls_compatible",
            False,
        )

        if asyncio_supports_tls_in_tls:
            return

        warnings.warn(
            "An HTTPS request is being sent through an HTTPS proxy. "
            "This support for TLS in TLS is known to be disabled "
            "in the stdlib asyncio (Python <3.11). This is why you'll probably see "
            "an error in the log below.\n\n"
            "It is possible to enable it via monkeypatching. "
            "For more details, see:\n"
            "* https://bugs.python.org/issue37179\n"
            "* https://github.com/python/cpython/pull/28073\n\n"
            "You can temporarily patch this as follows:\n"
            "* https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support\n"
            "* https://github.com/aio-libs/aiohttp/discussions/6044\n",
            RuntimeWarning,
            source=self,
            # Why `4`? At least 3 of the calls in the stack originate
            # from the methods in this class.
            stacklevel=3,
        )

    async def _start_tls_connection(
        self,
        underlying_transport: asyncio.Transport,
        req: ClientRequest,
        timeout: "ClientTimeout",
        client_error: Type[Exception] = ClientConnectorError,
    ) -> Tuple[asyncio.BaseTransport, ResponseHandler]:
        """Wrap the raw TCP transport with TLS."""
        tls_proto = self._factory()  # Create a brand new proto for TLS
        sslcontext = self._get_ssl_context(req)
        if TYPE_CHECKING:
            # _start_tls_connection is unreachable in the current code path
            # if sslcontext is None.
            assert sslcontext is not None

        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                try:
                    # ssl_shutdown_timeout is only available in Python 3.11+
                    if sys.version_info >= (3, 11) and self._ssl_shutdown_timeout:
                        tls_transport = await self._loop.start_tls(
                            underlying_transport,
                            tls_proto,
                            sslcontext,
                            server_hostname=req.server_hostname or req.host,
                            ssl_handshake_timeout=timeout.total,
                            ssl_shutdown_timeout=self._ssl_shutdown_timeout,
                        )
                    else:
                        tls_transport = await self._loop.start_tls(
                            underlying_transport,
                            tls_proto,
                            sslcontext,
                            server_hostname=req.server_hostname or req.host,
                            ssl_handshake_timeout=timeout.total,
                        )
                except BaseException:
                    # We need to close the underlying transport since
                    # `start_tls()` probably failed before it had a
                    # chance to do this:
                    if self._ssl_shutdown_timeout == 0:
                        underlying_transport.abort()
                    else:
                        underlying_transport.close()
                    raise
                if isinstance(tls_transport, asyncio.Transport):
                    fingerprint = self._get_fingerprint(req)
                    if fingerprint:
                        try:
                            fingerprint.check(tls_transport)
                        except ServerFingerprintMismatch:
                            tls_transport.close()
                            if not self._cleanup_closed_disabled:
                                self._cleanup_closed_transports.append(tls_transport)
                            raise
        except cert_errors as exc:
            raise ClientConnectorCertificateError(req.connection_key, exc) from exc
        except ssl_errors as exc:
            raise ClientConnectorSSLError(req.connection_key, exc) from exc
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise client_error(req.connection_key, exc) from exc
        except TypeError as type_err:
            # Example cause looks like this:
            # TypeError: transport <asyncio.sslproto._SSLProtocolTransport
            # object at 0x7f760615e460> is not supported by start_tls()

            raise ClientConnectionError(
                "Cannot initialize a TLS-in-TLS connection to host "
                f"{req.host!s}:{req.port:d} through an underlying connection "
                f"to an HTTPS proxy {req.proxy!s} ssl:{req.ssl or 'default'} "
                f"[{type_err!s}]"
            ) from type_err
        else:
            if tls_transport is None:
                msg = "Failed to start TLS (possibly caused by closing transport)"
                raise client_error(req.connection_key, OSError(msg))
            tls_proto.connection_made(
                tls_transport
            )  # Kick the state machine of the new TLS protocol

        return tls_transport, tls_proto

    def _convert_hosts_to_addr_infos(
        self, hosts: List[ResolveResult]
    ) -> List[AddrInfoType]:
        """Converts the list of hosts to a list of addr_infos.

        The list of hosts is the result of a DNS lookup. The list of
        addr_infos is the result of a call to `socket.getaddrinfo()`.
        """
        addr_infos: List[AddrInfoType] = []
        for hinfo in hosts:
            host = hinfo["host"]
            is_ipv6 = ":" in host
            family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
            if self._family and self._family != family:
                continue
            addr = (host, hinfo["port"], 0, 0) if is_ipv6 else (host, hinfo["port"])
            addr_infos.append(
                (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", addr)
            )
        return addr_infos

    async def _create_direct_connection(
        self,
        req: ClientRequest,
        traces: List["Trace"],
        timeout: "ClientTimeout",
        *,
        client_error: Type[Exception] = ClientConnectorError,
    ) -> Tuple[asyncio.Transport, ResponseHandler]:
        sslcontext = self._get_ssl_context(req)
        fingerprint = self._get_fingerprint(req)

        host = req.url.raw_host
        assert host is not None
        # Replace multiple trailing dots with a single one.
        # A trailing dot is only present for fully-qualified domain names.
        # See https://github.com/aio-libs/aiohttp/pull/7364.
        if host.endswith(".."):
            host = host.rstrip(".") + "."
        port = req.port
        assert port is not None
        try:
            # Cancelling this lookup should not cancel the underlying lookup
            #  or else the cancel event will get broadcast to all the waiters
            #  across all connections.
            hosts = await self._resolve_host(host, port, traces=traces)
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            # in case of proxy it is not ClientProxyConnectionError
            # it is problem of resolving proxy ip itself
            raise ClientConnectorDNSError(req.connection_key, exc) from exc

        last_exc: Optional[Exception] = None
        addr_infos = self._convert_hosts_to_addr_infos(hosts)
        while addr_infos:
            # Strip trailing dots, certificates contain FQDN without dots.
            # See https://github.com/aio-libs/aiohttp/issues/3636
            server_hostname = (
                (req.server_hostname or host).rstrip(".") if sslcontext else None
            )

            try:
                transp, proto = await self._wrap_create_connection(
                    self._factory,
                    timeout=timeout,
                    ssl=sslcontext,
                    addr_infos=addr_infos,
                    server_hostname=server_hostname,
                    req=req,
                    client_error=client_error,
                )
            except (ClientConnectorError, asyncio.TimeoutError) as exc:
                last_exc = exc
                aiohappyeyeballs.pop_addr_infos_interleave(addr_infos, self._interleave)
                continue

            if req.is_ssl() and fingerprint:
                try:
                    fingerprint.check(transp)
                except ServerFingerprintMismatch as exc:
                    transp.close()
                    if not self._cleanup_closed_disabled:
                        self._cleanup_closed_transports.append(transp)
                    last_exc = exc
                    # Remove the bad peer from the list of addr_infos
                    sock: socket.socket = transp.get_extra_info("socket")
                    bad_peer = sock.getpeername()
                    aiohappyeyeballs.remove_addr_infos(addr_infos, bad_peer)
                    continue

            return transp, proto
        else:
            assert last_exc is not None
            raise last_exc

    async def _create_proxy_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> Tuple[asyncio.BaseTransport, ResponseHandler]:
        self._fail_on_no_start_tls(req)
        runtime_has_start_tls = self._loop_supports_start_tls()

        headers: Dict[str, str] = {}
        if req.proxy_headers is not None:
            headers = req.proxy_headers  # type: ignore[assignment]
        headers[hdrs.HOST] = req.headers[hdrs.HOST]

        url = req.proxy
        assert url is not None
        proxy_req = ClientRequest(
            hdrs.METH_GET,
            url,
            headers=headers,
            auth=req.proxy_auth,
            loop=self._loop,
            ssl=req.ssl,
        )

        # create connection to proxy server
        transport, proto = await self._create_direct_connection(
            proxy_req, [], timeout, client_error=ClientProxyConnectionError
        )

        auth = proxy_req.headers.pop(hdrs.AUTHORIZATION, None)
        if auth is not None:
            if not req.is_ssl():
                req.headers[hdrs.PROXY_AUTHORIZATION] = auth
            else:
                proxy_req.headers[hdrs.PROXY_AUTHORIZATION] = auth

        if req.is_ssl():
            if runtime_has_start_tls:
                self._warn_about_tls_in_tls(transport, req)

            # For HTTPS requests over HTTP proxy
            # we must notify proxy to tunnel connection
            # so we send CONNECT command:
            #   CONNECT www.python.org:443 HTTP/1.1
            #   Host: www.python.org
            #
            # next we must do TLS handshake and so on
            # to do this we must wrap raw socket into secure one
            # asyncio handles this perfectly
            proxy_req.method = hdrs.METH_CONNECT
            proxy_req.url = req.url
            key = req.connection_key._replace(
                proxy=None, proxy_auth=None, proxy_headers_hash=None
            )
            conn = Connection(self, key, proto, self._loop)
            proxy_resp = await proxy_req.send(conn)
            try:
                protocol = conn._protocol
                assert protocol is not None

                # read_until_eof=True will ensure the connection isn't closed
                # once the response is received and processed allowing
                # START_TLS to work on the connection below.
                protocol.set_response_params(
                    read_until_eof=runtime_has_start_tls,
                    timeout_ceil_threshold=self._timeout_ceil_threshold,
                )
                resp = await proxy_resp.start(conn)
            except BaseException:
                proxy_resp.close()
                conn.close()
                raise
            else:
                conn._protocol = None
                try:
                    if resp.status != 200:
                        message = resp.reason
                        if message is None:
                            message = HTTPStatus(resp.status).phrase
                        raise ClientHttpProxyError(
                            proxy_resp.request_info,
                            resp.history,
                            status=resp.status,
                            message=message,
                            headers=resp.headers,
                        )
                    if not runtime_has_start_tls:
                        rawsock = transport.get_extra_info("socket", default=None)
                        if rawsock is None:
                            raise RuntimeError(
                                "Transport does not expose socket instance"
                            )
                        # Duplicate the socket, so now we can close proxy transport
                        rawsock = rawsock.dup()
                except BaseException:
                    # It shouldn't be closed in `finally` because it's fed to
                    # `loop.start_tls()` and the docs say not to touch it after
                    # passing there.
                    transport.close()
                    raise
                finally:
                    if not runtime_has_start_tls:
                        transport.close()

                if not runtime_has_start_tls:
                    # HTTP proxy with support for upgrade to HTTPS
                    sslcontext = self._get_ssl_context(req)
                    return await self._wrap_existing_connection(
                        self._factory,
                        timeout=timeout,
                        ssl=sslcontext,
                        sock=rawsock,
                        server_hostname=req.host,
                        req=req,
                    )

                return await self._start_tls_connection(
                    # Access the old transport for the last time before it's
                    # closed and forgotten forever:
                    transport,
                    req=req,
                    timeout=timeout,
                )
            finally:
                proxy_resp.close()

        return transport, proto


class UnixConnector(BaseConnector):
    """Unix socket connector.

    path - Unix socket path.
    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    loop - Optional event loop.
    """

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET | frozenset({"unix"})

    def __init__(
        self,
        path: str,
        force_close: bool = False,
        keepalive_timeout: Union[object, float, None] = sentinel,
        limit: int = 100,
        limit_per_host: int = 0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__(
            force_close=force_close,
            keepalive_timeout=keepalive_timeout,
            limit=limit,
            limit_per_host=limit_per_host,
            loop=loop,
        )
        self._path = path

    @property
    def path(self) -> str:
        """Path to unix socket."""
        return self._path

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                _, proto = await self._loop.create_unix_connection(
                    self._factory, self._path
                )
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise UnixClientConnectorError(self.path, req.connection_key, exc) from exc

        return proto


class NamedPipeConnector(BaseConnector):
    """Named pipe connector.

    Only supported by the proactor event loop.
    See also: https://docs.python.org/3/library/asyncio-eventloop.html

    path - Windows named pipe path.
    keepalive_timeout - (optional) Keep-alive timeout.
    force_close - Set to True to force close and do reconnect
        after each request (and between redirects).
    limit - The total number of simultaneous connections.
    limit_per_host - Number of simultaneous connections to one host.
    loop - Optional event loop.
    """

    allowed_protocol_schema_set = HIGH_LEVEL_SCHEMA_SET | frozenset({"npipe"})

    def __init__(
        self,
        path: str,
        force_close: bool = False,
        keepalive_timeout: Union[object, float, None] = sentinel,
        limit: int = 100,
        limit_per_host: int = 0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__(
            force_close=force_close,
            keepalive_timeout=keepalive_timeout,
            limit=limit,
            limit_per_host=limit_per_host,
            loop=loop,
        )
        if not isinstance(
            self._loop,
            asyncio.ProactorEventLoop,  # type: ignore[attr-defined]
        ):
            raise RuntimeError(
                "Named Pipes only available in proactor loop under windows"
            )
        self._path = path

    @property
    def path(self) -> str:
        """Path to the named pipe."""
        return self._path

    async def _create_connection(
        self, req: ClientRequest, traces: List["Trace"], timeout: "ClientTimeout"
    ) -> ResponseHandler:
        try:
            async with ceil_timeout(
                timeout.sock_connect, ceil_threshold=timeout.ceil_threshold
            ):
                _, proto = await self._loop.create_pipe_connection(  # type: ignore[attr-defined]
                    self._factory, self._path
                )
                # the drain is required so that the connection_made is called
                # and transport is set otherwise it is not set before the
                # `assert conn.transport is not None`
                # in client.py's _request method
                await asyncio.sleep(0)
                # other option is to manually set transport like
                # `proto.transport = trans`
        except OSError as exc:
            if exc.errno is None and isinstance(exc, asyncio.TimeoutError):
                raise
            raise ClientConnectorError(req.connection_key, exc) from exc

        return cast(ResponseHandler, proto)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\macaulay2.py ===
"""
    pygments.lexers.macaulay2
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Macaulay2.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, words
from pygments.token import Comment, Keyword, Name, String, Text

__all__ = ['Macaulay2Lexer']

# Auto-generated for Macaulay2-1.24.11. Do not modify this file manually.

M2KEYWORDS = (
    "SPACE",
    "TEST",
    "and",
    "break",
    "catch",
    "continue",
    "do",
    "elapsedTime",
    "elapsedTiming",
    "else",
    "for",
    "from",
    "global",
    "if",
    "in",
    "list",
    "local",
    "new",
    "not",
    "of",
    "or",
    "return",
    "shield",
    "step",
    "symbol",
    "then",
    "threadLocal",
    "threadVariable",
    "throw",
    "time",
    "timing",
    "to",
    "try",
    "when",
    "while",
    "xor"
    )

M2DATATYPES = (
    "ANCHOR",
    "Adjacent",
    "AffineVariety",
    "Analyzer",
    "AngleBarList",
    "Array",
    "AssociativeExpression",
    "AtomicInt",
    "BLOCKQUOTE",
    "BODY",
    "BOLD",
    "BR",
    "BUTTON",
    "Bag",
    "BasicList",
    "BettiTally",
    "BinaryOperation",
    "Boolean",
    "CC",
    "CDATA",
    "CODE",
    "COMMENT",
    "CacheFunction",
    "CacheTable",
    "ChainComplex",
    "ChainComplexMap",
    "CoherentSheaf",
    "Command",
    "CompiledFunction",
    "CompiledFunctionBody",
    "CompiledFunctionClosure",
    "ComplexField",
    "Constant",
    "DD",
    "DIV",
    "DL",
    "DT",
    "Database",
    "Descent",
    "Describe",
    "Dictionary",
    "DirectSum",
    "Divide",
    "DocumentTag",
    "EM",
    "Eliminate",
    "EngineRing",
    "Equation",
    "ExampleItem",
    "Expression",
    "File",
    "FilePosition",
    "FractionField",
    "Function",
    "FunctionApplication",
    "FunctionBody",
    "FunctionClosure",
    "GaloisField",
    "GeneralOrderedMonoid",
    "GlobalDictionary",
    "GradedModule",
    "GradedModuleMap",
    "GroebnerBasis",
    "GroebnerBasisOptions",
    "HEAD",
    "HEADER1",
    "HEADER2",
    "HEADER3",
    "HEADER4",
    "HEADER5",
    "HEADER6",
    "HR",
    "HREF",
    "HTML",
    "HashTable",
    "HeaderType",
    "Holder",
    "Hybrid",
    "Hypertext",
    "HypertextContainer",
    "HypertextParagraph",
    "HypertextVoid",
    "IMG",
    "INDENT",
    "INPUT",
    "ITALIC",
    "Ideal",
    "ImmutableType",
    "IndeterminateNumber",
    "IndexedVariable",
    "IndexedVariableTable",
    "InexactField",
    "InexactFieldFamily",
    "InexactNumber",
    "InfiniteNumber",
    "IntermediateMarkUpType",
    "Iterator",
    "KBD",
    "Keyword",
    "LABEL",
    "LATER",
    "LI",
    "LINK",
    "LITERAL",
    "List",
    "LocalDictionary",
    "LowerBound",
    "MENU",
    "META",
    "Manipulator",
    "MapExpression",
    "MarkUpType",
    "Matrix",
    "MatrixExpression",
    "MethodFunction",
    "MethodFunctionBinary",
    "MethodFunctionSingle",
    "MethodFunctionWithOptions",
    "Minus",
    "Module",
    "Monoid",
    "MonoidElement",
    "MonomialIdeal",
    "MultigradedBettiTally",
    "MutableHashTable",
    "MutableList",
    "MutableMatrix",
    "Net",
    "NetFile",
    "Nothing",
    "Number",
    "NumberedVerticalList",
    "OL",
    "OneExpression",
    "Option",
    "OptionTable",
    "OrderedMonoid",
    "PARA",
    "PRE",
    "Package",
    "Parenthesize",
    "Parser",
    "Partition",
    "PolynomialRing",
    "Power",
    "Product",
    "ProductOrder",
    "Program",
    "ProgramRun",
    "ProjectiveHilbertPolynomial",
    "ProjectiveVariety",
    "Pseudocode",
    "PseudocodeClosure",
    "QQ",
    "QuotientRing",
    "RR",
    "RRi",
    "RealField",
    "Resolution",
    "Ring",
    "RingElement",
    "RingFamily",
    "RingMap",
    "RowExpression",
    "SAMP",
    "SCRIPT",
    "SMALL",
    "SPAN",
    "STRONG",
    "STYLE",
    "SUB",
    "SUBSECTION",
    "SUP",
    "ScriptedFunctor",
    "SelfInitializingType",
    "Sequence",
    "Set",
    "SheafExpression",
    "SheafMap",
    "SheafOfRings",
    "SparseMonomialVectorExpression",
    "SparseVectorExpression",
    "String",
    "Subscript",
    "Sum",
    "SumOfTwists",
    "Superscript",
    "Symbol",
    "SymbolBody",
    "TABLE",
    "TD",
    "TEX",
    "TH",
    "TITLE",
    "TO",
    "TO2",
    "TOH",
    "TR",
    "TT",
    "Table",
    "Tally",
    "Task",
    "TensorProduct",
    "TestInput",
    "Thing",
    "Time",
    "Type",
    "UL",
    "URL",
    "VAR",
    "Variety",
    "Vector",
    "VectorExpression",
    "VerticalList",
    "VirtualTally",
    "VisibleList",
    "WrapperType",
    "ZZ",
    "ZeroExpression"
    )

M2FUNCTIONS = (
    "BesselJ",
    "BesselY",
    "Beta",
    "Digamma",
    "EXAMPLE",
    "End",
    "Fano",
    "GCstats",
    "GF",
    "Gamma",
    "Grassmannian",
    "Hom",
    "LLL",
    "LUdecomposition",
    "M2CODE",
    "NNParser",
    "Proj",
    "QQParser",
    "QRDecomposition",
    "SVD",
    "SYNOPSIS",
    "Schubert",
    "Spec",
    "ZZParser",
    "about",
    "abs",
    "accumulate",
    "acos",
    "acosh",
    "acot",
    "acoth",
    "addCancelTask",
    "addDependencyTask",
    "addEndFunction",
    "addHook",
    "addStartTask",
    "adjoint",
    "agm",
    "alarm",
    "all",
    "ambient",
    "analyticSpread",
    "ancestor",
    "ancestors",
    "andP",
    "ann",
    "annihilator",
    "antipode",
    "any",
    "append",
    "applicationDirectory",
    "apply",
    "applyKeys",
    "applyPairs",
    "applyTable",
    "applyValues",
    "apropos",
    "arXiv",
    "ascii",
    "asin",
    "asinh",
    "ass",
    "assert",
    "associatedGradedRing",
    "associatedPrimes",
    "atEndOfFile",
    "atan",
    "atan2",
    "atanh",
    "autoload",
    "baseFilename",
    "baseName",
    "baseRing",
    "basis",
    "beginDocumentation",
    "benchmark",
    "betti",
    "between",
    "binomial",
    "borel",
    "cacheValue",
    "cancelTask",
    "canonicalBundle",
    "capture",
    "ceiling",
    "centerString",
    "chainComplex",
    "changeBase",
    "changeDirectory",
    "char",
    "charAnalyzer",
    "characters",
    "check",
    "checkDegrees",
    "chi",
    "class",
    "clean",
    "clearEcho",
    "code",
    "codim",
    "coefficient",
    "coefficientRing",
    "coefficients",
    "cohomology",
    "coimage",
    "coker",
    "cokernel",
    "collectGarbage",
    "columnAdd",
    "columnMult",
    "columnPermute",
    "columnRankProfile",
    "columnSwap",
    "columnate",
    "combine",
    "commandInterpreter",
    "commonRing",
    "commonest",
    "comodule",
    "compareExchange",
    "complement",
    "complete",
    "components",
    "compose",
    "compositions",
    "compress",
    "concatenate",
    "conductor",
    "cone",
    "conjugate",
    "connectionCount",
    "constParser",
    "content",
    "contract",
    "conwayPolynomial",
    "copy",
    "copyDirectory",
    "copyFile",
    "cos",
    "cosh",
    "cot",
    "cotangentSheaf",
    "coth",
    "cover",
    "coverMap",
    "cpuTime",
    "createTask",
    "csc",
    "csch",
    "currentColumnNumber",
    "currentDirectory",
    "currentPosition",
    "currentRowNumber",
    "currentTime",
    "deadParser",
    "debug",
    "debugError",
    "decompose",
    "deepSplice",
    "default",
    "degree",
    "degreeGroup",
    "degreeLength",
    "degrees",
    "degreesMonoid",
    "degreesRing",
    "delete",
    "demark",
    "denominator",
    "depth",
    "describe",
    "det",
    "determinant",
    "diagonalMatrix",
    "diameter",
    "dictionary",
    "diff",
    "difference",
    "dim",
    "directSum",
    "disassemble",
    "discriminant",
    "dismiss",
    "distinguished",
    "divideByVariable",
    "doc",
    "document",
    "drop",
    "dual",
    "eagonNorthcott",
    "echoOff",
    "echoOn",
    "eigenvalues",
    "eigenvectors",
    "eint",
    "elements",
    "eliminate",
    "endPackage",
    "entries",
    "erase",
    "erf",
    "erfc",
    "error",
    "euler",
    "eulers",
    "even",
    "examples",
    "exchange",
    "exec",
    "exp",
    "expectedReesIdeal",
    "expm1",
    "exponents",
    "export",
    "exportFrom",
    "exportMutable",
    "expression",
    "extend",
    "exteriorPower",
    "factor",
    "fileExecutable",
    "fileExists",
    "fileLength",
    "fileMode",
    "fileReadable",
    "fileTime",
    "fileWritable",
    "fillMatrix",
    "findFiles",
    "findHeft",
    "findProgram",
    "findSynonyms",
    "first",
    "firstkey",
    "fittingIdeal",
    "flagLookup",
    "flatten",
    "flattenRing",
    "flip",
    "floor",
    "fold",
    "forceGB",
    "fork",
    "format",
    "formation",
    "frac",
    "fraction",
    "frames",
    "fromDividedPowers",
    "fromDual",
    "functionBody",
    "futureParser",
    "gb",
    "gbRemove",
    "gbSnapshot",
    "gcd",
    "gcdCoefficients",
    "gcdLLL",
    "genera",
    "generateAssertions",
    "generator",
    "generators",
    "genericMatrix",
    "genericSkewMatrix",
    "genericSymmetricMatrix",
    "gens",
    "genus",
    "get",
    "getChangeMatrix",
    "getGlobalSymbol",
    "getIOThreadMode",
    "getNetFile",
    "getNonUnit",
    "getPrimeWithRootOfUnity",
    "getSymbol",
    "getWWW",
    "getc",
    "getenv",
    "globalAssign",
    "globalAssignFunction",
    "globalAssignment",
    "globalReleaseFunction",
    "gradedModule",
    "gradedModuleMap",
    "gramm",
    "graphIdeal",
    "graphRing",
    "groebnerBasis",
    "groupID",
    "hash",
    "hashTable",
    "headlines",
    "heft",
    "height",
    "hermite",
    "hilbertFunction",
    "hilbertPolynomial",
    "hilbertSeries",
    "hold",
    "homogenize",
    "homology",
    "homomorphism",
    "hooks",
    "horizontalJoin",
    "html",
    "httpHeaders",
    "hypertext",
    "icFracP",
    "icFractions",
    "icMap",
    "icPIdeal",
    "ideal",
    "idealizer",
    "identity",
    "image",
    "imaginaryPart",
    "importFrom",
    "independentSets",
    "index",
    "indices",
    "inducedMap",
    "inducesWellDefinedMap",
    "info",
    "input",
    "insert",
    "installAssignmentMethod",
    "installHilbertFunction",
    "installMethod",
    "installMinprimes",
    "installPackage",
    "installedPackages",
    "instance",
    "instances",
    "integralClosure",
    "integrate",
    "intersect",
    "intersectInP",
    "intersection",
    "interval",
    "inverse",
    "inverseErf",
    "inversePermutation",
    "inverseRegularizedBeta",
    "inverseRegularizedGamma",
    "inverseSystem",
    "irreducibleCharacteristicSeries",
    "irreducibleDecomposition",
    "isANumber",
    "isAffineRing",
    "isBorel",
    "isCanceled",
    "isCommutative",
    "isConstant",
    "isDirectSum",
    "isDirectory",
    "isEmpty",
    "isField",
    "isFinite",
    "isFinitePrimeField",
    "isFreeModule",
    "isGlobalSymbol",
    "isHomogeneous",
    "isIdeal",
    "isInfinite",
    "isInjective",
    "isInputFile",
    "isIsomorphic",
    "isIsomorphism",
    "isLLL",
    "isLiftable",
    "isLinearType",
    "isListener",
    "isMember",
    "isModule",
    "isMonomialIdeal",
    "isMutable",
    "isNormal",
    "isOpen",
    "isOutputFile",
    "isPolynomialRing",
    "isPrimary",
    "isPrime",
    "isPrimitive",
    "isProjective",
    "isPseudoprime",
    "isQuotientModule",
    "isQuotientOf",
    "isQuotientRing",
    "isReady",
    "isReal",
    "isReduction",
    "isRegularFile",
    "isRing",
    "isSkewCommutative",
    "isSmooth",
    "isSorted",
    "isSquareFree",
    "isStandardGradedPolynomialRing",
    "isSubmodule",
    "isSubquotient",
    "isSubset",
    "isSupportedInZeroLocus",
    "isSurjective",
    "isTable",
    "isUnit",
    "isVeryAmple",
    "isWellDefined",
    "isWeylAlgebra",
    "isc",
    "iterator",
    "jacobian",
    "jacobianDual",
    "join",
    "ker",
    "kernel",
    "kernelLLL",
    "kernelOfLocalization",
    "keys",
    "kill",
    "koszul",
    "last",
    "lcm",
    "leadCoefficient",
    "leadComponent",
    "leadMonomial",
    "leadTerm",
    "left",
    "length",
    "letterParser",
    "lift",
    "liftable",
    "limitFiles",
    "limitProcesses",
    "lines",
    "linkFile",
    "listForm",
    "listSymbols",
    "lngamma",
    "load",
    "loadPackage",
    "localDictionaries",
    "localize",
    "locate",
    "log",
    "log1p",
    "lookup",
    "lookupCount",
    "makeDirectory",
    "makeDocumentTag",
    "makePackageIndex",
    "makeS2",
    "map",
    "markedGB",
    "match",
    "mathML",
    "matrix",
    "max",
    "maxPosition",
    "member",
    "memoize",
    "memoizeClear",
    "memoizeValues",
    "merge",
    "mergePairs",
    "method",
    "methodOptions",
    "methods",
    "midpoint",
    "min",
    "minPosition",
    "minPres",
    "mingens",
    "mingle",
    "minimalBetti",
    "minimalPresentation",
    "minimalPrimes",
    "minimalReduction",
    "minimize",
    "minimizeFilename",
    "minors",
    "minprimes",
    "minus",
    "mkdir",
    "mod",
    "module",
    "modulo",
    "monoid",
    "monomialCurveIdeal",
    "monomialIdeal",
    "monomialSubideal",
    "monomials",
    "moveFile",
    "multidegree",
    "multidoc",
    "multigraded",
    "multiplicity",
    "mutable",
    "mutableIdentity",
    "mutableMatrix",
    "nanosleep",
    "needs",
    "needsPackage",
    "net",
    "netList",
    "newClass",
    "newCoordinateSystem",
    "newNetFile",
    "newPackage",
    "newRing",
    "next",
    "nextPrime",
    "nextkey",
    "nonspaceAnalyzer",
    "norm",
    "normalCone",
    "notImplemented",
    "nullParser",
    "nullSpace",
    "nullhomotopy",
    "numColumns",
    "numRows",
    "number",
    "numcols",
    "numerator",
    "numeric",
    "numericInterval",
    "numgens",
    "numrows",
    "odd",
    "oeis",
    "ofClass",
    "on",
    "openDatabase",
    "openDatabaseOut",
    "openFiles",
    "openIn",
    "openInOut",
    "openListener",
    "openOut",
    "openOutAppend",
    "optP",
    "optionalSignParser",
    "options",
    "orP",
    "override",
    "pack",
    "package",
    "packageTemplate",
    "pad",
    "pager",
    "pairs",
    "parallelApply",
    "parent",
    "part",
    "partition",
    "partitions",
    "parts",
    "pdim",
    "peek",
    "permanents",
    "permutations",
    "pfaffians",
    "pivots",
    "plus",
    "poincare",
    "poincareN",
    "polarize",
    "poly",
    "position",
    "positions",
    "power",
    "powermod",
    "precision",
    "preimage",
    "prepend",
    "presentation",
    "pretty",
    "primaryComponent",
    "primaryDecomposition",
    "print",
    "printString",
    "printerr",
    "processID",
    "product",
    "profile",
    "projectiveHilbertPolynomial",
    "promote",
    "protect",
    "prune",
    "pseudoRemainder",
    "pseudocode",
    "pullback",
    "pushForward",
    "pushout",
    "quotient",
    "quotientRemainder",
    "radical",
    "radicalContainment",
    "random",
    "randomKRationalPoint",
    "randomMutableMatrix",
    "rank",
    "rays",
    "read",
    "readDirectory",
    "readPackage",
    "readlink",
    "realPart",
    "realpath",
    "recursionDepth",
    "reduceHilbert",
    "reducedRowEchelonForm",
    "reductionNumber",
    "reesAlgebra",
    "reesAlgebraIdeal",
    "reesIdeal",
    "regSeqInIdeal",
    "regex",
    "regexQuote",
    "registerFinalizer",
    "regularity",
    "regularizedBeta",
    "regularizedGamma",
    "relations",
    "relativizeFilename",
    "remainder",
    "remove",
    "removeDirectory",
    "removeFile",
    "removeLowestDimension",
    "reorganize",
    "replace",
    "res",
    "reshape",
    "resolution",
    "resultant",
    "reverse",
    "right",
    "ring",
    "ringFromFractions",
    "roots",
    "rotate",
    "round",
    "rowAdd",
    "rowMult",
    "rowPermute",
    "rowRankProfile",
    "rowSwap",
    "rsort",
    "run",
    "runHooks",
    "runLengthEncode",
    "runProgram",
    "same",
    "saturate",
    "scan",
    "scanKeys",
    "scanLines",
    "scanPairs",
    "scanValues",
    "schedule",
    "schreyerOrder",
    "searchPath",
    "sec",
    "sech",
    "seeParsing",
    "select",
    "selectInSubring",
    "selectKeys",
    "selectPairs",
    "selectValues",
    "selectVariables",
    "separate",
    "separateRegexp",
    "sequence",
    "serialNumber",
    "set",
    "setEcho",
    "setGroupID",
    "setIOExclusive",
    "setIOSynchronized",
    "setIOUnSynchronized",
    "setRandomSeed",
    "setup",
    "setupEmacs",
    "setupLift",
    "setupPromote",
    "sheaf",
    "sheafHom",
    "sheafMap",
    "show",
    "showHtml",
    "showTex",
    "simpleDocFrob",
    "sin",
    "singularLocus",
    "sinh",
    "size",
    "size2",
    "sleep",
    "smithNormalForm",
    "solve",
    "someTerms",
    "sort",
    "sortColumns",
    "source",
    "span",
    "specialFiber",
    "specialFiberIdeal",
    "splice",
    "splitWWW",
    "sqrt",
    "stack",
    "stacksProject",
    "standardForm",
    "standardPairs",
    "stashValue",
    "status",
    "store",
    "style",
    "sub",
    "sublists",
    "submatrix",
    "submatrixByDegrees",
    "subquotient",
    "subsets",
    "substitute",
    "substring",
    "subtable",
    "sum",
    "super",
    "support",
    "switch",
    "sylvesterMatrix",
    "symbolBody",
    "symlinkDirectory",
    "symlinkFile",
    "symmetricAlgebra",
    "symmetricAlgebraIdeal",
    "symmetricKernel",
    "symmetricPower",
    "synonym",
    "syz",
    "syzygyScheme",
    "table",
    "take",
    "tally",
    "tan",
    "tangentCone",
    "tangentSheaf",
    "tanh",
    "target",
    "taskResult",
    "temporaryFileName",
    "tensor",
    "tensorAssociativity",
    "terminalParser",
    "terms",
    "testHunekeQuestion",
    "tests",
    "tex",
    "texMath",
    "times",
    "toAbsolutePath",
    "toCC",
    "toDividedPowers",
    "toDual",
    "toExternalString",
    "toField",
    "toList",
    "toLower",
    "toRR",
    "toRRi",
    "toSequence",
    "toString",
    "toUpper",
    "top",
    "topCoefficients",
    "topComponents",
    "trace",
    "transpose",
    "trim",
    "truncate",
    "truncateOutput",
    "tutorial",
    "ultimate",
    "unbag",
    "uncurry",
    "undocumented",
    "uniform",
    "uninstallAllPackages",
    "uninstallPackage",
    "union",
    "unique",
    "uniquePermutations",
    "unsequence",
    "unstack",
    "urlEncode",
    "use",
    "userSymbols",
    "utf8",
    "utf8check",
    "utf8substring",
    "validate",
    "value",
    "values",
    "variety",
    "vars",
    "vector",
    "versalEmbedding",
    "wait",
    "wedgeProduct",
    "weightRange",
    "whichGm",
    "width",
    "wikipedia",
    "wrap",
    "youngest",
    "zero",
    "zeta"
    )

M2CONSTANTS = (
    "A1BrouwerDegrees",
    "AbstractSimplicialComplexes",
    "AbstractToricVarieties",
    "Acknowledgement",
    "AdditionalPaths",
    "AdjointIdeal",
    "AdjunctionForSurfaces",
    "AfterEval",
    "AfterNoPrint",
    "AfterPrint",
    "AInfinity",
    "AlgebraicSplines",
    "Algorithm",
    "Alignment",
    "AllCodimensions",
    "allowableThreads",
    "AnalyzeSheafOnP1",
    "applicationDirectorySuffix",
    "argument",
    "Ascending",
    "AssociativeAlgebras",
    "Authors",
    "AuxiliaryFiles",
    "backtrace",
    "Bareiss",
    "Base",
    "BaseFunction",
    "baseRings",
    "BaseRow",
    "BasisElementLimit",
    "Bayer",
    "BeforePrint",
    "BeginningMacaulay2",
    "Benchmark",
    "BernsteinSato",
    "Bertini",
    "BettiCharacters",
    "BGG",
    "BIBasis",
    "Binary",
    "Binomial",
    "BinomialEdgeIdeals",
    "Binomials",
    "BKZ",
    "blockMatrixForm",
    "Body",
    "BoijSoederberg",
    "Book3264Examples",
    "BooleanGB",
    "Boxes",
    "Browse",
    "Bruns",
    "cache",
    "CacheExampleOutput",
    "CallLimit",
    "CannedExample",
    "CatalanConstant",
    "Caveat",
    "CellularResolutions",
    "Center",
    "Certification",
    "ChainComplexExtras",
    "ChainComplexOperations",
    "ChangeMatrix",
    "CharacteristicClasses",
    "CheckDocumentation",
    "Chordal",
    "cite",
    "Classic",
    "clearAll",
    "clearOutput",
    "close",
    "closeIn",
    "closeOut",
    "ClosestFit",
    "Code",
    "CodimensionLimit",
    "CodingTheory",
    "CoefficientRing",
    "Cofactor",
    "CohenEngine",
    "CohenTopLevel",
    "CohomCalg",
    "CoincidentRootLoci",
    "commandLine",
    "compactMatrixForm",
    "Complement",
    "CompleteIntersection",
    "CompleteIntersectionResolutions",
    "Complexes",
    "ConductorElement",
    "Configuration",
    "ConformalBlocks",
    "Consequences",
    "Constants",
    "Contributors",
    "ConvexInterface",
    "ConwayPolynomials",
    "copyright",
    "Core",
    "CorrespondenceScrolls",
    "CotangentSchubert",
    "Cremona",
    "currentFileDirectory",
    "currentFileName",
    "currentLayout",
    "currentPackage",
    "Cyclotomic",
    "Date",
    "dd",
    "DebuggingMode",
    "debuggingMode",
    "debugLevel",
    "DecomposableSparseSystems",
    "Decompose",
    "Default",
    "defaultPrecision",
    "Degree",
    "DegreeGroup",
    "DegreeLift",
    "DegreeLimit",
    "DegreeMap",
    "DegreeOrder",
    "DegreeRank",
    "Degrees",
    "Dense",
    "Density",
    "Depth",
    "Descending",
    "Description",
    "DeterminantalRepresentations",
    "DGAlgebras",
    "dictionaryPath",
    "DiffAlg",
    "Dispatch",
    "DivideConquer",
    "DividedPowers",
    "Divisor",
    "Dmodules",
    "docExample",
    "docTemplate",
    "Down",
    "Dynamic",
    "EagonResolution",
    "EdgeIdeals",
    "edit",
    "EigenSolver",
    "EisenbudHunekeVasconcelos",
    "Elimination",
    "EliminationMatrices",
    "EllipticCurves",
    "EllipticIntegrals",
    "Email",
    "end",
    "endl",
    "Engine",
    "engineDebugLevel",
    "EngineTests",
    "EnumerationCurves",
    "environment",
    "EquivariantGB",
    "errorDepth",
    "EulerConstant",
    "Example",
    "ExampleFiles",
    "ExampleSystems",
    "Exclude",
    "exit",
    "Ext",
    "ExteriorIdeals",
    "ExteriorModules",
    "false",
    "FastMinors",
    "FastNonminimal",
    "FGLM",
    "fileDictionaries",
    "fileExitHooks",
    "FileName",
    "FindOne",
    "FiniteFittingIdeals",
    "First",
    "FirstPackage",
    "FlatMonoid",
    "Flexible",
    "flush",
    "FollowLinks",
    "ForeignFunctions",
    "FormalGroupLaws",
    "Format",
    "FourierMotzkin",
    "FourTiTwo",
    "fpLLL",
    "FrobeniusThresholds",
    "FunctionFieldDesingularization",
    "GBDegrees",
    "gbTrace",
    "GenerateAssertions",
    "Generic",
    "GenericInitialIdeal",
    "GeometricDecomposability",
    "gfanInterface",
    "Givens",
    "GKMVarieties",
    "GLex",
    "Global",
    "GlobalAssignHook",
    "globalAssignmentHooks",
    "GlobalHookStore",
    "GlobalReleaseHook",
    "GlobalSectionLimit",
    "Gorenstein",
    "GradedLieAlgebras",
    "GraphicalModels",
    "GraphicalModelsMLE",
    "Graphics",
    "Graphs",
    "GRevLex",
    "GroebnerStrata",
    "GroebnerWalk",
    "GroupLex",
    "GroupRevLex",
    "GTZ",
    "Hadamard",
    "handleInterrupts",
    "HardDegreeLimit",
    "Heading",
    "Headline",
    "Heft",
    "Height",
    "help",
    "Hermite",
    "Hermitian",
    "HH",
    "hh",
    "HigherCIOperators",
    "HighestWeights",
    "Hilbert",
    "HodgeIntegrals",
    "HolonomicSystems",
    "homeDirectory",
    "HomePage",
    "Homogeneous",
    "Homogeneous2",
    "HomotopyLieAlgebra",
    "HorizontalSpace",
    "HyperplaneArrangements",
    "id",
    "IgnoreExampleErrors",
    "ii",
    "incomparable",
    "Increment",
    "indeterminate",
    "Index",
    "indexComponents",
    "infinity",
    "InfoDirSection",
    "infoHelp",
    "Inhomogeneous",
    "Inputs",
    "InstallPrefix",
    "IntegralClosure",
    "interpreterDepth",
    "Intersection",
    "InvariantRing",
    "InverseMethod",
    "Inverses",
    "InverseSystems",
    "Invertible",
    "InvolutiveBases",
    "Isomorphism",
    "Item",
    "Iterate",
    "Jacobian",
    "Jets",
    "Join",
    "JSON",
    "Jupyter",
    "K3Carpets",
    "K3Surfaces",
    "Keep",
    "KeepFiles",
    "KeepZeroes",
    "Key",
    "Keywords",
    "Kronecker",
    "KustinMiller",
    "lastMatch",
    "LatticePolytopes",
    "Layout",
    "Left",
    "LengthLimit",
    "Lex",
    "LexIdeals",
    "Licenses",
    "LieTypes",
    "Limit",
    "Linear",
    "LinearAlgebra",
    "LinearTruncations",
    "lineNumber",
    "listLocalSymbols",
    "listUserSymbols",
    "LLLBases",
    "loadDepth",
    "LoadDocumentation",
    "loadedFiles",
    "loadedPackages",
    "Local",
    "LocalRings",
    "LongPolynomial",
    "M0nbar",
    "Macaulay2Doc",
    "Maintainer",
    "MakeDocumentation",
    "MakeHTML",
    "MakeInfo",
    "MakeLinks",
    "MakePDF",
    "MapleInterface",
    "Markov",
    "MatchingFields",
    "MatrixSchubert",
    "Matroids",
    "maxAllowableThreads",
    "maxExponent",
    "MaximalRank",
    "MaxReductionCount",
    "MCMApproximations",
    "MergeTeX",
    "minExponent",
    "MinimalGenerators",
    "MinimalMatrix",
    "minimalPresentationMap",
    "minimalPresentationMapInv",
    "MinimalPrimes",
    "Minimize",
    "MinimumVersion",
    "Miura",
    "MixedMultiplicity",
    "ModuleDeformations",
    "MonodromySolver",
    "Monomial",
    "MonomialAlgebras",
    "MonomialIntegerPrograms",
    "MonomialOrbits",
    "MonomialOrder",
    "Monomials",
    "MonomialSize",
    "Msolve",
    "MultigradedBGG",
    "MultigradedImplicitization",
    "MultiGradedRationalMap",
    "MultiplicitySequence",
    "MultiplierIdeals",
    "MultiplierIdealsDim2",
    "MultiprojectiveVarieties",
    "NAGtypes",
    "Name",
    "Nauty",
    "NautyGraphs",
    "NCAlgebra",
    "NCLex",
    "NewFromMethod",
    "newline",
    "NewMethod",
    "NewOfFromMethod",
    "NewOfMethod",
    "nil",
    "Node",
    "NoetherianOperators",
    "NoetherNormalization",
    "NonminimalComplexes",
    "NoPrint",
    "Normaliz",
    "NormalToricVarieties",
    "notify",
    "NTL",
    "null",
    "nullaryMethods",
    "NumericalAlgebraicGeometry",
    "NumericalCertification",
    "NumericalImplicitization",
    "NumericalLinearAlgebra",
    "NumericalSchubertCalculus",
    "NumericalSemigroups",
    "NumericSolutions",
    "numTBBThreads",
    "OIGroebnerBases",
    "OldPolyhedra",
    "OldToricVectorBundles",
    "OnlineLookup",
    "OO",
    "oo",
    "ooo",
    "oooo",
    "OpenMath",
    "operatorAttributes",
    "OptionalComponentsPresent",
    "Options",
    "Order",
    "order",
    "OutputDictionary",
    "Outputs",
    "PackageCitations",
    "PackageDictionary",
    "PackageExports",
    "PackageImports",
    "PackageTemplate",
    "PairLimit",
    "PairsRemaining",
    "ParallelF4",
    "ParallelizeByDegree",
    "Parametrization",
    "Parsing",
    "path",
    "PencilsOfQuadrics",
    "Permanents",
    "Permutations",
    "PHCpack",
    "PhylogeneticTrees",
    "pi",
    "PieriMaps",
    "PlaneCurveLinearSeries",
    "PlaneCurveSingularities",
    "Points",
    "Polyhedra",
    "Polymake",
    "PolyominoIdeals",
    "Posets",
    "Position",
    "PositivityToricBundles",
    "POSIX",
    "Postfix",
    "Pre",
    "Precision",
    "Prefix",
    "prefixDirectory",
    "prefixPath",
    "PrimaryDecomposition",
    "PrimaryTag",
    "PrimitiveElement",
    "Print",
    "printingAccuracy",
    "printingLeadLimit",
    "printingPrecision",
    "printingSeparator",
    "printingTimeLimit",
    "printingTrailLimit",
    "printWidth",
    "Probability",
    "profileSummary",
    "programPaths",
    "Projective",
    "Prune",
    "PruneComplex",
    "pruningMap",
    "PseudomonomialPrimaryDecomposition",
    "Pullback",
    "pullbackMaps",
    "PushForward",
    "pushoutMaps",
    "Python",
    "QthPower",
    "QuadraticIdealExamplesByRoos",
    "Quasidegrees",
    "QuaternaryQuartics",
    "QuillenSuslin",
    "quit",
    "Quotient",
    "Radical",
    "RadicalCodim1",
    "RaiseError",
    "RandomCanonicalCurves",
    "RandomComplexes",
    "RandomCurves",
    "RandomCurvesOverVerySmallFiniteFields",
    "RandomGenus14Curves",
    "RandomIdeals",
    "RandomMonomialIdeals",
    "RandomObjects",
    "RandomPlaneCurves",
    "RandomPoints",
    "RandomSpaceCurves",
    "Range",
    "RationalMaps",
    "RationalPoints",
    "RationalPoints2",
    "ReactionNetworks",
    "RealFP",
    "RealQP",
    "RealQP1",
    "RealRoots",
    "RealRR",
    "RealXD",
    "recursionLimit",
    "Reduce",
    "ReesAlgebra",
    "References",
    "ReflexivePolytopesDB",
    "Regularity",
    "RelativeCanonicalResolution",
    "Reload",
    "RemakeAllDocumentation",
    "RerunExamples",
    "ResidualIntersections",
    "ResLengthThree",
    "ResolutionsOfStanleyReisnerRings",
    "restart",
    "Result",
    "Resultants",
    "returnCode",
    "Reverse",
    "RevLex",
    "Right",
    "RInterface",
    "rootPath",
    "rootURI",
    "RunDirectory",
    "RunExamples",
    "RunExternalM2",
    "SagbiGbDetection",
    "Saturation",
    "SaturationMap",
    "Schubert2",
    "SchurComplexes",
    "SchurFunctors",
    "SchurRings",
    "SchurVeronese",
    "SCMAlgebras",
    "scriptCommandLine",
    "SCSCP",
    "SectionRing",
    "SeeAlso",
    "SegreClasses",
    "SemidefiniteProgramming",
    "Seminormalization",
    "SeparateExec",
    "Serialization",
    "sheafExt",
    "ShimoyamaYokoyama",
    "showClassStructure",
    "showStructure",
    "showUserStructure",
    "SimpleDoc",
    "SimplicialComplexes",
    "SimplicialDecomposability",
    "SimplicialPosets",
    "SimplifyFractions",
    "SizeLimit",
    "SkewCommutative",
    "SlackIdeals",
    "SLnEquivariantMatrices",
    "SLPexpressions",
    "Sort",
    "SortStrategy",
    "SourceCode",
    "SourceRing",
    "SpaceCurves",
    "SparseResultants",
    "SpechtModule",
    "SpecialFanoFourfolds",
    "SpectralSequences",
    "SRdeformations",
    "Standard",
    "StartWithOneMinor",
    "StatePolytope",
    "StatGraphs",
    "stderr",
    "stdio",
    "StopBeforeComputation",
    "stopIfError",
    "StopIteration",
    "StopWithMinimalGenerators",
    "Strategy",
    "Strict",
    "StronglyStableIdeals",
    "Style",
    "SubalgebraBases",
    "Subnodes",
    "SubringLimit",
    "subscript",
    "Sugarless",
    "SumsOfSquares",
    "SuperLinearAlgebra",
    "superscript",
    "SVDComplexes",
    "SwitchingFields",
    "SymbolicPowers",
    "SymmetricPolynomials",
    "Synopsis",
    "Syzygies",
    "SyzygyLimit",
    "SyzygyMatrix",
    "SyzygyRows",
    "TangentCone",
    "TateOnProducts",
    "TensorComplexes",
    "TerraciniLoci",
    "Test",
    "testExample",
    "TestIdeals",
    "TeXmacs",
    "Text",
    "ThinSincereQuivers",
    "ThreadedGB",
    "Threads",
    "Threshold",
    "Topcom",
    "topLevelMode",
    "Tor",
    "TorAlgebra",
    "Toric",
    "ToricInvariants",
    "ToricTopology",
    "ToricVectorBundles",
    "Torsion",
    "TorsionFree",
    "TotalPairs",
    "Tree",
    "TriangularSets",
    "Triangulations",
    "Tries",
    "Trim",
    "Triplets",
    "Tropical",
    "TropicalToric",
    "true",
    "Truncate",
    "Truncations",
    "TSpreadIdeals",
    "TypicalValue",
    "typicalValues",
    "Undo",
    "Unique",
    "Units",
    "Unmixed",
    "Up",
    "UpdateOnly",
    "UpperTriangular",
    "Usage",
    "UseCachedExampleOutput",
    "UseHilbertFunction",
    "UserMode",
    "UseSyzygies",
    "Valuations",
    "Variable",
    "VariableBaseName",
    "Variables",
    "Varieties",
    "Vasconcelos",
    "VectorFields",
    "VectorGraphics",
    "Verbose",
    "Verbosity",
    "Verify",
    "VersalDeformations",
    "Version",
    "version",
    "VerticalSpace",
    "viewHelp",
    "VirtualResolutions",
    "Visualize",
    "VNumber",
    "WebApp",
    "Weights",
    "WeylAlgebra",
    "WeylAlgebras",
    "WeylGroups",
    "WhitneyStratifications",
    "Wrap",
    "XML"
    )

class Macaulay2Lexer(RegexLexer):
    """Lexer for Macaulay2, a software system for research in algebraic geometry."""

    name = 'Macaulay2'
    url = 'https://macaulay2.com/'
    aliases = ['macaulay2']
    filenames = ['*.m2']
    version_added = '2.12'

    tokens = {
        'root': [
            (r'--.*$', Comment.Single),
            (r'-\*', Comment.Multiline, 'block comment'),
            (r'"', String, 'quote string'),
            (r'///', String, 'slash string'),
            (words(M2KEYWORDS, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(M2DATATYPES, prefix=r'\b', suffix=r'\b'), Name.Builtin),
            (words(M2FUNCTIONS, prefix=r'\b', suffix=r'\b'), Name.Function),
            (words(M2CONSTANTS, prefix=r'\b', suffix=r'\b'), Name.Constant),
            (r'\s+', Text.Whitespace),
            (r'.', Text)
        ],
        'block comment' : [
            (r'[^*-]+', Comment.Multiline),
            (r'\*-', Comment.Multiline, '#pop'),
            (r'[*-]', Comment.Multiline)
        ],
        'quote string' : [
            (r'[^\\"]+', String),
            (r'"', String, '#pop'),
            (r'\\"?', String),
        ],
        'slash string' : [
            (r'[^/]+', String),
            (r'(//)+(?!/)', String),
            (r'/(//)+(?!/)', String, '#pop'),
            (r'/', String)
        ]
    }

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\SlackAlerting\slack_alerting.py ===
#### What this does ####
#    Class for sending Slack Alerts #
import asyncio
import datetime
import os
import random
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple, Union

from openai import APIError

import litellm
import litellm.litellm_core_utils
import litellm.litellm_core_utils.litellm_logging
import litellm.types
from litellm._logging import verbose_logger, verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.constants import HOURS_IN_A_DAY
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.integrations.SlackAlerting.budget_alert_types import get_budget_alert_type
from litellm.integrations.SlackAlerting.hanging_request_check import (
    AlertingHangingRequestCheck,
)
from litellm.litellm_core_utils.duration_parser import duration_in_seconds
from litellm.litellm_core_utils.exception_mapping_utils import (
    _add_key_name_and_team_to_alert,
)
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import (
    AlertType,
    CallInfo,
    Litellm_EntityType,
    VirtualKeyEvent,
    WebhookEvent,
)
from litellm.types.integrations.slack_alerting import *

from ..email_templates.templates import *
from .batching_handler import send_to_webhook, squash_payloads
from .utils import process_slack_alerting_variables

if TYPE_CHECKING:
    from litellm.router import Router as _Router

    Router = _Router
else:
    Router = Any


class SlackAlerting(CustomBatchLogger):
    """
    Class for sending Slack Alerts
    """

    # Class variables or attributes
    def __init__(
        self,
        internal_usage_cache: Optional[DualCache] = None,
        alerting_threshold: Optional[
            float
        ] = None,  # threshold for slow / hanging llm responses (in seconds)
        alerting: Optional[List] = [],
        alert_types: List[AlertType] = DEFAULT_ALERT_TYPES,
        alert_to_webhook_url: Optional[
            Dict[AlertType, Union[List[str], str]]
        ] = None,  # if user wants to separate alerts to diff channels
        alerting_args={},
        default_webhook_url: Optional[str] = None,
        **kwargs,
    ):
        if alerting_threshold is None:
            alerting_threshold = 300
        self.alerting_threshold = alerting_threshold
        self.alerting = alerting
        self.alert_types = alert_types
        self.internal_usage_cache = internal_usage_cache or DualCache()
        self.async_http_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        self.alert_to_webhook_url = process_slack_alerting_variables(
            alert_to_webhook_url=alert_to_webhook_url
        )
        self.is_running = False
        self.alerting_args = SlackAlertingArgs(**alerting_args)
        self.default_webhook_url = default_webhook_url
        self.flush_lock = asyncio.Lock()
        self.periodic_started = False
        self.hanging_request_check = AlertingHangingRequestCheck(
            slack_alerting_object=self,
        )
        super().__init__(**kwargs, flush_lock=self.flush_lock)

    def update_values(
        self,
        alerting: Optional[List] = None,
        alerting_threshold: Optional[float] = None,
        alert_types: Optional[List[AlertType]] = None,
        alert_to_webhook_url: Optional[Dict[AlertType, Union[List[str], str]]] = None,
        alerting_args: Optional[Dict] = None,
        llm_router: Optional[Router] = None,
    ):
        if alerting is not None:
            self.alerting = alerting
            asyncio.create_task(self.periodic_flush())
            self.periodic_started = True
        if alerting_threshold is not None:
            self.alerting_threshold = alerting_threshold
        if alert_types is not None:
            self.alert_types = alert_types
        if alerting_args is not None:
            self.alerting_args = SlackAlertingArgs(**alerting_args)
            if not self.periodic_started:
                asyncio.create_task(self.periodic_flush())
                self.periodic_started = True

        if alert_to_webhook_url is not None:
            # update the dict
            if self.alert_to_webhook_url is None:
                self.alert_to_webhook_url = process_slack_alerting_variables(
                    alert_to_webhook_url=alert_to_webhook_url
                )
            else:
                _new_values = (
                    process_slack_alerting_variables(
                        alert_to_webhook_url=alert_to_webhook_url
                    )
                    or {}
                )
                self.alert_to_webhook_url.update(_new_values)
        if llm_router is not None:
            self.llm_router = llm_router

    async def deployment_in_cooldown(self):
        pass

    async def deployment_removed_from_cooldown(self):
        pass

    def _all_possible_alert_types(self):
        # used by the UI to show all supported alert types
        # Note: This is not the alerts the user has configured, instead it's all possible alert types a user can select
        # return list of all values AlertType enum
        return list(AlertType)

    def _response_taking_too_long_callback_helper(
        self,
        kwargs,  # kwargs to completion
        start_time,
        end_time,  # start/end time
    ):
        try:
            time_difference = end_time - start_time
            # Convert the timedelta to float (in seconds)
            time_difference_float = time_difference.total_seconds()
            litellm_params = kwargs.get("litellm_params", {})
            model = kwargs.get("model", "")
            api_base = litellm.get_api_base(model=model, optional_params=litellm_params)
            messages = kwargs.get("messages", None)
            # if messages does not exist fallback to "input"
            if messages is None:
                messages = kwargs.get("input", None)

            # only use first 100 chars for alerting
            _messages = str(messages)[:100]

            return time_difference_float, model, api_base, _messages
        except Exception as e:
            raise e

    def _get_deployment_latencies_to_alert(self, metadata=None):
        if metadata is None:
            return None

        if "_latency_per_deployment" in metadata:
            # Translate model_id to -> api_base
            # _latency_per_deployment is a dictionary that looks like this:
            """
            _latency_per_deployment: {
                api_base: 0.01336697916666667
            }
            """
            _message_to_send = ""
            _deployment_latencies = metadata["_latency_per_deployment"]
            if len(_deployment_latencies) == 0:
                return None
            _deployment_latency_map: Optional[dict] = None
            try:
                # try sorting deployments by latency
                _deployment_latencies = sorted(
                    _deployment_latencies.items(), key=lambda x: x[1]
                )
                _deployment_latency_map = dict(_deployment_latencies)
            except Exception:
                pass

            if _deployment_latency_map is None:
                return

            for api_base, latency in _deployment_latency_map.items():
                _message_to_send += f"\n{api_base}: {round(latency,2)}s"
            _message_to_send = "```" + _message_to_send + "```"
            return _message_to_send

    async def response_taking_too_long_callback(
        self,
        kwargs,  # kwargs to completion
        completion_response,  # response from completion
        start_time,
        end_time,  # start/end time
    ):
        if self.alerting is None or self.alert_types is None:
            return

        (
            time_difference_float,
            model,
            api_base,
            messages,
        ) = self._response_taking_too_long_callback_helper(
            kwargs=kwargs,
            start_time=start_time,
            end_time=end_time,
        )
        if litellm.turn_off_message_logging or litellm.redact_messages_in_exceptions:
            messages = "Message not logged. litellm.redact_messages_in_exceptions=True"
        request_info = f"\nRequest Model: `{model}`\nAPI Base: `{api_base}`\nMessages: `{messages}`"
        slow_message = f"`Responses are slow - {round(time_difference_float,2)}s response time > Alerting threshold: {self.alerting_threshold}s`"
        alerting_metadata: dict = {}
        if time_difference_float > self.alerting_threshold:
            # add deployment latencies to alert
            if (
                kwargs is not None
                and "litellm_params" in kwargs
                and "metadata" in kwargs["litellm_params"]
            ):
                _metadata: dict = kwargs["litellm_params"]["metadata"]
                request_info = _add_key_name_and_team_to_alert(
                    request_info=request_info, metadata=_metadata
                )

                _deployment_latency_map = self._get_deployment_latencies_to_alert(
                    metadata=_metadata
                )
                if _deployment_latency_map is not None:
                    request_info += (
                        f"\nAvailable Deployment Latencies\n{_deployment_latency_map}"
                    )

                if "alerting_metadata" in _metadata:
                    alerting_metadata = _metadata["alerting_metadata"]
            await self.send_alert(
                message=slow_message + request_info,
                level="Low",
                alert_type=AlertType.llm_too_slow,
                alerting_metadata=alerting_metadata,
            )

    async def async_update_daily_reports(
        self, deployment_metrics: DeploymentMetrics
    ) -> int:
        """
        Store the perf by deployment in cache
        - Number of failed requests per deployment
        - Latency / output tokens per deployment

        'deployment_id:daily_metrics:failed_requests'
        'deployment_id:daily_metrics:latency_per_output_token'

        Returns
            int - count of metrics set (1 - if just latency, 2 - if failed + latency)
        """

        return_val = 0
        try:
            ## FAILED REQUESTS ##
            if deployment_metrics.failed_request:
                await self.internal_usage_cache.async_increment_cache(
                    key="{}:{}".format(
                        deployment_metrics.id,
                        SlackAlertingCacheKeys.failed_requests_key.value,
                    ),
                    value=1,
                    parent_otel_span=None,  # no attached request, this is a background operation
                )

                return_val += 1

            ## LATENCY ##
            if deployment_metrics.latency_per_output_token is not None:
                await self.internal_usage_cache.async_increment_cache(
                    key="{}:{}".format(
                        deployment_metrics.id, SlackAlertingCacheKeys.latency_key.value
                    ),
                    value=deployment_metrics.latency_per_output_token,
                    parent_otel_span=None,  # no attached request, this is a background operation
                )

                return_val += 1

            return return_val
        except Exception:
            return 0

    async def send_daily_reports(self, router) -> bool:  # noqa: PLR0915
        """
        Send a daily report on:
        - Top 5 deployments with most failed requests
        - Top 5 slowest deployments (normalized by latency/output tokens)

        Get the value from redis cache (if available) or in-memory and send it

        Cleanup:
        - reset values in cache -> prevent memory leak

        Returns:
            True -> if successfuly sent
            False -> if not sent
        """

        ids = router.get_model_ids()

        # get keys
        failed_request_keys = [
            "{}:{}".format(id, SlackAlertingCacheKeys.failed_requests_key.value)
            for id in ids
        ]
        latency_keys = [
            "{}:{}".format(id, SlackAlertingCacheKeys.latency_key.value) for id in ids
        ]

        combined_metrics_keys = failed_request_keys + latency_keys  # reduce cache calls

        combined_metrics_values = await self.internal_usage_cache.async_batch_get_cache(
            keys=combined_metrics_keys
        )  # [1, 2, None, ..]

        if combined_metrics_values is None:
            return False

        all_none = True
        for val in combined_metrics_values:
            if val is not None and val > 0:
                all_none = False
                break

        if all_none:
            return False

        failed_request_values = combined_metrics_values[
            : len(failed_request_keys)
        ]  # # [1, 2, None, ..]
        latency_values = combined_metrics_values[len(failed_request_keys) :]

        # find top 5 failed
        ## Replace None values with a placeholder value (-1 in this case)
        placeholder_value = 0
        replaced_failed_values = [
            value if value is not None else placeholder_value
            for value in failed_request_values
        ]

        ## Get the indices of top 5 keys with the highest numerical values (ignoring None and 0 values)
        top_5_failed = sorted(
            range(len(replaced_failed_values)),
            key=lambda i: replaced_failed_values[i],
            reverse=True,
        )[:5]
        top_5_failed = [
            index for index in top_5_failed if replaced_failed_values[index] > 0
        ]

        # find top 5 slowest
        # Replace None values with a placeholder value (-1 in this case)
        placeholder_value = 0
        replaced_slowest_values = [
            value if value is not None else placeholder_value
            for value in latency_values
        ]

        # Get the indices of top 5 values with the highest numerical values (ignoring None and 0 values)
        top_5_slowest = sorted(
            range(len(replaced_slowest_values)),
            key=lambda i: replaced_slowest_values[i],
            reverse=True,
        )[:5]
        top_5_slowest = [
            index for index in top_5_slowest if replaced_slowest_values[index] > 0
        ]

        # format alert -> return the litellm model name + api base
        message = f"\n\nTime: `{time.time()}`s\nHere are today's key metrics 📈: \n\n"

        message += "\n\n*❗️ Top Deployments with Most Failed Requests:*\n\n"
        if not top_5_failed:
            message += "\tNone\n"
        for i in range(len(top_5_failed)):
            key = failed_request_keys[top_5_failed[i]].split(":")[0]
            _deployment = router.get_model_info(key)
            if isinstance(_deployment, dict):
                deployment_name = _deployment["litellm_params"].get("model", "")
            else:
                return False

            api_base = litellm.get_api_base(
                model=deployment_name,
                optional_params=(
                    _deployment["litellm_params"] if _deployment is not None else {}
                ),
            )
            if api_base is None:
                api_base = ""
            value = replaced_failed_values[top_5_failed[i]]
            message += f"\t{i+1}. Deployment: `{deployment_name}`, Failed Requests: `{value}`,  API Base: `{api_base}`\n"

        message += "\n\n*😅 Top Slowest Deployments:*\n\n"
        if not top_5_slowest:
            message += "\tNone\n"
        for i in range(len(top_5_slowest)):
            key = latency_keys[top_5_slowest[i]].split(":")[0]
            _deployment = router.get_model_info(key)
            if _deployment is not None:
                deployment_name = _deployment["litellm_params"].get("model", "")
            else:
                deployment_name = ""
            api_base = litellm.get_api_base(
                model=deployment_name,
                optional_params=(
                    _deployment["litellm_params"] if _deployment is not None else {}
                ),
            )
            value = round(replaced_slowest_values[top_5_slowest[i]], 3)
            message += f"\t{i+1}. Deployment: `{deployment_name}`, Latency per output token: `{value}s/token`,  API Base: `{api_base}`\n\n"

        # cache cleanup -> reset values to 0
        latency_cache_keys = [(key, 0) for key in latency_keys]
        failed_request_cache_keys = [(key, 0) for key in failed_request_keys]
        combined_metrics_cache_keys = latency_cache_keys + failed_request_cache_keys
        await self.internal_usage_cache.async_set_cache_pipeline(
            cache_list=combined_metrics_cache_keys
        )

        message += f"\n\nNext Run is at: `{time.time() + self.alerting_args.daily_report_frequency}`s"

        # send alert
        await self.send_alert(
            message=message,
            level="Low",
            alert_type=AlertType.daily_reports,
            alerting_metadata={},
        )

        return True

    async def response_taking_too_long(
        self,
        request_data: Optional[dict] = None,
    ):
        if self.alerting is None or self.alert_types is None:
            return

        if AlertType.llm_requests_hanging not in self.alert_types:
            return

        await self.hanging_request_check.add_request_to_hanging_request_check(
            request_data=request_data
        )

    async def failed_tracking_alert(self, error_message: str, failing_model: str):
        """
        Raise alert when tracking failed for specific model

        Args:
            error_message (str): Error message
            failing_model (str): Model that failed tracking
        """
        if self.alerting is None or self.alert_types is None:
            # do nothing if alerting is not switched on
            return
        if "failed_tracking_spend" not in self.alert_types:
            return

        _cache: DualCache = self.internal_usage_cache
        message = "Failed Tracking Cost for " + error_message
        _cache_key = "budget_alerts:failed_tracking:{}".format(failing_model)
        result = await _cache.async_get_cache(key=_cache_key)
        if result is None:
            await self.send_alert(
                message=message,
                level="High",
                alert_type=AlertType.failed_tracking_spend,
                alerting_metadata={},
            )
            await _cache.async_set_cache(
                key=_cache_key,
                value="SENT",
                ttl=self.alerting_args.budget_alert_ttl,
            )

    async def budget_alerts(
        self,
        type: Literal[
            "token_budget",
            "soft_budget",
            "user_budget",
            "team_budget",
            "proxy_budget",
            "projected_limit_exceeded",
        ],
        user_info: CallInfo,
    ):
        """
        Send a budget alert on slack or webhook

        Args:
            type: The type of budget alert to send
            user_info: The user info to send the alert for
        """
        ## PREVENTITIVE ALERTING ## - https://github.com/BerriAI/litellm/issues/2727
        # - Alert once within 24hr period
        # - Cache this information
        # - Don't re-alert, if alert already sent
        _cache: DualCache = self.internal_usage_cache

        if self.alerting is None or self.alert_types is None:
            # do nothing if alerting is not switched on
            return
        if "budget_alerts" not in self.alert_types:
            return

        # Get the appropriate budget alert type handler
        budget_alert_class = get_budget_alert_type(type)
        _id = budget_alert_class.get_id(user_info)
        user_info_json = user_info.model_dump(exclude_none=True)
        user_info_str = self._get_user_info_str(user_info)
        event_message = budget_alert_class.get_event_message()

        # Set default event unless we're in projected_limit_exceeded
        event: Optional[
            Literal[
                "budget_crossed",
                "threshold_crossed",
                "projected_limit_exceeded",
                "soft_budget_crossed",
            ]
        ] = (
            "projected_limit_exceeded" if type == "projected_limit_exceeded" else None
        )

        webhook_event: Optional[WebhookEvent] = None

        # percent of max_budget left to spend
        if user_info.max_budget is None and user_info.soft_budget is None:
            return

        # check if crossed budget
        event, event_message = self._get_event_and_event_message(
            event=event,
            user_info=user_info,
            event_message=event_message,
        )

        # send alert
        if event is not None and user_info.event_group is not None:
            _cache_key = "budget_alerts:{}:{}".format(event, _id)
            result = await _cache.async_get_cache(key=_cache_key)
            if result is None:
                webhook_event = WebhookEvent(
                    event=event,
                    event_message=event_message,
                    **user_info_json,
                )
                await self.send_alert(
                    message=event_message + "\n\n" + user_info_str,
                    level="High",
                    alert_type=AlertType.budget_alerts,
                    user_info=webhook_event,
                    alerting_metadata={},
                )
                await _cache.async_set_cache(
                    key=_cache_key,
                    value="SENT",
                    ttl=self.alerting_args.budget_alert_ttl,
                )

            return
        return

    def _get_event_and_event_message(
        self,
        user_info: CallInfo,
        event: Optional[
            Literal[
                "budget_crossed",
                "threshold_crossed",
                "soft_budget_crossed",
                "projected_limit_exceeded",
            ]
        ],
        event_message: str,
    ) -> Tuple[
        Optional[
            Literal[
                "budget_crossed",
                "threshold_crossed",
                "soft_budget_crossed",
                "projected_limit_exceeded",
            ]
        ],
        str,
    ]:
        """
        Get the event and event message for a budget alert

        This will append any new information to the event_message

        Handles Max Budget and Soft Budget Alerts
        """
        percent_left: float = self._get_percent_of_max_budget_left(user_info=user_info)

        #####################################################################
        # SOFT BUDGET CHECK
        # Check if the key/team/user has a soft budget set and they have crossed it
        #####################################################################
        if user_info.soft_budget is not None:
            if user_info.spend >= user_info.soft_budget:
                event = "soft_budget_crossed"
                event_message += f"Total Soft Budget:`{user_info.soft_budget}`"

        #####################################################################
        # MAX BUDGET CHECK
        # Check if the key/team/user has a max budget set and they have either
        ## a. Crossed their max budget
        ## b. Either 5% or 15% of their max budget is left
        #####################################################################
        if user_info.max_budget is not None:
            if user_info.spend >= user_info.max_budget:
                event = "budget_crossed"
                event_message += (
                    f"Budget Crossed\n Total Budget:`{user_info.max_budget}`"
                )
            elif percent_left <= SLACK_ALERTING_THRESHOLD_5_PERCENT:
                event = "threshold_crossed"
                event_message += "5% Threshold Crossed "
            elif percent_left <= SLACK_ALERTING_THRESHOLD_15_PERCENT:
                event = "threshold_crossed"
                event_message += "15% Threshold Crossed"

        return event, event_message

    def _get_percent_of_max_budget_left(self, user_info: CallInfo) -> float:
        """
        Get the percent of the max budget that is left
        """
        percent_left: float = 0.0
        current_spend: float = user_info.spend
        max_budget: Optional[float] = user_info.max_budget
        if max_budget is None:
            return percent_left
        if max_budget <= 0:
            return percent_left
        percent_left = (max_budget - current_spend) / max_budget
        return percent_left

    def _get_user_info_str(self, user_info: CallInfo) -> str:
        """
        Create a standard message for a budget alert
        """
        _all_fields_as_dict = user_info.model_dump(exclude_none=True)
        _all_fields_as_dict.pop("token")
        msg = ""
        for k, v in _all_fields_as_dict.items():
            if isinstance(v, Litellm_EntityType):
                v = v.value
            msg += f"*{k}:* `{v}`\n"

        return msg

    async def customer_spend_alert(
        self,
        token: Optional[str],
        key_alias: Optional[str],
        end_user_id: Optional[str],
        response_cost: Optional[float],
        max_budget: Optional[float],
    ):
        if (
            self.alerting is not None
            and "webhook" in self.alerting
            and end_user_id is not None
            and token is not None
            and response_cost is not None
        ):
            # log customer spend
            event = WebhookEvent(
                spend=response_cost,
                max_budget=max_budget,
                token=token,
                customer_id=end_user_id,
                user_id=None,
                team_id=None,
                user_email=None,
                key_alias=key_alias,
                projected_exceeded_date=None,
                projected_spend=None,
                event="spend_tracked",
                event_group=Litellm_EntityType.END_USER,
                event_message="Customer spend tracked. Customer={}, spend={}".format(
                    end_user_id, response_cost
                ),
            )

            await self.send_webhook_alert(webhook_event=event)

    def _count_outage_alerts(self, alerts: List[int]) -> str:
        """
        Parameters:
        - alerts: List[int] -> list of error codes (either 408 or 500+)

        Returns:
        - str -> formatted string. This is an alert message, giving a human-friendly description of the errors.
        """
        error_breakdown = {"Timeout Errors": 0, "API Errors": 0, "Unknown Errors": 0}
        for alert in alerts:
            if alert == 408:
                error_breakdown["Timeout Errors"] += 1
            elif alert >= 500:
                error_breakdown["API Errors"] += 1
            else:
                error_breakdown["Unknown Errors"] += 1

        error_msg = ""
        for key, value in error_breakdown.items():
            if value > 0:
                error_msg += "\n{}: {}\n".format(key, value)

        return error_msg

    def _outage_alert_msg_factory(
        self,
        alert_type: Literal["Major", "Minor"],
        key: Literal["Model", "Region"],
        key_val: str,
        provider: str,
        api_base: Optional[str],
        outage_value: BaseOutageModel,
    ) -> str:
        """Format an alert message for slack"""
        headers = {f"{key} Name": key_val, "Provider": provider}
        if api_base is not None:
            headers["API Base"] = api_base  # type: ignore

        headers_str = "\n"
        for k, v in headers.items():
            headers_str += f"*{k}:* `{v}`\n"
        return f"""\n\n
*⚠️ {alert_type} Service Outage*

{headers_str}

*Errors:*
{self._count_outage_alerts(alerts=outage_value["alerts"])}

*Last Check:* `{round(time.time() - outage_value["last_updated_at"], 4)}s ago`\n\n
"""

    async def region_outage_alerts(
        self,
        exception: APIError,
        deployment_id: str,
    ) -> None:
        """
        Send slack alert if specific provider region is having an outage.

        Track for 408 (Timeout) and >=500 Error codes
        """
        ## CREATE (PROVIDER+REGION) ID ##
        if self.llm_router is None:
            return

        deployment = self.llm_router.get_deployment(model_id=deployment_id)

        if deployment is None:
            return

        model = deployment.litellm_params.model
        ### GET PROVIDER ###
        provider = deployment.litellm_params.custom_llm_provider
        if provider is None:
            model, provider, _, _ = litellm.get_llm_provider(model=model)

        ### GET REGION ###
        region_name = deployment.litellm_params.region_name
        if region_name is None:
            region_name = litellm.utils._get_model_region(
                custom_llm_provider=provider, litellm_params=deployment.litellm_params
            )

        if region_name is None:
            return

        ### UNIQUE CACHE KEY ###
        cache_key = provider + region_name

        outage_value: Optional[ProviderRegionOutageModel] = (
            await self.internal_usage_cache.async_get_cache(key=cache_key)
        )

        if (
            getattr(exception, "status_code", None) is None
            or (
                exception.status_code != 408  # type: ignore
                and exception.status_code < 500  # type: ignore
            )
            or self.llm_router is None
        ):
            return

        if outage_value is None:
            _deployment_set = set()
            _deployment_set.add(deployment_id)
            outage_value = ProviderRegionOutageModel(
                provider_region_id=cache_key,
                alerts=[exception.status_code],  # type: ignore
                minor_alert_sent=False,
                major_alert_sent=False,
                last_updated_at=time.time(),
                deployment_ids=_deployment_set,
            )

            ## add to cache ##
            await self.internal_usage_cache.async_set_cache(
                key=cache_key,
                value=outage_value,
                ttl=self.alerting_args.region_outage_alert_ttl,
            )
            return

        if len(outage_value["alerts"]) < self.alerting_args.max_outage_alert_list_size:
            outage_value["alerts"].append(exception.status_code)  # type: ignore
        else:  # prevent memory leaks
            pass
        _deployment_set = outage_value["deployment_ids"]
        _deployment_set.add(deployment_id)
        outage_value["deployment_ids"] = _deployment_set
        outage_value["last_updated_at"] = time.time()

        ## MINOR OUTAGE ALERT SENT ##
        if (
            outage_value["minor_alert_sent"] is False
            and len(outage_value["alerts"])
            >= self.alerting_args.minor_outage_alert_threshold
            and len(_deployment_set) > 1  # make sure it's not just 1 bad deployment
        ):
            msg = self._outage_alert_msg_factory(
                alert_type="Minor",
                key="Region",
                key_val=region_name,
                api_base=None,
                outage_value=outage_value,
                provider=provider,
            )
            # send minor alert
            await self.send_alert(
                message=msg,
                level="Medium",
                alert_type=AlertType.outage_alerts,
                alerting_metadata={},
            )
            # set to true
            outage_value["minor_alert_sent"] = True

        ## MAJOR OUTAGE ALERT SENT ##
        elif (
            outage_value["major_alert_sent"] is False
            and len(outage_value["alerts"])
            >= self.alerting_args.major_outage_alert_threshold
            and len(_deployment_set) > 1  # make sure it's not just 1 bad deployment
        ):
            msg = self._outage_alert_msg_factory(
                alert_type="Major",
                key="Region",
                key_val=region_name,
                api_base=None,
                outage_value=outage_value,
                provider=provider,
            )

            # send minor alert
            await self.send_alert(
                message=msg,
                level="High",
                alert_type=AlertType.outage_alerts,
                alerting_metadata={},
            )
            # set to true
            outage_value["major_alert_sent"] = True

        ## update cache ##
        await self.internal_usage_cache.async_set_cache(
            key=cache_key, value=outage_value
        )

    async def outage_alerts(
        self,
        exception: APIError,
        deployment_id: str,
    ) -> None:
        """
        Send slack alert if model is badly configured / having an outage (408, 401, 429, >=500).

        key = model_id

        value = {
        - model_id
        - threshold
        - alerts []
        }

        ttl = 1hr
        max_alerts_size = 10
        """
        try:
            outage_value: Optional[OutageModel] = await self.internal_usage_cache.async_get_cache(key=deployment_id)  # type: ignore
            if (
                getattr(exception, "status_code", None) is None
                or (
                    exception.status_code != 408  # type: ignore
                    and exception.status_code < 500  # type: ignore
                )
                or self.llm_router is None
            ):
                return

            ### EXTRACT MODEL DETAILS ###
            deployment = self.llm_router.get_deployment(model_id=deployment_id)
            if deployment is None:
                return

            model = deployment.litellm_params.model
            provider = deployment.litellm_params.custom_llm_provider
            if provider is None:
                try:
                    model, provider, _, _ = litellm.get_llm_provider(model=model)
                except Exception:
                    provider = ""
            api_base = litellm.get_api_base(
                model=model, optional_params=deployment.litellm_params
            )

            if outage_value is None:
                outage_value = OutageModel(
                    model_id=deployment_id,
                    alerts=[exception.status_code],  # type: ignore
                    minor_alert_sent=False,
                    major_alert_sent=False,
                    last_updated_at=time.time(),
                )

                ## add to cache ##
                await self.internal_usage_cache.async_set_cache(
                    key=deployment_id,
                    value=outage_value,
                    ttl=self.alerting_args.outage_alert_ttl,
                )
                return

            if (
                len(outage_value["alerts"])
                < self.alerting_args.max_outage_alert_list_size
            ):
                outage_value["alerts"].append(exception.status_code)  # type: ignore
            else:  # prevent memory leaks
                pass

            outage_value["last_updated_at"] = time.time()

            ## MINOR OUTAGE ALERT SENT ##
            if (
                outage_value["minor_alert_sent"] is False
                and len(outage_value["alerts"])
                >= self.alerting_args.minor_outage_alert_threshold
            ):
                msg = self._outage_alert_msg_factory(
                    alert_type="Minor",
                    key="Model",
                    key_val=model,
                    api_base=api_base,
                    outage_value=outage_value,
                    provider=provider,
                )
                # send minor alert
                await self.send_alert(
                    message=msg,
                    level="Medium",
                    alert_type=AlertType.outage_alerts,
                    alerting_metadata={},
                )
                # set to true
                outage_value["minor_alert_sent"] = True
            elif (
                outage_value["major_alert_sent"] is False
                and len(outage_value["alerts"])
                >= self.alerting_args.major_outage_alert_threshold
            ):
                msg = self._outage_alert_msg_factory(
                    alert_type="Major",
                    key="Model",
                    key_val=model,
                    api_base=api_base,
                    outage_value=outage_value,
                    provider=provider,
                )
                # send minor alert
                await self.send_alert(
                    message=msg,
                    level="High",
                    alert_type=AlertType.outage_alerts,
                    alerting_metadata={},
                )
                # set to true
                outage_value["major_alert_sent"] = True

            ## update cache ##
            await self.internal_usage_cache.async_set_cache(
                key=deployment_id, value=outage_value
            )
        except Exception:
            pass

    async def model_added_alert(
        self, model_name: str, litellm_model_name: str, passed_model_info: Any
    ):
        base_model_from_user = getattr(passed_model_info, "base_model", None)
        model_info = {}
        base_model = ""
        if base_model_from_user is not None:
            model_info = litellm.model_cost.get(base_model_from_user, {})
            base_model = f"Base Model: `{base_model_from_user}`\n"
        else:
            model_info = litellm.model_cost.get(litellm_model_name, {})
        model_info_str = ""
        for k, v in model_info.items():
            if k == "input_cost_per_token" or k == "output_cost_per_token":
                # when converting to string it should not be 1.63e-06
                v = "{:.8f}".format(v)

            model_info_str += f"{k}: {v}\n"

        message = f"""
*🚅 New Model Added*
Model Name: `{model_name}`
{base_model}

Usage OpenAI Python SDK:
```
import openai
client = openai.OpenAI(
    api_key="your_api_key",
    base_url={os.getenv("PROXY_BASE_URL", "http://0.0.0.0:4000")}
)

response = client.chat.completions.create(
    model="{model_name}", # model to send to the proxy
    messages = [
        {{
            "role": "user",
            "content": "this is a test request, write a short poem"
        }}
    ]
)
```

Model Info: 
```
{model_info_str}
```
"""

        alert_val = self.send_alert(
            message=message,
            level="Low",
            alert_type=AlertType.new_model_added,
            alerting_metadata={},
        )

        if alert_val is not None and asyncio.iscoroutine(alert_val):
            await alert_val

    async def model_removed_alert(self, model_name: str):
        pass

    async def send_webhook_alert(self, webhook_event: WebhookEvent) -> bool:
        """
        Sends structured alert to webhook, if set.

        Currently only implemented for budget alerts

        Returns -> True if sent, False if not.

        Raises Exception
            - if WEBHOOK_URL is not set
        """

        webhook_url = os.getenv("WEBHOOK_URL", None)
        if webhook_url is None:
            raise Exception("Missing webhook_url from environment")

        payload = webhook_event.model_dump_json()
        headers = {"Content-type": "application/json"}

        response = await self.async_http_handler.post(
            url=webhook_url,
            headers=headers,
            data=payload,
        )
        if response.status_code == 200:
            return True
        else:
            print("Error sending webhook alert. Error=", response.text)  # noqa

        return False

    async def _check_if_using_premium_email_feature(
        self,
        premium_user: bool,
        email_logo_url: Optional[str] = None,
        email_support_contact: Optional[str] = None,
    ):
        from litellm.proxy.proxy_server import CommonProxyErrors, premium_user

        if premium_user is not True:
            if email_logo_url is not None or email_support_contact is not None:
                raise ValueError(
                    f"Trying to Customize Email Alerting\n {CommonProxyErrors.not_premium_user.value}"
                )
        return

    async def send_key_created_or_user_invited_email(
        self, webhook_event: WebhookEvent
    ) -> bool:
        try:
            from litellm.proxy.utils import send_email

            if self.alerting is None or "email" not in self.alerting:
                # do nothing if user does not want email alerts
                verbose_proxy_logger.error(
                    "Error sending email alert - 'email' not in self.alerting %s",
                    self.alerting,
                )
                return False
            from litellm.proxy.proxy_server import premium_user, prisma_client

            email_logo_url = os.getenv(
                "SMTP_SENDER_LOGO", os.getenv("EMAIL_LOGO_URL", None)
            )
            email_support_contact = os.getenv("EMAIL_SUPPORT_CONTACT", None)
            await self._check_if_using_premium_email_feature(
                premium_user, email_logo_url, email_support_contact
            )
            if email_logo_url is None:
                email_logo_url = LITELLM_LOGO_URL
            if email_support_contact is None:
                email_support_contact = LITELLM_SUPPORT_CONTACT

            event_name = webhook_event.event_message
            recipient_email = webhook_event.user_email
            recipient_user_id = webhook_event.user_id
            if (
                recipient_email is None
                and recipient_user_id is not None
                and prisma_client is not None
            ):
                user_row = await prisma_client.db.litellm_usertable.find_unique(
                    where={"user_id": recipient_user_id}
                )

                if user_row is not None:
                    recipient_email = user_row.user_email

            key_token = webhook_event.token
            key_budget = webhook_event.max_budget
            base_url = os.getenv("PROXY_BASE_URL", "http://0.0.0.0:4000")

            email_html_content = "Alert from LiteLLM Server"
            if recipient_email is None:
                verbose_proxy_logger.error(
                    "Trying to send email alert to no recipient",
                    extra=webhook_event.dict(),
                )

            if webhook_event.event == "key_created":
                email_html_content = KEY_CREATED_EMAIL_TEMPLATE.format(
                    email_logo_url=email_logo_url,
                    recipient_email=recipient_email,
                    key_budget=key_budget,
                    key_token=key_token,
                    base_url=base_url,
                    email_support_contact=email_support_contact,
                )
            elif webhook_event.event == "internal_user_created":
                # GET TEAM NAME
                team_id = webhook_event.team_id
                team_name = "Default Team"
                if team_id is not None and prisma_client is not None:
                    team_row = await prisma_client.db.litellm_teamtable.find_unique(
                        where={"team_id": team_id}
                    )
                    if team_row is not None:
                        team_name = team_row.team_alias or "-"
                email_html_content = USER_INVITED_EMAIL_TEMPLATE.format(
                    email_logo_url=email_logo_url,
                    recipient_email=recipient_email,
                    team_name=team_name,
                    base_url=base_url,
                    email_support_contact=email_support_contact,
                )
            else:
                verbose_proxy_logger.error(
                    "Trying to send email alert on unknown webhook event",
                    extra=webhook_event.model_dump(),
                )

            webhook_event.model_dump_json()
            email_event = {
                "to": recipient_email,
                "subject": f"LiteLLM: {event_name}",
                "html": email_html_content,
            }

            await send_email(
                receiver_email=email_event["to"],
                subject=email_event["subject"],
                html=email_event["html"],
            )

            return True

        except Exception as e:
            verbose_proxy_logger.error("Error sending email alert %s", str(e))
            return False

    async def send_email_alert_using_smtp(
        self, webhook_event: WebhookEvent, alert_type: str
    ) -> bool:
        """
        Sends structured Email alert to an SMTP server

        Currently only implemented for budget alerts

        Returns -> True if sent, False if not.
        """
        from litellm.proxy.proxy_server import premium_user
        from litellm.proxy.utils import send_email

        email_logo_url = os.getenv(
            "SMTP_SENDER_LOGO", os.getenv("EMAIL_LOGO_URL", None)
        )
        email_support_contact = os.getenv("EMAIL_SUPPORT_CONTACT", None)
        await self._check_if_using_premium_email_feature(
            premium_user, email_logo_url, email_support_contact
        )

        if email_logo_url is None:
            email_logo_url = LITELLM_LOGO_URL
        if email_support_contact is None:
            email_support_contact = LITELLM_SUPPORT_CONTACT

        event_name = webhook_event.event_message
        recipient_email = webhook_event.user_email
        user_name = webhook_event.user_id
        max_budget = webhook_event.max_budget
        email_html_content = "Alert from LiteLLM Server"
        if recipient_email is None:
            verbose_proxy_logger.error(
                "Trying to send email alert to no recipient", extra=webhook_event.dict()
            )

        if webhook_event.event == "budget_crossed":
            email_html_content = f"""
            <img src="{email_logo_url}" alt="LiteLLM Logo" width="150" height="50" />

            <p> Hi {user_name}, <br/>

            Your LLM API usage this month has reached your account's <b> monthly budget of ${max_budget} </b> <br /> <br />

            API requests will be rejected until either (a) you increase your monthly budget or (b) your monthly usage resets at the beginning of the next calendar month. <br /> <br />

            If you have any questions, please send an email to {email_support_contact} <br /> <br />

            Best, <br />
            The LiteLLM team <br />
            """

        webhook_event.model_dump_json()
        email_event = {
            "to": recipient_email,
            "subject": f"LiteLLM: {event_name}",
            "html": email_html_content,
        }

        await send_email(
            receiver_email=email_event["to"],
            subject=email_event["subject"],
            html=email_event["html"],
        )
        if webhook_event.event_group == "team":
            from litellm.integrations.email_alerting import send_team_budget_alert

            await send_team_budget_alert(webhook_event=webhook_event)

        return False

    async def send_alert(
        self,
        message: str,
        level: Literal["Low", "Medium", "High"],
        alert_type: AlertType,
        alerting_metadata: dict,
        user_info: Optional[WebhookEvent] = None,
        **kwargs,
    ):
        """
        Alerting based on thresholds: - https://github.com/BerriAI/litellm/issues/1298

        - Responses taking too long
        - Requests are hanging
        - Calls are failing
        - DB Read/Writes are failing
        - Proxy Close to max budget
        - Key Close to max budget

        Parameters:
            level: str - Low|Medium|High - if calls might fail (Medium) or are failing (High); Currently, no alerts would be 'Low'.
            message: str - what is the alert about
        """
        if self.alerting is None:
            return

        if (
            "webhook" in self.alerting
            and alert_type == "budget_alerts"
            and user_info is not None
        ):
            await self.send_webhook_alert(webhook_event=user_info)

        if (
            "email" in self.alerting
            and alert_type == "budget_alerts"
            and user_info is not None
        ):
            # only send budget alerts over Email
            await self.send_email_alert_using_smtp(
                webhook_event=user_info, alert_type=alert_type
            )

        if "slack" not in self.alerting:
            return
        if alert_type not in self.alert_types:
            return

        from datetime import datetime

        # Get the current timestamp
        current_time = datetime.now().strftime("%H:%M:%S")
        _proxy_base_url = os.getenv("PROXY_BASE_URL", None)
        if alert_type == "daily_reports" or alert_type == "new_model_added":
            formatted_message = message
        else:
            formatted_message = (
                f"Level: `{level}`\nTimestamp: `{current_time}`\n\nMessage: {message}"
            )

        if kwargs:
            for key, value in kwargs.items():
                formatted_message += f"\n\n{key}: `{value}`\n\n"
        if alerting_metadata:
            for key, value in alerting_metadata.items():
                formatted_message += f"\n\n*Alerting Metadata*: \n{key}: `{value}`\n\n"
        if _proxy_base_url is not None:
            formatted_message += f"\n\nProxy URL: `{_proxy_base_url}`"

        # check if we find the slack webhook url in self.alert_to_webhook_url
        if (
            self.alert_to_webhook_url is not None
            and alert_type in self.alert_to_webhook_url
        ):
            slack_webhook_url: Optional[Union[str, List[str]]] = (
                self.alert_to_webhook_url[alert_type]
            )
        elif self.default_webhook_url is not None:
            slack_webhook_url = self.default_webhook_url
        else:
            slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", None)

        if slack_webhook_url is None:
            raise ValueError("Missing SLACK_WEBHOOK_URL from environment")
        payload = {"text": formatted_message}
        headers = {"Content-type": "application/json"}

        if isinstance(slack_webhook_url, list):
            for url in slack_webhook_url:
                self.log_queue.append(
                    {
                        "url": url,
                        "headers": headers,
                        "payload": payload,
                        "alert_type": alert_type,
                    }
                )
        else:
            self.log_queue.append(
                {
                    "url": slack_webhook_url,
                    "headers": headers,
                    "payload": payload,
                    "alert_type": alert_type,
                }
            )

        if len(self.log_queue) >= self.batch_size:
            await self.flush_queue()

    async def async_send_batch(self):
        if not self.log_queue:
            return

        squashed_queue = squash_payloads(self.log_queue)
        tasks = [
            send_to_webhook(
                slackAlertingInstance=self, item=item["item"], count=item["count"]
            )
            for item in squashed_queue.values()
        ]
        await asyncio.gather(*tasks)
        self.log_queue.clear()

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """Log deployment latency"""
        try:
            if "daily_reports" in self.alert_types:
                litellm_params = kwargs.get("litellm_params", {}) or {}
                model_info = litellm_params.get("model_info", {}) or {}
                model_id = model_info.get("id", "") or ""
                response_s: timedelta = end_time - start_time

                final_value = response_s

                if isinstance(response_obj, litellm.ModelResponse) and (
                    hasattr(response_obj, "usage")
                    and response_obj.usage is not None  # type: ignore
                    and hasattr(response_obj.usage, "completion_tokens")  # type: ignore
                ):
                    completion_tokens = response_obj.usage.completion_tokens  # type: ignore
                    if completion_tokens is not None and completion_tokens > 0:
                        final_value = float(
                            response_s.total_seconds() / completion_tokens
                        )
                if isinstance(final_value, timedelta):
                    final_value = final_value.total_seconds()

                await self.async_update_daily_reports(
                    DeploymentMetrics(
                        id=model_id,
                        failed_request=False,
                        latency_per_output_token=final_value,
                        updated_at=litellm.utils.get_utc_datetime(),
                    )
                )
        except Exception as e:
            verbose_proxy_logger.error(
                f"[Non-Blocking Error] Slack Alerting: Got error in logging LLM deployment latency: {str(e)}"
            )
            pass

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """Log failure + deployment latency"""
        _litellm_params = kwargs.get("litellm_params", {})
        _model_info = _litellm_params.get("model_info", {}) or {}
        model_id = _model_info.get("id", "")
        try:
            if "daily_reports" in self.alert_types:
                try:
                    await self.async_update_daily_reports(
                        DeploymentMetrics(
                            id=model_id,
                            failed_request=True,
                            latency_per_output_token=None,
                            updated_at=litellm.utils.get_utc_datetime(),
                        )
                    )
                except Exception as e:
                    verbose_logger.debug(f"Exception raises -{str(e)}")

            if isinstance(kwargs.get("exception", ""), APIError):
                if "outage_alerts" in self.alert_types:
                    await self.outage_alerts(
                        exception=kwargs["exception"],
                        deployment_id=model_id,
                    )

                if "region_outage_alerts" in self.alert_types:
                    await self.region_outage_alerts(
                        exception=kwargs["exception"], deployment_id=model_id
                    )
        except Exception:
            pass

    async def _run_scheduler_helper(self, llm_router) -> bool:
        """
        Returns:
        - True -> report sent
        - False -> report not sent
        """
        report_sent_bool = False

        report_sent = await self.internal_usage_cache.async_get_cache(
            key=SlackAlertingCacheKeys.report_sent_key.value,
            parent_otel_span=None,
        )  # None | float

        current_time = time.time()

        if report_sent is None:
            await self.internal_usage_cache.async_set_cache(
                key=SlackAlertingCacheKeys.report_sent_key.value,
                value=current_time,
            )
        elif isinstance(report_sent, float):
            # Check if current time - interval >= time last sent
            interval_seconds = self.alerting_args.daily_report_frequency

            if current_time - report_sent >= interval_seconds:
                # Sneak in the reporting logic here
                await self.send_daily_reports(router=llm_router)
                # Also, don't forget to update the report_sent time after sending the report!
                await self.internal_usage_cache.async_set_cache(
                    key=SlackAlertingCacheKeys.report_sent_key.value,
                    value=current_time,
                )
                report_sent_bool = True

        return report_sent_bool

    async def _run_scheduled_daily_report(self, llm_router: Optional[Any] = None):
        """
        If 'daily_reports' enabled

        Ping redis cache every 5 minutes to check if we should send the report

        If yes -> call send_daily_report()
        """
        if llm_router is None or self.alert_types is None:
            return

        if "daily_reports" in self.alert_types:
            while True:
                await self._run_scheduler_helper(llm_router=llm_router)
                interval = random.randint(
                    self.alerting_args.report_check_interval - 3,
                    self.alerting_args.report_check_interval + 3,
                )  # shuffle to prevent collisions
                await asyncio.sleep(interval)
        return

    async def send_weekly_spend_report(
        self,
        time_range: str = "7d",
    ):
        """
        Send a spend report for a configurable time range.

        Args:
            time_range: A string specifying the time range for the report, e.g., "1d", "7d", "30d"
        """
        if self.alerting is None or "spend_reports" not in self.alert_types:
            return

        try:
            from litellm.proxy.spend_tracking.spend_management_endpoints import (
                _get_spend_report_for_time_range,
            )

            # Parse the time range
            days = int(time_range[:-1])
            if time_range[-1].lower() != "d":
                raise ValueError("Time range must be specified in days, e.g., '7d'")

            todays_date = datetime.datetime.now().date()
            start_date = todays_date - datetime.timedelta(days=days)

            _event_cache_key = f"weekly_spend_report_sent_{start_date.strftime('%Y-%m-%d')}_{todays_date.strftime('%Y-%m-%d')}"
            if await self.internal_usage_cache.async_get_cache(key=_event_cache_key):
                return

            _resp = await _get_spend_report_for_time_range(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=todays_date.strftime("%Y-%m-%d"),
            )
            if _resp is None or _resp == ([], []):
                return

            spend_per_team, spend_per_tag = _resp

            _spend_message = f"*💸 Spend Report for `{start_date.strftime('%m-%d-%Y')} - {todays_date.strftime('%m-%d-%Y')}` ({days} days)*\n"

            if spend_per_team is not None:
                _spend_message += "\n*Team Spend Report:*\n"
                for spend in spend_per_team:
                    _team_spend = round(float(spend["total_spend"]), 4)
                    _spend_message += (
                        f"Team: `{spend['team_alias']}` | Spend: `${_team_spend}`\n"
                    )

            if spend_per_tag is not None:
                _spend_message += "\n*Tag Spend Report:*\n"
                for spend in spend_per_tag:
                    _tag_spend = round(float(spend["total_spend"]), 4)
                    _spend_message += f"Tag: `{spend['individual_request_tag']}` | Spend: `${_tag_spend}`\n"

            await self.send_alert(
                message=_spend_message,
                level="Low",
                alert_type=AlertType.spend_reports,
                alerting_metadata={},
            )

            await self.internal_usage_cache.async_set_cache(
                key=_event_cache_key,
                value="SENT",
                ttl=duration_in_seconds(time_range),
            )

        except ValueError as ve:
            verbose_proxy_logger.error(f"Invalid time range format: {ve}")
        except Exception as e:
            verbose_proxy_logger.error(f"Error sending spend report: {e}")

    async def send_monthly_spend_report(self):
        """ """
        try:
            from calendar import monthrange

            from litellm.proxy.spend_tracking.spend_management_endpoints import (
                _get_spend_report_for_time_range,
            )

            todays_date = datetime.datetime.now().date()
            first_day_of_month = todays_date.replace(day=1)
            _, last_day_of_month = monthrange(todays_date.year, todays_date.month)
            last_day_of_month = first_day_of_month + datetime.timedelta(
                days=last_day_of_month - 1
            )

            _event_cache_key = f"monthly_spend_report_sent_{first_day_of_month.strftime('%Y-%m-%d')}_{last_day_of_month.strftime('%Y-%m-%d')}"
            if await self.internal_usage_cache.async_get_cache(key=_event_cache_key):
                return

            _resp = await _get_spend_report_for_time_range(
                start_date=first_day_of_month.strftime("%Y-%m-%d"),
                end_date=last_day_of_month.strftime("%Y-%m-%d"),
            )

            if _resp is None or _resp == ([], []):
                return

            monthly_spend_per_team, monthly_spend_per_tag = _resp

            _spend_message = f"*💸 Monthly Spend Report for `{first_day_of_month.strftime('%m-%d-%Y')} - {last_day_of_month.strftime('%m-%d-%Y')}` *\n"

            if monthly_spend_per_team is not None:
                _spend_message += "\n*Team Spend Report:*\n"
                for spend in monthly_spend_per_team:
                    _team_spend = spend["total_spend"]
                    _team_spend = float(_team_spend)
                    # round to 4 decimal places
                    _team_spend = round(_team_spend, 4)
                    _spend_message += (
                        f"Team: `{spend['team_alias']}` | Spend: `${_team_spend}`\n"
                    )

            if monthly_spend_per_tag is not None:
                _spend_message += "\n*Tag Spend Report:*\n"
                for spend in monthly_spend_per_tag:
                    _tag_spend = spend["total_spend"]
                    _tag_spend = float(_tag_spend)
                    # round to 4 decimal places
                    _tag_spend = round(_tag_spend, 4)
                    _spend_message += f"Tag: `{spend['individual_request_tag']}` | Spend: `${_tag_spend}`\n"

            await self.send_alert(
                message=_spend_message,
                level="Low",
                alert_type=AlertType.spend_reports,
                alerting_metadata={},
            )

            await self.internal_usage_cache.async_set_cache(
                key=_event_cache_key,
                value="SENT",
                ttl=(30 * HOURS_IN_A_DAY * 60 * 60),  # 1 month
            )

        except Exception as e:
            verbose_proxy_logger.exception("Error sending weekly spend report %s", e)

    async def send_fallback_stats_from_prometheus(self):
        """
        Helper to send fallback statistics from prometheus server -> to slack

        This runs once per day and sends an overview of all the fallback statistics
        """
        try:
            from litellm.integrations.prometheus_helpers.prometheus_api import (
                get_fallback_metric_from_prometheus,
            )

            # call prometheuslogger.
            falllback_success_info_prometheus = (
                await get_fallback_metric_from_prometheus()
            )

            fallback_message = (
                f"*Fallback Statistics:*\n{falllback_success_info_prometheus}"
            )

            await self.send_alert(
                message=fallback_message,
                level="Low",
                alert_type=AlertType.fallback_reports,
                alerting_metadata={},
            )

        except Exception as e:
            verbose_proxy_logger.error("Error sending weekly spend report %s", e)

        pass

    async def send_virtual_key_event_slack(
        self,
        key_event: VirtualKeyEvent,
        alert_type: AlertType,
        event_name: str,
    ):
        """
        Handles sending Virtual Key related alerts

        Example:
        - New Virtual Key Created
        - Internal User Updated
        - Team Created, Updated, Deleted
        """
        try:
            message = f"`{event_name}`\n"

            key_event_dict = key_event.model_dump()

            # Add Created by information first
            message += "*Action Done by:*\n"
            for key, value in key_event_dict.items():
                if "created_by" in key:
                    message += f"{key}: `{value}`\n"

            # Add args sent to function in the alert
            message += "\n*Arguments passed:*\n"
            request_kwargs = key_event.request_kwargs
            for key, value in request_kwargs.items():
                if key == "user_api_key_dict":
                    continue
                message += f"{key}: `{value}`\n"

            await self.send_alert(
                message=message,
                level="High",
                alert_type=alert_type,
                alerting_metadata={},
            )

        except Exception as e:
            verbose_proxy_logger.error(
                "Error sending send_virtual_key_event_slack %s", e
            )

        return

    async def _request_is_completed(self, request_data: Optional[dict]) -> bool:
        """
        Returns True if the request is completed - either as a success or failure
        """
        if request_data is None:
            return False

        if (
            request_data.get("litellm_status", "") != "success"
            and request_data.get("litellm_status", "") != "fail"
        ):
            ## CHECK IF CACHE IS UPDATED
            litellm_call_id = request_data.get("litellm_call_id", "")
            status: Optional[str] = await self.internal_usage_cache.async_get_cache(
                key="request_status:{}".format(litellm_call_id), local_only=True
            )
            if status is not None and (status == "success" or status == "fail"):
                return True
        return False

# === NexusCore/openenv\Lib\site-packages\trio_websocket\_impl.py ===
from __future__ import annotations

import sys
from collections import OrderedDict
from contextlib import asynccontextmanager, AbstractAsyncContextManager
from functools import partial
from ipaddress import ip_address
import itertools
import logging
import random
import ssl
import struct
import urllib.parse
from typing import Any, List, NoReturn, Optional, Union, TypeVar, TYPE_CHECKING, Generic, cast
from importlib.metadata import version

import outcome
import trio
import trio.abc
from wsproto import ConnectionType, WSConnection
from wsproto.connection import ConnectionState
import wsproto.frame_protocol as wsframeproto
from wsproto.events import (
    AcceptConnection,
    BytesMessage,
    CloseConnection,
    Ping,
    Pong,
    RejectConnection,
    RejectData,
    Request,
    TextMessage,
)
import wsproto.utilities

if sys.version_info < (3, 11):  # pragma: no cover
    # pylint doesn't care about the version_info check, so need to ignore the warning
    from exceptiongroup import BaseExceptionGroup  # pylint: disable=redefined-builtin

if TYPE_CHECKING:
    from types import TracebackType
    from typing_extensions import Final
    from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable, Coroutine, Sequence

_IS_TRIO_MULTI_ERROR: Final = tuple(map(int, version("trio").split(".")[:2])) < (0, 22)

if _IS_TRIO_MULTI_ERROR:
    _TRIO_EXC_GROUP_TYPE = trio.MultiError  # type: ignore[attr-defined] # pylint: disable=no-member
else:
    _TRIO_EXC_GROUP_TYPE = BaseExceptionGroup  # pylint: disable=possibly-used-before-assignment

CONN_TIMEOUT: Final = 60 # default connect & disconnect timeout, in seconds
MESSAGE_QUEUE_SIZE: Final = 1
MAX_MESSAGE_SIZE: Final = 2 ** 20 # 1 MiB
RECEIVE_BYTES: Final = 4 * 2 ** 10 # 4 KiB
logger: Final = logging.getLogger('trio-websocket')

T = TypeVar("T")
E = TypeVar("E", bound=BaseException)


class TrioWebsocketInternalError(Exception):
    """Raised as a fallback when open_websocket is unable to unwind an exceptiongroup
    into a single preferred exception. This should never happen, if it does then
    underlying assumptions about the internal code are incorrect.
    """


def _ignore_cancel(exc: E) -> E | None:
    return None if isinstance(exc, trio.Cancelled) else exc


class _preserve_current_exception:
    """A context manager which should surround an ``__exit__`` or
    ``__aexit__`` handler or the contents of a ``finally:``
    block. It ensures that any exception that was being handled
    upon entry is not masked by a `trio.Cancelled` raised within
    the body of the context manager.

    https://github.com/python-trio/trio/issues/1559
    https://gitter.im/python-trio/general?at=5faf2293d37a1a13d6a582cf
    """
    __slots__ = ("_armed",)

    def __init__(self) -> None:
        self._armed = False

    def __enter__(self) -> None:
        self._armed = sys.exc_info()[1] is not None

    def __exit__(
        self,
        ty: type[BaseException] | None,
        value: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if value is None or not self._armed:
            return False

        if _IS_TRIO_MULTI_ERROR:  # pragma: no cover
            filtered_exception = trio.MultiError.filter(_ignore_cancel, value)  # type: ignore[attr-defined]  # pylint: disable=no-member
        elif isinstance(value, BaseExceptionGroup):  # pylint: disable=possibly-used-before-assignment
            filtered_exception = value.subgroup(lambda exc: not isinstance(exc, trio.Cancelled))
        else:
            filtered_exception = _ignore_cancel(value)
        return filtered_exception is None


@asynccontextmanager
async def open_websocket(
    host: str,
    port: int,
    resource: str,
    *,
    use_ssl: Union[bool, ssl.SSLContext],
    subprotocols: Optional[Iterable[str]] = None,
    extra_headers: Optional[list[tuple[bytes,bytes]]] = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
    connect_timeout: float = CONN_TIMEOUT,
    disconnect_timeout: float = CONN_TIMEOUT
) -> AsyncGenerator[WebSocketConnection, None]:
    '''
    Open a WebSocket client connection to a host.

    This async context manager connects when entering the context manager and
    disconnects when exiting. It yields a
    :class:`WebSocketConnection` instance.

    :param str host: The host to connect to.
    :param int port: The port to connect to.
    :param str resource: The resource, i.e. URL path.
    :param Union[bool, ssl.SSLContext] use_ssl: If this is an SSL context, then
        use that context. If this is ``True`` then use default SSL context. If
        this is ``False`` then disable SSL.
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :param float connect_timeout: The number of seconds to wait for the
        connection before timing out.
    :param float disconnect_timeout: The number of seconds to wait when closing
        the connection before timing out.
    :raises HandshakeError: for any networking error,
        client-side timeout (:exc:`ConnectionTimeout`, :exc:`DisconnectionTimeout`),
        or server rejection (:exc:`ConnectionRejected`) during handshakes.
    '''

    # This context manager tries very very hard not to raise an exceptiongroup
    # in order to be as transparent as possible for the end user.
    # In the trivial case, this means that if user code inside the cm raises
    # we make sure that it doesn't get wrapped.

    # If opening the connection fails, then we will raise that exception. User
    # code is never executed, so we will never have multiple exceptions.

    # After opening the connection, we spawn _reader_task in the background and
    # yield to user code. If only one of those raise a non-cancelled exception
    # we will raise that non-cancelled exception.
    # If we get multiple cancelled, we raise the user's cancelled.
    # If both raise exceptions, we raise the user code's exception with __context__
    # set to a group containing internal exception(s) + any user exception __context__
    # If we somehow get multiple exceptions, but no user exception, then we raise
    # TrioWebsocketInternalError.

    # If closing the connection fails, then that will be raised as the top
    # exception in the last `finally`. If we encountered exceptions in user code
    # or in reader task then they will be set as the `__context__`.


    async def _open_connection(nursery: trio.Nursery) -> WebSocketConnection:
        try:
            with trio.fail_after(connect_timeout):
                return await connect_websocket(nursery, host, port,
                    resource, use_ssl=use_ssl, subprotocols=subprotocols,
                    extra_headers=extra_headers,
                    message_queue_size=message_queue_size,
                    max_message_size=max_message_size,
                    receive_buffer_size=receive_buffer_size)
        except trio.TooSlowError:
            raise ConnectionTimeout from None
        except OSError as e:
            raise HandshakeError from e

    async def _close_connection(connection: WebSocketConnection) -> None:
        try:
            with trio.fail_after(disconnect_timeout):
                await connection.aclose()
        except trio.TooSlowError:
            raise DisconnectionTimeout from None

    def _raise(exc: BaseException) -> NoReturn:
        """This helper allows re-raising an exception without __context__ being set."""
        # cause does not need special handlng, we simply avoid using `raise .. from ..`
        __tracebackhide__ = True
        context = exc.__context__
        try:
            raise exc
        finally:
            exc.__context__ = context
            del exc, context

    connection: WebSocketConnection|None=None
    close_result: outcome.Maybe[None] | None = None
    user_error = None

    # Unwrapping exception groups has a lot of pitfalls, one of them stemming from
    # the exception we raise also being inside the group that's set as the context.
    # This leads to loss of info unless properly handled.
    # See https://github.com/python-trio/flake8-async/issues/298
    # We therefore avoid having the exceptiongroup included as either cause or context

    try:
        async with trio.open_nursery() as new_nursery:
            result = await outcome.acapture(_open_connection, new_nursery)

            if isinstance(result, outcome.Value):
                connection = result.unwrap()
                try:
                    yield connection
                except BaseException as e:
                    user_error = e
                    raise
                finally:
                    close_result = await outcome.acapture(_close_connection, connection)
    # This exception handler should only be entered if either:
    # 1. The _reader_task started in connect_websocket raises
    # 2. User code raises an exception
    # I.e. open/close_connection are not included
    except _TRIO_EXC_GROUP_TYPE as e:
        # user_error, or exception bubbling up from _reader_task
        if len(e.exceptions) == 1:
            _raise(e.exceptions[0])

        # contains at most 1 non-cancelled exceptions
        exception_to_raise: BaseException|None = None
        for sub_exc in e.exceptions:
            if not isinstance(sub_exc, trio.Cancelled):
                if exception_to_raise is not None:
                    # multiple non-cancelled
                    break
                exception_to_raise = sub_exc
        else:
            if exception_to_raise is None:
                # all exceptions are cancelled
                # we reraise the user exception and throw out internal
                if user_error is not None:
                    _raise(user_error)
                # multiple internal Cancelled is not possible afaik
                # but if so we just raise one of them
                _raise(e.exceptions[0])  # pragma: no cover
            # raise the non-cancelled exception
            _raise(exception_to_raise)

        # if we have any KeyboardInterrupt in the group, raise a new KeyboardInterrupt
        # with the group as cause & context
        for sub_exc in e.exceptions:
            if isinstance(sub_exc, KeyboardInterrupt):
                raise KeyboardInterrupt from e

        # Both user code and internal code raised non-cancelled exceptions.
        # We set the context to be an exception group containing internal exceptions
        # and, if not None, `user_error.__context__`
        if user_error is not None:
            exceptions = [subexc for subexc in e.exceptions if subexc is not user_error]
            eg_substr = ''
            # there's technically loss of info here, with __suppress_context__=True you
            # still have original __context__ available, just not printed. But we delete
            # it completely because we can't partially suppress the group
            if user_error.__context__ is not None and not user_error.__suppress_context__:
                exceptions.append(user_error.__context__)
                eg_substr = ' and the context for the user exception'
            eg_str = (
                "Both internal and user exceptions encountered. This group contains "
                "the internal exception(s)" + eg_substr + "."
            )
            user_error.__context__ = BaseExceptionGroup(eg_str, exceptions)
            user_error.__suppress_context__ = False
            _raise(user_error)

        raise TrioWebsocketInternalError(
            "The trio-websocket API is not expected to raise multiple exceptions. "
            "Please report this as a bug to "
            "https://github.com/python-trio/trio-websocket"
        ) from e  # pragma: no cover

    finally:
        if close_result is not None:
            close_result.unwrap()


    # error setting up, unwrap that exception
    if connection is None:
        result.unwrap()


async def connect_websocket(
    nursery: trio.Nursery,
    host: str,
    port: int,
    resource: str,
    *,
    use_ssl: bool | ssl.SSLContext,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketConnection:
    '''
    Return an open WebSocket client connection to a host.

    This function is used to specify a custom nursery to run connection
    background tasks in. The caller is responsible for closing the connection.

    If you don't need a custom nursery, you should probably use
    :func:`open_websocket` instead.

    :param nursery: A Trio nursery to run background tasks in.
    :param str host: The host to connect to.
    :param int port: The port to connect to.
    :param str resource: The resource, i.e. URL path.
    :param Union[bool, ssl.SSLContext] use_ssl: If this is an SSL context, then
        use that context. If this is ``True`` then use default SSL context. If
        this is ``False`` then disable SSL.
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :rtype: WebSocketConnection
    '''
    if use_ssl is True:
        ssl_context = ssl.create_default_context()
    elif use_ssl is False:
        ssl_context = None
    elif isinstance(use_ssl, ssl.SSLContext):
        ssl_context = use_ssl
    else:
        raise TypeError('`use_ssl` argument must be bool or ssl.SSLContext')

    logger.debug('Connecting to ws%s://%s:%d%s',
        '' if ssl_context is None else 's', host, port, resource)
    stream: trio.SSLStream[trio.SocketStream] | trio.SocketStream
    if ssl_context is None:
        stream = await trio.open_tcp_stream(host, port)
    else:
        stream = await trio.open_ssl_over_tcp_stream(host, port,
            ssl_context=ssl_context, https_compatible=True)
    if port in (80, 443):
        host_header = host
    else:
        host_header = f'{host}:{port}'
    connection = WebSocketConnection(stream,
        WSConnection(ConnectionType.CLIENT),
        host=host_header,
        path=resource,
        client_subprotocols=subprotocols, client_extra_headers=extra_headers,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)
    nursery.start_soon(connection._reader_task)
    await connection._open_handshake.wait()
    return connection


def open_websocket_url(
    url: str,
    ssl_context: ssl.SSLContext | None = None,
    *,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    connect_timeout: float = CONN_TIMEOUT,
    disconnect_timeout: float = CONN_TIMEOUT,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> AbstractAsyncContextManager[WebSocketConnection]:
    '''
    Open a WebSocket client connection to a URL.

    This async context manager connects when entering the context manager and
    disconnects when exiting. It yields a
    :class:`WebSocketConnection` instance.

    :param str url: A WebSocket URL, i.e. `ws:` or `wss:` URL scheme.
    :param ssl_context: Optional SSL context used for ``wss:`` URLs. A default
        SSL context is used for ``wss:`` if this argument is ``None``.
    :type ssl_context: ssl.SSLContext or None
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :param float connect_timeout: The number of seconds to wait for the
        connection before timing out.
    :param float disconnect_timeout: The number of seconds to wait when closing
        the connection before timing out.
    :raises HandshakeError: for any networking error,
        client-side timeout (:exc:`ConnectionTimeout`, :exc:`DisconnectionTimeout`),
        or server rejection (:exc:`ConnectionRejected`) during handshakes.
    '''
    host, port, resource, return_ssl_context = _url_to_host(url, ssl_context)
    return open_websocket(host, port, resource, use_ssl=return_ssl_context,
        subprotocols=subprotocols, extra_headers=extra_headers,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size,
        connect_timeout=connect_timeout, disconnect_timeout=disconnect_timeout)


async def connect_websocket_url(
    nursery: trio.Nursery,
    url: str,
    ssl_context: ssl.SSLContext | None = None,
    *,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketConnection:
    '''
    Return an open WebSocket client connection to a URL.

    This function is used to specify a custom nursery to run connection
    background tasks in. The caller is responsible for closing the connection.

    If you don't need a custom nursery, you should probably use
    :func:`open_websocket_url` instead.

    :param nursery: A nursery to run background tasks in.
    :param str url: A WebSocket URL.
    :param ssl_context: Optional SSL context used for ``wss:`` URLs.
    :type ssl_context: ssl.SSLContext or None
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :rtype: WebSocketConnection
    '''
    host, port, resource, return_ssl_context = _url_to_host(url, ssl_context)
    return await connect_websocket(nursery, host, port, resource,
        use_ssl=return_ssl_context, subprotocols=subprotocols,
        extra_headers=extra_headers, message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)


def _url_to_host(
    url: str,
    ssl_context: ssl.SSLContext | None,
) -> tuple[str, int, str, ssl.SSLContext | bool]:
    '''
    Convert a WebSocket URL to a (host,port,resource) tuple.

    The returned ``ssl_context`` is either the same object that was passed in,
    or if ``ssl_context`` is None, then a bool indicating if a default SSL
    context needs to be created.

    :param str url: A WebSocket URL.
    :type ssl_context: ssl.SSLContext or None
    :returns: A tuple of ``(host, port, resource, ssl_context)``.
    '''
    url = str(url)  # For backward compat with isinstance(url, yarl.URL).
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ('ws', 'wss'):
        raise ValueError('WebSocket URL scheme must be "ws:" or "wss:"')
    return_ssl_context: ssl.SSLContext | bool
    if ssl_context is None:
        return_ssl_context = parts.scheme == 'wss'
    elif parts.scheme == 'ws':
        raise ValueError('SSL context must be None for ws: URL scheme')
    else:
        return_ssl_context = ssl_context
    host = parts.hostname
    if host is None:
        raise ValueError('URL host must not be None')
    if parts.port is not None:
        port = parts.port
    else:
        port = 443 if return_ssl_context else 80
    path_qs = parts.path
    # RFC 7230, Section 5.3.1:
    # If the target URI's path component is empty, the client MUST
    # send "/" as the path within the origin-form of request-target.
    if not path_qs:
        path_qs = '/'
    if '?' in url:
        path_qs += '?' + parts.query
    return host, port, path_qs, return_ssl_context


async def wrap_client_stream(
    nursery: trio.Nursery,
    stream: trio.SocketStream | trio.SSLStream[trio.SocketStream],
    host: str,
    resource: str,
    *,
    subprotocols: Iterable[str] | None = None,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketConnection:
    '''
    Wrap an arbitrary stream in a WebSocket connection.

    This is a low-level function only needed in rare cases. In most cases, you
    should use :func:`open_websocket` or :func:`open_websocket_url`.

    :param nursery: A Trio nursery to run background tasks in.
    :param stream: A Trio stream to be wrapped.
    :type stream: trio.abc.Stream
    :param str host: A host string that will be sent in the ``Host:`` header.
    :param str resource: A resource string, i.e. the path component to be
        accessed on the server.
    :param subprotocols: An iterable of strings representing preferred
        subprotocols.
    :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples containing
        HTTP header key/value pairs to send with the connection request. Note
        that headers used by the WebSocket protocol (e.g.
        ``Sec-WebSocket-Accept``) will be overwritten.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :rtype: WebSocketConnection
    '''
    connection = WebSocketConnection(stream,
        WSConnection(ConnectionType.CLIENT),
        host=host, path=resource,
        client_subprotocols=subprotocols, client_extra_headers=extra_headers,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)
    nursery.start_soon(connection._reader_task)
    await connection._open_handshake.wait()
    return connection


async def wrap_server_stream(
    nursery: trio.Nursery,
    stream: trio.abc.Stream,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
) -> WebSocketRequest:
    '''
    Wrap an arbitrary stream in a server-side WebSocket.

    This is a low-level function only needed in rare cases. In most cases, you
    should use :func:`serve_websocket`.

    :param nursery: A nursery to run background tasks in.
    :param stream: A stream to be wrapped.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :type stream: trio.abc.Stream
    :rtype: WebSocketRequest
    '''
    connection = WebSocketConnection(
        stream,
        WSConnection(ConnectionType.SERVER),
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size)
    nursery.start_soon(connection._reader_task)
    request = await connection._get_request()
    return request



async def serve_websocket(
    handler: Callable[[WebSocketRequest], Awaitable[None]],
    host: str | bytes | None,
    port: int,
    ssl_context: ssl.SSLContext | None,
    *,
    handler_nursery: trio.Nursery | None = None,
    message_queue_size: int = MESSAGE_QUEUE_SIZE,
    max_message_size: int = MAX_MESSAGE_SIZE,
    receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
    connect_timeout: float = CONN_TIMEOUT,
    disconnect_timeout: float = CONN_TIMEOUT,
    task_status: trio.TaskStatus[WebSocketServer] = trio.TASK_STATUS_IGNORED,
) -> NoReturn:
    """
    Serve a WebSocket over TCP.

    This function supports the Trio nursery start protocol: ``server = await
    nursery.start(serve_websocket, …)``. It will block until the server
    is accepting connections and then return a :class:`WebSocketServer` object.

    Note that if ``host`` is ``None`` and ``port`` is zero, then you may get
    multiple listeners that have *different port numbers!*

    :param handler: An async function that is invoked with a request
        for each new connection.
    :param host: The host interface to bind. This can be an address of an
        interface, a name that resolves to an interface address (e.g.
        ``localhost``), or a wildcard address like ``0.0.0.0`` for IPv4 or
        ``::`` for IPv6. If ``None``, then all local interfaces are bound.
    :type host: str, bytes, or None
    :param int port: The port to bind to.
    :param ssl_context: The SSL context to use for encrypted connections, or
        ``None`` for unencrypted connection.
    :type ssl_context: ssl.SSLContext or None
    :param handler_nursery: An optional nursery to spawn handlers and background
        tasks in. If not specified, a new nursery will be created internally.
    :param int message_queue_size: The maximum number of messages that will be
        buffered in the library's internal message queue.
    :param int max_message_size: The maximum message size as measured by
        ``len()``. If a message is received that is larger than this size,
        then the connection is closed with code 1009 (Message Too Big).
    :param Optional[int] receive_buffer_size: The buffer size we use to
        receive messages internally. None to let trio choose. Defaults
        to 4 KiB.
    :param float connect_timeout: The number of seconds to wait for a client
        to finish connection handshake before timing out.
    :param float disconnect_timeout: The number of seconds to wait for a client
        to finish the closing handshake before timing out.
    :param task_status: Part of Trio nursery start protocol.
    :returns: This function runs until cancelled.
    """
    open_tcp_listeners: (
        partial[Coroutine[Any, Any, list[trio.SocketListener]]]
        | partial[Coroutine[Any, Any, list[trio.SSLListener[trio.SocketStream]]]]
    )
    if ssl_context is None:
        open_tcp_listeners = partial(trio.open_tcp_listeners, port, host=host)
    else:
        open_tcp_listeners = partial(
            trio.open_ssl_over_tcp_listeners,
            port,
            ssl_context,
            host=host,
            https_compatible=True,
        )
    listeners = await open_tcp_listeners()
    server = WebSocketServer(
        handler,
        listeners,
        handler_nursery=handler_nursery,
        message_queue_size=message_queue_size,
        max_message_size=max_message_size,
        receive_buffer_size=receive_buffer_size,
        connect_timeout=connect_timeout,
        disconnect_timeout=disconnect_timeout,
    )
    await server.run(task_status=task_status)


class HandshakeError(Exception):
    '''
    There was an error during connection or disconnection with the websocket
    server.
    '''

class ConnectionTimeout(HandshakeError):
    '''There was a timeout when connecting to the websocket server.'''

class DisconnectionTimeout(HandshakeError):
    '''There was a timeout when disconnecting from the websocket server.'''

class ConnectionClosed(Exception):
    '''
    A WebSocket operation cannot be completed because the connection is closed
    or in the process of closing.
    '''
    def __init__(self, reason: CloseReason | None) -> None:
        '''
        Constructor.

        :param reason:
        :type reason: CloseReason
        '''
        super().__init__(reason)
        self.reason = reason

    def __repr__(self) -> str:
        ''' Return representation. '''
        return f'{self.__class__.__name__}<{self.reason}>'


class ConnectionRejected(HandshakeError):
    '''
    A WebSocket connection could not be established because the server rejected
    the connection attempt.
    '''
    def __init__(
        self,
        status_code: int,
        headers: tuple[tuple[bytes, bytes], ...],
        body: bytes | None,
    ) -> None:
        '''
        Constructor.

        :param reason:
        :type reason: CloseReason
        '''
        super().__init__(status_code, headers, body)
        #: a 3 digit HTTP status code
        self.status_code = status_code
        #: a tuple of 2-tuples containing header key/value pairs
        self.headers = headers
        #: an optional ``bytes`` response body
        self.body = body

    def __repr__(self) -> str:
        ''' Return representation. '''
        return f'{self.__class__.__name__}<status_code={self.status_code}>'


class CloseReason:
    ''' Contains information about why a WebSocket was closed. '''
    def __init__(self, code: int, reason: str | None) -> None:
        '''
        Constructor.

        :param int code:
        :param Optional[str] reason:
        '''
        self._code = code
        try:
            self._name = wsframeproto.CloseReason(code).name
        except ValueError:
            if 1000 <= code <= 2999:
                self._name = 'RFC_RESERVED'
            elif 3000 <= code <= 3999:
                self._name = 'IANA_RESERVED'
            elif 4000 <= code <= 4999:
                self._name = 'PRIVATE_RESERVED'
            else:
                self._name = 'INVALID_CODE'
        self._reason = reason

    @property
    def code(self) -> int:
        ''' (Read-only) The numeric close code. '''
        return self._code

    @property
    def name(self) -> str:
        ''' (Read-only) The human-readable close code. '''
        return self._name

    @property
    def reason(self) -> str | None:
        ''' (Read-only) An arbitrary reason string. '''
        return self._reason

    def __repr__(self) -> str:
        ''' Show close code, name, and reason. '''
        return f'{self.__class__.__name__}' \
               f'<code={self.code}, name={self.name}, reason={self.reason}>'


NULL: Final = object()


class Future(Generic[T]):
    ''' Represents a value that will be available in the future. '''
    def __init__(self) -> None:
        ''' Constructor. '''
        # We do some type shenanigins
        # Would do `T | Literal[NULL]` but that's not right apparently.
        self._value: T = cast(T, NULL)
        self._value_event = trio.Event()

    def set_value(self, value: T) -> None:
        '''
        Set a value, which will notify any waiters.

        :param value:
        '''
        self._value = value
        self._value_event.set()

    async def wait_value(self) -> T:
        '''
        Wait for this future to have a value, then return it.

        :returns: The value set by ``set_value()``.
        '''
        await self._value_event.wait()
        assert self._value is not NULL
        return self._value


class WebSocketRequest:
    '''
    Represents a handshake presented by a client to a server.

    The server may modify the handshake or leave it as is. The server should
    call ``accept()`` to finish the handshake and obtain a connection object.
    '''
    def __init__(
        self,
        connection: WebSocketConnection,
        event: wsproto.events.Request,
    ) -> None:
        '''
        Constructor.

        :param WebSocketConnection connection:
        :type event: wsproto.events.Request
        '''
        self._connection = connection
        self._event = event

    @property
    def headers(self) -> list[tuple[bytes, bytes]]:
        '''
        HTTP headers represented as a list of (name, value) pairs.

        :rtype: list[tuple]
        '''
        return self._event.extra_headers

    @property
    def path(self) -> str:
        '''
        The requested URL path.

        :rtype: str
        '''
        return self._event.target

    @property
    def proposed_subprotocols(self) -> tuple[str, ...]:
        '''
        A tuple of protocols proposed by the client.

        :rtype: tuple[str]
        '''
        return tuple(self._event.subprotocols)

    @property
    def local(self) -> Endpoint | str:
        '''
        The connection's local endpoint.

        :rtype: Endpoint or str
        '''
        return self._connection.local

    @property
    def remote(self) -> Endpoint | str:
        '''
        The connection's remote endpoint.

        :rtype: Endpoint or str
        '''
        return self._connection.remote

    async def accept(
        self,
        *,
        subprotocol: str | None = None,
        extra_headers: list[tuple[bytes, bytes]] | None = None,
    ) -> WebSocketConnection:
        '''
        Accept the request and return a connection object.

        :param subprotocol: The selected subprotocol for this connection.
        :type subprotocol: str or None
        :param extra_headers: A list of 2-tuples containing key/value pairs to
            send as HTTP headers.
        :type extra_headers: list[tuple[bytes,bytes]] or None
        :rtype: WebSocketConnection
        '''
        if extra_headers is None:
            extra_headers = []
        await self._connection._accept(self._event, subprotocol, extra_headers)
        return self._connection

    async def reject(
        self,
        status_code: int,
        *,
        extra_headers: list[tuple[bytes, bytes]] | None = None,
        body: bytes | None = None,
    ) -> None:
        '''
        Reject the handshake.

        :param int status_code: The 3 digit HTTP status code. In order to be
            RFC-compliant, this should NOT be 101, and would ideally be an
            appropriate code in the range 300-599.
        :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples
            containing key/value pairs to send as HTTP headers.
        :param body: If provided, this data will be sent in the response
            body, otherwise no response body will be sent.
        :type body: bytes or None
        '''
        extra_headers = extra_headers or []
        body = body or b''
        await self._connection._reject(status_code, extra_headers, body)


def _get_stream_endpoint(
    stream: trio.abc.Stream,
    *,
    local: bool,
) -> Endpoint | str:
    '''
    Construct an endpoint from a stream.

    :param trio.Stream stream:
    :param bool local: If true, return local endpoint. Otherwise return remote.
    :returns: An endpoint instance or ``repr()`` for streams that cannot be
        represented as an endpoint.
    :rtype: Endpoint or str
    '''
    socket, is_ssl = None, False
    if isinstance(stream, trio.SocketStream):
        socket = stream.socket
    elif isinstance(stream, trio.SSLStream):
        socket = stream.transport_stream.socket
        is_ssl = True
    endpoint: Endpoint | str
    if socket:
        addr, port, *_ = socket.getsockname() if local else socket.getpeername()
        endpoint = Endpoint(addr, port, is_ssl)
    else:
        endpoint = repr(stream)
    return endpoint


class WebSocketConnection(trio.abc.AsyncResource):
    ''' A WebSocket connection. '''

    CONNECTION_ID = itertools.count()

    def __init__(
        self,
        stream: trio.abc.Stream,
        ws_connection: wsproto.WSConnection,
        *,
        host: str | None = None,
        path: str | None = None,
        client_subprotocols: Iterable[str] | None = None,
        client_extra_headers: list[tuple[bytes, bytes]] | None = None,
        message_queue_size: int = MESSAGE_QUEUE_SIZE,
        max_message_size: int = MAX_MESSAGE_SIZE,
        receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
    ) -> None:
        '''
        Constructor.

        Generally speaking, users are discouraged from directly instantiating a
        ``WebSocketConnection`` and should instead use one of the convenience
        functions in this module, e.g. ``open_websocket()`` or
        ``serve_websocket()``. This class has some tricky internal logic and
        timing that depends on whether it is an instance of a client connection
        or a server connection. The convenience functions handle this complexity
        for you.

        :param SocketStream stream:
        :param ws_connection wsproto.WSConnection:
        :param str host: The hostname to send in the HTTP request headers. Only
            used for client connections.
        :param str path: The URL path for this connection.
        :param list client_subprotocols: A list of desired subprotocols. Only
            used for client connections.
        :param list[tuple[bytes,bytes]] client_extra_headers: Extra headers to
            send with the connection request. Only used for client connections.
        :param int message_queue_size: The maximum number of messages that will be
            buffered in the library's internal message queue.
        :param int max_message_size: The maximum message size as measured by
            ``len()``. If a message is received that is larger than this size,
            then the connection is closed with code 1009 (Message Too Big).
        :param Optional[int] receive_buffer_size: The buffer size we use to
            receive messages internally. None to let trio choose. Defaults
            to 4 KiB.
        '''
        # NOTE: The implementation uses _close_reason for more than an advisory
        #   purpose.  It's critical internal state, indicating when the
        #   connection is closed or closing.
        self._close_reason: Optional[CloseReason] = None
        self._id = next(self.__class__.CONNECTION_ID)
        self._stream = stream
        self._stream_lock = trio.StrictFIFOLock()
        self._wsproto = ws_connection
        self._message_size = 0
        self._message_parts: List[Union[bytes, str]] = []
        self._max_message_size = max_message_size
        self._receive_buffer_size: Optional[int] = receive_buffer_size
        self._reader_running = True
        if ws_connection.client:
            assert host is not None
            assert path is not None
            self._initial_request: Optional[Request] = Request(host=host, target=path,
                subprotocols=list(client_subprotocols or ()),
                extra_headers=client_extra_headers or [])
        else:
            self._initial_request = None
        self._path = path
        self._subprotocol: Optional[str] = None
        self._handshake_headers: tuple[tuple[bytes, bytes], ...] = ()
        self._reject_status = 0
        self._reject_headers: tuple[tuple[bytes, bytes], ...] = ()
        self._reject_body = b''
        self._send_channel, self._recv_channel = trio.open_memory_channel[
            Union[bytes, str]
        ](message_queue_size)
        self._pings: OrderedDict[bytes, trio.Event] = OrderedDict()
        # Set when the server has received a connection request event. This
        # future is never set on client connections.
        self._connection_proposal: Future[WebSocketRequest] | None = Future[WebSocketRequest]()
        # Set once the WebSocket open handshake takes place, i.e.
        # ConnectionRequested for server or ConnectedEstablished for client.
        self._open_handshake = trio.Event()
        # Set once a WebSocket closed handshake takes place, i.e after a close
        # frame has been sent and a close frame has been received.
        self._close_handshake = trio.Event()
        # Set upon receiving CloseConnection from peer.
        # Used to test close race conditions between client and server.
        self._for_testing_peer_closed_connection = trio.Event()

    @property
    def closed(self) -> CloseReason | None:
        '''
        (Read-only) The reason why the connection was or is being closed,
        else ``None``.

        :rtype: Optional[CloseReason]
        '''
        return self._close_reason

    @property
    def is_client(self) -> bool:
        ''' (Read-only) Is this a client instance? '''
        return self._wsproto.client

    @property
    def is_server(self) -> bool:
        ''' (Read-only) Is this a server instance? '''
        return not self._wsproto.client

    @property
    def local(self) -> Endpoint | str:
        '''
        The local endpoint of the connection.

        :rtype: Endpoint or str
        '''
        return _get_stream_endpoint(self._stream, local=True)

    @property
    def remote(self) -> Endpoint | str:
        '''
        The remote endpoint of the connection.

        :rtype: Endpoint or str
        '''
        return _get_stream_endpoint(self._stream, local=False)

    @property
    def path(self) -> str | None:
        '''
        The requested URL path. For clients, this is set when the connection is
        instantiated. For servers, it is set after the handshake completes.

        :rtype: str or None
        '''
        return self._path

    @property
    def subprotocol(self) -> str | None:
        '''
        (Read-only) The negotiated subprotocol, or ``None`` if there is no
        subprotocol.

        This is only valid after the opening handshake is complete.

        :rtype: str or None
        '''
        return self._subprotocol

    @property
    def handshake_headers(self) -> tuple[tuple[bytes, bytes], ...]:
        '''
        The HTTP headers that were sent by the remote during the handshake,
        stored as 2-tuples containing key/value pairs. Header keys are always
        lower case.

        :rtype: tuple[tuple[str,str]]
        '''
        return self._handshake_headers

    async def aclose(self, code: int = 1000, reason: str | None = None) -> None:  # pylint: disable=arguments-differ
        '''
        Close the WebSocket connection.

        This sends a closing frame and suspends until the connection is closed.
        After calling this method, any further I/O on this WebSocket (such as
        ``get_message()`` or ``send_message()``) will raise
        ``ConnectionClosed``.

        This method is idempotent: it may be called multiple times on the same
        connection without any errors.

        :param int code: A 4-digit code number indicating the type of closure.
        :param str reason: An optional string describing the closure.
        '''
        with _preserve_current_exception():
            await self._aclose(code, reason)

    async def _aclose(self, code: int, reason: str | None) -> None:
        if self._close_reason:
            # Per AsyncResource interface, calling aclose() on a closed resource
            # should succeed.
            return
        try:
            if self._wsproto.state == ConnectionState.OPEN:
                # Our side is initiating the close, so send a close connection
                # event to peer, while setting the local close reason to normal.
                self._close_reason = CloseReason(1000, None)
                await self._send(CloseConnection(code=code, reason=reason))
            elif self._wsproto.state in (ConnectionState.CONNECTING,
                    ConnectionState.REJECTING):
                self._close_handshake.set()
            # TODO: shouldn't the receive channel be closed earlier, so that
            #  get_message() during send of the CloseConneciton event fails?
            await self._recv_channel.aclose()
            await self._close_handshake.wait()
        except ConnectionClosed:
            # If _send() raised ConnectionClosed, then we can bail out.
            pass
        finally:
            # If cancelled during WebSocket close, make sure that the underlying
            # stream is closed.
            await self._close_stream()

    async def get_message(self) -> str | bytes:
        '''
        Receive the next WebSocket message.

        If no message is available immediately, then this function blocks until
        a message is ready.

        If the remote endpoint closes the connection, then the caller can still
        get messages sent prior to closing. Once all pending messages have been
        retrieved, additional calls to this method will raise
        ``ConnectionClosed``. If the local endpoint closes the connection, then
        pending messages are discarded and calls to this method will immediately
        raise ``ConnectionClosed``.

        :rtype: str or bytes
        :raises ConnectionClosed: if the connection is closed.
        '''
        try:
            message = await self._recv_channel.receive()
        except (trio.ClosedResourceError, trio.EndOfChannel):
            raise ConnectionClosed(self._close_reason) from None
        return message

    async def ping(self, payload: bytes | None = None) -> None:
        '''
        Send WebSocket ping to remote endpoint and wait for a correspoding pong.

        Each in-flight ping must include a unique payload. This function sends
        the ping and then waits for a corresponding pong from the remote
        endpoint.

        *Note: If the remote endpoint recieves multiple pings, it is allowed to
        send a single pong. Therefore, the order of calls to ``ping()`` is
        tracked, and a pong will wake up its corresponding ping as well as all
        previous in-flight pings.*

        :param payload: The payload to send. If ``None`` then a random 32-bit
            payload is created.
        :type payload: bytes or None
        :raises ConnectionClosed: if connection is closed.
        :raises ValueError: if ``payload`` is identical to another in-flight
            ping.
        '''
        if self._close_reason:
            raise ConnectionClosed(self._close_reason)
        if payload in self._pings:
            raise ValueError(f'Payload value {payload!r} is already in flight.')
        if payload is None:
            payload = struct.pack('!I', random.getrandbits(32))
        event = trio.Event()
        self._pings[payload] = event
        await self._send(Ping(payload=payload))
        await event.wait()

    async def pong(self, payload: bytes | None = None) -> None:
        '''
        Send an unsolicted pong.

        :param payload: The pong's payload. If ``None``, then no payload is
            sent.
        :type payload: bytes or None
        :raises ConnectionClosed: if connection is closed
        '''
        if self._close_reason:
            raise ConnectionClosed(self._close_reason)
        await self._send(Pong(payload=payload or b''))

    async def send_message(self, message: str | bytes) -> None:
        '''
        Send a WebSocket message.

        :param message: The message to send.
        :type message: str or bytes
        :raises ConnectionClosed: if connection is closed, or being closed
        '''
        if self._close_reason:
            raise ConnectionClosed(self._close_reason)
        event: TextMessage | BytesMessage
        if isinstance(message, str):
            event = TextMessage(data=message)
        elif isinstance(message, bytes):
            event = BytesMessage(data=message)
        else:
            raise ValueError('message must be str or bytes')
        await self._send(event)

    def __str__(self) -> str:
        ''' Connection ID and type. '''
        type_ = 'client' if self.is_client else 'server'
        return f'{type_}-{self._id}'

    async def _accept(
        self,
        request: Request,
        subprotocol: str | None,
        extra_headers: list[tuple[bytes, bytes]],
    ) -> None:
        '''
        Accept the handshake.

        This method is only applicable to server-side connections.

        :param wsproto.events.Request request:
        :param subprotocol:
        :type subprotocol: str or None
        :param list[tuple[bytes,bytes]] extra_headers: A list of 2-tuples
            containing key/value pairs to send as HTTP headers.
        '''
        self._subprotocol = subprotocol
        self._path = request.target
        await self._send(AcceptConnection(subprotocol=self._subprotocol,
            extra_headers=extra_headers))
        self._open_handshake.set()

    async def _reject(
        self,
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        '''
        Reject the handshake.

        :param int status_code: The 3 digit HTTP status code. In order to be
            RFC-compliant, this must not be 101, and should be an appropriate
            code in the range 300-599.
        :param list[tuple[bytes,bytes]] headers: A list of 2-tuples containing
            key/value pairs to send as HTTP headers.
        :param bytes body: An optional response body.
        '''
        if body:
            headers.append((b'Content-length', str(len(body)).encode('ascii')))
        reject_conn = RejectConnection(status_code=status_code, headers=headers,
            has_body=bool(body))
        await self._send(reject_conn)
        if body:
            reject_body = RejectData(data=body)
            await self._send(reject_body)
        self._close_reason = CloseReason(1006, 'Rejected WebSocket handshake')
        self._close_handshake.set()

    async def _abort_web_socket(self) -> None:
        '''
        If a stream is closed outside of this class, e.g. due to network
        conditions or because some other code closed our stream object, then we
        cannot perform the close handshake. We just need to clean up internal
        state.
        '''
        close_reason = wsframeproto.CloseReason.ABNORMAL_CLOSURE
        if self._wsproto.state == ConnectionState.OPEN:
            self._wsproto.send(CloseConnection(code=close_reason.value))
        if self._close_reason is None:
            await self._close_web_socket(close_reason)
        self._reader_running = False
        # We didn't really handshake, but we want any task waiting on this event
        # (e.g. self.aclose()) to resume.
        self._close_handshake.set()

    async def _close_stream(self) -> None:
        ''' Close the TCP connection. '''
        self._reader_running = False
        try:
            with _preserve_current_exception():
                await self._stream.aclose()
        except trio.BrokenResourceError:
            # This means the TCP connection is already dead.
            pass

    async def _close_web_socket(self, code: int, reason: str | None = None) -> None:
        '''
        Mark the WebSocket as closed. Close the message channel so that if any
        tasks are suspended in get_message(), they will wake up with a
        ConnectionClosed exception.
        '''
        self._close_reason = CloseReason(code, reason)
        exc = ConnectionClosed(self._close_reason)
        logger.debug('%s websocket closed %r', self, exc)
        await self._send_channel.aclose()

    async def _get_request(self) -> WebSocketRequest:
        '''
        Return a proposal for a WebSocket handshake.

        This method can only be called on server connections and it may only be
        called one time.

        :rtype: WebSocketRequest
        '''
        if not self.is_server:
            raise RuntimeError('This method is only valid for server connections.')
        if self._connection_proposal is None:
            raise RuntimeError('No proposal available. Did you call this method'
                ' multiple times or at the wrong time?')
        proposal = await self._connection_proposal.wait_value()
        self._connection_proposal = None
        return proposal

    async def _handle_request_event(self, event: wsproto.events.Request) -> None:
        '''
        Handle a connection request.

        This method is async even though it never awaits, because the event
        dispatch requires an async function.

        :param event:
        '''
        proposal = WebSocketRequest(self, event)
        assert self._connection_proposal is not None
        self._connection_proposal.set_value(proposal)

    async def _handle_accept_connection_event(self, event: wsproto.events.AcceptConnection) -> None:
        '''
        Handle an AcceptConnection event.

        :param wsproto.eventsAcceptConnection event:
        '''
        self._subprotocol = event.subprotocol
        self._handshake_headers = tuple(event.extra_headers)
        self._open_handshake.set()

    async def _handle_reject_connection_event(self, event: wsproto.events.RejectConnection) -> None:
        '''
        Handle a RejectConnection event.

        :param event:
        '''
        self._reject_status = event.status_code
        self._reject_headers = tuple(event.headers)
        if not event.has_body:
            raise ConnectionRejected(self._reject_status, self._reject_headers,
                body=None)

    async def _handle_reject_data_event(self, event: wsproto.events.RejectData) -> None:
        '''
        Handle a RejectData event.

        :param event:
        '''
        self._reject_body += event.data
        if event.body_finished:
            raise ConnectionRejected(self._reject_status, self._reject_headers,
                body=self._reject_body)

    async def _handle_close_connection_event(self, event: wsproto.events.CloseConnection) -> None:
        '''
        Handle a close event.

        :param wsproto.events.CloseConnection event:
        '''
        if self._wsproto.state == ConnectionState.REMOTE_CLOSING:
            # Set _close_reason in advance, so that send_message() will raise
            # ConnectionClosed during the close handshake.
            self._close_reason = CloseReason(event.code, event.reason or None)
            self._for_testing_peer_closed_connection.set()
            await self._send(event.response())
        await self._close_web_socket(event.code, event.reason or None)
        self._close_handshake.set()
        # RFC: "When a server is instructed to Close the WebSocket Connection
        #   it SHOULD initiate a TCP Close immediately, and when a client is
        #   instructed to do the same, it SHOULD wait for a TCP Close from the
        #   server."
        if self.is_server:
            await self._close_stream()

    async def _handle_message_event(
        self,
        event: wsproto.events.BytesMessage | wsproto.events.TextMessage,
    ) -> None:
        '''
        Handle a message event.

        :param event:
        :type event: wsproto.events.BytesMessage or wsproto.events.TextMessage
        '''
        self._message_size += len(event.data)
        self._message_parts.append(event.data)
        if self._message_size > self._max_message_size:
            err = f'Exceeded maximum message size: {self._max_message_size} bytes'
            self._message_size = 0
            self._message_parts = []
            self._close_reason = CloseReason(1009, err)
            await self._send(CloseConnection(code=1009, reason=err))
            await self._recv_channel.aclose()
            self._reader_running = False
        elif event.message_finished:
            msg: str | bytes
            # Type checker does not understand `_message_parts`
            if isinstance(event, BytesMessage):
                msg = b''.join(cast("list[bytes]", self._message_parts))
            else:
                msg = ''.join(cast("list[str]", self._message_parts))
            self._message_size = 0
            self._message_parts = []
            try:
                await self._send_channel.send(msg)
            except (trio.ClosedResourceError, trio.BrokenResourceError):
                # The receive channel is closed, probably because somebody
                # called ``aclose()``. We don't want to abort the reader task,
                # and there's no useful cleanup that we can do here.
                pass

    async def _handle_ping_event(self, event: wsproto.events.Ping) -> None:
        '''
        Handle a PingReceived event.

        Wsproto queues a pong frame automatically, so this handler just needs to
        send it.

        :param wsproto.events.Ping event:
        '''
        logger.debug('%s ping %r', self, event.payload)
        await self._send(event.response())

    async def _handle_pong_event(self, event: wsproto.events.Pong) -> None:
        '''
        Handle a PongReceived event.

        When a pong is received, check if we have any ping requests waiting for
        this pong response. If the remote endpoint skipped any earlier pings,
        then we wake up those skipped pings, too.

        This function is async even though it never awaits, because the other
        event handlers are async, too, and event dispatch would be more
        complicated if some handlers were sync.

        :param event:
        '''
        payload = bytes(event.payload)
        try:
            ping_event = self._pings[payload]
        except KeyError:
            # We received a pong that doesn't match any in-flight pongs. Nothing
            # we can do with it, so ignore it.
            return
        while self._pings:
            key, ping_event = self._pings.popitem(False)
            skipped = ' [skipped] ' if payload != key else ' '
            logger.debug('%s pong%s%r', self, skipped, key)
            ping_event.set()
            if payload == key:
                break

    async def _reader_task(self) -> None:
        ''' A background task that reads network data and generates events. '''
        handlers = {
            AcceptConnection: self._handle_accept_connection_event,
            BytesMessage: self._handle_message_event,
            CloseConnection: self._handle_close_connection_event,
            Ping: self._handle_ping_event,
            Pong: self._handle_pong_event,
            RejectConnection: self._handle_reject_connection_event,
            RejectData: self._handle_reject_data_event,
            Request: self._handle_request_event,
            TextMessage: self._handle_message_event,
        }

        # Clients need to initiate the opening handshake.
        if self._initial_request:
            try:
                await self._send(self._initial_request)
            except ConnectionClosed:
                self._reader_running = False

        async with self._send_channel:
            while self._reader_running:
                # Process events.
                for event in self._wsproto.events():
                    event_type = type(event)
                    try:
                        handler = handlers[event_type]
                        logger.debug('%s received event: %s', self,
                            event_type)
                        # Type checkers don't understand looking up type in handlers.
                        # If we wanted to fix, best I can figure is we'd need a huge
                        # if-else or case block for every type individually.
                        await handler(event)  # type: ignore[operator]
                    except KeyError:
                        logger.warning('%s received unknown event type: "%s"', self,
                            event_type)
                    except ConnectionClosed:
                        self._reader_running = False
                        break

                # Get network data.
                try:
                    data = await self._stream.receive_some(self._receive_buffer_size)
                except (trio.BrokenResourceError, trio.ClosedResourceError):
                    await self._abort_web_socket()
                    break
                if len(data) == 0:
                    logger.debug('%s received zero bytes (connection closed)',
                        self)
                    # If TCP closed before WebSocket, then record it as an abnormal
                    # closure.
                    if self._wsproto.state != ConnectionState.CLOSED:
                        await self._abort_web_socket()
                    break
                logger.debug('%s received %d bytes', self, len(data))
                if self._wsproto.state != ConnectionState.CLOSED:
                    try:
                        self._wsproto.receive_data(data)
                    except wsproto.utilities.RemoteProtocolError as err:
                        logger.debug('%s remote protocol error: %s', self, err)
                        if err.event_hint:
                            await self._send(err.event_hint)
                        await self._close_stream()

        logger.debug('%s reader task finished', self)

    async def _send(self, event: wsproto.events.Event) -> None:
        '''
        Send an event to the remote WebSocket.

        The reader task and one or more writers might try to send messages at
        the same time, so this method uses an internal lock to serialize
        requests to send data.

        :param wsproto.events.Event event:
        '''
        data = self._wsproto.send(event)
        async with self._stream_lock:
            logger.debug('%s sending %d bytes', self, len(data))
            try:
                await self._stream.send_all(data)
            except (trio.BrokenResourceError, trio.ClosedResourceError):
                await self._abort_web_socket()
                assert self._close_reason is not None
                raise ConnectionClosed(self._close_reason) from None


class Endpoint:
    ''' Represents a connection endpoint. '''
    def __init__(self, address: str | int, port: int, is_ssl: bool) -> None:
        #: IP address :class:`ipaddress.ip_address`
        self.address = ip_address(address)
        #: TCP port
        self.port = port
        #: Whether SSL is in use
        self.is_ssl = is_ssl

    @property
    def url(self) -> str:
        ''' Return a URL representation of a TCP endpoint, e.g.
        ``ws://127.0.0.1:80``. '''
        scheme = 'wss' if self.is_ssl else 'ws'
        if (self.port == 80 and not self.is_ssl) or \
           (self.port == 443 and self.is_ssl):
            port_str = ''
        else:
            port_str = ':' + str(self.port)
        if self.address.version == 4:
            return f'{scheme}://{self.address}{port_str}'
        return f'{scheme}://[{self.address}]{port_str}'

    def __repr__(self) -> str:
        ''' Return endpoint info as string. '''
        return f'Endpoint(address="{self.address}", port={self.port}, is_ssl={self.is_ssl})'


class WebSocketServer:
    '''
    WebSocket server.

    The server class handles incoming connections on one or more ``Listener``
    objects. For each incoming connection, it creates a ``WebSocketConnection``
    instance and starts some background tasks,
    '''

    def __init__(
        self,
        handler: Callable[[WebSocketRequest], Awaitable[None]],
        listeners: Sequence[trio.SSLListener[trio.SocketStream] | trio.SocketListener],
        *,
        handler_nursery: trio.Nursery | None = None,
        message_queue_size: int = MESSAGE_QUEUE_SIZE,
        max_message_size: int = MAX_MESSAGE_SIZE,
        receive_buffer_size: Union[None, int] = RECEIVE_BYTES,
        connect_timeout: float = CONN_TIMEOUT,
        disconnect_timeout: float = CONN_TIMEOUT,
    ) -> None:
        '''
        Constructor.

        Note that if ``host`` is ``None`` and ``port`` is zero, then you may get
        multiple listeners that have _different port numbers!_ See the
        ``listeners`` property.

        :param handler: the async function called with a :class:`WebSocketRequest`
            on each new connection.  The call will be made
            once the HTTP handshake completes, which notably implies that the
            connection's `path` property will be valid.
        :param listeners: The WebSocket will be served on each of the listeners.
        :param handler_nursery: An optional nursery to spawn connection tasks
            inside of. If ``None``, then a new nursery will be created
            internally.
        :param Optional[int] receive_buffer_size: The buffer size we use to
            receive messages internally. None to let trio choose. Defaults
            to 4 KiB.
        :param float connect_timeout: The number of seconds to wait for a client
            to finish connection handshake before timing out.
        :param float disconnect_timeout: The number of seconds to wait for a client
            to finish the closing handshake before timing out.
        '''
        if len(listeners) == 0:
            raise ValueError('Listeners must contain at least one item.')
        self._handler = handler
        self._handler_nursery = handler_nursery
        self._listeners = listeners
        self._message_queue_size = message_queue_size
        self._max_message_size = max_message_size
        self._receive_buffer_size = receive_buffer_size
        self._connect_timeout = connect_timeout
        self._disconnect_timeout = disconnect_timeout

    @property
    def port(self) -> int:
        """Returns the requested or kernel-assigned port number.

        In the case of kernel-assigned port (requested with port=0 in the
        constructor), the assigned port will be reflected after calling
        starting the `listen` task.  (Technically, once listen reaches the
        "started" state.)

        This property only works if you have a single listener, and that
        listener must be socket-based.
        """
        if len(self._listeners) > 1:
            raise RuntimeError('Cannot get port because this server has'
                ' more than 1 listener.')
        listener = self.listeners[0]
        try:
            return listener.port  # type: ignore[union-attr]
        except AttributeError:
            raise RuntimeError(f'This socket does not have a port: {repr(listener)}') from None

    @property
    def listeners(self) -> list[Endpoint | str]:
        '''
        Return a list of listener metadata. Each TCP listener is represented as
        an ``Endpoint`` instance. Other listener types are represented by their
        ``repr()``.

        :returns: Listeners
        :rtype list[Endpoint or str]:
        '''
        listeners: list[Endpoint | str] = []
        for listener in self._listeners:
            socket, is_ssl = None, False
            if isinstance(listener, trio.SocketListener):
                socket = listener.socket
            elif isinstance(listener, trio.SSLListener):
                internal_listener = listener.transport_listener
                assert isinstance(internal_listener, trio.SocketListener)
                socket = internal_listener.socket
                is_ssl = True
            if socket:
                sockname = socket.getsockname()
                listeners.append(Endpoint(sockname[0], sockname[1], is_ssl))
            else:
                listeners.append(repr(listener))
        return listeners

    # Type ignore is because type checker does not think NoReturn is
    # real for Trio 0.25.1 (current version used in requirements file as
    # of writing). Not a problem for newer versions however, which is
    # why we have unused-ignore as well.
    async def run(  # type: ignore[misc,unused-ignore]
        self,
        *,
        task_status: trio.TaskStatus[WebSocketServer] = trio.TASK_STATUS_IGNORED,
    ) -> NoReturn:
        '''
        Start serving incoming connections requests.

        This method supports the Trio nursery start protocol: ``server = await
        nursery.start(server.run, …)``. It will block until the server is
        accepting connections and then return a :class:`WebSocketServer` object.

        :param task_status: Part of the Trio nursery start protocol.
        :returns: This method never returns unless cancelled.
        '''
        async with trio.open_nursery() as nursery:
            serve_listeners = partial(trio.serve_listeners,
                self._handle_connection, list(self._listeners),
                handler_nursery=self._handler_nursery)
            await nursery.start(serve_listeners)
            logger.debug('Listening on %s',
                ','.join([str(l) for l in self.listeners]))
            task_status.started(self)
            await trio.sleep_forever()

    async def _handle_connection(self, stream: trio.abc.Stream) -> None:
        '''
        Handle an incoming connection by spawning a connection background task
        and a handler task inside a new nursery.

        :param stream:
        :type stream: trio.abc.Stream
        '''
        async with trio.open_nursery() as nursery:
            connection = WebSocketConnection(stream,
                WSConnection(ConnectionType.SERVER),
                message_queue_size=self._message_queue_size,
                max_message_size=self._max_message_size,
                receive_buffer_size=self._receive_buffer_size)
            nursery.start_soon(connection._reader_task)
            with trio.move_on_after(self._connect_timeout) as connect_scope:
                request = await connection._get_request()
            if connect_scope.cancelled_caught:
                nursery.cancel_scope.cancel()
                await stream.aclose()
                return
            try:
                await self._handler(request)
            finally:
                with trio.move_on_after(self._disconnect_timeout):
                    # aclose() will shut down the reader task even if it's
                    # cancelled:
                    await connection.aclose()

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\file_download.py ===
import copy
import errno
import inspect
import os
import re
import shutil
import stat
import time
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Dict, Literal, NoReturn, Optional, Tuple, Union
from urllib.parse import quote, urlparse

import requests

from . import (
    __version__,  # noqa: F401 # for backward compatibility
    constants,
)
from ._local_folder import get_local_download_paths, read_download_metadata, write_download_metadata
from .constants import (
    HUGGINGFACE_CO_URL_TEMPLATE,  # noqa: F401 # for backward compatibility
    HUGGINGFACE_HUB_CACHE,  # noqa: F401 # for backward compatibility
)
from .errors import (
    EntryNotFoundError,
    FileMetadataError,
    GatedRepoError,
    HfHubHTTPError,
    LocalEntryNotFoundError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)
from .utils import (
    OfflineModeIsEnabled,
    SoftTemporaryDirectory,
    WeakFileLock,
    XetFileData,
    build_hf_headers,
    get_fastai_version,  # noqa: F401 # for backward compatibility
    get_fastcore_version,  # noqa: F401 # for backward compatibility
    get_graphviz_version,  # noqa: F401 # for backward compatibility
    get_jinja_version,  # noqa: F401 # for backward compatibility
    get_pydot_version,  # noqa: F401 # for backward compatibility
    get_tf_version,  # noqa: F401 # for backward compatibility
    get_torch_version,  # noqa: F401 # for backward compatibility
    hf_raise_for_status,
    is_fastai_available,  # noqa: F401 # for backward compatibility
    is_fastcore_available,  # noqa: F401 # for backward compatibility
    is_graphviz_available,  # noqa: F401 # for backward compatibility
    is_jinja_available,  # noqa: F401 # for backward compatibility
    is_pydot_available,  # noqa: F401 # for backward compatibility
    is_tf_available,  # noqa: F401 # for backward compatibility
    is_torch_available,  # noqa: F401 # for backward compatibility
    logging,
    parse_xet_file_data_from_response,
    refresh_xet_connection_info,
    reset_sessions,
    tqdm,
    validate_hf_hub_args,
)
from .utils._http import _adjust_range_header, http_backoff
from .utils._runtime import _PY_VERSION, is_xet_available  # noqa: F401 # for backward compatibility
from .utils._typing import HTTP_METHOD_T
from .utils.sha import sha_fileobj
from .utils.tqdm import _get_progress_bar_context


logger = logging.get_logger(__name__)

# Return value when trying to load a file from cache but the file does not exist in the distant repo.
_CACHED_NO_EXIST = object()
_CACHED_NO_EXIST_T = Any

# Regex to get filename from a "Content-Disposition" header for CDN-served files
HEADER_FILENAME_PATTERN = re.compile(r'filename="(?P<filename>.*?)";')

# Regex to check if the revision IS directly a commit_hash
REGEX_COMMIT_HASH = re.compile(r"^[0-9a-f]{40}$")

# Regex to check if the file etag IS a valid sha256
REGEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_are_symlinks_supported_in_dir: Dict[str, bool] = {}


def are_symlinks_supported(cache_dir: Union[str, Path, None] = None) -> bool:
    """Return whether the symlinks are supported on the machine.

    Since symlinks support can change depending on the mounted disk, we need to check
    on the precise cache folder. By default, the default HF cache directory is checked.

    Args:
        cache_dir (`str`, `Path`, *optional*):
            Path to the folder where cached files are stored.

    Returns: [bool] Whether symlinks are supported in the directory.
    """
    # Defaults to HF cache
    if cache_dir is None:
        cache_dir = constants.HF_HUB_CACHE
    cache_dir = str(Path(cache_dir).expanduser().resolve())  # make it unique

    # Check symlink compatibility only once (per cache directory) at first time use
    if cache_dir not in _are_symlinks_supported_in_dir:
        _are_symlinks_supported_in_dir[cache_dir] = True

        os.makedirs(cache_dir, exist_ok=True)
        with SoftTemporaryDirectory(dir=cache_dir) as tmpdir:
            src_path = Path(tmpdir) / "dummy_file_src"
            src_path.touch()
            dst_path = Path(tmpdir) / "dummy_file_dst"

            # Relative source path as in `_create_symlink``
            relative_src = os.path.relpath(src_path, start=os.path.dirname(dst_path))
            try:
                os.symlink(relative_src, dst_path)
            except OSError:
                # Likely running on Windows
                _are_symlinks_supported_in_dir[cache_dir] = False

                if not constants.HF_HUB_DISABLE_SYMLINKS_WARNING:
                    message = (
                        "`huggingface_hub` cache-system uses symlinks by default to"
                        " efficiently store duplicated files but your machine does not"
                        f" support them in {cache_dir}. Caching files will still work"
                        " but in a degraded version that might require more space on"
                        " your disk. This warning can be disabled by setting the"
                        " `HF_HUB_DISABLE_SYMLINKS_WARNING` environment variable. For"
                        " more details, see"
                        " https://huggingface.co/docs/huggingface_hub/how-to-cache#limitations."
                    )
                    if os.name == "nt":
                        message += (
                            "\nTo support symlinks on Windows, you either need to"
                            " activate Developer Mode or to run Python as an"
                            " administrator. In order to activate developer mode,"
                            " see this article:"
                            " https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development"
                        )
                    warnings.warn(message)

    return _are_symlinks_supported_in_dir[cache_dir]


@dataclass(frozen=True)
class HfFileMetadata:
    """Data structure containing information about a file versioned on the Hub.

    Returned by [`get_hf_file_metadata`] based on a URL.

    Args:
        commit_hash (`str`, *optional*):
            The commit_hash related to the file.
        etag (`str`, *optional*):
            Etag of the file on the server.
        location (`str`):
            Location where to download the file. Can be a Hub url or not (CDN).
        size (`size`):
            Size of the file. In case of an LFS file, contains the size of the actual
            LFS file, not the pointer.
        xet_file_data (`XetFileData`, *optional*):
            Xet information for the file. This is only set if the file is stored using Xet storage.
    """

    commit_hash: Optional[str]
    etag: Optional[str]
    location: str
    size: Optional[int]
    xet_file_data: Optional[XetFileData]


@validate_hf_hub_args
def hf_hub_url(
    repo_id: str,
    filename: str,
    *,
    subfolder: Optional[str] = None,
    repo_type: Optional[str] = None,
    revision: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> str:
    """Construct the URL of a file from the given information.

    The resolved address can either be a huggingface.co-hosted url, or a link to
    Cloudfront (a Content Delivery Network, or CDN) for large files which are
    more than a few MBs.

    Args:
        repo_id (`str`):
            A namespace (user or an organization) name and a repo name separated
            by a `/`.
        filename (`str`):
            The name of the file in the repo.
        subfolder (`str`, *optional*):
            An optional value corresponding to a folder inside the repo.
        repo_type (`str`, *optional*):
            Set to `"dataset"` or `"space"` if downloading from a dataset or space,
            `None` or `"model"` if downloading from a model. Default is `None`.
        revision (`str`, *optional*):
            An optional Git revision id which can be a branch name, a tag, or a
            commit hash.

    Example:

    ```python
    >>> from huggingface_hub import hf_hub_url

    >>> hf_hub_url(
    ...     repo_id="julien-c/EsperBERTo-small", filename="pytorch_model.bin"
    ... )
    'https://huggingface.co/julien-c/EsperBERTo-small/resolve/main/pytorch_model.bin'
    ```

    <Tip>

    Notes:

        Cloudfront is replicated over the globe so downloads are way faster for
        the end user (and it also lowers our bandwidth costs).

        Cloudfront aggressively caches files by default (default TTL is 24
        hours), however this is not an issue here because we implement a
        git-based versioning system on huggingface.co, which means that we store
        the files on S3/Cloudfront in a content-addressable way (i.e., the file
        name is its hash). Using content-addressable filenames means cache can't
        ever be stale.

        In terms of client-side caching from this library, we base our caching
        on the objects' entity tag (`ETag`), which is an identifier of a
        specific version of a resource [1]_. An object's ETag is: its git-sha1
        if stored in git, or its sha256 if stored in git-lfs.

    </Tip>

    References:

    -  [1] https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag
    """
    if subfolder == "":
        subfolder = None
    if subfolder is not None:
        filename = f"{subfolder}/{filename}"

    if repo_type not in constants.REPO_TYPES:
        raise ValueError("Invalid repo type")

    if repo_type in constants.REPO_TYPES_URL_PREFIXES:
        repo_id = constants.REPO_TYPES_URL_PREFIXES[repo_type] + repo_id

    if revision is None:
        revision = constants.DEFAULT_REVISION
    url = HUGGINGFACE_CO_URL_TEMPLATE.format(
        repo_id=repo_id, revision=quote(revision, safe=""), filename=quote(filename)
    )
    # Update endpoint if provided
    if endpoint is not None and url.startswith(constants.ENDPOINT):
        url = endpoint + url[len(constants.ENDPOINT) :]
    return url


def _request_wrapper(
    method: HTTP_METHOD_T, url: str, *, follow_relative_redirects: bool = False, **params
) -> requests.Response:
    """Wrapper around requests methods to follow relative redirects if `follow_relative_redirects=True` even when
    `allow_redirection=False`.

    A backoff mechanism retries the HTTP call on 429, 503 and 504 errors.

    Args:
        method (`str`):
            HTTP method, such as 'GET' or 'HEAD'.
        url (`str`):
            The URL of the resource to fetch.
        follow_relative_redirects (`bool`, *optional*, defaults to `False`)
            If True, relative redirection (redirection to the same site) will be resolved even when `allow_redirection`
            kwarg is set to False. Useful when we want to follow a redirection to a renamed repository without
            following redirection to a CDN.
        **params (`dict`, *optional*):
            Params to pass to `requests.request`.
    """
    # Recursively follow relative redirects
    if follow_relative_redirects:
        response = _request_wrapper(
            method=method,
            url=url,
            follow_relative_redirects=False,
            **params,
        )

        # If redirection, we redirect only relative paths.
        # This is useful in case of a renamed repository.
        if 300 <= response.status_code <= 399:
            parsed_target = urlparse(response.headers["Location"])
            if parsed_target.netloc == "":
                # This means it is a relative 'location' headers, as allowed by RFC 7231.
                # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
                # We want to follow this relative redirect !
                #
                # Highly inspired by `resolve_redirects` from requests library.
                # See https://github.com/psf/requests/blob/main/requests/sessions.py#L159
                next_url = urlparse(url)._replace(path=parsed_target.path).geturl()
                return _request_wrapper(method=method, url=next_url, follow_relative_redirects=True, **params)
        return response

    # Perform request and return if status_code is not in the retry list.
    response = http_backoff(method=method, url=url, **params, retry_on_exceptions=(), retry_on_status_codes=(429,))
    hf_raise_for_status(response)
    return response


def _get_file_length_from_http_response(response: requests.Response) -> Optional[int]:
    """
    Get the length of the file from the HTTP response headers.

    This function extracts the file size from the HTTP response headers, either from the
    `Content-Range` or `Content-Length` header, if available (in that order).
        The HTTP response object containing the headers.
        `int` or `None`: The length of the file in bytes if the information is available,
        otherwise `None`.

    Args:
        response (`requests.Response`):
            The HTTP response object.

    Returns:
        `int` or `None`: The length of the file in bytes, or None if not available.
    """

    content_range = response.headers.get("Content-Range")
    if content_range is not None:
        return int(content_range.rsplit("/")[-1])

    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        return int(content_length)

    return None


def http_get(
    url: str,
    temp_file: BinaryIO,
    *,
    proxies: Optional[Dict] = None,
    resume_size: int = 0,
    headers: Optional[Dict[str, Any]] = None,
    expected_size: Optional[int] = None,
    displayed_filename: Optional[str] = None,
    _nb_retries: int = 5,
    _tqdm_bar: Optional[tqdm] = None,
) -> None:
    """
    Download a remote file. Do not gobble up errors, and will return errors tailored to the Hugging Face Hub.

    If ConnectionError (SSLError) or ReadTimeout happen while streaming data from the server, it is most likely a
    transient error (network outage?). We log a warning message and try to resume the download a few times before
    giving up. The method gives up after 5 attempts if no new data has being received from the server.

    Args:
        url (`str`):
            The URL of the file to download.
        temp_file (`BinaryIO`):
            The file-like object where to save the file.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to `requests.request`.
        resume_size (`int`, *optional*):
            The number of bytes already downloaded. If set to 0 (default), the whole file is download. If set to a
            positive number, the download will resume at the given position.
        headers (`dict`, *optional*):
            Dictionary of HTTP Headers to send with the request.
        expected_size (`int`, *optional*):
            The expected size of the file to download. If set, the download will raise an error if the size of the
            received content is different from the expected one.
        displayed_filename (`str`, *optional*):
            The filename of the file that is being downloaded. Value is used only to display a nice progress bar. If
            not set, the filename is guessed from the URL or the `Content-Disposition` header.
    """
    if expected_size is not None and resume_size == expected_size:
        # If the file is already fully downloaded, we don't need to download it again.
        return

    has_custom_range_header = headers is not None and any(h.lower() == "range" for h in headers)
    hf_transfer = None
    if constants.HF_HUB_ENABLE_HF_TRANSFER:
        if resume_size != 0:
            warnings.warn("'hf_transfer' does not support `resume_size`: falling back to regular download method")
        elif proxies is not None:
            warnings.warn("'hf_transfer' does not support `proxies`: falling back to regular download method")
        elif has_custom_range_header:
            warnings.warn("'hf_transfer' ignores custom 'Range' headers; falling back to regular download method")
        else:
            try:
                import hf_transfer  # type: ignore[no-redef]
            except ImportError:
                raise ValueError(
                    "Fast download using 'hf_transfer' is enabled"
                    " (HF_HUB_ENABLE_HF_TRANSFER=1) but 'hf_transfer' package is not"
                    " available in your environment. Try `pip install hf_transfer`."
                )

    initial_headers = headers
    headers = copy.deepcopy(headers) or {}
    if resume_size > 0:
        headers["Range"] = _adjust_range_header(headers.get("Range"), resume_size)
    elif expected_size and expected_size > constants.MAX_HTTP_DOWNLOAD_SIZE:
        # Any files over 50GB will not be available through basic http request.
        # Setting the range header to 0-0 will force the server to return the file size in the Content-Range header.
        # Since hf_transfer splits the download into chunks, the process will succeed afterwards.
        if hf_transfer:
            headers["Range"] = "bytes=0-0"
        else:
            raise ValueError(
                "The file is too large to be downloaded using the regular download method. Use `hf_transfer` or `hf_xet` instead."
                " Try `pip install hf_transfer` or `pip install hf_xet`."
            )

    r = _request_wrapper(
        method="GET", url=url, stream=True, proxies=proxies, headers=headers, timeout=constants.HF_HUB_DOWNLOAD_TIMEOUT
    )

    hf_raise_for_status(r)
    content_length = _get_file_length_from_http_response(r)

    # NOTE: 'total' is the total number of bytes to download, not the number of bytes in the file.
    #       If the file is compressed, the number of bytes in the saved file will be higher than 'total'.
    total = resume_size + int(content_length) if content_length is not None else None

    if displayed_filename is None:
        displayed_filename = url
        content_disposition = r.headers.get("Content-Disposition")
        if content_disposition is not None:
            match = HEADER_FILENAME_PATTERN.search(content_disposition)
            if match is not None:
                # Means file is on CDN
                displayed_filename = match.groupdict()["filename"]

    # Truncate filename if too long to display
    if len(displayed_filename) > 40:
        displayed_filename = f"(…){displayed_filename[-40:]}"

    consistency_error_message = (
        f"Consistency check failed: file should be of size {expected_size} but has size"
        f" {{actual_size}} ({displayed_filename}).\nThis is usually due to network issues while downloading the file."
        " Please retry with `force_download=True`."
    )
    progress_cm = _get_progress_bar_context(
        desc=displayed_filename,
        log_level=logger.getEffectiveLevel(),
        total=total,
        initial=resume_size,
        name="huggingface_hub.http_get",
        _tqdm_bar=_tqdm_bar,
    )

    with progress_cm as progress:
        if hf_transfer and total is not None and total > 5 * constants.DOWNLOAD_CHUNK_SIZE:
            supports_callback = "callback" in inspect.signature(hf_transfer.download).parameters
            if not supports_callback:
                warnings.warn(
                    "You are using an outdated version of `hf_transfer`. "
                    "Consider upgrading to latest version to enable progress bars "
                    "using `pip install -U hf_transfer`."
                )
            try:
                hf_transfer.download(
                    url=url,
                    filename=temp_file.name,
                    max_files=constants.HF_TRANSFER_CONCURRENCY,
                    chunk_size=constants.DOWNLOAD_CHUNK_SIZE,
                    headers=initial_headers,
                    parallel_failures=3,
                    max_retries=5,
                    **({"callback": progress.update} if supports_callback else {}),
                )
            except Exception as e:
                raise RuntimeError(
                    "An error occurred while downloading using `hf_transfer`. Consider"
                    " disabling HF_HUB_ENABLE_HF_TRANSFER for better error handling."
                ) from e
            if not supports_callback:
                progress.update(total)
            if expected_size is not None and expected_size != os.path.getsize(temp_file.name):
                raise EnvironmentError(
                    consistency_error_message.format(
                        actual_size=os.path.getsize(temp_file.name),
                    )
                )
            return
        new_resume_size = resume_size
        try:
            for chunk in r.iter_content(chunk_size=constants.DOWNLOAD_CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    progress.update(len(chunk))
                    temp_file.write(chunk)
                    new_resume_size += len(chunk)
                    # Some data has been downloaded from the server so we reset the number of retries.
                    _nb_retries = 5
        except (requests.ConnectionError, requests.ReadTimeout) as e:
            # If ConnectionError (SSLError) or ReadTimeout happen while streaming data from the server, it is most likely
            # a transient error (network outage?). We log a warning message and try to resume the download a few times
            # before giving up. Tre retry mechanism is basic but should be enough in most cases.
            if _nb_retries <= 0:
                logger.warning("Error while downloading from %s: %s\nMax retries exceeded.", url, str(e))
                raise
            logger.warning("Error while downloading from %s: %s\nTrying to resume download...", url, str(e))
            time.sleep(1)
            reset_sessions()  # In case of SSLError it's best to reset the shared requests.Session objects
            return http_get(
                url=url,
                temp_file=temp_file,
                proxies=proxies,
                resume_size=new_resume_size,
                headers=initial_headers,
                expected_size=expected_size,
                _nb_retries=_nb_retries - 1,
                _tqdm_bar=_tqdm_bar,
            )

    if expected_size is not None and expected_size != temp_file.tell():
        raise EnvironmentError(
            consistency_error_message.format(
                actual_size=temp_file.tell(),
            )
        )


def xet_get(
    *,
    incomplete_path: Path,
    xet_file_data: XetFileData,
    headers: Dict[str, str],
    expected_size: Optional[int] = None,
    displayed_filename: Optional[str] = None,
    _tqdm_bar: Optional[tqdm] = None,
) -> None:
    """
    Download a file using Xet storage service.

    Args:
        incomplete_path (`Path`):
            The path to the file to download.
        xet_file_data (`XetFileData`):
            The file metadata needed to make the request to the xet storage service.
        headers (`Dict[str, str]`):
            The headers to send to the xet storage service.
        expected_size (`int`, *optional*):
            The expected size of the file to download. If set, the download will raise an error if the size of the
            received content is different from the expected one.
        displayed_filename (`str`, *optional*):
            The filename of the file that is being downloaded. Value is used only to display a nice progress bar. If
            not set, the filename is guessed from the URL or the `Content-Disposition` header.

    **How it works:**
        The file download system uses Xet storage, which is a content-addressable storage system that breaks files into chunks
        for efficient storage and transfer.

        `hf_xet.download_files` manages downloading files by:
        - Taking a list of files to download (each with its unique content hash)
        - Connecting to a storage server (CAS server) that knows how files are chunked
        - Using authentication to ensure secure access
        - Providing progress updates during download

        Authentication works by regularly refreshing access tokens through `refresh_xet_connection_info` to maintain a valid
        connection to the storage server.

        The download process works like this:
        1. Create a local cache folder at `~/.cache/huggingface/xet/chunk-cache` to store reusable file chunks
        2. Download files in parallel:
            2.1. Prepare to write the file to disk
            2.2. Ask the server "how is this file split into chunks?" using the file's unique hash
                The server responds with:
                - Which chunks make up the complete file
                - Where each chunk can be downloaded from
            2.3. For each needed chunk:
                - Checks if we already have it in our local cache
                - If not, download it from cloud storage (S3)
                - Save it to cache for future use
                - Assemble the chunks in order to recreate the original file

    """
    try:
        from hf_xet import PyXetDownloadInfo, download_files  # type: ignore[no-redef]
    except ImportError:
        raise ValueError(
            "To use optimized download using Xet storage, you need to install the hf_xet package. "
            'Try `pip install "huggingface_hub[hf_xet]"` or `pip install hf_xet`.'
        )

    connection_info = refresh_xet_connection_info(file_data=xet_file_data, headers=headers)

    def token_refresher() -> Tuple[str, int]:
        connection_info = refresh_xet_connection_info(file_data=xet_file_data, headers=headers)
        if connection_info is None:
            raise ValueError("Failed to refresh token using xet metadata.")
        return connection_info.access_token, connection_info.expiration_unix_epoch

    xet_download_info = [
        PyXetDownloadInfo(
            destination_path=str(incomplete_path.absolute()), hash=xet_file_data.file_hash, file_size=expected_size
        )
    ]

    if not displayed_filename:
        displayed_filename = incomplete_path.name

    # Truncate filename if too long to display
    if len(displayed_filename) > 40:
        displayed_filename = f"{displayed_filename[:40]}(…)"

    progress_cm = _get_progress_bar_context(
        desc=displayed_filename,
        log_level=logger.getEffectiveLevel(),
        total=expected_size,
        initial=0,
        name="huggingface_hub.xet_get",
        _tqdm_bar=_tqdm_bar,
    )

    with progress_cm as progress:

        def progress_updater(progress_bytes: float):
            progress.update(progress_bytes)

        download_files(
            xet_download_info,
            endpoint=connection_info.endpoint,
            token_info=(connection_info.access_token, connection_info.expiration_unix_epoch),
            token_refresher=token_refresher,
            progress_updater=[progress_updater],
        )


def _normalize_etag(etag: Optional[str]) -> Optional[str]:
    """Normalize ETag HTTP header, so it can be used to create nice filepaths.

    The HTTP spec allows two forms of ETag:
      ETag: W/"<etag_value>"
      ETag: "<etag_value>"

    For now, we only expect the second form from the server, but we want to be future-proof so we support both. For
    more context, see `TestNormalizeEtag` tests and https://github.com/huggingface/huggingface_hub/pull/1428.

    Args:
        etag (`str`, *optional*): HTTP header

    Returns:
        `str` or `None`: string that can be used as a nice directory name.
        Returns `None` if input is None.
    """
    if etag is None:
        return None
    return etag.lstrip("W/").strip('"')


def _create_relative_symlink(src: str, dst: str, new_blob: bool = False) -> None:
    """Alias method used in `transformers` conversion script."""
    return _create_symlink(src=src, dst=dst, new_blob=new_blob)


def _create_symlink(src: str, dst: str, new_blob: bool = False) -> None:
    """Create a symbolic link named dst pointing to src.

    By default, it will try to create a symlink using a relative path. Relative paths have 2 advantages:
    - If the cache_folder is moved (example: back-up on a shared drive), relative paths within the cache folder will
      not break.
    - Relative paths seems to be better handled on Windows. Issue was reported 3 times in less than a week when
      changing from relative to absolute paths. See https://github.com/huggingface/huggingface_hub/issues/1398,
      https://github.com/huggingface/diffusers/issues/2729 and https://github.com/huggingface/transformers/pull/22228.
      NOTE: The issue with absolute paths doesn't happen on admin mode.
    When creating a symlink from the cache to a local folder, it is possible that a relative path cannot be created.
    This happens when paths are not on the same volume. In that case, we use absolute paths.


    The result layout looks something like
        └── [ 128]  snapshots
            ├── [ 128]  2439f60ef33a0d46d85da5001d52aeda5b00ce9f
            │   ├── [  52]  README.md -> ../../../blobs/d7edf6bd2a681fb0175f7735299831ee1b22b812
            │   └── [  76]  pytorch_model.bin -> ../../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd

    If symlinks cannot be created on this platform (most likely to be Windows), the workaround is to avoid symlinks by
    having the actual file in `dst`. If it is a new file (`new_blob=True`), we move it to `dst`. If it is not a new file
    (`new_blob=False`), we don't know if the blob file is already referenced elsewhere. To avoid breaking existing
    cache, the file is duplicated on the disk.

    In case symlinks are not supported, a warning message is displayed to the user once when loading `huggingface_hub`.
    The warning message can be disabled with the `DISABLE_SYMLINKS_WARNING` environment variable.
    """
    try:
        os.remove(dst)
    except OSError:
        pass

    abs_src = os.path.abspath(os.path.expanduser(src))
    abs_dst = os.path.abspath(os.path.expanduser(dst))
    abs_dst_folder = os.path.dirname(abs_dst)

    # Use relative_dst in priority
    try:
        relative_src = os.path.relpath(abs_src, abs_dst_folder)
    except ValueError:
        # Raised on Windows if src and dst are not on the same volume. This is the case when creating a symlink to a
        # local_dir instead of within the cache directory.
        # See https://docs.python.org/3/library/os.path.html#os.path.relpath
        relative_src = None

    try:
        commonpath = os.path.commonpath([abs_src, abs_dst])
        _support_symlinks = are_symlinks_supported(commonpath)
    except ValueError:
        # Raised if src and dst are not on the same volume. Symlinks will still work on Linux/Macos.
        # See https://docs.python.org/3/library/os.path.html#os.path.commonpath
        _support_symlinks = os.name != "nt"
    except PermissionError:
        # Permission error means src and dst are not in the same volume (e.g. destination path has been provided
        # by the user via `local_dir`. Let's test symlink support there)
        _support_symlinks = are_symlinks_supported(abs_dst_folder)
    except OSError as e:
        # OS error (errno=30) means that the commonpath is readonly on Linux/MacOS.
        if e.errno == errno.EROFS:
            _support_symlinks = are_symlinks_supported(abs_dst_folder)
        else:
            raise

    # Symlinks are supported => let's create a symlink.
    if _support_symlinks:
        src_rel_or_abs = relative_src or abs_src
        logger.debug(f"Creating pointer from {src_rel_or_abs} to {abs_dst}")
        try:
            os.symlink(src_rel_or_abs, abs_dst)
            return
        except FileExistsError:
            if os.path.islink(abs_dst) and os.path.realpath(abs_dst) == os.path.realpath(abs_src):
                # `abs_dst` already exists and is a symlink to the `abs_src` blob. It is most likely that the file has
                # been cached twice concurrently (exactly between `os.remove` and `os.symlink`). Do nothing.
                return
            else:
                # Very unlikely to happen. Means a file `dst` has been created exactly between `os.remove` and
                # `os.symlink` and is not a symlink to the `abs_src` blob file. Raise exception.
                raise
        except PermissionError:
            # Permission error means src and dst are not in the same volume (e.g. download to local dir) and symlink
            # is supported on both volumes but not between them. Let's just make a hard copy in that case.
            pass

    # Symlinks are not supported => let's move or copy the file.
    if new_blob:
        logger.info(f"Symlink not supported. Moving file from {abs_src} to {abs_dst}")
        shutil.move(abs_src, abs_dst, copy_function=_copy_no_matter_what)
    else:
        logger.info(f"Symlink not supported. Copying file from {abs_src} to {abs_dst}")
        shutil.copyfile(abs_src, abs_dst)


def _cache_commit_hash_for_specific_revision(storage_folder: str, revision: str, commit_hash: str) -> None:
    """Cache reference between a revision (tag, branch or truncated commit hash) and the corresponding commit hash.

    Does nothing if `revision` is already a proper `commit_hash` or reference is already cached.
    """
    if revision != commit_hash:
        ref_path = Path(storage_folder) / "refs" / revision
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        if not ref_path.exists() or commit_hash != ref_path.read_text():
            # Update ref only if has been updated. Could cause useless error in case
            # repo is already cached and user doesn't have write access to cache folder.
            # See https://github.com/huggingface/huggingface_hub/issues/1216.
            ref_path.write_text(commit_hash)


@validate_hf_hub_args
def repo_folder_name(*, repo_id: str, repo_type: str) -> str:
    """Return a serialized version of a hf.co repo name and type, safe for disk storage
    as a single non-nested folder.

    Example: models--julien-c--EsperBERTo-small
    """
    # remove all `/` occurrences to correctly convert repo to directory name
    parts = [f"{repo_type}s", *repo_id.split("/")]
    return constants.REPO_ID_SEPARATOR.join(parts)


def _check_disk_space(expected_size: int, target_dir: Union[str, Path]) -> None:
    """Check disk usage and log a warning if there is not enough disk space to download the file.

    Args:
        expected_size (`int`):
            The expected size of the file in bytes.
        target_dir (`str`):
            The directory where the file will be stored after downloading.
    """

    target_dir = Path(target_dir)  # format as `Path`
    for path in [target_dir] + list(target_dir.parents):  # first check target_dir, then each parents one by one
        try:
            target_dir_free = shutil.disk_usage(path).free
            if target_dir_free < expected_size:
                warnings.warn(
                    "Not enough free disk space to download the file. "
                    f"The expected file size is: {expected_size / 1e6:.2f} MB. "
                    f"The target location {target_dir} only has {target_dir_free / 1e6:.2f} MB free disk space."
                )
            return
        except OSError:  # raise on anything: file does not exist or space disk cannot be checked
            pass


@validate_hf_hub_args
def hf_hub_download(
    repo_id: str,
    filename: str,
    *,
    subfolder: Optional[str] = None,
    repo_type: Optional[str] = None,
    revision: Optional[str] = None,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    cache_dir: Union[str, Path, None] = None,
    local_dir: Union[str, Path, None] = None,
    user_agent: Union[Dict, str, None] = None,
    force_download: bool = False,
    proxies: Optional[Dict] = None,
    etag_timeout: float = constants.DEFAULT_ETAG_TIMEOUT,
    token: Union[bool, str, None] = None,
    local_files_only: bool = False,
    headers: Optional[Dict[str, str]] = None,
    endpoint: Optional[str] = None,
    resume_download: Optional[bool] = None,
    force_filename: Optional[str] = None,
    local_dir_use_symlinks: Union[bool, Literal["auto"]] = "auto",
) -> str:
    """Download a given file if it's not already present in the local cache.

    The new cache file layout looks like this:
    - The cache directory contains one subfolder per repo_id (namespaced by repo type)
    - inside each repo folder:
        - refs is a list of the latest known revision => commit_hash pairs
        - blobs contains the actual file blobs (identified by their git-sha or sha256, depending on
          whether they're LFS files or not)
        - snapshots contains one subfolder per commit, each "commit" contains the subset of the files
          that have been resolved at that particular commit. Each filename is a symlink to the blob
          at that particular commit.

    ```
    [  96]  .
    └── [ 160]  models--julien-c--EsperBERTo-small
        ├── [ 160]  blobs
        │   ├── [321M]  403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
        │   ├── [ 398]  7cb18dc9bafbfcf74629a4b760af1b160957a83e
        │   └── [1.4K]  d7edf6bd2a681fb0175f7735299831ee1b22b812
        ├── [  96]  refs
        │   └── [  40]  main
        └── [ 128]  snapshots
            ├── [ 128]  2439f60ef33a0d46d85da5001d52aeda5b00ce9f
            │   ├── [  52]  README.md -> ../../blobs/d7edf6bd2a681fb0175f7735299831ee1b22b812
            │   └── [  76]  pytorch_model.bin -> ../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
            └── [ 128]  bbc77c8132af1cc5cf678da3f1ddf2de43606d48
                ├── [  52]  README.md -> ../../blobs/7cb18dc9bafbfcf74629a4b760af1b160957a83e
                └── [  76]  pytorch_model.bin -> ../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
    ```

    If `local_dir` is provided, the file structure from the repo will be replicated in this location. When using this
    option, the `cache_dir` will not be used and a `.cache/huggingface/` folder will be created at the root of `local_dir`
    to store some metadata related to the downloaded files. While this mechanism is not as robust as the main
    cache-system, it's optimized for regularly pulling the latest version of a repository.

    Args:
        repo_id (`str`):
            A user or an organization name and a repo name separated by a `/`.
        filename (`str`):
            The name of the file in the repo.
        subfolder (`str`, *optional*):
            An optional value corresponding to a folder inside the model repo.
        repo_type (`str`, *optional*):
            Set to `"dataset"` or `"space"` if downloading from a dataset or space,
            `None` or `"model"` if downloading from a model. Default is `None`.
        revision (`str`, *optional*):
            An optional Git revision id which can be a branch name, a tag, or a
            commit hash.
        library_name (`str`, *optional*):
            The name of the library to which the object corresponds.
        library_version (`str`, *optional*):
            The version of the library.
        cache_dir (`str`, `Path`, *optional*):
            Path to the folder where cached files are stored.
        local_dir (`str` or `Path`, *optional*):
            If provided, the downloaded file will be placed under this directory.
        user_agent (`dict`, `str`, *optional*):
            The user-agent info in the form of a dictionary or a string.
        force_download (`bool`, *optional*, defaults to `False`):
            Whether the file should be downloaded even if it already exists in
            the local cache.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to
            `requests.request`.
        etag_timeout (`float`, *optional*, defaults to `10`):
            When fetching ETag, how many seconds to wait for the server to send
            data before giving up which is passed to `requests.request`.
        token (`str`, `bool`, *optional*):
            A token to be used for the download.
                - If `True`, the token is read from the HuggingFace config
                  folder.
                - If a string, it's used as the authentication token.
        local_files_only (`bool`, *optional*, defaults to `False`):
            If `True`, avoid downloading the file and return the path to the
            local cached file if it exists.
        headers (`dict`, *optional*):
            Additional headers to be sent with the request.

    Returns:
        `str`: Local path of file or if networking is off, last version of file cached on disk.

    Raises:
        [`~utils.RepositoryNotFoundError`]
            If the repository to download from cannot be found. This may be because it doesn't exist,
            or because it is set to `private` and you do not have access.
        [`~utils.RevisionNotFoundError`]
            If the revision to download from cannot be found.
        [`~utils.EntryNotFoundError`]
            If the file to download cannot be found.
        [`~utils.LocalEntryNotFoundError`]
            If network is disabled or unavailable and file is not found in cache.
        [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
            If `token=True` but the token cannot be found.
        [`OSError`](https://docs.python.org/3/library/exceptions.html#OSError)
            If ETag cannot be determined.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If some parameter value is invalid.

    """
    if constants.HF_HUB_ETAG_TIMEOUT != constants.DEFAULT_ETAG_TIMEOUT:
        # Respect environment variable above user value
        etag_timeout = constants.HF_HUB_ETAG_TIMEOUT

    if force_filename is not None:
        warnings.warn(
            "The `force_filename` parameter is deprecated as a new caching system, "
            "which keeps the filenames as they are on the Hub, is now in place.",
            FutureWarning,
        )
    if resume_download is not None:
        warnings.warn(
            "`resume_download` is deprecated and will be removed in version 1.0.0. "
            "Downloads always resume when possible. "
            "If you want to force a new download, use `force_download=True`.",
            FutureWarning,
        )

    if cache_dir is None:
        cache_dir = constants.HF_HUB_CACHE
    if revision is None:
        revision = constants.DEFAULT_REVISION
    if isinstance(cache_dir, Path):
        cache_dir = str(cache_dir)
    if isinstance(local_dir, Path):
        local_dir = str(local_dir)

    if subfolder == "":
        subfolder = None
    if subfolder is not None:
        # This is used to create a URL, and not a local path, hence the forward slash.
        filename = f"{subfolder}/{filename}"

    if repo_type is None:
        repo_type = "model"
    if repo_type not in constants.REPO_TYPES:
        raise ValueError(f"Invalid repo type: {repo_type}. Accepted repo types are: {str(constants.REPO_TYPES)}")

    hf_headers = build_hf_headers(
        token=token,
        library_name=library_name,
        library_version=library_version,
        user_agent=user_agent,
        headers=headers,
    )

    if local_dir is not None:
        if local_dir_use_symlinks != "auto":
            warnings.warn(
                "`local_dir_use_symlinks` parameter is deprecated and will be ignored. "
                "The process to download files to a local folder has been updated and do "
                "not rely on symlinks anymore. You only need to pass a destination folder "
                "as`local_dir`.\n"
                "For more details, check out https://huggingface.co/docs/huggingface_hub/main/en/guides/download#download-files-to-local-folder."
            )

        return _hf_hub_download_to_local_dir(
            # Destination
            local_dir=local_dir,
            # File info
            repo_id=repo_id,
            repo_type=repo_type,
            filename=filename,
            revision=revision,
            # HTTP info
            endpoint=endpoint,
            etag_timeout=etag_timeout,
            headers=hf_headers,
            proxies=proxies,
            token=token,
            # Additional options
            cache_dir=cache_dir,
            force_download=force_download,
            local_files_only=local_files_only,
        )
    else:
        return _hf_hub_download_to_cache_dir(
            # Destination
            cache_dir=cache_dir,
            # File info
            repo_id=repo_id,
            filename=filename,
            repo_type=repo_type,
            revision=revision,
            # HTTP info
            endpoint=endpoint,
            etag_timeout=etag_timeout,
            headers=hf_headers,
            proxies=proxies,
            token=token,
            # Additional options
            local_files_only=local_files_only,
            force_download=force_download,
        )


def _hf_hub_download_to_cache_dir(
    *,
    # Destination
    cache_dir: str,
    # File info
    repo_id: str,
    filename: str,
    repo_type: str,
    revision: str,
    # HTTP info
    endpoint: Optional[str],
    etag_timeout: float,
    headers: Dict[str, str],
    proxies: Optional[Dict],
    token: Optional[Union[bool, str]],
    # Additional options
    local_files_only: bool,
    force_download: bool,
) -> str:
    """Download a given file to a cache folder, if not already present.

    Method should not be called directly. Please use `hf_hub_download` instead.
    """
    locks_dir = os.path.join(cache_dir, ".locks")
    storage_folder = os.path.join(cache_dir, repo_folder_name(repo_id=repo_id, repo_type=repo_type))

    # cross platform transcription of filename, to be used as a local file path.
    relative_filename = os.path.join(*filename.split("/"))
    if os.name == "nt":
        if relative_filename.startswith("..\\") or "\\..\\" in relative_filename:
            raise ValueError(
                f"Invalid filename: cannot handle filename '{relative_filename}' on Windows. Please ask the repository"
                " owner to rename this file."
            )

    # if user provides a commit_hash and they already have the file on disk, shortcut everything.
    if REGEX_COMMIT_HASH.match(revision):
        pointer_path = _get_pointer_path(storage_folder, revision, relative_filename)
        if os.path.exists(pointer_path) and not force_download:
            return pointer_path

    # Try to get metadata (etag, commit_hash, url, size) from the server.
    # If we can't, a HEAD request error is returned.
    (url_to_download, etag, commit_hash, expected_size, xet_file_data, head_call_error) = _get_metadata_or_catch_error(
        repo_id=repo_id,
        filename=filename,
        repo_type=repo_type,
        revision=revision,
        endpoint=endpoint,
        proxies=proxies,
        etag_timeout=etag_timeout,
        headers=headers,
        token=token,
        local_files_only=local_files_only,
        storage_folder=storage_folder,
        relative_filename=relative_filename,
    )

    # etag can be None for several reasons:
    # 1. we passed local_files_only.
    # 2. we don't have a connection
    # 3. Hub is down (HTTP 500, 503, 504)
    # 4. repo is not found -for example private or gated- and invalid/missing token sent
    # 5. Hub is blocked by a firewall or proxy is not set correctly.
    # => Try to get the last downloaded one from the specified revision.
    #
    # If the specified revision is a commit hash, look inside "snapshots".
    # If the specified revision is a branch or tag, look inside "refs".
    if head_call_error is not None:
        # Couldn't make a HEAD call => let's try to find a local file
        if not force_download:
            commit_hash = None
            if REGEX_COMMIT_HASH.match(revision):
                commit_hash = revision
            else:
                ref_path = os.path.join(storage_folder, "refs", revision)
                if os.path.isfile(ref_path):
                    with open(ref_path) as f:
                        commit_hash = f.read()

            # Return pointer file if exists
            if commit_hash is not None:
                pointer_path = _get_pointer_path(storage_folder, commit_hash, relative_filename)
                if os.path.exists(pointer_path) and not force_download:
                    return pointer_path

        # Otherwise, raise appropriate error
        _raise_on_head_call_error(head_call_error, force_download, local_files_only)

    # From now on, etag, commit_hash, url and size are not None.
    assert etag is not None, "etag must have been retrieved from server"
    assert commit_hash is not None, "commit_hash must have been retrieved from server"
    assert url_to_download is not None, "file location must have been retrieved from server"
    assert expected_size is not None, "expected_size must have been retrieved from server"
    blob_path = os.path.join(storage_folder, "blobs", etag)
    pointer_path = _get_pointer_path(storage_folder, commit_hash, relative_filename)

    os.makedirs(os.path.dirname(blob_path), exist_ok=True)
    os.makedirs(os.path.dirname(pointer_path), exist_ok=True)

    # if passed revision is not identical to commit_hash
    # then revision has to be a branch name or tag name.
    # In that case store a ref.
    _cache_commit_hash_for_specific_revision(storage_folder, revision, commit_hash)

    # Prevent parallel downloads of the same file with a lock.
    # etag could be duplicated across repos,
    lock_path = os.path.join(locks_dir, repo_folder_name(repo_id=repo_id, repo_type=repo_type), f"{etag}.lock")

    # Some Windows versions do not allow for paths longer than 255 characters.
    # In this case, we must specify it as an extended path by using the "\\?\" prefix.
    if os.name == "nt" and len(os.path.abspath(lock_path)) > 255:
        lock_path = "\\\\?\\" + os.path.abspath(lock_path)

    if os.name == "nt" and len(os.path.abspath(blob_path)) > 255:
        blob_path = "\\\\?\\" + os.path.abspath(blob_path)

    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)

    # pointer already exists -> immediate return
    if not force_download and os.path.exists(pointer_path):
        return pointer_path

    # Blob exists but pointer must be (safely) created -> take the lock
    if not force_download and os.path.exists(blob_path):
        with WeakFileLock(lock_path):
            if not os.path.exists(pointer_path):
                _create_symlink(blob_path, pointer_path, new_blob=False)
            return pointer_path

    # Local file doesn't exist or etag isn't a match => retrieve file from remote (or cache)

    with WeakFileLock(lock_path):
        _download_to_tmp_and_move(
            incomplete_path=Path(blob_path + ".incomplete"),
            destination_path=Path(blob_path),
            url_to_download=url_to_download,
            proxies=proxies,
            headers=headers,
            expected_size=expected_size,
            filename=filename,
            force_download=force_download,
            etag=etag,
            xet_file_data=xet_file_data,
        )
        if not os.path.exists(pointer_path):
            _create_symlink(blob_path, pointer_path, new_blob=True)

    return pointer_path


def _hf_hub_download_to_local_dir(
    *,
    # Destination
    local_dir: Union[str, Path],
    # File info
    repo_id: str,
    repo_type: str,
    filename: str,
    revision: str,
    # HTTP info
    endpoint: Optional[str],
    etag_timeout: float,
    headers: Dict[str, str],
    proxies: Optional[Dict],
    token: Union[bool, str, None],
    # Additional options
    cache_dir: str,
    force_download: bool,
    local_files_only: bool,
) -> str:
    """Download a given file to a local folder, if not already present.

    Method should not be called directly. Please use `hf_hub_download` instead.
    """
    # Some Windows versions do not allow for paths longer than 255 characters.
    # In this case, we must specify it as an extended path by using the "\\?\" prefix.
    if os.name == "nt" and len(os.path.abspath(local_dir)) > 255:
        local_dir = "\\\\?\\" + os.path.abspath(local_dir)
    local_dir = Path(local_dir)
    paths = get_local_download_paths(local_dir=local_dir, filename=filename)
    local_metadata = read_download_metadata(local_dir=local_dir, filename=filename)

    # Local file exists + metadata exists + commit_hash matches => return file
    if (
        not force_download
        and REGEX_COMMIT_HASH.match(revision)
        and paths.file_path.is_file()
        and local_metadata is not None
        and local_metadata.commit_hash == revision
    ):
        return str(paths.file_path)

    # Local file doesn't exist or commit_hash doesn't match => we need the etag
    (url_to_download, etag, commit_hash, expected_size, xet_file_data, head_call_error) = _get_metadata_or_catch_error(
        repo_id=repo_id,
        filename=filename,
        repo_type=repo_type,
        revision=revision,
        endpoint=endpoint,
        proxies=proxies,
        etag_timeout=etag_timeout,
        headers=headers,
        token=token,
        local_files_only=local_files_only,
    )

    if head_call_error is not None:
        # No HEAD call but local file exists => default to local file
        if not force_download and paths.file_path.is_file():
            logger.warning(
                f"Couldn't access the Hub to check for update but local file already exists. Defaulting to existing file. (error: {head_call_error})"
            )
            return str(paths.file_path)
        # Otherwise => raise
        _raise_on_head_call_error(head_call_error, force_download, local_files_only)

    # From now on, etag, commit_hash, url and size are not None.
    assert etag is not None, "etag must have been retrieved from server"
    assert commit_hash is not None, "commit_hash must have been retrieved from server"
    assert url_to_download is not None, "file location must have been retrieved from server"
    assert expected_size is not None, "expected_size must have been retrieved from server"

    # Local file exists => check if it's up-to-date
    if not force_download and paths.file_path.is_file():
        # etag matches => update metadata and return file
        if local_metadata is not None and local_metadata.etag == etag:
            write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
            return str(paths.file_path)

        # metadata is outdated + etag is a sha256
        # => means it's an LFS file (large)
        # => let's compute local hash and compare
        # => if match, update metadata and return file
        if local_metadata is None and REGEX_SHA256.match(etag) is not None:
            with open(paths.file_path, "rb") as f:
                file_hash = sha_fileobj(f).hex()
            if file_hash == etag:
                write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
                return str(paths.file_path)

    # Local file doesn't exist or etag isn't a match => retrieve file from remote (or cache)

    # If we are lucky enough, the file is already in the cache => copy it
    if not force_download:
        cached_path = try_to_load_from_cache(
            repo_id=repo_id,
            filename=filename,
            cache_dir=cache_dir,
            revision=commit_hash,
            repo_type=repo_type,
        )
        if isinstance(cached_path, str):
            with WeakFileLock(paths.lock_path):
                paths.file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cached_path, paths.file_path)
            write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
            return str(paths.file_path)

    # Otherwise, let's download the file!
    with WeakFileLock(paths.lock_path):
        paths.file_path.unlink(missing_ok=True)  # delete outdated file first
        _download_to_tmp_and_move(
            incomplete_path=paths.incomplete_path(etag),
            destination_path=paths.file_path,
            url_to_download=url_to_download,
            proxies=proxies,
            headers=headers,
            expected_size=expected_size,
            filename=filename,
            force_download=force_download,
            etag=etag,
            xet_file_data=xet_file_data,
        )

    write_download_metadata(local_dir=local_dir, filename=filename, commit_hash=commit_hash, etag=etag)
    return str(paths.file_path)


@validate_hf_hub_args
def try_to_load_from_cache(
    repo_id: str,
    filename: str,
    cache_dir: Union[str, Path, None] = None,
    revision: Optional[str] = None,
    repo_type: Optional[str] = None,
) -> Union[str, _CACHED_NO_EXIST_T, None]:
    """
    Explores the cache to return the latest cached file for a given revision if found.

    This function will not raise any exception if the file in not cached.

    Args:
        cache_dir (`str` or `os.PathLike`):
            The folder where the cached files lie.
        repo_id (`str`):
            The ID of the repo on huggingface.co.
        filename (`str`):
            The filename to look for inside `repo_id`.
        revision (`str`, *optional*):
            The specific model version to use. Will default to `"main"` if it's not provided and no `commit_hash` is
            provided either.
        repo_type (`str`, *optional*):
            The type of the repository. Will default to `"model"`.

    Returns:
        `Optional[str]` or `_CACHED_NO_EXIST`:
            Will return `None` if the file was not cached. Otherwise:
            - The exact path to the cached file if it's found in the cache
            - A special value `_CACHED_NO_EXIST` if the file does not exist at the given commit hash and this fact was
              cached.

    Example:

    ```python
    from huggingface_hub import try_to_load_from_cache, _CACHED_NO_EXIST

    filepath = try_to_load_from_cache()
    if isinstance(filepath, str):
        # file exists and is cached
        ...
    elif filepath is _CACHED_NO_EXIST:
        # non-existence of file is cached
        ...
    else:
        # file is not cached
        ...
    ```
    """
    if revision is None:
        revision = "main"
    if repo_type is None:
        repo_type = "model"
    if repo_type not in constants.REPO_TYPES:
        raise ValueError(f"Invalid repo type: {repo_type}. Accepted repo types are: {str(constants.REPO_TYPES)}")
    if cache_dir is None:
        cache_dir = constants.HF_HUB_CACHE

    object_id = repo_id.replace("/", "--")
    repo_cache = os.path.join(cache_dir, f"{repo_type}s--{object_id}")
    if not os.path.isdir(repo_cache):
        # No cache for this model
        return None

    refs_dir = os.path.join(repo_cache, "refs")
    snapshots_dir = os.path.join(repo_cache, "snapshots")
    no_exist_dir = os.path.join(repo_cache, ".no_exist")

    # Resolve refs (for instance to convert main to the associated commit sha)
    if os.path.isdir(refs_dir):
        revision_file = os.path.join(refs_dir, revision)
        if os.path.isfile(revision_file):
            with open(revision_file) as f:
                revision = f.read()

    # Check if file is cached as "no_exist"
    if os.path.isfile(os.path.join(no_exist_dir, revision, filename)):
        return _CACHED_NO_EXIST

    # Check if revision folder exists
    if not os.path.exists(snapshots_dir):
        return None
    cached_shas = os.listdir(snapshots_dir)
    if revision not in cached_shas:
        # No cache for this revision and we won't try to return a random revision
        return None

    # Check if file exists in cache
    cached_file = os.path.join(snapshots_dir, revision, filename)
    return cached_file if os.path.isfile(cached_file) else None


@validate_hf_hub_args
def get_hf_file_metadata(
    url: str,
    token: Union[bool, str, None] = None,
    proxies: Optional[Dict] = None,
    timeout: Optional[float] = constants.DEFAULT_REQUEST_TIMEOUT,
    library_name: Optional[str] = None,
    library_version: Optional[str] = None,
    user_agent: Union[Dict, str, None] = None,
    headers: Optional[Dict[str, str]] = None,
) -> HfFileMetadata:
    """Fetch metadata of a file versioned on the Hub for a given url.

    Args:
        url (`str`):
            File url, for example returned by [`hf_hub_url`].
        token (`str` or `bool`, *optional*):
            A token to be used for the download.
                - If `True`, the token is read from the HuggingFace config
                  folder.
                - If `False` or `None`, no token is provided.
                - If a string, it's used as the authentication token.
        proxies (`dict`, *optional*):
            Dictionary mapping protocol to the URL of the proxy passed to
            `requests.request`.
        timeout (`float`, *optional*, defaults to 10):
            How many seconds to wait for the server to send metadata before giving up.
        library_name (`str`, *optional*):
            The name of the library to which the object corresponds.
        library_version (`str`, *optional*):
            The version of the library.
        user_agent (`dict`, `str`, *optional*):
            The user-agent info in the form of a dictionary or a string.
        headers (`dict`, *optional*):
            Additional headers to be sent with the request.

    Returns:
        A [`HfFileMetadata`] object containing metadata such as location, etag, size and
        commit_hash.
    """
    hf_headers = build_hf_headers(
        token=token,
        library_name=library_name,
        library_version=library_version,
        user_agent=user_agent,
        headers=headers,
    )
    hf_headers["Accept-Encoding"] = "identity"  # prevent any compression => we want to know the real size of the file

    # Retrieve metadata
    r = _request_wrapper(
        method="HEAD",
        url=url,
        headers=hf_headers,
        allow_redirects=False,
        follow_relative_redirects=True,
        proxies=proxies,
        timeout=timeout,
    )
    hf_raise_for_status(r)

    # Return
    return HfFileMetadata(
        commit_hash=r.headers.get(constants.HUGGINGFACE_HEADER_X_REPO_COMMIT),
        # We favor a custom header indicating the etag of the linked resource, and
        # we fallback to the regular etag header.
        etag=_normalize_etag(r.headers.get(constants.HUGGINGFACE_HEADER_X_LINKED_ETAG) or r.headers.get("ETag")),
        # Either from response headers (if redirected) or defaults to request url
        # Do not use directly `url`, as `_request_wrapper` might have followed relative
        # redirects.
        location=r.headers.get("Location") or r.request.url,  # type: ignore
        size=_int_or_none(
            r.headers.get(constants.HUGGINGFACE_HEADER_X_LINKED_SIZE) or r.headers.get("Content-Length")
        ),
        xet_file_data=parse_xet_file_data_from_response(r),  # type: ignore
    )


def _get_metadata_or_catch_error(
    *,
    repo_id: str,
    filename: str,
    repo_type: str,
    revision: str,
    endpoint: Optional[str],
    proxies: Optional[Dict],
    etag_timeout: Optional[float],
    headers: Dict[str, str],  # mutated inplace!
    token: Union[bool, str, None],
    local_files_only: bool,
    relative_filename: Optional[str] = None,  # only used to store `.no_exists` in cache
    storage_folder: Optional[str] = None,  # only used to store `.no_exists` in cache
) -> Union[
    # Either an exception is caught and returned
    Tuple[None, None, None, None, None, Exception],
    # Or the metadata is returned as
    # `(url_to_download, etag, commit_hash, expected_size, xet_file_data, None)`
    Tuple[str, str, str, int, Optional[XetFileData], None],
]:
    """Get metadata for a file on the Hub, safely handling network issues.

    Returns either the etag, commit_hash and expected size of the file, or the error
    raised while fetching the metadata.

    NOTE: This function mutates `headers` inplace! It removes the `authorization` header
          if the file is a LFS blob and the domain of the url is different from the
          domain of the location (typically an S3 bucket).
    """
    if local_files_only:
        return (
            None,
            None,
            None,
            None,
            None,
            OfflineModeIsEnabled(
                f"Cannot access file since 'local_files_only=True' as been set. (repo_id: {repo_id}, repo_type: {repo_type}, revision: {revision}, filename: {filename})"
            ),
        )

    url = hf_hub_url(repo_id, filename, repo_type=repo_type, revision=revision, endpoint=endpoint)
    url_to_download: str = url
    etag: Optional[str] = None
    commit_hash: Optional[str] = None
    expected_size: Optional[int] = None
    head_error_call: Optional[Exception] = None
    xet_file_data: Optional[XetFileData] = None

    # Try to get metadata from the server.
    # Do not raise yet if the file is not found or not accessible.
    if not local_files_only:
        try:
            try:
                metadata = get_hf_file_metadata(
                    url=url, proxies=proxies, timeout=etag_timeout, headers=headers, token=token
                )
            except EntryNotFoundError as http_error:
                if storage_folder is not None and relative_filename is not None:
                    # Cache the non-existence of the file
                    commit_hash = http_error.response.headers.get(constants.HUGGINGFACE_HEADER_X_REPO_COMMIT)
                    if commit_hash is not None:
                        no_exist_file_path = Path(storage_folder) / ".no_exist" / commit_hash / relative_filename
                        try:
                            no_exist_file_path.parent.mkdir(parents=True, exist_ok=True)
                            no_exist_file_path.touch()
                        except OSError as e:
                            logger.error(
                                f"Could not cache non-existence of file. Will ignore error and continue. Error: {e}"
                            )
                        _cache_commit_hash_for_specific_revision(storage_folder, revision, commit_hash)
                raise

            # Commit hash must exist
            commit_hash = metadata.commit_hash
            if commit_hash is None:
                raise FileMetadataError(
                    "Distant resource does not seem to be on huggingface.co. It is possible that a configuration issue"
                    " prevents you from downloading resources from https://huggingface.co. Please check your firewall"
                    " and proxy settings and make sure your SSL certificates are updated."
                )

            # Etag must exist
            # If we don't have any of those, raise an error.
            etag = metadata.etag
            if etag is None:
                raise FileMetadataError(
                    "Distant resource does not have an ETag, we won't be able to reliably ensure reproducibility."
                )

            # Size must exist
            expected_size = metadata.size
            if expected_size is None:
                raise FileMetadataError("Distant resource does not have a Content-Length.")

            xet_file_data = metadata.xet_file_data

            # In case of a redirect, save an extra redirect on the request.get call,
            # and ensure we download the exact atomic version even if it changed
            # between the HEAD and the GET (unlikely, but hey).
            #
            # If url domain is different => we are downloading from a CDN => url is signed => don't send auth
            # If url domain is the same => redirect due to repo rename AND downloading a regular file => keep auth
            if xet_file_data is None and url != metadata.location:
                url_to_download = metadata.location
                if urlparse(url).netloc != urlparse(metadata.location).netloc:
                    # Remove authorization header when downloading a LFS blob
                    headers.pop("authorization", None)
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError):
            # Actually raise for those subclasses of ConnectionError
            raise
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            OfflineModeIsEnabled,
        ) as error:
            # Otherwise, our Internet connection is down.
            # etag is None
            head_error_call = error
        except (RevisionNotFoundError, EntryNotFoundError):
            # The repo was found but the revision or entry doesn't exist on the Hub (never existed or got deleted)
            raise
        except requests.HTTPError as error:
            # Multiple reasons for an http error:
            # - Repository is private and invalid/missing token sent
            # - Repository is gated and invalid/missing token sent
            # - Hub is down (error 500 or 504)
            # => let's switch to 'local_files_only=True' to check if the files are already cached.
            #    (if it's not the case, the error will be re-raised)
            head_error_call = error
        except FileMetadataError as error:
            # Multiple reasons for a FileMetadataError:
            # - Wrong network configuration (proxy, firewall, SSL certificates)
            # - Inconsistency on the Hub
            # => let's switch to 'local_files_only=True' to check if the files are already cached.
            #    (if it's not the case, the error will be re-raised)
            head_error_call = error

    if not (local_files_only or etag is not None or head_error_call is not None):
        raise RuntimeError("etag is empty due to uncovered problems")

    return (url_to_download, etag, commit_hash, expected_size, xet_file_data, head_error_call)  # type: ignore [return-value]


def _raise_on_head_call_error(head_call_error: Exception, force_download: bool, local_files_only: bool) -> NoReturn:
    """Raise an appropriate error when the HEAD call failed and we cannot locate a local file."""
    # No head call => we cannot force download.
    if force_download:
        if local_files_only:
            raise ValueError("Cannot pass 'force_download=True' and 'local_files_only=True' at the same time.")
        elif isinstance(head_call_error, OfflineModeIsEnabled):
            raise ValueError("Cannot pass 'force_download=True' when offline mode is enabled.") from head_call_error
        else:
            raise ValueError("Force download failed due to the above error.") from head_call_error

    # No head call + couldn't find an appropriate file on disk => raise an error.
    if local_files_only:
        raise LocalEntryNotFoundError(
            "Cannot find the requested files in the disk cache and outgoing traffic has been disabled. To enable"
            " hf.co look-ups and downloads online, set 'local_files_only' to False."
        )
    elif isinstance(head_call_error, (RepositoryNotFoundError, GatedRepoError)) or (
        isinstance(head_call_error, HfHubHTTPError) and head_call_error.response.status_code == 401
    ):
        # Repo not found or gated => let's raise the actual error
        # Unauthorized => likely a token issue => let's raise the actual error
        raise head_call_error
    else:
        # Otherwise: most likely a connection issue or Hub downtime => let's warn the user
        raise LocalEntryNotFoundError(
            "An error happened while trying to locate the file on the Hub and we cannot find the requested files"
            " in the local cache. Please check your connection and try again or make sure your Internet connection"
            " is on."
        ) from head_call_error


def _download_to_tmp_and_move(
    incomplete_path: Path,
    destination_path: Path,
    url_to_download: str,
    proxies: Optional[Dict],
    headers: Dict[str, str],
    expected_size: Optional[int],
    filename: str,
    force_download: bool,
    etag: Optional[str],
    xet_file_data: Optional[XetFileData],
) -> None:
    """Download content from a URL to a destination path.

    Internal logic:
    - return early if file is already downloaded
    - resume download if possible (from incomplete file)
    - do not resume download if `force_download=True` or `HF_HUB_ENABLE_HF_TRANSFER=True`
    - check disk space before downloading
    - download content to a temporary file
    - set correct permissions on temporary file
    - move the temporary file to the destination path

    Both `incomplete_path` and `destination_path` must be on the same volume to avoid a local copy.
    """
    if destination_path.exists() and not force_download:
        # Do nothing if already exists (except if force_download=True)
        return

    if incomplete_path.exists() and (force_download or (constants.HF_HUB_ENABLE_HF_TRANSFER and not proxies)):
        # By default, we will try to resume the download if possible.
        # However, if the user has set `force_download=True` or if `hf_transfer` is enabled, then we should
        # not resume the download => delete the incomplete file.
        message = f"Removing incomplete file '{incomplete_path}'"
        if force_download:
            message += " (force_download=True)"
        elif constants.HF_HUB_ENABLE_HF_TRANSFER and not proxies:
            message += " (hf_transfer=True)"
        logger.info(message)
        incomplete_path.unlink(missing_ok=True)

    with incomplete_path.open("ab") as f:
        resume_size = f.tell()
        message = f"Downloading '{filename}' to '{incomplete_path}'"
        if resume_size > 0 and expected_size is not None:
            message += f" (resume from {resume_size}/{expected_size})"
        logger.info(message)

        if expected_size is not None:  # might be None if HTTP header not set correctly
            # Check disk space in both tmp and destination path
            _check_disk_space(expected_size, incomplete_path.parent)
            _check_disk_space(expected_size, destination_path.parent)

        if xet_file_data is not None and is_xet_available():
            logger.debug("Xet Storage is enabled for this repo. Downloading file from Xet Storage..")
            xet_get(
                incomplete_path=incomplete_path,
                xet_file_data=xet_file_data,
                headers=headers,
                expected_size=expected_size,
                displayed_filename=filename,
            )
        else:
            if xet_file_data is not None:
                logger.warning(
                    "Xet Storage is enabled for this repo, but the 'hf_xet' package is not installed. "
                    "Falling back to regular HTTP download. "
                    "For better performance, install the package with: `pip install huggingface_hub[hf_xet]` or `pip install hf_xet`"
                )

            http_get(
                url_to_download,
                f,
                proxies=proxies,
                resume_size=resume_size,
                headers=headers,
                expected_size=expected_size,
            )

    logger.info(f"Download complete. Moving file to {destination_path}")
    _chmod_and_move(incomplete_path, destination_path)


def _int_or_none(value: Optional[str]) -> Optional[int]:
    try:
        return int(value)  # type: ignore
    except (TypeError, ValueError):
        return None


def _chmod_and_move(src: Path, dst: Path) -> None:
    """Set correct permission before moving a blob from tmp directory to cache dir.

    Do not take into account the `umask` from the process as there is no convenient way
    to get it that is thread-safe.

    See:
    - About umask: https://docs.python.org/3/library/os.html#os.umask
    - Thread-safety: https://stackoverflow.com/a/70343066
    - About solution: https://github.com/huggingface/huggingface_hub/pull/1220#issuecomment-1326211591
    - Fix issue: https://github.com/huggingface/huggingface_hub/issues/1141
    - Fix issue: https://github.com/huggingface/huggingface_hub/issues/1215
    """
    # Get umask by creating a temporary file in the cached repo folder.
    tmp_file = dst.parent.parent / f"tmp_{uuid.uuid4()}"
    try:
        tmp_file.touch()
        cache_dir_mode = Path(tmp_file).stat().st_mode
        os.chmod(str(src), stat.S_IMODE(cache_dir_mode))
    except OSError as e:
        logger.warning(
            f"Could not set the permissions on the file '{src}'. Error: {e}.\nContinuing without setting permissions."
        )
    finally:
        try:
            tmp_file.unlink()
        except OSError:
            # fails if `tmp_file.touch()` failed => do nothing
            # See https://github.com/huggingface/huggingface_hub/issues/2359
            pass

    shutil.move(str(src), str(dst), copy_function=_copy_no_matter_what)


def _copy_no_matter_what(src: str, dst: str) -> None:
    """Copy file from src to dst.

    If `shutil.copy2` fails, fallback to `shutil.copyfile`.
    """
    try:
        # Copy file with metadata and permission
        # Can fail e.g. if dst is an S3 mount
        shutil.copy2(src, dst)
    except OSError:
        # Copy only file content
        shutil.copyfile(src, dst)


def _get_pointer_path(storage_folder: str, revision: str, relative_filename: str) -> str:
    # Using `os.path.abspath` instead of `Path.resolve()` to avoid resolving symlinks
    snapshot_path = os.path.join(storage_folder, "snapshots")
    pointer_path = os.path.join(snapshot_path, revision, relative_filename)
    if Path(os.path.abspath(snapshot_path)) not in Path(os.path.abspath(pointer_path)).parents:
        raise ValueError(
            "Invalid pointer path: cannot create pointer path in snapshot folder if"
            f" `storage_folder='{storage_folder}'`, `revision='{revision}'` and"
            f" `relative_filename='{relative_filename}'`."
        )
    return pointer_path