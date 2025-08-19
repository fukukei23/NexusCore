
# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\combined_11.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_scimath_impl.py ===
"""
Wrapper functions to more user-friendly calling of certain math functions
whose output data-type is different than the input data-type in certain
domains of the input.

For example, for functions like `log` with branch cuts, the versions in this
module provide the mathematically valid answers in the complex plane::

  >>> import math
  >>> np.emath.log(-math.exp(1)) == (1+1j*math.pi)
  True

Similarly, `sqrt`, other base logarithms, `power` and trig functions are
correctly handled.  See their respective docstrings for specific examples.

"""
import numpy._core.numeric as nx
import numpy._core.numerictypes as nt
from numpy._core.numeric import any, asarray
from numpy._core.overrides import array_function_dispatch, set_module
from numpy.lib._type_check_impl import isreal

__all__ = [
    'sqrt', 'log', 'log2', 'logn', 'log10', 'power', 'arccos', 'arcsin',
    'arctanh'
    ]


_ln2 = nx.log(2.0)


def _tocomplex(arr):
    """Convert its input `arr` to a complex array.

    The input is returned as a complex array of the smallest type that will fit
    the original data: types like single, byte, short, etc. become csingle,
    while others become cdouble.

    A copy of the input is always made.

    Parameters
    ----------
    arr : array

    Returns
    -------
    array
        An array with the same input data as the input but in complex form.

    Examples
    --------
    >>> import numpy as np

    First, consider an input of type short:

    >>> a = np.array([1,2,3],np.short)

    >>> ac = np.lib.scimath._tocomplex(a); ac
    array([1.+0.j, 2.+0.j, 3.+0.j], dtype=complex64)

    >>> ac.dtype
    dtype('complex64')

    If the input is of type double, the output is correspondingly of the
    complex double type as well:

    >>> b = np.array([1,2,3],np.double)

    >>> bc = np.lib.scimath._tocomplex(b); bc
    array([1.+0.j, 2.+0.j, 3.+0.j])

    >>> bc.dtype
    dtype('complex128')

    Note that even if the input was complex to begin with, a copy is still
    made, since the astype() method always copies:

    >>> c = np.array([1,2,3],np.csingle)

    >>> cc = np.lib.scimath._tocomplex(c); cc
    array([1.+0.j,  2.+0.j,  3.+0.j], dtype=complex64)

    >>> c *= 2; c
    array([2.+0.j,  4.+0.j,  6.+0.j], dtype=complex64)

    >>> cc
    array([1.+0.j,  2.+0.j,  3.+0.j], dtype=complex64)
    """
    if issubclass(arr.dtype.type, (nt.single, nt.byte, nt.short, nt.ubyte,
                                   nt.ushort, nt.csingle)):
        return arr.astype(nt.csingle)
    else:
        return arr.astype(nt.cdouble)


def _fix_real_lt_zero(x):
    """Convert `x` to complex if it has real, negative components.

    Otherwise, output is just the array version of the input (via asarray).

    Parameters
    ----------
    x : array_like

    Returns
    -------
    array

    Examples
    --------
    >>> import numpy as np
    >>> np.lib.scimath._fix_real_lt_zero([1,2])
    array([1, 2])

    >>> np.lib.scimath._fix_real_lt_zero([-1,2])
    array([-1.+0.j,  2.+0.j])

    """
    x = asarray(x)
    if any(isreal(x) & (x < 0)):
        x = _tocomplex(x)
    return x


def _fix_int_lt_zero(x):
    """Convert `x` to double if it has real, negative components.

    Otherwise, output is just the array version of the input (via asarray).

    Parameters
    ----------
    x : array_like

    Returns
    -------
    array

    Examples
    --------
    >>> import numpy as np
    >>> np.lib.scimath._fix_int_lt_zero([1,2])
    array([1, 2])

    >>> np.lib.scimath._fix_int_lt_zero([-1,2])
    array([-1.,  2.])
    """
    x = asarray(x)
    if any(isreal(x) & (x < 0)):
        x = x * 1.0
    return x


def _fix_real_abs_gt_1(x):
    """Convert `x` to complex if it has real components x_i with abs(x_i)>1.

    Otherwise, output is just the array version of the input (via asarray).

    Parameters
    ----------
    x : array_like

    Returns
    -------
    array

    Examples
    --------
    >>> import numpy as np
    >>> np.lib.scimath._fix_real_abs_gt_1([0,1])
    array([0, 1])

    >>> np.lib.scimath._fix_real_abs_gt_1([0,2])
    array([0.+0.j, 2.+0.j])
    """
    x = asarray(x)
    if any(isreal(x) & (abs(x) > 1)):
        x = _tocomplex(x)
    return x


def _unary_dispatcher(x):
    return (x,)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_unary_dispatcher)
def sqrt(x):
    """
    Compute the square root of x.

    For negative input elements, a complex value is returned
    (unlike `numpy.sqrt` which returns NaN).

    Parameters
    ----------
    x : array_like
       The input value(s).

    Returns
    -------
    out : ndarray or scalar
       The square root of `x`. If `x` was a scalar, so is `out`,
       otherwise an array is returned.

    See Also
    --------
    numpy.sqrt

    Examples
    --------
    For real, non-negative inputs this works just like `numpy.sqrt`:

    >>> import numpy as np

    >>> np.emath.sqrt(1)
    1.0
    >>> np.emath.sqrt([1, 4])
    array([1.,  2.])

    But it automatically handles negative inputs:

    >>> np.emath.sqrt(-1)
    1j
    >>> np.emath.sqrt([-1,4])
    array([0.+1.j, 2.+0.j])

    Different results are expected because:
    floating point 0.0 and -0.0 are distinct.

    For more control, explicitly use complex() as follows:

    >>> np.emath.sqrt(complex(-4.0, 0.0))
    2j
    >>> np.emath.sqrt(complex(-4.0, -0.0))
    -2j
    """
    x = _fix_real_lt_zero(x)
    return nx.sqrt(x)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_unary_dispatcher)
def log(x):
    """
    Compute the natural logarithm of `x`.

    Return the "principal value" (for a description of this, see `numpy.log`)
    of :math:`log_e(x)`. For real `x > 0`, this is a real number (``log(0)``
    returns ``-inf`` and ``log(np.inf)`` returns ``inf``). Otherwise, the
    complex principle value is returned.

    Parameters
    ----------
    x : array_like
       The value(s) whose log is (are) required.

    Returns
    -------
    out : ndarray or scalar
       The log of the `x` value(s). If `x` was a scalar, so is `out`,
       otherwise an array is returned.

    See Also
    --------
    numpy.log

    Notes
    -----
    For a log() that returns ``NAN`` when real `x < 0`, use `numpy.log`
    (note, however, that otherwise `numpy.log` and this `log` are identical,
    i.e., both return ``-inf`` for `x = 0`, ``inf`` for `x = inf`, and,
    notably, the complex principle value if ``x.imag != 0``).

    Examples
    --------
    >>> import numpy as np
    >>> np.emath.log(np.exp(1))
    1.0

    Negative arguments are handled "correctly" (recall that
    ``exp(log(x)) == x`` does *not* hold for real ``x < 0``):

    >>> np.emath.log(-np.exp(1)) == (1 + np.pi * 1j)
    True

    """
    x = _fix_real_lt_zero(x)
    return nx.log(x)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_unary_dispatcher)
def log10(x):
    """
    Compute the logarithm base 10 of `x`.

    Return the "principal value" (for a description of this, see
    `numpy.log10`) of :math:`log_{10}(x)`. For real `x > 0`, this
    is a real number (``log10(0)`` returns ``-inf`` and ``log10(np.inf)``
    returns ``inf``). Otherwise, the complex principle value is returned.

    Parameters
    ----------
    x : array_like or scalar
       The value(s) whose log base 10 is (are) required.

    Returns
    -------
    out : ndarray or scalar
       The log base 10 of the `x` value(s). If `x` was a scalar, so is `out`,
       otherwise an array object is returned.

    See Also
    --------
    numpy.log10

    Notes
    -----
    For a log10() that returns ``NAN`` when real `x < 0`, use `numpy.log10`
    (note, however, that otherwise `numpy.log10` and this `log10` are
    identical, i.e., both return ``-inf`` for `x = 0`, ``inf`` for `x = inf`,
    and, notably, the complex principle value if ``x.imag != 0``).

    Examples
    --------
    >>> import numpy as np

    (We set the printing precision so the example can be auto-tested)

    >>> np.set_printoptions(precision=4)

    >>> np.emath.log10(10**1)
    1.0

    >>> np.emath.log10([-10**1, -10**2, 10**2])
    array([1.+1.3644j, 2.+1.3644j, 2.+0.j    ])

    """
    x = _fix_real_lt_zero(x)
    return nx.log10(x)


def _logn_dispatcher(n, x):
    return (n, x,)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_logn_dispatcher)
def logn(n, x):
    """
    Take log base n of x.

    If `x` contains negative inputs, the answer is computed and returned in the
    complex domain.

    Parameters
    ----------
    n : array_like
       The integer base(s) in which the log is taken.
    x : array_like
       The value(s) whose log base `n` is (are) required.

    Returns
    -------
    out : ndarray or scalar
       The log base `n` of the `x` value(s). If `x` was a scalar, so is
       `out`, otherwise an array is returned.

    Examples
    --------
    >>> import numpy as np
    >>> np.set_printoptions(precision=4)

    >>> np.emath.logn(2, [4, 8])
    array([2., 3.])
    >>> np.emath.logn(2, [-4, -8, 8])
    array([2.+4.5324j, 3.+4.5324j, 3.+0.j    ])

    """
    x = _fix_real_lt_zero(x)
    n = _fix_real_lt_zero(n)
    return nx.log(x) / nx.log(n)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_unary_dispatcher)
def log2(x):
    """
    Compute the logarithm base 2 of `x`.

    Return the "principal value" (for a description of this, see
    `numpy.log2`) of :math:`log_2(x)`. For real `x > 0`, this is
    a real number (``log2(0)`` returns ``-inf`` and ``log2(np.inf)`` returns
    ``inf``). Otherwise, the complex principle value is returned.

    Parameters
    ----------
    x : array_like
       The value(s) whose log base 2 is (are) required.

    Returns
    -------
    out : ndarray or scalar
       The log base 2 of the `x` value(s). If `x` was a scalar, so is `out`,
       otherwise an array is returned.

    See Also
    --------
    numpy.log2

    Notes
    -----
    For a log2() that returns ``NAN`` when real `x < 0`, use `numpy.log2`
    (note, however, that otherwise `numpy.log2` and this `log2` are
    identical, i.e., both return ``-inf`` for `x = 0`, ``inf`` for `x = inf`,
    and, notably, the complex principle value if ``x.imag != 0``).

    Examples
    --------

    We set the printing precision so the example can be auto-tested:

    >>> np.set_printoptions(precision=4)

    >>> np.emath.log2(8)
    3.0
    >>> np.emath.log2([-4, -8, 8])
    array([2.+4.5324j, 3.+4.5324j, 3.+0.j    ])

    """
    x = _fix_real_lt_zero(x)
    return nx.log2(x)


def _power_dispatcher(x, p):
    return (x, p)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_power_dispatcher)
def power(x, p):
    """
    Return x to the power p, (x**p).

    If `x` contains negative values, the output is converted to the
    complex domain.

    Parameters
    ----------
    x : array_like
        The input value(s).
    p : array_like of ints
        The power(s) to which `x` is raised. If `x` contains multiple values,
        `p` has to either be a scalar, or contain the same number of values
        as `x`. In the latter case, the result is
        ``x[0]**p[0], x[1]**p[1], ...``.

    Returns
    -------
    out : ndarray or scalar
        The result of ``x**p``. If `x` and `p` are scalars, so is `out`,
        otherwise an array is returned.

    See Also
    --------
    numpy.power

    Examples
    --------
    >>> import numpy as np
    >>> np.set_printoptions(precision=4)

    >>> np.emath.power(2, 2)
    4

    >>> np.emath.power([2, 4], 2)
    array([ 4, 16])

    >>> np.emath.power([2, 4], -2)
    array([0.25  ,  0.0625])

    >>> np.emath.power([-2, 4], 2)
    array([ 4.-0.j, 16.+0.j])

    >>> np.emath.power([2, 4], [2, 4])
    array([ 4, 256])

    """
    x = _fix_real_lt_zero(x)
    p = _fix_int_lt_zero(p)
    return nx.power(x, p)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_unary_dispatcher)
def arccos(x):
    """
    Compute the inverse cosine of x.

    Return the "principal value" (for a description of this, see
    `numpy.arccos`) of the inverse cosine of `x`. For real `x` such that
    `abs(x) <= 1`, this is a real number in the closed interval
    :math:`[0, \\pi]`.  Otherwise, the complex principle value is returned.

    Parameters
    ----------
    x : array_like or scalar
       The value(s) whose arccos is (are) required.

    Returns
    -------
    out : ndarray or scalar
       The inverse cosine(s) of the `x` value(s). If `x` was a scalar, so
       is `out`, otherwise an array object is returned.

    See Also
    --------
    numpy.arccos

    Notes
    -----
    For an arccos() that returns ``NAN`` when real `x` is not in the
    interval ``[-1,1]``, use `numpy.arccos`.

    Examples
    --------
    >>> import numpy as np
    >>> np.set_printoptions(precision=4)

    >>> np.emath.arccos(1) # a scalar is returned
    0.0

    >>> np.emath.arccos([1,2])
    array([0.-0.j   , 0.-1.317j])

    """
    x = _fix_real_abs_gt_1(x)
    return nx.arccos(x)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_unary_dispatcher)
def arcsin(x):
    """
    Compute the inverse sine of x.

    Return the "principal value" (for a description of this, see
    `numpy.arcsin`) of the inverse sine of `x`. For real `x` such that
    `abs(x) <= 1`, this is a real number in the closed interval
    :math:`[-\\pi/2, \\pi/2]`.  Otherwise, the complex principle value is
    returned.

    Parameters
    ----------
    x : array_like or scalar
       The value(s) whose arcsin is (are) required.

    Returns
    -------
    out : ndarray or scalar
       The inverse sine(s) of the `x` value(s). If `x` was a scalar, so
       is `out`, otherwise an array object is returned.

    See Also
    --------
    numpy.arcsin

    Notes
    -----
    For an arcsin() that returns ``NAN`` when real `x` is not in the
    interval ``[-1,1]``, use `numpy.arcsin`.

    Examples
    --------
    >>> import numpy as np
    >>> np.set_printoptions(precision=4)

    >>> np.emath.arcsin(0)
    0.0

    >>> np.emath.arcsin([0,1])
    array([0.    , 1.5708])

    """
    x = _fix_real_abs_gt_1(x)
    return nx.arcsin(x)


@set_module('numpy.lib.scimath')
@array_function_dispatch(_unary_dispatcher)
def arctanh(x):
    """
    Compute the inverse hyperbolic tangent of `x`.

    Return the "principal value" (for a description of this, see
    `numpy.arctanh`) of ``arctanh(x)``. For real `x` such that
    ``abs(x) < 1``, this is a real number.  If `abs(x) > 1`, or if `x` is
    complex, the result is complex. Finally, `x = 1` returns``inf`` and
    ``x=-1`` returns ``-inf``.

    Parameters
    ----------
    x : array_like
       The value(s) whose arctanh is (are) required.

    Returns
    -------
    out : ndarray or scalar
       The inverse hyperbolic tangent(s) of the `x` value(s). If `x` was
       a scalar so is `out`, otherwise an array is returned.


    See Also
    --------
    numpy.arctanh

    Notes
    -----
    For an arctanh() that returns ``NAN`` when real `x` is not in the
    interval ``(-1,1)``, use `numpy.arctanh` (this latter, however, does
    return +/-inf for ``x = +/-1``).

    Examples
    --------
    >>> import numpy as np
    >>> np.set_printoptions(precision=4)

    >>> np.emath.arctanh(0.5)
    0.5493061443340549

    >>> from numpy.testing import suppress_warnings
    >>> with suppress_warnings() as sup:
    ...     sup.filter(RuntimeWarning)
    ...     np.emath.arctanh(np.eye(2))
    array([[inf,  0.],
           [ 0., inf]])
    >>> np.emath.arctanh([1j])
    array([0.+0.7854j])

    """
    x = _fix_real_abs_gt_1(x)
    return nx.arctanh(x)

# === NexusCore/src\sandbox_logs\repair_20250713_132959_fixed.py ===
このエラーは、Pythonコードが日本語で書かれているために発生しています。Pythonは日本語のコメント以外を解釈できません。そのため、日本語で書かれたコードを英語に置き換える必要があります。ただし、元のコードが何をするものだったのかが不明なため、具体的な修正案を提案することはできません。

ただし、エラーメッセージから推測すると、おそらくユニットテストを書こうとしていた可能性があります。その場合、以下のような形式で書くことが一般的です。

```python
import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)

if __name__ == '__main__':
    unittest.main()
```

このコードは、add関数が正しく動作することを確認するユニットテストを含んでいます。

# === NexusCore/src\sandbox_logs\repair_20250713_133018_fixed.py ===
申し訳ありませんが、元のコードが見えないため、具体的な修正案を提案することはできません。ただし、エラーメッセージから推測すると、Pythonコードが日本語で書かれているためにエラーが発生しているようです。Pythonは日本語のコメント以外を解釈できません。そのため、日本語で書かれたコードを英語に置き換える必要があります。

また、エラーメッセージからは、ユニットテストを書こうとしていたことが推測できます。その場合、以下のような形式で書くことが一般的です。

```python
import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)

if __name__ == '__main__':
    unittest.main()
```

このコードは、add関数が正しく動作することを確認するユニットテストを含んでいます。

# === NexusCore/src\sandbox_logs\repair_20250713_133018_original.py ===
このエラーは、Pythonコードが日本語で書かれているために発生しています。Pythonは日本語のコメント以外を解釈できません。そのため、日本語で書かれたコードを英語に置き換える必要があります。ただし、元のコードが何をするものだったのかが不明なため、具体的な修正案を提案することはできません。

ただし、エラーメッセージから推測すると、おそらくユニットテストを書こうとしていた可能性があります。その場合、以下のような形式で書くことが一般的です。

```python
import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)

if __name__ == '__main__':
    unittest.main()
```

このコードは、add関数が正しく動作することを確認するユニットテストを含んでいます。

# === NexusCore/src\sandbox_logs\repair_20250713_133036_fixed.py ===
申し訳ありませんが、エラーメッセージからは具体的な修正案を提案することが難しいです。ただし、エラーメッセージから推測すると、Pythonコードが日本語で書かれているためにエラーが発生しているようです。Pythonは日本語のコメント以外を解釈できません。そのため、日本語で書かれたコードを英語に置き換える必要があります。

また、エラーメッセージからは、ユニットテストを書こうとしていたことが推測できます。その場合、以下のような形式で書くことが一般的です。

```python
import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)

if __name__ == '__main__':
    unittest.main()
```

このコードは、add関数が正しく動作することを確認するユニットテストを含んでいます。

# === NexusCore/src\sandbox_logs\repair_20250713_133036_original.py ===
申し訳ありませんが、元のコードが見えないため、具体的な修正案を提案することはできません。ただし、エラーメッセージから推測すると、Pythonコードが日本語で書かれているためにエラーが発生しているようです。Pythonは日本語のコメント以外を解釈できません。そのため、日本語で書かれたコードを英語に置き換える必要があります。

また、エラーメッセージからは、ユニットテストを書こうとしていたことが推測できます。その場合、以下のような形式で書くことが一般的です。

```python
import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)

if __name__ == '__main__':
    unittest.main()
```

このコードは、add関数が正しく動作することを確認するユニットテストを含んでいます。

# === NexusCore/src\sandbox_logs\repair_20250713_134201_fixed.py ===
```python
# 以下のように、pytest形式のユニットテストを生成します。
def add(a, b):
    return a + b
```

エラーメッセージによると、Pythonのコード中に無効な文字 '、' (U+3001)が存在しています。しかし、提供されたコードにはそのような文字は存在していません。したがって、エラーはコメント部分に由来している可能性が高いです。

Pythonのコメントは英語を基本としており、一部の非ASCII文字はサポートされていません。このエラーは、コメント内の日本語の句読点 '、' が原因である可能性があります。

したがって、コメントを英語に変更することでエラーを解消できます。以下に修正後のコードを示します。

```python
# Generate unit tests in pytest format as follows.
def add(a, b):
    return a + b
```

なお、このエラーが発生した環境が日本語を完全にサポートしていない可能性もあります。その場合、日本語のコメントを全て英語に変更するか、非ASCII文字を含まないようにする必要があります。

# === NexusCore/src\utils\diff_tools.py ===
# 📁 ファイル名: diff_tools.py
# 📂 保存先: /src/utils/diff_tools.py

from difflib import unified_diff

def generate_diff_report(original: str, modified: str) -> str:
    diff = unified_diff(
        original.splitlines(),
        modified.splitlines(),
        fromfile="Original",
        tofile="Modified",
        lineterm=""
    )
    return "\n".join(diff)

def score_code_improvement(original: str, modified: str) -> float:
    orig_lines = len(original.strip().splitlines())
    mod_lines = len(modified.strip().splitlines())
    return round((mod_lines - orig_lines) / max(orig_lines, 1), 2)

# === NexusCore/openenv\Lib\site-packages\openai\lib\azure.py ===
from __future__ import annotations

import os
import inspect
from typing import Any, Union, Mapping, TypeVar, Callable, Awaitable, cast, overload
from typing_extensions import Self, override

import httpx

from .._types import NOT_GIVEN, Omit, Query, Timeout, NotGiven
from .._utils import is_given, is_mapping
from .._client import OpenAI, AsyncOpenAI
from .._compat import model_copy
from .._models import FinalRequestOptions
from .._streaming import Stream, AsyncStream
from .._exceptions import OpenAIError
from .._base_client import DEFAULT_MAX_RETRIES, BaseClient

_deployments_endpoints = set(
    [
        "/completions",
        "/chat/completions",
        "/embeddings",
        "/audio/transcriptions",
        "/audio/translations",
        "/audio/speech",
        "/images/generations",
        "/images/edits",
    ]
)


AzureADTokenProvider = Callable[[], str]
AsyncAzureADTokenProvider = Callable[[], "str | Awaitable[str]"]
_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


# we need to use a sentinel API key value for Azure AD
# as we don't want to make the `api_key` in the main client Optional
# and Azure AD tokens may be retrieved on a per-request basis
API_KEY_SENTINEL = "".join(["<", "missing API key", ">"])


class MutuallyExclusiveAuthError(OpenAIError):
    def __init__(self) -> None:
        super().__init__(
            "The `api_key`, `azure_ad_token` and `azure_ad_token_provider` arguments are mutually exclusive; Only one can be passed at a time"
        )


class BaseAzureClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    _azure_endpoint: httpx.URL | None
    _azure_deployment: str | None

    @override
    def _build_request(
        self,
        options: FinalRequestOptions,
        *,
        retries_taken: int = 0,
    ) -> httpx.Request:
        if options.url in _deployments_endpoints and is_mapping(options.json_data):
            model = options.json_data.get("model")
            if model is not None and "/deployments" not in str(self.base_url.path):
                options.url = f"/deployments/{model}{options.url}"

        return super()._build_request(options, retries_taken=retries_taken)

    @override
    def _prepare_url(self, url: str) -> httpx.URL:
        """Adjust the URL if the client was configured with an Azure endpoint + deployment
        and the API feature being called is **not** a deployments-based endpoint
        (i.e. requires /deployments/deployment-name in the URL path).
        """
        if self._azure_deployment and self._azure_endpoint and url not in _deployments_endpoints:
            merge_url = httpx.URL(url)
            if merge_url.is_relative_url:
                merge_raw_path = (
                    self._azure_endpoint.raw_path.rstrip(b"/") + b"/openai/" + merge_url.raw_path.lstrip(b"/")
                )
                return self._azure_endpoint.copy_with(raw_path=merge_raw_path)

            return merge_url

        return super()._prepare_url(url)


class AzureOpenAI(BaseAzureClient[httpx.Client, Stream[Any]], OpenAI):
    @overload
    def __init__(
        self,
        *,
        azure_endpoint: str,
        azure_deployment: str | None = None,
        api_version: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AzureADTokenProvider | None = None,
        organization: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.Client | None = None,
        _strict_response_validation: bool = False,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        azure_deployment: str | None = None,
        api_version: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AzureADTokenProvider | None = None,
        organization: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.Client | None = None,
        _strict_response_validation: bool = False,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        base_url: str,
        api_version: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AzureADTokenProvider | None = None,
        organization: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.Client | None = None,
        _strict_response_validation: bool = False,
    ) -> None: ...

    def __init__(
        self,
        *,
        api_version: str | None = None,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AzureADTokenProvider | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        base_url: str | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.Client | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new synchronous azure openai client instance.

        This automatically infers the following arguments from their corresponding environment variables if they are not provided:
        - `api_key` from `AZURE_OPENAI_API_KEY`
        - `organization` from `OPENAI_ORG_ID`
        - `project` from `OPENAI_PROJECT_ID`
        - `azure_ad_token` from `AZURE_OPENAI_AD_TOKEN`
        - `api_version` from `OPENAI_API_VERSION`
        - `azure_endpoint` from `AZURE_OPENAI_ENDPOINT`

        Args:
            azure_endpoint: Your Azure endpoint, including the resource, e.g. `https://example-resource.azure.openai.com/`

            azure_ad_token: Your Azure Active Directory token, https://www.microsoft.com/en-us/security/business/identity-access/microsoft-entra-id

            azure_ad_token_provider: A function that returns an Azure Active Directory token, will be invoked on every request.

            azure_deployment: A model deployment, if given with `azure_endpoint`, sets the base client URL to include `/deployments/{azure_deployment}`.
                Not supported with Assistants APIs.
        """
        if api_key is None:
            api_key = os.environ.get("AZURE_OPENAI_API_KEY")

        if azure_ad_token is None:
            azure_ad_token = os.environ.get("AZURE_OPENAI_AD_TOKEN")

        if api_key is None and azure_ad_token is None and azure_ad_token_provider is None:
            raise OpenAIError(
                "Missing credentials. Please pass one of `api_key`, `azure_ad_token`, `azure_ad_token_provider`, or the `AZURE_OPENAI_API_KEY` or `AZURE_OPENAI_AD_TOKEN` environment variables."
            )

        if api_version is None:
            api_version = os.environ.get("OPENAI_API_VERSION")

        if api_version is None:
            raise ValueError(
                "Must provide either the `api_version` argument or the `OPENAI_API_VERSION` environment variable"
            )

        if default_query is None:
            default_query = {"api-version": api_version}
        else:
            default_query = {**default_query, "api-version": api_version}

        if base_url is None:
            if azure_endpoint is None:
                azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")

            if azure_endpoint is None:
                raise ValueError(
                    "Must provide one of the `base_url` or `azure_endpoint` arguments, or the `AZURE_OPENAI_ENDPOINT` environment variable"
                )

            if azure_deployment is not None:
                base_url = f"{azure_endpoint.rstrip('/')}/openai/deployments/{azure_deployment}"
            else:
                base_url = f"{azure_endpoint.rstrip('/')}/openai"
        else:
            if azure_endpoint is not None:
                raise ValueError("base_url and azure_endpoint are mutually exclusive")

        if api_key is None:
            # define a sentinel value to avoid any typing issues
            api_key = API_KEY_SENTINEL

        super().__init__(
            api_key=api_key,
            organization=organization,
            project=project,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            default_query=default_query,
            http_client=http_client,
            websocket_base_url=websocket_base_url,
            _strict_response_validation=_strict_response_validation,
        )
        self._api_version = api_version
        self._azure_ad_token = azure_ad_token
        self._azure_ad_token_provider = azure_ad_token_provider
        self._azure_deployment = azure_deployment if azure_endpoint else None
        self._azure_endpoint = httpx.URL(azure_endpoint) if azure_endpoint else None

    @override
    def copy(
        self,
        *,
        api_key: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        api_version: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AzureADTokenProvider | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        return super().copy(
            api_key=api_key,
            organization=organization,
            project=project,
            websocket_base_url=websocket_base_url,
            base_url=base_url,
            timeout=timeout,
            http_client=http_client,
            max_retries=max_retries,
            default_headers=default_headers,
            set_default_headers=set_default_headers,
            default_query=default_query,
            set_default_query=set_default_query,
            _extra_kwargs={
                "api_version": api_version or self._api_version,
                "azure_ad_token": azure_ad_token or self._azure_ad_token,
                "azure_ad_token_provider": azure_ad_token_provider or self._azure_ad_token_provider,
                **_extra_kwargs,
            },
        )

    with_options = copy

    def _get_azure_ad_token(self) -> str | None:
        if self._azure_ad_token is not None:
            return self._azure_ad_token

        provider = self._azure_ad_token_provider
        if provider is not None:
            token = provider()
            if not token or not isinstance(token, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise ValueError(
                    f"Expected `azure_ad_token_provider` argument to return a string but it returned {token}",
                )
            return token

        return None

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        headers: dict[str, str | Omit] = {**options.headers} if is_given(options.headers) else {}

        options = model_copy(options)
        options.headers = headers

        azure_ad_token = self._get_azure_ad_token()
        if azure_ad_token is not None:
            if headers.get("Authorization") is None:
                headers["Authorization"] = f"Bearer {azure_ad_token}"
        elif self.api_key is not API_KEY_SENTINEL:
            if headers.get("api-key") is None:
                headers["api-key"] = self.api_key
        else:
            # should never be hit
            raise ValueError("Unable to handle auth")

        return options

    def _configure_realtime(self, model: str, extra_query: Query) -> tuple[httpx.URL, dict[str, str]]:
        auth_headers = {}
        query = {
            **extra_query,
            "api-version": self._api_version,
            "deployment": self._azure_deployment or model,
        }
        if self.api_key != "<missing API key>":
            auth_headers = {"api-key": self.api_key}
        else:
            token = self._get_azure_ad_token()
            if token:
                auth_headers = {"Authorization": f"Bearer {token}"}

        if self.websocket_base_url is not None:
            base_url = httpx.URL(self.websocket_base_url)
            merge_raw_path = base_url.raw_path.rstrip(b"/") + b"/realtime"
            realtime_url = base_url.copy_with(raw_path=merge_raw_path)
        else:
            base_url = self._prepare_url("/realtime")
            realtime_url = base_url.copy_with(scheme="wss")

        url = realtime_url.copy_with(params={**query})
        return url, auth_headers


class AsyncAzureOpenAI(BaseAzureClient[httpx.AsyncClient, AsyncStream[Any]], AsyncOpenAI):
    @overload
    def __init__(
        self,
        *,
        azure_endpoint: str,
        azure_deployment: str | None = None,
        api_version: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AsyncAzureADTokenProvider | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.AsyncClient | None = None,
        _strict_response_validation: bool = False,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        azure_deployment: str | None = None,
        api_version: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AsyncAzureADTokenProvider | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.AsyncClient | None = None,
        _strict_response_validation: bool = False,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        base_url: str,
        api_version: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AsyncAzureADTokenProvider | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.AsyncClient | None = None,
        _strict_response_validation: bool = False,
    ) -> None: ...

    def __init__(
        self,
        *,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        api_version: str | None = None,
        api_key: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AsyncAzureADTokenProvider | None = None,
        organization: str | None = None,
        project: str | None = None,
        base_url: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        http_client: httpx.AsyncClient | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new asynchronous azure openai client instance.

        This automatically infers the following arguments from their corresponding environment variables if they are not provided:
        - `api_key` from `AZURE_OPENAI_API_KEY`
        - `organization` from `OPENAI_ORG_ID`
        - `project` from `OPENAI_PROJECT_ID`
        - `azure_ad_token` from `AZURE_OPENAI_AD_TOKEN`
        - `api_version` from `OPENAI_API_VERSION`
        - `azure_endpoint` from `AZURE_OPENAI_ENDPOINT`

        Args:
            azure_endpoint: Your Azure endpoint, including the resource, e.g. `https://example-resource.azure.openai.com/`

            azure_ad_token: Your Azure Active Directory token, https://www.microsoft.com/en-us/security/business/identity-access/microsoft-entra-id

            azure_ad_token_provider: A function that returns an Azure Active Directory token, will be invoked on every request.

            azure_deployment: A model deployment, if given with `azure_endpoint`, sets the base client URL to include `/deployments/{azure_deployment}`.
                Not supported with Assistants APIs.
        """
        if api_key is None:
            api_key = os.environ.get("AZURE_OPENAI_API_KEY")

        if azure_ad_token is None:
            azure_ad_token = os.environ.get("AZURE_OPENAI_AD_TOKEN")

        if api_key is None and azure_ad_token is None and azure_ad_token_provider is None:
            raise OpenAIError(
                "Missing credentials. Please pass one of `api_key`, `azure_ad_token`, `azure_ad_token_provider`, or the `AZURE_OPENAI_API_KEY` or `AZURE_OPENAI_AD_TOKEN` environment variables."
            )

        if api_version is None:
            api_version = os.environ.get("OPENAI_API_VERSION")

        if api_version is None:
            raise ValueError(
                "Must provide either the `api_version` argument or the `OPENAI_API_VERSION` environment variable"
            )

        if default_query is None:
            default_query = {"api-version": api_version}
        else:
            default_query = {**default_query, "api-version": api_version}

        if base_url is None:
            if azure_endpoint is None:
                azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")

            if azure_endpoint is None:
                raise ValueError(
                    "Must provide one of the `base_url` or `azure_endpoint` arguments, or the `AZURE_OPENAI_ENDPOINT` environment variable"
                )

            if azure_deployment is not None:
                base_url = f"{azure_endpoint.rstrip('/')}/openai/deployments/{azure_deployment}"
            else:
                base_url = f"{azure_endpoint.rstrip('/')}/openai"
        else:
            if azure_endpoint is not None:
                raise ValueError("base_url and azure_endpoint are mutually exclusive")

        if api_key is None:
            # define a sentinel value to avoid any typing issues
            api_key = API_KEY_SENTINEL

        super().__init__(
            api_key=api_key,
            organization=organization,
            project=project,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            default_query=default_query,
            http_client=http_client,
            websocket_base_url=websocket_base_url,
            _strict_response_validation=_strict_response_validation,
        )
        self._api_version = api_version
        self._azure_ad_token = azure_ad_token
        self._azure_ad_token_provider = azure_ad_token_provider
        self._azure_deployment = azure_deployment if azure_endpoint else None
        self._azure_endpoint = httpx.URL(azure_endpoint) if azure_endpoint else None

    @override
    def copy(
        self,
        *,
        api_key: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        api_version: str | None = None,
        azure_ad_token: str | None = None,
        azure_ad_token_provider: AsyncAzureADTokenProvider | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        return super().copy(
            api_key=api_key,
            organization=organization,
            project=project,
            websocket_base_url=websocket_base_url,
            base_url=base_url,
            timeout=timeout,
            http_client=http_client,
            max_retries=max_retries,
            default_headers=default_headers,
            set_default_headers=set_default_headers,
            default_query=default_query,
            set_default_query=set_default_query,
            _extra_kwargs={
                "api_version": api_version or self._api_version,
                "azure_ad_token": azure_ad_token or self._azure_ad_token,
                "azure_ad_token_provider": azure_ad_token_provider or self._azure_ad_token_provider,
                **_extra_kwargs,
            },
        )

    with_options = copy

    async def _get_azure_ad_token(self) -> str | None:
        if self._azure_ad_token is not None:
            return self._azure_ad_token

        provider = self._azure_ad_token_provider
        if provider is not None:
            token = provider()
            if inspect.isawaitable(token):
                token = await token
            if not token or not isinstance(cast(Any, token), str):
                raise ValueError(
                    f"Expected `azure_ad_token_provider` argument to return a string but it returned {token}",
                )
            return str(token)

        return None

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        headers: dict[str, str | Omit] = {**options.headers} if is_given(options.headers) else {}

        options = model_copy(options)
        options.headers = headers

        azure_ad_token = await self._get_azure_ad_token()
        if azure_ad_token is not None:
            if headers.get("Authorization") is None:
                headers["Authorization"] = f"Bearer {azure_ad_token}"
        elif self.api_key is not API_KEY_SENTINEL:
            if headers.get("api-key") is None:
                headers["api-key"] = self.api_key
        else:
            # should never be hit
            raise ValueError("Unable to handle auth")

        return options

    async def _configure_realtime(self, model: str, extra_query: Query) -> tuple[httpx.URL, dict[str, str]]:
        auth_headers = {}
        query = {
            **extra_query,
            "api-version": self._api_version,
            "deployment": self._azure_deployment or model,
        }
        if self.api_key != "<missing API key>":
            auth_headers = {"api-key": self.api_key}
        else:
            token = await self._get_azure_ad_token()
            if token:
                auth_headers = {"Authorization": f"Bearer {token}"}

        if self.websocket_base_url is not None:
            base_url = httpx.URL(self.websocket_base_url)
            merge_raw_path = base_url.raw_path.rstrip(b"/") + b"/realtime"
            realtime_url = base_url.copy_with(raw_path=merge_raw_path)
        else:
            base_url = self._prepare_url("/realtime")
            realtime_url = base_url.copy_with(scheme="wss")

        url = realtime_url.copy_with(params={**query})
        return url, auth_headers

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32netcon.py ===
# Generated by h2py from lmaccess.h

# Included from lmcons.h
CNLEN = 15
LM20_CNLEN = 15
DNLEN = CNLEN
LM20_DNLEN = LM20_CNLEN
UNCLEN = CNLEN + 2
LM20_UNCLEN = LM20_CNLEN + 2
NNLEN = 80
LM20_NNLEN = 12
RMLEN = UNCLEN + 1 + NNLEN
LM20_RMLEN = LM20_UNCLEN + 1 + LM20_NNLEN
SNLEN = 80
LM20_SNLEN = 15
STXTLEN = 256
LM20_STXTLEN = 63
PATHLEN = 256
LM20_PATHLEN = 256
DEVLEN = 80
LM20_DEVLEN = 8
EVLEN = 16
UNLEN = 256
LM20_UNLEN = 20
GNLEN = UNLEN
LM20_GNLEN = LM20_UNLEN
PWLEN = 256
LM20_PWLEN = 14
SHPWLEN = 8
CLTYPE_LEN = 12
MAXCOMMENTSZ = 256
LM20_MAXCOMMENTSZ = 48
QNLEN = NNLEN
LM20_QNLEN = LM20_NNLEN
ALERTSZ = 128
NETBIOS_NAME_LEN = 16
CRYPT_KEY_LEN = 7
CRYPT_TXT_LEN = 8
ENCRYPTED_PWLEN = 16
SESSION_PWLEN = 24
SESSION_CRYPT_KLEN = 21
PARMNUM_ALL = 0
PARM_ERROR_NONE = 0
PARMNUM_BASE_INFOLEVEL = 1000
NULL = 0
PLATFORM_ID_DOS = 300
PLATFORM_ID_OS2 = 400
PLATFORM_ID_NT = 500
PLATFORM_ID_OSF = 600
PLATFORM_ID_VMS = 700
MAX_LANMAN_MESSAGE_ID = 5799
UF_SCRIPT = 1
UF_ACCOUNTDISABLE = 2
UF_HOMEDIR_REQUIRED = 8
UF_LOCKOUT = 16
UF_PASSWD_NOTREQD = 32
UF_PASSWD_CANT_CHANGE = 64
UF_TEMP_DUPLICATE_ACCOUNT = 256
UF_NORMAL_ACCOUNT = 512
UF_INTERDOMAIN_TRUST_ACCOUNT = 2048
UF_WORKSTATION_TRUST_ACCOUNT = 4096
UF_SERVER_TRUST_ACCOUNT = 8192
UF_MACHINE_ACCOUNT_MASK = (
    UF_INTERDOMAIN_TRUST_ACCOUNT
    | UF_WORKSTATION_TRUST_ACCOUNT
    | UF_SERVER_TRUST_ACCOUNT
)
UF_ACCOUNT_TYPE_MASK = (
    UF_TEMP_DUPLICATE_ACCOUNT
    | UF_NORMAL_ACCOUNT
    | UF_INTERDOMAIN_TRUST_ACCOUNT
    | UF_WORKSTATION_TRUST_ACCOUNT
    | UF_SERVER_TRUST_ACCOUNT
)
UF_DONT_EXPIRE_PASSWD = 65536
UF_MNS_LOGON_ACCOUNT = 131072
UF_SETTABLE_BITS = (
    UF_SCRIPT
    | UF_ACCOUNTDISABLE
    | UF_LOCKOUT
    | UF_HOMEDIR_REQUIRED
    | UF_PASSWD_NOTREQD
    | UF_PASSWD_CANT_CHANGE
    | UF_ACCOUNT_TYPE_MASK
    | UF_DONT_EXPIRE_PASSWD
    | UF_MNS_LOGON_ACCOUNT
)
FILTER_TEMP_DUPLICATE_ACCOUNT = 1
FILTER_NORMAL_ACCOUNT = 2
FILTER_INTERDOMAIN_TRUST_ACCOUNT = 8
FILTER_WORKSTATION_TRUST_ACCOUNT = 16
FILTER_SERVER_TRUST_ACCOUNT = 32
LG_INCLUDE_INDIRECT = 1
AF_OP_PRINT = 1
AF_OP_COMM = 2
AF_OP_SERVER = 4
AF_OP_ACCOUNTS = 8
AF_SETTABLE_BITS = AF_OP_PRINT | AF_OP_COMM | AF_OP_SERVER | AF_OP_ACCOUNTS
UAS_ROLE_STANDALONE = 0
UAS_ROLE_MEMBER = 1
UAS_ROLE_BACKUP = 2
UAS_ROLE_PRIMARY = 3
USER_NAME_PARMNUM = 1
USER_PASSWORD_PARMNUM = 3
USER_PASSWORD_AGE_PARMNUM = 4
USER_PRIV_PARMNUM = 5
USER_HOME_DIR_PARMNUM = 6
USER_COMMENT_PARMNUM = 7
USER_FLAGS_PARMNUM = 8
USER_SCRIPT_PATH_PARMNUM = 9
USER_AUTH_FLAGS_PARMNUM = 10
USER_FULL_NAME_PARMNUM = 11
USER_USR_COMMENT_PARMNUM = 12
USER_PARMS_PARMNUM = 13
USER_WORKSTATIONS_PARMNUM = 14
USER_LAST_LOGON_PARMNUM = 15
USER_LAST_LOGOFF_PARMNUM = 16
USER_ACCT_EXPIRES_PARMNUM = 17
USER_MAX_STORAGE_PARMNUM = 18
USER_UNITS_PER_WEEK_PARMNUM = 19
USER_LOGON_HOURS_PARMNUM = 20
USER_PAD_PW_COUNT_PARMNUM = 21
USER_NUM_LOGONS_PARMNUM = 22
USER_LOGON_SERVER_PARMNUM = 23
USER_COUNTRY_CODE_PARMNUM = 24
USER_CODE_PAGE_PARMNUM = 25
USER_PRIMARY_GROUP_PARMNUM = 51
USER_PROFILE = 52
USER_PROFILE_PARMNUM = 52
USER_HOME_DIR_DRIVE_PARMNUM = 53
USER_NAME_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_NAME_PARMNUM
USER_PASSWORD_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_PASSWORD_PARMNUM
USER_PASSWORD_AGE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_PASSWORD_AGE_PARMNUM
USER_PRIV_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_PRIV_PARMNUM
USER_HOME_DIR_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_HOME_DIR_PARMNUM
USER_COMMENT_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_COMMENT_PARMNUM
USER_FLAGS_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_FLAGS_PARMNUM
USER_SCRIPT_PATH_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_SCRIPT_PATH_PARMNUM
USER_AUTH_FLAGS_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_AUTH_FLAGS_PARMNUM
USER_FULL_NAME_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_FULL_NAME_PARMNUM
USER_USR_COMMENT_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_USR_COMMENT_PARMNUM
USER_PARMS_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_PARMS_PARMNUM
USER_WORKSTATIONS_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_WORKSTATIONS_PARMNUM
USER_LAST_LOGON_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_LAST_LOGON_PARMNUM
USER_LAST_LOGOFF_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_LAST_LOGOFF_PARMNUM
USER_ACCT_EXPIRES_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_ACCT_EXPIRES_PARMNUM
USER_MAX_STORAGE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_MAX_STORAGE_PARMNUM
USER_UNITS_PER_WEEK_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_UNITS_PER_WEEK_PARMNUM
USER_LOGON_HOURS_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_LOGON_HOURS_PARMNUM
USER_PAD_PW_COUNT_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_PAD_PW_COUNT_PARMNUM
USER_NUM_LOGONS_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_NUM_LOGONS_PARMNUM
USER_LOGON_SERVER_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_LOGON_SERVER_PARMNUM
USER_COUNTRY_CODE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_COUNTRY_CODE_PARMNUM
USER_CODE_PAGE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_CODE_PAGE_PARMNUM
USER_PRIMARY_GROUP_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_PRIMARY_GROUP_PARMNUM
USER_HOME_DIR_DRIVE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + USER_HOME_DIR_DRIVE_PARMNUM
NULL_USERSETINFO_PASSWD = "              "
UNITS_PER_DAY = 24
UNITS_PER_WEEK = UNITS_PER_DAY * 7
USER_PRIV_MASK = 3
USER_PRIV_GUEST = 0
USER_PRIV_USER = 1
USER_PRIV_ADMIN = 2
MAX_PASSWD_LEN = PWLEN
DEF_MIN_PWLEN = 6
DEF_PWUNIQUENESS = 5
DEF_MAX_PWHIST = 8
DEF_MAX_BADPW = 0
VALIDATED_LOGON = 0
PASSWORD_EXPIRED = 2
NON_VALIDATED_LOGON = 3
VALID_LOGOFF = 1
MODALS_MIN_PASSWD_LEN_PARMNUM = 1
MODALS_MAX_PASSWD_AGE_PARMNUM = 2
MODALS_MIN_PASSWD_AGE_PARMNUM = 3
MODALS_FORCE_LOGOFF_PARMNUM = 4
MODALS_PASSWD_HIST_LEN_PARMNUM = 5
MODALS_ROLE_PARMNUM = 6
MODALS_PRIMARY_PARMNUM = 7
MODALS_DOMAIN_NAME_PARMNUM = 8
MODALS_DOMAIN_ID_PARMNUM = 9
MODALS_LOCKOUT_DURATION_PARMNUM = 10
MODALS_LOCKOUT_OBSERVATION_WINDOW_PARMNUM = 11
MODALS_LOCKOUT_THRESHOLD_PARMNUM = 12
MODALS_MIN_PASSWD_LEN_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_MIN_PASSWD_LEN_PARMNUM
MODALS_MAX_PASSWD_AGE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_MAX_PASSWD_AGE_PARMNUM
MODALS_MIN_PASSWD_AGE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_MIN_PASSWD_AGE_PARMNUM
MODALS_FORCE_LOGOFF_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_FORCE_LOGOFF_PARMNUM
MODALS_PASSWD_HIST_LEN_INFOLEVEL = (
    PARMNUM_BASE_INFOLEVEL + MODALS_PASSWD_HIST_LEN_PARMNUM
)
MODALS_ROLE_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_ROLE_PARMNUM
MODALS_PRIMARY_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_PRIMARY_PARMNUM
MODALS_DOMAIN_NAME_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_DOMAIN_NAME_PARMNUM
MODALS_DOMAIN_ID_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + MODALS_DOMAIN_ID_PARMNUM
GROUPIDMASK = 32768
GROUP_ALL_PARMNUM = 0
GROUP_NAME_PARMNUM = 1
GROUP_COMMENT_PARMNUM = 2
GROUP_ATTRIBUTES_PARMNUM = 3
GROUP_ALL_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + GROUP_ALL_PARMNUM
GROUP_NAME_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + GROUP_NAME_PARMNUM
GROUP_COMMENT_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + GROUP_COMMENT_PARMNUM
GROUP_ATTRIBUTES_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + GROUP_ATTRIBUTES_PARMNUM
LOCALGROUP_NAME_PARMNUM = 1
LOCALGROUP_COMMENT_PARMNUM = 2
MAXPERMENTRIES = 64
ACCESS_NONE = 0
ACCESS_READ = 1
ACCESS_WRITE = 2
ACCESS_CREATE = 4
ACCESS_EXEC = 8
ACCESS_DELETE = 16
ACCESS_ATRIB = 32
ACCESS_PERM = 64
ACCESS_GROUP = 32768
ACCESS_AUDIT = 1
ACCESS_SUCCESS_OPEN = 16
ACCESS_SUCCESS_WRITE = 32
ACCESS_SUCCESS_DELETE = 64
ACCESS_SUCCESS_ACL = 128
ACCESS_SUCCESS_MASK = 240
ACCESS_FAIL_OPEN = 256
ACCESS_FAIL_WRITE = 512
ACCESS_FAIL_DELETE = 1024
ACCESS_FAIL_ACL = 2048
ACCESS_FAIL_MASK = 3840
ACCESS_FAIL_SHIFT = 4
ACCESS_RESOURCE_NAME_PARMNUM = 1
ACCESS_ATTR_PARMNUM = 2
ACCESS_COUNT_PARMNUM = 3
ACCESS_ACCESS_LIST_PARMNUM = 4
ACCESS_RESOURCE_NAME_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + ACCESS_RESOURCE_NAME_PARMNUM
ACCESS_ATTR_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + ACCESS_ATTR_PARMNUM
ACCESS_COUNT_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + ACCESS_COUNT_PARMNUM
ACCESS_ACCESS_LIST_INFOLEVEL = PARMNUM_BASE_INFOLEVEL + ACCESS_ACCESS_LIST_PARMNUM
ACCESS_LETTERS = "RWCXDAP         "
NETLOGON_CONTROL_QUERY = 1
NETLOGON_CONTROL_REPLICATE = 2
NETLOGON_CONTROL_SYNCHRONIZE = 3
NETLOGON_CONTROL_PDC_REPLICATE = 4
NETLOGON_CONTROL_REDISCOVER = 5
NETLOGON_CONTROL_TC_QUERY = 6
NETLOGON_CONTROL_TRANSPORT_NOTIFY = 7
NETLOGON_CONTROL_FIND_USER = 8
NETLOGON_CONTROL_UNLOAD_NETLOGON_DLL = 65531
NETLOGON_CONTROL_BACKUP_CHANGE_LOG = 65532
NETLOGON_CONTROL_TRUNCATE_LOG = 65533
NETLOGON_CONTROL_SET_DBFLAG = 65534
NETLOGON_CONTROL_BREAKPOINT = 65535
NETLOGON_REPLICATION_NEEDED = 1
NETLOGON_REPLICATION_IN_PROGRESS = 2
NETLOGON_FULL_SYNC_REPLICATION = 4
NETLOGON_REDO_NEEDED = 8

######################
# Manual stuff

TEXT = lambda x: x

MAX_PREFERRED_LENGTH = -1
PARM_ERROR_UNKNOWN = -1
MESSAGE_FILENAME = TEXT("NETMSG")
OS2MSG_FILENAME = TEXT("BASE")
HELP_MSG_FILENAME = TEXT("NETH")
BACKUP_MSG_FILENAME = TEXT("BAK.MSG")
TIMEQ_FOREVER = -1
USER_MAXSTORAGE_UNLIMITED = -1
USER_NO_LOGOFF = -1
DEF_MAX_PWAGE = TIMEQ_FOREVER
DEF_MIN_PWAGE = 0
DEF_FORCE_LOGOFF = -1
ONE_DAY = 1 * 24 * 3600
GROUP_SPECIALGRP_USERS = "USERS"
GROUP_SPECIALGRP_ADMINS = "ADMINS"
GROUP_SPECIALGRP_GUESTS = "GUESTS"
GROUP_SPECIALGRP_LOCAL = "LOCAL"
ACCESS_ALL = (
    ACCESS_READ
    | ACCESS_WRITE
    | ACCESS_CREATE
    | ACCESS_EXEC
    | ACCESS_DELETE
    | ACCESS_ATRIB
    | ACCESS_PERM
)

# From lmserver.h
SV_PLATFORM_ID_OS2 = 400
SV_PLATFORM_ID_NT = 500
MAJOR_VERSION_MASK = 15
SV_TYPE_WORKSTATION = 1
SV_TYPE_SERVER = 2
SV_TYPE_SQLSERVER = 4
SV_TYPE_DOMAIN_CTRL = 8
SV_TYPE_DOMAIN_BAKCTRL = 16
SV_TYPE_TIME_SOURCE = 32
SV_TYPE_AFP = 64
SV_TYPE_NOVELL = 128
SV_TYPE_DOMAIN_MEMBER = 256
SV_TYPE_PRINTQ_SERVER = 512
SV_TYPE_DIALIN_SERVER = 1024
SV_TYPE_XENIX_SERVER = 2048
SV_TYPE_SERVER_UNIX = SV_TYPE_XENIX_SERVER
SV_TYPE_NT = 4096
SV_TYPE_WFW = 8192
SV_TYPE_SERVER_MFPN = 16384
SV_TYPE_SERVER_NT = 32768
SV_TYPE_POTENTIAL_BROWSER = 65536
SV_TYPE_BACKUP_BROWSER = 131072
SV_TYPE_MASTER_BROWSER = 262144
SV_TYPE_DOMAIN_MASTER = 524288
SV_TYPE_SERVER_OSF = 1048576
SV_TYPE_SERVER_VMS = 2097152
SV_TYPE_WINDOWS = 4194304
SV_TYPE_DFS = 8388608
SV_TYPE_CLUSTER_NT = 16777216
SV_TYPE_DCE = 268435456
SV_TYPE_ALTERNATE_XPORT = 536870912
SV_TYPE_LOCAL_LIST_ONLY = 1073741824
SV_TYPE_DOMAIN_ENUM = -2147483648
SV_TYPE_ALL = -1
SV_NODISC = -1
SV_USERSECURITY = 1
SV_SHARESECURITY = 0
SV_HIDDEN = 1
SV_VISIBLE = 0
SV_PLATFORM_ID_PARMNUM = 101
SV_NAME_PARMNUM = 102
SV_VERSION_MAJOR_PARMNUM = 103
SV_VERSION_MINOR_PARMNUM = 104
SV_TYPE_PARMNUM = 105
SV_COMMENT_PARMNUM = 5
SV_USERS_PARMNUM = 107
SV_DISC_PARMNUM = 10
SV_HIDDEN_PARMNUM = 16
SV_ANNOUNCE_PARMNUM = 17
SV_ANNDELTA_PARMNUM = 18
SV_USERPATH_PARMNUM = 112
SV_ULIST_MTIME_PARMNUM = 401
SV_GLIST_MTIME_PARMNUM = 402
SV_ALIST_MTIME_PARMNUM = 403
SV_ALERTS_PARMNUM = 11
SV_SECURITY_PARMNUM = 405
SV_NUMADMIN_PARMNUM = 406
SV_LANMASK_PARMNUM = 407
SV_GUESTACC_PARMNUM = 408
SV_CHDEVQ_PARMNUM = 410
SV_CHDEVJOBS_PARMNUM = 411
SV_CONNECTIONS_PARMNUM = 412
SV_SHARES_PARMNUM = 413
SV_OPENFILES_PARMNUM = 414
SV_SESSREQS_PARMNUM = 417
SV_ACTIVELOCKS_PARMNUM = 419
SV_NUMREQBUF_PARMNUM = 420
SV_NUMBIGBUF_PARMNUM = 422
SV_NUMFILETASKS_PARMNUM = 423
SV_ALERTSCHED_PARMNUM = 37
SV_ERRORALERT_PARMNUM = 38
SV_LOGONALERT_PARMNUM = 39
SV_ACCESSALERT_PARMNUM = 40
SV_DISKALERT_PARMNUM = 41
SV_NETIOALERT_PARMNUM = 42
SV_MAXAUDITSZ_PARMNUM = 43
SV_SRVHEURISTICS_PARMNUM = 431
SV_SESSOPENS_PARMNUM = 501
SV_SESSVCS_PARMNUM = 502
SV_OPENSEARCH_PARMNUM = 503
SV_SIZREQBUF_PARMNUM = 504
SV_INITWORKITEMS_PARMNUM = 505
SV_MAXWORKITEMS_PARMNUM = 506
SV_RAWWORKITEMS_PARMNUM = 507
SV_IRPSTACKSIZE_PARMNUM = 508
SV_MAXRAWBUFLEN_PARMNUM = 509
SV_SESSUSERS_PARMNUM = 510
SV_SESSCONNS_PARMNUM = 511
SV_MAXNONPAGEDMEMORYUSAGE_PARMNUM = 512
SV_MAXPAGEDMEMORYUSAGE_PARMNUM = 513
SV_ENABLESOFTCOMPAT_PARMNUM = 514
SV_ENABLEFORCEDLOGOFF_PARMNUM = 515
SV_TIMESOURCE_PARMNUM = 516
SV_ACCEPTDOWNLEVELAPIS_PARMNUM = 517
SV_LMANNOUNCE_PARMNUM = 518
SV_DOMAIN_PARMNUM = 519
SV_MAXCOPYREADLEN_PARMNUM = 520
SV_MAXCOPYWRITELEN_PARMNUM = 521
SV_MINKEEPSEARCH_PARMNUM = 522
SV_MAXKEEPSEARCH_PARMNUM = 523
SV_MINKEEPCOMPLSEARCH_PARMNUM = 524
SV_MAXKEEPCOMPLSEARCH_PARMNUM = 525
SV_THREADCOUNTADD_PARMNUM = 526
SV_NUMBLOCKTHREADS_PARMNUM = 527
SV_SCAVTIMEOUT_PARMNUM = 528
SV_MINRCVQUEUE_PARMNUM = 529
SV_MINFREEWORKITEMS_PARMNUM = 530
SV_XACTMEMSIZE_PARMNUM = 531
SV_THREADPRIORITY_PARMNUM = 532
SV_MAXMPXCT_PARMNUM = 533
SV_OPLOCKBREAKWAIT_PARMNUM = 534
SV_OPLOCKBREAKRESPONSEWAIT_PARMNUM = 535
SV_ENABLEOPLOCKS_PARMNUM = 536
SV_ENABLEOPLOCKFORCECLOSE_PARMNUM = 537
SV_ENABLEFCBOPENS_PARMNUM = 538
SV_ENABLERAW_PARMNUM = 539
SV_ENABLESHAREDNETDRIVES_PARMNUM = 540
SV_MINFREECONNECTIONS_PARMNUM = 541
SV_MAXFREECONNECTIONS_PARMNUM = 542
SV_INITSESSTABLE_PARMNUM = 543
SV_INITCONNTABLE_PARMNUM = 544
SV_INITFILETABLE_PARMNUM = 545
SV_INITSEARCHTABLE_PARMNUM = 546
SV_ALERTSCHEDULE_PARMNUM = 547
SV_ERRORTHRESHOLD_PARMNUM = 548
SV_NETWORKERRORTHRESHOLD_PARMNUM = 549
SV_DISKSPACETHRESHOLD_PARMNUM = 550
SV_MAXLINKDELAY_PARMNUM = 552
SV_MINLINKTHROUGHPUT_PARMNUM = 553
SV_LINKINFOVALIDTIME_PARMNUM = 554
SV_SCAVQOSINFOUPDATETIME_PARMNUM = 555
SV_MAXWORKITEMIDLETIME_PARMNUM = 556
SV_MAXRAWWORKITEMS_PARMNUM = 557
SV_PRODUCTTYPE_PARMNUM = 560
SV_SERVERSIZE_PARMNUM = 561
SV_CONNECTIONLESSAUTODISC_PARMNUM = 562
SV_SHARINGVIOLATIONRETRIES_PARMNUM = 563
SV_SHARINGVIOLATIONDELAY_PARMNUM = 564
SV_MAXGLOBALOPENSEARCH_PARMNUM = 565
SV_REMOVEDUPLICATESEARCHES_PARMNUM = 566
SV_LOCKVIOLATIONRETRIES_PARMNUM = 567
SV_LOCKVIOLATIONOFFSET_PARMNUM = 568
SV_LOCKVIOLATIONDELAY_PARMNUM = 569
SV_MDLREADSWITCHOVER_PARMNUM = 570
SV_CACHEDOPENLIMIT_PARMNUM = 571
SV_CRITICALTHREADS_PARMNUM = 572
SV_RESTRICTNULLSESSACCESS_PARMNUM = 573
SV_ENABLEWFW311DIRECTIPX_PARMNUM = 574
SV_OTHERQUEUEAFFINITY_PARMNUM = 575
SV_QUEUESAMPLESECS_PARMNUM = 576
SV_BALANCECOUNT_PARMNUM = 577
SV_PREFERREDAFFINITY_PARMNUM = 578
SV_MAXFREERFCBS_PARMNUM = 579
SV_MAXFREEMFCBS_PARMNUM = 580
SV_MAXFREELFCBS_PARMNUM = 581
SV_MAXFREEPAGEDPOOLCHUNKS_PARMNUM = 582
SV_MINPAGEDPOOLCHUNKSIZE_PARMNUM = 583
SV_MAXPAGEDPOOLCHUNKSIZE_PARMNUM = 584
SV_SENDSFROMPREFERREDPROCESSOR_PARMNUM = 585
SV_MAXTHREADSPERQUEUE_PARMNUM = 586
SV_CACHEDDIRECTORYLIMIT_PARMNUM = 587
SV_MAXCOPYLENGTH_PARMNUM = 588
SV_ENABLEBULKTRANSFER_PARMNUM = 589
SV_ENABLECOMPRESSION_PARMNUM = 590
SV_AUTOSHAREWKS_PARMNUM = 591
SV_AUTOSHARESERVER_PARMNUM = 592
SV_ENABLESECURITYSIGNATURE_PARMNUM = 593
SV_REQUIRESECURITYSIGNATURE_PARMNUM = 594
SV_MINCLIENTBUFFERSIZE_PARMNUM = 595
SV_CONNECTIONNOSESSIONSTIMEOUT_PARMNUM = 596
SVI1_NUM_ELEMENTS = 5
SVI2_NUM_ELEMENTS = 40
SVI3_NUM_ELEMENTS = 44
SW_AUTOPROF_LOAD_MASK = 1
SW_AUTOPROF_SAVE_MASK = 2
SV_MAX_SRV_HEUR_LEN = 32
SV_USERS_PER_LICENSE = 5
SVTI2_REMAP_PIPE_NAMES = 2

# Generated by h2py from lmshare.h
SHARE_NETNAME_PARMNUM = 1
SHARE_TYPE_PARMNUM = 3
SHARE_REMARK_PARMNUM = 4
SHARE_PERMISSIONS_PARMNUM = 5
SHARE_MAX_USES_PARMNUM = 6
SHARE_CURRENT_USES_PARMNUM = 7
SHARE_PATH_PARMNUM = 8
SHARE_PASSWD_PARMNUM = 9
SHARE_FILE_SD_PARMNUM = 501
SHI1_NUM_ELEMENTS = 4
SHI2_NUM_ELEMENTS = 10
STYPE_DISKTREE = 0
STYPE_PRINTQ = 1
STYPE_DEVICE = 2
STYPE_IPC = 3
STYPE_SPECIAL = -2147483648
SHI1005_FLAGS_DFS = 1
SHI1005_FLAGS_DFS_ROOT = 2
COW_PERMACHINE = 4
COW_PERUSER = 8
CSC_CACHEABLE = 16
CSC_NOFLOWOPS = 32
CSC_AUTO_INWARD = 64
CSC_AUTO_OUTWARD = 128
SHI1005_VALID_FLAGS_SET = (
    CSC_CACHEABLE
    | CSC_NOFLOWOPS
    | CSC_AUTO_INWARD
    | CSC_AUTO_OUTWARD
    | COW_PERMACHINE
    | COW_PERUSER
)
SHI1007_VALID_FLAGS_SET = SHI1005_VALID_FLAGS_SET
SESS_GUEST = 1
SESS_NOENCRYPTION = 2
SESI1_NUM_ELEMENTS = 8
SESI2_NUM_ELEMENTS = 9
PERM_FILE_READ = 1
PERM_FILE_WRITE = 2
PERM_FILE_CREATE = 4

# Generated by h2py from d:\mssdk\include\winnetwk.h
WNNC_NET_MSNET = 65536
WNNC_NET_LANMAN = 131072
WNNC_NET_NETWARE = 196608
WNNC_NET_VINES = 262144
WNNC_NET_10NET = 327680
WNNC_NET_LOCUS = 393216
WNNC_NET_SUN_PC_NFS = 458752
WNNC_NET_LANSTEP = 524288
WNNC_NET_9TILES = 589824
WNNC_NET_LANTASTIC = 655360
WNNC_NET_AS400 = 720896
WNNC_NET_FTP_NFS = 786432
WNNC_NET_PATHWORKS = 851968
WNNC_NET_LIFENET = 917504
WNNC_NET_POWERLAN = 983040
WNNC_NET_BWNFS = 1048576
WNNC_NET_COGENT = 1114112
WNNC_NET_FARALLON = 1179648
WNNC_NET_APPLETALK = 1245184
WNNC_NET_INTERGRAPH = 1310720
WNNC_NET_SYMFONET = 1376256
WNNC_NET_CLEARCASE = 1441792
WNNC_NET_FRONTIER = 1507328
WNNC_NET_BMC = 1572864
WNNC_NET_DCE = 1638400
WNNC_NET_DECORB = 2097152
WNNC_NET_PROTSTOR = 2162688
WNNC_NET_FJ_REDIR = 2228224
WNNC_NET_DISTINCT = 2293760
WNNC_NET_TWINS = 2359296
WNNC_NET_RDR2SAMPLE = 2424832
RESOURCE_CONNECTED = 1
RESOURCE_GLOBALNET = 2
RESOURCE_REMEMBERED = 3
RESOURCE_RECENT = 4
RESOURCE_CONTEXT = 5
RESOURCETYPE_ANY = 0
RESOURCETYPE_DISK = 1
RESOURCETYPE_PRINT = 2
RESOURCETYPE_RESERVED = 8
RESOURCETYPE_UNKNOWN = -1
RESOURCEUSAGE_CONNECTABLE = 1
RESOURCEUSAGE_CONTAINER = 2
RESOURCEUSAGE_NOLOCALDEVICE = 4
RESOURCEUSAGE_SIBLING = 8
RESOURCEUSAGE_ATTACHED = 16
RESOURCEUSAGE_ALL = (
    RESOURCEUSAGE_CONNECTABLE | RESOURCEUSAGE_CONTAINER | RESOURCEUSAGE_ATTACHED
)
RESOURCEUSAGE_RESERVED = -2147483648
RESOURCEDISPLAYTYPE_GENERIC = 0
RESOURCEDISPLAYTYPE_DOMAIN = 1
RESOURCEDISPLAYTYPE_SERVER = 2
RESOURCEDISPLAYTYPE_SHARE = 3
RESOURCEDISPLAYTYPE_FILE = 4
RESOURCEDISPLAYTYPE_GROUP = 5
RESOURCEDISPLAYTYPE_NETWORK = 6
RESOURCEDISPLAYTYPE_ROOT = 7
RESOURCEDISPLAYTYPE_SHAREADMIN = 8
RESOURCEDISPLAYTYPE_DIRECTORY = 9
RESOURCEDISPLAYTYPE_TREE = 10
RESOURCEDISPLAYTYPE_NDSCONTAINER = 11
NETPROPERTY_PERSISTENT = 1
CONNECT_UPDATE_PROFILE = 1
CONNECT_UPDATE_RECENT = 2
CONNECT_TEMPORARY = 4
CONNECT_INTERACTIVE = 8
CONNECT_PROMPT = 16
CONNECT_NEED_DRIVE = 32
CONNECT_REFCOUNT = 64
CONNECT_REDIRECT = 128
CONNECT_LOCALDRIVE = 256
CONNECT_CURRENT_MEDIA = 512
CONNECT_DEFERRED = 1024
CONNECT_RESERVED = -16777216
CONNDLG_RO_PATH = 1
CONNDLG_CONN_POINT = 2
CONNDLG_USE_MRU = 4
CONNDLG_HIDE_BOX = 8
CONNDLG_PERSIST = 16
CONNDLG_NOT_PERSIST = 32
DISC_UPDATE_PROFILE = 1
DISC_NO_FORCE = 64
UNIVERSAL_NAME_INFO_LEVEL = 1
REMOTE_NAME_INFO_LEVEL = 2
WNFMT_MULTILINE = 1
WNFMT_ABBREVIATED = 2
WNFMT_INENUM = 16
WNFMT_CONNECTION = 32
NETINFO_DLL16 = 1
NETINFO_DISKRED = 4
NETINFO_PRINTERRED = 8
RP_LOGON = 1
RP_INIFILE = 2
PP_DISPLAYERRORS = 1
WNCON_FORNETCARD = 1
WNCON_NOTROUTED = 2
WNCON_SLOWLINK = 4
WNCON_DYNAMIC = 8

## NETSETUP_NAME_TYPE, used with NetValidateName
NetSetupUnknown = 0
NetSetupMachine = 1
NetSetupWorkgroup = 2
NetSetupDomain = 3
NetSetupNonExistentDomain = 4
NetSetupDnsMachine = 5

## NETSETUP_JOIN_STATUS, use with NetGetJoinInformation
NetSetupUnknownStatus = 0
NetSetupUnjoined = 1
NetSetupWorkgroupName = 2
NetSetupDomainName = 3

NetValidateAuthentication = 1
NetValidatePasswordChange = 2
NetValidatePasswordReset = 3

# === NexusCore/exported_projects\app_20250703_223016\app\utils\models\make_deeplab_onnx.py ===
# make_deeplab_onnx.py
import torch, torchvision

# 1) 学習済み DeepLab v3 + MobileNetV3 Large（Cityscapes 21クラス）
model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(weights="DEFAULT")  # PyTorch 2.2 時点で公開[3]
model.eval()

# 2) ダミー入力（513×513 は元論文の標準解像度）
dummy = torch.randn(1, 3, 513, 513)

# 3) ONNX にエクスポート
torch.onnx.export(
    model, dummy, "deeplabv3_mnv3.onnx",
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    opset_version=12                                            # OpenCV 4.7+ が正式対応[3]
)
print("✓ deeplabv3_mnv3.onnx を生成しました")

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\models\make_deeplab_onnx.py ===
# make_deeplab_onnx.py
import torch, torchvision

# 1) 学習済み DeepLab v3 + MobileNetV3 Large（Cityscapes 21クラス）
model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(weights="DEFAULT")  # PyTorch 2.2 時点で公開[3]
model.eval()

# 2) ダミー入力（513×513 は元論文の標準解像度）
dummy = torch.randn(1, 3, 513, 513)

# 3) ONNX にエクスポート
torch.onnx.export(
    model, dummy, "deeplabv3_mnv3.onnx",
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    opset_version=12                                            # OpenCV 4.7+ が正式対応[3]
)
print("✓ deeplabv3_mnv3.onnx を生成しました")

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\models\make_deeplab_onnx.py ===
# make_deeplab_onnx.py
import torch, torchvision

# 1) 学習済み DeepLab v3 + MobileNetV3 Large（Cityscapes 21クラス）
model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(weights="DEFAULT")  # PyTorch 2.2 時点で公開[3]
model.eval()

# 2) ダミー入力（513×513 は元論文の標準解像度）
dummy = torch.randn(1, 3, 513, 513)

# 3) ONNX にエクスポート
torch.onnx.export(
    model, dummy, "deeplabv3_mnv3.onnx",
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    opset_version=12                                            # OpenCV 4.7+ が正式対応[3]
)
print("✓ deeplabv3_mnv3.onnx を生成しました")

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\models\make_deeplab_onnx.py ===
# make_deeplab_onnx.py
import torch, torchvision

# 1) 学習済み DeepLab v3 + MobileNetV3 Large（Cityscapes 21クラス）
model = torchvision.models.segmentation.deeplabv3_mobilenet_v3_large(weights="DEFAULT")  # PyTorch 2.2 時点で公開[3]
model.eval()

# 2) ダミー入力（513×513 は元論文の標準解像度）
dummy = torch.randn(1, 3, 513, 513)

# 3) ONNX にエクスポート
torch.onnx.export(
    model, dummy, "deeplabv3_mnv3.onnx",
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    opset_version=12                                            # OpenCV 4.7+ が正式対応[3]
)
print("✓ deeplabv3_mnv3.onnx を生成しました")

# === NexusCore/src\utils\tree_sitter_checker.py ===
# tree_sitter_checker.py
from tree_sitter import Language, Parser
import os

# 絶対パス指定（Windows環境対応）
base_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.abspath(os.path.join(base_dir, "..", "..", "build", "my-languages.so"))

# Python用の言語を読み込み
PY_LANGUAGE = Language(lib_path, 'python')

# Tree-sitter構文解析を実行
def print_syntax_tree(code: str):
    parser = Parser()
    parser.set_language(PY_LANGUAGE)
    tree = parser.parse(bytes(code, "utf8"))
    print(tree.root_node.sexp())
    return tree.root_node.sexp()

# === NexusCore/my-crm-app\app\views.py ===
# TODO: Define routes and view functions

from flask import Blueprint, request, jsonify
from .models import Customer
from . import db

main = Blueprint('main', __name__)

@main.route('/customers', methods=['GET'])
def get_customers():
    # TODO: Implement logic to retrieve customers
    return jsonify([])

@main.route('/customers', methods=['POST'])
def add_customer():
    # TODO: Implement logic to add a new customer
    return jsonify({'message': 'Customer added'})

# === NexusCore/src\utils\zip_output.py ===
import os
import zipfile
from datetime import datetime

def zip_project(output_dir="deploy_output"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(output_dir, f"OpenCodeInterpreter_{timestamp}.zip")

    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk("."):
            if any(x in foldername for x in [".git", "__pycache__", "venv", ".mypy_cache"]):
                continue
            for filename in filenames:
                filepath = os.path.join(foldername, filename)
                arcname = os.path.relpath(filepath, ".")
                zipf.write(filepath, arcname)
    print(f"✅ プロジェクトが {zip_filename} に保存されました")

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32pdhquery.py ===
"""
Performance Data Helper (PDH) Query Classes

Wrapper classes for end-users and high-level access to the PDH query
mechanisms.  PDH is a win32-specific mechanism for accessing the
performance data made available by the system.  The Python for Windows
PDH module does not implement the "Registry" interface, implementing
the more straightforward Query-based mechanism.

The basic idea of a PDH Query is an object which can query the system
about the status of any number of "counters."  The counters are paths
to a particular piece of performance data.  For instance, the path
'\\Memory\\Available Bytes' describes just about exactly what it says
it does, the amount of free memory on the default computer expressed
in Bytes.  These paths can be considerably more complex than this,
but part of the point of this wrapper module is to hide that
complexity from the end-user/programmer.

EXAMPLE: A more complex Path
    '\\\\RAISTLIN\\PhysicalDisk(_Total)\\Avg. Disk Bytes/Read'
    Raistlin --> Computer Name
    PhysicalDisk --> Object Name
    _Total --> The particular Instance (in this case, all instances, i.e. all drives)
    Avg. Disk Bytes/Read --> The piece of data being monitored.

EXAMPLE: Collecting Data with a Query
    As an example, the following code implements a logger which allows the
    user to choose what counters they would like to log, and logs those
    counters for 30 seconds, at two-second intervals.

    query = Query()
    query.addcounterbybrowsing()
    query.collectdatafor(30,2)

    The data is now stored in a list of lists as:
    query.curresults

    The counters(paths) which were used to collect the data are:
    query.curpaths

    You can use the win32pdh.ParseCounterPath(path) utility function
    to turn the paths into more easily read values for your task, or
    write the data to a file, or do whatever you want with it.

OTHER NOTABLE METHODS:
    query.collectdatawhile(period) # start a logging thread for collecting data
    query.collectdatawhile_stop() # signal the logging thread to stop logging
    query.collectdata() # run the query only once
    query.addperfcounter(object, counter, machine=None) # add a standard performance counter
    query.addinstcounter(object, counter,machine=None,objtype = 'Process',volatile=1,format = win32pdh.PDH_FMT_LONG) # add a possibly volatile counter

### Known bugs and limitations ###
Due to a problem with threading under the PythonWin interpreter, there
will be no data logged if the PythonWin window is not the foreground
application.  Workaround: scripts using threading should be run in the
python.exe interpreter.

The volatile-counter handlers are possibly buggy, they haven't been
tested to any extent.  The wrapper Query makes it safe to pass invalid
paths (a -1 will be returned, or the Query will be totally ignored,
depending on the missing element), so you should be able to work around
the error by including all possible paths and filtering out the -1's.

There is no way I know of to stop a thread which is currently sleeping,
so you have to wait until the thread in collectdatawhile is activated
again.  This might become a problem in situations where the collection
period is multiple minutes (or hours, or whatever).

Should make the win32pdh.ParseCounter function available to the Query
classes as a method or something similar, so that it can be accessed
by programmes that have just picked up an instance from somewhere.

Should explicitly mention where QueryErrors can be raised, and create a
full test set to see if there are any uncaught win32api.error's still
hanging around.

When using the python.exe interpreter, the addcounterbybrowsing-
generated browser window is often hidden behind other windows.  No known
workaround other than Alt-tabing to reach the browser window.

### Other References ###
The win32pdhutil module (which should be in the %pythonroot%/win32/lib
directory) provides quick-and-dirty utilities for one-off access to
variables from the PDH.  Almost everything in that module can be done
with a Query object, but it provides task-oriented functions for a
number of common one-off tasks.

If you can access the MS Developers Network Library, you can find
information about the PDH API as MS describes it.  For a background article,
try:
https://web.archive.org/web/20040926110045/http://msdn.microsoft.com:80/library/en-us/dnperfmo/html/msdn_pdhlib.asp

The reference guide for the PDH API was last spotted at:
https://learn.microsoft.com/en-us/windows/win32/perfctrs/using-the-pdh-functions-to-consume-counter-data


In general the Python version of the API is just a wrapper around the
Query-based version of this API (as far as I can see), so you can learn what
you need to from there.  From what I understand, the MSDN Online
resources are available for the price of signing up for them.  I can't
guarantee how long that's supposed to last. (Or anything for that
matter).
http://premium.microsoft.com/isapi/devonly/prodinfo/msdnprod/msdnlib.idc?theURL=/msdn/library/sdkdoc/perfdata_4982.htm

The eventual plan is for my (Mike Fletcher's) Starship account to include
a section on NT Administration, and the Query is the first project
in this plan.  There should be an article describing the creation of
a simple logger there, but the example above is 90% of the work of
that project, so don't sweat it if you don't find anything there.
(currently the account hasn't been set up).
https://web.archive.org/web/19980422204546/http://starship.skyport.net/crew/mcfletch/

If you need to contact me immediately, (why I can't imagine), you can
email me at mcfletch@golden.net, or just post your question to the
Python newsgroup with a catchy subject line.
news:comp.lang.python

### Other Stuff ###
The Query classes are by Mike Fletcher, with the working code
being corruptions of Mark Hammonds win32pdhutil module.

Use at your own risk, no warranties, no guarantees, no assurances,
if you use it, you accept the risk of using it, etceteras.
"""

# Feb 12, 98 - MH added "rawaddcounter" so caller can get exception details.

import _thread
import copy
import time

import win32api
import win32pdh


class BaseQuery:
    """
    Provides wrapped access to the Performance Data Helper query
    objects, generally you should use the child class Query
    unless you have need of doing weird things :)

    This class supports two major working paradigms.  In the first,
    you open the query, and run it as many times as you need, closing
    the query when you're done with it.  This is suitable for static
    queries (ones where processes being monitored don't disappear).

    In the second, you allow the query to be opened each time and
    closed afterward.  This causes the base query object to be
    destroyed after each call.  Suitable for dynamic queries (ones
    which watch processes which might be closed while watching.)
    """

    def __init__(self, paths=None):
        """
        The PDH Query object is initialised with a single, optional
        list argument, that must be properly formatted PDH Counter
        paths.  Generally this list will only be provided by the class
        when it is being unpickled (removed from storage).  Normal
        use is to call the class with no arguments and use the various
        addcounter functions (particularly, for end user's, the use of
        addcounterbybrowsing is the most common approach)  You might
        want to provide the list directly if you want to hard-code the
        elements with which your query deals (and thereby avoid the
        overhead of unpickling the class).
        """
        self.counters = []
        if paths:
            self.paths = paths
        else:
            self.paths = []
        self._base = None
        self.active = 0
        self.curpaths = []

    def addcounterbybrowsing(
        self, flags=win32pdh.PERF_DETAIL_WIZARD, windowtitle="Python Browser"
    ):
        """
        Adds possibly multiple paths to the paths attribute of the query,
        does this by calling the standard counter browsing dialogue.  Within
        this dialogue, find the counter you want to log, and click: Add,
        repeat for every path you want to log, then click on close.  The
        paths are appended to the non-volatile paths list for this class,
        subclasses may create a function which parses the paths and decides
        (via heuristics) whether to add the path to the volatile or non-volatile
        path list.
        e.g.:
                query.addcounter()
        """
        win32pdh.BrowseCounters(None, 0, self.paths.append, flags, windowtitle)

    def rawaddcounter(self, object, counter, instance=None, inum=-1, machine=None):
        """
        Adds a single counter path, without catching any exceptions.

        See addcounter for details.
        """
        path = win32pdh.MakeCounterPath(
            (machine, object, instance, None, inum, counter)
        )
        self.paths.append(path)

    def addcounter(self, object, counter, instance=None, inum=-1, machine=None):
        """
        Adds a single counter path to the paths attribute.  Normally
        this will be called by a child class' speciality functions,
        rather than being called directly by the user. (Though it isn't
        hard to call manually, since almost everything is given a default)
        This method is only functional when the query is closed (or hasn't
        yet been opened).  This is to prevent conflict in multi-threaded
        query applications).
        e.g.:
                query.addcounter('Memory','Available Bytes')
        """
        if not self.active:
            try:
                self.rawaddcounter(object, counter, instance, inum, machine)
                return 0
            except win32api.error:
                return -1
        else:
            return -1

    def open(self):
        """
        Build the base query object for this wrapper,
        then add all of the counters required for the query.
        Raise a QueryError if we can't complete the functions.
        If we are already open, then do nothing.
        """
        if not self.active:  # to prevent having multiple open queries
            # curpaths are made accessible here because of the possibility of volatile paths
            # which may be dynamically altered by subclasses.
            self.curpaths = copy.copy(self.paths)
            try:
                base = win32pdh.OpenQuery()
                for path in self.paths:
                    try:
                        self.counters.append(win32pdh.AddCounter(base, path))
                    except win32api.error:  # we passed a bad path
                        self.counters.append(0)
                        pass
                self._base = base
                self.active = 1
                return 0  # open succeeded
            except:  # if we encounter any errors, kill the Query
                try:
                    self.killbase(base)
                except NameError:  # failed in creating query
                    pass
                self.active = 0
                self.curpaths = []
                raise QueryError(self)
        return 1  # already open

    def killbase(self, base=None):
        """
        ### This is not a public method
        Mission critical function to kill the win32pdh objects held
        by this object.  User's should generally use the close method
        instead of this method, in case a sub-class has overridden
        close to provide some special functionality.
        """
        # Kill Pythonic references to the objects in this object's namespace
        self._base = None
        counters = self.counters
        self.counters = []
        # we don't kill the curpaths for convenience, this allows the
        # user to close a query and still access the last paths
        self.active = 0
        # Now call the delete functions on all of the objects
        try:
            map(win32pdh.RemoveCounter, counters)
        except:
            pass
        try:
            win32pdh.CloseQuery(base)
        except:
            pass
        del counters
        del base

    def close(self):
        """
        Makes certain that the underlying query object has been closed,
        and that all counters have been removed from it.  This is
        important for reference counting.
        You should only need to call close if you have previously called
        open.  The collectdata methods all can handle opening and
        closing the query.  Calling close multiple times is acceptable.
        """
        try:
            self.killbase(self._base)
        except AttributeError:
            self.killbase()

    __del__ = close

    def collectdata(self, format=win32pdh.PDH_FMT_LONG):
        """
        Returns the formatted current values for the Query
        """
        if self._base:  # we are currently open, don't change this
            return self.collectdataslave(format)
        else:  # need to open and then close the _base, should be used by one-offs and elements tracking application instances
            self.open()  # will raise QueryError if couldn't open the query
            temp = self.collectdataslave(format)
            self.close()  # will always close
            return temp

    def collectdataslave(self, format=win32pdh.PDH_FMT_LONG):
        """
        ### Not a public method
        Called only when the Query is known to be open, runs over
        the whole set of counters, appending results to the temp,
        returns the values as a list.
        """
        try:
            win32pdh.CollectQueryData(self._base)
            temp = []
            for counter in self.counters:
                ok = 0
                try:
                    if counter:
                        temp.append(
                            win32pdh.GetFormattedCounterValue(counter, format)[1]
                        )
                        ok = 1
                except win32api.error:
                    pass
                if not ok:
                    temp.append(-1)  # a better way to signal failure???
            return temp
        # will happen if, for instance, no counters are part of the query and we attempt to collect data for it.
        except win32api.error:
            return [-1] * len(self.counters)

    # pickle functions
    def __getinitargs__(self):
        """
        ### Not a public method
        """
        return (self.paths,)


class Query(BaseQuery):
    """
    Performance Data Helper(PDH) Query object:

    Provides a wrapper around the native PDH query object which
    allows for query reuse, query storage, and general maintenance
    functions (adding counter paths in various ways being the most
    obvious ones).
    """

    def __init__(self, *args, **namedargs):
        """
        The PDH Query object is initialised with a single, optional
        list argument, that must be properly formatted PDH Counter
        paths.  Generally this list will only be provided by the class
        when it is being unpickled (removed from storage).  Normal
        use is to call the class with no arguments and use the various
        addcounter functions (particularly, for end user's, the use of
        addcounterbybrowsing is the most common approach)  You might
        want to provide the list directly if you want to hard-code the
        elements with which your query deals (and thereby avoid the
        overhead of unpickling the class).
        """
        self.volatilecounters = []
        BaseQuery.__init__(*(self,) + args, **namedargs)

    def addperfcounter(self, object, counter, machine=None):
        """
        A "Performance Counter" is a stable, known, common counter,
        such as Memory, or Processor.  The use of addperfcounter by
        end-users is deprecated, since the use of
        addcounterbybrowsing is considerably more flexible and general.
        It is provided here to allow the easy development of scripts
        which need to access variables so common we know them by name
        (such as Memory|Available Bytes), and to provide symmetry with
        the add inst counter method.
        usage:
                query.addperfcounter('Memory', 'Available Bytes')
        It is just as easy to access addcounter directly, the following
        has an identicle effect.
                query.addcounter('Memory', 'Available Bytes')
        """
        BaseQuery.addcounter(self, object=object, counter=counter, machine=machine)

    def addinstcounter(
        self,
        object,
        counter,
        machine=None,
        objtype="Process",
        volatile=1,
        format=win32pdh.PDH_FMT_LONG,
    ):
        """
        The purpose of using an instcounter is to track particular
        instances of a counter object (e.g. a single processor, a single
        running copy of a process).  For instance, to track all python.exe
        instances, you would need merely to ask:
                query.addinstcounter('python','Virtual Bytes')
        You can find the names of the objects and their available counters
        by doing an addcounterbybrowsing() call on a query object (or by
        looking in performance monitor's add dialog.)

        Beyond merely rearranging the call arguments to make more sense,
        if the volatile flag is true, the instcounters also recalculate
        the paths of the available instances on every call to open the
        query.
        """
        if volatile:
            self.volatilecounters.append((object, counter, machine, objtype, format))
        else:
            self.paths[len(self.paths) :] = self.getinstpaths(
                object, counter, machine, objtype, format
            )

    def getinstpaths(
        self,
        object,
        counter,
        machine=None,
        objtype="Process",
        format=win32pdh.PDH_FMT_LONG,
    ):
        """
        ### Not an end-user function
        Calculate the paths for an instance object. Should alter
        to allow processing for lists of object-counter pairs.
        """
        items, instances = win32pdh.EnumObjectItems(None, None, objtype, -1)
        # find out how many instances of this element we have...
        instances.sort()
        try:
            cur = instances.index(object)
        except ValueError:
            return []  # no instances of this object
        temp = [object]
        try:
            while instances[cur + 1] == object:
                temp.append(object)
                cur += 1
        except IndexError:  # if we went over the end
            pass
        paths = []
        for ind in range(len(temp)):
            # can this raise an error?
            paths.append(
                win32pdh.MakeCounterPath(
                    (machine, "Process", object, None, ind, counter)
                )
            )
        return paths  # should also return the number of elements for naming purposes

    def open(self, *args, **namedargs):
        """
        Explicitly open a query:
        When you are needing to make multiple calls to the same query,
        it is most efficient to open the query, run all of the calls,
        then close the query, instead of having the collectdata method
        automatically open and close the query each time it runs.
        There are currently no arguments to open.
        """
        # do all the normal opening stuff, self._base is now the query object
        BaseQuery.open(*(self,) + args, **namedargs)
        # should rewrite getinstpaths to take a single tuple
        paths = []
        for tup in self.volatilecounters:
            paths[len(paths) :] = self.getinstpaths(*tup)
        for path in paths:
            try:
                self.counters.append(win32pdh.AddCounter(self._base, path))
                self.curpaths.append(
                    path
                )  # if we fail on the line above, this path won't be in the table or the counters
            except win32api.error:
                pass  # again, what to do with a malformed path???

    def collectdatafor(self, totalperiod, period=1):
        """
        Non-threaded collection of performance data:
        This method allows you to specify the total period for which you would
        like to run the Query, and the time interval between individual
        runs.  The collected data is stored in query.curresults at the
        _end_ of the run.  The pathnames for the query are stored in
        query.curpaths.
        e.g.:
                query.collectdatafor(30,2)
        Will collect data for 30seconds at 2 second intervals
        """
        tempresults = []
        try:
            self.open()
            for ind in range(int(totalperiod / period)):
                tempresults.append(self.collectdata())
                time.sleep(period)
            self.curresults = tempresults
        finally:
            self.close()

    def collectdatawhile(self, period=1):
        """
        Threaded collection of performance data:
        This method sets up a simple semaphore system for signalling
        when you would like to start and stop a threaded data collection
        method.  The collection runs every period seconds until the
        semaphore attribute is set to a non-true value (which normally
        should be done by calling query.collectdatawhile_stop() .)
        e.g.:
                query.collectdatawhile(2)
                # starts the query running, returns control to the caller immediately
                # is collecting data every two seconds.
                # do whatever you want to do while the thread runs, then call:
                query.collectdatawhile_stop()
                # when you want to deal with the data.  It is generally a good idea
                # to sleep for period seconds yourself, since the query will not copy
                # the required data until the next iteration:
                time.sleep(2)
                # now you can access the data from the attributes of the query
                query.curresults
                query.curpaths
        """
        self.collectdatawhile_active = 1
        _thread.start_new_thread(self.collectdatawhile_slave, (period,))

    def collectdatawhile_stop(self):
        """
        Signals the collectdatawhile slave thread to stop collecting data
        on the next logging iteration.
        """
        self.collectdatawhile_active = 0

    def collectdatawhile_slave(self, period):
        """
        ### Not a public function
        Does the threaded work of collecting the data and storing it
        in an attribute of the class.
        """
        tempresults = []
        try:
            self.open()  # also sets active, so can't be changed.
            while self.collectdatawhile_active:
                tempresults.append(self.collectdata())
                time.sleep(period)
            self.curresults = tempresults
        finally:
            self.close()

    # pickle functions
    def __getinitargs__(self):
        return (self.paths,)

    def __getstate__(self):
        return self.volatilecounters

    def __setstate__(self, volatilecounters):
        self.volatilecounters = volatilecounters


class QueryError(Exception):
    def __init__(self, query: BaseQuery):
        self.query = query

    def __repr__(self):
        return f"<Query Error in {self.query!r}>"

    __str__ = __repr__

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_index_tricks.py ===
import pytest

import numpy as np
from numpy.lib._index_tricks_impl import (
    c_,
    diag_indices,
    diag_indices_from,
    fill_diagonal,
    index_exp,
    ix_,
    mgrid,
    ndenumerate,
    ndindex,
    ogrid,
    r_,
    s_,
)
from numpy.testing import (
    assert_,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
)


class TestRavelUnravelIndex:
    def test_basic(self):
        assert_equal(np.unravel_index(2, (2, 2)), (1, 0))

        # test that new shape argument works properly
        assert_equal(np.unravel_index(indices=2,
                                      shape=(2, 2)),
                                      (1, 0))

        # test that an invalid second keyword argument
        # is properly handled, including the old name `dims`.
        with assert_raises(TypeError):
            np.unravel_index(indices=2, hape=(2, 2))

        with assert_raises(TypeError):
            np.unravel_index(2, hape=(2, 2))

        with assert_raises(TypeError):
            np.unravel_index(254, ims=(17, 94))

        with assert_raises(TypeError):
            np.unravel_index(254, dims=(17, 94))

        assert_equal(np.ravel_multi_index((1, 0), (2, 2)), 2)
        assert_equal(np.unravel_index(254, (17, 94)), (2, 66))
        assert_equal(np.ravel_multi_index((2, 66), (17, 94)), 254)
        assert_raises(ValueError, np.unravel_index, -1, (2, 2))
        assert_raises(TypeError, np.unravel_index, 0.5, (2, 2))
        assert_raises(ValueError, np.unravel_index, 4, (2, 2))
        assert_raises(ValueError, np.ravel_multi_index, (-3, 1), (2, 2))
        assert_raises(ValueError, np.ravel_multi_index, (2, 1), (2, 2))
        assert_raises(ValueError, np.ravel_multi_index, (0, -3), (2, 2))
        assert_raises(ValueError, np.ravel_multi_index, (0, 2), (2, 2))
        assert_raises(TypeError, np.ravel_multi_index, (0.1, 0.), (2, 2))

        assert_equal(np.unravel_index((2 * 3 + 1) * 6 + 4, (4, 3, 6)), [2, 1, 4])
        assert_equal(
            np.ravel_multi_index([2, 1, 4], (4, 3, 6)), (2 * 3 + 1) * 6 + 4)

        arr = np.array([[3, 6, 6], [4, 5, 1]])
        assert_equal(np.ravel_multi_index(arr, (7, 6)), [22, 41, 37])
        assert_equal(
            np.ravel_multi_index(arr, (7, 6), order='F'), [31, 41, 13])
        assert_equal(
            np.ravel_multi_index(arr, (4, 6), mode='clip'), [22, 23, 19])
        assert_equal(np.ravel_multi_index(arr, (4, 4), mode=('clip', 'wrap')),
                     [12, 13, 13])
        assert_equal(np.ravel_multi_index((3, 1, 4, 1), (6, 7, 8, 9)), 1621)

        assert_equal(np.unravel_index(np.array([22, 41, 37]), (7, 6)),
                     [[3, 6, 6], [4, 5, 1]])
        assert_equal(
            np.unravel_index(np.array([31, 41, 13]), (7, 6), order='F'),
            [[3, 6, 6], [4, 5, 1]])
        assert_equal(np.unravel_index(1621, (6, 7, 8, 9)), [3, 1, 4, 1])

    def test_empty_indices(self):
        msg1 = 'indices must be integral: the provided empty sequence was'
        msg2 = 'only int indices permitted'
        assert_raises_regex(TypeError, msg1, np.unravel_index, [], (10, 3, 5))
        assert_raises_regex(TypeError, msg1, np.unravel_index, (), (10, 3, 5))
        assert_raises_regex(TypeError, msg2, np.unravel_index, np.array([]),
                            (10, 3, 5))
        assert_equal(np.unravel_index(np.array([], dtype=int), (10, 3, 5)),
                     [[], [], []])
        assert_raises_regex(TypeError, msg1, np.ravel_multi_index, ([], []),
                            (10, 3))
        assert_raises_regex(TypeError, msg1, np.ravel_multi_index, ([], ['abc']),
                            (10, 3))
        assert_raises_regex(TypeError, msg2, np.ravel_multi_index,
                    (np.array([]), np.array([])), (5, 3))
        assert_equal(np.ravel_multi_index(
                (np.array([], dtype=int), np.array([], dtype=int)), (5, 3)), [])
        assert_equal(np.ravel_multi_index(np.array([[], []], dtype=int),
                     (5, 3)), [])

    def test_big_indices(self):
        # ravel_multi_index for big indices (issue #7546)
        if np.intp == np.int64:
            arr = ([1, 29], [3, 5], [3, 117], [19, 2],
                   [2379, 1284], [2, 2], [0, 1])
            assert_equal(
                np.ravel_multi_index(arr, (41, 7, 120, 36, 2706, 8, 6)),
                [5627771580, 117259570957])

        # test unravel_index for big indices (issue #9538)
        assert_raises(ValueError, np.unravel_index, 1, (2**32 - 1, 2**31 + 1))

        # test overflow checking for too big array (issue #7546)
        dummy_arr = ([0], [0])
        half_max = np.iinfo(np.intp).max // 2
        assert_equal(
            np.ravel_multi_index(dummy_arr, (half_max, 2)), [0])
        assert_raises(ValueError,
            np.ravel_multi_index, dummy_arr, (half_max + 1, 2))
        assert_equal(
            np.ravel_multi_index(dummy_arr, (half_max, 2), order='F'), [0])
        assert_raises(ValueError,
            np.ravel_multi_index, dummy_arr, (half_max + 1, 2), order='F')

    def test_dtypes(self):
        # Test with different data types
        for dtype in [np.int16, np.uint16, np.int32,
                      np.uint32, np.int64, np.uint64]:
            coords = np.array(
                [[1, 0, 1, 2, 3, 4], [1, 6, 1, 3, 2, 0]], dtype=dtype)
            shape = (5, 8)
            uncoords = 8 * coords[0] + coords[1]
            assert_equal(np.ravel_multi_index(coords, shape), uncoords)
            assert_equal(coords, np.unravel_index(uncoords, shape))
            uncoords = coords[0] + 5 * coords[1]
            assert_equal(
                np.ravel_multi_index(coords, shape, order='F'), uncoords)
            assert_equal(coords, np.unravel_index(uncoords, shape, order='F'))

            coords = np.array(
                [[1, 0, 1, 2, 3, 4], [1, 6, 1, 3, 2, 0], [1, 3, 1, 0, 9, 5]],
                dtype=dtype)
            shape = (5, 8, 10)
            uncoords = 10 * (8 * coords[0] + coords[1]) + coords[2]
            assert_equal(np.ravel_multi_index(coords, shape), uncoords)
            assert_equal(coords, np.unravel_index(uncoords, shape))
            uncoords = coords[0] + 5 * (coords[1] + 8 * coords[2])
            assert_equal(
                np.ravel_multi_index(coords, shape, order='F'), uncoords)
            assert_equal(coords, np.unravel_index(uncoords, shape, order='F'))

    def test_clipmodes(self):
        # Test clipmodes
        assert_equal(
            np.ravel_multi_index([5, 1, -1, 2], (4, 3, 7, 12), mode='wrap'),
            np.ravel_multi_index([1, 1, 6, 2], (4, 3, 7, 12)))
        assert_equal(np.ravel_multi_index([5, 1, -1, 2], (4, 3, 7, 12),
                                          mode=(
                                              'wrap', 'raise', 'clip', 'raise')),
                     np.ravel_multi_index([1, 1, 0, 2], (4, 3, 7, 12)))
        assert_raises(
            ValueError, np.ravel_multi_index, [5, 1, -1, 2], (4, 3, 7, 12))

    def test_writeability(self):
        # gh-7269
        x, y = np.unravel_index([1, 2, 3], (4, 5))
        assert_(x.flags.writeable)
        assert_(y.flags.writeable)

    def test_0d(self):
        # gh-580
        x = np.unravel_index(0, ())
        assert_equal(x, ())

        assert_raises_regex(ValueError, "0d array", np.unravel_index, [0], ())
        assert_raises_regex(
            ValueError, "out of bounds", np.unravel_index, [1], ())

    @pytest.mark.parametrize("mode", ["clip", "wrap", "raise"])
    def test_empty_array_ravel(self, mode):
        res = np.ravel_multi_index(
                    np.zeros((3, 0), dtype=np.intp), (2, 1, 0), mode=mode)
        assert res.shape == (0,)

        with assert_raises(ValueError):
            np.ravel_multi_index(
                    np.zeros((3, 1), dtype=np.intp), (2, 1, 0), mode=mode)

    def test_empty_array_unravel(self):
        res = np.unravel_index(np.zeros(0, dtype=np.intp), (2, 1, 0))
        # res is a tuple of three empty arrays
        assert len(res) == 3
        assert all(a.shape == (0,) for a in res)

        with assert_raises(ValueError):
            np.unravel_index([1], (2, 1, 0))

class TestGrid:
    def test_basic(self):
        a = mgrid[-1:1:10j]
        b = mgrid[-1:1:0.1]
        assert_(a.shape == (10,))
        assert_(b.shape == (20,))
        assert_(a[0] == -1)
        assert_almost_equal(a[-1], 1)
        assert_(b[0] == -1)
        assert_almost_equal(b[1] - b[0], 0.1, 11)
        assert_almost_equal(b[-1], b[0] + 19 * 0.1, 11)
        assert_almost_equal(a[1] - a[0], 2.0 / 9.0, 11)

    def test_linspace_equivalence(self):
        y, st = np.linspace(2, 10, retstep=True)
        assert_almost_equal(st, 8 / 49.0)
        assert_array_almost_equal(y, mgrid[2:10:50j], 13)

    def test_nd(self):
        c = mgrid[-1:1:10j, -2:2:10j]
        d = mgrid[-1:1:0.1, -2:2:0.2]
        assert_(c.shape == (2, 10, 10))
        assert_(d.shape == (2, 20, 20))
        assert_array_equal(c[0][0, :], -np.ones(10, 'd'))
        assert_array_equal(c[1][:, 0], -2 * np.ones(10, 'd'))
        assert_array_almost_equal(c[0][-1, :], np.ones(10, 'd'), 11)
        assert_array_almost_equal(c[1][:, -1], 2 * np.ones(10, 'd'), 11)
        assert_array_almost_equal(d[0, 1, :] - d[0, 0, :],
                                  0.1 * np.ones(20, 'd'), 11)
        assert_array_almost_equal(d[1, :, 1] - d[1, :, 0],
                                  0.2 * np.ones(20, 'd'), 11)

    def test_sparse(self):
        grid_full = mgrid[-1:1:10j, -2:2:10j]
        grid_sparse = ogrid[-1:1:10j, -2:2:10j]

        # sparse grids can be made dense by broadcasting
        grid_broadcast = np.broadcast_arrays(*grid_sparse)
        for f, b in zip(grid_full, grid_broadcast):
            assert_equal(f, b)

    @pytest.mark.parametrize("start, stop, step, expected", [
        (None, 10, 10j, (200, 10)),
        (-10, 20, None, (1800, 30)),
        ])
    def test_mgrid_size_none_handling(self, start, stop, step, expected):
        # regression test None value handling for
        # start and step values used by mgrid;
        # internally, this aims to cover previously
        # unexplored code paths in nd_grid()
        grid = mgrid[start:stop:step, start:stop:step]
        # need a smaller grid to explore one of the
        # untested code paths
        grid_small = mgrid[start:stop:step]
        assert_equal(grid.size, expected[0])
        assert_equal(grid_small.size, expected[1])

    def test_accepts_npfloating(self):
        # regression test for #16466
        grid64 = mgrid[0.1:0.33:0.1, ]
        grid32 = mgrid[np.float32(0.1):np.float32(0.33):np.float32(0.1), ]
        assert_array_almost_equal(grid64, grid32)
        # At some point this was float64, but NEP 50 changed it:
        assert grid32.dtype == np.float32
        assert grid64.dtype == np.float64

        # different code path for single slice
        grid64 = mgrid[0.1:0.33:0.1]
        grid32 = mgrid[np.float32(0.1):np.float32(0.33):np.float32(0.1)]
        assert_(grid32.dtype == np.float64)
        assert_array_almost_equal(grid64, grid32)

    def test_accepts_longdouble(self):
        # regression tests for #16945
        grid64 = mgrid[0.1:0.33:0.1, ]
        grid128 = mgrid[
            np.longdouble(0.1):np.longdouble(0.33):np.longdouble(0.1),
        ]
        assert_(grid128.dtype == np.longdouble)
        assert_array_almost_equal(grid64, grid128)

        grid128c_a = mgrid[0:np.longdouble(1):3.4j]
        grid128c_b = mgrid[0:np.longdouble(1):3.4j, ]
        assert_(grid128c_a.dtype == grid128c_b.dtype == np.longdouble)
        assert_array_equal(grid128c_a, grid128c_b[0])

        # different code path for single slice
        grid64 = mgrid[0.1:0.33:0.1]
        grid128 = mgrid[
            np.longdouble(0.1):np.longdouble(0.33):np.longdouble(0.1)
        ]
        assert_(grid128.dtype == np.longdouble)
        assert_array_almost_equal(grid64, grid128)

    def test_accepts_npcomplexfloating(self):
        # Related to #16466
        assert_array_almost_equal(
            mgrid[0.1:0.3:3j, ], mgrid[0.1:0.3:np.complex64(3j), ]
        )

        # different code path for single slice
        assert_array_almost_equal(
            mgrid[0.1:0.3:3j], mgrid[0.1:0.3:np.complex64(3j)]
        )

        # Related to #16945
        grid64_a = mgrid[0.1:0.3:3.3j]
        grid64_b = mgrid[0.1:0.3:3.3j, ][0]
        assert_(grid64_a.dtype == grid64_b.dtype == np.float64)
        assert_array_equal(grid64_a, grid64_b)

        grid128_a = mgrid[0.1:0.3:np.clongdouble(3.3j)]
        grid128_b = mgrid[0.1:0.3:np.clongdouble(3.3j), ][0]
        assert_(grid128_a.dtype == grid128_b.dtype == np.longdouble)
        assert_array_equal(grid64_a, grid64_b)


class TestConcatenator:
    def test_1d(self):
        assert_array_equal(r_[1, 2, 3, 4, 5, 6], np.array([1, 2, 3, 4, 5, 6]))
        b = np.ones(5)
        c = r_[b, 0, 0, b]
        assert_array_equal(c, [1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1])

    def test_mixed_type(self):
        g = r_[10.1, 1:10]
        assert_(g.dtype == 'f8')

    def test_more_mixed_type(self):
        g = r_[-10.1, np.array([1]), np.array([2, 3, 4]), 10.0]
        assert_(g.dtype == 'f8')

    def test_complex_step(self):
        # Regression test for #12262
        g = r_[0:36:100j]
        assert_(g.shape == (100,))

        # Related to #16466
        g = r_[0:36:np.complex64(100j)]
        assert_(g.shape == (100,))

    def test_2d(self):
        b = np.random.rand(5, 5)
        c = np.random.rand(5, 5)
        d = r_['1', b, c]  # append columns
        assert_(d.shape == (5, 10))
        assert_array_equal(d[:, :5], b)
        assert_array_equal(d[:, 5:], c)
        d = r_[b, c]
        assert_(d.shape == (10, 5))
        assert_array_equal(d[:5, :], b)
        assert_array_equal(d[5:, :], c)

    def test_0d(self):
        assert_equal(r_[0, np.array(1), 2], [0, 1, 2])
        assert_equal(r_[[0, 1, 2], np.array(3)], [0, 1, 2, 3])
        assert_equal(r_[np.array(0), [1, 2, 3]], [0, 1, 2, 3])


class TestNdenumerate:
    def test_basic(self):
        a = np.array([[1, 2], [3, 4]])
        assert_equal(list(ndenumerate(a)),
                     [((0, 0), 1), ((0, 1), 2), ((1, 0), 3), ((1, 1), 4)])


class TestIndexExpression:
    def test_regression_1(self):
        # ticket #1196
        a = np.arange(2)
        assert_equal(a[:-1], a[s_[:-1]])
        assert_equal(a[:-1], a[index_exp[:-1]])

    def test_simple_1(self):
        a = np.random.rand(4, 5, 6)

        assert_equal(a[:, :3, [1, 2]], a[index_exp[:, :3, [1, 2]]])
        assert_equal(a[:, :3, [1, 2]], a[s_[:, :3, [1, 2]]])


class TestIx_:
    def test_regression_1(self):
        # Test empty untyped inputs create outputs of indexing type, gh-5804
        a, = np.ix_(range(0))
        assert_equal(a.dtype, np.intp)

        a, = np.ix_([])
        assert_equal(a.dtype, np.intp)

        # but if the type is specified, don't change it
        a, = np.ix_(np.array([], dtype=np.float32))
        assert_equal(a.dtype, np.float32)

    def test_shape_and_dtype(self):
        sizes = (4, 5, 3, 2)
        # Test both lists and arrays
        for func in (range, np.arange):
            arrays = np.ix_(*[func(sz) for sz in sizes])
            for k, (a, sz) in enumerate(zip(arrays, sizes)):
                assert_equal(a.shape[k], sz)
                assert_(all(sh == 1 for j, sh in enumerate(a.shape) if j != k))
                assert_(np.issubdtype(a.dtype, np.integer))

    def test_bool(self):
        bool_a = [True, False, True, True]
        int_a, = np.nonzero(bool_a)
        assert_equal(np.ix_(bool_a)[0], int_a)

    def test_1d_only(self):
        idx2d = [[1, 2, 3], [4, 5, 6]]
        assert_raises(ValueError, np.ix_, idx2d)

    def test_repeated_input(self):
        length_of_vector = 5
        x = np.arange(length_of_vector)
        out = ix_(x, x)
        assert_equal(out[0].shape, (length_of_vector, 1))
        assert_equal(out[1].shape, (1, length_of_vector))
        # check that input shape is not modified
        assert_equal(x.shape, (length_of_vector,))


def test_c_():
    a = c_[np.array([[1, 2, 3]]), 0, 0, np.array([[4, 5, 6]])]
    assert_equal(a, [[1, 2, 3, 0, 0, 4, 5, 6]])


class TestFillDiagonal:
    def test_basic(self):
        a = np.zeros((3, 3), int)
        fill_diagonal(a, 5)
        assert_array_equal(
            a, np.array([[5, 0, 0],
                         [0, 5, 0],
                         [0, 0, 5]])
            )

    def test_tall_matrix(self):
        a = np.zeros((10, 3), int)
        fill_diagonal(a, 5)
        assert_array_equal(
            a, np.array([[5, 0, 0],
                         [0, 5, 0],
                         [0, 0, 5],
                         [0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0],
                         [0, 0, 0]])
            )

    def test_tall_matrix_wrap(self):
        a = np.zeros((10, 3), int)
        fill_diagonal(a, 5, True)
        assert_array_equal(
            a, np.array([[5, 0, 0],
                         [0, 5, 0],
                         [0, 0, 5],
                         [0, 0, 0],
                         [5, 0, 0],
                         [0, 5, 0],
                         [0, 0, 5],
                         [0, 0, 0],
                         [5, 0, 0],
                         [0, 5, 0]])
            )

    def test_wide_matrix(self):
        a = np.zeros((3, 10), int)
        fill_diagonal(a, 5)
        assert_array_equal(
            a, np.array([[5, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                         [0, 5, 0, 0, 0, 0, 0, 0, 0, 0],
                         [0, 0, 5, 0, 0, 0, 0, 0, 0, 0]])
            )

    def test_operate_4d_array(self):
        a = np.zeros((3, 3, 3, 3), int)
        fill_diagonal(a, 4)
        i = np.array([0, 1, 2])
        assert_equal(np.where(a != 0), (i, i, i, i))

    def test_low_dim_handling(self):
        # raise error with low dimensionality
        a = np.zeros(3, int)
        with assert_raises_regex(ValueError, "at least 2-d"):
            fill_diagonal(a, 5)

    def test_hetero_shape_handling(self):
        # raise error with high dimensionality and
        # shape mismatch
        a = np.zeros((3, 3, 7, 3), int)
        with assert_raises_regex(ValueError, "equal length"):
            fill_diagonal(a, 2)


def test_diag_indices():
    di = diag_indices(4)
    a = np.array([[1, 2, 3, 4],
                  [5, 6, 7, 8],
                  [9, 10, 11, 12],
                  [13, 14, 15, 16]])
    a[di] = 100
    assert_array_equal(
        a, np.array([[100, 2, 3, 4],
                     [5, 100, 7, 8],
                     [9, 10, 100, 12],
                     [13, 14, 15, 100]])
        )

    # Now, we create indices to manipulate a 3-d array:
    d3 = diag_indices(2, 3)

    # And use it to set the diagonal of a zeros array to 1:
    a = np.zeros((2, 2, 2), int)
    a[d3] = 1
    assert_array_equal(
        a, np.array([[[1, 0],
                      [0, 0]],
                     [[0, 0],
                      [0, 1]]])
        )


class TestDiagIndicesFrom:

    def test_diag_indices_from(self):
        x = np.random.random((4, 4))
        r, c = diag_indices_from(x)
        assert_array_equal(r, np.arange(4))
        assert_array_equal(c, np.arange(4))

    def test_error_small_input(self):
        x = np.ones(7)
        with assert_raises_regex(ValueError, "at least 2-d"):
            diag_indices_from(x)

    def test_error_shape_mismatch(self):
        x = np.zeros((3, 3, 2, 3), int)
        with assert_raises_regex(ValueError, "equal length"):
            diag_indices_from(x)


def test_ndindex():
    x = list(ndindex(1, 2, 3))
    expected = [ix for ix, e in ndenumerate(np.zeros((1, 2, 3)))]
    assert_array_equal(x, expected)

    x = list(ndindex((1, 2, 3)))
    assert_array_equal(x, expected)

    # Test use of scalars and tuples
    x = list(ndindex((3,)))
    assert_array_equal(x, list(ndindex(3)))

    # Make sure size argument is optional
    x = list(ndindex())
    assert_equal(x, [()])

    x = list(ndindex(()))
    assert_equal(x, [()])

    # Make sure 0-sized ndindex works correctly
    x = list(ndindex(*[0]))
    assert_equal(x, [])

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_twodim_base.py ===
"""Test functions for matrix module

"""
import pytest

import numpy as np
from numpy import (
    add,
    arange,
    array,
    diag,
    eye,
    fliplr,
    flipud,
    histogram2d,
    mask_indices,
    ones,
    tri,
    tril_indices,
    tril_indices_from,
    triu_indices,
    triu_indices_from,
    vander,
    zeros,
)
from numpy.testing import (
    assert_,
    assert_array_almost_equal,
    assert_array_equal,
    assert_array_max_ulp,
    assert_equal,
    assert_raises,
)


def get_mat(n):
    data = arange(n)
    data = add.outer(data, data)
    return data


class TestEye:
    def test_basic(self):
        assert_equal(eye(4),
                     array([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]]))

        assert_equal(eye(4, dtype='f'),
                     array([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]], 'f'))

        assert_equal(eye(3) == 1,
                     eye(3, dtype=bool))

    def test_uint64(self):
        # Regression test for gh-9982
        assert_equal(eye(np.uint64(2), dtype=int), array([[1, 0], [0, 1]]))
        assert_equal(eye(np.uint64(2), M=np.uint64(4), k=np.uint64(1)),
                     array([[0, 1, 0, 0], [0, 0, 1, 0]]))

    def test_diag(self):
        assert_equal(eye(4, k=1),
                     array([[0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1],
                            [0, 0, 0, 0]]))

        assert_equal(eye(4, k=-1),
                     array([[0, 0, 0, 0],
                            [1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0]]))

    def test_2d(self):
        assert_equal(eye(4, 3),
                     array([[1, 0, 0],
                            [0, 1, 0],
                            [0, 0, 1],
                            [0, 0, 0]]))

        assert_equal(eye(3, 4),
                     array([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0]]))

    def test_diag2d(self):
        assert_equal(eye(3, 4, k=2),
                     array([[0, 0, 1, 0],
                            [0, 0, 0, 1],
                            [0, 0, 0, 0]]))

        assert_equal(eye(4, 3, k=-2),
                     array([[0, 0, 0],
                            [0, 0, 0],
                            [1, 0, 0],
                            [0, 1, 0]]))

    def test_eye_bounds(self):
        assert_equal(eye(2, 2, 1), [[0, 1], [0, 0]])
        assert_equal(eye(2, 2, -1), [[0, 0], [1, 0]])
        assert_equal(eye(2, 2, 2), [[0, 0], [0, 0]])
        assert_equal(eye(2, 2, -2), [[0, 0], [0, 0]])
        assert_equal(eye(3, 2, 2), [[0, 0], [0, 0], [0, 0]])
        assert_equal(eye(3, 2, 1), [[0, 1], [0, 0], [0, 0]])
        assert_equal(eye(3, 2, -1), [[0, 0], [1, 0], [0, 1]])
        assert_equal(eye(3, 2, -2), [[0, 0], [0, 0], [1, 0]])
        assert_equal(eye(3, 2, -3), [[0, 0], [0, 0], [0, 0]])

    def test_strings(self):
        assert_equal(eye(2, 2, dtype='S3'),
                     [[b'1', b''], [b'', b'1']])

    def test_bool(self):
        assert_equal(eye(2, 2, dtype=bool), [[True, False], [False, True]])

    def test_order(self):
        mat_c = eye(4, 3, k=-1)
        mat_f = eye(4, 3, k=-1, order='F')
        assert_equal(mat_c, mat_f)
        assert mat_c.flags.c_contiguous
        assert not mat_c.flags.f_contiguous
        assert not mat_f.flags.c_contiguous
        assert mat_f.flags.f_contiguous


class TestDiag:
    def test_vector(self):
        vals = (100 * arange(5)).astype('l')
        b = zeros((5, 5))
        for k in range(5):
            b[k, k] = vals[k]
        assert_equal(diag(vals), b)
        b = zeros((7, 7))
        c = b.copy()
        for k in range(5):
            b[k, k + 2] = vals[k]
            c[k + 2, k] = vals[k]
        assert_equal(diag(vals, k=2), b)
        assert_equal(diag(vals, k=-2), c)

    def test_matrix(self, vals=None):
        if vals is None:
            vals = (100 * get_mat(5) + 1).astype('l')
        b = zeros((5,))
        for k in range(5):
            b[k] = vals[k, k]
        assert_equal(diag(vals), b)
        b = b * 0
        for k in range(3):
            b[k] = vals[k, k + 2]
        assert_equal(diag(vals, 2), b[:3])
        for k in range(3):
            b[k] = vals[k + 2, k]
        assert_equal(diag(vals, -2), b[:3])

    def test_fortran_order(self):
        vals = array((100 * get_mat(5) + 1), order='F', dtype='l')
        self.test_matrix(vals)

    def test_diag_bounds(self):
        A = [[1, 2], [3, 4], [5, 6]]
        assert_equal(diag(A, k=2), [])
        assert_equal(diag(A, k=1), [2])
        assert_equal(diag(A, k=0), [1, 4])
        assert_equal(diag(A, k=-1), [3, 6])
        assert_equal(diag(A, k=-2), [5])
        assert_equal(diag(A, k=-3), [])

    def test_failure(self):
        assert_raises(ValueError, diag, [[[1]]])


class TestFliplr:
    def test_basic(self):
        assert_raises(ValueError, fliplr, ones(4))
        a = get_mat(4)
        b = a[:, ::-1]
        assert_equal(fliplr(a), b)
        a = [[0, 1, 2],
             [3, 4, 5]]
        b = [[2, 1, 0],
             [5, 4, 3]]
        assert_equal(fliplr(a), b)


class TestFlipud:
    def test_basic(self):
        a = get_mat(4)
        b = a[::-1, :]
        assert_equal(flipud(a), b)
        a = [[0, 1, 2],
             [3, 4, 5]]
        b = [[3, 4, 5],
             [0, 1, 2]]
        assert_equal(flipud(a), b)


class TestHistogram2d:
    def test_simple(self):
        x = array(
            [0.41702200, 0.72032449, 1.1437481e-4, 0.302332573, 0.146755891])
        y = array(
            [0.09233859, 0.18626021, 0.34556073, 0.39676747, 0.53881673])
        xedges = np.linspace(0, 1, 10)
        yedges = np.linspace(0, 1, 10)
        H = histogram2d(x, y, (xedges, yedges))[0]
        answer = array(
            [[0, 0, 0, 1, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 1, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0],
             [1, 0, 1, 0, 0, 0, 0, 0, 0],
             [0, 1, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0],
             [0, 0, 0, 0, 0, 0, 0, 0, 0]])
        assert_array_equal(H.T, answer)
        H = histogram2d(x, y, xedges)[0]
        assert_array_equal(H.T, answer)
        H, xedges, yedges = histogram2d(list(range(10)), list(range(10)))
        assert_array_equal(H, eye(10, 10))
        assert_array_equal(xedges, np.linspace(0, 9, 11))
        assert_array_equal(yedges, np.linspace(0, 9, 11))

    def test_asym(self):
        x = array([1, 1, 2, 3, 4, 4, 4, 5])
        y = array([1, 3, 2, 0, 1, 2, 3, 4])
        H, xed, yed = histogram2d(
            x, y, (6, 5), range=[[0, 6], [0, 5]], density=True)
        answer = array(
            [[0., 0, 0, 0, 0],
             [0, 1, 0, 1, 0],
             [0, 0, 1, 0, 0],
             [1, 0, 0, 0, 0],
             [0, 1, 1, 1, 0],
             [0, 0, 0, 0, 1]])
        assert_array_almost_equal(H, answer / 8., 3)
        assert_array_equal(xed, np.linspace(0, 6, 7))
        assert_array_equal(yed, np.linspace(0, 5, 6))

    def test_density(self):
        x = array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        y = array([1, 1, 1, 2, 2, 2, 3, 3, 3])
        H, xed, yed = histogram2d(
            x, y, [[1, 2, 3, 5], [1, 2, 3, 5]], density=True)
        answer = array([[1, 1, .5],
                        [1, 1, .5],
                        [.5, .5, .25]]) / 9.
        assert_array_almost_equal(H, answer, 3)

    def test_all_outliers(self):
        r = np.random.rand(100) + 1. + 1e6  # histogramdd rounds by decimal=6
        H, xed, yed = histogram2d(r, r, (4, 5), range=([0, 1], [0, 1]))
        assert_array_equal(H, 0)

    def test_empty(self):
        a, edge1, edge2 = histogram2d([], [], bins=([0, 1], [0, 1]))
        assert_array_max_ulp(a, array([[0.]]))

        a, edge1, edge2 = histogram2d([], [], bins=4)
        assert_array_max_ulp(a, np.zeros((4, 4)))

    def test_binparameter_combination(self):
        x = array(
            [0, 0.09207008, 0.64575234, 0.12875982, 0.47390599,
             0.59944483, 1])
        y = array(
            [0, 0.14344267, 0.48988575, 0.30558665, 0.44700682,
             0.15886423, 1])
        edges = (0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1)
        H, xe, ye = histogram2d(x, y, (edges, 4))
        answer = array(
            [[2., 0., 0., 0.],
             [0., 1., 0., 0.],
             [0., 0., 0., 0.],
             [0., 0., 0., 0.],
             [0., 1., 0., 0.],
             [1., 0., 0., 0.],
             [0., 1., 0., 0.],
             [0., 0., 0., 0.],
             [0., 0., 0., 0.],
             [0., 0., 0., 1.]])
        assert_array_equal(H, answer)
        assert_array_equal(ye, array([0., 0.25, 0.5, 0.75, 1]))
        H, xe, ye = histogram2d(x, y, (4, edges))
        answer = array(
            [[1., 1., 0., 1., 0., 0., 0., 0., 0., 0.],
             [0., 0., 0., 0., 1., 0., 0., 0., 0., 0.],
             [0., 1., 0., 0., 1., 0., 0., 0., 0., 0.],
             [0., 0., 0., 0., 0., 0., 0., 0., 0., 1.]])
        assert_array_equal(H, answer)
        assert_array_equal(xe, array([0., 0.25, 0.5, 0.75, 1]))

    def test_dispatch(self):
        class ShouldDispatch:
            def __array_function__(self, function, types, args, kwargs):
                return types, args, kwargs

        xy = [1, 2]
        s_d = ShouldDispatch()
        r = histogram2d(s_d, xy)
        # Cannot use assert_equal since that dispatches...
        assert_(r == ((ShouldDispatch,), (s_d, xy), {}))
        r = histogram2d(xy, s_d)
        assert_(r == ((ShouldDispatch,), (xy, s_d), {}))
        r = histogram2d(xy, xy, bins=s_d)
        assert_(r, ((ShouldDispatch,), (xy, xy), {'bins': s_d}))
        r = histogram2d(xy, xy, bins=[s_d, 5])
        assert_(r, ((ShouldDispatch,), (xy, xy), {'bins': [s_d, 5]}))
        assert_raises(Exception, histogram2d, xy, xy, bins=[s_d])
        r = histogram2d(xy, xy, weights=s_d)
        assert_(r, ((ShouldDispatch,), (xy, xy), {'weights': s_d}))

    @pytest.mark.parametrize(("x_len", "y_len"), [(10, 11), (20, 19)])
    def test_bad_length(self, x_len, y_len):
        x, y = np.ones(x_len), np.ones(y_len)
        with pytest.raises(ValueError,
                           match='x and y must have the same length.'):
            histogram2d(x, y)


class TestTri:
    def test_dtype(self):
        out = array([[1, 0, 0],
                     [1, 1, 0],
                     [1, 1, 1]])
        assert_array_equal(tri(3), out)
        assert_array_equal(tri(3, dtype=bool), out.astype(bool))


def test_tril_triu_ndim2():
    for dtype in np.typecodes['AllFloat'] + np.typecodes['AllInteger']:
        a = np.ones((2, 2), dtype=dtype)
        b = np.tril(a)
        c = np.triu(a)
        assert_array_equal(b, [[1, 0], [1, 1]])
        assert_array_equal(c, b.T)
        # should return the same dtype as the original array
        assert_equal(b.dtype, a.dtype)
        assert_equal(c.dtype, a.dtype)


def test_tril_triu_ndim3():
    for dtype in np.typecodes['AllFloat'] + np.typecodes['AllInteger']:
        a = np.array([
            [[1, 1], [1, 1]],
            [[1, 1], [1, 0]],
            [[1, 1], [0, 0]],
            ], dtype=dtype)
        a_tril_desired = np.array([
            [[1, 0], [1, 1]],
            [[1, 0], [1, 0]],
            [[1, 0], [0, 0]],
            ], dtype=dtype)
        a_triu_desired = np.array([
            [[1, 1], [0, 1]],
            [[1, 1], [0, 0]],
            [[1, 1], [0, 0]],
            ], dtype=dtype)
        a_triu_observed = np.triu(a)
        a_tril_observed = np.tril(a)
        assert_array_equal(a_triu_observed, a_triu_desired)
        assert_array_equal(a_tril_observed, a_tril_desired)
        assert_equal(a_triu_observed.dtype, a.dtype)
        assert_equal(a_tril_observed.dtype, a.dtype)


def test_tril_triu_with_inf():
    # Issue 4859
    arr = np.array([[1, 1, np.inf],
                    [1, 1, 1],
                    [np.inf, 1, 1]])
    out_tril = np.array([[1, 0, 0],
                         [1, 1, 0],
                         [np.inf, 1, 1]])
    out_triu = out_tril.T
    assert_array_equal(np.triu(arr), out_triu)
    assert_array_equal(np.tril(arr), out_tril)


def test_tril_triu_dtype():
    # Issue 4916
    # tril and triu should return the same dtype as input
    for c in np.typecodes['All']:
        if c == 'V':
            continue
        arr = np.zeros((3, 3), dtype=c)
        assert_equal(np.triu(arr).dtype, arr.dtype)
        assert_equal(np.tril(arr).dtype, arr.dtype)

    # check special cases
    arr = np.array([['2001-01-01T12:00', '2002-02-03T13:56'],
                    ['2004-01-01T12:00', '2003-01-03T13:45']],
                   dtype='datetime64')
    assert_equal(np.triu(arr).dtype, arr.dtype)
    assert_equal(np.tril(arr).dtype, arr.dtype)

    arr = np.zeros((3, 3), dtype='f4,f4')
    assert_equal(np.triu(arr).dtype, arr.dtype)
    assert_equal(np.tril(arr).dtype, arr.dtype)


def test_mask_indices():
    # simple test without offset
    iu = mask_indices(3, np.triu)
    a = np.arange(9).reshape(3, 3)
    assert_array_equal(a[iu], array([0, 1, 2, 4, 5, 8]))
    # Now with an offset
    iu1 = mask_indices(3, np.triu, 1)
    assert_array_equal(a[iu1], array([1, 2, 5]))


def test_tril_indices():
    # indices without and with offset
    il1 = tril_indices(4)
    il2 = tril_indices(4, k=2)
    il3 = tril_indices(4, m=5)
    il4 = tril_indices(4, k=2, m=5)

    a = np.array([[1, 2, 3, 4],
                  [5, 6, 7, 8],
                  [9, 10, 11, 12],
                  [13, 14, 15, 16]])
    b = np.arange(1, 21).reshape(4, 5)

    # indexing:
    assert_array_equal(a[il1],
                       array([1, 5, 6, 9, 10, 11, 13, 14, 15, 16]))
    assert_array_equal(b[il3],
                       array([1, 6, 7, 11, 12, 13, 16, 17, 18, 19]))

    # And for assigning values:
    a[il1] = -1
    assert_array_equal(a,
                       array([[-1, 2, 3, 4],
                              [-1, -1, 7, 8],
                              [-1, -1, -1, 12],
                              [-1, -1, -1, -1]]))
    b[il3] = -1
    assert_array_equal(b,
                       array([[-1, 2, 3, 4, 5],
                              [-1, -1, 8, 9, 10],
                              [-1, -1, -1, 14, 15],
                              [-1, -1, -1, -1, 20]]))
    # These cover almost the whole array (two diagonals right of the main one):
    a[il2] = -10
    assert_array_equal(a,
                       array([[-10, -10, -10, 4],
                              [-10, -10, -10, -10],
                              [-10, -10, -10, -10],
                              [-10, -10, -10, -10]]))
    b[il4] = -10
    assert_array_equal(b,
                       array([[-10, -10, -10, 4, 5],
                              [-10, -10, -10, -10, 10],
                              [-10, -10, -10, -10, -10],
                              [-10, -10, -10, -10, -10]]))


class TestTriuIndices:
    def test_triu_indices(self):
        iu1 = triu_indices(4)
        iu2 = triu_indices(4, k=2)
        iu3 = triu_indices(4, m=5)
        iu4 = triu_indices(4, k=2, m=5)

        a = np.array([[1, 2, 3, 4],
                      [5, 6, 7, 8],
                      [9, 10, 11, 12],
                      [13, 14, 15, 16]])
        b = np.arange(1, 21).reshape(4, 5)

        # Both for indexing:
        assert_array_equal(a[iu1],
                           array([1, 2, 3, 4, 6, 7, 8, 11, 12, 16]))
        assert_array_equal(b[iu3],
                           array([1, 2, 3, 4, 5, 7, 8, 9,
                                  10, 13, 14, 15, 19, 20]))

        # And for assigning values:
        a[iu1] = -1
        assert_array_equal(a,
                           array([[-1, -1, -1, -1],
                                  [5, -1, -1, -1],
                                  [9, 10, -1, -1],
                                  [13, 14, 15, -1]]))
        b[iu3] = -1
        assert_array_equal(b,
                           array([[-1, -1, -1, -1, -1],
                                  [6, -1, -1, -1, -1],
                                  [11, 12, -1, -1, -1],
                                  [16, 17, 18, -1, -1]]))

        # These cover almost the whole array (two diagonals right of the
        # main one):
        a[iu2] = -10
        assert_array_equal(a,
                           array([[-1, -1, -10, -10],
                                  [5, -1, -1, -10],
                                  [9, 10, -1, -1],
                                  [13, 14, 15, -1]]))
        b[iu4] = -10
        assert_array_equal(b,
                           array([[-1, -1, -10, -10, -10],
                                  [6, -1, -1, -10, -10],
                                  [11, 12, -1, -1, -10],
                                  [16, 17, 18, -1, -1]]))


class TestTrilIndicesFrom:
    def test_exceptions(self):
        assert_raises(ValueError, tril_indices_from, np.ones((2,)))
        assert_raises(ValueError, tril_indices_from, np.ones((2, 2, 2)))
        # assert_raises(ValueError, tril_indices_from, np.ones((2, 3)))


class TestTriuIndicesFrom:
    def test_exceptions(self):
        assert_raises(ValueError, triu_indices_from, np.ones((2,)))
        assert_raises(ValueError, triu_indices_from, np.ones((2, 2, 2)))
        # assert_raises(ValueError, triu_indices_from, np.ones((2, 3)))


class TestVander:
    def test_basic(self):
        c = np.array([0, 1, -2, 3])
        v = vander(c)
        powers = np.array([[0, 0, 0, 0, 1],
                           [1, 1, 1, 1, 1],
                           [16, -8, 4, -2, 1],
                           [81, 27, 9, 3, 1]])
        # Check default value of N:
        assert_array_equal(v, powers[:, 1:])
        # Check a range of N values, including 0 and 5 (greater than default)
        m = powers.shape[1]
        for n in range(6):
            v = vander(c, N=n)
            assert_array_equal(v, powers[:, m - n:m])

    def test_dtypes(self):
        c = array([11, -12, 13], dtype=np.int8)
        v = vander(c)
        expected = np.array([[121, 11, 1],
                             [144, -12, 1],
                             [169, 13, 1]])
        assert_array_equal(v, expected)

        c = array([1.0 + 1j, 1.0 - 1j])
        v = vander(c, N=3)
        expected = np.array([[2j, 1 + 1j, 1],
                             [-2j, 1 - 1j, 1]])
        # The data is floating point, but the values are small integers,
        # so assert_array_equal *should* be safe here (rather than, say,
        # assert_array_almost_equal).
        assert_array_equal(v, expected)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_stride_tricks_impl.py ===
"""
Utilities that manipulate strides to achieve desirable effects.

An explanation of strides can be found in the :ref:`arrays.ndarray`.

"""
import numpy as np
from numpy._core.numeric import normalize_axis_tuple
from numpy._core.overrides import array_function_dispatch, set_module

__all__ = ['broadcast_to', 'broadcast_arrays', 'broadcast_shapes']


class DummyArray:
    """Dummy object that just exists to hang __array_interface__ dictionaries
    and possibly keep alive a reference to a base array.
    """

    def __init__(self, interface, base=None):
        self.__array_interface__ = interface
        self.base = base


def _maybe_view_as_subclass(original_array, new_array):
    if type(original_array) is not type(new_array):
        # if input was an ndarray subclass and subclasses were OK,
        # then view the result as that subclass.
        new_array = new_array.view(type=type(original_array))
        # Since we have done something akin to a view from original_array, we
        # should let the subclass finalize (if it has it implemented, i.e., is
        # not None).
        if new_array.__array_finalize__:
            new_array.__array_finalize__(original_array)
    return new_array


@set_module("numpy.lib.stride_tricks")
def as_strided(x, shape=None, strides=None, subok=False, writeable=True):
    """
    Create a view into the array with the given shape and strides.

    .. warning:: This function has to be used with extreme care, see notes.

    Parameters
    ----------
    x : ndarray
        Array to create a new.
    shape : sequence of int, optional
        The shape of the new array. Defaults to ``x.shape``.
    strides : sequence of int, optional
        The strides of the new array. Defaults to ``x.strides``.
    subok : bool, optional
        If True, subclasses are preserved.
    writeable : bool, optional
        If set to False, the returned array will always be readonly.
        Otherwise it will be writable if the original array was. It
        is advisable to set this to False if possible (see Notes).

    Returns
    -------
    view : ndarray

    See also
    --------
    broadcast_to : broadcast an array to a given shape.
    reshape : reshape an array.
    lib.stride_tricks.sliding_window_view :
        userfriendly and safe function for a creation of sliding window views.

    Notes
    -----
    ``as_strided`` creates a view into the array given the exact strides
    and shape. This means it manipulates the internal data structure of
    ndarray and, if done incorrectly, the array elements can point to
    invalid memory and can corrupt results or crash your program.
    It is advisable to always use the original ``x.strides`` when
    calculating new strides to avoid reliance on a contiguous memory
    layout.

    Furthermore, arrays created with this function often contain self
    overlapping memory, so that two elements are identical.
    Vectorized write operations on such arrays will typically be
    unpredictable. They may even give different results for small, large,
    or transposed arrays.

    Since writing to these arrays has to be tested and done with great
    care, you may want to use ``writeable=False`` to avoid accidental write
    operations.

    For these reasons it is advisable to avoid ``as_strided`` when
    possible.
    """
    # first convert input to array, possibly keeping subclass
    x = np.array(x, copy=None, subok=subok)
    interface = dict(x.__array_interface__)
    if shape is not None:
        interface['shape'] = tuple(shape)
    if strides is not None:
        interface['strides'] = tuple(strides)

    array = np.asarray(DummyArray(interface, base=x))
    # The route via `__interface__` does not preserve structured
    # dtypes. Since dtype should remain unchanged, we set it explicitly.
    array.dtype = x.dtype

    view = _maybe_view_as_subclass(x, array)

    if view.flags.writeable and not writeable:
        view.flags.writeable = False

    return view


def _sliding_window_view_dispatcher(x, window_shape, axis=None, *,
                                    subok=None, writeable=None):
    return (x,)


@array_function_dispatch(
    _sliding_window_view_dispatcher, module="numpy.lib.stride_tricks"
)
def sliding_window_view(x, window_shape, axis=None, *,
                        subok=False, writeable=False):
    """
    Create a sliding window view into the array with the given window shape.

    Also known as rolling or moving window, the window slides across all
    dimensions of the array and extracts subsets of the array at all window
    positions.

    .. versionadded:: 1.20.0

    Parameters
    ----------
    x : array_like
        Array to create the sliding window view from.
    window_shape : int or tuple of int
        Size of window over each axis that takes part in the sliding window.
        If `axis` is not present, must have same length as the number of input
        array dimensions. Single integers `i` are treated as if they were the
        tuple `(i,)`.
    axis : int or tuple of int, optional
        Axis or axes along which the sliding window is applied.
        By default, the sliding window is applied to all axes and
        `window_shape[i]` will refer to axis `i` of `x`.
        If `axis` is given as a `tuple of int`, `window_shape[i]` will refer to
        the axis `axis[i]` of `x`.
        Single integers `i` are treated as if they were the tuple `(i,)`.
    subok : bool, optional
        If True, sub-classes will be passed-through, otherwise the returned
        array will be forced to be a base-class array (default).
    writeable : bool, optional
        When true, allow writing to the returned view. The default is false,
        as this should be used with caution: the returned view contains the
        same memory location multiple times, so writing to one location will
        cause others to change.

    Returns
    -------
    view : ndarray
        Sliding window view of the array. The sliding window dimensions are
        inserted at the end, and the original dimensions are trimmed as
        required by the size of the sliding window.
        That is, ``view.shape = x_shape_trimmed + window_shape``, where
        ``x_shape_trimmed`` is ``x.shape`` with every entry reduced by one less
        than the corresponding window size.

    See Also
    --------
    lib.stride_tricks.as_strided: A lower-level and less safe routine for
        creating arbitrary views from custom shape and strides.
    broadcast_to: broadcast an array to a given shape.

    Notes
    -----
    For many applications using a sliding window view can be convenient, but
    potentially very slow. Often specialized solutions exist, for example:

    - `scipy.signal.fftconvolve`

    - filtering functions in `scipy.ndimage`

    - moving window functions provided by
      `bottleneck <https://github.com/pydata/bottleneck>`_.

    As a rough estimate, a sliding window approach with an input size of `N`
    and a window size of `W` will scale as `O(N*W)` where frequently a special
    algorithm can achieve `O(N)`. That means that the sliding window variant
    for a window size of 100 can be a 100 times slower than a more specialized
    version.

    Nevertheless, for small window sizes, when no custom algorithm exists, or
    as a prototyping and developing tool, this function can be a good solution.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib.stride_tricks import sliding_window_view
    >>> x = np.arange(6)
    >>> x.shape
    (6,)
    >>> v = sliding_window_view(x, 3)
    >>> v.shape
    (4, 3)
    >>> v
    array([[0, 1, 2],
           [1, 2, 3],
           [2, 3, 4],
           [3, 4, 5]])

    This also works in more dimensions, e.g.

    >>> i, j = np.ogrid[:3, :4]
    >>> x = 10*i + j
    >>> x.shape
    (3, 4)
    >>> x
    array([[ 0,  1,  2,  3],
           [10, 11, 12, 13],
           [20, 21, 22, 23]])
    >>> shape = (2,2)
    >>> v = sliding_window_view(x, shape)
    >>> v.shape
    (2, 3, 2, 2)
    >>> v
    array([[[[ 0,  1],
             [10, 11]],
            [[ 1,  2],
             [11, 12]],
            [[ 2,  3],
             [12, 13]]],
           [[[10, 11],
             [20, 21]],
            [[11, 12],
             [21, 22]],
            [[12, 13],
             [22, 23]]]])

    The axis can be specified explicitly:

    >>> v = sliding_window_view(x, 3, 0)
    >>> v.shape
    (1, 4, 3)
    >>> v
    array([[[ 0, 10, 20],
            [ 1, 11, 21],
            [ 2, 12, 22],
            [ 3, 13, 23]]])

    The same axis can be used several times. In that case, every use reduces
    the corresponding original dimension:

    >>> v = sliding_window_view(x, (2, 3), (1, 1))
    >>> v.shape
    (3, 1, 2, 3)
    >>> v
    array([[[[ 0,  1,  2],
             [ 1,  2,  3]]],
           [[[10, 11, 12],
             [11, 12, 13]]],
           [[[20, 21, 22],
             [21, 22, 23]]]])

    Combining with stepped slicing (`::step`), this can be used to take sliding
    views which skip elements:

    >>> x = np.arange(7)
    >>> sliding_window_view(x, 5)[:, ::2]
    array([[0, 2, 4],
           [1, 3, 5],
           [2, 4, 6]])

    or views which move by multiple elements

    >>> x = np.arange(7)
    >>> sliding_window_view(x, 3)[::2, :]
    array([[0, 1, 2],
           [2, 3, 4],
           [4, 5, 6]])

    A common application of `sliding_window_view` is the calculation of running
    statistics. The simplest example is the
    `moving average <https://en.wikipedia.org/wiki/Moving_average>`_:

    >>> x = np.arange(6)
    >>> x.shape
    (6,)
    >>> v = sliding_window_view(x, 3)
    >>> v.shape
    (4, 3)
    >>> v
    array([[0, 1, 2],
           [1, 2, 3],
           [2, 3, 4],
           [3, 4, 5]])
    >>> moving_average = v.mean(axis=-1)
    >>> moving_average
    array([1., 2., 3., 4.])

    Note that a sliding window approach is often **not** optimal (see Notes).
    """
    window_shape = (tuple(window_shape)
                    if np.iterable(window_shape)
                    else (window_shape,))
    # first convert input to array, possibly keeping subclass
    x = np.array(x, copy=None, subok=subok)

    window_shape_array = np.array(window_shape)
    if np.any(window_shape_array < 0):
        raise ValueError('`window_shape` cannot contain negative values')

    if axis is None:
        axis = tuple(range(x.ndim))
        if len(window_shape) != len(axis):
            raise ValueError(f'Since axis is `None`, must provide '
                             f'window_shape for all dimensions of `x`; '
                             f'got {len(window_shape)} window_shape elements '
                             f'and `x.ndim` is {x.ndim}.')
    else:
        axis = normalize_axis_tuple(axis, x.ndim, allow_duplicate=True)
        if len(window_shape) != len(axis):
            raise ValueError(f'Must provide matching length window_shape and '
                             f'axis; got {len(window_shape)} window_shape '
                             f'elements and {len(axis)} axes elements.')

    out_strides = x.strides + tuple(x.strides[ax] for ax in axis)

    # note: same axis can be windowed repeatedly
    x_shape_trimmed = list(x.shape)
    for ax, dim in zip(axis, window_shape):
        if x_shape_trimmed[ax] < dim:
            raise ValueError(
                'window shape cannot be larger than input array shape')
        x_shape_trimmed[ax] -= dim - 1
    out_shape = tuple(x_shape_trimmed) + window_shape
    return as_strided(x, strides=out_strides, shape=out_shape,
                      subok=subok, writeable=writeable)


def _broadcast_to(array, shape, subok, readonly):
    shape = tuple(shape) if np.iterable(shape) else (shape,)
    array = np.array(array, copy=None, subok=subok)
    if not shape and array.shape:
        raise ValueError('cannot broadcast a non-scalar to a scalar array')
    if any(size < 0 for size in shape):
        raise ValueError('all elements of broadcast shape must be non-'
                         'negative')
    extras = []
    it = np.nditer(
        (array,), flags=['multi_index', 'refs_ok', 'zerosize_ok'] + extras,
        op_flags=['readonly'], itershape=shape, order='C')
    with it:
        # never really has writebackifcopy semantics
        broadcast = it.itviews[0]
    result = _maybe_view_as_subclass(array, broadcast)
    # In a future version this will go away
    if not readonly and array.flags._writeable_no_warn:
        result.flags.writeable = True
        result.flags._warn_on_write = True
    return result


def _broadcast_to_dispatcher(array, shape, subok=None):
    return (array,)


@array_function_dispatch(_broadcast_to_dispatcher, module='numpy')
def broadcast_to(array, shape, subok=False):
    """Broadcast an array to a new shape.

    Parameters
    ----------
    array : array_like
        The array to broadcast.
    shape : tuple or int
        The shape of the desired array. A single integer ``i`` is interpreted
        as ``(i,)``.
    subok : bool, optional
        If True, then sub-classes will be passed-through, otherwise
        the returned array will be forced to be a base-class array (default).

    Returns
    -------
    broadcast : array
        A readonly view on the original array with the given shape. It is
        typically not contiguous. Furthermore, more than one element of a
        broadcasted array may refer to a single memory location.

    Raises
    ------
    ValueError
        If the array is not compatible with the new shape according to NumPy's
        broadcasting rules.

    See Also
    --------
    broadcast
    broadcast_arrays
    broadcast_shapes

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> np.broadcast_to(x, (3, 3))
    array([[1, 2, 3],
           [1, 2, 3],
           [1, 2, 3]])
    """
    return _broadcast_to(array, shape, subok=subok, readonly=True)


def _broadcast_shape(*args):
    """Returns the shape of the arrays that would result from broadcasting the
    supplied arrays against each other.
    """
    # use the old-iterator because np.nditer does not handle size 0 arrays
    # consistently
    b = np.broadcast(*args[:32])
    # unfortunately, it cannot handle 32 or more arguments directly
    for pos in range(32, len(args), 31):
        # ironically, np.broadcast does not properly handle np.broadcast
        # objects (it treats them as scalars)
        # use broadcasting to avoid allocating the full array
        b = broadcast_to(0, b.shape)
        b = np.broadcast(b, *args[pos:(pos + 31)])
    return b.shape


_size0_dtype = np.dtype([])


@set_module('numpy')
def broadcast_shapes(*args):
    """
    Broadcast the input shapes into a single shape.

    :ref:`Learn more about broadcasting here <basics.broadcasting>`.

    .. versionadded:: 1.20.0

    Parameters
    ----------
    *args : tuples of ints, or ints
        The shapes to be broadcast against each other.

    Returns
    -------
    tuple
        Broadcasted shape.

    Raises
    ------
    ValueError
        If the shapes are not compatible and cannot be broadcast according
        to NumPy's broadcasting rules.

    See Also
    --------
    broadcast
    broadcast_arrays
    broadcast_to

    Examples
    --------
    >>> import numpy as np
    >>> np.broadcast_shapes((1, 2), (3, 1), (3, 2))
    (3, 2)

    >>> np.broadcast_shapes((6, 7), (5, 6, 1), (7,), (5, 1, 7))
    (5, 6, 7)
    """
    arrays = [np.empty(x, dtype=_size0_dtype) for x in args]
    return _broadcast_shape(*arrays)


def _broadcast_arrays_dispatcher(*args, subok=None):
    return args


@array_function_dispatch(_broadcast_arrays_dispatcher, module='numpy')
def broadcast_arrays(*args, subok=False):
    """
    Broadcast any number of arrays against each other.

    Parameters
    ----------
    *args : array_likes
        The arrays to broadcast.

    subok : bool, optional
        If True, then sub-classes will be passed-through, otherwise
        the returned arrays will be forced to be a base-class array (default).

    Returns
    -------
    broadcasted : tuple of arrays
        These arrays are views on the original arrays.  They are typically
        not contiguous.  Furthermore, more than one element of a
        broadcasted array may refer to a single memory location. If you need
        to write to the arrays, make copies first. While you can set the
        ``writable`` flag True, writing to a single output value may end up
        changing more than one location in the output array.

        .. deprecated:: 1.17
            The output is currently marked so that if written to, a deprecation
            warning will be emitted. A future version will set the
            ``writable`` flag False so writing to it will raise an error.

    See Also
    --------
    broadcast
    broadcast_to
    broadcast_shapes

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[1,2,3]])
    >>> y = np.array([[4],[5]])
    >>> np.broadcast_arrays(x, y)
    (array([[1, 2, 3],
            [1, 2, 3]]),
     array([[4, 4, 4],
            [5, 5, 5]]))

    Here is a useful idiom for getting contiguous copies instead of
    non-contiguous views.

    >>> [np.array(a) for a in np.broadcast_arrays(x, y)]
    [array([[1, 2, 3],
            [1, 2, 3]]),
     array([[4, 4, 4],
            [5, 5, 5]])]

    """
    # nditer is not used here to avoid the limit of 32 arrays.
    # Otherwise, something like the following one-liner would suffice:
    # return np.nditer(args, flags=['multi_index', 'zerosize_ok'],
    #                  order='C').itviews

    args = [np.array(_m, copy=None, subok=subok) for _m in args]

    shape = _broadcast_shape(*args)

    result = [array if array.shape == shape
              else _broadcast_to(array, shape, subok=subok, readonly=False)
                              for array in args]
    return tuple(result)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\_debug_adapter\pydevd_schema.py ===
# coding: utf-8
# Automatically generated code.
# Do not edit manually.
# Generated by running: __main__pydevd_gen_debug_adapter_protocol.py
from .pydevd_base_schema import BaseSchema, register, register_request, register_response, register_event


@register
class ProtocolMessage(BaseSchema):
    """
    Base class of requests, responses, and events.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "description": "Message type.", "_enum": ["request", "response", "event"]},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, type, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type: Message type.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = type
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        seq = self.seq
        dct = {
            "type": type,
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class Request(BaseSchema):
    """
    A client or debug adapter initiated request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "description": "The command to execute."},
        "arguments": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Object containing arguments for the command.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, command, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command: The command to execute.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] arguments: Object containing arguments for the command.
        """
        self.type = "request"
        self.command = command
        self.seq = seq
        self.arguments = arguments
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments
        dct.update(self.kwargs)
        return dct


@register
class Event(BaseSchema):
    """
    A debug adapter initiated event.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "description": "Type of event."},
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Event-specific information.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, event, seq=-1, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event: Type of event.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Event-specific information.
        """
        self.type = "event"
        self.event = event
        self.seq = seq
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        seq = self.seq
        body = self.body
        dct = {
            "type": type,
            "event": event,
            "seq": seq,
        }
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register
class Response(BaseSchema):
    """
    Response for a request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_response("error")
@register
class ErrorResponse(BaseSchema):
    """
    On error (whenever `success` is false), the body can provide more details.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {"error": {"$ref": "#/definitions/Message", "description": "A structured error message."}},
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param ErrorResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = ErrorResponseBody()
        else:
            self.body = ErrorResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ErrorResponseBody else body
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("cancel")
@register
class CancelRequest(BaseSchema):
    """
    The `cancel` request is used by the client in two situations:

    - to indicate that it is no longer interested in the result produced by a specific request issued
    earlier

    - to cancel a progress sequence.

    Clients should only call this request if the corresponding capability `supportsCancelRequest` is
    true.

    This request has a hint characteristic: a debug adapter can only be expected to make a 'best effort'
    in honoring this request but there are no guarantees.

    The `cancel` request may return an error if it could not cancel an operation but a client should
    refrain from presenting this error to end users.

    The request that got cancelled still needs to send a response back. This can either be a normal
    result (`success` attribute true) or an error response (`success` attribute false and the `message`
    set to `cancelled`).

    Returning partial results from a cancelled request is possible but please note that a client has no
    generic way for detecting that a response is partial or not.

    The progress that got cancelled still needs to send a `progressEnd` event back.

    A client should not assume that progress just got cancelled after sending the `cancel` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["cancel"]},
        "arguments": {"type": "CancelArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param CancelArguments arguments:
        """
        self.type = "request"
        self.command = "cancel"
        self.seq = seq
        if arguments is None:
            self.arguments = CancelArguments()
        else:
            self.arguments = (
                CancelArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != CancelArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class CancelArguments(BaseSchema):
    """
    Arguments for `cancel` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "requestId": {
            "type": "integer",
            "description": "The ID (attribute `seq`) of the request to cancel. If missing no request is cancelled.\nBoth a `requestId` and a `progressId` can be specified in one request.",
        },
        "progressId": {
            "type": "string",
            "description": "The ID (attribute `progressId`) of the progress to cancel. If missing no progress is cancelled.\nBoth a `requestId` and a `progressId` can be specified in one request.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, requestId=None, progressId=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer requestId: The ID (attribute `seq`) of the request to cancel. If missing no request is cancelled.
        Both a `requestId` and a `progressId` can be specified in one request.
        :param string progressId: The ID (attribute `progressId`) of the progress to cancel. If missing no progress is cancelled.
        Both a `requestId` and a `progressId` can be specified in one request.
        """
        self.requestId = requestId
        self.progressId = progressId
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        requestId = self.requestId
        progressId = self.progressId
        dct = {}
        if requestId is not None:
            dct["requestId"] = requestId
        if progressId is not None:
            dct["progressId"] = progressId
        dct.update(self.kwargs)
        return dct


@register_response("cancel")
@register
class CancelResponse(BaseSchema):
    """
    Response to `cancel` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_event("initialized")
@register
class InitializedEvent(BaseSchema):
    """
    This event indicates that the debug adapter is ready to accept configuration requests (e.g.
    `setBreakpoints`, `setExceptionBreakpoints`).

    A debug adapter is expected to send this event when it is ready to accept configuration requests
    (but not before the `initialize` request has finished).

    The sequence of events/requests is as follows:

    - adapters sends `initialized` event (after the `initialize` request has returned)

    - client sends zero or more `setBreakpoints` requests

    - client sends one `setFunctionBreakpoints` request (if corresponding capability
    `supportsFunctionBreakpoints` is true)

    - client sends a `setExceptionBreakpoints` request if one or more `exceptionBreakpointFilters` have
    been defined (or if `supportsConfigurationDoneRequest` is not true)

    - client sends other future configuration requests

    - client sends one `configurationDone` request to indicate the end of the configuration.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["initialized"]},
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Event-specific information.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Event-specific information.
        """
        self.type = "event"
        self.event = "initialized"
        self.seq = seq
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        seq = self.seq
        body = self.body
        dct = {
            "type": type,
            "event": event,
            "seq": seq,
        }
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_event("stopped")
@register
class StoppedEvent(BaseSchema):
    """
    The event indicates that the execution of the debuggee has stopped due to some condition.

    This can be caused by a breakpoint previously set, a stepping request has completed, by executing a
    debugger statement etc.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["stopped"]},
        "body": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "The reason for the event.\nFor backward compatibility this string is shown in the UI if the `description` attribute is missing (but it must not be translated).",
                    "_enum": [
                        "step",
                        "breakpoint",
                        "exception",
                        "pause",
                        "entry",
                        "goto",
                        "function breakpoint",
                        "data breakpoint",
                        "instruction breakpoint",
                    ],
                },
                "description": {
                    "type": "string",
                    "description": "The full reason for the event, e.g. 'Paused on exception'. This string is shown in the UI as is and can be translated.",
                },
                "threadId": {"type": "integer", "description": "The thread which was stopped."},
                "preserveFocusHint": {
                    "type": "boolean",
                    "description": "A value of True hints to the client that this event should not change the focus.",
                },
                "text": {
                    "type": "string",
                    "description": "Additional information. E.g. if reason is `exception`, text contains the exception name. This string is shown in the UI.",
                },
                "allThreadsStopped": {
                    "type": "boolean",
                    "description": "If `allThreadsStopped` is True, a debug adapter can announce that all threads have stopped.\n- The client should use this information to enable that all threads can be expanded to access their stacktraces.\n- If the attribute is missing or false, only the thread with the given `threadId` can be expanded.",
                },
                "hitBreakpointIds": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Ids of the breakpoints that triggered the event. In most cases there is only a single breakpoint but here are some examples for multiple breakpoints:\n- Different types of breakpoints map to the same location.\n- Multiple source breakpoints get collapsed to the same instruction by the compiler/runtime.\n- Multiple function breakpoints with different function names map to the same location.",
                },
            },
            "required": ["reason"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param StoppedEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "stopped"
        if body is None:
            self.body = StoppedEventBody()
        else:
            self.body = StoppedEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != StoppedEventBody else body
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("continued")
@register
class ContinuedEvent(BaseSchema):
    """
    The event indicates that the execution of the debuggee has continued.

    Please note: a debug adapter is not expected to send this event in response to a request that
    implies that execution continues, e.g. `launch` or `continue`.

    It is only necessary to send a `continued` event if there was no previous request that implied this.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["continued"]},
        "body": {
            "type": "object",
            "properties": {
                "threadId": {"type": "integer", "description": "The thread which was continued."},
                "allThreadsContinued": {
                    "type": "boolean",
                    "description": "If `allThreadsContinued` is True, a debug adapter can announce that all threads have continued.",
                },
            },
            "required": ["threadId"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ContinuedEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "continued"
        if body is None:
            self.body = ContinuedEventBody()
        else:
            self.body = (
                ContinuedEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ContinuedEventBody else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("exited")
@register
class ExitedEvent(BaseSchema):
    """
    The event indicates that the debuggee has exited and returns its exit code.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["exited"]},
        "body": {
            "type": "object",
            "properties": {"exitCode": {"type": "integer", "description": "The exit code returned from the debuggee."}},
            "required": ["exitCode"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ExitedEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "exited"
        if body is None:
            self.body = ExitedEventBody()
        else:
            self.body = ExitedEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ExitedEventBody else body
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("terminated")
@register
class TerminatedEvent(BaseSchema):
    """
    The event indicates that debugging of the debuggee has terminated. This does **not** mean that the
    debuggee itself has exited.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["terminated"]},
        "body": {
            "type": "object",
            "properties": {
                "restart": {
                    "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
                    "description": "A debug adapter may set `restart` to True (or to an arbitrary object) to request that the client restarts the session.\nThe value is not interpreted by the client and passed unmodified as an attribute `__restart` to the `launch` and `attach` requests.",
                }
            },
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param TerminatedEventBody body:
        """
        self.type = "event"
        self.event = "terminated"
        self.seq = seq
        if body is None:
            self.body = TerminatedEventBody()
        else:
            self.body = (
                TerminatedEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != TerminatedEventBody else body
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        seq = self.seq
        body = self.body
        dct = {
            "type": type,
            "event": event,
            "seq": seq,
        }
        if body is not None:
            dct["body"] = body.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register_event("thread")
@register
class ThreadEvent(BaseSchema):
    """
    The event indicates that a thread has started or exited.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["thread"]},
        "body": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "The reason for the event.", "_enum": ["started", "exited"]},
                "threadId": {"type": "integer", "description": "The identifier of the thread."},
            },
            "required": ["reason", "threadId"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ThreadEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "thread"
        if body is None:
            self.body = ThreadEventBody()
        else:
            self.body = ThreadEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ThreadEventBody else body
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("output")
@register
class OutputEvent(BaseSchema):
    """
    The event indicates that the target has produced some output.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["output"]},
        "body": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "The output category. If not specified or if the category is not understood by the client, `console` is assumed.",
                    "_enum": ["console", "important", "stdout", "stderr", "telemetry"],
                    "enumDescriptions": [
                        "Show the output in the client's default message UI, e.g. a 'debug console'. This category should only be used for informational output from the debugger (as opposed to the debuggee).",
                        "A hint for the client to show the output in the client's UI for important and highly visible information, e.g. as a popup notification. This category should only be used for important messages from the debugger (as opposed to the debuggee). Since this category value is a hint, clients might ignore the hint and assume the `console` category.",
                        "Show the output as normal program output from the debuggee.",
                        "Show the output as error program output from the debuggee.",
                        "Send the output to telemetry instead of showing it to the user.",
                    ],
                },
                "output": {"type": "string", "description": "The output to report."},
                "group": {
                    "type": "string",
                    "description": "Support for keeping an output log organized by grouping related messages.",
                    "enum": ["start", "startCollapsed", "end"],
                    "enumDescriptions": [
                        "Start a new group in expanded mode. Subsequent output events are members of the group and should be shown indented.\nThe `output` attribute becomes the name of the group and is not indented.",
                        "Start a new group in collapsed mode. Subsequent output events are members of the group and should be shown indented (as soon as the group is expanded).\nThe `output` attribute becomes the name of the group and is not indented.",
                        "End the current group and decrease the indentation of subsequent output events.\nA non-empty `output` attribute is shown as the unindented end of the group.",
                    ],
                },
                "variablesReference": {
                    "type": "integer",
                    "description": "If an attribute `variablesReference` exists and its value is > 0, the output contains objects which can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
                },
                "source": {"$ref": "#/definitions/Source", "description": "The source location where the output was produced."},
                "line": {"type": "integer", "description": "The source location's line where the output was produced."},
                "column": {
                    "type": "integer",
                    "description": "The position in `line` where the output was produced. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
                },
                "data": {
                    "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
                    "description": "Additional data to report. For the `telemetry` category the data is sent to telemetry, for the other categories the data is shown in JSON format.",
                },
            },
            "required": ["output"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param OutputEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "output"
        if body is None:
            self.body = OutputEventBody()
        else:
            self.body = OutputEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != OutputEventBody else body
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("breakpoint")
@register
class BreakpointEvent(BaseSchema):
    """
    The event indicates that some information about a breakpoint has changed.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["breakpoint"]},
        "body": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "The reason for the event.", "_enum": ["changed", "new", "removed"]},
                "breakpoint": {
                    "$ref": "#/definitions/Breakpoint",
                    "description": "The `id` attribute is used to find the target breakpoint, the other attributes are used as the new values.",
                },
            },
            "required": ["reason", "breakpoint"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param BreakpointEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "breakpoint"
        if body is None:
            self.body = BreakpointEventBody()
        else:
            self.body = (
                BreakpointEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != BreakpointEventBody else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("module")
@register
class ModuleEvent(BaseSchema):
    """
    The event indicates that some information about a module has changed.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["module"]},
        "body": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "The reason for the event.", "enum": ["new", "changed", "removed"]},
                "module": {
                    "$ref": "#/definitions/Module",
                    "description": "The new, changed, or removed module. In case of `removed` only the module id is used.",
                },
            },
            "required": ["reason", "module"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ModuleEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "module"
        if body is None:
            self.body = ModuleEventBody()
        else:
            self.body = ModuleEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ModuleEventBody else body
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("loadedSource")
@register
class LoadedSourceEvent(BaseSchema):
    """
    The event indicates that some source has been added, changed, or removed from the set of all loaded
    sources.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["loadedSource"]},
        "body": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "The reason for the event.", "enum": ["new", "changed", "removed"]},
                "source": {"$ref": "#/definitions/Source", "description": "The new, changed, or removed source."},
            },
            "required": ["reason", "source"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param LoadedSourceEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "loadedSource"
        if body is None:
            self.body = LoadedSourceEventBody()
        else:
            self.body = (
                LoadedSourceEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != LoadedSourceEventBody else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("process")
@register
class ProcessEvent(BaseSchema):
    """
    The event indicates that the debugger has begun debugging a new process. Either one that it has
    launched, or one that it has attached to.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["process"]},
        "body": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The logical name of the process. This is usually the full path to process's executable file. Example: /home/example/myproj/program.js.",
                },
                "systemProcessId": {
                    "type": "integer",
                    "description": "The system process id of the debugged process. This property is missing for non-system processes.",
                },
                "isLocalProcess": {
                    "type": "boolean",
                    "description": "If True, the process is running on the same computer as the debug adapter.",
                },
                "startMethod": {
                    "type": "string",
                    "enum": ["launch", "attach", "attachForSuspendedLaunch"],
                    "description": "Describes how the debug engine started debugging this process.",
                    "enumDescriptions": [
                        "Process was launched under the debugger.",
                        "Debugger attached to an existing process.",
                        "A project launcher component has launched a new process in a suspended state and then asked the debugger to attach.",
                    ],
                },
                "pointerSize": {
                    "type": "integer",
                    "description": "The size of a pointer or address for this process, in bits. This value may be used by clients when formatting addresses for display.",
                },
            },
            "required": ["name"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ProcessEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "process"
        if body is None:
            self.body = ProcessEventBody()
        else:
            self.body = ProcessEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ProcessEventBody else body
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("capabilities")
@register
class CapabilitiesEvent(BaseSchema):
    """
    The event indicates that one or more capabilities have changed.

    Since the capabilities are dependent on the client and its UI, it might not be possible to change
    that at random times (or too late).

    Consequently this event has a hint characteristic: a client can only be expected to make a 'best
    effort' in honoring individual capabilities but there are no guarantees.

    Only changed capabilities need to be included, all other capabilities keep their values.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["capabilities"]},
        "body": {
            "type": "object",
            "properties": {"capabilities": {"$ref": "#/definitions/Capabilities", "description": "The set of updated capabilities."}},
            "required": ["capabilities"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param CapabilitiesEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "capabilities"
        if body is None:
            self.body = CapabilitiesEventBody()
        else:
            self.body = (
                CapabilitiesEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != CapabilitiesEventBody else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("progressStart")
@register
class ProgressStartEvent(BaseSchema):
    """
    The event signals that a long running operation is about to start and provides additional
    information for the client to set up a corresponding progress and cancellation UI.

    The client is free to delay the showing of the UI in order to reduce flicker.

    This event should only be sent if the corresponding capability `supportsProgressReporting` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["progressStart"]},
        "body": {
            "type": "object",
            "properties": {
                "progressId": {
                    "type": "string",
                    "description": "An ID that can be used in subsequent `progressUpdate` and `progressEnd` events to make them refer to the same progress reporting.\nIDs must be unique within a debug session.",
                },
                "title": {
                    "type": "string",
                    "description": "Short title of the progress reporting. Shown in the UI to describe the long running operation.",
                },
                "requestId": {
                    "type": "integer",
                    "description": "The request ID that this progress report is related to. If specified a debug adapter is expected to emit progress events for the long running request until the request has been either completed or cancelled.\nIf the request ID is omitted, the progress report is assumed to be related to some general activity of the debug adapter.",
                },
                "cancellable": {
                    "type": "boolean",
                    "description": "If True, the request that reports progress may be cancelled with a `cancel` request.\nSo this property basically controls whether the client should use UX that supports cancellation.\nClients that don't support cancellation are allowed to ignore the setting.",
                },
                "message": {"type": "string", "description": "More detailed progress message."},
                "percentage": {
                    "type": "number",
                    "description": "Progress percentage to display (value range: 0 to 100). If omitted no percentage is shown.",
                },
            },
            "required": ["progressId", "title"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ProgressStartEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "progressStart"
        if body is None:
            self.body = ProgressStartEventBody()
        else:
            self.body = (
                ProgressStartEventBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != ProgressStartEventBody
                else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("progressUpdate")
@register
class ProgressUpdateEvent(BaseSchema):
    """
    The event signals that the progress reporting needs to be updated with a new message and/or
    percentage.

    The client does not have to update the UI immediately, but the clients needs to keep track of the
    message and/or percentage values.

    This event should only be sent if the corresponding capability `supportsProgressReporting` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["progressUpdate"]},
        "body": {
            "type": "object",
            "properties": {
                "progressId": {"type": "string", "description": "The ID that was introduced in the initial `progressStart` event."},
                "message": {
                    "type": "string",
                    "description": "More detailed progress message. If omitted, the previous message (if any) is used.",
                },
                "percentage": {
                    "type": "number",
                    "description": "Progress percentage to display (value range: 0 to 100). If omitted no percentage is shown.",
                },
            },
            "required": ["progressId"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ProgressUpdateEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "progressUpdate"
        if body is None:
            self.body = ProgressUpdateEventBody()
        else:
            self.body = (
                ProgressUpdateEventBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != ProgressUpdateEventBody
                else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("progressEnd")
@register
class ProgressEndEvent(BaseSchema):
    """
    The event signals the end of the progress reporting with a final message.

    This event should only be sent if the corresponding capability `supportsProgressReporting` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["progressEnd"]},
        "body": {
            "type": "object",
            "properties": {
                "progressId": {"type": "string", "description": "The ID that was introduced in the initial `ProgressStartEvent`."},
                "message": {
                    "type": "string",
                    "description": "More detailed progress message. If omitted, the previous message (if any) is used.",
                },
            },
            "required": ["progressId"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param ProgressEndEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "progressEnd"
        if body is None:
            self.body = ProgressEndEventBody()
        else:
            self.body = (
                ProgressEndEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ProgressEndEventBody else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("invalidated")
@register
class InvalidatedEvent(BaseSchema):
    """
    This event signals that some state in the debug adapter has changed and requires that the client
    needs to re-render the data snapshot previously requested.

    Debug adapters do not have to emit this event for runtime changes like stopped or thread events
    because in that case the client refetches the new state anyway. But the event can be used for
    example to refresh the UI after rendering formatting has changed in the debug adapter.

    This event should only be sent if the corresponding capability `supportsInvalidatedEvent` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["invalidated"]},
        "body": {
            "type": "object",
            "properties": {
                "areas": {
                    "type": "array",
                    "description": "Set of logical areas that got invalidated. This property has a hint characteristic: a client can only be expected to make a 'best effort' in honoring the areas but there are no guarantees. If this property is missing, empty, or if values are not understood, the client should assume a single value `all`.",
                    "items": {"$ref": "#/definitions/InvalidatedAreas"},
                },
                "threadId": {
                    "type": "integer",
                    "description": "If specified, the client only needs to refetch data related to this thread.",
                },
                "stackFrameId": {
                    "type": "integer",
                    "description": "If specified, the client only needs to refetch data related to this stack frame (and the `threadId` is ignored).",
                },
            },
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param InvalidatedEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "invalidated"
        if body is None:
            self.body = InvalidatedEventBody()
        else:
            self.body = (
                InvalidatedEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != InvalidatedEventBody else body
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_event("memory")
@register
class MemoryEvent(BaseSchema):
    """
    This event indicates that some memory range has been updated. It should only be sent if the
    corresponding capability `supportsMemoryEvent` is true.

    Clients typically react to the event by re-issuing a `readMemory` request if they show the memory
    identified by the `memoryReference` and if the updated memory range overlaps the displayed range.
    Clients should not make assumptions how individual memory references relate to each other, so they
    should not assume that they are part of a single continuous address range and might overlap.

    Debug adapters can use this event to indicate that the contents of a memory range has changed due to
    some other request like `setVariable` or `setExpression`. Debug adapters are not expected to emit
    this event for each and every memory change of a running program, because that information is
    typically not available from debuggers and it would flood clients with too many events.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["memory"]},
        "body": {
            "type": "object",
            "properties": {
                "memoryReference": {"type": "string", "description": "Memory reference of a memory range that has been updated."},
                "offset": {"type": "integer", "description": "Starting offset in bytes where memory has been updated. Can be negative."},
                "count": {"type": "integer", "description": "Number of bytes updated."},
            },
            "required": ["memoryReference", "offset", "count"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, body, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param MemoryEventBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "event"
        self.event = "memory"
        if body is None:
            self.body = MemoryEventBody()
        else:
            self.body = MemoryEventBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != MemoryEventBody else body
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        body = self.body
        seq = self.seq
        dct = {
            "type": type,
            "event": event,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register_request("runInTerminal")
@register
class RunInTerminalRequest(BaseSchema):
    """
    This request is sent from the debug adapter to the client to run a command in a terminal.

    This is typically used to launch the debuggee in a terminal provided by the client.

    This request should only be called if the corresponding client capability
    `supportsRunInTerminalRequest` is true.

    Client implementations of `runInTerminal` are free to run the command however they choose including
    issuing the command to a command line interpreter (aka 'shell'). Argument strings passed to the
    `runInTerminal` request must arrive verbatim in the command to be run. As a consequence, clients
    which use a shell are responsible for escaping any special shell characters in the argument strings
    to prevent them from being interpreted (and modified) by the shell.

    Some users may wish to take advantage of shell processing in the argument strings. For clients which
    implement `runInTerminal` using an intermediary shell, the `argsCanBeInterpretedByShell` property
    can be set to true. In this case the client is requested not to escape any special shell characters
    in the argument strings.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["runInTerminal"]},
        "arguments": {"type": "RunInTerminalRequestArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param RunInTerminalRequestArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "runInTerminal"
        if arguments is None:
            self.arguments = RunInTerminalRequestArguments()
        else:
            self.arguments = (
                RunInTerminalRequestArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != RunInTerminalRequestArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class RunInTerminalRequestArguments(BaseSchema):
    """
    Arguments for `runInTerminal` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "kind": {
            "type": "string",
            "enum": ["integrated", "external"],
            "description": "What kind of terminal to launch. Defaults to `integrated` if not specified.",
        },
        "title": {"type": "string", "description": "Title of the terminal."},
        "cwd": {
            "type": "string",
            "description": "Working directory for the command. For non-empty, valid paths this typically results in execution of a change directory command.",
        },
        "args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of arguments. The first argument is the command to run.",
        },
        "env": {
            "type": "object",
            "description": "Environment key-value pairs that are added to or removed from the default environment.",
            "additionalProperties": {
                "type": ["string", "null"],
                "description": "A string is a proper value for an environment variable. The value `null` removes the variable from the environment.",
            },
        },
        "argsCanBeInterpretedByShell": {
            "type": "boolean",
            "description": "This property should only be set if the corresponding capability `supportsArgsCanBeInterpretedByShell` is True. If the client uses an intermediary shell to launch the application, then the client must not attempt to escape characters with special meanings for the shell. The user is fully responsible for escaping as needed and that arguments using special characters may not be portable across shells.",
        },
    }
    __refs__ = set(["env"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, cwd, args, kind=None, title=None, env=None, argsCanBeInterpretedByShell=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string cwd: Working directory for the command. For non-empty, valid paths this typically results in execution of a change directory command.
        :param array args: List of arguments. The first argument is the command to run.
        :param string kind: What kind of terminal to launch. Defaults to `integrated` if not specified.
        :param string title: Title of the terminal.
        :param RunInTerminalRequestArgumentsEnv env: Environment key-value pairs that are added to or removed from the default environment.
        :param boolean argsCanBeInterpretedByShell: This property should only be set if the corresponding capability `supportsArgsCanBeInterpretedByShell` is true. If the client uses an intermediary shell to launch the application, then the client must not attempt to escape characters with special meanings for the shell. The user is fully responsible for escaping as needed and that arguments using special characters may not be portable across shells.
        """
        self.cwd = cwd
        self.args = args
        self.kind = kind
        self.title = title
        if env is None:
            self.env = RunInTerminalRequestArgumentsEnv()
        else:
            self.env = (
                RunInTerminalRequestArgumentsEnv(update_ids_from_dap=update_ids_from_dap, **env)
                if env.__class__ != RunInTerminalRequestArgumentsEnv
                else env
            )
        self.argsCanBeInterpretedByShell = argsCanBeInterpretedByShell
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        cwd = self.cwd
        args = self.args
        if args and hasattr(args[0], "to_dict"):
            args = [x.to_dict() for x in args]
        kind = self.kind
        title = self.title
        env = self.env
        argsCanBeInterpretedByShell = self.argsCanBeInterpretedByShell
        dct = {
            "cwd": cwd,
            "args": args,
        }
        if kind is not None:
            dct["kind"] = kind
        if title is not None:
            dct["title"] = title
        if env is not None:
            dct["env"] = env.to_dict(update_ids_to_dap=update_ids_to_dap)
        if argsCanBeInterpretedByShell is not None:
            dct["argsCanBeInterpretedByShell"] = argsCanBeInterpretedByShell
        dct.update(self.kwargs)
        return dct


@register_response("runInTerminal")
@register
class RunInTerminalResponse(BaseSchema):
    """
    Response to `runInTerminal` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "processId": {
                    "type": "integer",
                    "description": "The process ID. The value should be less than or equal to 2147483647 (2^31-1).",
                },
                "shellProcessId": {
                    "type": "integer",
                    "description": "The process ID of the terminal shell. The value should be less than or equal to 2147483647 (2^31-1).",
                },
            },
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param RunInTerminalResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = RunInTerminalResponseBody()
        else:
            self.body = (
                RunInTerminalResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != RunInTerminalResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("startDebugging")
@register
class StartDebuggingRequest(BaseSchema):
    """
    This request is sent from the debug adapter to the client to start a new debug session of the same
    type as the caller.

    This request should only be sent if the corresponding client capability
    `supportsStartDebuggingRequest` is true.

    A client implementation of `startDebugging` should start a new debug session (of the same type as
    the caller) in the same way that the caller's session was started. If the client supports
    hierarchical debug sessions, the newly created session can be treated as a child of the caller
    session.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["startDebugging"]},
        "arguments": {"type": "StartDebuggingRequestArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param StartDebuggingRequestArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "startDebugging"
        if arguments is None:
            self.arguments = StartDebuggingRequestArguments()
        else:
            self.arguments = (
                StartDebuggingRequestArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != StartDebuggingRequestArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class StartDebuggingRequestArguments(BaseSchema):
    """
    Arguments for `startDebugging` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "configuration": {
            "type": "object",
            "additionalProperties": True,
            "description": "Arguments passed to the new debug session. The arguments must only contain properties understood by the `launch` or `attach` requests of the debug adapter and they must not contain any client-specific properties (e.g. `type`) or client-specific features (e.g. substitutable 'variables').",
        },
        "request": {
            "type": "string",
            "enum": ["launch", "attach"],
            "description": "Indicates whether the new debug session should be started with a `launch` or `attach` request.",
        },
    }
    __refs__ = set(["configuration"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, configuration, request, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param StartDebuggingRequestArgumentsConfiguration configuration: Arguments passed to the new debug session. The arguments must only contain properties understood by the `launch` or `attach` requests of the debug adapter and they must not contain any client-specific properties (e.g. `type`) or client-specific features (e.g. substitutable 'variables').
        :param string request: Indicates whether the new debug session should be started with a `launch` or `attach` request.
        """
        if configuration is None:
            self.configuration = StartDebuggingRequestArgumentsConfiguration()
        else:
            self.configuration = (
                StartDebuggingRequestArgumentsConfiguration(update_ids_from_dap=update_ids_from_dap, **configuration)
                if configuration.__class__ != StartDebuggingRequestArgumentsConfiguration
                else configuration
            )
        self.request = request
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        configuration = self.configuration
        request = self.request
        dct = {
            "configuration": configuration.to_dict(update_ids_to_dap=update_ids_to_dap),
            "request": request,
        }
        dct.update(self.kwargs)
        return dct


@register_response("startDebugging")
@register
class StartDebuggingResponse(BaseSchema):
    """
    Response to `startDebugging` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("initialize")
@register
class InitializeRequest(BaseSchema):
    """
    The `initialize` request is sent as the first request from the client to the debug adapter in order
    to configure it with client capabilities and to retrieve capabilities from the debug adapter.

    Until the debug adapter has responded with an `initialize` response, the client must not send any
    additional requests or events to the debug adapter.

    In addition the debug adapter is not allowed to send any requests or events to the client until it
    has responded with an `initialize` response.

    The `initialize` request may only be sent once.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["initialize"]},
        "arguments": {"type": "InitializeRequestArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param InitializeRequestArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "initialize"
        if arguments is None:
            self.arguments = InitializeRequestArguments()
        else:
            self.arguments = (
                InitializeRequestArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != InitializeRequestArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class InitializeRequestArguments(BaseSchema):
    """
    Arguments for `initialize` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "clientID": {"type": "string", "description": "The ID of the client using this adapter."},
        "clientName": {"type": "string", "description": "The human-readable name of the client using this adapter."},
        "adapterID": {"type": "string", "description": "The ID of the debug adapter."},
        "locale": {"type": "string", "description": "The ISO-639 locale of the client using this adapter, e.g. en-US or de-CH."},
        "linesStartAt1": {"type": "boolean", "description": "If True all line numbers are 1-based (default)."},
        "columnsStartAt1": {"type": "boolean", "description": "If True all column numbers are 1-based (default)."},
        "pathFormat": {
            "type": "string",
            "_enum": ["path", "uri"],
            "description": "Determines in what format paths are specified. The default is `path`, which is the native format.",
        },
        "supportsVariableType": {"type": "boolean", "description": "Client supports the `type` attribute for variables."},
        "supportsVariablePaging": {"type": "boolean", "description": "Client supports the paging of variables."},
        "supportsRunInTerminalRequest": {"type": "boolean", "description": "Client supports the `runInTerminal` request."},
        "supportsMemoryReferences": {"type": "boolean", "description": "Client supports memory references."},
        "supportsProgressReporting": {"type": "boolean", "description": "Client supports progress reporting."},
        "supportsInvalidatedEvent": {"type": "boolean", "description": "Client supports the `invalidated` event."},
        "supportsMemoryEvent": {"type": "boolean", "description": "Client supports the `memory` event."},
        "supportsArgsCanBeInterpretedByShell": {
            "type": "boolean",
            "description": "Client supports the `argsCanBeInterpretedByShell` attribute on the `runInTerminal` request.",
        },
        "supportsStartDebuggingRequest": {"type": "boolean", "description": "Client supports the `startDebugging` request."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        adapterID,
        clientID=None,
        clientName=None,
        locale=None,
        linesStartAt1=None,
        columnsStartAt1=None,
        pathFormat=None,
        supportsVariableType=None,
        supportsVariablePaging=None,
        supportsRunInTerminalRequest=None,
        supportsMemoryReferences=None,
        supportsProgressReporting=None,
        supportsInvalidatedEvent=None,
        supportsMemoryEvent=None,
        supportsArgsCanBeInterpretedByShell=None,
        supportsStartDebuggingRequest=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string adapterID: The ID of the debug adapter.
        :param string clientID: The ID of the client using this adapter.
        :param string clientName: The human-readable name of the client using this adapter.
        :param string locale: The ISO-639 locale of the client using this adapter, e.g. en-US or de-CH.
        :param boolean linesStartAt1: If true all line numbers are 1-based (default).
        :param boolean columnsStartAt1: If true all column numbers are 1-based (default).
        :param string pathFormat: Determines in what format paths are specified. The default is `path`, which is the native format.
        :param boolean supportsVariableType: Client supports the `type` attribute for variables.
        :param boolean supportsVariablePaging: Client supports the paging of variables.
        :param boolean supportsRunInTerminalRequest: Client supports the `runInTerminal` request.
        :param boolean supportsMemoryReferences: Client supports memory references.
        :param boolean supportsProgressReporting: Client supports progress reporting.
        :param boolean supportsInvalidatedEvent: Client supports the `invalidated` event.
        :param boolean supportsMemoryEvent: Client supports the `memory` event.
        :param boolean supportsArgsCanBeInterpretedByShell: Client supports the `argsCanBeInterpretedByShell` attribute on the `runInTerminal` request.
        :param boolean supportsStartDebuggingRequest: Client supports the `startDebugging` request.
        """
        self.adapterID = adapterID
        self.clientID = clientID
        self.clientName = clientName
        self.locale = locale
        self.linesStartAt1 = linesStartAt1
        self.columnsStartAt1 = columnsStartAt1
        self.pathFormat = pathFormat
        self.supportsVariableType = supportsVariableType
        self.supportsVariablePaging = supportsVariablePaging
        self.supportsRunInTerminalRequest = supportsRunInTerminalRequest
        self.supportsMemoryReferences = supportsMemoryReferences
        self.supportsProgressReporting = supportsProgressReporting
        self.supportsInvalidatedEvent = supportsInvalidatedEvent
        self.supportsMemoryEvent = supportsMemoryEvent
        self.supportsArgsCanBeInterpretedByShell = supportsArgsCanBeInterpretedByShell
        self.supportsStartDebuggingRequest = supportsStartDebuggingRequest
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        adapterID = self.adapterID
        clientID = self.clientID
        clientName = self.clientName
        locale = self.locale
        linesStartAt1 = self.linesStartAt1
        columnsStartAt1 = self.columnsStartAt1
        pathFormat = self.pathFormat
        supportsVariableType = self.supportsVariableType
        supportsVariablePaging = self.supportsVariablePaging
        supportsRunInTerminalRequest = self.supportsRunInTerminalRequest
        supportsMemoryReferences = self.supportsMemoryReferences
        supportsProgressReporting = self.supportsProgressReporting
        supportsInvalidatedEvent = self.supportsInvalidatedEvent
        supportsMemoryEvent = self.supportsMemoryEvent
        supportsArgsCanBeInterpretedByShell = self.supportsArgsCanBeInterpretedByShell
        supportsStartDebuggingRequest = self.supportsStartDebuggingRequest
        dct = {
            "adapterID": adapterID,
        }
        if clientID is not None:
            dct["clientID"] = clientID
        if clientName is not None:
            dct["clientName"] = clientName
        if locale is not None:
            dct["locale"] = locale
        if linesStartAt1 is not None:
            dct["linesStartAt1"] = linesStartAt1
        if columnsStartAt1 is not None:
            dct["columnsStartAt1"] = columnsStartAt1
        if pathFormat is not None:
            dct["pathFormat"] = pathFormat
        if supportsVariableType is not None:
            dct["supportsVariableType"] = supportsVariableType
        if supportsVariablePaging is not None:
            dct["supportsVariablePaging"] = supportsVariablePaging
        if supportsRunInTerminalRequest is not None:
            dct["supportsRunInTerminalRequest"] = supportsRunInTerminalRequest
        if supportsMemoryReferences is not None:
            dct["supportsMemoryReferences"] = supportsMemoryReferences
        if supportsProgressReporting is not None:
            dct["supportsProgressReporting"] = supportsProgressReporting
        if supportsInvalidatedEvent is not None:
            dct["supportsInvalidatedEvent"] = supportsInvalidatedEvent
        if supportsMemoryEvent is not None:
            dct["supportsMemoryEvent"] = supportsMemoryEvent
        if supportsArgsCanBeInterpretedByShell is not None:
            dct["supportsArgsCanBeInterpretedByShell"] = supportsArgsCanBeInterpretedByShell
        if supportsStartDebuggingRequest is not None:
            dct["supportsStartDebuggingRequest"] = supportsStartDebuggingRequest
        dct.update(self.kwargs)
        return dct


@register_response("initialize")
@register
class InitializeResponse(BaseSchema):
    """
    Response to `initialize` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {"description": "The capabilities of this debug adapter.", "type": "Capabilities"},
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param Capabilities body: The capabilities of this debug adapter.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        if body is None:
            self.body = Capabilities()
        else:
            self.body = Capabilities(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != Capabilities else body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register_request("configurationDone")
@register
class ConfigurationDoneRequest(BaseSchema):
    """
    This request indicates that the client has finished initialization of the debug adapter.

    So it is the last request in the sequence of configuration requests (which was started by the
    `initialized` event).

    Clients should only call this request if the corresponding capability
    `supportsConfigurationDoneRequest` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["configurationDone"]},
        "arguments": {"type": "ConfigurationDoneArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param ConfigurationDoneArguments arguments:
        """
        self.type = "request"
        self.command = "configurationDone"
        self.seq = seq
        if arguments is None:
            self.arguments = ConfigurationDoneArguments()
        else:
            self.arguments = (
                ConfigurationDoneArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != ConfigurationDoneArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class ConfigurationDoneArguments(BaseSchema):
    """
    Arguments for `configurationDone` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register_response("configurationDone")
@register
class ConfigurationDoneResponse(BaseSchema):
    """
    Response to `configurationDone` request. This is just an acknowledgement, so no body field is
    required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("launch")
@register
class LaunchRequest(BaseSchema):
    """
    This launch request is sent from the client to the debug adapter to start the debuggee with or
    without debugging (if `noDebug` is true).

    Since launching is debugger/runtime specific, the arguments for this request are not part of this
    specification.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["launch"]},
        "arguments": {"type": "LaunchRequestArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param LaunchRequestArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "launch"
        if arguments is None:
            self.arguments = LaunchRequestArguments()
        else:
            self.arguments = (
                LaunchRequestArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != LaunchRequestArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class LaunchRequestArguments(BaseSchema):
    """
    Arguments for `launch` request. Additional attributes are implementation specific.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "noDebug": {"type": "boolean", "description": "If True, the launch request should launch the program without enabling debugging."},
        "__restart": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Arbitrary data from the previous, restarted session.\nThe data is sent as the `restart` attribute of the `terminated` event.\nThe client should leave the data intact.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, noDebug=None, __restart=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean noDebug: If true, the launch request should launch the program without enabling debugging.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] __restart: Arbitrary data from the previous, restarted session.
        The data is sent as the `restart` attribute of the `terminated` event.
        The client should leave the data intact.
        """
        self.noDebug = noDebug
        self.__restart = __restart
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        noDebug = self.noDebug
        __restart = self.__restart
        dct = {}
        if noDebug is not None:
            dct["noDebug"] = noDebug
        if __restart is not None:
            dct["__restart"] = __restart
        dct.update(self.kwargs)
        return dct


@register_response("launch")
@register
class LaunchResponse(BaseSchema):
    """
    Response to `launch` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("attach")
@register
class AttachRequest(BaseSchema):
    """
    The `attach` request is sent from the client to the debug adapter to attach to a debuggee that is
    already running.

    Since attaching is debugger/runtime specific, the arguments for this request are not part of this
    specification.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["attach"]},
        "arguments": {"type": "AttachRequestArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param AttachRequestArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "attach"
        if arguments is None:
            self.arguments = AttachRequestArguments()
        else:
            self.arguments = (
                AttachRequestArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != AttachRequestArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class AttachRequestArguments(BaseSchema):
    """
    Arguments for `attach` request. Additional attributes are implementation specific.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "__restart": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Arbitrary data from the previous, restarted session.\nThe data is sent as the `restart` attribute of the `terminated` event.\nThe client should leave the data intact.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, __restart=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] __restart: Arbitrary data from the previous, restarted session.
        The data is sent as the `restart` attribute of the `terminated` event.
        The client should leave the data intact.
        """
        self.__restart = __restart
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        __restart = self.__restart
        dct = {}
        if __restart is not None:
            dct["__restart"] = __restart
        dct.update(self.kwargs)
        return dct


@register_response("attach")
@register
class AttachResponse(BaseSchema):
    """
    Response to `attach` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("restart")
@register
class RestartRequest(BaseSchema):
    """
    Restarts a debug session. Clients should only call this request if the corresponding capability
    `supportsRestartRequest` is true.

    If the capability is missing or has the value false, a typical client emulates `restart` by
    terminating the debug adapter first and then launching it anew.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["restart"]},
        "arguments": {"type": "RestartArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param RestartArguments arguments:
        """
        self.type = "request"
        self.command = "restart"
        self.seq = seq
        if arguments is None:
            self.arguments = RestartArguments()
        else:
            self.arguments = (
                RestartArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != RestartArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class RestartArguments(BaseSchema):
    """
    Arguments for `restart` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "arguments": {
            "oneOf": [{"$ref": "#/definitions/LaunchRequestArguments"}, {"$ref": "#/definitions/AttachRequestArguments"}],
            "description": "The latest version of the `launch` or `attach` configuration.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param TypeNA arguments: The latest version of the `launch` or `attach` configuration.
        """
        self.arguments = arguments
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        arguments = self.arguments
        dct = {}
        if arguments is not None:
            dct["arguments"] = arguments
        dct.update(self.kwargs)
        return dct


@register_response("restart")
@register
class RestartResponse(BaseSchema):
    """
    Response to `restart` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("disconnect")
@register
class DisconnectRequest(BaseSchema):
    """
    The `disconnect` request asks the debug adapter to disconnect from the debuggee (thus ending the
    debug session) and then to shut down itself (the debug adapter).

    In addition, the debug adapter must terminate the debuggee if it was started with the `launch`
    request. If an `attach` request was used to connect to the debuggee, then the debug adapter must not
    terminate the debuggee.

    This implicit behavior of when to terminate the debuggee can be overridden with the
    `terminateDebuggee` argument (which is only supported by a debug adapter if the corresponding
    capability `supportTerminateDebuggee` is true).

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["disconnect"]},
        "arguments": {"type": "DisconnectArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param DisconnectArguments arguments:
        """
        self.type = "request"
        self.command = "disconnect"
        self.seq = seq
        if arguments is None:
            self.arguments = DisconnectArguments()
        else:
            self.arguments = (
                DisconnectArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != DisconnectArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class DisconnectArguments(BaseSchema):
    """
    Arguments for `disconnect` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "restart": {
            "type": "boolean",
            "description": "A value of True indicates that this `disconnect` request is part of a restart sequence.",
        },
        "terminateDebuggee": {
            "type": "boolean",
            "description": "Indicates whether the debuggee should be terminated when the debugger is disconnected.\nIf unspecified, the debug adapter is free to do whatever it thinks is best.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportTerminateDebuggee` is True.",
        },
        "suspendDebuggee": {
            "type": "boolean",
            "description": "Indicates whether the debuggee should stay suspended when the debugger is disconnected.\nIf unspecified, the debuggee should resume execution.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportSuspendDebuggee` is True.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, restart=None, terminateDebuggee=None, suspendDebuggee=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean restart: A value of true indicates that this `disconnect` request is part of a restart sequence.
        :param boolean terminateDebuggee: Indicates whether the debuggee should be terminated when the debugger is disconnected.
        If unspecified, the debug adapter is free to do whatever it thinks is best.
        The attribute is only honored by a debug adapter if the corresponding capability `supportTerminateDebuggee` is true.
        :param boolean suspendDebuggee: Indicates whether the debuggee should stay suspended when the debugger is disconnected.
        If unspecified, the debuggee should resume execution.
        The attribute is only honored by a debug adapter if the corresponding capability `supportSuspendDebuggee` is true.
        """
        self.restart = restart
        self.terminateDebuggee = terminateDebuggee
        self.suspendDebuggee = suspendDebuggee
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        restart = self.restart
        terminateDebuggee = self.terminateDebuggee
        suspendDebuggee = self.suspendDebuggee
        dct = {}
        if restart is not None:
            dct["restart"] = restart
        if terminateDebuggee is not None:
            dct["terminateDebuggee"] = terminateDebuggee
        if suspendDebuggee is not None:
            dct["suspendDebuggee"] = suspendDebuggee
        dct.update(self.kwargs)
        return dct


@register_response("disconnect")
@register
class DisconnectResponse(BaseSchema):
    """
    Response to `disconnect` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("terminate")
@register
class TerminateRequest(BaseSchema):
    """
    The `terminate` request is sent from the client to the debug adapter in order to shut down the
    debuggee gracefully. Clients should only call this request if the capability
    `supportsTerminateRequest` is true.

    Typically a debug adapter implements `terminate` by sending a software signal which the debuggee
    intercepts in order to clean things up properly before terminating itself.

    Please note that this request does not directly affect the state of the debug session: if the
    debuggee decides to veto the graceful shutdown for any reason by not terminating itself, then the
    debug session just continues.

    Clients can surface the `terminate` request as an explicit command or they can integrate it into a
    two stage Stop command that first sends `terminate` to request a graceful shutdown, and if that
    fails uses `disconnect` for a forceful shutdown.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["terminate"]},
        "arguments": {"type": "TerminateArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param TerminateArguments arguments:
        """
        self.type = "request"
        self.command = "terminate"
        self.seq = seq
        if arguments is None:
            self.arguments = TerminateArguments()
        else:
            self.arguments = (
                TerminateArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != TerminateArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class TerminateArguments(BaseSchema):
    """
    Arguments for `terminate` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "restart": {
            "type": "boolean",
            "description": "A value of True indicates that this `terminate` request is part of a restart sequence.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, restart=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean restart: A value of true indicates that this `terminate` request is part of a restart sequence.
        """
        self.restart = restart
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        restart = self.restart
        dct = {}
        if restart is not None:
            dct["restart"] = restart
        dct.update(self.kwargs)
        return dct


@register_response("terminate")
@register
class TerminateResponse(BaseSchema):
    """
    Response to `terminate` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("breakpointLocations")
@register
class BreakpointLocationsRequest(BaseSchema):
    """
    The `breakpointLocations` request returns all possible locations for source breakpoints in a given
    range.

    Clients should only call this request if the corresponding capability
    `supportsBreakpointLocationsRequest` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["breakpointLocations"]},
        "arguments": {"type": "BreakpointLocationsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param BreakpointLocationsArguments arguments:
        """
        self.type = "request"
        self.command = "breakpointLocations"
        self.seq = seq
        if arguments is None:
            self.arguments = BreakpointLocationsArguments()
        else:
            self.arguments = (
                BreakpointLocationsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != BreakpointLocationsArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class BreakpointLocationsArguments(BaseSchema):
    """
    Arguments for `breakpointLocations` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "source": {
            "description": "The source location of the breakpoints; either `source.path` or `source.sourceReference` must be specified.",
            "type": "Source",
        },
        "line": {
            "type": "integer",
            "description": "Start line of range to search possible breakpoint locations in. If only the line is specified, the request returns all possible locations in that line.",
        },
        "column": {
            "type": "integer",
            "description": "Start position within `line` to search possible breakpoint locations in. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If no column is given, the first position in the start line is assumed.",
        },
        "endLine": {
            "type": "integer",
            "description": "End line of range to search possible breakpoint locations in. If no end line is given, then the end line is assumed to be the start line.",
        },
        "endColumn": {
            "type": "integer",
            "description": "End position within `endLine` to search possible breakpoint locations in. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If no end column is given, the last position in the end line is assumed.",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, source, line, column=None, endLine=None, endColumn=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param Source source: The source location of the breakpoints; either `source.path` or `source.sourceReference` must be specified.
        :param integer line: Start line of range to search possible breakpoint locations in. If only the line is specified, the request returns all possible locations in that line.
        :param integer column: Start position within `line` to search possible breakpoint locations in. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If no column is given, the first position in the start line is assumed.
        :param integer endLine: End line of range to search possible breakpoint locations in. If no end line is given, then the end line is assumed to be the start line.
        :param integer endColumn: End position within `endLine` to search possible breakpoint locations in. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If no end column is given, the last position in the end line is assumed.
        """
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.line = line
        self.column = column
        self.endLine = endLine
        self.endColumn = endColumn
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        source = self.source
        line = self.line
        column = self.column
        endLine = self.endLine
        endColumn = self.endColumn
        dct = {
            "source": source.to_dict(update_ids_to_dap=update_ids_to_dap),
            "line": line,
        }
        if column is not None:
            dct["column"] = column
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        dct.update(self.kwargs)
        return dct


@register_response("breakpointLocations")
@register
class BreakpointLocationsResponse(BaseSchema):
    """
    Response to `breakpointLocations` request.

    Contains possible locations for source breakpoints.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "breakpoints": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/BreakpointLocation"},
                    "description": "Sorted set of possible breakpoint locations.",
                }
            },
            "required": ["breakpoints"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param BreakpointLocationsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = BreakpointLocationsResponseBody()
        else:
            self.body = (
                BreakpointLocationsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != BreakpointLocationsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("setBreakpoints")
@register
class SetBreakpointsRequest(BaseSchema):
    """
    Sets multiple breakpoints for a single source and clears all previous breakpoints in that source.

    To clear all breakpoint for a source, specify an empty array.

    When a breakpoint is hit, a `stopped` event (with reason `breakpoint`) is generated.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setBreakpoints"]},
        "arguments": {"type": "SetBreakpointsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetBreakpointsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setBreakpoints"
        if arguments is None:
            self.arguments = SetBreakpointsArguments()
        else:
            self.arguments = (
                SetBreakpointsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetBreakpointsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetBreakpointsArguments(BaseSchema):
    """
    Arguments for `setBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "source": {
            "description": "The source location of the breakpoints; either `source.path` or `source.sourceReference` must be specified.",
            "type": "Source",
        },
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/SourceBreakpoint"},
            "description": "The code locations of the breakpoints.",
        },
        "lines": {"type": "array", "items": {"type": "integer"}, "description": "Deprecated: The code locations of the breakpoints."},
        "sourceModified": {
            "type": "boolean",
            "description": "A value of True indicates that the underlying source has been modified which results in new breakpoint locations.",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, source, breakpoints=None, lines=None, sourceModified=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param Source source: The source location of the breakpoints; either `source.path` or `source.sourceReference` must be specified.
        :param array breakpoints: The code locations of the breakpoints.
        :param array lines: Deprecated: The code locations of the breakpoints.
        :param boolean sourceModified: A value of true indicates that the underlying source has been modified which results in new breakpoint locations.
        """
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                SourceBreakpoint.update_dict_ids_from_dap(o)
        self.lines = lines
        self.sourceModified = sourceModified
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        source = self.source
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        lines = self.lines
        if lines and hasattr(lines[0], "to_dict"):
            lines = [x.to_dict() for x in lines]
        sourceModified = self.sourceModified
        dct = {
            "source": source.to_dict(update_ids_to_dap=update_ids_to_dap),
        }
        if breakpoints is not None:
            dct["breakpoints"] = (
                [SourceBreakpoint.update_dict_ids_to_dap(o) for o in breakpoints] if (update_ids_to_dap and breakpoints) else breakpoints
            )
        if lines is not None:
            dct["lines"] = lines
        if sourceModified is not None:
            dct["sourceModified"] = sourceModified
        dct.update(self.kwargs)
        return dct


@register_response("setBreakpoints")
@register
class SetBreakpointsResponse(BaseSchema):
    """
    Response to `setBreakpoints` request.

    Returned is information about each breakpoint created by this request.

    This includes the actual code location and whether the breakpoint could be verified.

    The breakpoints returned are in the same order as the elements of the `breakpoints`

    (or the deprecated `lines`) array in the arguments.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "breakpoints": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Breakpoint"},
                    "description": "Information about the breakpoints.\nThe array elements are in the same order as the elements of the `breakpoints` (or the deprecated `lines`) array in the arguments.",
                }
            },
            "required": ["breakpoints"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param SetBreakpointsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = SetBreakpointsResponseBody()
        else:
            self.body = (
                SetBreakpointsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != SetBreakpointsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("setFunctionBreakpoints")
@register
class SetFunctionBreakpointsRequest(BaseSchema):
    """
    Replaces all existing function breakpoints with new function breakpoints.

    To clear all function breakpoints, specify an empty array.

    When a function breakpoint is hit, a `stopped` event (with reason `function breakpoint`) is
    generated.

    Clients should only call this request if the corresponding capability `supportsFunctionBreakpoints`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setFunctionBreakpoints"]},
        "arguments": {"type": "SetFunctionBreakpointsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetFunctionBreakpointsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setFunctionBreakpoints"
        if arguments is None:
            self.arguments = SetFunctionBreakpointsArguments()
        else:
            self.arguments = (
                SetFunctionBreakpointsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetFunctionBreakpointsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetFunctionBreakpointsArguments(BaseSchema):
    """
    Arguments for `setFunctionBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/FunctionBreakpoint"},
            "description": "The function names of the breakpoints.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: The function names of the breakpoints.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                FunctionBreakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [FunctionBreakpoint.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register_response("setFunctionBreakpoints")
@register
class SetFunctionBreakpointsResponse(BaseSchema):
    """
    Response to `setFunctionBreakpoints` request.

    Returned is information about each breakpoint created by this request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "breakpoints": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Breakpoint"},
                    "description": "Information about the breakpoints. The array elements correspond to the elements of the `breakpoints` array.",
                }
            },
            "required": ["breakpoints"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param SetFunctionBreakpointsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = SetFunctionBreakpointsResponseBody()
        else:
            self.body = (
                SetFunctionBreakpointsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != SetFunctionBreakpointsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("setExceptionBreakpoints")
@register
class SetExceptionBreakpointsRequest(BaseSchema):
    """
    The request configures the debugger's response to thrown exceptions.

    If an exception is configured to break, a `stopped` event is fired (with reason `exception`).

    Clients should only call this request if the corresponding capability `exceptionBreakpointFilters`
    returns one or more filters.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setExceptionBreakpoints"]},
        "arguments": {"type": "SetExceptionBreakpointsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetExceptionBreakpointsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setExceptionBreakpoints"
        if arguments is None:
            self.arguments = SetExceptionBreakpointsArguments()
        else:
            self.arguments = (
                SetExceptionBreakpointsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetExceptionBreakpointsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetExceptionBreakpointsArguments(BaseSchema):
    """
    Arguments for `setExceptionBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "filters": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Set of exception filters specified by their ID. The set of all possible exception filters is defined by the `exceptionBreakpointFilters` capability. The `filter` and `filterOptions` sets are additive.",
        },
        "filterOptions": {
            "type": "array",
            "items": {"$ref": "#/definitions/ExceptionFilterOptions"},
            "description": "Set of exception filters and their options. The set of all possible exception filters is defined by the `exceptionBreakpointFilters` capability. This attribute is only honored by a debug adapter if the corresponding capability `supportsExceptionFilterOptions` is True. The `filter` and `filterOptions` sets are additive.",
        },
        "exceptionOptions": {
            "type": "array",
            "items": {"$ref": "#/definitions/ExceptionOptions"},
            "description": "Configuration options for selected exceptions.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsExceptionOptions` is True.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, filters, filterOptions=None, exceptionOptions=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array filters: Set of exception filters specified by their ID. The set of all possible exception filters is defined by the `exceptionBreakpointFilters` capability. The `filter` and `filterOptions` sets are additive.
        :param array filterOptions: Set of exception filters and their options. The set of all possible exception filters is defined by the `exceptionBreakpointFilters` capability. This attribute is only honored by a debug adapter if the corresponding capability `supportsExceptionFilterOptions` is true. The `filter` and `filterOptions` sets are additive.
        :param array exceptionOptions: Configuration options for selected exceptions.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsExceptionOptions` is true.
        """
        self.filters = filters
        self.filterOptions = filterOptions
        if update_ids_from_dap and self.filterOptions:
            for o in self.filterOptions:
                ExceptionFilterOptions.update_dict_ids_from_dap(o)
        self.exceptionOptions = exceptionOptions
        if update_ids_from_dap and self.exceptionOptions:
            for o in self.exceptionOptions:
                ExceptionOptions.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        filters = self.filters
        if filters and hasattr(filters[0], "to_dict"):
            filters = [x.to_dict() for x in filters]
        filterOptions = self.filterOptions
        if filterOptions and hasattr(filterOptions[0], "to_dict"):
            filterOptions = [x.to_dict() for x in filterOptions]
        exceptionOptions = self.exceptionOptions
        if exceptionOptions and hasattr(exceptionOptions[0], "to_dict"):
            exceptionOptions = [x.to_dict() for x in exceptionOptions]
        dct = {
            "filters": filters,
        }
        if filterOptions is not None:
            dct["filterOptions"] = (
                [ExceptionFilterOptions.update_dict_ids_to_dap(o) for o in filterOptions]
                if (update_ids_to_dap and filterOptions)
                else filterOptions
            )
        if exceptionOptions is not None:
            dct["exceptionOptions"] = (
                [ExceptionOptions.update_dict_ids_to_dap(o) for o in exceptionOptions]
                if (update_ids_to_dap and exceptionOptions)
                else exceptionOptions
            )
        dct.update(self.kwargs)
        return dct


@register_response("setExceptionBreakpoints")
@register
class SetExceptionBreakpointsResponse(BaseSchema):
    """
    Response to `setExceptionBreakpoints` request.

    The response contains an array of `Breakpoint` objects with information about each exception
    breakpoint or filter. The `Breakpoint` objects are in the same order as the elements of the
    `filters`, `filterOptions`, `exceptionOptions` arrays given as arguments. If both `filters` and
    `filterOptions` are given, the returned array must start with `filters` information first, followed
    by `filterOptions` information.

    The `verified` property of a `Breakpoint` object signals whether the exception breakpoint or filter
    could be successfully created and whether the condition is valid. In case of an error the `message`
    property explains the problem. The `id` property can be used to introduce a unique ID for the
    exception breakpoint or filter so that it can be updated subsequently by sending breakpoint events.

    For backward compatibility both the `breakpoints` array and the enclosing `body` are optional. If
    these elements are missing a client is not able to show problems for individual exception
    breakpoints or filters.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "breakpoints": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Breakpoint"},
                    "description": "Information about the exception breakpoints or filters.\nThe breakpoints returned are in the same order as the elements of the `filters`, `filterOptions`, `exceptionOptions` arrays in the arguments. If both `filters` and `filterOptions` are given, the returned array must start with `filters` information first, followed by `filterOptions` information.",
                }
            },
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param SetExceptionBreakpointsResponseBody body:
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        if body is None:
            self.body = SetExceptionBreakpointsResponseBody()
        else:
            self.body = (
                SetExceptionBreakpointsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != SetExceptionBreakpointsResponseBody
                else body
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register_request("dataBreakpointInfo")
@register
class DataBreakpointInfoRequest(BaseSchema):
    """
    Obtains information on a possible data breakpoint that could be set on an expression or variable.

    Clients should only call this request if the corresponding capability `supportsDataBreakpoints` is
    true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["dataBreakpointInfo"]},
        "arguments": {"type": "DataBreakpointInfoArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param DataBreakpointInfoArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "dataBreakpointInfo"
        if arguments is None:
            self.arguments = DataBreakpointInfoArguments()
        else:
            self.arguments = (
                DataBreakpointInfoArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != DataBreakpointInfoArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class DataBreakpointInfoArguments(BaseSchema):
    """
    Arguments for `dataBreakpointInfo` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "variablesReference": {
            "type": "integer",
            "description": "Reference to the variable container if the data breakpoint is requested for a child of the container. The `variablesReference` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "name": {
            "type": "string",
            "description": "The name of the variable's child to obtain data breakpoint information for.\nIf `variablesReference` isn't specified, this can be an expression.",
        },
        "frameId": {
            "type": "integer",
            "description": "When `name` is an expression, evaluate it in the scope of this stack frame. If not specified, the expression is evaluated in the global scope. When `variablesReference` is specified, this property has no effect.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, name, variablesReference=None, frameId=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: The name of the variable's child to obtain data breakpoint information for.
        If `variablesReference` isn't specified, this can be an expression.
        :param integer variablesReference: Reference to the variable container if the data breakpoint is requested for a child of the container. The `variablesReference` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.
        :param integer frameId: When `name` is an expression, evaluate it in the scope of this stack frame. If not specified, the expression is evaluated in the global scope. When `variablesReference` is specified, this property has no effect.
        """
        self.name = name
        self.variablesReference = variablesReference
        self.frameId = frameId
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
            self.frameId = self._translate_id_from_dap(self.frameId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_from_dap(dct["frameId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        variablesReference = self.variablesReference
        frameId = self.frameId
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
            if frameId is not None:
                frameId = self._translate_id_to_dap(frameId)
        dct = {
            "name": name,
        }
        if variablesReference is not None:
            dct["variablesReference"] = variablesReference
        if frameId is not None:
            dct["frameId"] = frameId
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_to_dap(dct["frameId"])
        return dct


@register_response("dataBreakpointInfo")
@register
class DataBreakpointInfoResponse(BaseSchema):
    """
    Response to `dataBreakpointInfo` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "dataId": {
                    "type": ["string", "null"],
                    "description": "An identifier for the data on which a data breakpoint can be registered with the `setDataBreakpoints` request or null if no data breakpoint is available. If a `variablesReference` or `frameId` is passed, the `dataId` is valid in the current suspended state, otherwise it's valid indefinitely. See 'Lifetime of Object References' in the Overview section for details. Breakpoints set using the `dataId` in the `setDataBreakpoints` request may outlive the lifetime of the associated `dataId`.",
                },
                "description": {
                    "type": "string",
                    "description": "UI string that describes on what data the breakpoint is set on or why a data breakpoint is not available.",
                },
                "accessTypes": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/DataBreakpointAccessType"},
                    "description": "Attribute lists the available access types for a potential data breakpoint. A UI client could surface this information.",
                },
                "canPersist": {
                    "type": "boolean",
                    "description": "Attribute indicates that a potential data breakpoint could be persisted across sessions.",
                },
            },
            "required": ["dataId", "description"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param DataBreakpointInfoResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = DataBreakpointInfoResponseBody()
        else:
            self.body = (
                DataBreakpointInfoResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != DataBreakpointInfoResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("setDataBreakpoints")
@register
class SetDataBreakpointsRequest(BaseSchema):
    """
    Replaces all existing data breakpoints with new data breakpoints.

    To clear all data breakpoints, specify an empty array.

    When a data breakpoint is hit, a `stopped` event (with reason `data breakpoint`) is generated.

    Clients should only call this request if the corresponding capability `supportsDataBreakpoints` is
    true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setDataBreakpoints"]},
        "arguments": {"type": "SetDataBreakpointsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetDataBreakpointsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setDataBreakpoints"
        if arguments is None:
            self.arguments = SetDataBreakpointsArguments()
        else:
            self.arguments = (
                SetDataBreakpointsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetDataBreakpointsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetDataBreakpointsArguments(BaseSchema):
    """
    Arguments for `setDataBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/DataBreakpoint"},
            "description": "The contents of this array replaces all existing data breakpoints. An empty array clears all data breakpoints.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: The contents of this array replaces all existing data breakpoints. An empty array clears all data breakpoints.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                DataBreakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [DataBreakpoint.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register_response("setDataBreakpoints")
@register
class SetDataBreakpointsResponse(BaseSchema):
    """
    Response to `setDataBreakpoints` request.

    Returned is information about each breakpoint created by this request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "breakpoints": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Breakpoint"},
                    "description": "Information about the data breakpoints. The array elements correspond to the elements of the input argument `breakpoints` array.",
                }
            },
            "required": ["breakpoints"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param SetDataBreakpointsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = SetDataBreakpointsResponseBody()
        else:
            self.body = (
                SetDataBreakpointsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != SetDataBreakpointsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("setInstructionBreakpoints")
@register
class SetInstructionBreakpointsRequest(BaseSchema):
    """
    Replaces all existing instruction breakpoints. Typically, instruction breakpoints would be set from
    a disassembly window.

    To clear all instruction breakpoints, specify an empty array.

    When an instruction breakpoint is hit, a `stopped` event (with reason `instruction breakpoint`) is
    generated.

    Clients should only call this request if the corresponding capability
    `supportsInstructionBreakpoints` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setInstructionBreakpoints"]},
        "arguments": {"type": "SetInstructionBreakpointsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetInstructionBreakpointsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setInstructionBreakpoints"
        if arguments is None:
            self.arguments = SetInstructionBreakpointsArguments()
        else:
            self.arguments = (
                SetInstructionBreakpointsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetInstructionBreakpointsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetInstructionBreakpointsArguments(BaseSchema):
    """
    Arguments for `setInstructionBreakpoints` request

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/InstructionBreakpoint"},
            "description": "The instruction references of the breakpoints",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: The instruction references of the breakpoints
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                InstructionBreakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [InstructionBreakpoint.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register_response("setInstructionBreakpoints")
@register
class SetInstructionBreakpointsResponse(BaseSchema):
    """
    Response to `setInstructionBreakpoints` request

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "breakpoints": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Breakpoint"},
                    "description": "Information about the breakpoints. The array elements correspond to the elements of the `breakpoints` array.",
                }
            },
            "required": ["breakpoints"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param SetInstructionBreakpointsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = SetInstructionBreakpointsResponseBody()
        else:
            self.body = (
                SetInstructionBreakpointsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != SetInstructionBreakpointsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("continue")
@register
class ContinueRequest(BaseSchema):
    """
    The request resumes execution of all threads. If the debug adapter supports single thread execution
    (see capability `supportsSingleThreadExecutionRequests`), setting the `singleThread` argument to
    true resumes only the specified thread. If not all threads were resumed, the `allThreadsContinued`
    attribute of the response should be set to false.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["continue"]},
        "arguments": {"type": "ContinueArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param ContinueArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "continue"
        if arguments is None:
            self.arguments = ContinueArguments()
        else:
            self.arguments = (
                ContinueArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != ContinueArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class ContinueArguments(BaseSchema):
    """
    Arguments for `continue` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {
            "type": "integer",
            "description": "Specifies the active thread. If the debug adapter supports single thread execution (see `supportsSingleThreadExecutionRequests`) and the argument `singleThread` is True, only the thread with this ID is resumed.",
        },
        "singleThread": {
            "type": "boolean",
            "description": "If this flag is True, execution is resumed only for the thread with given `threadId`.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, singleThread=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Specifies the active thread. If the debug adapter supports single thread execution (see `supportsSingleThreadExecutionRequests`) and the argument `singleThread` is true, only the thread with this ID is resumed.
        :param boolean singleThread: If this flag is true, execution is resumed only for the thread with given `threadId`.
        """
        self.threadId = threadId
        self.singleThread = singleThread
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        singleThread = self.singleThread
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if singleThread is not None:
            dct["singleThread"] = singleThread
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("continue")
@register
class ContinueResponse(BaseSchema):
    """
    Response to `continue` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "allThreadsContinued": {
                    "type": "boolean",
                    "description": "The value True (or a missing property) signals to the client that all threads have been resumed. The value false indicates that not all threads were resumed.",
                }
            },
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param ContinueResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = ContinueResponseBody()
        else:
            self.body = (
                ContinueResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ContinueResponseBody else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("next")
@register
class NextRequest(BaseSchema):
    """
    The request executes one step (in the given granularity) for the specified thread and allows all
    other threads to run freely by resuming them.

    If the debug adapter supports single thread execution (see capability
    `supportsSingleThreadExecutionRequests`), setting the `singleThread` argument to true prevents other
    suspended threads from resuming.

    The debug adapter first sends the response and then a `stopped` event (with reason `step`) after the
    step has completed.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["next"]},
        "arguments": {"type": "NextArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param NextArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "next"
        if arguments is None:
            self.arguments = NextArguments()
        else:
            self.arguments = (
                NextArguments(update_ids_from_dap=update_ids_from_dap, **arguments) if arguments.__class__ != NextArguments else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class NextArguments(BaseSchema):
    """
    Arguments for `next` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {
            "type": "integer",
            "description": "Specifies the thread for which to resume execution for one step (of the given granularity).",
        },
        "singleThread": {"type": "boolean", "description": "If this flag is True, all other suspended threads are not resumed."},
        "granularity": {
            "description": "Stepping granularity. If no granularity is specified, a granularity of `statement` is assumed.",
            "type": "SteppingGranularity",
        },
    }
    __refs__ = set(["granularity"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, singleThread=None, granularity=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Specifies the thread for which to resume execution for one step (of the given granularity).
        :param boolean singleThread: If this flag is true, all other suspended threads are not resumed.
        :param SteppingGranularity granularity: Stepping granularity. If no granularity is specified, a granularity of `statement` is assumed.
        """
        self.threadId = threadId
        self.singleThread = singleThread
        if granularity is not None:
            assert granularity in SteppingGranularity.VALID_VALUES
        self.granularity = granularity
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        singleThread = self.singleThread
        granularity = self.granularity
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if singleThread is not None:
            dct["singleThread"] = singleThread
        if granularity is not None:
            dct["granularity"] = granularity
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("next")
@register
class NextResponse(BaseSchema):
    """
    Response to `next` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("stepIn")
@register
class StepInRequest(BaseSchema):
    """
    The request resumes the given thread to step into a function/method and allows all other threads to
    run freely by resuming them.

    If the debug adapter supports single thread execution (see capability
    `supportsSingleThreadExecutionRequests`), setting the `singleThread` argument to true prevents other
    suspended threads from resuming.

    If the request cannot step into a target, `stepIn` behaves like the `next` request.

    The debug adapter first sends the response and then a `stopped` event (with reason `step`) after the
    step has completed.

    If there are multiple function/method calls (or other targets) on the source line,

    the argument `targetId` can be used to control into which target the `stepIn` should occur.

    The list of possible targets for a given source line can be retrieved via the `stepInTargets`
    request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["stepIn"]},
        "arguments": {"type": "StepInArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param StepInArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "stepIn"
        if arguments is None:
            self.arguments = StepInArguments()
        else:
            self.arguments = (
                StepInArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != StepInArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class StepInArguments(BaseSchema):
    """
    Arguments for `stepIn` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {
            "type": "integer",
            "description": "Specifies the thread for which to resume execution for one step-into (of the given granularity).",
        },
        "singleThread": {"type": "boolean", "description": "If this flag is True, all other suspended threads are not resumed."},
        "targetId": {"type": "integer", "description": "Id of the target to step into."},
        "granularity": {
            "description": "Stepping granularity. If no granularity is specified, a granularity of `statement` is assumed.",
            "type": "SteppingGranularity",
        },
    }
    __refs__ = set(["granularity"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, singleThread=None, targetId=None, granularity=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Specifies the thread for which to resume execution for one step-into (of the given granularity).
        :param boolean singleThread: If this flag is true, all other suspended threads are not resumed.
        :param integer targetId: Id of the target to step into.
        :param SteppingGranularity granularity: Stepping granularity. If no granularity is specified, a granularity of `statement` is assumed.
        """
        self.threadId = threadId
        self.singleThread = singleThread
        self.targetId = targetId
        if granularity is not None:
            assert granularity in SteppingGranularity.VALID_VALUES
        self.granularity = granularity
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        singleThread = self.singleThread
        targetId = self.targetId
        granularity = self.granularity
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if singleThread is not None:
            dct["singleThread"] = singleThread
        if targetId is not None:
            dct["targetId"] = targetId
        if granularity is not None:
            dct["granularity"] = granularity
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("stepIn")
@register
class StepInResponse(BaseSchema):
    """
    Response to `stepIn` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("stepOut")
@register
class StepOutRequest(BaseSchema):
    """
    The request resumes the given thread to step out (return) from a function/method and allows all
    other threads to run freely by resuming them.

    If the debug adapter supports single thread execution (see capability
    `supportsSingleThreadExecutionRequests`), setting the `singleThread` argument to true prevents other
    suspended threads from resuming.

    The debug adapter first sends the response and then a `stopped` event (with reason `step`) after the
    step has completed.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["stepOut"]},
        "arguments": {"type": "StepOutArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param StepOutArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "stepOut"
        if arguments is None:
            self.arguments = StepOutArguments()
        else:
            self.arguments = (
                StepOutArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != StepOutArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class StepOutArguments(BaseSchema):
    """
    Arguments for `stepOut` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {
            "type": "integer",
            "description": "Specifies the thread for which to resume execution for one step-out (of the given granularity).",
        },
        "singleThread": {"type": "boolean", "description": "If this flag is True, all other suspended threads are not resumed."},
        "granularity": {
            "description": "Stepping granularity. If no granularity is specified, a granularity of `statement` is assumed.",
            "type": "SteppingGranularity",
        },
    }
    __refs__ = set(["granularity"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, singleThread=None, granularity=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Specifies the thread for which to resume execution for one step-out (of the given granularity).
        :param boolean singleThread: If this flag is true, all other suspended threads are not resumed.
        :param SteppingGranularity granularity: Stepping granularity. If no granularity is specified, a granularity of `statement` is assumed.
        """
        self.threadId = threadId
        self.singleThread = singleThread
        if granularity is not None:
            assert granularity in SteppingGranularity.VALID_VALUES
        self.granularity = granularity
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        singleThread = self.singleThread
        granularity = self.granularity
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if singleThread is not None:
            dct["singleThread"] = singleThread
        if granularity is not None:
            dct["granularity"] = granularity
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("stepOut")
@register
class StepOutResponse(BaseSchema):
    """
    Response to `stepOut` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("stepBack")
@register
class StepBackRequest(BaseSchema):
    """
    The request executes one backward step (in the given granularity) for the specified thread and
    allows all other threads to run backward freely by resuming them.

    If the debug adapter supports single thread execution (see capability
    `supportsSingleThreadExecutionRequests`), setting the `singleThread` argument to true prevents other
    suspended threads from resuming.

    The debug adapter first sends the response and then a `stopped` event (with reason `step`) after the
    step has completed.

    Clients should only call this request if the corresponding capability `supportsStepBack` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["stepBack"]},
        "arguments": {"type": "StepBackArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param StepBackArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "stepBack"
        if arguments is None:
            self.arguments = StepBackArguments()
        else:
            self.arguments = (
                StepBackArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != StepBackArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class StepBackArguments(BaseSchema):
    """
    Arguments for `stepBack` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {
            "type": "integer",
            "description": "Specifies the thread for which to resume execution for one step backwards (of the given granularity).",
        },
        "singleThread": {"type": "boolean", "description": "If this flag is True, all other suspended threads are not resumed."},
        "granularity": {
            "description": "Stepping granularity to step. If no granularity is specified, a granularity of `statement` is assumed.",
            "type": "SteppingGranularity",
        },
    }
    __refs__ = set(["granularity"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, singleThread=None, granularity=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Specifies the thread for which to resume execution for one step backwards (of the given granularity).
        :param boolean singleThread: If this flag is true, all other suspended threads are not resumed.
        :param SteppingGranularity granularity: Stepping granularity to step. If no granularity is specified, a granularity of `statement` is assumed.
        """
        self.threadId = threadId
        self.singleThread = singleThread
        if granularity is not None:
            assert granularity in SteppingGranularity.VALID_VALUES
        self.granularity = granularity
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        singleThread = self.singleThread
        granularity = self.granularity
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if singleThread is not None:
            dct["singleThread"] = singleThread
        if granularity is not None:
            dct["granularity"] = granularity
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("stepBack")
@register
class StepBackResponse(BaseSchema):
    """
    Response to `stepBack` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("reverseContinue")
@register
class ReverseContinueRequest(BaseSchema):
    """
    The request resumes backward execution of all threads. If the debug adapter supports single thread
    execution (see capability `supportsSingleThreadExecutionRequests`), setting the `singleThread`
    argument to true resumes only the specified thread. If not all threads were resumed, the
    `allThreadsContinued` attribute of the response should be set to false.

    Clients should only call this request if the corresponding capability `supportsStepBack` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["reverseContinue"]},
        "arguments": {"type": "ReverseContinueArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param ReverseContinueArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "reverseContinue"
        if arguments is None:
            self.arguments = ReverseContinueArguments()
        else:
            self.arguments = (
                ReverseContinueArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != ReverseContinueArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class ReverseContinueArguments(BaseSchema):
    """
    Arguments for `reverseContinue` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {
            "type": "integer",
            "description": "Specifies the active thread. If the debug adapter supports single thread execution (see `supportsSingleThreadExecutionRequests`) and the `singleThread` argument is True, only the thread with this ID is resumed.",
        },
        "singleThread": {
            "type": "boolean",
            "description": "If this flag is True, backward execution is resumed only for the thread with given `threadId`.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, singleThread=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Specifies the active thread. If the debug adapter supports single thread execution (see `supportsSingleThreadExecutionRequests`) and the `singleThread` argument is true, only the thread with this ID is resumed.
        :param boolean singleThread: If this flag is true, backward execution is resumed only for the thread with given `threadId`.
        """
        self.threadId = threadId
        self.singleThread = singleThread
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        singleThread = self.singleThread
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if singleThread is not None:
            dct["singleThread"] = singleThread
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("reverseContinue")
@register
class ReverseContinueResponse(BaseSchema):
    """
    Response to `reverseContinue` request. This is just an acknowledgement, so no body field is
    required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("restartFrame")
@register
class RestartFrameRequest(BaseSchema):
    """
    The request restarts execution of the specified stack frame.

    The debug adapter first sends the response and then a `stopped` event (with reason `restart`) after
    the restart has completed.

    Clients should only call this request if the corresponding capability `supportsRestartFrame` is
    true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["restartFrame"]},
        "arguments": {"type": "RestartFrameArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param RestartFrameArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "restartFrame"
        if arguments is None:
            self.arguments = RestartFrameArguments()
        else:
            self.arguments = (
                RestartFrameArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != RestartFrameArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class RestartFrameArguments(BaseSchema):
    """
    Arguments for `restartFrame` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "frameId": {
            "type": "integer",
            "description": "Restart the stack frame identified by `frameId`. The `frameId` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, frameId, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer frameId: Restart the stack frame identified by `frameId`. The `frameId` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.
        """
        self.frameId = frameId
        if update_ids_from_dap:
            self.frameId = self._translate_id_from_dap(self.frameId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_from_dap(dct["frameId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        frameId = self.frameId
        if update_ids_to_dap:
            if frameId is not None:
                frameId = self._translate_id_to_dap(frameId)
        dct = {
            "frameId": frameId,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_to_dap(dct["frameId"])
        return dct


@register_response("restartFrame")
@register
class RestartFrameResponse(BaseSchema):
    """
    Response to `restartFrame` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("goto")
@register
class GotoRequest(BaseSchema):
    """
    The request sets the location where the debuggee will continue to run.

    This makes it possible to skip the execution of code or to execute code again.

    The code between the current location and the goto target is not executed but skipped.

    The debug adapter first sends the response and then a `stopped` event with reason `goto`.

    Clients should only call this request if the corresponding capability `supportsGotoTargetsRequest`
    is true (because only then goto targets exist that can be passed as arguments).

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["goto"]},
        "arguments": {"type": "GotoArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param GotoArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "goto"
        if arguments is None:
            self.arguments = GotoArguments()
        else:
            self.arguments = (
                GotoArguments(update_ids_from_dap=update_ids_from_dap, **arguments) if arguments.__class__ != GotoArguments else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class GotoArguments(BaseSchema):
    """
    Arguments for `goto` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {"type": "integer", "description": "Set the goto target for this thread."},
        "targetId": {"type": "integer", "description": "The location where the debuggee will continue to run."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, targetId, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Set the goto target for this thread.
        :param integer targetId: The location where the debuggee will continue to run.
        """
        self.threadId = threadId
        self.targetId = targetId
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        targetId = self.targetId
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
            "targetId": targetId,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("goto")
@register
class GotoResponse(BaseSchema):
    """
    Response to `goto` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("pause")
@register
class PauseRequest(BaseSchema):
    """
    The request suspends the debuggee.

    The debug adapter first sends the response and then a `stopped` event (with reason `pause`) after
    the thread has been paused successfully.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["pause"]},
        "arguments": {"type": "PauseArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param PauseArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "pause"
        if arguments is None:
            self.arguments = PauseArguments()
        else:
            self.arguments = (
                PauseArguments(update_ids_from_dap=update_ids_from_dap, **arguments) if arguments.__class__ != PauseArguments else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class PauseArguments(BaseSchema):
    """
    Arguments for `pause` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"threadId": {"type": "integer", "description": "Pause execution for this thread."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Pause execution for this thread.
        """
        self.threadId = threadId
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("pause")
@register
class PauseResponse(BaseSchema):
    """
    Response to `pause` request. This is just an acknowledgement, so no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("stackTrace")
@register
class StackTraceRequest(BaseSchema):
    """
    The request returns a stacktrace from the current execution state of a given thread.

    A client can request all stack frames by omitting the startFrame and levels arguments. For
    performance-conscious clients and if the corresponding capability `supportsDelayedStackTraceLoading`
    is true, stack frames can be retrieved in a piecemeal way with the `startFrame` and `levels`
    arguments. The response of the `stackTrace` request may contain a `totalFrames` property that hints
    at the total number of frames in the stack. If a client needs this total number upfront, it can
    issue a request for a single (first) frame and depending on the value of `totalFrames` decide how to
    proceed. In any case a client should be prepared to receive fewer frames than requested, which is an
    indication that the end of the stack has been reached.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["stackTrace"]},
        "arguments": {"type": "StackTraceArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param StackTraceArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "stackTrace"
        if arguments is None:
            self.arguments = StackTraceArguments()
        else:
            self.arguments = (
                StackTraceArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != StackTraceArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class StackTraceArguments(BaseSchema):
    """
    Arguments for `stackTrace` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {"type": "integer", "description": "Retrieve the stacktrace for this thread."},
        "startFrame": {"type": "integer", "description": "The index of the first frame to return; if omitted frames start at 0."},
        "levels": {
            "type": "integer",
            "description": "The maximum number of frames to return. If levels is not specified or 0, all frames are returned.",
        },
        "format": {
            "description": "Specifies details on how to format the stack frames.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsValueFormattingOptions` is True.",
            "type": "StackFrameFormat",
        },
    }
    __refs__ = set(["format"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, startFrame=None, levels=None, format=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Retrieve the stacktrace for this thread.
        :param integer startFrame: The index of the first frame to return; if omitted frames start at 0.
        :param integer levels: The maximum number of frames to return. If levels is not specified or 0, all frames are returned.
        :param StackFrameFormat format: Specifies details on how to format the stack frames.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsValueFormattingOptions` is true.
        """
        self.threadId = threadId
        self.startFrame = startFrame
        self.levels = levels
        if format is None:
            self.format = StackFrameFormat()
        else:
            self.format = (
                StackFrameFormat(update_ids_from_dap=update_ids_from_dap, **format) if format.__class__ != StackFrameFormat else format
            )
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        startFrame = self.startFrame
        levels = self.levels
        format = self.format  # noqa (assign to builtin)
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if startFrame is not None:
            dct["startFrame"] = startFrame
        if levels is not None:
            dct["levels"] = levels
        if format is not None:
            dct["format"] = format.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("stackTrace")
@register
class StackTraceResponse(BaseSchema):
    """
    Response to `stackTrace` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "stackFrames": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/StackFrame"},
                    "description": "The frames of the stack frame. If the array has length zero, there are no stack frames available.\nThis means that there is no location information available.",
                },
                "totalFrames": {
                    "type": "integer",
                    "description": "The total number of frames available in the stack. If omitted or if `totalFrames` is larger than the available frames, a client is expected to request frames until a request returns less frames than requested (which indicates the end of the stack). Returning monotonically increasing `totalFrames` values for subsequent requests can be used to enforce paging in the client.",
                },
            },
            "required": ["stackFrames"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param StackTraceResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = StackTraceResponseBody()
        else:
            self.body = (
                StackTraceResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != StackTraceResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("scopes")
@register
class ScopesRequest(BaseSchema):
    """
    The request returns the variable scopes for a given stack frame ID.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["scopes"]},
        "arguments": {"type": "ScopesArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param ScopesArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "scopes"
        if arguments is None:
            self.arguments = ScopesArguments()
        else:
            self.arguments = (
                ScopesArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != ScopesArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class ScopesArguments(BaseSchema):
    """
    Arguments for `scopes` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "frameId": {
            "type": "integer",
            "description": "Retrieve the scopes for the stack frame identified by `frameId`. The `frameId` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, frameId, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer frameId: Retrieve the scopes for the stack frame identified by `frameId`. The `frameId` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.
        """
        self.frameId = frameId
        if update_ids_from_dap:
            self.frameId = self._translate_id_from_dap(self.frameId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_from_dap(dct["frameId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        frameId = self.frameId
        if update_ids_to_dap:
            if frameId is not None:
                frameId = self._translate_id_to_dap(frameId)
        dct = {
            "frameId": frameId,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_to_dap(dct["frameId"])
        return dct


@register_response("scopes")
@register
class ScopesResponse(BaseSchema):
    """
    Response to `scopes` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "scopes": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Scope"},
                    "description": "The scopes of the stack frame. If the array has length zero, there are no scopes available.",
                }
            },
            "required": ["scopes"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param ScopesResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = ScopesResponseBody()
        else:
            self.body = (
                ScopesResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ScopesResponseBody else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("variables")
@register
class VariablesRequest(BaseSchema):
    """
    Retrieves all child variables for the given variable reference.

    A filter can be used to limit the fetched children to either named or indexed children.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["variables"]},
        "arguments": {"type": "VariablesArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param VariablesArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "variables"
        if arguments is None:
            self.arguments = VariablesArguments()
        else:
            self.arguments = (
                VariablesArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != VariablesArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class VariablesArguments(BaseSchema):
    """
    Arguments for `variables` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "variablesReference": {
            "type": "integer",
            "description": "The variable for which to retrieve its children. The `variablesReference` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "filter": {
            "type": "string",
            "enum": ["indexed", "named"],
            "description": "Filter to limit the child variables to either named or indexed. If omitted, both types are fetched.",
        },
        "start": {
            "type": "integer",
            "description": "The index of the first variable to return; if omitted children start at 0.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsVariablePaging` is True.",
        },
        "count": {
            "type": "integer",
            "description": "The number of variables to return. If count is missing or 0, all variables are returned.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsVariablePaging` is True.",
        },
        "format": {
            "description": "Specifies details on how to format the Variable values.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsValueFormattingOptions` is True.",
            "type": "ValueFormat",
        },
    }
    __refs__ = set(["format"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, variablesReference, filter=None, start=None, count=None, format=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer variablesReference: The variable for which to retrieve its children. The `variablesReference` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.
        :param string filter: Filter to limit the child variables to either named or indexed. If omitted, both types are fetched.
        :param integer start: The index of the first variable to return; if omitted children start at 0.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsVariablePaging` is true.
        :param integer count: The number of variables to return. If count is missing or 0, all variables are returned.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsVariablePaging` is true.
        :param ValueFormat format: Specifies details on how to format the Variable values.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsValueFormattingOptions` is true.
        """
        self.variablesReference = variablesReference
        self.filter = filter
        self.start = start
        self.count = count
        if format is None:
            self.format = ValueFormat()
        else:
            self.format = ValueFormat(update_ids_from_dap=update_ids_from_dap, **format) if format.__class__ != ValueFormat else format
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        variablesReference = self.variablesReference
        filter = self.filter  # noqa (assign to builtin)
        start = self.start
        count = self.count
        format = self.format  # noqa (assign to builtin)
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "variablesReference": variablesReference,
        }
        if filter is not None:
            dct["filter"] = filter
        if start is not None:
            dct["start"] = start
        if count is not None:
            dct["count"] = count
        if format is not None:
            dct["format"] = format.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register_response("variables")
@register
class VariablesResponse(BaseSchema):
    """
    Response to `variables` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "variables": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Variable"},
                    "description": "All (or a range) of variables for the given variable reference.",
                }
            },
            "required": ["variables"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param VariablesResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = VariablesResponseBody()
        else:
            self.body = (
                VariablesResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != VariablesResponseBody else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("setVariable")
@register
class SetVariableRequest(BaseSchema):
    """
    Set the variable with the given name in the variable container to a new value. Clients should only
    call this request if the corresponding capability `supportsSetVariable` is true.

    If a debug adapter implements both `setVariable` and `setExpression`, a client will only use
    `setExpression` if the variable has an `evaluateName` property.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setVariable"]},
        "arguments": {"type": "SetVariableArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetVariableArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setVariable"
        if arguments is None:
            self.arguments = SetVariableArguments()
        else:
            self.arguments = (
                SetVariableArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetVariableArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetVariableArguments(BaseSchema):
    """
    Arguments for `setVariable` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "variablesReference": {
            "type": "integer",
            "description": "The reference of the variable container. The `variablesReference` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "name": {"type": "string", "description": "The name of the variable in the container."},
        "value": {"type": "string", "description": "The value of the variable."},
        "format": {"description": "Specifies details on how to format the response value.", "type": "ValueFormat"},
    }
    __refs__ = set(["format"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, variablesReference, name, value, format=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer variablesReference: The reference of the variable container. The `variablesReference` must have been obtained in the current suspended state. See 'Lifetime of Object References' in the Overview section for details.
        :param string name: The name of the variable in the container.
        :param string value: The value of the variable.
        :param ValueFormat format: Specifies details on how to format the response value.
        """
        self.variablesReference = variablesReference
        self.name = name
        self.value = value
        if format is None:
            self.format = ValueFormat()
        else:
            self.format = ValueFormat(update_ids_from_dap=update_ids_from_dap, **format) if format.__class__ != ValueFormat else format
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        variablesReference = self.variablesReference
        name = self.name
        value = self.value
        format = self.format  # noqa (assign to builtin)
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "variablesReference": variablesReference,
            "name": name,
            "value": value,
        }
        if format is not None:
            dct["format"] = format.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register_response("setVariable")
@register
class SetVariableResponse(BaseSchema):
    """
    Response to `setVariable` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "The new value of the variable."},
                "type": {
                    "type": "string",
                    "description": "The type of the new value. Typically shown in the UI when hovering over the value.",
                },
                "variablesReference": {
                    "type": "integer",
                    "description": "If `variablesReference` is > 0, the new value is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
                },
                "namedVariables": {
                    "type": "integer",
                    "description": "The number of named child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
                },
                "indexedVariables": {
                    "type": "integer",
                    "description": "The number of indexed child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
                },
                "memoryReference": {
                    "type": "string",
                    "description": "A memory reference to a location appropriate for this result.\nFor pointer type eval results, this is generally a reference to the memory address contained in the pointer.\nThis attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is True.",
                },
            },
            "required": ["value"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param SetVariableResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = SetVariableResponseBody()
        else:
            self.body = (
                SetVariableResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != SetVariableResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("source")
@register
class SourceRequest(BaseSchema):
    """
    The request retrieves the source code for a given source reference.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["source"]},
        "arguments": {"type": "SourceArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SourceArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "source"
        if arguments is None:
            self.arguments = SourceArguments()
        else:
            self.arguments = (
                SourceArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SourceArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SourceArguments(BaseSchema):
    """
    Arguments for `source` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "source": {
            "description": "Specifies the source content to load. Either `source.path` or `source.sourceReference` must be specified.",
            "type": "Source",
        },
        "sourceReference": {
            "type": "integer",
            "description": "The reference to the source. This is the same as `source.sourceReference`.\nThis is provided for backward compatibility since old clients do not understand the `source` attribute.",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, sourceReference, source=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer sourceReference: The reference to the source. This is the same as `source.sourceReference`.
        This is provided for backward compatibility since old clients do not understand the `source` attribute.
        :param Source source: Specifies the source content to load. Either `source.path` or `source.sourceReference` must be specified.
        """
        self.sourceReference = sourceReference
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        sourceReference = self.sourceReference
        source = self.source
        dct = {
            "sourceReference": sourceReference,
        }
        if source is not None:
            dct["source"] = source.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register_response("source")
@register
class SourceResponse(BaseSchema):
    """
    Response to `source` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content of the source reference."},
                "mimeType": {"type": "string", "description": "Content type (MIME type) of the source."},
            },
            "required": ["content"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param SourceResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = SourceResponseBody()
        else:
            self.body = (
                SourceResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != SourceResponseBody else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("threads")
@register
class ThreadsRequest(BaseSchema):
    """
    The request retrieves a list of all threads.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["threads"]},
        "arguments": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Object containing arguments for the command.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] arguments: Object containing arguments for the command.
        """
        self.type = "request"
        self.command = "threads"
        self.seq = seq
        self.arguments = arguments
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments
        dct.update(self.kwargs)
        return dct


@register_response("threads")
@register
class ThreadsResponse(BaseSchema):
    """
    Response to `threads` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {"threads": {"type": "array", "items": {"$ref": "#/definitions/Thread"}, "description": "All threads."}},
            "required": ["threads"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param ThreadsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = ThreadsResponseBody()
        else:
            self.body = (
                ThreadsResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ThreadsResponseBody else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("terminateThreads")
@register
class TerminateThreadsRequest(BaseSchema):
    """
    The request terminates the threads with the given ids.

    Clients should only call this request if the corresponding capability
    `supportsTerminateThreadsRequest` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["terminateThreads"]},
        "arguments": {"type": "TerminateThreadsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param TerminateThreadsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "terminateThreads"
        if arguments is None:
            self.arguments = TerminateThreadsArguments()
        else:
            self.arguments = (
                TerminateThreadsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != TerminateThreadsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class TerminateThreadsArguments(BaseSchema):
    """
    Arguments for `terminateThreads` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"threadIds": {"type": "array", "items": {"type": "integer"}, "description": "Ids of threads to be terminated."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadIds=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array threadIds: Ids of threads to be terminated.
        """
        self.threadIds = threadIds
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadIds = self.threadIds
        if threadIds and hasattr(threadIds[0], "to_dict"):
            threadIds = [x.to_dict() for x in threadIds]
        dct = {}
        if threadIds is not None:
            dct["threadIds"] = threadIds
        dct.update(self.kwargs)
        return dct


@register_response("terminateThreads")
@register
class TerminateThreadsResponse(BaseSchema):
    """
    Response to `terminateThreads` request. This is just an acknowledgement, no body field is required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("modules")
@register
class ModulesRequest(BaseSchema):
    """
    Modules can be retrieved from the debug adapter with this request which can either return all
    modules or a range of modules to support paging.

    Clients should only call this request if the corresponding capability `supportsModulesRequest` is
    true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["modules"]},
        "arguments": {"type": "ModulesArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param ModulesArguments arguments:
        """
        self.type = "request"
        self.command = "modules"
        self.seq = seq
        if arguments is None:
            self.arguments = ModulesArguments()
        else:
            self.arguments = (
                ModulesArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != ModulesArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class ModulesArguments(BaseSchema):
    """
    Arguments for `modules` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "startModule": {"type": "integer", "description": "The index of the first module to return; if omitted modules start at 0."},
        "moduleCount": {
            "type": "integer",
            "description": "The number of modules to return. If `moduleCount` is not specified or 0, all modules are returned.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, startModule=None, moduleCount=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer startModule: The index of the first module to return; if omitted modules start at 0.
        :param integer moduleCount: The number of modules to return. If `moduleCount` is not specified or 0, all modules are returned.
        """
        self.startModule = startModule
        self.moduleCount = moduleCount
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        startModule = self.startModule
        moduleCount = self.moduleCount
        dct = {}
        if startModule is not None:
            dct["startModule"] = startModule
        if moduleCount is not None:
            dct["moduleCount"] = moduleCount
        dct.update(self.kwargs)
        return dct


@register_response("modules")
@register
class ModulesResponse(BaseSchema):
    """
    Response to `modules` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "modules": {"type": "array", "items": {"$ref": "#/definitions/Module"}, "description": "All modules or range of modules."},
                "totalModules": {"type": "integer", "description": "The total number of modules available."},
            },
            "required": ["modules"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param ModulesResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = ModulesResponseBody()
        else:
            self.body = (
                ModulesResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != ModulesResponseBody else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("loadedSources")
@register
class LoadedSourcesRequest(BaseSchema):
    """
    Retrieves the set of all sources currently loaded by the debugged process.

    Clients should only call this request if the corresponding capability `supportsLoadedSourcesRequest`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["loadedSources"]},
        "arguments": {"type": "LoadedSourcesArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param LoadedSourcesArguments arguments:
        """
        self.type = "request"
        self.command = "loadedSources"
        self.seq = seq
        if arguments is None:
            self.arguments = LoadedSourcesArguments()
        else:
            self.arguments = (
                LoadedSourcesArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != LoadedSourcesArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class LoadedSourcesArguments(BaseSchema):
    """
    Arguments for `loadedSources` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register_response("loadedSources")
@register
class LoadedSourcesResponse(BaseSchema):
    """
    Response to `loadedSources` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "sources": {"type": "array", "items": {"$ref": "#/definitions/Source"}, "description": "Set of loaded sources."}
            },
            "required": ["sources"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param LoadedSourcesResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = LoadedSourcesResponseBody()
        else:
            self.body = (
                LoadedSourcesResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != LoadedSourcesResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("evaluate")
@register
class EvaluateRequest(BaseSchema):
    """
    Evaluates the given expression in the context of the topmost stack frame.

    The expression has access to any variables and arguments that are in scope.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["evaluate"]},
        "arguments": {"type": "EvaluateArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param EvaluateArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "evaluate"
        if arguments is None:
            self.arguments = EvaluateArguments()
        else:
            self.arguments = (
                EvaluateArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != EvaluateArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class EvaluateArguments(BaseSchema):
    """
    Arguments for `evaluate` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "expression": {"type": "string", "description": "The expression to evaluate."},
        "frameId": {
            "type": "integer",
            "description": "Evaluate the expression in the scope of this stack frame. If not specified, the expression is evaluated in the global scope.",
        },
        "context": {
            "type": "string",
            "_enum": ["watch", "repl", "hover", "clipboard", "variables"],
            "enumDescriptions": [
                "evaluate is called from a watch view context.",
                "evaluate is called from a REPL context.",
                "evaluate is called to generate the debug hover contents.\nThis value should only be used if the corresponding capability `supportsEvaluateForHovers` is True.",
                "evaluate is called to generate clipboard contents.\nThis value should only be used if the corresponding capability `supportsClipboardContext` is True.",
                "evaluate is called from a variables view context.",
            ],
            "description": "The context in which the evaluate request is used.",
        },
        "format": {
            "description": "Specifies details on how to format the result.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsValueFormattingOptions` is True.",
            "type": "ValueFormat",
        },
    }
    __refs__ = set(["format"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, expression, frameId=None, context=None, format=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string expression: The expression to evaluate.
        :param integer frameId: Evaluate the expression in the scope of this stack frame. If not specified, the expression is evaluated in the global scope.
        :param string context: The context in which the evaluate request is used.
        :param ValueFormat format: Specifies details on how to format the result.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsValueFormattingOptions` is true.
        """
        self.expression = expression
        self.frameId = frameId
        self.context = context
        if format is None:
            self.format = ValueFormat()
        else:
            self.format = ValueFormat(update_ids_from_dap=update_ids_from_dap, **format) if format.__class__ != ValueFormat else format
        if update_ids_from_dap:
            self.frameId = self._translate_id_from_dap(self.frameId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_from_dap(dct["frameId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        expression = self.expression
        frameId = self.frameId
        context = self.context
        format = self.format  # noqa (assign to builtin)
        if update_ids_to_dap:
            if frameId is not None:
                frameId = self._translate_id_to_dap(frameId)
        dct = {
            "expression": expression,
        }
        if frameId is not None:
            dct["frameId"] = frameId
        if context is not None:
            dct["context"] = context
        if format is not None:
            dct["format"] = format.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_to_dap(dct["frameId"])
        return dct


@register_response("evaluate")
@register
class EvaluateResponse(BaseSchema):
    """
    Response to `evaluate` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "The result of the evaluate request."},
                "type": {
                    "type": "string",
                    "description": "The type of the evaluate result.\nThis attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is True.",
                },
                "presentationHint": {
                    "$ref": "#/definitions/VariablePresentationHint",
                    "description": "Properties of an evaluate result that can be used to determine how to render the result in the UI.",
                },
                "variablesReference": {
                    "type": "integer",
                    "description": "If `variablesReference` is > 0, the evaluate result is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
                },
                "namedVariables": {
                    "type": "integer",
                    "description": "The number of named child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
                },
                "indexedVariables": {
                    "type": "integer",
                    "description": "The number of indexed child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
                },
                "memoryReference": {
                    "type": "string",
                    "description": "A memory reference to a location appropriate for this result.\nFor pointer type eval results, this is generally a reference to the memory address contained in the pointer.\nThis attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is True.",
                },
            },
            "required": ["result", "variablesReference"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param EvaluateResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = EvaluateResponseBody()
        else:
            self.body = (
                EvaluateResponseBody(update_ids_from_dap=update_ids_from_dap, **body) if body.__class__ != EvaluateResponseBody else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("setExpression")
@register
class SetExpressionRequest(BaseSchema):
    """
    Evaluates the given `value` expression and assigns it to the `expression` which must be a modifiable
    l-value.

    The expressions have access to any variables and arguments that are in scope of the specified frame.

    Clients should only call this request if the corresponding capability `supportsSetExpression` is
    true.

    If a debug adapter implements both `setExpression` and `setVariable`, a client uses `setExpression`
    if the variable has an `evaluateName` property.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setExpression"]},
        "arguments": {"type": "SetExpressionArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetExpressionArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setExpression"
        if arguments is None:
            self.arguments = SetExpressionArguments()
        else:
            self.arguments = (
                SetExpressionArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetExpressionArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetExpressionArguments(BaseSchema):
    """
    Arguments for `setExpression` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "expression": {"type": "string", "description": "The l-value expression to assign to."},
        "value": {"type": "string", "description": "The value expression to assign to the l-value expression."},
        "frameId": {
            "type": "integer",
            "description": "Evaluate the expressions in the scope of this stack frame. If not specified, the expressions are evaluated in the global scope.",
        },
        "format": {"description": "Specifies how the resulting value should be formatted.", "type": "ValueFormat"},
    }
    __refs__ = set(["format"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, expression, value, frameId=None, format=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string expression: The l-value expression to assign to.
        :param string value: The value expression to assign to the l-value expression.
        :param integer frameId: Evaluate the expressions in the scope of this stack frame. If not specified, the expressions are evaluated in the global scope.
        :param ValueFormat format: Specifies how the resulting value should be formatted.
        """
        self.expression = expression
        self.value = value
        self.frameId = frameId
        if format is None:
            self.format = ValueFormat()
        else:
            self.format = ValueFormat(update_ids_from_dap=update_ids_from_dap, **format) if format.__class__ != ValueFormat else format
        if update_ids_from_dap:
            self.frameId = self._translate_id_from_dap(self.frameId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_from_dap(dct["frameId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        expression = self.expression
        value = self.value
        frameId = self.frameId
        format = self.format  # noqa (assign to builtin)
        if update_ids_to_dap:
            if frameId is not None:
                frameId = self._translate_id_to_dap(frameId)
        dct = {
            "expression": expression,
            "value": value,
        }
        if frameId is not None:
            dct["frameId"] = frameId
        if format is not None:
            dct["format"] = format.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_to_dap(dct["frameId"])
        return dct


@register_response("setExpression")
@register
class SetExpressionResponse(BaseSchema):
    """
    Response to `setExpression` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "The new value of the expression."},
                "type": {
                    "type": "string",
                    "description": "The type of the value.\nThis attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is True.",
                },
                "presentationHint": {
                    "$ref": "#/definitions/VariablePresentationHint",
                    "description": "Properties of a value that can be used to determine how to render the result in the UI.",
                },
                "variablesReference": {
                    "type": "integer",
                    "description": "If `variablesReference` is > 0, the evaluate result is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
                },
                "namedVariables": {
                    "type": "integer",
                    "description": "The number of named child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
                },
                "indexedVariables": {
                    "type": "integer",
                    "description": "The number of indexed child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
                },
                "memoryReference": {
                    "type": "string",
                    "description": "A memory reference to a location appropriate for this result.\nFor pointer type eval results, this is generally a reference to the memory address contained in the pointer.\nThis attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is True.",
                },
            },
            "required": ["value"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param SetExpressionResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = SetExpressionResponseBody()
        else:
            self.body = (
                SetExpressionResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != SetExpressionResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("stepInTargets")
@register
class StepInTargetsRequest(BaseSchema):
    """
    This request retrieves the possible step-in targets for the specified stack frame.

    These targets can be used in the `stepIn` request.

    Clients should only call this request if the corresponding capability `supportsStepInTargetsRequest`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["stepInTargets"]},
        "arguments": {"type": "StepInTargetsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param StepInTargetsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "stepInTargets"
        if arguments is None:
            self.arguments = StepInTargetsArguments()
        else:
            self.arguments = (
                StepInTargetsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != StepInTargetsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class StepInTargetsArguments(BaseSchema):
    """
    Arguments for `stepInTargets` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"frameId": {"type": "integer", "description": "The stack frame for which to retrieve the possible step-in targets."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, frameId, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer frameId: The stack frame for which to retrieve the possible step-in targets.
        """
        self.frameId = frameId
        if update_ids_from_dap:
            self.frameId = self._translate_id_from_dap(self.frameId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_from_dap(dct["frameId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        frameId = self.frameId
        if update_ids_to_dap:
            if frameId is not None:
                frameId = self._translate_id_to_dap(frameId)
        dct = {
            "frameId": frameId,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_to_dap(dct["frameId"])
        return dct


@register_response("stepInTargets")
@register
class StepInTargetsResponse(BaseSchema):
    """
    Response to `stepInTargets` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "targets": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/StepInTarget"},
                    "description": "The possible step-in targets of the specified source location.",
                }
            },
            "required": ["targets"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param StepInTargetsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = StepInTargetsResponseBody()
        else:
            self.body = (
                StepInTargetsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != StepInTargetsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("gotoTargets")
@register
class GotoTargetsRequest(BaseSchema):
    """
    This request retrieves the possible goto targets for the specified source location.

    These targets can be used in the `goto` request.

    Clients should only call this request if the corresponding capability `supportsGotoTargetsRequest`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["gotoTargets"]},
        "arguments": {"type": "GotoTargetsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param GotoTargetsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "gotoTargets"
        if arguments is None:
            self.arguments = GotoTargetsArguments()
        else:
            self.arguments = (
                GotoTargetsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != GotoTargetsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class GotoTargetsArguments(BaseSchema):
    """
    Arguments for `gotoTargets` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "source": {"description": "The source location for which the goto targets are determined.", "type": "Source"},
        "line": {"type": "integer", "description": "The line location for which the goto targets are determined."},
        "column": {
            "type": "integer",
            "description": "The position within `line` for which the goto targets are determined. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, source, line, column=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param Source source: The source location for which the goto targets are determined.
        :param integer line: The line location for which the goto targets are determined.
        :param integer column: The position within `line` for which the goto targets are determined. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        """
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.line = line
        self.column = column
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        source = self.source
        line = self.line
        column = self.column
        dct = {
            "source": source.to_dict(update_ids_to_dap=update_ids_to_dap),
            "line": line,
        }
        if column is not None:
            dct["column"] = column
        dct.update(self.kwargs)
        return dct


@register_response("gotoTargets")
@register
class GotoTargetsResponse(BaseSchema):
    """
    Response to `gotoTargets` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "targets": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/GotoTarget"},
                    "description": "The possible goto targets of the specified location.",
                }
            },
            "required": ["targets"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param GotoTargetsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = GotoTargetsResponseBody()
        else:
            self.body = (
                GotoTargetsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != GotoTargetsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("completions")
@register
class CompletionsRequest(BaseSchema):
    """
    Returns a list of possible completions for a given caret position and text.

    Clients should only call this request if the corresponding capability `supportsCompletionsRequest`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["completions"]},
        "arguments": {"type": "CompletionsArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param CompletionsArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "completions"
        if arguments is None:
            self.arguments = CompletionsArguments()
        else:
            self.arguments = (
                CompletionsArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != CompletionsArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class CompletionsArguments(BaseSchema):
    """
    Arguments for `completions` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "frameId": {
            "type": "integer",
            "description": "Returns completions in the scope of this stack frame. If not specified, the completions are returned for the global scope.",
        },
        "text": {
            "type": "string",
            "description": "One or more source lines. Typically this is the text users have typed into the debug console before they asked for completion.",
        },
        "column": {
            "type": "integer",
            "description": "The position within `text` for which to determine the completion proposals. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "line": {
            "type": "integer",
            "description": "A line for which to determine the completion proposals. If missing the first line of the text is assumed.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, text, column, frameId=None, line=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string text: One or more source lines. Typically this is the text users have typed into the debug console before they asked for completion.
        :param integer column: The position within `text` for which to determine the completion proposals. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param integer frameId: Returns completions in the scope of this stack frame. If not specified, the completions are returned for the global scope.
        :param integer line: A line for which to determine the completion proposals. If missing the first line of the text is assumed.
        """
        self.text = text
        self.column = column
        self.frameId = frameId
        self.line = line
        if update_ids_from_dap:
            self.frameId = self._translate_id_from_dap(self.frameId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_from_dap(dct["frameId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        text = self.text
        column = self.column
        frameId = self.frameId
        line = self.line
        if update_ids_to_dap:
            if frameId is not None:
                frameId = self._translate_id_to_dap(frameId)
        dct = {
            "text": text,
            "column": column,
        }
        if frameId is not None:
            dct["frameId"] = frameId
        if line is not None:
            dct["line"] = line
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "frameId" in dct:
            dct["frameId"] = cls._translate_id_to_dap(dct["frameId"])
        return dct


@register_response("completions")
@register
class CompletionsResponse(BaseSchema):
    """
    Response to `completions` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "targets": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/CompletionItem"},
                    "description": "The possible completions for .",
                }
            },
            "required": ["targets"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param CompletionsResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = CompletionsResponseBody()
        else:
            self.body = (
                CompletionsResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != CompletionsResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("exceptionInfo")
@register
class ExceptionInfoRequest(BaseSchema):
    """
    Retrieves the details of the exception that caused this event to be raised.

    Clients should only call this request if the corresponding capability `supportsExceptionInfoRequest`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["exceptionInfo"]},
        "arguments": {"type": "ExceptionInfoArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param ExceptionInfoArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "exceptionInfo"
        if arguments is None:
            self.arguments = ExceptionInfoArguments()
        else:
            self.arguments = (
                ExceptionInfoArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != ExceptionInfoArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class ExceptionInfoArguments(BaseSchema):
    """
    Arguments for `exceptionInfo` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"threadId": {"type": "integer", "description": "Thread for which exception information should be retrieved."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: Thread for which exception information should be retrieved.
        """
        self.threadId = threadId
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register_response("exceptionInfo")
@register
class ExceptionInfoResponse(BaseSchema):
    """
    Response to `exceptionInfo` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "exceptionId": {"type": "string", "description": "ID of the exception that was thrown."},
                "description": {"type": "string", "description": "Descriptive text for the exception."},
                "breakMode": {
                    "$ref": "#/definitions/ExceptionBreakMode",
                    "description": "Mode that caused the exception notification to be raised.",
                },
                "details": {"$ref": "#/definitions/ExceptionDetails", "description": "Detailed information about the exception."},
            },
            "required": ["exceptionId", "breakMode"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param ExceptionInfoResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = ExceptionInfoResponseBody()
        else:
            self.body = (
                ExceptionInfoResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != ExceptionInfoResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register_request("readMemory")
@register
class ReadMemoryRequest(BaseSchema):
    """
    Reads bytes from memory at the provided location.

    Clients should only call this request if the corresponding capability `supportsReadMemoryRequest` is
    true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["readMemory"]},
        "arguments": {"type": "ReadMemoryArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param ReadMemoryArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "readMemory"
        if arguments is None:
            self.arguments = ReadMemoryArguments()
        else:
            self.arguments = (
                ReadMemoryArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != ReadMemoryArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class ReadMemoryArguments(BaseSchema):
    """
    Arguments for `readMemory` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "memoryReference": {"type": "string", "description": "Memory reference to the base location from which data should be read."},
        "offset": {
            "type": "integer",
            "description": "Offset (in bytes) to be applied to the reference location before reading data. Can be negative.",
        },
        "count": {"type": "integer", "description": "Number of bytes to read at the specified location and offset."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, memoryReference, count, offset=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string memoryReference: Memory reference to the base location from which data should be read.
        :param integer count: Number of bytes to read at the specified location and offset.
        :param integer offset: Offset (in bytes) to be applied to the reference location before reading data. Can be negative.
        """
        self.memoryReference = memoryReference
        self.count = count
        self.offset = offset
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        memoryReference = self.memoryReference
        count = self.count
        offset = self.offset
        dct = {
            "memoryReference": memoryReference,
            "count": count,
        }
        if offset is not None:
            dct["offset"] = offset
        dct.update(self.kwargs)
        return dct


@register_response("readMemory")
@register
class ReadMemoryResponse(BaseSchema):
    """
    Response to `readMemory` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "The address of the first byte of data returned.\nTreated as a hex value if prefixed with `0x`, or as a decimal value otherwise.",
                },
                "unreadableBytes": {
                    "type": "integer",
                    "description": "The number of unreadable bytes encountered after the last successfully read byte.\nThis can be used to determine the number of bytes that should be skipped before a subsequent `readMemory` request succeeds.",
                },
                "data": {
                    "type": "string",
                    "description": "The bytes read from memory, encoded using base64. If the decoded length of `data` is less than the requested `count` in the original `readMemory` request, and `unreadableBytes` is zero or omitted, then the client should assume it's reached the end of readable memory.",
                },
            },
            "required": ["address"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ReadMemoryResponseBody body:
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        if body is None:
            self.body = ReadMemoryResponseBody()
        else:
            self.body = (
                ReadMemoryResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != ReadMemoryResponseBody
                else body
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register_request("writeMemory")
@register
class WriteMemoryRequest(BaseSchema):
    """
    Writes bytes to memory at the provided location.

    Clients should only call this request if the corresponding capability `supportsWriteMemoryRequest`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["writeMemory"]},
        "arguments": {"type": "WriteMemoryArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param WriteMemoryArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "writeMemory"
        if arguments is None:
            self.arguments = WriteMemoryArguments()
        else:
            self.arguments = (
                WriteMemoryArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != WriteMemoryArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class WriteMemoryArguments(BaseSchema):
    """
    Arguments for `writeMemory` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "memoryReference": {"type": "string", "description": "Memory reference to the base location to which data should be written."},
        "offset": {
            "type": "integer",
            "description": "Offset (in bytes) to be applied to the reference location before writing data. Can be negative.",
        },
        "allowPartial": {
            "type": "boolean",
            "description": "Property to control partial writes. If True, the debug adapter should attempt to write memory even if the entire memory region is not writable. In such a case the debug adapter should stop after hitting the first byte of memory that cannot be written and return the number of bytes written in the response via the `offset` and `bytesWritten` properties.\nIf false or missing, a debug adapter should attempt to verify the region is writable before writing, and fail the response if it is not.",
        },
        "data": {"type": "string", "description": "Bytes to write, encoded using base64."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, memoryReference, data, offset=None, allowPartial=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string memoryReference: Memory reference to the base location to which data should be written.
        :param string data: Bytes to write, encoded using base64.
        :param integer offset: Offset (in bytes) to be applied to the reference location before writing data. Can be negative.
        :param boolean allowPartial: Property to control partial writes. If true, the debug adapter should attempt to write memory even if the entire memory region is not writable. In such a case the debug adapter should stop after hitting the first byte of memory that cannot be written and return the number of bytes written in the response via the `offset` and `bytesWritten` properties.
        If false or missing, a debug adapter should attempt to verify the region is writable before writing, and fail the response if it is not.
        """
        self.memoryReference = memoryReference
        self.data = data
        self.offset = offset
        self.allowPartial = allowPartial
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        memoryReference = self.memoryReference
        data = self.data
        offset = self.offset
        allowPartial = self.allowPartial
        dct = {
            "memoryReference": memoryReference,
            "data": data,
        }
        if offset is not None:
            dct["offset"] = offset
        if allowPartial is not None:
            dct["allowPartial"] = allowPartial
        dct.update(self.kwargs)
        return dct


@register_response("writeMemory")
@register
class WriteMemoryResponse(BaseSchema):
    """
    Response to `writeMemory` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "offset": {
                    "type": "integer",
                    "description": "Property that should be returned when `allowPartial` is True to indicate the offset of the first byte of data successfully written. Can be negative.",
                },
                "bytesWritten": {
                    "type": "integer",
                    "description": "Property that should be returned when `allowPartial` is True to indicate the number of bytes starting from address that were successfully written.",
                },
            },
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param WriteMemoryResponseBody body:
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        if body is None:
            self.body = WriteMemoryResponseBody()
        else:
            self.body = (
                WriteMemoryResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != WriteMemoryResponseBody
                else body
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register_request("disassemble")
@register
class DisassembleRequest(BaseSchema):
    """
    Disassembles code stored at the provided location.

    Clients should only call this request if the corresponding capability `supportsDisassembleRequest`
    is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["disassemble"]},
        "arguments": {"type": "DisassembleArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param DisassembleArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "disassemble"
        if arguments is None:
            self.arguments = DisassembleArguments()
        else:
            self.arguments = (
                DisassembleArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != DisassembleArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class DisassembleArguments(BaseSchema):
    """
    Arguments for `disassemble` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "memoryReference": {
            "type": "string",
            "description": "Memory reference to the base location containing the instructions to disassemble.",
        },
        "offset": {
            "type": "integer",
            "description": "Offset (in bytes) to be applied to the reference location before disassembling. Can be negative.",
        },
        "instructionOffset": {
            "type": "integer",
            "description": "Offset (in instructions) to be applied after the byte offset (if any) before disassembling. Can be negative.",
        },
        "instructionCount": {
            "type": "integer",
            "description": "Number of instructions to disassemble starting at the specified location and offset.\nAn adapter must return exactly this number of instructions - any unavailable instructions should be replaced with an implementation-defined 'invalid instruction' value.",
        },
        "resolveSymbols": {
            "type": "boolean",
            "description": "If True, the adapter should attempt to resolve memory addresses and other values to symbolic names.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        memoryReference,
        instructionCount,
        offset=None,
        instructionOffset=None,
        resolveSymbols=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string memoryReference: Memory reference to the base location containing the instructions to disassemble.
        :param integer instructionCount: Number of instructions to disassemble starting at the specified location and offset.
        An adapter must return exactly this number of instructions - any unavailable instructions should be replaced with an implementation-defined 'invalid instruction' value.
        :param integer offset: Offset (in bytes) to be applied to the reference location before disassembling. Can be negative.
        :param integer instructionOffset: Offset (in instructions) to be applied after the byte offset (if any) before disassembling. Can be negative.
        :param boolean resolveSymbols: If true, the adapter should attempt to resolve memory addresses and other values to symbolic names.
        """
        self.memoryReference = memoryReference
        self.instructionCount = instructionCount
        self.offset = offset
        self.instructionOffset = instructionOffset
        self.resolveSymbols = resolveSymbols
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        memoryReference = self.memoryReference
        instructionCount = self.instructionCount
        offset = self.offset
        instructionOffset = self.instructionOffset
        resolveSymbols = self.resolveSymbols
        dct = {
            "memoryReference": memoryReference,
            "instructionCount": instructionCount,
        }
        if offset is not None:
            dct["offset"] = offset
        if instructionOffset is not None:
            dct["instructionOffset"] = instructionOffset
        if resolveSymbols is not None:
            dct["resolveSymbols"] = resolveSymbols
        dct.update(self.kwargs)
        return dct


@register_response("disassemble")
@register
class DisassembleResponse(BaseSchema):
    """
    Response to `disassemble` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "instructions": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/DisassembledInstruction"},
                    "description": "The list of disassembled instructions.",
                }
            },
            "required": ["instructions"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param DisassembleResponseBody body:
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        if body is None:
            self.body = DisassembleResponseBody()
        else:
            self.body = (
                DisassembleResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != DisassembleResponseBody
                else body
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class Capabilities(BaseSchema):
    """
    Information about the capabilities of a debug adapter.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "supportsConfigurationDoneRequest": {
            "type": "boolean",
            "description": "The debug adapter supports the `configurationDone` request.",
        },
        "supportsFunctionBreakpoints": {"type": "boolean", "description": "The debug adapter supports function breakpoints."},
        "supportsConditionalBreakpoints": {"type": "boolean", "description": "The debug adapter supports conditional breakpoints."},
        "supportsHitConditionalBreakpoints": {
            "type": "boolean",
            "description": "The debug adapter supports breakpoints that break execution after a specified number of hits.",
        },
        "supportsEvaluateForHovers": {
            "type": "boolean",
            "description": "The debug adapter supports a (side effect free) `evaluate` request for data hovers.",
        },
        "exceptionBreakpointFilters": {
            "type": "array",
            "items": {"$ref": "#/definitions/ExceptionBreakpointsFilter"},
            "description": "Available exception filter options for the `setExceptionBreakpoints` request.",
        },
        "supportsStepBack": {
            "type": "boolean",
            "description": "The debug adapter supports stepping back via the `stepBack` and `reverseContinue` requests.",
        },
        "supportsSetVariable": {"type": "boolean", "description": "The debug adapter supports setting a variable to a value."},
        "supportsRestartFrame": {"type": "boolean", "description": "The debug adapter supports restarting a frame."},
        "supportsGotoTargetsRequest": {"type": "boolean", "description": "The debug adapter supports the `gotoTargets` request."},
        "supportsStepInTargetsRequest": {"type": "boolean", "description": "The debug adapter supports the `stepInTargets` request."},
        "supportsCompletionsRequest": {"type": "boolean", "description": "The debug adapter supports the `completions` request."},
        "completionTriggerCharacters": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The set of characters that should trigger completion in a REPL. If not specified, the UI should assume the `.` character.",
        },
        "supportsModulesRequest": {"type": "boolean", "description": "The debug adapter supports the `modules` request."},
        "additionalModuleColumns": {
            "type": "array",
            "items": {"$ref": "#/definitions/ColumnDescriptor"},
            "description": "The set of additional module information exposed by the debug adapter.",
        },
        "supportedChecksumAlgorithms": {
            "type": "array",
            "items": {"$ref": "#/definitions/ChecksumAlgorithm"},
            "description": "Checksum algorithms supported by the debug adapter.",
        },
        "supportsRestartRequest": {
            "type": "boolean",
            "description": "The debug adapter supports the `restart` request. In this case a client should not implement `restart` by terminating and relaunching the adapter but by calling the `restart` request.",
        },
        "supportsExceptionOptions": {
            "type": "boolean",
            "description": "The debug adapter supports `exceptionOptions` on the `setExceptionBreakpoints` request.",
        },
        "supportsValueFormattingOptions": {
            "type": "boolean",
            "description": "The debug adapter supports a `format` attribute on the `stackTrace`, `variables`, and `evaluate` requests.",
        },
        "supportsExceptionInfoRequest": {"type": "boolean", "description": "The debug adapter supports the `exceptionInfo` request."},
        "supportTerminateDebuggee": {
            "type": "boolean",
            "description": "The debug adapter supports the `terminateDebuggee` attribute on the `disconnect` request.",
        },
        "supportSuspendDebuggee": {
            "type": "boolean",
            "description": "The debug adapter supports the `suspendDebuggee` attribute on the `disconnect` request.",
        },
        "supportsDelayedStackTraceLoading": {
            "type": "boolean",
            "description": "The debug adapter supports the delayed loading of parts of the stack, which requires that both the `startFrame` and `levels` arguments and the `totalFrames` result of the `stackTrace` request are supported.",
        },
        "supportsLoadedSourcesRequest": {"type": "boolean", "description": "The debug adapter supports the `loadedSources` request."},
        "supportsLogPoints": {
            "type": "boolean",
            "description": "The debug adapter supports log points by interpreting the `logMessage` attribute of the `SourceBreakpoint`.",
        },
        "supportsTerminateThreadsRequest": {"type": "boolean", "description": "The debug adapter supports the `terminateThreads` request."},
        "supportsSetExpression": {"type": "boolean", "description": "The debug adapter supports the `setExpression` request."},
        "supportsTerminateRequest": {"type": "boolean", "description": "The debug adapter supports the `terminate` request."},
        "supportsDataBreakpoints": {"type": "boolean", "description": "The debug adapter supports data breakpoints."},
        "supportsReadMemoryRequest": {"type": "boolean", "description": "The debug adapter supports the `readMemory` request."},
        "supportsWriteMemoryRequest": {"type": "boolean", "description": "The debug adapter supports the `writeMemory` request."},
        "supportsDisassembleRequest": {"type": "boolean", "description": "The debug adapter supports the `disassemble` request."},
        "supportsCancelRequest": {"type": "boolean", "description": "The debug adapter supports the `cancel` request."},
        "supportsBreakpointLocationsRequest": {
            "type": "boolean",
            "description": "The debug adapter supports the `breakpointLocations` request.",
        },
        "supportsClipboardContext": {
            "type": "boolean",
            "description": "The debug adapter supports the `clipboard` context value in the `evaluate` request.",
        },
        "supportsSteppingGranularity": {
            "type": "boolean",
            "description": "The debug adapter supports stepping granularities (argument `granularity`) for the stepping requests.",
        },
        "supportsInstructionBreakpoints": {
            "type": "boolean",
            "description": "The debug adapter supports adding breakpoints based on instruction references.",
        },
        "supportsExceptionFilterOptions": {
            "type": "boolean",
            "description": "The debug adapter supports `filterOptions` as an argument on the `setExceptionBreakpoints` request.",
        },
        "supportsSingleThreadExecutionRequests": {
            "type": "boolean",
            "description": "The debug adapter supports the `singleThread` property on the execution requests (`continue`, `next`, `stepIn`, `stepOut`, `reverseContinue`, `stepBack`).",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        supportsConfigurationDoneRequest=None,
        supportsFunctionBreakpoints=None,
        supportsConditionalBreakpoints=None,
        supportsHitConditionalBreakpoints=None,
        supportsEvaluateForHovers=None,
        exceptionBreakpointFilters=None,
        supportsStepBack=None,
        supportsSetVariable=None,
        supportsRestartFrame=None,
        supportsGotoTargetsRequest=None,
        supportsStepInTargetsRequest=None,
        supportsCompletionsRequest=None,
        completionTriggerCharacters=None,
        supportsModulesRequest=None,
        additionalModuleColumns=None,
        supportedChecksumAlgorithms=None,
        supportsRestartRequest=None,
        supportsExceptionOptions=None,
        supportsValueFormattingOptions=None,
        supportsExceptionInfoRequest=None,
        supportTerminateDebuggee=None,
        supportSuspendDebuggee=None,
        supportsDelayedStackTraceLoading=None,
        supportsLoadedSourcesRequest=None,
        supportsLogPoints=None,
        supportsTerminateThreadsRequest=None,
        supportsSetExpression=None,
        supportsTerminateRequest=None,
        supportsDataBreakpoints=None,
        supportsReadMemoryRequest=None,
        supportsWriteMemoryRequest=None,
        supportsDisassembleRequest=None,
        supportsCancelRequest=None,
        supportsBreakpointLocationsRequest=None,
        supportsClipboardContext=None,
        supportsSteppingGranularity=None,
        supportsInstructionBreakpoints=None,
        supportsExceptionFilterOptions=None,
        supportsSingleThreadExecutionRequests=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean supportsConfigurationDoneRequest: The debug adapter supports the `configurationDone` request.
        :param boolean supportsFunctionBreakpoints: The debug adapter supports function breakpoints.
        :param boolean supportsConditionalBreakpoints: The debug adapter supports conditional breakpoints.
        :param boolean supportsHitConditionalBreakpoints: The debug adapter supports breakpoints that break execution after a specified number of hits.
        :param boolean supportsEvaluateForHovers: The debug adapter supports a (side effect free) `evaluate` request for data hovers.
        :param array exceptionBreakpointFilters: Available exception filter options for the `setExceptionBreakpoints` request.
        :param boolean supportsStepBack: The debug adapter supports stepping back via the `stepBack` and `reverseContinue` requests.
        :param boolean supportsSetVariable: The debug adapter supports setting a variable to a value.
        :param boolean supportsRestartFrame: The debug adapter supports restarting a frame.
        :param boolean supportsGotoTargetsRequest: The debug adapter supports the `gotoTargets` request.
        :param boolean supportsStepInTargetsRequest: The debug adapter supports the `stepInTargets` request.
        :param boolean supportsCompletionsRequest: The debug adapter supports the `completions` request.
        :param array completionTriggerCharacters: The set of characters that should trigger completion in a REPL. If not specified, the UI should assume the `.` character.
        :param boolean supportsModulesRequest: The debug adapter supports the `modules` request.
        :param array additionalModuleColumns: The set of additional module information exposed by the debug adapter.
        :param array supportedChecksumAlgorithms: Checksum algorithms supported by the debug adapter.
        :param boolean supportsRestartRequest: The debug adapter supports the `restart` request. In this case a client should not implement `restart` by terminating and relaunching the adapter but by calling the `restart` request.
        :param boolean supportsExceptionOptions: The debug adapter supports `exceptionOptions` on the `setExceptionBreakpoints` request.
        :param boolean supportsValueFormattingOptions: The debug adapter supports a `format` attribute on the `stackTrace`, `variables`, and `evaluate` requests.
        :param boolean supportsExceptionInfoRequest: The debug adapter supports the `exceptionInfo` request.
        :param boolean supportTerminateDebuggee: The debug adapter supports the `terminateDebuggee` attribute on the `disconnect` request.
        :param boolean supportSuspendDebuggee: The debug adapter supports the `suspendDebuggee` attribute on the `disconnect` request.
        :param boolean supportsDelayedStackTraceLoading: The debug adapter supports the delayed loading of parts of the stack, which requires that both the `startFrame` and `levels` arguments and the `totalFrames` result of the `stackTrace` request are supported.
        :param boolean supportsLoadedSourcesRequest: The debug adapter supports the `loadedSources` request.
        :param boolean supportsLogPoints: The debug adapter supports log points by interpreting the `logMessage` attribute of the `SourceBreakpoint`.
        :param boolean supportsTerminateThreadsRequest: The debug adapter supports the `terminateThreads` request.
        :param boolean supportsSetExpression: The debug adapter supports the `setExpression` request.
        :param boolean supportsTerminateRequest: The debug adapter supports the `terminate` request.
        :param boolean supportsDataBreakpoints: The debug adapter supports data breakpoints.
        :param boolean supportsReadMemoryRequest: The debug adapter supports the `readMemory` request.
        :param boolean supportsWriteMemoryRequest: The debug adapter supports the `writeMemory` request.
        :param boolean supportsDisassembleRequest: The debug adapter supports the `disassemble` request.
        :param boolean supportsCancelRequest: The debug adapter supports the `cancel` request.
        :param boolean supportsBreakpointLocationsRequest: The debug adapter supports the `breakpointLocations` request.
        :param boolean supportsClipboardContext: The debug adapter supports the `clipboard` context value in the `evaluate` request.
        :param boolean supportsSteppingGranularity: The debug adapter supports stepping granularities (argument `granularity`) for the stepping requests.
        :param boolean supportsInstructionBreakpoints: The debug adapter supports adding breakpoints based on instruction references.
        :param boolean supportsExceptionFilterOptions: The debug adapter supports `filterOptions` as an argument on the `setExceptionBreakpoints` request.
        :param boolean supportsSingleThreadExecutionRequests: The debug adapter supports the `singleThread` property on the execution requests (`continue`, `next`, `stepIn`, `stepOut`, `reverseContinue`, `stepBack`).
        """
        self.supportsConfigurationDoneRequest = supportsConfigurationDoneRequest
        self.supportsFunctionBreakpoints = supportsFunctionBreakpoints
        self.supportsConditionalBreakpoints = supportsConditionalBreakpoints
        self.supportsHitConditionalBreakpoints = supportsHitConditionalBreakpoints
        self.supportsEvaluateForHovers = supportsEvaluateForHovers
        self.exceptionBreakpointFilters = exceptionBreakpointFilters
        if update_ids_from_dap and self.exceptionBreakpointFilters:
            for o in self.exceptionBreakpointFilters:
                ExceptionBreakpointsFilter.update_dict_ids_from_dap(o)
        self.supportsStepBack = supportsStepBack
        self.supportsSetVariable = supportsSetVariable
        self.supportsRestartFrame = supportsRestartFrame
        self.supportsGotoTargetsRequest = supportsGotoTargetsRequest
        self.supportsStepInTargetsRequest = supportsStepInTargetsRequest
        self.supportsCompletionsRequest = supportsCompletionsRequest
        self.completionTriggerCharacters = completionTriggerCharacters
        self.supportsModulesRequest = supportsModulesRequest
        self.additionalModuleColumns = additionalModuleColumns
        if update_ids_from_dap and self.additionalModuleColumns:
            for o in self.additionalModuleColumns:
                ColumnDescriptor.update_dict_ids_from_dap(o)
        self.supportedChecksumAlgorithms = supportedChecksumAlgorithms
        if update_ids_from_dap and self.supportedChecksumAlgorithms:
            for o in self.supportedChecksumAlgorithms:
                ChecksumAlgorithm.update_dict_ids_from_dap(o)
        self.supportsRestartRequest = supportsRestartRequest
        self.supportsExceptionOptions = supportsExceptionOptions
        self.supportsValueFormattingOptions = supportsValueFormattingOptions
        self.supportsExceptionInfoRequest = supportsExceptionInfoRequest
        self.supportTerminateDebuggee = supportTerminateDebuggee
        self.supportSuspendDebuggee = supportSuspendDebuggee
        self.supportsDelayedStackTraceLoading = supportsDelayedStackTraceLoading
        self.supportsLoadedSourcesRequest = supportsLoadedSourcesRequest
        self.supportsLogPoints = supportsLogPoints
        self.supportsTerminateThreadsRequest = supportsTerminateThreadsRequest
        self.supportsSetExpression = supportsSetExpression
        self.supportsTerminateRequest = supportsTerminateRequest
        self.supportsDataBreakpoints = supportsDataBreakpoints
        self.supportsReadMemoryRequest = supportsReadMemoryRequest
        self.supportsWriteMemoryRequest = supportsWriteMemoryRequest
        self.supportsDisassembleRequest = supportsDisassembleRequest
        self.supportsCancelRequest = supportsCancelRequest
        self.supportsBreakpointLocationsRequest = supportsBreakpointLocationsRequest
        self.supportsClipboardContext = supportsClipboardContext
        self.supportsSteppingGranularity = supportsSteppingGranularity
        self.supportsInstructionBreakpoints = supportsInstructionBreakpoints
        self.supportsExceptionFilterOptions = supportsExceptionFilterOptions
        self.supportsSingleThreadExecutionRequests = supportsSingleThreadExecutionRequests
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        supportsConfigurationDoneRequest = self.supportsConfigurationDoneRequest
        supportsFunctionBreakpoints = self.supportsFunctionBreakpoints
        supportsConditionalBreakpoints = self.supportsConditionalBreakpoints
        supportsHitConditionalBreakpoints = self.supportsHitConditionalBreakpoints
        supportsEvaluateForHovers = self.supportsEvaluateForHovers
        exceptionBreakpointFilters = self.exceptionBreakpointFilters
        if exceptionBreakpointFilters and hasattr(exceptionBreakpointFilters[0], "to_dict"):
            exceptionBreakpointFilters = [x.to_dict() for x in exceptionBreakpointFilters]
        supportsStepBack = self.supportsStepBack
        supportsSetVariable = self.supportsSetVariable
        supportsRestartFrame = self.supportsRestartFrame
        supportsGotoTargetsRequest = self.supportsGotoTargetsRequest
        supportsStepInTargetsRequest = self.supportsStepInTargetsRequest
        supportsCompletionsRequest = self.supportsCompletionsRequest
        completionTriggerCharacters = self.completionTriggerCharacters
        if completionTriggerCharacters and hasattr(completionTriggerCharacters[0], "to_dict"):
            completionTriggerCharacters = [x.to_dict() for x in completionTriggerCharacters]
        supportsModulesRequest = self.supportsModulesRequest
        additionalModuleColumns = self.additionalModuleColumns
        if additionalModuleColumns and hasattr(additionalModuleColumns[0], "to_dict"):
            additionalModuleColumns = [x.to_dict() for x in additionalModuleColumns]
        supportedChecksumAlgorithms = self.supportedChecksumAlgorithms
        if supportedChecksumAlgorithms and hasattr(supportedChecksumAlgorithms[0], "to_dict"):
            supportedChecksumAlgorithms = [x.to_dict() for x in supportedChecksumAlgorithms]
        supportsRestartRequest = self.supportsRestartRequest
        supportsExceptionOptions = self.supportsExceptionOptions
        supportsValueFormattingOptions = self.supportsValueFormattingOptions
        supportsExceptionInfoRequest = self.supportsExceptionInfoRequest
        supportTerminateDebuggee = self.supportTerminateDebuggee
        supportSuspendDebuggee = self.supportSuspendDebuggee
        supportsDelayedStackTraceLoading = self.supportsDelayedStackTraceLoading
        supportsLoadedSourcesRequest = self.supportsLoadedSourcesRequest
        supportsLogPoints = self.supportsLogPoints
        supportsTerminateThreadsRequest = self.supportsTerminateThreadsRequest
        supportsSetExpression = self.supportsSetExpression
        supportsTerminateRequest = self.supportsTerminateRequest
        supportsDataBreakpoints = self.supportsDataBreakpoints
        supportsReadMemoryRequest = self.supportsReadMemoryRequest
        supportsWriteMemoryRequest = self.supportsWriteMemoryRequest
        supportsDisassembleRequest = self.supportsDisassembleRequest
        supportsCancelRequest = self.supportsCancelRequest
        supportsBreakpointLocationsRequest = self.supportsBreakpointLocationsRequest
        supportsClipboardContext = self.supportsClipboardContext
        supportsSteppingGranularity = self.supportsSteppingGranularity
        supportsInstructionBreakpoints = self.supportsInstructionBreakpoints
        supportsExceptionFilterOptions = self.supportsExceptionFilterOptions
        supportsSingleThreadExecutionRequests = self.supportsSingleThreadExecutionRequests
        dct = {}
        if supportsConfigurationDoneRequest is not None:
            dct["supportsConfigurationDoneRequest"] = supportsConfigurationDoneRequest
        if supportsFunctionBreakpoints is not None:
            dct["supportsFunctionBreakpoints"] = supportsFunctionBreakpoints
        if supportsConditionalBreakpoints is not None:
            dct["supportsConditionalBreakpoints"] = supportsConditionalBreakpoints
        if supportsHitConditionalBreakpoints is not None:
            dct["supportsHitConditionalBreakpoints"] = supportsHitConditionalBreakpoints
        if supportsEvaluateForHovers is not None:
            dct["supportsEvaluateForHovers"] = supportsEvaluateForHovers
        if exceptionBreakpointFilters is not None:
            dct["exceptionBreakpointFilters"] = (
                [ExceptionBreakpointsFilter.update_dict_ids_to_dap(o) for o in exceptionBreakpointFilters]
                if (update_ids_to_dap and exceptionBreakpointFilters)
                else exceptionBreakpointFilters
            )
        if supportsStepBack is not None:
            dct["supportsStepBack"] = supportsStepBack
        if supportsSetVariable is not None:
            dct["supportsSetVariable"] = supportsSetVariable
        if supportsRestartFrame is not None:
            dct["supportsRestartFrame"] = supportsRestartFrame
        if supportsGotoTargetsRequest is not None:
            dct["supportsGotoTargetsRequest"] = supportsGotoTargetsRequest
        if supportsStepInTargetsRequest is not None:
            dct["supportsStepInTargetsRequest"] = supportsStepInTargetsRequest
        if supportsCompletionsRequest is not None:
            dct["supportsCompletionsRequest"] = supportsCompletionsRequest
        if completionTriggerCharacters is not None:
            dct["completionTriggerCharacters"] = completionTriggerCharacters
        if supportsModulesRequest is not None:
            dct["supportsModulesRequest"] = supportsModulesRequest
        if additionalModuleColumns is not None:
            dct["additionalModuleColumns"] = (
                [ColumnDescriptor.update_dict_ids_to_dap(o) for o in additionalModuleColumns]
                if (update_ids_to_dap and additionalModuleColumns)
                else additionalModuleColumns
            )
        if supportedChecksumAlgorithms is not None:
            dct["supportedChecksumAlgorithms"] = (
                [ChecksumAlgorithm.update_dict_ids_to_dap(o) for o in supportedChecksumAlgorithms]
                if (update_ids_to_dap and supportedChecksumAlgorithms)
                else supportedChecksumAlgorithms
            )
        if supportsRestartRequest is not None:
            dct["supportsRestartRequest"] = supportsRestartRequest
        if supportsExceptionOptions is not None:
            dct["supportsExceptionOptions"] = supportsExceptionOptions
        if supportsValueFormattingOptions is not None:
            dct["supportsValueFormattingOptions"] = supportsValueFormattingOptions
        if supportsExceptionInfoRequest is not None:
            dct["supportsExceptionInfoRequest"] = supportsExceptionInfoRequest
        if supportTerminateDebuggee is not None:
            dct["supportTerminateDebuggee"] = supportTerminateDebuggee
        if supportSuspendDebuggee is not None:
            dct["supportSuspendDebuggee"] = supportSuspendDebuggee
        if supportsDelayedStackTraceLoading is not None:
            dct["supportsDelayedStackTraceLoading"] = supportsDelayedStackTraceLoading
        if supportsLoadedSourcesRequest is not None:
            dct["supportsLoadedSourcesRequest"] = supportsLoadedSourcesRequest
        if supportsLogPoints is not None:
            dct["supportsLogPoints"] = supportsLogPoints
        if supportsTerminateThreadsRequest is not None:
            dct["supportsTerminateThreadsRequest"] = supportsTerminateThreadsRequest
        if supportsSetExpression is not None:
            dct["supportsSetExpression"] = supportsSetExpression
        if supportsTerminateRequest is not None:
            dct["supportsTerminateRequest"] = supportsTerminateRequest
        if supportsDataBreakpoints is not None:
            dct["supportsDataBreakpoints"] = supportsDataBreakpoints
        if supportsReadMemoryRequest is not None:
            dct["supportsReadMemoryRequest"] = supportsReadMemoryRequest
        if supportsWriteMemoryRequest is not None:
            dct["supportsWriteMemoryRequest"] = supportsWriteMemoryRequest
        if supportsDisassembleRequest is not None:
            dct["supportsDisassembleRequest"] = supportsDisassembleRequest
        if supportsCancelRequest is not None:
            dct["supportsCancelRequest"] = supportsCancelRequest
        if supportsBreakpointLocationsRequest is not None:
            dct["supportsBreakpointLocationsRequest"] = supportsBreakpointLocationsRequest
        if supportsClipboardContext is not None:
            dct["supportsClipboardContext"] = supportsClipboardContext
        if supportsSteppingGranularity is not None:
            dct["supportsSteppingGranularity"] = supportsSteppingGranularity
        if supportsInstructionBreakpoints is not None:
            dct["supportsInstructionBreakpoints"] = supportsInstructionBreakpoints
        if supportsExceptionFilterOptions is not None:
            dct["supportsExceptionFilterOptions"] = supportsExceptionFilterOptions
        if supportsSingleThreadExecutionRequests is not None:
            dct["supportsSingleThreadExecutionRequests"] = supportsSingleThreadExecutionRequests
        dct.update(self.kwargs)
        return dct


@register
class ExceptionBreakpointsFilter(BaseSchema):
    """
    An `ExceptionBreakpointsFilter` is shown in the UI as an filter option for configuring how
    exceptions are dealt with.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "filter": {
            "type": "string",
            "description": "The internal ID of the filter option. This value is passed to the `setExceptionBreakpoints` request.",
        },
        "label": {"type": "string", "description": "The name of the filter option. This is shown in the UI."},
        "description": {
            "type": "string",
            "description": "A help text providing additional information about the exception filter. This string is typically shown as a hover and can be translated.",
        },
        "default": {"type": "boolean", "description": "Initial value of the filter option. If not specified a value false is assumed."},
        "supportsCondition": {
            "type": "boolean",
            "description": "Controls whether a condition can be specified for this filter option. If false or missing, a condition can not be set.",
        },
        "conditionDescription": {
            "type": "string",
            "description": "A help text providing information about the condition. This string is shown as the placeholder text for a text box and can be translated.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        filter,
        label,
        description=None,
        default=None,
        supportsCondition=None,
        conditionDescription=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string filter: The internal ID of the filter option. This value is passed to the `setExceptionBreakpoints` request.
        :param string label: The name of the filter option. This is shown in the UI.
        :param string description: A help text providing additional information about the exception filter. This string is typically shown as a hover and can be translated.
        :param boolean default: Initial value of the filter option. If not specified a value false is assumed.
        :param boolean supportsCondition: Controls whether a condition can be specified for this filter option. If false or missing, a condition can not be set.
        :param string conditionDescription: A help text providing information about the condition. This string is shown as the placeholder text for a text box and can be translated.
        """
        self.filter = filter
        self.label = label
        self.description = description
        self.default = default
        self.supportsCondition = supportsCondition
        self.conditionDescription = conditionDescription
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        filter = self.filter  # noqa (assign to builtin)
        label = self.label
        description = self.description
        default = self.default
        supportsCondition = self.supportsCondition
        conditionDescription = self.conditionDescription
        dct = {
            "filter": filter,
            "label": label,
        }
        if description is not None:
            dct["description"] = description
        if default is not None:
            dct["default"] = default
        if supportsCondition is not None:
            dct["supportsCondition"] = supportsCondition
        if conditionDescription is not None:
            dct["conditionDescription"] = conditionDescription
        dct.update(self.kwargs)
        return dct


@register
class Message(BaseSchema):
    """
    A structured message object. Used to return errors from requests.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "id": {
            "type": "integer",
            "description": "Unique (within a debug adapter implementation) identifier for the message. The purpose of these error IDs is to help extension authors that have the requirement that every user visible error message needs a corresponding error number, so that users or customer support can find information about the specific error more easily.",
        },
        "format": {
            "type": "string",
            "description": "A format string for the message. Embedded variables have the form `{name}`.\nIf variable name starts with an underscore character, the variable does not contain user data (PII) and can be safely used for telemetry purposes.",
        },
        "variables": {
            "type": "object",
            "description": "An object used as a dictionary for looking up the variables in the format string.",
            "additionalProperties": {"type": "string", "description": "All dictionary values must be strings."},
        },
        "sendTelemetry": {"type": "boolean", "description": "If True send to telemetry."},
        "showUser": {"type": "boolean", "description": "If True show user."},
        "url": {"type": "string", "description": "A url where additional information about this message can be found."},
        "urlLabel": {"type": "string", "description": "A label that is presented to the user as the UI for opening the url."},
    }
    __refs__ = set(["variables"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self, id, format, variables=None, sendTelemetry=None, showUser=None, url=None, urlLabel=None, update_ids_from_dap=False, **kwargs
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer id: Unique (within a debug adapter implementation) identifier for the message. The purpose of these error IDs is to help extension authors that have the requirement that every user visible error message needs a corresponding error number, so that users or customer support can find information about the specific error more easily.
        :param string format: A format string for the message. Embedded variables have the form `{name}`.
        If variable name starts with an underscore character, the variable does not contain user data (PII) and can be safely used for telemetry purposes.
        :param MessageVariables variables: An object used as a dictionary for looking up the variables in the format string.
        :param boolean sendTelemetry: If true send to telemetry.
        :param boolean showUser: If true show user.
        :param string url: A url where additional information about this message can be found.
        :param string urlLabel: A label that is presented to the user as the UI for opening the url.
        """
        self.id = id
        self.format = format
        if variables is None:
            self.variables = MessageVariables()
        else:
            self.variables = (
                MessageVariables(update_ids_from_dap=update_ids_from_dap, **variables)
                if variables.__class__ != MessageVariables
                else variables
            )
        self.sendTelemetry = sendTelemetry
        self.showUser = showUser
        self.url = url
        self.urlLabel = urlLabel
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        id = self.id  # noqa (assign to builtin)
        format = self.format  # noqa (assign to builtin)
        variables = self.variables
        sendTelemetry = self.sendTelemetry
        showUser = self.showUser
        url = self.url
        urlLabel = self.urlLabel
        dct = {
            "id": id,
            "format": format,
        }
        if variables is not None:
            dct["variables"] = variables.to_dict(update_ids_to_dap=update_ids_to_dap)
        if sendTelemetry is not None:
            dct["sendTelemetry"] = sendTelemetry
        if showUser is not None:
            dct["showUser"] = showUser
        if url is not None:
            dct["url"] = url
        if urlLabel is not None:
            dct["urlLabel"] = urlLabel
        dct.update(self.kwargs)
        return dct


@register
class Module(BaseSchema):
    """
    A Module object represents a row in the modules view.

    The `id` attribute identifies a module in the modules view and is used in a `module` event for
    identifying a module for adding, updating or deleting.

    The `name` attribute is used to minimally render the module in the UI.


    Additional attributes can be added to the module. They show up in the module view if they have a
    corresponding `ColumnDescriptor`.


    To avoid an unnecessary proliferation of additional attributes with similar semantics but different
    names, we recommend to re-use attributes from the 'recommended' list below first, and only introduce
    new attributes if nothing appropriate could be found.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "id": {"type": ["integer", "string"], "description": "Unique identifier for the module."},
        "name": {"type": "string", "description": "A name of the module."},
        "path": {
            "type": "string",
            "description": "Logical full path to the module. The exact definition is implementation defined, but usually this would be a full path to the on-disk file for the module.",
        },
        "isOptimized": {"type": "boolean", "description": "True if the module is optimized."},
        "isUserCode": {
            "type": "boolean",
            "description": "True if the module is considered 'user code' by a debugger that supports 'Just My Code'.",
        },
        "version": {"type": "string", "description": "Version of Module."},
        "symbolStatus": {
            "type": "string",
            "description": "User-understandable description of if symbols were found for the module (ex: 'Symbols Loaded', 'Symbols not found', etc.)",
        },
        "symbolFilePath": {
            "type": "string",
            "description": "Logical full path to the symbol file. The exact definition is implementation defined.",
        },
        "dateTimeStamp": {"type": "string", "description": "Module created or modified, encoded as a RFC 3339 timestamp."},
        "addressRange": {"type": "string", "description": "Address range covered by this module."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        id,
        name,
        path=None,
        isOptimized=None,
        isUserCode=None,
        version=None,
        symbolStatus=None,
        symbolFilePath=None,
        dateTimeStamp=None,
        addressRange=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param ['integer', 'string'] id: Unique identifier for the module.
        :param string name: A name of the module.
        :param string path: Logical full path to the module. The exact definition is implementation defined, but usually this would be a full path to the on-disk file for the module.
        :param boolean isOptimized: True if the module is optimized.
        :param boolean isUserCode: True if the module is considered 'user code' by a debugger that supports 'Just My Code'.
        :param string version: Version of Module.
        :param string symbolStatus: User-understandable description of if symbols were found for the module (ex: 'Symbols Loaded', 'Symbols not found', etc.)
        :param string symbolFilePath: Logical full path to the symbol file. The exact definition is implementation defined.
        :param string dateTimeStamp: Module created or modified, encoded as a RFC 3339 timestamp.
        :param string addressRange: Address range covered by this module.
        """
        self.id = id
        self.name = name
        self.path = path
        self.isOptimized = isOptimized
        self.isUserCode = isUserCode
        self.version = version
        self.symbolStatus = symbolStatus
        self.symbolFilePath = symbolFilePath
        self.dateTimeStamp = dateTimeStamp
        self.addressRange = addressRange
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        id = self.id  # noqa (assign to builtin)
        name = self.name
        path = self.path
        isOptimized = self.isOptimized
        isUserCode = self.isUserCode
        version = self.version
        symbolStatus = self.symbolStatus
        symbolFilePath = self.symbolFilePath
        dateTimeStamp = self.dateTimeStamp
        addressRange = self.addressRange
        dct = {
            "id": id,
            "name": name,
        }
        if path is not None:
            dct["path"] = path
        if isOptimized is not None:
            dct["isOptimized"] = isOptimized
        if isUserCode is not None:
            dct["isUserCode"] = isUserCode
        if version is not None:
            dct["version"] = version
        if symbolStatus is not None:
            dct["symbolStatus"] = symbolStatus
        if symbolFilePath is not None:
            dct["symbolFilePath"] = symbolFilePath
        if dateTimeStamp is not None:
            dct["dateTimeStamp"] = dateTimeStamp
        if addressRange is not None:
            dct["addressRange"] = addressRange
        dct.update(self.kwargs)
        return dct


@register
class ColumnDescriptor(BaseSchema):
    """
    A `ColumnDescriptor` specifies what module attribute to show in a column of the modules view, how to
    format it,

    and what the column's label should be.

    It is only used if the underlying UI actually supports this level of customization.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "attributeName": {"type": "string", "description": "Name of the attribute rendered in this column."},
        "label": {"type": "string", "description": "Header UI label of column."},
        "format": {
            "type": "string",
            "description": "Format to use for the rendered values in this column. TBD how the format strings looks like.",
        },
        "type": {
            "type": "string",
            "enum": ["string", "number", "boolean", "unixTimestampUTC"],
            "description": "Datatype of values in this column. Defaults to `string` if not specified.",
        },
        "width": {"type": "integer", "description": "Width of this column in characters (hint only)."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, attributeName, label, format=None, type=None, width=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string attributeName: Name of the attribute rendered in this column.
        :param string label: Header UI label of column.
        :param string format: Format to use for the rendered values in this column. TBD how the format strings looks like.
        :param string type: Datatype of values in this column. Defaults to `string` if not specified.
        :param integer width: Width of this column in characters (hint only).
        """
        self.attributeName = attributeName
        self.label = label
        self.format = format
        self.type = type
        self.width = width
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        attributeName = self.attributeName
        label = self.label
        format = self.format  # noqa (assign to builtin)
        type = self.type  # noqa (assign to builtin)
        width = self.width
        dct = {
            "attributeName": attributeName,
            "label": label,
        }
        if format is not None:
            dct["format"] = format
        if type is not None:
            dct["type"] = type
        if width is not None:
            dct["width"] = width
        dct.update(self.kwargs)
        return dct


@register
class Thread(BaseSchema):
    """
    A Thread

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "id": {"type": "integer", "description": "Unique identifier for the thread."},
        "name": {"type": "string", "description": "The name of the thread."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, id, name, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer id: Unique identifier for the thread.
        :param string name: The name of the thread.
        """
        self.id = id
        self.name = name
        if update_ids_from_dap:
            self.id = self._translate_id_from_dap(self.id)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "id" in dct:
            dct["id"] = cls._translate_id_from_dap(dct["id"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        id = self.id  # noqa (assign to builtin)
        name = self.name
        if update_ids_to_dap:
            if id is not None:
                id = self._translate_id_to_dap(id)  # noqa (assign to builtin)
        dct = {
            "id": id,
            "name": name,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "id" in dct:
            dct["id"] = cls._translate_id_to_dap(dct["id"])
        return dct


@register
class Source(BaseSchema):
    """
    A `Source` is a descriptor for source code.

    It is returned from the debug adapter as part of a `StackFrame` and it is used by clients when
    specifying breakpoints.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "name": {
            "type": "string",
            "description": "The short name of the source. Every source returned from the debug adapter has a name.\nWhen sending a source to the debug adapter this name is optional.",
        },
        "path": {
            "type": "string",
            "description": "The path of the source to be shown in the UI.\nIt is only used to locate and load the content of the source if no `sourceReference` is specified (or its value is 0).",
        },
        "sourceReference": {
            "type": "integer",
            "description": "If the value > 0 the contents of the source must be retrieved through the `source` request (even if a path is specified).\nSince a `sourceReference` is only valid for a session, it can not be used to persist a source.\nThe value should be less than or equal to 2147483647 (2^31-1).",
        },
        "presentationHint": {
            "type": "string",
            "description": "A hint for how to present the source in the UI.\nA value of `deemphasize` can be used to indicate that the source is not available or that it is skipped on stepping.",
            "enum": ["normal", "emphasize", "deemphasize"],
        },
        "origin": {
            "type": "string",
            "description": "The origin of this source. For example, 'internal module', 'inlined content from source map', etc.",
        },
        "sources": {
            "type": "array",
            "items": {"$ref": "#/definitions/Source"},
            "description": "A list of sources that are related to this source. These may be the source that generated this source.",
        },
        "adapterData": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Additional data that a debug adapter might want to loop through the client.\nThe client should leave the data intact and persist it across sessions. The client should not interpret the data.",
        },
        "checksums": {
            "type": "array",
            "items": {"$ref": "#/definitions/Checksum"},
            "description": "The checksums associated with this file.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        name=None,
        path=None,
        sourceReference=None,
        presentationHint=None,
        origin=None,
        sources=None,
        adapterData=None,
        checksums=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: The short name of the source. Every source returned from the debug adapter has a name.
        When sending a source to the debug adapter this name is optional.
        :param string path: The path of the source to be shown in the UI.
        It is only used to locate and load the content of the source if no `sourceReference` is specified (or its value is 0).
        :param integer sourceReference: If the value > 0 the contents of the source must be retrieved through the `source` request (even if a path is specified).
        Since a `sourceReference` is only valid for a session, it can not be used to persist a source.
        The value should be less than or equal to 2147483647 (2^31-1).
        :param string presentationHint: A hint for how to present the source in the UI.
        A value of `deemphasize` can be used to indicate that the source is not available or that it is skipped on stepping.
        :param string origin: The origin of this source. For example, 'internal module', 'inlined content from source map', etc.
        :param array sources: A list of sources that are related to this source. These may be the source that generated this source.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] adapterData: Additional data that a debug adapter might want to loop through the client.
        The client should leave the data intact and persist it across sessions. The client should not interpret the data.
        :param array checksums: The checksums associated with this file.
        """
        self.name = name
        self.path = path
        self.sourceReference = sourceReference
        self.presentationHint = presentationHint
        self.origin = origin
        self.sources = sources
        if update_ids_from_dap and self.sources:
            for o in self.sources:
                Source.update_dict_ids_from_dap(o)
        self.adapterData = adapterData
        self.checksums = checksums
        if update_ids_from_dap and self.checksums:
            for o in self.checksums:
                Checksum.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        path = self.path
        sourceReference = self.sourceReference
        presentationHint = self.presentationHint
        origin = self.origin
        sources = self.sources
        if sources and hasattr(sources[0], "to_dict"):
            sources = [x.to_dict() for x in sources]
        adapterData = self.adapterData
        checksums = self.checksums
        if checksums and hasattr(checksums[0], "to_dict"):
            checksums = [x.to_dict() for x in checksums]
        dct = {}
        if name is not None:
            dct["name"] = name
        if path is not None:
            dct["path"] = path
        if sourceReference is not None:
            dct["sourceReference"] = sourceReference
        if presentationHint is not None:
            dct["presentationHint"] = presentationHint
        if origin is not None:
            dct["origin"] = origin
        if sources is not None:
            dct["sources"] = [Source.update_dict_ids_to_dap(o) for o in sources] if (update_ids_to_dap and sources) else sources
        if adapterData is not None:
            dct["adapterData"] = adapterData
        if checksums is not None:
            dct["checksums"] = [Checksum.update_dict_ids_to_dap(o) for o in checksums] if (update_ids_to_dap and checksums) else checksums
        dct.update(self.kwargs)
        return dct


@register
class StackFrame(BaseSchema):
    """
    A Stackframe contains the source location.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "id": {
            "type": "integer",
            "description": "An identifier for the stack frame. It must be unique across all threads.\nThis id can be used to retrieve the scopes of the frame with the `scopes` request or to restart the execution of a stack frame.",
        },
        "name": {"type": "string", "description": "The name of the stack frame, typically a method name."},
        "source": {"description": "The source of the frame.", "type": "Source"},
        "line": {
            "type": "integer",
            "description": "The line within the source of the frame. If the source attribute is missing or doesn't exist, `line` is 0 and should be ignored by the client.",
        },
        "column": {
            "type": "integer",
            "description": "Start position of the range covered by the stack frame. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If attribute `source` is missing or doesn't exist, `column` is 0 and should be ignored by the client.",
        },
        "endLine": {"type": "integer", "description": "The end line of the range covered by the stack frame."},
        "endColumn": {
            "type": "integer",
            "description": "End position of the range covered by the stack frame. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "canRestart": {
            "type": "boolean",
            "description": "Indicates whether this frame can be restarted with the `restart` request. Clients should only use this if the debug adapter supports the `restart` request and the corresponding capability `supportsRestartRequest` is True. If a debug adapter has this capability, then `canRestart` defaults to `True` if the property is absent.",
        },
        "instructionPointerReference": {
            "type": "string",
            "description": "A memory reference for the current instruction pointer in this frame.",
        },
        "moduleId": {"type": ["integer", "string"], "description": "The module associated with this frame, if any."},
        "presentationHint": {
            "type": "string",
            "enum": ["normal", "label", "subtle"],
            "description": "A hint for how to present this frame in the UI.\nA value of `label` can be used to indicate that the frame is an artificial frame that is used as a visual label or separator. A value of `subtle` can be used to change the appearance of a frame in a 'subtle' way.",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        id,
        name,
        line,
        column,
        source=None,
        endLine=None,
        endColumn=None,
        canRestart=None,
        instructionPointerReference=None,
        moduleId=None,
        presentationHint=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer id: An identifier for the stack frame. It must be unique across all threads.
        This id can be used to retrieve the scopes of the frame with the `scopes` request or to restart the execution of a stack frame.
        :param string name: The name of the stack frame, typically a method name.
        :param integer line: The line within the source of the frame. If the source attribute is missing or doesn't exist, `line` is 0 and should be ignored by the client.
        :param integer column: Start position of the range covered by the stack frame. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If attribute `source` is missing or doesn't exist, `column` is 0 and should be ignored by the client.
        :param Source source: The source of the frame.
        :param integer endLine: The end line of the range covered by the stack frame.
        :param integer endColumn: End position of the range covered by the stack frame. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param boolean canRestart: Indicates whether this frame can be restarted with the `restart` request. Clients should only use this if the debug adapter supports the `restart` request and the corresponding capability `supportsRestartRequest` is true. If a debug adapter has this capability, then `canRestart` defaults to `true` if the property is absent.
        :param string instructionPointerReference: A memory reference for the current instruction pointer in this frame.
        :param ['integer', 'string'] moduleId: The module associated with this frame, if any.
        :param string presentationHint: A hint for how to present this frame in the UI.
        A value of `label` can be used to indicate that the frame is an artificial frame that is used as a visual label or separator. A value of `subtle` can be used to change the appearance of a frame in a 'subtle' way.
        """
        self.id = id
        self.name = name
        self.line = line
        self.column = column
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.endLine = endLine
        self.endColumn = endColumn
        self.canRestart = canRestart
        self.instructionPointerReference = instructionPointerReference
        self.moduleId = moduleId
        self.presentationHint = presentationHint
        if update_ids_from_dap:
            self.id = self._translate_id_from_dap(self.id)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "id" in dct:
            dct["id"] = cls._translate_id_from_dap(dct["id"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        id = self.id  # noqa (assign to builtin)
        name = self.name
        line = self.line
        column = self.column
        source = self.source
        endLine = self.endLine
        endColumn = self.endColumn
        canRestart = self.canRestart
        instructionPointerReference = self.instructionPointerReference
        moduleId = self.moduleId
        presentationHint = self.presentationHint
        if update_ids_to_dap:
            if id is not None:
                id = self._translate_id_to_dap(id)  # noqa (assign to builtin)
        dct = {
            "id": id,
            "name": name,
            "line": line,
            "column": column,
        }
        if source is not None:
            dct["source"] = source.to_dict(update_ids_to_dap=update_ids_to_dap)
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        if canRestart is not None:
            dct["canRestart"] = canRestart
        if instructionPointerReference is not None:
            dct["instructionPointerReference"] = instructionPointerReference
        if moduleId is not None:
            dct["moduleId"] = moduleId
        if presentationHint is not None:
            dct["presentationHint"] = presentationHint
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "id" in dct:
            dct["id"] = cls._translate_id_to_dap(dct["id"])
        return dct


@register
class Scope(BaseSchema):
    """
    A `Scope` is a named container for variables. Optionally a scope can map to a source or a range
    within a source.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "name": {
            "type": "string",
            "description": "Name of the scope such as 'Arguments', 'Locals', or 'Registers'. This string is shown in the UI as is and can be translated.",
        },
        "presentationHint": {
            "type": "string",
            "description": "A hint for how to present this scope in the UI. If this attribute is missing, the scope is shown with a generic UI.",
            "_enum": ["arguments", "locals", "registers"],
            "enumDescriptions": [
                "Scope contains method arguments.",
                "Scope contains local variables.",
                "Scope contains registers. Only a single `registers` scope should be returned from a `scopes` request.",
            ],
        },
        "variablesReference": {
            "type": "integer",
            "description": "The variables of this scope can be retrieved by passing the value of `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "namedVariables": {
            "type": "integer",
            "description": "The number of named variables in this scope.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.",
        },
        "indexedVariables": {
            "type": "integer",
            "description": "The number of indexed variables in this scope.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.",
        },
        "expensive": {
            "type": "boolean",
            "description": "If True, the number of variables in this scope is large or expensive to retrieve.",
        },
        "source": {"description": "The source for this scope.", "type": "Source"},
        "line": {"type": "integer", "description": "The start line of the range covered by this scope."},
        "column": {
            "type": "integer",
            "description": "Start position of the range covered by the scope. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "endLine": {"type": "integer", "description": "The end line of the range covered by this scope."},
        "endColumn": {
            "type": "integer",
            "description": "End position of the range covered by the scope. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        name,
        variablesReference,
        expensive,
        presentationHint=None,
        namedVariables=None,
        indexedVariables=None,
        source=None,
        line=None,
        column=None,
        endLine=None,
        endColumn=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: Name of the scope such as 'Arguments', 'Locals', or 'Registers'. This string is shown in the UI as is and can be translated.
        :param integer variablesReference: The variables of this scope can be retrieved by passing the value of `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.
        :param boolean expensive: If true, the number of variables in this scope is large or expensive to retrieve.
        :param string presentationHint: A hint for how to present this scope in the UI. If this attribute is missing, the scope is shown with a generic UI.
        :param integer namedVariables: The number of named variables in this scope.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        :param integer indexedVariables: The number of indexed variables in this scope.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        :param Source source: The source for this scope.
        :param integer line: The start line of the range covered by this scope.
        :param integer column: Start position of the range covered by the scope. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param integer endLine: The end line of the range covered by this scope.
        :param integer endColumn: End position of the range covered by the scope. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        """
        self.name = name
        self.variablesReference = variablesReference
        self.expensive = expensive
        self.presentationHint = presentationHint
        self.namedVariables = namedVariables
        self.indexedVariables = indexedVariables
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.line = line
        self.column = column
        self.endLine = endLine
        self.endColumn = endColumn
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        variablesReference = self.variablesReference
        expensive = self.expensive
        presentationHint = self.presentationHint
        namedVariables = self.namedVariables
        indexedVariables = self.indexedVariables
        source = self.source
        line = self.line
        column = self.column
        endLine = self.endLine
        endColumn = self.endColumn
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "name": name,
            "variablesReference": variablesReference,
            "expensive": expensive,
        }
        if presentationHint is not None:
            dct["presentationHint"] = presentationHint
        if namedVariables is not None:
            dct["namedVariables"] = namedVariables
        if indexedVariables is not None:
            dct["indexedVariables"] = indexedVariables
        if source is not None:
            dct["source"] = source.to_dict(update_ids_to_dap=update_ids_to_dap)
        if line is not None:
            dct["line"] = line
        if column is not None:
            dct["column"] = column
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register
class Variable(BaseSchema):
    """
    A Variable is a name/value pair.

    The `type` attribute is shown if space permits or when hovering over the variable's name.

    The `kind` attribute is used to render additional properties of the variable, e.g. different icons
    can be used to indicate that a variable is public or private.

    If the value is structured (has children), a handle is provided to retrieve the children with the
    `variables` request.

    If the number of named or indexed children is large, the numbers should be returned via the
    `namedVariables` and `indexedVariables` attributes.

    The client can use this information to present the children in a paged UI and fetch them in chunks.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "name": {"type": "string", "description": "The variable's name."},
        "value": {
            "type": "string",
            "description": "The variable's value.\nThis can be a multi-line text, e.g. for a function the body of a function.\nFor structured variables (which do not have a simple value), it is recommended to provide a one-line representation of the structured object. This helps to identify the structured object in the collapsed state when its children are not yet visible.\nAn empty string can be used if no value should be shown in the UI.",
        },
        "type": {
            "type": "string",
            "description": "The type of the variable's value. Typically shown in the UI when hovering over the value.\nThis attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is True.",
        },
        "presentationHint": {
            "description": "Properties of a variable that can be used to determine how to render the variable in the UI.",
            "type": "VariablePresentationHint",
        },
        "evaluateName": {
            "type": "string",
            "description": "The evaluatable name of this variable which can be passed to the `evaluate` request to fetch the variable's value.",
        },
        "variablesReference": {
            "type": "integer",
            "description": "If `variablesReference` is > 0, the variable is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "namedVariables": {
            "type": "integer",
            "description": "The number of named child variables.\nThe client can use this information to present the children in a paged UI and fetch them in chunks.",
        },
        "indexedVariables": {
            "type": "integer",
            "description": "The number of indexed child variables.\nThe client can use this information to present the children in a paged UI and fetch them in chunks.",
        },
        "memoryReference": {
            "type": "string",
            "description": "A memory reference associated with this variable.\nFor pointer type variables, this is generally a reference to the memory address contained in the pointer.\nFor executable data, this reference may later be used in a `disassemble` request.\nThis attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is True.",
        },
    }
    __refs__ = set(["presentationHint"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        name,
        value,
        variablesReference,
        type=None,
        presentationHint=None,
        evaluateName=None,
        namedVariables=None,
        indexedVariables=None,
        memoryReference=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: The variable's name.
        :param string value: The variable's value.
        This can be a multi-line text, e.g. for a function the body of a function.
        For structured variables (which do not have a simple value), it is recommended to provide a one-line representation of the structured object. This helps to identify the structured object in the collapsed state when its children are not yet visible.
        An empty string can be used if no value should be shown in the UI.
        :param integer variablesReference: If `variablesReference` is > 0, the variable is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.
        :param string type: The type of the variable's value. Typically shown in the UI when hovering over the value.
        This attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is true.
        :param VariablePresentationHint presentationHint: Properties of a variable that can be used to determine how to render the variable in the UI.
        :param string evaluateName: The evaluatable name of this variable which can be passed to the `evaluate` request to fetch the variable's value.
        :param integer namedVariables: The number of named child variables.
        The client can use this information to present the children in a paged UI and fetch them in chunks.
        :param integer indexedVariables: The number of indexed child variables.
        The client can use this information to present the children in a paged UI and fetch them in chunks.
        :param string memoryReference: A memory reference associated with this variable.
        For pointer type variables, this is generally a reference to the memory address contained in the pointer.
        For executable data, this reference may later be used in a `disassemble` request.
        This attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is true.
        """
        self.name = name
        self.value = value
        self.variablesReference = variablesReference
        self.type = type
        if presentationHint is None:
            self.presentationHint = VariablePresentationHint()
        else:
            self.presentationHint = (
                VariablePresentationHint(update_ids_from_dap=update_ids_from_dap, **presentationHint)
                if presentationHint.__class__ != VariablePresentationHint
                else presentationHint
            )
        self.evaluateName = evaluateName
        self.namedVariables = namedVariables
        self.indexedVariables = indexedVariables
        self.memoryReference = memoryReference
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        value = self.value
        variablesReference = self.variablesReference
        type = self.type  # noqa (assign to builtin)
        presentationHint = self.presentationHint
        evaluateName = self.evaluateName
        namedVariables = self.namedVariables
        indexedVariables = self.indexedVariables
        memoryReference = self.memoryReference
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "name": name,
            "value": value,
            "variablesReference": variablesReference,
        }
        if type is not None:
            dct["type"] = type
        if presentationHint is not None:
            dct["presentationHint"] = presentationHint.to_dict(update_ids_to_dap=update_ids_to_dap)
        if evaluateName is not None:
            dct["evaluateName"] = evaluateName
        if namedVariables is not None:
            dct["namedVariables"] = namedVariables
        if indexedVariables is not None:
            dct["indexedVariables"] = indexedVariables
        if memoryReference is not None:
            dct["memoryReference"] = memoryReference
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register
class VariablePresentationHint(BaseSchema):
    """
    Properties of a variable that can be used to determine how to render the variable in the UI.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "kind": {
            "description": "The kind of variable. Before introducing additional values, try to use the listed values.",
            "type": "string",
            "_enum": [
                "property",
                "method",
                "class",
                "data",
                "event",
                "baseClass",
                "innerClass",
                "interface",
                "mostDerivedClass",
                "virtual",
                "dataBreakpoint",
            ],
            "enumDescriptions": [
                "Indicates that the object is a property.",
                "Indicates that the object is a method.",
                "Indicates that the object is a class.",
                "Indicates that the object is data.",
                "Indicates that the object is an event.",
                "Indicates that the object is a base class.",
                "Indicates that the object is an inner class.",
                "Indicates that the object is an interface.",
                "Indicates that the object is the most derived class.",
                "Indicates that the object is virtual, that means it is a synthetic object introduced by the adapter for rendering purposes, e.g. an index range for large arrays.",
                "Deprecated: Indicates that a data breakpoint is registered for the object. The `hasDataBreakpoint` attribute should generally be used instead.",
            ],
        },
        "attributes": {
            "description": "Set of attributes represented as an array of strings. Before introducing additional values, try to use the listed values.",
            "type": "array",
            "items": {
                "type": "string",
                "_enum": [
                    "static",
                    "constant",
                    "readOnly",
                    "rawString",
                    "hasObjectId",
                    "canHaveObjectId",
                    "hasSideEffects",
                    "hasDataBreakpoint",
                ],
                "enumDescriptions": [
                    "Indicates that the object is static.",
                    "Indicates that the object is a constant.",
                    "Indicates that the object is read only.",
                    "Indicates that the object is a raw string.",
                    "Indicates that the object can have an Object ID created for it. This is a vestigial attribute that is used by some clients; 'Object ID's are not specified in the protocol.",
                    "Indicates that the object has an Object ID associated with it. This is a vestigial attribute that is used by some clients; 'Object ID's are not specified in the protocol.",
                    "Indicates that the evaluation had side effects.",
                    "Indicates that the object has its value tracked by a data breakpoint.",
                ],
            },
        },
        "visibility": {
            "description": "Visibility of variable. Before introducing additional values, try to use the listed values.",
            "type": "string",
            "_enum": ["public", "private", "protected", "internal", "final"],
        },
        "lazy": {
            "description": "If True, clients can present the variable with a UI that supports a specific gesture to trigger its evaluation.\nThis mechanism can be used for properties that require executing code when retrieving their value and where the code execution can be expensive and/or produce side-effects. A typical example are properties based on a getter function.\nPlease note that in addition to the `lazy` flag, the variable's `variablesReference` is expected to refer to a variable that will provide the value through another `variable` request.",
            "type": "boolean",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, kind=None, attributes=None, visibility=None, lazy=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string kind: The kind of variable. Before introducing additional values, try to use the listed values.
        :param array attributes: Set of attributes represented as an array of strings. Before introducing additional values, try to use the listed values.
        :param string visibility: Visibility of variable. Before introducing additional values, try to use the listed values.
        :param boolean lazy: If true, clients can present the variable with a UI that supports a specific gesture to trigger its evaluation.
        This mechanism can be used for properties that require executing code when retrieving their value and where the code execution can be expensive and/or produce side-effects. A typical example are properties based on a getter function.
        Please note that in addition to the `lazy` flag, the variable's `variablesReference` is expected to refer to a variable that will provide the value through another `variable` request.
        """
        self.kind = kind
        self.attributes = attributes
        self.visibility = visibility
        self.lazy = lazy
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        kind = self.kind
        attributes = self.attributes
        if attributes and hasattr(attributes[0], "to_dict"):
            attributes = [x.to_dict() for x in attributes]
        visibility = self.visibility
        lazy = self.lazy
        dct = {}
        if kind is not None:
            dct["kind"] = kind
        if attributes is not None:
            dct["attributes"] = attributes
        if visibility is not None:
            dct["visibility"] = visibility
        if lazy is not None:
            dct["lazy"] = lazy
        dct.update(self.kwargs)
        return dct


@register
class BreakpointLocation(BaseSchema):
    """
    Properties of a breakpoint location returned from the `breakpointLocations` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "line": {"type": "integer", "description": "Start line of breakpoint location."},
        "column": {
            "type": "integer",
            "description": "The start position of a breakpoint location. Position is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "endLine": {"type": "integer", "description": "The end line of breakpoint location if the location covers a range."},
        "endColumn": {
            "type": "integer",
            "description": "The end position of a breakpoint location (if the location covers a range). Position is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, line, column=None, endLine=None, endColumn=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer line: Start line of breakpoint location.
        :param integer column: The start position of a breakpoint location. Position is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param integer endLine: The end line of breakpoint location if the location covers a range.
        :param integer endColumn: The end position of a breakpoint location (if the location covers a range). Position is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        """
        self.line = line
        self.column = column
        self.endLine = endLine
        self.endColumn = endColumn
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        line = self.line
        column = self.column
        endLine = self.endLine
        endColumn = self.endColumn
        dct = {
            "line": line,
        }
        if column is not None:
            dct["column"] = column
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        dct.update(self.kwargs)
        return dct


@register
class SourceBreakpoint(BaseSchema):
    """
    Properties of a breakpoint or logpoint passed to the `setBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "line": {"type": "integer", "description": "The source line of the breakpoint or logpoint."},
        "column": {
            "type": "integer",
            "description": "Start position within source line of the breakpoint or logpoint. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "condition": {
            "type": "string",
            "description": "The expression for conditional breakpoints.\nIt is only honored by a debug adapter if the corresponding capability `supportsConditionalBreakpoints` is True.",
        },
        "hitCondition": {
            "type": "string",
            "description": "The expression that controls how many hits of the breakpoint are ignored.\nThe debug adapter is expected to interpret the expression as needed.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsHitConditionalBreakpoints` is True.\nIf both this property and `condition` are specified, `hitCondition` should be evaluated only if the `condition` is met, and the debug adapter should stop only if both conditions are met.",
        },
        "logMessage": {
            "type": "string",
            "description": "If this attribute exists and is non-empty, the debug adapter must not 'break' (stop)\nbut log the message instead. Expressions within `{}` are interpolated.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsLogPoints` is True.\nIf either `hitCondition` or `condition` is specified, then the message should only be logged if those conditions are met.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, line, column=None, condition=None, hitCondition=None, logMessage=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer line: The source line of the breakpoint or logpoint.
        :param integer column: Start position within source line of the breakpoint or logpoint. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param string condition: The expression for conditional breakpoints.
        It is only honored by a debug adapter if the corresponding capability `supportsConditionalBreakpoints` is true.
        :param string hitCondition: The expression that controls how many hits of the breakpoint are ignored.
        The debug adapter is expected to interpret the expression as needed.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsHitConditionalBreakpoints` is true.
        If both this property and `condition` are specified, `hitCondition` should be evaluated only if the `condition` is met, and the debug adapter should stop only if both conditions are met.
        :param string logMessage: If this attribute exists and is non-empty, the debug adapter must not 'break' (stop)
        but log the message instead. Expressions within `{}` are interpolated.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsLogPoints` is true.
        If either `hitCondition` or `condition` is specified, then the message should only be logged if those conditions are met.
        """
        self.line = line
        self.column = column
        self.condition = condition
        self.hitCondition = hitCondition
        self.logMessage = logMessage
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        line = self.line
        column = self.column
        condition = self.condition
        hitCondition = self.hitCondition
        logMessage = self.logMessage
        dct = {
            "line": line,
        }
        if column is not None:
            dct["column"] = column
        if condition is not None:
            dct["condition"] = condition
        if hitCondition is not None:
            dct["hitCondition"] = hitCondition
        if logMessage is not None:
            dct["logMessage"] = logMessage
        dct.update(self.kwargs)
        return dct


@register
class FunctionBreakpoint(BaseSchema):
    """
    Properties of a breakpoint passed to the `setFunctionBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "name": {"type": "string", "description": "The name of the function."},
        "condition": {
            "type": "string",
            "description": "An expression for conditional breakpoints.\nIt is only honored by a debug adapter if the corresponding capability `supportsConditionalBreakpoints` is True.",
        },
        "hitCondition": {
            "type": "string",
            "description": "An expression that controls how many hits of the breakpoint are ignored.\nThe debug adapter is expected to interpret the expression as needed.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsHitConditionalBreakpoints` is True.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, name, condition=None, hitCondition=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: The name of the function.
        :param string condition: An expression for conditional breakpoints.
        It is only honored by a debug adapter if the corresponding capability `supportsConditionalBreakpoints` is true.
        :param string hitCondition: An expression that controls how many hits of the breakpoint are ignored.
        The debug adapter is expected to interpret the expression as needed.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsHitConditionalBreakpoints` is true.
        """
        self.name = name
        self.condition = condition
        self.hitCondition = hitCondition
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        condition = self.condition
        hitCondition = self.hitCondition
        dct = {
            "name": name,
        }
        if condition is not None:
            dct["condition"] = condition
        if hitCondition is not None:
            dct["hitCondition"] = hitCondition
        dct.update(self.kwargs)
        return dct


@register
class DataBreakpointAccessType(BaseSchema):
    """
    This enumeration defines all possible access types for data breakpoints.

    Note: automatically generated code. Do not edit manually.
    """

    READ = "read"
    WRITE = "write"
    READWRITE = "readWrite"

    VALID_VALUES = set(["read", "write", "readWrite"])

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class DataBreakpoint(BaseSchema):
    """
    Properties of a data breakpoint passed to the `setDataBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "dataId": {
            "type": "string",
            "description": "An id representing the data. This id is returned from the `dataBreakpointInfo` request.",
        },
        "accessType": {"description": "The access type of the data.", "type": "DataBreakpointAccessType"},
        "condition": {"type": "string", "description": "An expression for conditional breakpoints."},
        "hitCondition": {
            "type": "string",
            "description": "An expression that controls how many hits of the breakpoint are ignored.\nThe debug adapter is expected to interpret the expression as needed.",
        },
    }
    __refs__ = set(["accessType"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, dataId, accessType=None, condition=None, hitCondition=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string dataId: An id representing the data. This id is returned from the `dataBreakpointInfo` request.
        :param DataBreakpointAccessType accessType: The access type of the data.
        :param string condition: An expression for conditional breakpoints.
        :param string hitCondition: An expression that controls how many hits of the breakpoint are ignored.
        The debug adapter is expected to interpret the expression as needed.
        """
        self.dataId = dataId
        if accessType is not None:
            assert accessType in DataBreakpointAccessType.VALID_VALUES
        self.accessType = accessType
        self.condition = condition
        self.hitCondition = hitCondition
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dataId = self.dataId
        accessType = self.accessType
        condition = self.condition
        hitCondition = self.hitCondition
        dct = {
            "dataId": dataId,
        }
        if accessType is not None:
            dct["accessType"] = accessType
        if condition is not None:
            dct["condition"] = condition
        if hitCondition is not None:
            dct["hitCondition"] = hitCondition
        dct.update(self.kwargs)
        return dct


@register
class InstructionBreakpoint(BaseSchema):
    """
    Properties of a breakpoint passed to the `setInstructionBreakpoints` request

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "instructionReference": {
            "type": "string",
            "description": "The instruction reference of the breakpoint.\nThis should be a memory or instruction pointer reference from an `EvaluateResponse`, `Variable`, `StackFrame`, `GotoTarget`, or `Breakpoint`.",
        },
        "offset": {"type": "integer", "description": "The offset from the instruction reference in bytes.\nThis can be negative."},
        "condition": {
            "type": "string",
            "description": "An expression for conditional breakpoints.\nIt is only honored by a debug adapter if the corresponding capability `supportsConditionalBreakpoints` is True.",
        },
        "hitCondition": {
            "type": "string",
            "description": "An expression that controls how many hits of the breakpoint are ignored.\nThe debug adapter is expected to interpret the expression as needed.\nThe attribute is only honored by a debug adapter if the corresponding capability `supportsHitConditionalBreakpoints` is True.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, instructionReference, offset=None, condition=None, hitCondition=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string instructionReference: The instruction reference of the breakpoint.
        This should be a memory or instruction pointer reference from an `EvaluateResponse`, `Variable`, `StackFrame`, `GotoTarget`, or `Breakpoint`.
        :param integer offset: The offset from the instruction reference in bytes.
        This can be negative.
        :param string condition: An expression for conditional breakpoints.
        It is only honored by a debug adapter if the corresponding capability `supportsConditionalBreakpoints` is true.
        :param string hitCondition: An expression that controls how many hits of the breakpoint are ignored.
        The debug adapter is expected to interpret the expression as needed.
        The attribute is only honored by a debug adapter if the corresponding capability `supportsHitConditionalBreakpoints` is true.
        """
        self.instructionReference = instructionReference
        self.offset = offset
        self.condition = condition
        self.hitCondition = hitCondition
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        instructionReference = self.instructionReference
        offset = self.offset
        condition = self.condition
        hitCondition = self.hitCondition
        dct = {
            "instructionReference": instructionReference,
        }
        if offset is not None:
            dct["offset"] = offset
        if condition is not None:
            dct["condition"] = condition
        if hitCondition is not None:
            dct["hitCondition"] = hitCondition
        dct.update(self.kwargs)
        return dct


@register
class Breakpoint(BaseSchema):
    """
    Information about a breakpoint created in `setBreakpoints`, `setFunctionBreakpoints`,
    `setInstructionBreakpoints`, or `setDataBreakpoints` requests.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "id": {
            "type": "integer",
            "description": "The identifier for the breakpoint. It is needed if breakpoint events are used to update or remove breakpoints.",
        },
        "verified": {
            "type": "boolean",
            "description": "If True, the breakpoint could be set (but not necessarily at the desired location).",
        },
        "message": {
            "type": "string",
            "description": "A message about the state of the breakpoint.\nThis is shown to the user and can be used to explain why a breakpoint could not be verified.",
        },
        "source": {"description": "The source where the breakpoint is located.", "type": "Source"},
        "line": {"type": "integer", "description": "The start line of the actual range covered by the breakpoint."},
        "column": {
            "type": "integer",
            "description": "Start position of the source range covered by the breakpoint. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "endLine": {"type": "integer", "description": "The end line of the actual range covered by the breakpoint."},
        "endColumn": {
            "type": "integer",
            "description": "End position of the source range covered by the breakpoint. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.\nIf no end line is given, then the end column is assumed to be in the start line.",
        },
        "instructionReference": {"type": "string", "description": "A memory reference to where the breakpoint is set."},
        "offset": {"type": "integer", "description": "The offset from the instruction reference.\nThis can be negative."},
        "reason": {
            "type": "string",
            "description": "A machine-readable explanation of why a breakpoint may not be verified. If a breakpoint is verified or a specific reason is not known, the adapter should omit this property. Possible values include:\n\n- `pending`: Indicates a breakpoint might be verified in the future, but the adapter cannot verify it in the current state.\n - `failed`: Indicates a breakpoint was not able to be verified, and the adapter does not believe it can be verified without intervention.",
            "enum": ["pending", "failed"],
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        verified,
        id=None,
        message=None,
        source=None,
        line=None,
        column=None,
        endLine=None,
        endColumn=None,
        instructionReference=None,
        offset=None,
        reason=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean verified: If true, the breakpoint could be set (but not necessarily at the desired location).
        :param integer id: The identifier for the breakpoint. It is needed if breakpoint events are used to update or remove breakpoints.
        :param string message: A message about the state of the breakpoint.
        This is shown to the user and can be used to explain why a breakpoint could not be verified.
        :param Source source: The source where the breakpoint is located.
        :param integer line: The start line of the actual range covered by the breakpoint.
        :param integer column: Start position of the source range covered by the breakpoint. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param integer endLine: The end line of the actual range covered by the breakpoint.
        :param integer endColumn: End position of the source range covered by the breakpoint. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        If no end line is given, then the end column is assumed to be in the start line.
        :param string instructionReference: A memory reference to where the breakpoint is set.
        :param integer offset: The offset from the instruction reference.
        This can be negative.
        :param string reason: A machine-readable explanation of why a breakpoint may not be verified. If a breakpoint is verified or a specific reason is not known, the adapter should omit this property. Possible values include:

        - `pending`: Indicates a breakpoint might be verified in the future, but the adapter cannot verify it in the current state.
         - `failed`: Indicates a breakpoint was not able to be verified, and the adapter does not believe it can be verified without intervention.
        """
        self.verified = verified
        self.id = id
        self.message = message
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.line = line
        self.column = column
        self.endLine = endLine
        self.endColumn = endColumn
        self.instructionReference = instructionReference
        self.offset = offset
        self.reason = reason
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        verified = self.verified
        id = self.id  # noqa (assign to builtin)
        message = self.message
        source = self.source
        line = self.line
        column = self.column
        endLine = self.endLine
        endColumn = self.endColumn
        instructionReference = self.instructionReference
        offset = self.offset
        reason = self.reason
        dct = {
            "verified": verified,
        }
        if id is not None:
            dct["id"] = id
        if message is not None:
            dct["message"] = message
        if source is not None:
            dct["source"] = source.to_dict(update_ids_to_dap=update_ids_to_dap)
        if line is not None:
            dct["line"] = line
        if column is not None:
            dct["column"] = column
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        if instructionReference is not None:
            dct["instructionReference"] = instructionReference
        if offset is not None:
            dct["offset"] = offset
        if reason is not None:
            dct["reason"] = reason
        dct.update(self.kwargs)
        return dct


@register
class SteppingGranularity(BaseSchema):
    """
    The granularity of one 'step' in the stepping requests `next`, `stepIn`, `stepOut`, and `stepBack`.

    Note: automatically generated code. Do not edit manually.
    """

    STATEMENT = "statement"
    LINE = "line"
    INSTRUCTION = "instruction"

    VALID_VALUES = set(["statement", "line", "instruction"])

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class StepInTarget(BaseSchema):
    """
    A `StepInTarget` can be used in the `stepIn` request and determines into which single target the
    `stepIn` request should step.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "id": {"type": "integer", "description": "Unique identifier for a step-in target."},
        "label": {"type": "string", "description": "The name of the step-in target (shown in the UI)."},
        "line": {"type": "integer", "description": "The line of the step-in target."},
        "column": {
            "type": "integer",
            "description": "Start position of the range covered by the step in target. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "endLine": {"type": "integer", "description": "The end line of the range covered by the step-in target."},
        "endColumn": {
            "type": "integer",
            "description": "End position of the range covered by the step in target. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, id, label, line=None, column=None, endLine=None, endColumn=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer id: Unique identifier for a step-in target.
        :param string label: The name of the step-in target (shown in the UI).
        :param integer line: The line of the step-in target.
        :param integer column: Start position of the range covered by the step in target. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param integer endLine: The end line of the range covered by the step-in target.
        :param integer endColumn: End position of the range covered by the step in target. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        """
        self.id = id
        self.label = label
        self.line = line
        self.column = column
        self.endLine = endLine
        self.endColumn = endColumn
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        id = self.id  # noqa (assign to builtin)
        label = self.label
        line = self.line
        column = self.column
        endLine = self.endLine
        endColumn = self.endColumn
        dct = {
            "id": id,
            "label": label,
        }
        if line is not None:
            dct["line"] = line
        if column is not None:
            dct["column"] = column
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        dct.update(self.kwargs)
        return dct


@register
class GotoTarget(BaseSchema):
    """
    A `GotoTarget` describes a code location that can be used as a target in the `goto` request.

    The possible goto targets can be determined via the `gotoTargets` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "id": {"type": "integer", "description": "Unique identifier for a goto target. This is used in the `goto` request."},
        "label": {"type": "string", "description": "The name of the goto target (shown in the UI)."},
        "line": {"type": "integer", "description": "The line of the goto target."},
        "column": {"type": "integer", "description": "The column of the goto target."},
        "endLine": {"type": "integer", "description": "The end line of the range covered by the goto target."},
        "endColumn": {"type": "integer", "description": "The end column of the range covered by the goto target."},
        "instructionPointerReference": {
            "type": "string",
            "description": "A memory reference for the instruction pointer value represented by this target.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        id,
        label,
        line,
        column=None,
        endLine=None,
        endColumn=None,
        instructionPointerReference=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer id: Unique identifier for a goto target. This is used in the `goto` request.
        :param string label: The name of the goto target (shown in the UI).
        :param integer line: The line of the goto target.
        :param integer column: The column of the goto target.
        :param integer endLine: The end line of the range covered by the goto target.
        :param integer endColumn: The end column of the range covered by the goto target.
        :param string instructionPointerReference: A memory reference for the instruction pointer value represented by this target.
        """
        self.id = id
        self.label = label
        self.line = line
        self.column = column
        self.endLine = endLine
        self.endColumn = endColumn
        self.instructionPointerReference = instructionPointerReference
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        id = self.id  # noqa (assign to builtin)
        label = self.label
        line = self.line
        column = self.column
        endLine = self.endLine
        endColumn = self.endColumn
        instructionPointerReference = self.instructionPointerReference
        dct = {
            "id": id,
            "label": label,
            "line": line,
        }
        if column is not None:
            dct["column"] = column
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        if instructionPointerReference is not None:
            dct["instructionPointerReference"] = instructionPointerReference
        dct.update(self.kwargs)
        return dct


@register
class CompletionItem(BaseSchema):
    """
    `CompletionItems` are the suggestions returned from the `completions` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "label": {
            "type": "string",
            "description": "The label of this completion item. By default this is also the text that is inserted when selecting this completion.",
        },
        "text": {"type": "string", "description": "If text is returned and not an empty string, then it is inserted instead of the label."},
        "sortText": {
            "type": "string",
            "description": "A string that should be used when comparing this item with other items. If not returned or an empty string, the `label` is used instead.",
        },
        "detail": {
            "type": "string",
            "description": "A human-readable string with additional information about this item, like type or symbol information.",
        },
        "type": {
            "description": "The item's type. Typically the client uses this information to render the item in the UI with an icon.",
            "type": "CompletionItemType",
        },
        "start": {
            "type": "integer",
            "description": "Start position (within the `text` attribute of the `completions` request) where the completion text is added. The position is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If the start position is omitted the text is added at the location specified by the `column` attribute of the `completions` request.",
        },
        "length": {
            "type": "integer",
            "description": "Length determines how many characters are overwritten by the completion text and it is measured in UTF-16 code units. If missing the value 0 is assumed which results in the completion text being inserted.",
        },
        "selectionStart": {
            "type": "integer",
            "description": "Determines the start of the new selection after the text has been inserted (or replaced). `selectionStart` is measured in UTF-16 code units and must be in the range 0 and length of the completion text. If omitted the selection starts at the end of the completion text.",
        },
        "selectionLength": {
            "type": "integer",
            "description": "Determines the length of the new selection after the text has been inserted (or replaced) and it is measured in UTF-16 code units. The selection can not extend beyond the bounds of the completion text. If omitted the length is assumed to be 0.",
        },
    }
    __refs__ = set(["type"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        label,
        text=None,
        sortText=None,
        detail=None,
        type=None,
        start=None,
        length=None,
        selectionStart=None,
        selectionLength=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string label: The label of this completion item. By default this is also the text that is inserted when selecting this completion.
        :param string text: If text is returned and not an empty string, then it is inserted instead of the label.
        :param string sortText: A string that should be used when comparing this item with other items. If not returned or an empty string, the `label` is used instead.
        :param string detail: A human-readable string with additional information about this item, like type or symbol information.
        :param CompletionItemType type: The item's type. Typically the client uses this information to render the item in the UI with an icon.
        :param integer start: Start position (within the `text` attribute of the `completions` request) where the completion text is added. The position is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based. If the start position is omitted the text is added at the location specified by the `column` attribute of the `completions` request.
        :param integer length: Length determines how many characters are overwritten by the completion text and it is measured in UTF-16 code units. If missing the value 0 is assumed which results in the completion text being inserted.
        :param integer selectionStart: Determines the start of the new selection after the text has been inserted (or replaced). `selectionStart` is measured in UTF-16 code units and must be in the range 0 and length of the completion text. If omitted the selection starts at the end of the completion text.
        :param integer selectionLength: Determines the length of the new selection after the text has been inserted (or replaced) and it is measured in UTF-16 code units. The selection can not extend beyond the bounds of the completion text. If omitted the length is assumed to be 0.
        """
        self.label = label
        self.text = text
        self.sortText = sortText
        self.detail = detail
        if type is not None:
            assert type in CompletionItemType.VALID_VALUES
        self.type = type
        self.start = start
        self.length = length
        self.selectionStart = selectionStart
        self.selectionLength = selectionLength
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        label = self.label
        text = self.text
        sortText = self.sortText
        detail = self.detail
        type = self.type  # noqa (assign to builtin)
        start = self.start
        length = self.length
        selectionStart = self.selectionStart
        selectionLength = self.selectionLength
        dct = {
            "label": label,
        }
        if text is not None:
            dct["text"] = text
        if sortText is not None:
            dct["sortText"] = sortText
        if detail is not None:
            dct["detail"] = detail
        if type is not None:
            dct["type"] = type
        if start is not None:
            dct["start"] = start
        if length is not None:
            dct["length"] = length
        if selectionStart is not None:
            dct["selectionStart"] = selectionStart
        if selectionLength is not None:
            dct["selectionLength"] = selectionLength
        dct.update(self.kwargs)
        return dct


@register
class CompletionItemType(BaseSchema):
    """
    Some predefined types for the CompletionItem. Please note that not all clients have specific icons
    for all of them.

    Note: automatically generated code. Do not edit manually.
    """

    METHOD = "method"
    FUNCTION = "function"
    CONSTRUCTOR = "constructor"
    FIELD = "field"
    VARIABLE = "variable"
    CLASS = "class"
    INTERFACE = "interface"
    MODULE = "module"
    PROPERTY = "property"
    UNIT = "unit"
    VALUE = "value"
    ENUM = "enum"
    KEYWORD = "keyword"
    SNIPPET = "snippet"
    TEXT = "text"
    COLOR = "color"
    FILE = "file"
    REFERENCE = "reference"
    CUSTOMCOLOR = "customcolor"

    VALID_VALUES = set(
        [
            "method",
            "function",
            "constructor",
            "field",
            "variable",
            "class",
            "interface",
            "module",
            "property",
            "unit",
            "value",
            "enum",
            "keyword",
            "snippet",
            "text",
            "color",
            "file",
            "reference",
            "customcolor",
        ]
    )

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class ChecksumAlgorithm(BaseSchema):
    """
    Names of checksum algorithms that may be supported by a debug adapter.

    Note: automatically generated code. Do not edit manually.
    """

    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    TIMESTAMP = "timestamp"

    VALID_VALUES = set(["MD5", "SHA1", "SHA256", "timestamp"])

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class Checksum(BaseSchema):
    """
    The checksum of an item calculated by the specified algorithm.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "algorithm": {"description": "The algorithm used to calculate this checksum.", "type": "ChecksumAlgorithm"},
        "checksum": {"type": "string", "description": "Value of the checksum, encoded as a hexadecimal value."},
    }
    __refs__ = set(["algorithm"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, algorithm, checksum, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param ChecksumAlgorithm algorithm: The algorithm used to calculate this checksum.
        :param string checksum: Value of the checksum, encoded as a hexadecimal value.
        """
        if algorithm is not None:
            assert algorithm in ChecksumAlgorithm.VALID_VALUES
        self.algorithm = algorithm
        self.checksum = checksum
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        algorithm = self.algorithm
        checksum = self.checksum
        dct = {
            "algorithm": algorithm,
            "checksum": checksum,
        }
        dct.update(self.kwargs)
        return dct


@register
class ValueFormat(BaseSchema):
    """
    Provides formatting information for a value.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"hex": {"type": "boolean", "description": "Display the value in hex."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, hex=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean hex: Display the value in hex.
        """
        self.hex = hex
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        hex = self.hex  # noqa (assign to builtin)
        dct = {}
        if hex is not None:
            dct["hex"] = hex
        dct.update(self.kwargs)
        return dct


@register
class StackFrameFormat(BaseSchema):
    """
    Provides formatting information for a stack frame.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "hex": {"type": "boolean", "description": "Display the value in hex."},
        "parameters": {"type": "boolean", "description": "Displays parameters for the stack frame."},
        "parameterTypes": {"type": "boolean", "description": "Displays the types of parameters for the stack frame."},
        "parameterNames": {"type": "boolean", "description": "Displays the names of parameters for the stack frame."},
        "parameterValues": {"type": "boolean", "description": "Displays the values of parameters for the stack frame."},
        "line": {"type": "boolean", "description": "Displays the line number of the stack frame."},
        "module": {"type": "boolean", "description": "Displays the module of the stack frame."},
        "includeAll": {
            "type": "boolean",
            "description": "Includes all stack frames, including those the debug adapter might otherwise hide.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        hex=None,
        parameters=None,
        parameterTypes=None,
        parameterNames=None,
        parameterValues=None,
        line=None,
        module=None,
        includeAll=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean hex: Display the value in hex.
        :param boolean parameters: Displays parameters for the stack frame.
        :param boolean parameterTypes: Displays the types of parameters for the stack frame.
        :param boolean parameterNames: Displays the names of parameters for the stack frame.
        :param boolean parameterValues: Displays the values of parameters for the stack frame.
        :param boolean line: Displays the line number of the stack frame.
        :param boolean module: Displays the module of the stack frame.
        :param boolean includeAll: Includes all stack frames, including those the debug adapter might otherwise hide.
        """
        self.hex = hex
        self.parameters = parameters
        self.parameterTypes = parameterTypes
        self.parameterNames = parameterNames
        self.parameterValues = parameterValues
        self.line = line
        self.module = module
        self.includeAll = includeAll
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        hex = self.hex  # noqa (assign to builtin)
        parameters = self.parameters
        parameterTypes = self.parameterTypes
        parameterNames = self.parameterNames
        parameterValues = self.parameterValues
        line = self.line
        module = self.module
        includeAll = self.includeAll
        dct = {}
        if hex is not None:
            dct["hex"] = hex
        if parameters is not None:
            dct["parameters"] = parameters
        if parameterTypes is not None:
            dct["parameterTypes"] = parameterTypes
        if parameterNames is not None:
            dct["parameterNames"] = parameterNames
        if parameterValues is not None:
            dct["parameterValues"] = parameterValues
        if line is not None:
            dct["line"] = line
        if module is not None:
            dct["module"] = module
        if includeAll is not None:
            dct["includeAll"] = includeAll
        dct.update(self.kwargs)
        return dct


@register
class ExceptionFilterOptions(BaseSchema):
    """
    An `ExceptionFilterOptions` is used to specify an exception filter together with a condition for the
    `setExceptionBreakpoints` request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "filterId": {"type": "string", "description": "ID of an exception filter returned by the `exceptionBreakpointFilters` capability."},
        "condition": {
            "type": "string",
            "description": "An expression for conditional exceptions.\nThe exception breaks into the debugger if the result of the condition is True.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, filterId, condition=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string filterId: ID of an exception filter returned by the `exceptionBreakpointFilters` capability.
        :param string condition: An expression for conditional exceptions.
        The exception breaks into the debugger if the result of the condition is true.
        """
        self.filterId = filterId
        self.condition = condition
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        filterId = self.filterId
        condition = self.condition
        dct = {
            "filterId": filterId,
        }
        if condition is not None:
            dct["condition"] = condition
        dct.update(self.kwargs)
        return dct


@register
class ExceptionOptions(BaseSchema):
    """
    An `ExceptionOptions` assigns configuration options to a set of exceptions.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "path": {
            "type": "array",
            "items": {"$ref": "#/definitions/ExceptionPathSegment"},
            "description": "A path that selects a single or multiple exceptions in a tree. If `path` is missing, the whole tree is selected.\nBy convention the first segment of the path is a category that is used to group exceptions in the UI.",
        },
        "breakMode": {"description": "Condition when a thrown exception should result in a break.", "type": "ExceptionBreakMode"},
    }
    __refs__ = set(["breakMode"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakMode, path=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param ExceptionBreakMode breakMode: Condition when a thrown exception should result in a break.
        :param array path: A path that selects a single or multiple exceptions in a tree. If `path` is missing, the whole tree is selected.
        By convention the first segment of the path is a category that is used to group exceptions in the UI.
        """
        if breakMode is not None:
            assert breakMode in ExceptionBreakMode.VALID_VALUES
        self.breakMode = breakMode
        self.path = path
        if update_ids_from_dap and self.path:
            for o in self.path:
                ExceptionPathSegment.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakMode = self.breakMode
        path = self.path
        if path and hasattr(path[0], "to_dict"):
            path = [x.to_dict() for x in path]
        dct = {
            "breakMode": breakMode,
        }
        if path is not None:
            dct["path"] = [ExceptionPathSegment.update_dict_ids_to_dap(o) for o in path] if (update_ids_to_dap and path) else path
        dct.update(self.kwargs)
        return dct


@register
class ExceptionBreakMode(BaseSchema):
    """
    This enumeration defines all possible conditions when a thrown exception should result in a break.

    never: never breaks,

    always: always breaks,

    unhandled: breaks when exception unhandled,

    userUnhandled: breaks if the exception is not handled by user code.

    Note: automatically generated code. Do not edit manually.
    """

    NEVER = "never"
    ALWAYS = "always"
    UNHANDLED = "unhandled"
    USERUNHANDLED = "userUnhandled"

    VALID_VALUES = set(["never", "always", "unhandled", "userUnhandled"])

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class ExceptionPathSegment(BaseSchema):
    """
    An `ExceptionPathSegment` represents a segment in a path that is used to match leafs or nodes in a
    tree of exceptions.

    If a segment consists of more than one name, it matches the names provided if `negate` is false or
    missing, or it matches anything except the names provided if `negate` is true.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "negate": {
            "type": "boolean",
            "description": "If false or missing this segment matches the names provided, otherwise it matches anything except the names provided.",
        },
        "names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Depending on the value of `negate` the names that should match or not match.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, names, negate=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array names: Depending on the value of `negate` the names that should match or not match.
        :param boolean negate: If false or missing this segment matches the names provided, otherwise it matches anything except the names provided.
        """
        self.names = names
        self.negate = negate
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        names = self.names
        if names and hasattr(names[0], "to_dict"):
            names = [x.to_dict() for x in names]
        negate = self.negate
        dct = {
            "names": names,
        }
        if negate is not None:
            dct["negate"] = negate
        dct.update(self.kwargs)
        return dct


@register
class ExceptionDetails(BaseSchema):
    """
    Detailed information about an exception that has occurred.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "message": {"type": "string", "description": "Message contained in the exception."},
        "typeName": {"type": "string", "description": "Short type name of the exception object."},
        "fullTypeName": {"type": "string", "description": "Fully-qualified type name of the exception object."},
        "evaluateName": {
            "type": "string",
            "description": "An expression that can be evaluated in the current scope to obtain the exception object.",
        },
        "stackTrace": {"type": "string", "description": "Stack trace at the time the exception was thrown."},
        "innerException": {
            "type": "array",
            "items": {"$ref": "#/definitions/ExceptionDetails"},
            "description": "Details of the exception contained by this exception, if any.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        message=None,
        typeName=None,
        fullTypeName=None,
        evaluateName=None,
        stackTrace=None,
        innerException=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string message: Message contained in the exception.
        :param string typeName: Short type name of the exception object.
        :param string fullTypeName: Fully-qualified type name of the exception object.
        :param string evaluateName: An expression that can be evaluated in the current scope to obtain the exception object.
        :param string stackTrace: Stack trace at the time the exception was thrown.
        :param array innerException: Details of the exception contained by this exception, if any.
        """
        self.message = message
        self.typeName = typeName
        self.fullTypeName = fullTypeName
        self.evaluateName = evaluateName
        self.stackTrace = stackTrace
        self.innerException = innerException
        if update_ids_from_dap and self.innerException:
            for o in self.innerException:
                ExceptionDetails.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        message = self.message
        typeName = self.typeName
        fullTypeName = self.fullTypeName
        evaluateName = self.evaluateName
        stackTrace = self.stackTrace
        innerException = self.innerException
        if innerException and hasattr(innerException[0], "to_dict"):
            innerException = [x.to_dict() for x in innerException]
        dct = {}
        if message is not None:
            dct["message"] = message
        if typeName is not None:
            dct["typeName"] = typeName
        if fullTypeName is not None:
            dct["fullTypeName"] = fullTypeName
        if evaluateName is not None:
            dct["evaluateName"] = evaluateName
        if stackTrace is not None:
            dct["stackTrace"] = stackTrace
        if innerException is not None:
            dct["innerException"] = (
                [ExceptionDetails.update_dict_ids_to_dap(o) for o in innerException]
                if (update_ids_to_dap and innerException)
                else innerException
            )
        dct.update(self.kwargs)
        return dct


@register
class DisassembledInstruction(BaseSchema):
    """
    Represents a single disassembled instruction.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "address": {
            "type": "string",
            "description": "The address of the instruction. Treated as a hex value if prefixed with `0x`, or as a decimal value otherwise.",
        },
        "instructionBytes": {
            "type": "string",
            "description": "Raw bytes representing the instruction and its operands, in an implementation-defined format.",
        },
        "instruction": {
            "type": "string",
            "description": "Text representing the instruction and its operands, in an implementation-defined format.",
        },
        "symbol": {"type": "string", "description": "Name of the symbol that corresponds with the location of this instruction, if any."},
        "location": {
            "description": "Source location that corresponds to this instruction, if any.\nShould always be set (if available) on the first instruction returned,\nbut can be omitted afterwards if this instruction maps to the same source file as the previous instruction.",
            "type": "Source",
        },
        "line": {"type": "integer", "description": "The line within the source location that corresponds to this instruction, if any."},
        "column": {"type": "integer", "description": "The column within the line that corresponds to this instruction, if any."},
        "endLine": {"type": "integer", "description": "The end line of the range that corresponds to this instruction, if any."},
        "endColumn": {"type": "integer", "description": "The end column of the range that corresponds to this instruction, if any."},
        "presentationHint": {
            "type": "string",
            "description": "A hint for how to present the instruction in the UI.\n\nA value of `invalid` may be used to indicate this instruction is 'filler' and cannot be reached by the program. For example, unreadable memory addresses may be presented is 'invalid.'",
            "enum": ["normal", "invalid"],
        },
    }
    __refs__ = set(["location"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        address,
        instruction,
        instructionBytes=None,
        symbol=None,
        location=None,
        line=None,
        column=None,
        endLine=None,
        endColumn=None,
        presentationHint=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string address: The address of the instruction. Treated as a hex value if prefixed with `0x`, or as a decimal value otherwise.
        :param string instruction: Text representing the instruction and its operands, in an implementation-defined format.
        :param string instructionBytes: Raw bytes representing the instruction and its operands, in an implementation-defined format.
        :param string symbol: Name of the symbol that corresponds with the location of this instruction, if any.
        :param Source location: Source location that corresponds to this instruction, if any.
        Should always be set (if available) on the first instruction returned,
        but can be omitted afterwards if this instruction maps to the same source file as the previous instruction.
        :param integer line: The line within the source location that corresponds to this instruction, if any.
        :param integer column: The column within the line that corresponds to this instruction, if any.
        :param integer endLine: The end line of the range that corresponds to this instruction, if any.
        :param integer endColumn: The end column of the range that corresponds to this instruction, if any.
        :param string presentationHint: A hint for how to present the instruction in the UI.

        A value of `invalid` may be used to indicate this instruction is 'filler' and cannot be reached by the program. For example, unreadable memory addresses may be presented is 'invalid.'
        """
        self.address = address
        self.instruction = instruction
        self.instructionBytes = instructionBytes
        self.symbol = symbol
        if location is None:
            self.location = Source()
        else:
            self.location = Source(update_ids_from_dap=update_ids_from_dap, **location) if location.__class__ != Source else location
        self.line = line
        self.column = column
        self.endLine = endLine
        self.endColumn = endColumn
        self.presentationHint = presentationHint
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        address = self.address
        instruction = self.instruction
        instructionBytes = self.instructionBytes
        symbol = self.symbol
        location = self.location
        line = self.line
        column = self.column
        endLine = self.endLine
        endColumn = self.endColumn
        presentationHint = self.presentationHint
        dct = {
            "address": address,
            "instruction": instruction,
        }
        if instructionBytes is not None:
            dct["instructionBytes"] = instructionBytes
        if symbol is not None:
            dct["symbol"] = symbol
        if location is not None:
            dct["location"] = location.to_dict(update_ids_to_dap=update_ids_to_dap)
        if line is not None:
            dct["line"] = line
        if column is not None:
            dct["column"] = column
        if endLine is not None:
            dct["endLine"] = endLine
        if endColumn is not None:
            dct["endColumn"] = endColumn
        if presentationHint is not None:
            dct["presentationHint"] = presentationHint
        dct.update(self.kwargs)
        return dct


@register
class InvalidatedAreas(BaseSchema):
    """
    Logical areas that can be invalidated by the `invalidated` event.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register_request("setDebuggerProperty")
@register
class SetDebuggerPropertyRequest(BaseSchema):
    """
    The request can be used to enable or disable debugger features.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setDebuggerProperty"]},
        "arguments": {"type": "SetDebuggerPropertyArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetDebuggerPropertyArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setDebuggerProperty"
        if arguments is None:
            self.arguments = SetDebuggerPropertyArguments()
        else:
            self.arguments = (
                SetDebuggerPropertyArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetDebuggerPropertyArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetDebuggerPropertyArguments(BaseSchema):
    """
    Arguments for 'setDebuggerProperty' request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "ideOS": {"type": ["string"], "description": "OS where the ide is running. Supported values [Windows, Linux]"},
        "dontTraceStartPatterns": {
            "type": ["array"],
            "description": "Patterns to match with the start of the file paths. Matching paths will be added to a list of file where trace is ignored.",
        },
        "dontTraceEndPatterns": {
            "type": ["array"],
            "description": "Patterns to match with the end of the file paths. Matching paths will be added to a list of file where trace is ignored.",
        },
        "skipSuspendOnBreakpointException": {
            "type": ["array"],
            "description": "List of exceptions that should be skipped when doing condition evaluations.",
        },
        "skipPrintBreakpointException": {
            "type": ["array"],
            "description": "List of exceptions that should skip printing to stderr when doing condition evaluations.",
        },
        "multiThreadsSingleNotification": {
            "type": ["boolean"],
            "description": "If false then a notification is generated for each thread event. If True a single event is gnenerated, and all threads follow that behavior.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        ideOS=None,
        dontTraceStartPatterns=None,
        dontTraceEndPatterns=None,
        skipSuspendOnBreakpointException=None,
        skipPrintBreakpointException=None,
        multiThreadsSingleNotification=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param ['string'] ideOS: OS where the ide is running. Supported values [Windows, Linux]
        :param ['array'] dontTraceStartPatterns: Patterns to match with the start of the file paths. Matching paths will be added to a list of file where trace is ignored.
        :param ['array'] dontTraceEndPatterns: Patterns to match with the end of the file paths. Matching paths will be added to a list of file where trace is ignored.
        :param ['array'] skipSuspendOnBreakpointException: List of exceptions that should be skipped when doing condition evaluations.
        :param ['array'] skipPrintBreakpointException: List of exceptions that should skip printing to stderr when doing condition evaluations.
        :param ['boolean'] multiThreadsSingleNotification: If false then a notification is generated for each thread event. If true a single event is gnenerated, and all threads follow that behavior.
        """
        self.ideOS = ideOS
        self.dontTraceStartPatterns = dontTraceStartPatterns
        self.dontTraceEndPatterns = dontTraceEndPatterns
        self.skipSuspendOnBreakpointException = skipSuspendOnBreakpointException
        self.skipPrintBreakpointException = skipPrintBreakpointException
        self.multiThreadsSingleNotification = multiThreadsSingleNotification
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        ideOS = self.ideOS
        dontTraceStartPatterns = self.dontTraceStartPatterns
        dontTraceEndPatterns = self.dontTraceEndPatterns
        skipSuspendOnBreakpointException = self.skipSuspendOnBreakpointException
        skipPrintBreakpointException = self.skipPrintBreakpointException
        multiThreadsSingleNotification = self.multiThreadsSingleNotification
        dct = {}
        if ideOS is not None:
            dct["ideOS"] = ideOS
        if dontTraceStartPatterns is not None:
            dct["dontTraceStartPatterns"] = dontTraceStartPatterns
        if dontTraceEndPatterns is not None:
            dct["dontTraceEndPatterns"] = dontTraceEndPatterns
        if skipSuspendOnBreakpointException is not None:
            dct["skipSuspendOnBreakpointException"] = skipSuspendOnBreakpointException
        if skipPrintBreakpointException is not None:
            dct["skipPrintBreakpointException"] = skipPrintBreakpointException
        if multiThreadsSingleNotification is not None:
            dct["multiThreadsSingleNotification"] = multiThreadsSingleNotification
        dct.update(self.kwargs)
        return dct


@register_response("setDebuggerProperty")
@register
class SetDebuggerPropertyResponse(BaseSchema):
    """
    Response to 'setDebuggerProperty' request. This is just an acknowledgement, so no body field is
    required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_event("pydevdInputRequested")
@register
class PydevdInputRequestedEvent(BaseSchema):
    """
    The event indicates input was requested by debuggee.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["event"]},
        "event": {"type": "string", "enum": ["pydevdInputRequested"]},
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Event-specific information.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string event:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Event-specific information.
        """
        self.type = "event"
        self.event = "pydevdInputRequested"
        self.seq = seq
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        event = self.event
        seq = self.seq
        body = self.body
        dct = {
            "type": type,
            "event": event,
            "seq": seq,
        }
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register_request("setPydevdSourceMap")
@register
class SetPydevdSourceMapRequest(BaseSchema):
    """
    Sets multiple PydevdSourceMap for a single source and clears all previous PydevdSourceMap in that
    source.

    i.e.: Maps paths and lines in a 1:N mapping (use case: map a single file in the IDE to multiple
    IPython cells).

    To clear all PydevdSourceMap for a source, specify an empty array.

    Interaction with breakpoints: When a new mapping is sent, breakpoints that match the source (or
    previously matched a source) are reapplied.

    Interaction with launch pathMapping: both mappings are independent. This mapping is applied after
    the launch pathMapping.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["setPydevdSourceMap"]},
        "arguments": {"type": "SetPydevdSourceMapArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param SetPydevdSourceMapArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "setPydevdSourceMap"
        if arguments is None:
            self.arguments = SetPydevdSourceMapArguments()
        else:
            self.arguments = (
                SetPydevdSourceMapArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != SetPydevdSourceMapArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetPydevdSourceMapArguments(BaseSchema):
    """
    Arguments for 'setPydevdSourceMap' request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "source": {
            "description": "The source location of the PydevdSourceMap; 'source.path' must be specified (e.g.: for an ipython notebook this could be something as /home/notebook/note.py).",
            "type": "Source",
        },
        "pydevdSourceMaps": {
            "type": "array",
            "items": {"$ref": "#/definitions/PydevdSourceMap"},
            "description": "The PydevdSourceMaps to be set to the given source (provide an empty array to clear the source mappings for a given path).",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, source, pydevdSourceMaps=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param Source source: The source location of the PydevdSourceMap; 'source.path' must be specified (e.g.: for an ipython notebook this could be something as /home/notebook/note.py).
        :param array pydevdSourceMaps: The PydevdSourceMaps to be set to the given source (provide an empty array to clear the source mappings for a given path).
        """
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.pydevdSourceMaps = pydevdSourceMaps
        if update_ids_from_dap and self.pydevdSourceMaps:
            for o in self.pydevdSourceMaps:
                PydevdSourceMap.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        source = self.source
        pydevdSourceMaps = self.pydevdSourceMaps
        if pydevdSourceMaps and hasattr(pydevdSourceMaps[0], "to_dict"):
            pydevdSourceMaps = [x.to_dict() for x in pydevdSourceMaps]
        dct = {
            "source": source.to_dict(update_ids_to_dap=update_ids_to_dap),
        }
        if pydevdSourceMaps is not None:
            dct["pydevdSourceMaps"] = (
                [PydevdSourceMap.update_dict_ids_to_dap(o) for o in pydevdSourceMaps]
                if (update_ids_to_dap and pydevdSourceMaps)
                else pydevdSourceMaps
            )
        dct.update(self.kwargs)
        return dct


@register_response("setPydevdSourceMap")
@register
class SetPydevdSourceMapResponse(BaseSchema):
    """
    Response to 'setPydevdSourceMap' request. This is just an acknowledgement, so no body field is
    required.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Contains request result if success is True and error details if success is false.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, seq=-1, message=None, body=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] body: Contains request result if success is true and error details if success is false.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        self.seq = seq
        self.message = message
        self.body = body
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        seq = self.seq
        message = self.message
        body = self.body
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        if body is not None:
            dct["body"] = body
        dct.update(self.kwargs)
        return dct


@register
class PydevdSourceMap(BaseSchema):
    """
    Information that allows mapping a local line to a remote source/line.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "line": {
            "type": "integer",
            "description": "The local line to which the mapping should map to (e.g.: for an ipython notebook this would be the first line of the cell in the file).",
        },
        "endLine": {"type": "integer", "description": "The end line."},
        "runtimeSource": {
            "description": "The path that the user has remotely -- 'source.path' must be specified (e.g.: for an ipython notebook this could be something as '<ipython-input-1-4561234>')",
            "type": "Source",
        },
        "runtimeLine": {
            "type": "integer",
            "description": "The remote line to which the mapping should map to (e.g.: for an ipython notebook this would be always 1 as it'd map the start of the cell).",
        },
    }
    __refs__ = set(["runtimeSource"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, line, endLine, runtimeSource, runtimeLine, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer line: The local line to which the mapping should map to (e.g.: for an ipython notebook this would be the first line of the cell in the file).
        :param integer endLine: The end line.
        :param Source runtimeSource: The path that the user has remotely -- 'source.path' must be specified (e.g.: for an ipython notebook this could be something as '<ipython-input-1-4561234>')
        :param integer runtimeLine: The remote line to which the mapping should map to (e.g.: for an ipython notebook this would be always 1 as it'd map the start of the cell).
        """
        self.line = line
        self.endLine = endLine
        if runtimeSource is None:
            self.runtimeSource = Source()
        else:
            self.runtimeSource = (
                Source(update_ids_from_dap=update_ids_from_dap, **runtimeSource) if runtimeSource.__class__ != Source else runtimeSource
            )
        self.runtimeLine = runtimeLine
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        line = self.line
        endLine = self.endLine
        runtimeSource = self.runtimeSource
        runtimeLine = self.runtimeLine
        dct = {
            "line": line,
            "endLine": endLine,
            "runtimeSource": runtimeSource.to_dict(update_ids_to_dap=update_ids_to_dap),
            "runtimeLine": runtimeLine,
        }
        dct.update(self.kwargs)
        return dct


@register_request("pydevdSystemInfo")
@register
class PydevdSystemInfoRequest(BaseSchema):
    """
    The request can be used retrieve system information, python version, etc.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["pydevdSystemInfo"]},
        "arguments": {"type": "PydevdSystemInfoArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, seq=-1, arguments=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param PydevdSystemInfoArguments arguments:
        """
        self.type = "request"
        self.command = "pydevdSystemInfo"
        self.seq = seq
        if arguments is None:
            self.arguments = PydevdSystemInfoArguments()
        else:
            self.arguments = (
                PydevdSystemInfoArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != PydevdSystemInfoArguments
                else arguments
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        seq = self.seq
        arguments = self.arguments
        dct = {
            "type": type,
            "command": command,
            "seq": seq,
        }
        if arguments is not None:
            dct["arguments"] = arguments.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class PydevdSystemInfoArguments(BaseSchema):
    """
    Arguments for 'pydevdSystemInfo' request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register_response("pydevdSystemInfo")
@register
class PydevdSystemInfoResponse(BaseSchema):
    """
    Response to 'pydevdSystemInfo' request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "python": {
                    "$ref": "#/definitions/PydevdPythonInfo",
                    "description": "Information about the python version running in the current process.",
                },
                "platform": {
                    "$ref": "#/definitions/PydevdPlatformInfo",
                    "description": "Information about the plarforn on which the current process is running.",
                },
                "process": {"$ref": "#/definitions/PydevdProcessInfo", "description": "Information about the current process."},
                "pydevd": {"$ref": "#/definitions/PydevdInfo", "description": "Information about pydevd."},
            },
            "required": ["python", "platform", "process", "pydevd"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param PydevdSystemInfoResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = PydevdSystemInfoResponseBody()
        else:
            self.body = (
                PydevdSystemInfoResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != PydevdSystemInfoResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register
class PydevdPythonInfo(BaseSchema):
    """
    This object contains python version and implementation details.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "version": {
            "type": "string",
            "description": "Python version as a string in semver format: <major>.<minor>.<micro><releaselevel><serial>.",
        },
        "implementation": {
            "description": "Python version as a string in this format <major>.<minor>.<micro><releaselevel><serial>.",
            "type": "PydevdPythonImplementationInfo",
        },
    }
    __refs__ = set(["implementation"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, version=None, implementation=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string version: Python version as a string in semver format: <major>.<minor>.<micro><releaselevel><serial>.
        :param PydevdPythonImplementationInfo implementation: Python version as a string in this format <major>.<minor>.<micro><releaselevel><serial>.
        """
        self.version = version
        if implementation is None:
            self.implementation = PydevdPythonImplementationInfo()
        else:
            self.implementation = (
                PydevdPythonImplementationInfo(update_ids_from_dap=update_ids_from_dap, **implementation)
                if implementation.__class__ != PydevdPythonImplementationInfo
                else implementation
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        version = self.version
        implementation = self.implementation
        dct = {}
        if version is not None:
            dct["version"] = version
        if implementation is not None:
            dct["implementation"] = implementation.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class PydevdPythonImplementationInfo(BaseSchema):
    """
    This object contains python implementation details.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "name": {"type": "string", "description": "Python implementation name."},
        "version": {
            "type": "string",
            "description": "Python version as a string in semver format: <major>.<minor>.<micro><releaselevel><serial>.",
        },
        "description": {"type": "string", "description": "Optional description for this python implementation."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, name=None, version=None, description=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: Python implementation name.
        :param string version: Python version as a string in semver format: <major>.<minor>.<micro><releaselevel><serial>.
        :param string description: Optional description for this python implementation.
        """
        self.name = name
        self.version = version
        self.description = description
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        version = self.version
        description = self.description
        dct = {}
        if name is not None:
            dct["name"] = name
        if version is not None:
            dct["version"] = version
        if description is not None:
            dct["description"] = description
        dct.update(self.kwargs)
        return dct


@register
class PydevdPlatformInfo(BaseSchema):
    """
    This object contains python version and implementation details.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"name": {"type": "string", "description": "Name of the platform as returned by 'sys.platform'."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, name=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: Name of the platform as returned by 'sys.platform'.
        """
        self.name = name
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        dct = {}
        if name is not None:
            dct["name"] = name
        dct.update(self.kwargs)
        return dct


@register
class PydevdProcessInfo(BaseSchema):
    """
    This object contains python process details.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "pid": {"type": "integer", "description": "Process ID for the current process."},
        "ppid": {"type": "integer", "description": "Parent Process ID for the current process."},
        "executable": {"type": "string", "description": "Path to the executable as returned by 'sys.executable'."},
        "bitness": {"type": "integer", "description": "Integer value indicating the bitness of the current process."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, pid=None, ppid=None, executable=None, bitness=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer pid: Process ID for the current process.
        :param integer ppid: Parent Process ID for the current process.
        :param string executable: Path to the executable as returned by 'sys.executable'.
        :param integer bitness: Integer value indicating the bitness of the current process.
        """
        self.pid = pid
        self.ppid = ppid
        self.executable = executable
        self.bitness = bitness
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        pid = self.pid
        ppid = self.ppid
        executable = self.executable
        bitness = self.bitness
        dct = {}
        if pid is not None:
            dct["pid"] = pid
        if ppid is not None:
            dct["ppid"] = ppid
        if executable is not None:
            dct["executable"] = executable
        if bitness is not None:
            dct["bitness"] = bitness
        dct.update(self.kwargs)
        return dct


@register
class PydevdInfo(BaseSchema):
    """
    This object contains details on pydevd.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "usingCython": {"type": "boolean", "description": "Specifies whether the cython native module is being used."},
        "usingFrameEval": {"type": "boolean", "description": "Specifies whether the frame eval native module is being used."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, usingCython=None, usingFrameEval=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean usingCython: Specifies whether the cython native module is being used.
        :param boolean usingFrameEval: Specifies whether the frame eval native module is being used.
        """
        self.usingCython = usingCython
        self.usingFrameEval = usingFrameEval
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        usingCython = self.usingCython
        usingFrameEval = self.usingFrameEval
        dct = {}
        if usingCython is not None:
            dct["usingCython"] = usingCython
        if usingFrameEval is not None:
            dct["usingFrameEval"] = usingFrameEval
        dct.update(self.kwargs)
        return dct


@register_request("pydevdAuthorize")
@register
class PydevdAuthorizeRequest(BaseSchema):
    """
    A request to authorize the ide to start accepting commands.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["request"]},
        "command": {"type": "string", "enum": ["pydevdAuthorize"]},
        "arguments": {"type": "PydevdAuthorizeArguments"},
    }
    __refs__ = set(["arguments"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, arguments, seq=-1, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param string command:
        :param PydevdAuthorizeArguments arguments:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        """
        self.type = "request"
        self.command = "pydevdAuthorize"
        if arguments is None:
            self.arguments = PydevdAuthorizeArguments()
        else:
            self.arguments = (
                PydevdAuthorizeArguments(update_ids_from_dap=update_ids_from_dap, **arguments)
                if arguments.__class__ != PydevdAuthorizeArguments
                else arguments
            )
        self.seq = seq
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        command = self.command
        arguments = self.arguments
        seq = self.seq
        dct = {
            "type": type,
            "command": command,
            "arguments": arguments.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        dct.update(self.kwargs)
        return dct


@register
class PydevdAuthorizeArguments(BaseSchema):
    """
    Arguments for 'pydevdAuthorize' request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"debugServerAccessToken": {"type": "string", "description": "The access token to access the debug server."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, debugServerAccessToken=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string debugServerAccessToken: The access token to access the debug server.
        """
        self.debugServerAccessToken = debugServerAccessToken
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        debugServerAccessToken = self.debugServerAccessToken
        dct = {}
        if debugServerAccessToken is not None:
            dct["debugServerAccessToken"] = debugServerAccessToken
        dct.update(self.kwargs)
        return dct


@register_response("pydevdAuthorize")
@register
class PydevdAuthorizeResponse(BaseSchema):
    """
    Response to 'pydevdAuthorize' request.

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "seq": {
            "type": "integer",
            "description": "Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.",
        },
        "type": {"type": "string", "enum": ["response"]},
        "request_seq": {"type": "integer", "description": "Sequence number of the corresponding request."},
        "success": {
            "type": "boolean",
            "description": "Outcome of the request.\nIf True, the request was successful and the `body` attribute may contain the result of the request.\nIf the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).",
        },
        "command": {"type": "string", "description": "The command requested."},
        "message": {
            "type": "string",
            "description": "Contains the raw error in short form if `success` is false.\nThis raw error might be interpreted by the client and is not shown in the UI.\nSome predefined values exist.",
            "_enum": ["cancelled", "notStopped"],
            "enumDescriptions": ["the request was cancelled.", "the request may be retried once the adapter is in a 'stopped' state."],
        },
        "body": {
            "type": "object",
            "properties": {
                "clientAccessToken": {"type": "string", "description": "The access token to access the client (i.e.: usually the IDE)."}
            },
            "required": ["clientAccessToken"],
        },
    }
    __refs__ = set(["body"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, request_seq, success, command, body, seq=-1, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string type:
        :param integer request_seq: Sequence number of the corresponding request.
        :param boolean success: Outcome of the request.
        If true, the request was successful and the `body` attribute may contain the result of the request.
        If the value is false, the attribute `message` contains the error in short form and the `body` may contain additional information (see `ErrorResponse.body.error`).
        :param string command: The command requested.
        :param PydevdAuthorizeResponseBody body:
        :param integer seq: Sequence number of the message (also known as message ID). The `seq` for the first message sent by a client or debug adapter is 1, and for each subsequent message is 1 greater than the previous message sent by that actor. `seq` can be used to order requests, responses, and events, and to associate requests with their corresponding responses. For protocol messages of type `request` the sequence number can be used to cancel the request.
        :param string message: Contains the raw error in short form if `success` is false.
        This raw error might be interpreted by the client and is not shown in the UI.
        Some predefined values exist.
        """
        self.type = "response"
        self.request_seq = request_seq
        self.success = success
        self.command = command
        if body is None:
            self.body = PydevdAuthorizeResponseBody()
        else:
            self.body = (
                PydevdAuthorizeResponseBody(update_ids_from_dap=update_ids_from_dap, **body)
                if body.__class__ != PydevdAuthorizeResponseBody
                else body
            )
        self.seq = seq
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        type = self.type  # noqa (assign to builtin)
        request_seq = self.request_seq
        success = self.success
        command = self.command
        body = self.body
        seq = self.seq
        message = self.message
        dct = {
            "type": type,
            "request_seq": request_seq,
            "success": success,
            "command": command,
            "body": body.to_dict(update_ids_to_dap=update_ids_to_dap),
            "seq": seq,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register
class ErrorResponseBody(BaseSchema):
    """
    "body" of ErrorResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"error": {"description": "A structured error message.", "type": "Message"}}
    __refs__ = set(["error"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, error=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param Message error: A structured error message.
        """
        if error is None:
            self.error = Message()
        else:
            self.error = Message(update_ids_from_dap=update_ids_from_dap, **error) if error.__class__ != Message else error
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        error = self.error
        dct = {}
        if error is not None:
            dct["error"] = error.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class StoppedEventBody(BaseSchema):
    """
    "body" of StoppedEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "reason": {
            "type": "string",
            "description": "The reason for the event.\nFor backward compatibility this string is shown in the UI if the `description` attribute is missing (but it must not be translated).",
            "_enum": [
                "step",
                "breakpoint",
                "exception",
                "pause",
                "entry",
                "goto",
                "function breakpoint",
                "data breakpoint",
                "instruction breakpoint",
            ],
        },
        "description": {
            "type": "string",
            "description": "The full reason for the event, e.g. 'Paused on exception'. This string is shown in the UI as is and can be translated.",
        },
        "threadId": {"type": "integer", "description": "The thread which was stopped."},
        "preserveFocusHint": {
            "type": "boolean",
            "description": "A value of True hints to the client that this event should not change the focus.",
        },
        "text": {
            "type": "string",
            "description": "Additional information. E.g. if reason is `exception`, text contains the exception name. This string is shown in the UI.",
        },
        "allThreadsStopped": {
            "type": "boolean",
            "description": "If `allThreadsStopped` is True, a debug adapter can announce that all threads have stopped.\n- The client should use this information to enable that all threads can be expanded to access their stacktraces.\n- If the attribute is missing or false, only the thread with the given `threadId` can be expanded.",
        },
        "hitBreakpointIds": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Ids of the breakpoints that triggered the event. In most cases there is only a single breakpoint but here are some examples for multiple breakpoints:\n- Different types of breakpoints map to the same location.\n- Multiple source breakpoints get collapsed to the same instruction by the compiler/runtime.\n- Multiple function breakpoints with different function names map to the same location.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        reason,
        description=None,
        threadId=None,
        preserveFocusHint=None,
        text=None,
        allThreadsStopped=None,
        hitBreakpointIds=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string reason: The reason for the event.
        For backward compatibility this string is shown in the UI if the `description` attribute is missing (but it must not be translated).
        :param string description: The full reason for the event, e.g. 'Paused on exception'. This string is shown in the UI as is and can be translated.
        :param integer threadId: The thread which was stopped.
        :param boolean preserveFocusHint: A value of true hints to the client that this event should not change the focus.
        :param string text: Additional information. E.g. if reason is `exception`, text contains the exception name. This string is shown in the UI.
        :param boolean allThreadsStopped: If `allThreadsStopped` is true, a debug adapter can announce that all threads have stopped.
        - The client should use this information to enable that all threads can be expanded to access their stacktraces.
        - If the attribute is missing or false, only the thread with the given `threadId` can be expanded.
        :param array hitBreakpointIds: Ids of the breakpoints that triggered the event. In most cases there is only a single breakpoint but here are some examples for multiple breakpoints:
        - Different types of breakpoints map to the same location.
        - Multiple source breakpoints get collapsed to the same instruction by the compiler/runtime.
        - Multiple function breakpoints with different function names map to the same location.
        """
        self.reason = reason
        self.description = description
        self.threadId = threadId
        self.preserveFocusHint = preserveFocusHint
        self.text = text
        self.allThreadsStopped = allThreadsStopped
        self.hitBreakpointIds = hitBreakpointIds
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        reason = self.reason
        description = self.description
        threadId = self.threadId
        preserveFocusHint = self.preserveFocusHint
        text = self.text
        allThreadsStopped = self.allThreadsStopped
        hitBreakpointIds = self.hitBreakpointIds
        if hitBreakpointIds and hasattr(hitBreakpointIds[0], "to_dict"):
            hitBreakpointIds = [x.to_dict() for x in hitBreakpointIds]
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "reason": reason,
        }
        if description is not None:
            dct["description"] = description
        if threadId is not None:
            dct["threadId"] = threadId
        if preserveFocusHint is not None:
            dct["preserveFocusHint"] = preserveFocusHint
        if text is not None:
            dct["text"] = text
        if allThreadsStopped is not None:
            dct["allThreadsStopped"] = allThreadsStopped
        if hitBreakpointIds is not None:
            dct["hitBreakpointIds"] = hitBreakpointIds
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register
class ContinuedEventBody(BaseSchema):
    """
    "body" of ContinuedEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "threadId": {"type": "integer", "description": "The thread which was continued."},
        "allThreadsContinued": {
            "type": "boolean",
            "description": "If `allThreadsContinued` is True, a debug adapter can announce that all threads have continued.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threadId, allThreadsContinued=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer threadId: The thread which was continued.
        :param boolean allThreadsContinued: If `allThreadsContinued` is true, a debug adapter can announce that all threads have continued.
        """
        self.threadId = threadId
        self.allThreadsContinued = allThreadsContinued
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threadId = self.threadId
        allThreadsContinued = self.allThreadsContinued
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "threadId": threadId,
        }
        if allThreadsContinued is not None:
            dct["allThreadsContinued"] = allThreadsContinued
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register
class ExitedEventBody(BaseSchema):
    """
    "body" of ExitedEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"exitCode": {"type": "integer", "description": "The exit code returned from the debuggee."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, exitCode, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer exitCode: The exit code returned from the debuggee.
        """
        self.exitCode = exitCode
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        exitCode = self.exitCode
        dct = {
            "exitCode": exitCode,
        }
        dct.update(self.kwargs)
        return dct


@register
class TerminatedEventBody(BaseSchema):
    """
    "body" of TerminatedEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "restart": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "A debug adapter may set `restart` to True (or to an arbitrary object) to request that the client restarts the session.\nThe value is not interpreted by the client and passed unmodified as an attribute `__restart` to the `launch` and `attach` requests.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, restart=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] restart: A debug adapter may set `restart` to true (or to an arbitrary object) to request that the client restarts the session.
        The value is not interpreted by the client and passed unmodified as an attribute `__restart` to the `launch` and `attach` requests.
        """
        self.restart = restart
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        restart = self.restart
        dct = {}
        if restart is not None:
            dct["restart"] = restart
        dct.update(self.kwargs)
        return dct


@register
class ThreadEventBody(BaseSchema):
    """
    "body" of ThreadEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "reason": {"type": "string", "description": "The reason for the event.", "_enum": ["started", "exited"]},
        "threadId": {"type": "integer", "description": "The identifier of the thread."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, reason, threadId, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string reason: The reason for the event.
        :param integer threadId: The identifier of the thread.
        """
        self.reason = reason
        self.threadId = threadId
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        reason = self.reason
        threadId = self.threadId
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {
            "reason": reason,
            "threadId": threadId,
        }
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register
class OutputEventBody(BaseSchema):
    """
    "body" of OutputEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "category": {
            "type": "string",
            "description": "The output category. If not specified or if the category is not understood by the client, `console` is assumed.",
            "_enum": ["console", "important", "stdout", "stderr", "telemetry"],
            "enumDescriptions": [
                "Show the output in the client's default message UI, e.g. a 'debug console'. This category should only be used for informational output from the debugger (as opposed to the debuggee).",
                "A hint for the client to show the output in the client's UI for important and highly visible information, e.g. as a popup notification. This category should only be used for important messages from the debugger (as opposed to the debuggee). Since this category value is a hint, clients might ignore the hint and assume the `console` category.",
                "Show the output as normal program output from the debuggee.",
                "Show the output as error program output from the debuggee.",
                "Send the output to telemetry instead of showing it to the user.",
            ],
        },
        "output": {"type": "string", "description": "The output to report."},
        "group": {
            "type": "string",
            "description": "Support for keeping an output log organized by grouping related messages.",
            "enum": ["start", "startCollapsed", "end"],
            "enumDescriptions": [
                "Start a new group in expanded mode. Subsequent output events are members of the group and should be shown indented.\nThe `output` attribute becomes the name of the group and is not indented.",
                "Start a new group in collapsed mode. Subsequent output events are members of the group and should be shown indented (as soon as the group is expanded).\nThe `output` attribute becomes the name of the group and is not indented.",
                "End the current group and decrease the indentation of subsequent output events.\nA non-empty `output` attribute is shown as the unindented end of the group.",
            ],
        },
        "variablesReference": {
            "type": "integer",
            "description": "If an attribute `variablesReference` exists and its value is > 0, the output contains objects which can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "source": {"description": "The source location where the output was produced.", "type": "Source"},
        "line": {"type": "integer", "description": "The source location's line where the output was produced."},
        "column": {
            "type": "integer",
            "description": "The position in `line` where the output was produced. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.",
        },
        "data": {
            "type": ["array", "boolean", "integer", "null", "number", "object", "string"],
            "description": "Additional data to report. For the `telemetry` category the data is sent to telemetry, for the other categories the data is shown in JSON format.",
        },
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        output,
        category=None,
        group=None,
        variablesReference=None,
        source=None,
        line=None,
        column=None,
        data=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string output: The output to report.
        :param string category: The output category. If not specified or if the category is not understood by the client, `console` is assumed.
        :param string group: Support for keeping an output log organized by grouping related messages.
        :param integer variablesReference: If an attribute `variablesReference` exists and its value is > 0, the output contains objects which can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.
        :param Source source: The source location where the output was produced.
        :param integer line: The source location's line where the output was produced.
        :param integer column: The position in `line` where the output was produced. It is measured in UTF-16 code units and the client capability `columnsStartAt1` determines whether it is 0- or 1-based.
        :param ['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'] data: Additional data to report. For the `telemetry` category the data is sent to telemetry, for the other categories the data is shown in JSON format.
        """
        self.output = output
        self.category = category
        self.group = group
        self.variablesReference = variablesReference
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.line = line
        self.column = column
        self.data = data
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        output = self.output
        category = self.category
        group = self.group
        variablesReference = self.variablesReference
        source = self.source
        line = self.line
        column = self.column
        data = self.data
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "output": output,
        }
        if category is not None:
            dct["category"] = category
        if group is not None:
            dct["group"] = group
        if variablesReference is not None:
            dct["variablesReference"] = variablesReference
        if source is not None:
            dct["source"] = source.to_dict(update_ids_to_dap=update_ids_to_dap)
        if line is not None:
            dct["line"] = line
        if column is not None:
            dct["column"] = column
        if data is not None:
            dct["data"] = data
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register
class BreakpointEventBody(BaseSchema):
    """
    "body" of BreakpointEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "reason": {"type": "string", "description": "The reason for the event.", "_enum": ["changed", "new", "removed"]},
        "breakpoint": {
            "description": "The `id` attribute is used to find the target breakpoint, the other attributes are used as the new values.",
            "type": "Breakpoint",
        },
    }
    __refs__ = set(["breakpoint"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, reason, breakpoint, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string reason: The reason for the event.
        :param Breakpoint breakpoint: The `id` attribute is used to find the target breakpoint, the other attributes are used as the new values.
        """
        self.reason = reason
        if breakpoint is None:
            self.breakpoint = Breakpoint()
        else:
            self.breakpoint = (
                Breakpoint(update_ids_from_dap=update_ids_from_dap, **breakpoint) if breakpoint.__class__ != Breakpoint else breakpoint
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        reason = self.reason
        breakpoint = self.breakpoint  # noqa (assign to builtin)
        dct = {
            "reason": reason,
            "breakpoint": breakpoint.to_dict(update_ids_to_dap=update_ids_to_dap),
        }
        dct.update(self.kwargs)
        return dct


@register
class ModuleEventBody(BaseSchema):
    """
    "body" of ModuleEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "reason": {"type": "string", "description": "The reason for the event.", "enum": ["new", "changed", "removed"]},
        "module": {
            "description": "The new, changed, or removed module. In case of `removed` only the module id is used.",
            "type": "Module",
        },
    }
    __refs__ = set(["module"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, reason, module, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string reason: The reason for the event.
        :param Module module: The new, changed, or removed module. In case of `removed` only the module id is used.
        """
        self.reason = reason
        if module is None:
            self.module = Module()
        else:
            self.module = Module(update_ids_from_dap=update_ids_from_dap, **module) if module.__class__ != Module else module
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        reason = self.reason
        module = self.module
        dct = {
            "reason": reason,
            "module": module.to_dict(update_ids_to_dap=update_ids_to_dap),
        }
        dct.update(self.kwargs)
        return dct


@register
class LoadedSourceEventBody(BaseSchema):
    """
    "body" of LoadedSourceEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "reason": {"type": "string", "description": "The reason for the event.", "enum": ["new", "changed", "removed"]},
        "source": {"description": "The new, changed, or removed source.", "type": "Source"},
    }
    __refs__ = set(["source"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, reason, source, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string reason: The reason for the event.
        :param Source source: The new, changed, or removed source.
        """
        self.reason = reason
        if source is None:
            self.source = Source()
        else:
            self.source = Source(update_ids_from_dap=update_ids_from_dap, **source) if source.__class__ != Source else source
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        reason = self.reason
        source = self.source
        dct = {
            "reason": reason,
            "source": source.to_dict(update_ids_to_dap=update_ids_to_dap),
        }
        dct.update(self.kwargs)
        return dct


@register
class ProcessEventBody(BaseSchema):
    """
    "body" of ProcessEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "name": {
            "type": "string",
            "description": "The logical name of the process. This is usually the full path to process's executable file. Example: /home/example/myproj/program.js.",
        },
        "systemProcessId": {
            "type": "integer",
            "description": "The system process id of the debugged process. This property is missing for non-system processes.",
        },
        "isLocalProcess": {"type": "boolean", "description": "If True, the process is running on the same computer as the debug adapter."},
        "startMethod": {
            "type": "string",
            "enum": ["launch", "attach", "attachForSuspendedLaunch"],
            "description": "Describes how the debug engine started debugging this process.",
            "enumDescriptions": [
                "Process was launched under the debugger.",
                "Debugger attached to an existing process.",
                "A project launcher component has launched a new process in a suspended state and then asked the debugger to attach.",
            ],
        },
        "pointerSize": {
            "type": "integer",
            "description": "The size of a pointer or address for this process, in bits. This value may be used by clients when formatting addresses for display.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self, name, systemProcessId=None, isLocalProcess=None, startMethod=None, pointerSize=None, update_ids_from_dap=False, **kwargs
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string name: The logical name of the process. This is usually the full path to process's executable file. Example: /home/example/myproj/program.js.
        :param integer systemProcessId: The system process id of the debugged process. This property is missing for non-system processes.
        :param boolean isLocalProcess: If true, the process is running on the same computer as the debug adapter.
        :param string startMethod: Describes how the debug engine started debugging this process.
        :param integer pointerSize: The size of a pointer or address for this process, in bits. This value may be used by clients when formatting addresses for display.
        """
        self.name = name
        self.systemProcessId = systemProcessId
        self.isLocalProcess = isLocalProcess
        self.startMethod = startMethod
        self.pointerSize = pointerSize
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        name = self.name
        systemProcessId = self.systemProcessId
        isLocalProcess = self.isLocalProcess
        startMethod = self.startMethod
        pointerSize = self.pointerSize
        dct = {
            "name": name,
        }
        if systemProcessId is not None:
            dct["systemProcessId"] = systemProcessId
        if isLocalProcess is not None:
            dct["isLocalProcess"] = isLocalProcess
        if startMethod is not None:
            dct["startMethod"] = startMethod
        if pointerSize is not None:
            dct["pointerSize"] = pointerSize
        dct.update(self.kwargs)
        return dct


@register
class CapabilitiesEventBody(BaseSchema):
    """
    "body" of CapabilitiesEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"capabilities": {"description": "The set of updated capabilities.", "type": "Capabilities"}}
    __refs__ = set(["capabilities"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, capabilities, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param Capabilities capabilities: The set of updated capabilities.
        """
        if capabilities is None:
            self.capabilities = Capabilities()
        else:
            self.capabilities = (
                Capabilities(update_ids_from_dap=update_ids_from_dap, **capabilities)
                if capabilities.__class__ != Capabilities
                else capabilities
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        capabilities = self.capabilities
        dct = {
            "capabilities": capabilities.to_dict(update_ids_to_dap=update_ids_to_dap),
        }
        dct.update(self.kwargs)
        return dct


@register
class ProgressStartEventBody(BaseSchema):
    """
    "body" of ProgressStartEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "progressId": {
            "type": "string",
            "description": "An ID that can be used in subsequent `progressUpdate` and `progressEnd` events to make them refer to the same progress reporting.\nIDs must be unique within a debug session.",
        },
        "title": {
            "type": "string",
            "description": "Short title of the progress reporting. Shown in the UI to describe the long running operation.",
        },
        "requestId": {
            "type": "integer",
            "description": "The request ID that this progress report is related to. If specified a debug adapter is expected to emit progress events for the long running request until the request has been either completed or cancelled.\nIf the request ID is omitted, the progress report is assumed to be related to some general activity of the debug adapter.",
        },
        "cancellable": {
            "type": "boolean",
            "description": "If True, the request that reports progress may be cancelled with a `cancel` request.\nSo this property basically controls whether the client should use UX that supports cancellation.\nClients that don't support cancellation are allowed to ignore the setting.",
        },
        "message": {"type": "string", "description": "More detailed progress message."},
        "percentage": {
            "type": "number",
            "description": "Progress percentage to display (value range: 0 to 100). If omitted no percentage is shown.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self, progressId, title, requestId=None, cancellable=None, message=None, percentage=None, update_ids_from_dap=False, **kwargs
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string progressId: An ID that can be used in subsequent `progressUpdate` and `progressEnd` events to make them refer to the same progress reporting.
        IDs must be unique within a debug session.
        :param string title: Short title of the progress reporting. Shown in the UI to describe the long running operation.
        :param integer requestId: The request ID that this progress report is related to. If specified a debug adapter is expected to emit progress events for the long running request until the request has been either completed or cancelled.
        If the request ID is omitted, the progress report is assumed to be related to some general activity of the debug adapter.
        :param boolean cancellable: If true, the request that reports progress may be cancelled with a `cancel` request.
        So this property basically controls whether the client should use UX that supports cancellation.
        Clients that don't support cancellation are allowed to ignore the setting.
        :param string message: More detailed progress message.
        :param number percentage: Progress percentage to display (value range: 0 to 100). If omitted no percentage is shown.
        """
        self.progressId = progressId
        self.title = title
        self.requestId = requestId
        self.cancellable = cancellable
        self.message = message
        self.percentage = percentage
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        progressId = self.progressId
        title = self.title
        requestId = self.requestId
        cancellable = self.cancellable
        message = self.message
        percentage = self.percentage
        dct = {
            "progressId": progressId,
            "title": title,
        }
        if requestId is not None:
            dct["requestId"] = requestId
        if cancellable is not None:
            dct["cancellable"] = cancellable
        if message is not None:
            dct["message"] = message
        if percentage is not None:
            dct["percentage"] = percentage
        dct.update(self.kwargs)
        return dct


@register
class ProgressUpdateEventBody(BaseSchema):
    """
    "body" of ProgressUpdateEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "progressId": {"type": "string", "description": "The ID that was introduced in the initial `progressStart` event."},
        "message": {"type": "string", "description": "More detailed progress message. If omitted, the previous message (if any) is used."},
        "percentage": {
            "type": "number",
            "description": "Progress percentage to display (value range: 0 to 100). If omitted no percentage is shown.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, progressId, message=None, percentage=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string progressId: The ID that was introduced in the initial `progressStart` event.
        :param string message: More detailed progress message. If omitted, the previous message (if any) is used.
        :param number percentage: Progress percentage to display (value range: 0 to 100). If omitted no percentage is shown.
        """
        self.progressId = progressId
        self.message = message
        self.percentage = percentage
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        progressId = self.progressId
        message = self.message
        percentage = self.percentage
        dct = {
            "progressId": progressId,
        }
        if message is not None:
            dct["message"] = message
        if percentage is not None:
            dct["percentage"] = percentage
        dct.update(self.kwargs)
        return dct


@register
class ProgressEndEventBody(BaseSchema):
    """
    "body" of ProgressEndEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "progressId": {"type": "string", "description": "The ID that was introduced in the initial `ProgressStartEvent`."},
        "message": {"type": "string", "description": "More detailed progress message. If omitted, the previous message (if any) is used."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, progressId, message=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string progressId: The ID that was introduced in the initial `ProgressStartEvent`.
        :param string message: More detailed progress message. If omitted, the previous message (if any) is used.
        """
        self.progressId = progressId
        self.message = message
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        progressId = self.progressId
        message = self.message
        dct = {
            "progressId": progressId,
        }
        if message is not None:
            dct["message"] = message
        dct.update(self.kwargs)
        return dct


@register
class InvalidatedEventBody(BaseSchema):
    """
    "body" of InvalidatedEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "areas": {
            "type": "array",
            "description": "Set of logical areas that got invalidated. This property has a hint characteristic: a client can only be expected to make a 'best effort' in honoring the areas but there are no guarantees. If this property is missing, empty, or if values are not understood, the client should assume a single value `all`.",
            "items": {"$ref": "#/definitions/InvalidatedAreas"},
        },
        "threadId": {"type": "integer", "description": "If specified, the client only needs to refetch data related to this thread."},
        "stackFrameId": {
            "type": "integer",
            "description": "If specified, the client only needs to refetch data related to this stack frame (and the `threadId` is ignored).",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, areas=None, threadId=None, stackFrameId=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array areas: Set of logical areas that got invalidated. This property has a hint characteristic: a client can only be expected to make a 'best effort' in honoring the areas but there are no guarantees. If this property is missing, empty, or if values are not understood, the client should assume a single value `all`.
        :param integer threadId: If specified, the client only needs to refetch data related to this thread.
        :param integer stackFrameId: If specified, the client only needs to refetch data related to this stack frame (and the `threadId` is ignored).
        """
        self.areas = areas
        if update_ids_from_dap and self.areas:
            for o in self.areas:
                InvalidatedAreas.update_dict_ids_from_dap(o)
        self.threadId = threadId
        self.stackFrameId = stackFrameId
        if update_ids_from_dap:
            self.threadId = self._translate_id_from_dap(self.threadId)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_from_dap(dct["threadId"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        areas = self.areas
        if areas and hasattr(areas[0], "to_dict"):
            areas = [x.to_dict() for x in areas]
        threadId = self.threadId
        stackFrameId = self.stackFrameId
        if update_ids_to_dap:
            if threadId is not None:
                threadId = self._translate_id_to_dap(threadId)
        dct = {}
        if areas is not None:
            dct["areas"] = [InvalidatedAreas.update_dict_ids_to_dap(o) for o in areas] if (update_ids_to_dap and areas) else areas
        if threadId is not None:
            dct["threadId"] = threadId
        if stackFrameId is not None:
            dct["stackFrameId"] = stackFrameId
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "threadId" in dct:
            dct["threadId"] = cls._translate_id_to_dap(dct["threadId"])
        return dct


@register
class MemoryEventBody(BaseSchema):
    """
    "body" of MemoryEvent

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "memoryReference": {"type": "string", "description": "Memory reference of a memory range that has been updated."},
        "offset": {"type": "integer", "description": "Starting offset in bytes where memory has been updated. Can be negative."},
        "count": {"type": "integer", "description": "Number of bytes updated."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, memoryReference, offset, count, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string memoryReference: Memory reference of a memory range that has been updated.
        :param integer offset: Starting offset in bytes where memory has been updated. Can be negative.
        :param integer count: Number of bytes updated.
        """
        self.memoryReference = memoryReference
        self.offset = offset
        self.count = count
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        memoryReference = self.memoryReference
        offset = self.offset
        count = self.count
        dct = {
            "memoryReference": memoryReference,
            "offset": offset,
            "count": count,
        }
        dct.update(self.kwargs)
        return dct


@register
class RunInTerminalRequestArgumentsEnv(BaseSchema):
    """
    "env" of RunInTerminalRequestArguments

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class RunInTerminalResponseBody(BaseSchema):
    """
    "body" of RunInTerminalResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "processId": {"type": "integer", "description": "The process ID. The value should be less than or equal to 2147483647 (2^31-1)."},
        "shellProcessId": {
            "type": "integer",
            "description": "The process ID of the terminal shell. The value should be less than or equal to 2147483647 (2^31-1).",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, processId=None, shellProcessId=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer processId: The process ID. The value should be less than or equal to 2147483647 (2^31-1).
        :param integer shellProcessId: The process ID of the terminal shell. The value should be less than or equal to 2147483647 (2^31-1).
        """
        self.processId = processId
        self.shellProcessId = shellProcessId
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        processId = self.processId
        shellProcessId = self.shellProcessId
        dct = {}
        if processId is not None:
            dct["processId"] = processId
        if shellProcessId is not None:
            dct["shellProcessId"] = shellProcessId
        dct.update(self.kwargs)
        return dct


@register
class StartDebuggingRequestArgumentsConfiguration(BaseSchema):
    """
    "configuration" of StartDebuggingRequestArguments

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class BreakpointLocationsResponseBody(BaseSchema):
    """
    "body" of BreakpointLocationsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/BreakpointLocation"},
            "description": "Sorted set of possible breakpoint locations.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: Sorted set of possible breakpoint locations.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                BreakpointLocation.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [BreakpointLocation.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetBreakpointsResponseBody(BaseSchema):
    """
    "body" of SetBreakpointsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/Breakpoint"},
            "description": "Information about the breakpoints.\nThe array elements are in the same order as the elements of the `breakpoints` (or the deprecated `lines`) array in the arguments.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: Information about the breakpoints.
        The array elements are in the same order as the elements of the `breakpoints` (or the deprecated `lines`) array in the arguments.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                Breakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [Breakpoint.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetFunctionBreakpointsResponseBody(BaseSchema):
    """
    "body" of SetFunctionBreakpointsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/Breakpoint"},
            "description": "Information about the breakpoints. The array elements correspond to the elements of the `breakpoints` array.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: Information about the breakpoints. The array elements correspond to the elements of the `breakpoints` array.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                Breakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [Breakpoint.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetExceptionBreakpointsResponseBody(BaseSchema):
    """
    "body" of SetExceptionBreakpointsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/Breakpoint"},
            "description": "Information about the exception breakpoints or filters.\nThe breakpoints returned are in the same order as the elements of the `filters`, `filterOptions`, `exceptionOptions` arrays in the arguments. If both `filters` and `filterOptions` are given, the returned array must start with `filters` information first, followed by `filterOptions` information.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: Information about the exception breakpoints or filters.
        The breakpoints returned are in the same order as the elements of the `filters`, `filterOptions`, `exceptionOptions` arrays in the arguments. If both `filters` and `filterOptions` are given, the returned array must start with `filters` information first, followed by `filterOptions` information.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                Breakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {}
        if breakpoints is not None:
            dct["breakpoints"] = (
                [Breakpoint.update_dict_ids_to_dap(o) for o in breakpoints] if (update_ids_to_dap and breakpoints) else breakpoints
            )
        dct.update(self.kwargs)
        return dct


@register
class DataBreakpointInfoResponseBody(BaseSchema):
    """
    "body" of DataBreakpointInfoResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "dataId": {
            "type": ["string", "null"],
            "description": "An identifier for the data on which a data breakpoint can be registered with the `setDataBreakpoints` request or null if no data breakpoint is available. If a `variablesReference` or `frameId` is passed, the `dataId` is valid in the current suspended state, otherwise it's valid indefinitely. See 'Lifetime of Object References' in the Overview section for details. Breakpoints set using the `dataId` in the `setDataBreakpoints` request may outlive the lifetime of the associated `dataId`.",
        },
        "description": {
            "type": "string",
            "description": "UI string that describes on what data the breakpoint is set on or why a data breakpoint is not available.",
        },
        "accessTypes": {
            "type": "array",
            "items": {"$ref": "#/definitions/DataBreakpointAccessType"},
            "description": "Attribute lists the available access types for a potential data breakpoint. A UI client could surface this information.",
        },
        "canPersist": {
            "type": "boolean",
            "description": "Attribute indicates that a potential data breakpoint could be persisted across sessions.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, dataId, description, accessTypes=None, canPersist=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param ['string', 'null'] dataId: An identifier for the data on which a data breakpoint can be registered with the `setDataBreakpoints` request or null if no data breakpoint is available. If a `variablesReference` or `frameId` is passed, the `dataId` is valid in the current suspended state, otherwise it's valid indefinitely. See 'Lifetime of Object References' in the Overview section for details. Breakpoints set using the `dataId` in the `setDataBreakpoints` request may outlive the lifetime of the associated `dataId`.
        :param string description: UI string that describes on what data the breakpoint is set on or why a data breakpoint is not available.
        :param array accessTypes: Attribute lists the available access types for a potential data breakpoint. A UI client could surface this information.
        :param boolean canPersist: Attribute indicates that a potential data breakpoint could be persisted across sessions.
        """
        self.dataId = dataId
        self.description = description
        self.accessTypes = accessTypes
        if update_ids_from_dap and self.accessTypes:
            for o in self.accessTypes:
                DataBreakpointAccessType.update_dict_ids_from_dap(o)
        self.canPersist = canPersist
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dataId = self.dataId
        description = self.description
        accessTypes = self.accessTypes
        if accessTypes and hasattr(accessTypes[0], "to_dict"):
            accessTypes = [x.to_dict() for x in accessTypes]
        canPersist = self.canPersist
        dct = {
            "dataId": dataId,
            "description": description,
        }
        if accessTypes is not None:
            dct["accessTypes"] = (
                [DataBreakpointAccessType.update_dict_ids_to_dap(o) for o in accessTypes]
                if (update_ids_to_dap and accessTypes)
                else accessTypes
            )
        if canPersist is not None:
            dct["canPersist"] = canPersist
        dct.update(self.kwargs)
        return dct


@register
class SetDataBreakpointsResponseBody(BaseSchema):
    """
    "body" of SetDataBreakpointsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/Breakpoint"},
            "description": "Information about the data breakpoints. The array elements correspond to the elements of the input argument `breakpoints` array.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: Information about the data breakpoints. The array elements correspond to the elements of the input argument `breakpoints` array.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                Breakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [Breakpoint.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetInstructionBreakpointsResponseBody(BaseSchema):
    """
    "body" of SetInstructionBreakpointsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "breakpoints": {
            "type": "array",
            "items": {"$ref": "#/definitions/Breakpoint"},
            "description": "Information about the breakpoints. The array elements correspond to the elements of the `breakpoints` array.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, breakpoints, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array breakpoints: Information about the breakpoints. The array elements correspond to the elements of the `breakpoints` array.
        """
        self.breakpoints = breakpoints
        if update_ids_from_dap and self.breakpoints:
            for o in self.breakpoints:
                Breakpoint.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        breakpoints = self.breakpoints
        if breakpoints and hasattr(breakpoints[0], "to_dict"):
            breakpoints = [x.to_dict() for x in breakpoints]
        dct = {
            "breakpoints": [Breakpoint.update_dict_ids_to_dap(o) for o in breakpoints]
            if (update_ids_to_dap and breakpoints)
            else breakpoints,
        }
        dct.update(self.kwargs)
        return dct


@register
class ContinueResponseBody(BaseSchema):
    """
    "body" of ContinueResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "allThreadsContinued": {
            "type": "boolean",
            "description": "The value True (or a missing property) signals to the client that all threads have been resumed. The value false indicates that not all threads were resumed.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, allThreadsContinued=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param boolean allThreadsContinued: The value true (or a missing property) signals to the client that all threads have been resumed. The value false indicates that not all threads were resumed.
        """
        self.allThreadsContinued = allThreadsContinued
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        allThreadsContinued = self.allThreadsContinued
        dct = {}
        if allThreadsContinued is not None:
            dct["allThreadsContinued"] = allThreadsContinued
        dct.update(self.kwargs)
        return dct


@register
class StackTraceResponseBody(BaseSchema):
    """
    "body" of StackTraceResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "stackFrames": {
            "type": "array",
            "items": {"$ref": "#/definitions/StackFrame"},
            "description": "The frames of the stack frame. If the array has length zero, there are no stack frames available.\nThis means that there is no location information available.",
        },
        "totalFrames": {
            "type": "integer",
            "description": "The total number of frames available in the stack. If omitted or if `totalFrames` is larger than the available frames, a client is expected to request frames until a request returns less frames than requested (which indicates the end of the stack). Returning monotonically increasing `totalFrames` values for subsequent requests can be used to enforce paging in the client.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, stackFrames, totalFrames=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array stackFrames: The frames of the stack frame. If the array has length zero, there are no stack frames available.
        This means that there is no location information available.
        :param integer totalFrames: The total number of frames available in the stack. If omitted or if `totalFrames` is larger than the available frames, a client is expected to request frames until a request returns less frames than requested (which indicates the end of the stack). Returning monotonically increasing `totalFrames` values for subsequent requests can be used to enforce paging in the client.
        """
        self.stackFrames = stackFrames
        if update_ids_from_dap and self.stackFrames:
            for o in self.stackFrames:
                StackFrame.update_dict_ids_from_dap(o)
        self.totalFrames = totalFrames
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        stackFrames = self.stackFrames
        if stackFrames and hasattr(stackFrames[0], "to_dict"):
            stackFrames = [x.to_dict() for x in stackFrames]
        totalFrames = self.totalFrames
        dct = {
            "stackFrames": [StackFrame.update_dict_ids_to_dap(o) for o in stackFrames]
            if (update_ids_to_dap and stackFrames)
            else stackFrames,
        }
        if totalFrames is not None:
            dct["totalFrames"] = totalFrames
        dct.update(self.kwargs)
        return dct


@register
class ScopesResponseBody(BaseSchema):
    """
    "body" of ScopesResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "scopes": {
            "type": "array",
            "items": {"$ref": "#/definitions/Scope"},
            "description": "The scopes of the stack frame. If the array has length zero, there are no scopes available.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, scopes, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array scopes: The scopes of the stack frame. If the array has length zero, there are no scopes available.
        """
        self.scopes = scopes
        if update_ids_from_dap and self.scopes:
            for o in self.scopes:
                Scope.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        scopes = self.scopes
        if scopes and hasattr(scopes[0], "to_dict"):
            scopes = [x.to_dict() for x in scopes]
        dct = {
            "scopes": [Scope.update_dict_ids_to_dap(o) for o in scopes] if (update_ids_to_dap and scopes) else scopes,
        }
        dct.update(self.kwargs)
        return dct


@register
class VariablesResponseBody(BaseSchema):
    """
    "body" of VariablesResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "variables": {
            "type": "array",
            "items": {"$ref": "#/definitions/Variable"},
            "description": "All (or a range) of variables for the given variable reference.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, variables, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array variables: All (or a range) of variables for the given variable reference.
        """
        self.variables = variables
        if update_ids_from_dap and self.variables:
            for o in self.variables:
                Variable.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        variables = self.variables
        if variables and hasattr(variables[0], "to_dict"):
            variables = [x.to_dict() for x in variables]
        dct = {
            "variables": [Variable.update_dict_ids_to_dap(o) for o in variables] if (update_ids_to_dap and variables) else variables,
        }
        dct.update(self.kwargs)
        return dct


@register
class SetVariableResponseBody(BaseSchema):
    """
    "body" of SetVariableResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "value": {"type": "string", "description": "The new value of the variable."},
        "type": {"type": "string", "description": "The type of the new value. Typically shown in the UI when hovering over the value."},
        "variablesReference": {
            "type": "integer",
            "description": "If `variablesReference` is > 0, the new value is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "namedVariables": {
            "type": "integer",
            "description": "The number of named child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
        },
        "indexedVariables": {
            "type": "integer",
            "description": "The number of indexed child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
        },
        "memoryReference": {
            "type": "string",
            "description": "A memory reference to a location appropriate for this result.\nFor pointer type eval results, this is generally a reference to the memory address contained in the pointer.\nThis attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is True.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        value,
        type=None,
        variablesReference=None,
        namedVariables=None,
        indexedVariables=None,
        memoryReference=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string value: The new value of the variable.
        :param string type: The type of the new value. Typically shown in the UI when hovering over the value.
        :param integer variablesReference: If `variablesReference` is > 0, the new value is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.
        :param integer namedVariables: The number of named child variables.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        The value should be less than or equal to 2147483647 (2^31-1).
        :param integer indexedVariables: The number of indexed child variables.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        The value should be less than or equal to 2147483647 (2^31-1).
        :param string memoryReference: A memory reference to a location appropriate for this result.
        For pointer type eval results, this is generally a reference to the memory address contained in the pointer.
        This attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is true.
        """
        self.value = value
        self.type = type
        self.variablesReference = variablesReference
        self.namedVariables = namedVariables
        self.indexedVariables = indexedVariables
        self.memoryReference = memoryReference
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        value = self.value
        type = self.type  # noqa (assign to builtin)
        variablesReference = self.variablesReference
        namedVariables = self.namedVariables
        indexedVariables = self.indexedVariables
        memoryReference = self.memoryReference
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "value": value,
        }
        if type is not None:
            dct["type"] = type
        if variablesReference is not None:
            dct["variablesReference"] = variablesReference
        if namedVariables is not None:
            dct["namedVariables"] = namedVariables
        if indexedVariables is not None:
            dct["indexedVariables"] = indexedVariables
        if memoryReference is not None:
            dct["memoryReference"] = memoryReference
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register
class SourceResponseBody(BaseSchema):
    """
    "body" of SourceResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "content": {"type": "string", "description": "Content of the source reference."},
        "mimeType": {"type": "string", "description": "Content type (MIME type) of the source."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, content, mimeType=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string content: Content of the source reference.
        :param string mimeType: Content type (MIME type) of the source.
        """
        self.content = content
        self.mimeType = mimeType
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        content = self.content
        mimeType = self.mimeType
        dct = {
            "content": content,
        }
        if mimeType is not None:
            dct["mimeType"] = mimeType
        dct.update(self.kwargs)
        return dct


@register
class ThreadsResponseBody(BaseSchema):
    """
    "body" of ThreadsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"threads": {"type": "array", "items": {"$ref": "#/definitions/Thread"}, "description": "All threads."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, threads, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array threads: All threads.
        """
        self.threads = threads
        if update_ids_from_dap and self.threads:
            for o in self.threads:
                Thread.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        threads = self.threads
        if threads and hasattr(threads[0], "to_dict"):
            threads = [x.to_dict() for x in threads]
        dct = {
            "threads": [Thread.update_dict_ids_to_dap(o) for o in threads] if (update_ids_to_dap and threads) else threads,
        }
        dct.update(self.kwargs)
        return dct


@register
class ModulesResponseBody(BaseSchema):
    """
    "body" of ModulesResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "modules": {"type": "array", "items": {"$ref": "#/definitions/Module"}, "description": "All modules or range of modules."},
        "totalModules": {"type": "integer", "description": "The total number of modules available."},
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, modules, totalModules=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array modules: All modules or range of modules.
        :param integer totalModules: The total number of modules available.
        """
        self.modules = modules
        if update_ids_from_dap and self.modules:
            for o in self.modules:
                Module.update_dict_ids_from_dap(o)
        self.totalModules = totalModules
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        modules = self.modules
        if modules and hasattr(modules[0], "to_dict"):
            modules = [x.to_dict() for x in modules]
        totalModules = self.totalModules
        dct = {
            "modules": [Module.update_dict_ids_to_dap(o) for o in modules] if (update_ids_to_dap and modules) else modules,
        }
        if totalModules is not None:
            dct["totalModules"] = totalModules
        dct.update(self.kwargs)
        return dct


@register
class LoadedSourcesResponseBody(BaseSchema):
    """
    "body" of LoadedSourcesResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"sources": {"type": "array", "items": {"$ref": "#/definitions/Source"}, "description": "Set of loaded sources."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, sources, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array sources: Set of loaded sources.
        """
        self.sources = sources
        if update_ids_from_dap and self.sources:
            for o in self.sources:
                Source.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        sources = self.sources
        if sources and hasattr(sources[0], "to_dict"):
            sources = [x.to_dict() for x in sources]
        dct = {
            "sources": [Source.update_dict_ids_to_dap(o) for o in sources] if (update_ids_to_dap and sources) else sources,
        }
        dct.update(self.kwargs)
        return dct


@register
class EvaluateResponseBody(BaseSchema):
    """
    "body" of EvaluateResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "result": {"type": "string", "description": "The result of the evaluate request."},
        "type": {
            "type": "string",
            "description": "The type of the evaluate result.\nThis attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is True.",
        },
        "presentationHint": {
            "description": "Properties of an evaluate result that can be used to determine how to render the result in the UI.",
            "type": "VariablePresentationHint",
        },
        "variablesReference": {
            "type": "integer",
            "description": "If `variablesReference` is > 0, the evaluate result is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "namedVariables": {
            "type": "integer",
            "description": "The number of named child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
        },
        "indexedVariables": {
            "type": "integer",
            "description": "The number of indexed child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
        },
        "memoryReference": {
            "type": "string",
            "description": "A memory reference to a location appropriate for this result.\nFor pointer type eval results, this is generally a reference to the memory address contained in the pointer.\nThis attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is True.",
        },
    }
    __refs__ = set(["presentationHint"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        result,
        variablesReference,
        type=None,
        presentationHint=None,
        namedVariables=None,
        indexedVariables=None,
        memoryReference=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string result: The result of the evaluate request.
        :param integer variablesReference: If `variablesReference` is > 0, the evaluate result is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.
        :param string type: The type of the evaluate result.
        This attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is true.
        :param VariablePresentationHint presentationHint: Properties of an evaluate result that can be used to determine how to render the result in the UI.
        :param integer namedVariables: The number of named child variables.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        The value should be less than or equal to 2147483647 (2^31-1).
        :param integer indexedVariables: The number of indexed child variables.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        The value should be less than or equal to 2147483647 (2^31-1).
        :param string memoryReference: A memory reference to a location appropriate for this result.
        For pointer type eval results, this is generally a reference to the memory address contained in the pointer.
        This attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is true.
        """
        self.result = result
        self.variablesReference = variablesReference
        self.type = type
        if presentationHint is None:
            self.presentationHint = VariablePresentationHint()
        else:
            self.presentationHint = (
                VariablePresentationHint(update_ids_from_dap=update_ids_from_dap, **presentationHint)
                if presentationHint.__class__ != VariablePresentationHint
                else presentationHint
            )
        self.namedVariables = namedVariables
        self.indexedVariables = indexedVariables
        self.memoryReference = memoryReference
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        result = self.result
        variablesReference = self.variablesReference
        type = self.type  # noqa (assign to builtin)
        presentationHint = self.presentationHint
        namedVariables = self.namedVariables
        indexedVariables = self.indexedVariables
        memoryReference = self.memoryReference
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "result": result,
            "variablesReference": variablesReference,
        }
        if type is not None:
            dct["type"] = type
        if presentationHint is not None:
            dct["presentationHint"] = presentationHint.to_dict(update_ids_to_dap=update_ids_to_dap)
        if namedVariables is not None:
            dct["namedVariables"] = namedVariables
        if indexedVariables is not None:
            dct["indexedVariables"] = indexedVariables
        if memoryReference is not None:
            dct["memoryReference"] = memoryReference
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register
class SetExpressionResponseBody(BaseSchema):
    """
    "body" of SetExpressionResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "value": {"type": "string", "description": "The new value of the expression."},
        "type": {
            "type": "string",
            "description": "The type of the value.\nThis attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is True.",
        },
        "presentationHint": {
            "description": "Properties of a value that can be used to determine how to render the result in the UI.",
            "type": "VariablePresentationHint",
        },
        "variablesReference": {
            "type": "integer",
            "description": "If `variablesReference` is > 0, the evaluate result is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.",
        },
        "namedVariables": {
            "type": "integer",
            "description": "The number of named child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
        },
        "indexedVariables": {
            "type": "integer",
            "description": "The number of indexed child variables.\nThe client can use this information to present the variables in a paged UI and fetch them in chunks.\nThe value should be less than or equal to 2147483647 (2^31-1).",
        },
        "memoryReference": {
            "type": "string",
            "description": "A memory reference to a location appropriate for this result.\nFor pointer type eval results, this is generally a reference to the memory address contained in the pointer.\nThis attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is True.",
        },
    }
    __refs__ = set(["presentationHint"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(
        self,
        value,
        type=None,
        presentationHint=None,
        variablesReference=None,
        namedVariables=None,
        indexedVariables=None,
        memoryReference=None,
        update_ids_from_dap=False,
        **kwargs,
    ):  # noqa (update_ids_from_dap may be unused)
        """
        :param string value: The new value of the expression.
        :param string type: The type of the value.
        This attribute should only be returned by a debug adapter if the corresponding capability `supportsVariableType` is true.
        :param VariablePresentationHint presentationHint: Properties of a value that can be used to determine how to render the result in the UI.
        :param integer variablesReference: If `variablesReference` is > 0, the evaluate result is structured and its children can be retrieved by passing `variablesReference` to the `variables` request as long as execution remains suspended. See 'Lifetime of Object References' in the Overview section for details.
        :param integer namedVariables: The number of named child variables.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        The value should be less than or equal to 2147483647 (2^31-1).
        :param integer indexedVariables: The number of indexed child variables.
        The client can use this information to present the variables in a paged UI and fetch them in chunks.
        The value should be less than or equal to 2147483647 (2^31-1).
        :param string memoryReference: A memory reference to a location appropriate for this result.
        For pointer type eval results, this is generally a reference to the memory address contained in the pointer.
        This attribute may be returned by a debug adapter if corresponding capability `supportsMemoryReferences` is true.
        """
        self.value = value
        self.type = type
        if presentationHint is None:
            self.presentationHint = VariablePresentationHint()
        else:
            self.presentationHint = (
                VariablePresentationHint(update_ids_from_dap=update_ids_from_dap, **presentationHint)
                if presentationHint.__class__ != VariablePresentationHint
                else presentationHint
            )
        self.variablesReference = variablesReference
        self.namedVariables = namedVariables
        self.indexedVariables = indexedVariables
        self.memoryReference = memoryReference
        if update_ids_from_dap:
            self.variablesReference = self._translate_id_from_dap(self.variablesReference)
        self.kwargs = kwargs

    @classmethod
    def update_dict_ids_from_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_from_dap(dct["variablesReference"])
        return dct

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        value = self.value
        type = self.type  # noqa (assign to builtin)
        presentationHint = self.presentationHint
        variablesReference = self.variablesReference
        namedVariables = self.namedVariables
        indexedVariables = self.indexedVariables
        memoryReference = self.memoryReference
        if update_ids_to_dap:
            if variablesReference is not None:
                variablesReference = self._translate_id_to_dap(variablesReference)
        dct = {
            "value": value,
        }
        if type is not None:
            dct["type"] = type
        if presentationHint is not None:
            dct["presentationHint"] = presentationHint.to_dict(update_ids_to_dap=update_ids_to_dap)
        if variablesReference is not None:
            dct["variablesReference"] = variablesReference
        if namedVariables is not None:
            dct["namedVariables"] = namedVariables
        if indexedVariables is not None:
            dct["indexedVariables"] = indexedVariables
        if memoryReference is not None:
            dct["memoryReference"] = memoryReference
        dct.update(self.kwargs)
        return dct

    @classmethod
    def update_dict_ids_to_dap(cls, dct):
        if "variablesReference" in dct:
            dct["variablesReference"] = cls._translate_id_to_dap(dct["variablesReference"])
        return dct


@register
class StepInTargetsResponseBody(BaseSchema):
    """
    "body" of StepInTargetsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "targets": {
            "type": "array",
            "items": {"$ref": "#/definitions/StepInTarget"},
            "description": "The possible step-in targets of the specified source location.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, targets, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array targets: The possible step-in targets of the specified source location.
        """
        self.targets = targets
        if update_ids_from_dap and self.targets:
            for o in self.targets:
                StepInTarget.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        targets = self.targets
        if targets and hasattr(targets[0], "to_dict"):
            targets = [x.to_dict() for x in targets]
        dct = {
            "targets": [StepInTarget.update_dict_ids_to_dap(o) for o in targets] if (update_ids_to_dap and targets) else targets,
        }
        dct.update(self.kwargs)
        return dct


@register
class GotoTargetsResponseBody(BaseSchema):
    """
    "body" of GotoTargetsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "targets": {
            "type": "array",
            "items": {"$ref": "#/definitions/GotoTarget"},
            "description": "The possible goto targets of the specified location.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, targets, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array targets: The possible goto targets of the specified location.
        """
        self.targets = targets
        if update_ids_from_dap and self.targets:
            for o in self.targets:
                GotoTarget.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        targets = self.targets
        if targets and hasattr(targets[0], "to_dict"):
            targets = [x.to_dict() for x in targets]
        dct = {
            "targets": [GotoTarget.update_dict_ids_to_dap(o) for o in targets] if (update_ids_to_dap and targets) else targets,
        }
        dct.update(self.kwargs)
        return dct


@register
class CompletionsResponseBody(BaseSchema):
    """
    "body" of CompletionsResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "targets": {"type": "array", "items": {"$ref": "#/definitions/CompletionItem"}, "description": "The possible completions for ."}
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, targets, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array targets: The possible completions for .
        """
        self.targets = targets
        if update_ids_from_dap and self.targets:
            for o in self.targets:
                CompletionItem.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        targets = self.targets
        if targets and hasattr(targets[0], "to_dict"):
            targets = [x.to_dict() for x in targets]
        dct = {
            "targets": [CompletionItem.update_dict_ids_to_dap(o) for o in targets] if (update_ids_to_dap and targets) else targets,
        }
        dct.update(self.kwargs)
        return dct


@register
class ExceptionInfoResponseBody(BaseSchema):
    """
    "body" of ExceptionInfoResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "exceptionId": {"type": "string", "description": "ID of the exception that was thrown."},
        "description": {"type": "string", "description": "Descriptive text for the exception."},
        "breakMode": {"description": "Mode that caused the exception notification to be raised.", "type": "ExceptionBreakMode"},
        "details": {"description": "Detailed information about the exception.", "type": "ExceptionDetails"},
    }
    __refs__ = set(["breakMode", "details"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, exceptionId, breakMode, description=None, details=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string exceptionId: ID of the exception that was thrown.
        :param ExceptionBreakMode breakMode: Mode that caused the exception notification to be raised.
        :param string description: Descriptive text for the exception.
        :param ExceptionDetails details: Detailed information about the exception.
        """
        self.exceptionId = exceptionId
        if breakMode is not None:
            assert breakMode in ExceptionBreakMode.VALID_VALUES
        self.breakMode = breakMode
        self.description = description
        if details is None:
            self.details = ExceptionDetails()
        else:
            self.details = (
                ExceptionDetails(update_ids_from_dap=update_ids_from_dap, **details) if details.__class__ != ExceptionDetails else details
            )
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        exceptionId = self.exceptionId
        breakMode = self.breakMode
        description = self.description
        details = self.details
        dct = {
            "exceptionId": exceptionId,
            "breakMode": breakMode,
        }
        if description is not None:
            dct["description"] = description
        if details is not None:
            dct["details"] = details.to_dict(update_ids_to_dap=update_ids_to_dap)
        dct.update(self.kwargs)
        return dct


@register
class ReadMemoryResponseBody(BaseSchema):
    """
    "body" of ReadMemoryResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "address": {
            "type": "string",
            "description": "The address of the first byte of data returned.\nTreated as a hex value if prefixed with `0x`, or as a decimal value otherwise.",
        },
        "unreadableBytes": {
            "type": "integer",
            "description": "The number of unreadable bytes encountered after the last successfully read byte.\nThis can be used to determine the number of bytes that should be skipped before a subsequent `readMemory` request succeeds.",
        },
        "data": {
            "type": "string",
            "description": "The bytes read from memory, encoded using base64. If the decoded length of `data` is less than the requested `count` in the original `readMemory` request, and `unreadableBytes` is zero or omitted, then the client should assume it's reached the end of readable memory.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, address, unreadableBytes=None, data=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string address: The address of the first byte of data returned.
        Treated as a hex value if prefixed with `0x`, or as a decimal value otherwise.
        :param integer unreadableBytes: The number of unreadable bytes encountered after the last successfully read byte.
        This can be used to determine the number of bytes that should be skipped before a subsequent `readMemory` request succeeds.
        :param string data: The bytes read from memory, encoded using base64. If the decoded length of `data` is less than the requested `count` in the original `readMemory` request, and `unreadableBytes` is zero or omitted, then the client should assume it's reached the end of readable memory.
        """
        self.address = address
        self.unreadableBytes = unreadableBytes
        self.data = data
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        address = self.address
        unreadableBytes = self.unreadableBytes
        data = self.data
        dct = {
            "address": address,
        }
        if unreadableBytes is not None:
            dct["unreadableBytes"] = unreadableBytes
        if data is not None:
            dct["data"] = data
        dct.update(self.kwargs)
        return dct


@register
class WriteMemoryResponseBody(BaseSchema):
    """
    "body" of WriteMemoryResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "offset": {
            "type": "integer",
            "description": "Property that should be returned when `allowPartial` is True to indicate the offset of the first byte of data successfully written. Can be negative.",
        },
        "bytesWritten": {
            "type": "integer",
            "description": "Property that should be returned when `allowPartial` is True to indicate the number of bytes starting from address that were successfully written.",
        },
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, offset=None, bytesWritten=None, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param integer offset: Property that should be returned when `allowPartial` is true to indicate the offset of the first byte of data successfully written. Can be negative.
        :param integer bytesWritten: Property that should be returned when `allowPartial` is true to indicate the number of bytes starting from address that were successfully written.
        """
        self.offset = offset
        self.bytesWritten = bytesWritten
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        offset = self.offset
        bytesWritten = self.bytesWritten
        dct = {}
        if offset is not None:
            dct["offset"] = offset
        if bytesWritten is not None:
            dct["bytesWritten"] = bytesWritten
        dct.update(self.kwargs)
        return dct


@register
class DisassembleResponseBody(BaseSchema):
    """
    "body" of DisassembleResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "instructions": {
            "type": "array",
            "items": {"$ref": "#/definitions/DisassembledInstruction"},
            "description": "The list of disassembled instructions.",
        }
    }
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, instructions, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param array instructions: The list of disassembled instructions.
        """
        self.instructions = instructions
        if update_ids_from_dap and self.instructions:
            for o in self.instructions:
                DisassembledInstruction.update_dict_ids_from_dap(o)
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        instructions = self.instructions
        if instructions and hasattr(instructions[0], "to_dict"):
            instructions = [x.to_dict() for x in instructions]
        dct = {
            "instructions": [DisassembledInstruction.update_dict_ids_to_dap(o) for o in instructions]
            if (update_ids_to_dap and instructions)
            else instructions,
        }
        dct.update(self.kwargs)
        return dct


@register
class MessageVariables(BaseSchema):
    """
    "variables" of Message

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """ """

        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        dct = {}
        dct.update(self.kwargs)
        return dct


@register
class PydevdSystemInfoResponseBody(BaseSchema):
    """
    "body" of PydevdSystemInfoResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {
        "python": {"description": "Information about the python version running in the current process.", "type": "PydevdPythonInfo"},
        "platform": {
            "description": "Information about the plarforn on which the current process is running.",
            "type": "PydevdPlatformInfo",
        },
        "process": {"description": "Information about the current process.", "type": "PydevdProcessInfo"},
        "pydevd": {"description": "Information about pydevd.", "type": "PydevdInfo"},
    }
    __refs__ = set(["python", "platform", "process", "pydevd"])

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, python, platform, process, pydevd, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param PydevdPythonInfo python: Information about the python version running in the current process.
        :param PydevdPlatformInfo platform: Information about the plarforn on which the current process is running.
        :param PydevdProcessInfo process: Information about the current process.
        :param PydevdInfo pydevd: Information about pydevd.
        """
        if python is None:
            self.python = PydevdPythonInfo()
        else:
            self.python = (
                PydevdPythonInfo(update_ids_from_dap=update_ids_from_dap, **python) if python.__class__ != PydevdPythonInfo else python
            )
        if platform is None:
            self.platform = PydevdPlatformInfo()
        else:
            self.platform = (
                PydevdPlatformInfo(update_ids_from_dap=update_ids_from_dap, **platform)
                if platform.__class__ != PydevdPlatformInfo
                else platform
            )
        if process is None:
            self.process = PydevdProcessInfo()
        else:
            self.process = (
                PydevdProcessInfo(update_ids_from_dap=update_ids_from_dap, **process) if process.__class__ != PydevdProcessInfo else process
            )
        if pydevd is None:
            self.pydevd = PydevdInfo()
        else:
            self.pydevd = PydevdInfo(update_ids_from_dap=update_ids_from_dap, **pydevd) if pydevd.__class__ != PydevdInfo else pydevd
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        python = self.python
        platform = self.platform
        process = self.process
        pydevd = self.pydevd
        dct = {
            "python": python.to_dict(update_ids_to_dap=update_ids_to_dap),
            "platform": platform.to_dict(update_ids_to_dap=update_ids_to_dap),
            "process": process.to_dict(update_ids_to_dap=update_ids_to_dap),
            "pydevd": pydevd.to_dict(update_ids_to_dap=update_ids_to_dap),
        }
        dct.update(self.kwargs)
        return dct


@register
class PydevdAuthorizeResponseBody(BaseSchema):
    """
    "body" of PydevdAuthorizeResponse

    Note: automatically generated code. Do not edit manually.
    """

    __props__ = {"clientAccessToken": {"type": "string", "description": "The access token to access the client (i.e.: usually the IDE)."}}
    __refs__ = set()

    __slots__ = list(__props__.keys()) + ["kwargs"]

    def __init__(self, clientAccessToken, update_ids_from_dap=False, **kwargs):  # noqa (update_ids_from_dap may be unused)
        """
        :param string clientAccessToken: The access token to access the client (i.e.: usually the IDE).
        """
        self.clientAccessToken = clientAccessToken
        self.kwargs = kwargs

    def to_dict(self, update_ids_to_dap=False):  # noqa (update_ids_to_dap may be unused)
        clientAccessToken = self.clientAccessToken
        dct = {
            "clientAccessToken": clientAccessToken,
        }
        dct.update(self.kwargs)
        return dct