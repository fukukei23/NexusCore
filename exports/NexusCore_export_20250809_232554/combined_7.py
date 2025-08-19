
# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_function_base_impl.py ===
import builtins
import collections.abc
import functools
import re
import sys
import warnings

import numpy as np
import numpy._core.numeric as _nx
from numpy._core import overrides, transpose
from numpy._core._multiarray_umath import _array_converter
from numpy._core.fromnumeric import any, mean, nonzero, partition, ravel, sum
from numpy._core.multiarray import _monotonicity, _place, bincount, normalize_axis_index
from numpy._core.multiarray import interp as compiled_interp
from numpy._core.multiarray import interp_complex as compiled_interp_complex
from numpy._core.numeric import (
    absolute,
    arange,
    array,
    asanyarray,
    asarray,
    concatenate,
    dot,
    empty,
    integer,
    intp,
    isscalar,
    ndarray,
    ones,
    take,
    where,
    zeros_like,
)
from numpy._core.numerictypes import typecodes
from numpy._core.umath import (
    add,
    arctan2,
    cos,
    exp,
    frompyfunc,
    less_equal,
    minimum,
    mod,
    not_equal,
    pi,
    sin,
    sqrt,
    subtract,
)
from numpy._utils import set_module

# needed in this module for compatibility
from numpy.lib._histograms_impl import histogram, histogramdd  # noqa: F401
from numpy.lib._twodim_base_impl import diag

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'select', 'piecewise', 'trim_zeros', 'copy', 'iterable', 'percentile',
    'diff', 'gradient', 'angle', 'unwrap', 'sort_complex', 'flip',
    'rot90', 'extract', 'place', 'vectorize', 'asarray_chkfinite', 'average',
    'bincount', 'digitize', 'cov', 'corrcoef',
    'median', 'sinc', 'hamming', 'hanning', 'bartlett',
    'blackman', 'kaiser', 'trapezoid', 'trapz', 'i0',
    'meshgrid', 'delete', 'insert', 'append', 'interp',
    'quantile'
    ]

# _QuantileMethods is a dictionary listing all the supported methods to
# compute quantile/percentile.
#
# Below virtual_index refers to the index of the element where the percentile
# would be found in the sorted sample.
# When the sample contains exactly the percentile wanted, the virtual_index is
# an integer to the index of this element.
# When the percentile wanted is in between two elements, the virtual_index
# is made of a integer part (a.k.a 'i' or 'left') and a fractional part
# (a.k.a 'g' or 'gamma')
#
# Each method in _QuantileMethods has two properties
# get_virtual_index : Callable
#   The function used to compute the virtual_index.
# fix_gamma : Callable
#   A function used for discrete methods to force the index to a specific value.
_QuantileMethods = {
    # --- HYNDMAN and FAN METHODS
    # Discrete methods
    'inverted_cdf': {
        'get_virtual_index': lambda n, quantiles: _inverted_cdf(n, quantiles),  # noqa: PLW0108
        'fix_gamma': None,  # should never be called
    },
    'averaged_inverted_cdf': {
        'get_virtual_index': lambda n, quantiles: (n * quantiles) - 1,
        'fix_gamma': lambda gamma, _: _get_gamma_mask(
            shape=gamma.shape,
            default_value=1.,
            conditioned_value=0.5,
            where=gamma == 0),
    },
    'closest_observation': {
        'get_virtual_index': lambda n, quantiles: _closest_observation(n, quantiles),  # noqa: PLW0108
        'fix_gamma': None,  # should never be called
    },
    # Continuous methods
    'interpolated_inverted_cdf': {
        'get_virtual_index': lambda n, quantiles:
        _compute_virtual_index(n, quantiles, 0, 1),
        'fix_gamma': lambda gamma, _: gamma,
    },
    'hazen': {
        'get_virtual_index': lambda n, quantiles:
        _compute_virtual_index(n, quantiles, 0.5, 0.5),
        'fix_gamma': lambda gamma, _: gamma,
    },
    'weibull': {
        'get_virtual_index': lambda n, quantiles:
        _compute_virtual_index(n, quantiles, 0, 0),
        'fix_gamma': lambda gamma, _: gamma,
    },
    # Default method.
    # To avoid some rounding issues, `(n-1) * quantiles` is preferred to
    # `_compute_virtual_index(n, quantiles, 1, 1)`.
    # They are mathematically equivalent.
    'linear': {
        'get_virtual_index': lambda n, quantiles: (n - 1) * quantiles,
        'fix_gamma': lambda gamma, _: gamma,
    },
    'median_unbiased': {
        'get_virtual_index': lambda n, quantiles:
        _compute_virtual_index(n, quantiles, 1 / 3.0, 1 / 3.0),
        'fix_gamma': lambda gamma, _: gamma,
    },
    'normal_unbiased': {
        'get_virtual_index': lambda n, quantiles:
        _compute_virtual_index(n, quantiles, 3 / 8.0, 3 / 8.0),
        'fix_gamma': lambda gamma, _: gamma,
    },
    # --- OTHER METHODS
    'lower': {
        'get_virtual_index': lambda n, quantiles: np.floor(
            (n - 1) * quantiles).astype(np.intp),
        'fix_gamma': None,  # should never be called, index dtype is int
    },
    'higher': {
        'get_virtual_index': lambda n, quantiles: np.ceil(
            (n - 1) * quantiles).astype(np.intp),
        'fix_gamma': None,  # should never be called, index dtype is int
    },
    'midpoint': {
        'get_virtual_index': lambda n, quantiles: 0.5 * (
                np.floor((n - 1) * quantiles)
                + np.ceil((n - 1) * quantiles)),
        'fix_gamma': lambda gamma, index: _get_gamma_mask(
            shape=gamma.shape,
            default_value=0.5,
            conditioned_value=0.,
            where=index % 1 == 0),
    },
    'nearest': {
        'get_virtual_index': lambda n, quantiles: np.around(
            (n - 1) * quantiles).astype(np.intp),
        'fix_gamma': None,
        # should never be called, index dtype is int
    }}


def _rot90_dispatcher(m, k=None, axes=None):
    return (m,)


@array_function_dispatch(_rot90_dispatcher)
def rot90(m, k=1, axes=(0, 1)):
    """
    Rotate an array by 90 degrees in the plane specified by axes.

    Rotation direction is from the first towards the second axis.
    This means for a 2D array with the default `k` and `axes`, the
    rotation will be counterclockwise.

    Parameters
    ----------
    m : array_like
        Array of two or more dimensions.
    k : integer
        Number of times the array is rotated by 90 degrees.
    axes : (2,) array_like
        The array is rotated in the plane defined by the axes.
        Axes must be different.

    Returns
    -------
    y : ndarray
        A rotated view of `m`.

    See Also
    --------
    flip : Reverse the order of elements in an array along the given axis.
    fliplr : Flip an array horizontally.
    flipud : Flip an array vertically.

    Notes
    -----
    ``rot90(m, k=1, axes=(1,0))``  is the reverse of
    ``rot90(m, k=1, axes=(0,1))``

    ``rot90(m, k=1, axes=(1,0))`` is equivalent to
    ``rot90(m, k=-1, axes=(0,1))``

    Examples
    --------
    >>> import numpy as np
    >>> m = np.array([[1,2],[3,4]], int)
    >>> m
    array([[1, 2],
           [3, 4]])
    >>> np.rot90(m)
    array([[2, 4],
           [1, 3]])
    >>> np.rot90(m, 2)
    array([[4, 3],
           [2, 1]])
    >>> m = np.arange(8).reshape((2,2,2))
    >>> np.rot90(m, 1, (1,2))
    array([[[1, 3],
            [0, 2]],
           [[5, 7],
            [4, 6]]])

    """
    axes = tuple(axes)
    if len(axes) != 2:
        raise ValueError("len(axes) must be 2.")

    m = asanyarray(m)

    if axes[0] == axes[1] or absolute(axes[0] - axes[1]) == m.ndim:
        raise ValueError("Axes must be different.")

    if (axes[0] >= m.ndim or axes[0] < -m.ndim
        or axes[1] >= m.ndim or axes[1] < -m.ndim):
        raise ValueError(f"Axes={axes} out of range for array of ndim={m.ndim}.")

    k %= 4

    if k == 0:
        return m[:]
    if k == 2:
        return flip(flip(m, axes[0]), axes[1])

    axes_list = arange(0, m.ndim)
    (axes_list[axes[0]], axes_list[axes[1]]) = (axes_list[axes[1]],
                                                axes_list[axes[0]])

    if k == 1:
        return transpose(flip(m, axes[1]), axes_list)
    else:
        # k == 3
        return flip(transpose(m, axes_list), axes[1])


def _flip_dispatcher(m, axis=None):
    return (m,)


@array_function_dispatch(_flip_dispatcher)
def flip(m, axis=None):
    """
    Reverse the order of elements in an array along the given axis.

    The shape of the array is preserved, but the elements are reordered.

    Parameters
    ----------
    m : array_like
        Input array.
    axis : None or int or tuple of ints, optional
         Axis or axes along which to flip over. The default,
         axis=None, will flip over all of the axes of the input array.
         If axis is negative it counts from the last to the first axis.

         If axis is a tuple of ints, flipping is performed on all of the axes
         specified in the tuple.

    Returns
    -------
    out : array_like
        A view of `m` with the entries of axis reversed.  Since a view is
        returned, this operation is done in constant time.

    See Also
    --------
    flipud : Flip an array vertically (axis=0).
    fliplr : Flip an array horizontally (axis=1).

    Notes
    -----
    flip(m, 0) is equivalent to flipud(m).

    flip(m, 1) is equivalent to fliplr(m).

    flip(m, n) corresponds to ``m[...,::-1,...]`` with ``::-1`` at position n.

    flip(m) corresponds to ``m[::-1,::-1,...,::-1]`` with ``::-1`` at all
    positions.

    flip(m, (0, 1)) corresponds to ``m[::-1,::-1,...]`` with ``::-1`` at
    position 0 and position 1.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.arange(8).reshape((2,2,2))
    >>> A
    array([[[0, 1],
            [2, 3]],
           [[4, 5],
            [6, 7]]])
    >>> np.flip(A, 0)
    array([[[4, 5],
            [6, 7]],
           [[0, 1],
            [2, 3]]])
    >>> np.flip(A, 1)
    array([[[2, 3],
            [0, 1]],
           [[6, 7],
            [4, 5]]])
    >>> np.flip(A)
    array([[[7, 6],
            [5, 4]],
           [[3, 2],
            [1, 0]]])
    >>> np.flip(A, (0, 2))
    array([[[5, 4],
            [7, 6]],
           [[1, 0],
            [3, 2]]])
    >>> rng = np.random.default_rng()
    >>> A = rng.normal(size=(3,4,5))
    >>> np.all(np.flip(A,2) == A[:,:,::-1,...])
    True
    """
    if not hasattr(m, 'ndim'):
        m = asarray(m)
    if axis is None:
        indexer = (np.s_[::-1],) * m.ndim
    else:
        axis = _nx.normalize_axis_tuple(axis, m.ndim)
        indexer = [np.s_[:]] * m.ndim
        for ax in axis:
            indexer[ax] = np.s_[::-1]
        indexer = tuple(indexer)
    return m[indexer]


@set_module('numpy')
def iterable(y):
    """
    Check whether or not an object can be iterated over.

    Parameters
    ----------
    y : object
      Input object.

    Returns
    -------
    b : bool
      Return ``True`` if the object has an iterator method or is a
      sequence and ``False`` otherwise.


    Examples
    --------
    >>> import numpy as np
    >>> np.iterable([1, 2, 3])
    True
    >>> np.iterable(2)
    False

    Notes
    -----
    In most cases, the results of ``np.iterable(obj)`` are consistent with
    ``isinstance(obj, collections.abc.Iterable)``. One notable exception is
    the treatment of 0-dimensional arrays::

        >>> from collections.abc import Iterable
        >>> a = np.array(1.0)  # 0-dimensional numpy array
        >>> isinstance(a, Iterable)
        True
        >>> np.iterable(a)
        False

    """
    try:
        iter(y)
    except TypeError:
        return False
    return True


def _weights_are_valid(weights, a, axis):
    """Validate weights array.

    We assume, weights is not None.
    """
    wgt = np.asanyarray(weights)

    # Sanity checks
    if a.shape != wgt.shape:
        if axis is None:
            raise TypeError(
                "Axis must be specified when shapes of a and weights "
                "differ.")
        if wgt.shape != tuple(a.shape[ax] for ax in axis):
            raise ValueError(
                "Shape of weights must be consistent with "
                "shape of a along specified axis.")

        # setup wgt to broadcast along axis
        wgt = wgt.transpose(np.argsort(axis))
        wgt = wgt.reshape(tuple((s if ax in axis else 1)
                                for ax, s in enumerate(a.shape)))
    return wgt


def _average_dispatcher(a, axis=None, weights=None, returned=None, *,
                        keepdims=None):
    return (a, weights)


@array_function_dispatch(_average_dispatcher)
def average(a, axis=None, weights=None, returned=False, *,
            keepdims=np._NoValue):
    """
    Compute the weighted average along the specified axis.

    Parameters
    ----------
    a : array_like
        Array containing data to be averaged. If `a` is not an array, a
        conversion is attempted.
    axis : None or int or tuple of ints, optional
        Axis or axes along which to average `a`.  The default,
        `axis=None`, will average over all of the elements of the input array.
        If axis is negative it counts from the last to the first axis.
        If axis is a tuple of ints, averaging is performed on all of the axes
        specified in the tuple instead of a single axis or all the axes as
        before.
    weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the average according to its associated weight.
        The array of weights must be the same shape as `a` if no axis is
        specified, otherwise the weights must have dimensions and shape
        consistent with `a` along the specified axis.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        The calculation is::

            avg = sum(a * weights) / sum(weights)

        where the sum is over all included elements.
        The only constraint on the values of `weights` is that `sum(weights)`
        must not be 0.
    returned : bool, optional
        Default is `False`. If `True`, the tuple (`average`, `sum_of_weights`)
        is returned, otherwise only the average is returned.
        If `weights=None`, `sum_of_weights` is equivalent to the number of
        elements over which the average is taken.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.
        *Note:* `keepdims` will not work with instances of `numpy.matrix`
        or other classes whose methods do not support `keepdims`.

        .. versionadded:: 1.23.0

    Returns
    -------
    retval, [sum_of_weights] : array_type or double
        Return the average along the specified axis. When `returned` is `True`,
        return a tuple with the average as the first element and the sum
        of the weights as the second element. `sum_of_weights` is of the
        same type as `retval`. The result dtype follows a general pattern.
        If `weights` is None, the result dtype will be that of `a` , or ``float64``
        if `a` is integral. Otherwise, if `weights` is not None and `a` is non-
        integral, the result type will be the type of lowest precision capable of
        representing values of both `a` and `weights`. If `a` happens to be
        integral, the previous rules still applies but the result dtype will
        at least be ``float64``.

    Raises
    ------
    ZeroDivisionError
        When all weights along axis are zero. See `numpy.ma.average` for a
        version robust to this type of error.
    TypeError
        When `weights` does not have the same shape as `a`, and `axis=None`.
    ValueError
        When `weights` does not have dimensions and shape consistent with `a`
        along specified `axis`.

    See Also
    --------
    mean

    ma.average : average for masked arrays -- useful if your data contains
                 "missing" values
    numpy.result_type : Returns the type that results from applying the
                        numpy type promotion rules to the arguments.

    Examples
    --------
    >>> import numpy as np
    >>> data = np.arange(1, 5)
    >>> data
    array([1, 2, 3, 4])
    >>> np.average(data)
    2.5
    >>> np.average(np.arange(1, 11), weights=np.arange(10, 0, -1))
    4.0

    >>> data = np.arange(6).reshape((3, 2))
    >>> data
    array([[0, 1],
           [2, 3],
           [4, 5]])
    >>> np.average(data, axis=1, weights=[1./4, 3./4])
    array([0.75, 2.75, 4.75])
    >>> np.average(data, weights=[1./4, 3./4])
    Traceback (most recent call last):
        ...
    TypeError: Axis must be specified when shapes of a and weights differ.

    With ``keepdims=True``, the following result has shape (3, 1).

    >>> np.average(data, axis=1, keepdims=True)
    array([[0.5],
           [2.5],
           [4.5]])

    >>> data = np.arange(8).reshape((2, 2, 2))
    >>> data
    array([[[0, 1],
            [2, 3]],
           [[4, 5],
            [6, 7]]])
    >>> np.average(data, axis=(0, 1), weights=[[1./4, 3./4], [1., 1./2]])
    array([3.4, 4.4])
    >>> np.average(data, axis=0, weights=[[1./4, 3./4], [1., 1./2]])
    Traceback (most recent call last):
        ...
    ValueError: Shape of weights must be consistent
    with shape of a along specified axis.
    """
    a = np.asanyarray(a)

    if axis is not None:
        axis = _nx.normalize_axis_tuple(axis, a.ndim, argname="axis")

    if keepdims is np._NoValue:
        # Don't pass on the keepdims argument if one wasn't given.
        keepdims_kw = {}
    else:
        keepdims_kw = {'keepdims': keepdims}

    if weights is None:
        avg = a.mean(axis, **keepdims_kw)
        avg_as_array = np.asanyarray(avg)
        scl = avg_as_array.dtype.type(a.size / avg_as_array.size)
    else:
        wgt = _weights_are_valid(weights=weights, a=a, axis=axis)

        if issubclass(a.dtype.type, (np.integer, np.bool)):
            result_dtype = np.result_type(a.dtype, wgt.dtype, 'f8')
        else:
            result_dtype = np.result_type(a.dtype, wgt.dtype)

        scl = wgt.sum(axis=axis, dtype=result_dtype, **keepdims_kw)
        if np.any(scl == 0.0):
            raise ZeroDivisionError(
                "Weights sum to zero, can't be normalized")

        avg = avg_as_array = np.multiply(a, wgt,
                          dtype=result_dtype).sum(axis, **keepdims_kw) / scl

    if returned:
        if scl.shape != avg_as_array.shape:
            scl = np.broadcast_to(scl, avg_as_array.shape).copy()
        return avg, scl
    else:
        return avg


@set_module('numpy')
def asarray_chkfinite(a, dtype=None, order=None):
    """Convert the input to an array, checking for NaNs or Infs.

    Parameters
    ----------
    a : array_like
        Input data, in any form that can be converted to an array.  This
        includes lists, lists of tuples, tuples, tuples of tuples, tuples
        of lists and ndarrays.  Success requires no NaNs or Infs.
    dtype : data-type, optional
        By default, the data-type is inferred from the input data.
    order : {'C', 'F', 'A', 'K'}, optional
        Memory layout.  'A' and 'K' depend on the order of input array a.
        'C' row-major (C-style),
        'F' column-major (Fortran-style) memory representation.
        'A' (any) means 'F' if `a` is Fortran contiguous, 'C' otherwise
        'K' (keep) preserve input order
        Defaults to 'C'.

    Returns
    -------
    out : ndarray
        Array interpretation of `a`.  No copy is performed if the input
        is already an ndarray.  If `a` is a subclass of ndarray, a base
        class ndarray is returned.

    Raises
    ------
    ValueError
        Raises ValueError if `a` contains NaN (Not a Number) or Inf (Infinity).

    See Also
    --------
    asarray : Create and array.
    asanyarray : Similar function which passes through subclasses.
    ascontiguousarray : Convert input to a contiguous array.
    asfortranarray : Convert input to an ndarray with column-major
                     memory order.
    fromiter : Create an array from an iterator.
    fromfunction : Construct an array by executing a function on grid
                   positions.

    Examples
    --------
    >>> import numpy as np

    Convert a list into an array. If all elements are finite, then
    ``asarray_chkfinite`` is identical to ``asarray``.

    >>> a = [1, 2]
    >>> np.asarray_chkfinite(a, dtype=float)
    array([1., 2.])

    Raises ValueError if array_like contains Nans or Infs.

    >>> a = [1, 2, np.inf]
    >>> try:
    ...     np.asarray_chkfinite(a)
    ... except ValueError:
    ...     print('ValueError')
    ...
    ValueError

    """
    a = asarray(a, dtype=dtype, order=order)
    if a.dtype.char in typecodes['AllFloat'] and not np.isfinite(a).all():
        raise ValueError(
            "array must not contain infs or NaNs")
    return a


def _piecewise_dispatcher(x, condlist, funclist, *args, **kw):
    yield x
    # support the undocumented behavior of allowing scalars
    if np.iterable(condlist):
        yield from condlist


@array_function_dispatch(_piecewise_dispatcher)
def piecewise(x, condlist, funclist, *args, **kw):
    """
    Evaluate a piecewise-defined function.

    Given a set of conditions and corresponding functions, evaluate each
    function on the input data wherever its condition is true.

    Parameters
    ----------
    x : ndarray or scalar
        The input domain.
    condlist : list of bool arrays or bool scalars
        Each boolean array corresponds to a function in `funclist`.  Wherever
        `condlist[i]` is True, `funclist[i](x)` is used as the output value.

        Each boolean array in `condlist` selects a piece of `x`,
        and should therefore be of the same shape as `x`.

        The length of `condlist` must correspond to that of `funclist`.
        If one extra function is given, i.e. if
        ``len(funclist) == len(condlist) + 1``, then that extra function
        is the default value, used wherever all conditions are false.
    funclist : list of callables, f(x,*args,**kw), or scalars
        Each function is evaluated over `x` wherever its corresponding
        condition is True.  It should take a 1d array as input and give an 1d
        array or a scalar value as output.  If, instead of a callable,
        a scalar is provided then a constant function (``lambda x: scalar``) is
        assumed.
    args : tuple, optional
        Any further arguments given to `piecewise` are passed to the functions
        upon execution, i.e., if called ``piecewise(..., ..., 1, 'a')``, then
        each function is called as ``f(x, 1, 'a')``.
    kw : dict, optional
        Keyword arguments used in calling `piecewise` are passed to the
        functions upon execution, i.e., if called
        ``piecewise(..., ..., alpha=1)``, then each function is called as
        ``f(x, alpha=1)``.

    Returns
    -------
    out : ndarray
        The output is the same shape and type as x and is found by
        calling the functions in `funclist` on the appropriate portions of `x`,
        as defined by the boolean arrays in `condlist`.  Portions not covered
        by any condition have a default value of 0.


    See Also
    --------
    choose, select, where

    Notes
    -----
    This is similar to choose or select, except that functions are
    evaluated on elements of `x` that satisfy the corresponding condition from
    `condlist`.

    The result is::

            |--
            |funclist[0](x[condlist[0]])
      out = |funclist[1](x[condlist[1]])
            |...
            |funclist[n2](x[condlist[n2]])
            |--

    Examples
    --------
    >>> import numpy as np

    Define the signum function, which is -1 for ``x < 0`` and +1 for ``x >= 0``.

    >>> x = np.linspace(-2.5, 2.5, 6)
    >>> np.piecewise(x, [x < 0, x >= 0], [-1, 1])
    array([-1., -1., -1.,  1.,  1.,  1.])

    Define the absolute value, which is ``-x`` for ``x <0`` and ``x`` for
    ``x >= 0``.

    >>> np.piecewise(x, [x < 0, x >= 0], [lambda x: -x, lambda x: x])
    array([2.5,  1.5,  0.5,  0.5,  1.5,  2.5])

    Apply the same function to a scalar value.

    >>> y = -2
    >>> np.piecewise(y, [y < 0, y >= 0], [lambda x: -x, lambda x: x])
    array(2)

    """
    x = asanyarray(x)
    n2 = len(funclist)

    # undocumented: single condition is promoted to a list of one condition
    if isscalar(condlist) or (
            not isinstance(condlist[0], (list, ndarray)) and x.ndim != 0):
        condlist = [condlist]

    condlist = asarray(condlist, dtype=bool)
    n = len(condlist)

    if n == n2 - 1:  # compute the "otherwise" condition.
        condelse = ~np.any(condlist, axis=0, keepdims=True)
        condlist = np.concatenate([condlist, condelse], axis=0)
        n += 1
    elif n != n2:
        raise ValueError(
            f"with {n} condition(s), either {n} or {n + 1} functions are expected"
        )

    y = zeros_like(x)
    for cond, func in zip(condlist, funclist):
        if not isinstance(func, collections.abc.Callable):
            y[cond] = func
        else:
            vals = x[cond]
            if vals.size > 0:
                y[cond] = func(vals, *args, **kw)

    return y


def _select_dispatcher(condlist, choicelist, default=None):
    yield from condlist
    yield from choicelist


@array_function_dispatch(_select_dispatcher)
def select(condlist, choicelist, default=0):
    """
    Return an array drawn from elements in choicelist, depending on conditions.

    Parameters
    ----------
    condlist : list of bool ndarrays
        The list of conditions which determine from which array in `choicelist`
        the output elements are taken. When multiple conditions are satisfied,
        the first one encountered in `condlist` is used.
    choicelist : list of ndarrays
        The list of arrays from which the output elements are taken. It has
        to be of the same length as `condlist`.
    default : scalar, optional
        The element inserted in `output` when all conditions evaluate to False.

    Returns
    -------
    output : ndarray
        The output at position m is the m-th element of the array in
        `choicelist` where the m-th element of the corresponding array in
        `condlist` is True.

    See Also
    --------
    where : Return elements from one of two arrays depending on condition.
    take, choose, compress, diag, diagonal

    Examples
    --------
    >>> import numpy as np

    Beginning with an array of integers from 0 to 5 (inclusive),
    elements less than ``3`` are negated, elements greater than ``3``
    are squared, and elements not meeting either of these conditions
    (exactly ``3``) are replaced with a `default` value of ``42``.

    >>> x = np.arange(6)
    >>> condlist = [x<3, x>3]
    >>> choicelist = [-x, x**2]
    >>> np.select(condlist, choicelist, 42)
    array([ 0,  -1,  -2, 42, 16, 25])

    When multiple conditions are satisfied, the first one encountered in
    `condlist` is used.

    >>> condlist = [x<=4, x>3]
    >>> choicelist = [x, x**2]
    >>> np.select(condlist, choicelist, 55)
    array([ 0,  1,  2,  3,  4, 25])

    """
    # Check the size of condlist and choicelist are the same, or abort.
    if len(condlist) != len(choicelist):
        raise ValueError(
            'list of cases must be same length as list of conditions')

    # Now that the dtype is known, handle the deprecated select([], []) case
    if len(condlist) == 0:
        raise ValueError("select with an empty condition list is not possible")

    # TODO: This preserves the Python int, float, complex manually to get the
    #       right `result_type` with NEP 50.  Most likely we will grow a better
    #       way to spell this (and this can be replaced).
    choicelist = [
        choice if type(choice) in (int, float, complex) else np.asarray(choice)
        for choice in choicelist]
    choicelist.append(default if type(default) in (int, float, complex)
                      else np.asarray(default))

    try:
        dtype = np.result_type(*choicelist)
    except TypeError as e:
        msg = f'Choicelist and default value do not have a common dtype: {e}'
        raise TypeError(msg) from None

    # Convert conditions to arrays and broadcast conditions and choices
    # as the shape is needed for the result. Doing it separately optimizes
    # for example when all choices are scalars.
    condlist = np.broadcast_arrays(*condlist)
    choicelist = np.broadcast_arrays(*choicelist)

    # If cond array is not an ndarray in boolean format or scalar bool, abort.
    for i, cond in enumerate(condlist):
        if cond.dtype.type is not np.bool:
            raise TypeError(
                f'invalid entry {i} in condlist: should be boolean ndarray')

    if choicelist[0].ndim == 0:
        # This may be common, so avoid the call.
        result_shape = condlist[0].shape
    else:
        result_shape = np.broadcast_arrays(condlist[0], choicelist[0])[0].shape

    result = np.full(result_shape, choicelist[-1], dtype)

    # Use np.copyto to burn each choicelist array onto result, using the
    # corresponding condlist as a boolean mask. This is done in reverse
    # order since the first choice should take precedence.
    choicelist = choicelist[-2::-1]
    condlist = condlist[::-1]
    for choice, cond in zip(choicelist, condlist):
        np.copyto(result, choice, where=cond)

    return result


def _copy_dispatcher(a, order=None, subok=None):
    return (a,)


@array_function_dispatch(_copy_dispatcher)
def copy(a, order='K', subok=False):
    """
    Return an array copy of the given object.

    Parameters
    ----------
    a : array_like
        Input data.
    order : {'C', 'F', 'A', 'K'}, optional
        Controls the memory layout of the copy. 'C' means C-order,
        'F' means F-order, 'A' means 'F' if `a` is Fortran contiguous,
        'C' otherwise. 'K' means match the layout of `a` as closely
        as possible. (Note that this function and :meth:`ndarray.copy` are very
        similar, but have different default values for their order=
        arguments.)
    subok : bool, optional
        If True, then sub-classes will be passed-through, otherwise the
        returned array will be forced to be a base-class array (defaults to False).

    Returns
    -------
    arr : ndarray
        Array interpretation of `a`.

    See Also
    --------
    ndarray.copy : Preferred method for creating an array copy

    Notes
    -----
    This is equivalent to:

    >>> np.array(a, copy=True)  #doctest: +SKIP

    The copy made of the data is shallow, i.e., for arrays with object dtype,
    the new array will point to the same objects.
    See Examples from `ndarray.copy`.

    Examples
    --------
    >>> import numpy as np

    Create an array x, with a reference y and a copy z:

    >>> x = np.array([1, 2, 3])
    >>> y = x
    >>> z = np.copy(x)

    Note that, when we modify x, y changes, but not z:

    >>> x[0] = 10
    >>> x[0] == y[0]
    True
    >>> x[0] == z[0]
    False

    Note that, np.copy clears previously set WRITEABLE=False flag.

    >>> a = np.array([1, 2, 3])
    >>> a.flags["WRITEABLE"] = False
    >>> b = np.copy(a)
    >>> b.flags["WRITEABLE"]
    True
    >>> b[0] = 3
    >>> b
    array([3, 2, 3])
    """
    return array(a, order=order, subok=subok, copy=True)

# Basic operations


def _gradient_dispatcher(f, *varargs, axis=None, edge_order=None):
    yield f
    yield from varargs


@array_function_dispatch(_gradient_dispatcher)
def gradient(f, *varargs, axis=None, edge_order=1):
    """
    Return the gradient of an N-dimensional array.

    The gradient is computed using second order accurate central differences
    in the interior points and either first or second order accurate one-sides
    (forward or backwards) differences at the boundaries.
    The returned gradient hence has the same shape as the input array.

    Parameters
    ----------
    f : array_like
        An N-dimensional array containing samples of a scalar function.
    varargs : list of scalar or array, optional
        Spacing between f values. Default unitary spacing for all dimensions.
        Spacing can be specified using:

        1. single scalar to specify a sample distance for all dimensions.
        2. N scalars to specify a constant sample distance for each dimension.
           i.e. `dx`, `dy`, `dz`, ...
        3. N arrays to specify the coordinates of the values along each
           dimension of F. The length of the array must match the size of
           the corresponding dimension
        4. Any combination of N scalars/arrays with the meaning of 2. and 3.

        If `axis` is given, the number of varargs must equal the number of axes
        specified in the axis parameter.
        Default: 1. (see Examples below).

    edge_order : {1, 2}, optional
        Gradient is calculated using N-th order accurate differences
        at the boundaries. Default: 1.
    axis : None or int or tuple of ints, optional
        Gradient is calculated only along the given axis or axes
        The default (axis = None) is to calculate the gradient for all the axes
        of the input array. axis may be negative, in which case it counts from
        the last to the first axis.

    Returns
    -------
    gradient : ndarray or tuple of ndarray
        A tuple of ndarrays (or a single ndarray if there is only one
        dimension) corresponding to the derivatives of f with respect
        to each dimension. Each derivative has the same shape as f.

    Examples
    --------
    >>> import numpy as np
    >>> f = np.array([1, 2, 4, 7, 11, 16])
    >>> np.gradient(f)
    array([1. , 1.5, 2.5, 3.5, 4.5, 5. ])
    >>> np.gradient(f, 2)
    array([0.5 ,  0.75,  1.25,  1.75,  2.25,  2.5 ])

    Spacing can be also specified with an array that represents the coordinates
    of the values F along the dimensions.
    For instance a uniform spacing:

    >>> x = np.arange(f.size)
    >>> np.gradient(f, x)
    array([1. ,  1.5,  2.5,  3.5,  4.5,  5. ])

    Or a non uniform one:

    >>> x = np.array([0., 1., 1.5, 3.5, 4., 6.])
    >>> np.gradient(f, x)
    array([1. ,  3. ,  3.5,  6.7,  6.9,  2.5])

    For two dimensional arrays, the return will be two arrays ordered by
    axis. In this example the first array stands for the gradient in
    rows and the second one in columns direction:

    >>> np.gradient(np.array([[1, 2, 6], [3, 4, 5]]))
    (array([[ 2.,  2., -1.],
            [ 2.,  2., -1.]]),
     array([[1. , 2.5, 4. ],
            [1. , 1. , 1. ]]))

    In this example the spacing is also specified:
    uniform for axis=0 and non uniform for axis=1

    >>> dx = 2.
    >>> y = [1., 1.5, 3.5]
    >>> np.gradient(np.array([[1, 2, 6], [3, 4, 5]]), dx, y)
    (array([[ 1. ,  1. , -0.5],
            [ 1. ,  1. , -0.5]]),
     array([[2. , 2. , 2. ],
            [2. , 1.7, 0.5]]))

    It is possible to specify how boundaries are treated using `edge_order`

    >>> x = np.array([0, 1, 2, 3, 4])
    >>> f = x**2
    >>> np.gradient(f, edge_order=1)
    array([1.,  2.,  4.,  6.,  7.])
    >>> np.gradient(f, edge_order=2)
    array([0., 2., 4., 6., 8.])

    The `axis` keyword can be used to specify a subset of axes of which the
    gradient is calculated

    >>> np.gradient(np.array([[1, 2, 6], [3, 4, 5]]), axis=0)
    array([[ 2.,  2., -1.],
           [ 2.,  2., -1.]])

    The `varargs` argument defines the spacing between sample points in the
    input array. It can take two forms:

    1. An array, specifying coordinates, which may be unevenly spaced:

    >>> x = np.array([0., 2., 3., 6., 8.])
    >>> y = x ** 2
    >>> np.gradient(y, x, edge_order=2)
    array([ 0.,  4.,  6., 12., 16.])

    2. A scalar, representing the fixed sample distance:

    >>> dx = 2
    >>> x = np.array([0., 2., 4., 6., 8.])
    >>> y = x ** 2
    >>> np.gradient(y, dx, edge_order=2)
    array([ 0.,  4.,  8., 12., 16.])

    It's possible to provide different data for spacing along each dimension.
    The number of arguments must match the number of dimensions in the input
    data.

    >>> dx = 2
    >>> dy = 3
    >>> x = np.arange(0, 6, dx)
    >>> y = np.arange(0, 9, dy)
    >>> xs, ys = np.meshgrid(x, y)
    >>> zs = xs + 2 * ys
    >>> np.gradient(zs, dy, dx)  # Passing two scalars
    (array([[2., 2., 2.],
            [2., 2., 2.],
            [2., 2., 2.]]),
     array([[1., 1., 1.],
            [1., 1., 1.],
            [1., 1., 1.]]))

    Mixing scalars and arrays is also allowed:

    >>> np.gradient(zs, y, dx)  # Passing one array and one scalar
    (array([[2., 2., 2.],
            [2., 2., 2.],
            [2., 2., 2.]]),
     array([[1., 1., 1.],
            [1., 1., 1.],
            [1., 1., 1.]]))

    Notes
    -----
    Assuming that :math:`f\\in C^{3}` (i.e., :math:`f` has at least 3 continuous
    derivatives) and let :math:`h_{*}` be a non-homogeneous stepsize, we
    minimize the "consistency error" :math:`\\eta_{i}` between the true gradient
    and its estimate from a linear combination of the neighboring grid-points:

    .. math::

        \\eta_{i} = f_{i}^{\\left(1\\right)} -
                    \\left[ \\alpha f\\left(x_{i}\\right) +
                            \\beta f\\left(x_{i} + h_{d}\\right) +
                            \\gamma f\\left(x_{i}-h_{s}\\right)
                    \\right]

    By substituting :math:`f(x_{i} + h_{d})` and :math:`f(x_{i} - h_{s})`
    with their Taylor series expansion, this translates into solving
    the following the linear system:

    .. math::

        \\left\\{
            \\begin{array}{r}
                \\alpha+\\beta+\\gamma=0 \\\\
                \\beta h_{d}-\\gamma h_{s}=1 \\\\
                \\beta h_{d}^{2}+\\gamma h_{s}^{2}=0
            \\end{array}
        \\right.

    The resulting approximation of :math:`f_{i}^{(1)}` is the following:

    .. math::

        \\hat f_{i}^{(1)} =
            \\frac{
                h_{s}^{2}f\\left(x_{i} + h_{d}\\right)
                + \\left(h_{d}^{2} - h_{s}^{2}\\right)f\\left(x_{i}\\right)
                - h_{d}^{2}f\\left(x_{i}-h_{s}\\right)}
                { h_{s}h_{d}\\left(h_{d} + h_{s}\\right)}
            + \\mathcal{O}\\left(\\frac{h_{d}h_{s}^{2}
                                + h_{s}h_{d}^{2}}{h_{d}
                                + h_{s}}\\right)

    It is worth noting that if :math:`h_{s}=h_{d}`
    (i.e., data are evenly spaced)
    we find the standard second order approximation:

    .. math::

        \\hat f_{i}^{(1)}=
            \\frac{f\\left(x_{i+1}\\right) - f\\left(x_{i-1}\\right)}{2h}
            + \\mathcal{O}\\left(h^{2}\\right)

    With a similar procedure the forward/backward approximations used for
    boundaries can be derived.

    References
    ----------
    .. [1]  Quarteroni A., Sacco R., Saleri F. (2007) Numerical Mathematics
            (Texts in Applied Mathematics). New York: Springer.
    .. [2]  Durran D. R. (1999) Numerical Methods for Wave Equations
            in Geophysical Fluid Dynamics. New York: Springer.
    .. [3]  Fornberg B. (1988) Generation of Finite Difference Formulas on
            Arbitrarily Spaced Grids,
            Mathematics of Computation 51, no. 184 : 699-706.
            `PDF <https://www.ams.org/journals/mcom/1988-51-184/
            S0025-5718-1988-0935077-0/S0025-5718-1988-0935077-0.pdf>`_.
    """
    f = np.asanyarray(f)
    N = f.ndim  # number of dimensions

    if axis is None:
        axes = tuple(range(N))
    else:
        axes = _nx.normalize_axis_tuple(axis, N)

    len_axes = len(axes)
    n = len(varargs)
    if n == 0:
        # no spacing argument - use 1 in all axes
        dx = [1.0] * len_axes
    elif n == 1 and np.ndim(varargs[0]) == 0:
        # single scalar for all axes
        dx = varargs * len_axes
    elif n == len_axes:
        # scalar or 1d array for each axis
        dx = list(varargs)
        for i, distances in enumerate(dx):
            distances = np.asanyarray(distances)
            if distances.ndim == 0:
                continue
            elif distances.ndim != 1:
                raise ValueError("distances must be either scalars or 1d")
            if len(distances) != f.shape[axes[i]]:
                raise ValueError("when 1d, distances must match "
                                 "the length of the corresponding dimension")
            if np.issubdtype(distances.dtype, np.integer):
                # Convert numpy integer types to float64 to avoid modular
                # arithmetic in np.diff(distances).
                distances = distances.astype(np.float64)
            diffx = np.diff(distances)
            # if distances are constant reduce to the scalar case
            # since it brings a consistent speedup
            if (diffx == diffx[0]).all():
                diffx = diffx[0]
            dx[i] = diffx
    else:
        raise TypeError("invalid number of arguments")

    if edge_order > 2:
        raise ValueError("'edge_order' greater than 2 not supported")

    # use central differences on interior and one-sided differences on the
    # endpoints. This preserves second order-accuracy over the full domain.

    outvals = []

    # create slice objects --- initially all are [:, :, ..., :]
    slice1 = [slice(None)] * N
    slice2 = [slice(None)] * N
    slice3 = [slice(None)] * N
    slice4 = [slice(None)] * N

    otype = f.dtype
    if otype.type is np.datetime64:
        # the timedelta dtype with the same unit information
        otype = np.dtype(otype.name.replace('datetime', 'timedelta'))
        # view as timedelta to allow addition
        f = f.view(otype)
    elif otype.type is np.timedelta64:
        pass
    elif np.issubdtype(otype, np.inexact):
        pass
    else:
        # All other types convert to floating point.
        # First check if f is a numpy integer type; if so, convert f to float64
        # to avoid modular arithmetic when computing the changes in f.
        if np.issubdtype(otype, np.integer):
            f = f.astype(np.float64)
        otype = np.float64

    for axis, ax_dx in zip(axes, dx):
        if f.shape[axis] < edge_order + 1:
            raise ValueError(
                "Shape of array too small to calculate a numerical gradient, "
                "at least (edge_order + 1) elements are required.")
        # result allocation
        out = np.empty_like(f, dtype=otype)

        # spacing for the current axis
        uniform_spacing = np.ndim(ax_dx) == 0

        # Numerical differentiation: 2nd order interior
        slice1[axis] = slice(1, -1)
        slice2[axis] = slice(None, -2)
        slice3[axis] = slice(1, -1)
        slice4[axis] = slice(2, None)

        if uniform_spacing:
            out[tuple(slice1)] = (f[tuple(slice4)] - f[tuple(slice2)]) / (2. * ax_dx)
        else:
            dx1 = ax_dx[0:-1]
            dx2 = ax_dx[1:]
            a = -(dx2) / (dx1 * (dx1 + dx2))
            b = (dx2 - dx1) / (dx1 * dx2)
            c = dx1 / (dx2 * (dx1 + dx2))
            # fix the shape for broadcasting
            shape = np.ones(N, dtype=int)
            shape[axis] = -1
            a.shape = b.shape = c.shape = shape
            # 1D equivalent -- out[1:-1] = a * f[:-2] + b * f[1:-1] + c * f[2:]
            out[tuple(slice1)] = a * f[tuple(slice2)] + b * f[tuple(slice3)] \
                                                + c * f[tuple(slice4)]

        # Numerical differentiation: 1st order edges
        if edge_order == 1:
            slice1[axis] = 0
            slice2[axis] = 1
            slice3[axis] = 0
            dx_0 = ax_dx if uniform_spacing else ax_dx[0]
            # 1D equivalent -- out[0] = (f[1] - f[0]) / (x[1] - x[0])
            out[tuple(slice1)] = (f[tuple(slice2)] - f[tuple(slice3)]) / dx_0

            slice1[axis] = -1
            slice2[axis] = -1
            slice3[axis] = -2
            dx_n = ax_dx if uniform_spacing else ax_dx[-1]
            # 1D equivalent -- out[-1] = (f[-1] - f[-2]) / (x[-1] - x[-2])
            out[tuple(slice1)] = (f[tuple(slice2)] - f[tuple(slice3)]) / dx_n

        # Numerical differentiation: 2nd order edges
        else:
            slice1[axis] = 0
            slice2[axis] = 0
            slice3[axis] = 1
            slice4[axis] = 2
            if uniform_spacing:
                a = -1.5 / ax_dx
                b = 2. / ax_dx
                c = -0.5 / ax_dx
            else:
                dx1 = ax_dx[0]
                dx2 = ax_dx[1]
                a = -(2. * dx1 + dx2) / (dx1 * (dx1 + dx2))
                b = (dx1 + dx2) / (dx1 * dx2)
                c = - dx1 / (dx2 * (dx1 + dx2))
            # 1D equivalent -- out[0] = a * f[0] + b * f[1] + c * f[2]
            out[tuple(slice1)] = a * f[tuple(slice2)] + b * f[tuple(slice3)] \
                                                        + c * f[tuple(slice4)]

            slice1[axis] = -1
            slice2[axis] = -3
            slice3[axis] = -2
            slice4[axis] = -1
            if uniform_spacing:
                a = 0.5 / ax_dx
                b = -2. / ax_dx
                c = 1.5 / ax_dx
            else:
                dx1 = ax_dx[-2]
                dx2 = ax_dx[-1]
                a = (dx2) / (dx1 * (dx1 + dx2))
                b = - (dx2 + dx1) / (dx1 * dx2)
                c = (2. * dx2 + dx1) / (dx2 * (dx1 + dx2))
            # 1D equivalent -- out[-1] = a * f[-3] + b * f[-2] + c * f[-1]
            out[tuple(slice1)] = a * f[tuple(slice2)] + b * f[tuple(slice3)] \
                                                        + c * f[tuple(slice4)]

        outvals.append(out)

        # reset the slice object in this dimension to ":"
        slice1[axis] = slice(None)
        slice2[axis] = slice(None)
        slice3[axis] = slice(None)
        slice4[axis] = slice(None)

    if len_axes == 1:
        return outvals[0]
    return tuple(outvals)


def _diff_dispatcher(a, n=None, axis=None, prepend=None, append=None):
    return (a, prepend, append)


@array_function_dispatch(_diff_dispatcher)
def diff(a, n=1, axis=-1, prepend=np._NoValue, append=np._NoValue):
    """
    Calculate the n-th discrete difference along the given axis.

    The first difference is given by ``out[i] = a[i+1] - a[i]`` along
    the given axis, higher differences are calculated by using `diff`
    recursively.

    Parameters
    ----------
    a : array_like
        Input array
    n : int, optional
        The number of times values are differenced. If zero, the input
        is returned as-is.
    axis : int, optional
        The axis along which the difference is taken, default is the
        last axis.
    prepend, append : array_like, optional
        Values to prepend or append to `a` along axis prior to
        performing the difference.  Scalar values are expanded to
        arrays with length 1 in the direction of axis and the shape
        of the input array in along all other axes.  Otherwise the
        dimension and shape must match `a` except along axis.

    Returns
    -------
    diff : ndarray
        The n-th differences. The shape of the output is the same as `a`
        except along `axis` where the dimension is smaller by `n`. The
        type of the output is the same as the type of the difference
        between any two elements of `a`. This is the same as the type of
        `a` in most cases. A notable exception is `datetime64`, which
        results in a `timedelta64` output array.

    See Also
    --------
    gradient, ediff1d, cumsum

    Notes
    -----
    Type is preserved for boolean arrays, so the result will contain
    `False` when consecutive elements are the same and `True` when they
    differ.

    For unsigned integer arrays, the results will also be unsigned. This
    should not be surprising, as the result is consistent with
    calculating the difference directly:

    >>> u8_arr = np.array([1, 0], dtype=np.uint8)
    >>> np.diff(u8_arr)
    array([255], dtype=uint8)
    >>> u8_arr[1,...] - u8_arr[0,...]
    np.uint8(255)

    If this is not desirable, then the array should be cast to a larger
    integer type first:

    >>> i16_arr = u8_arr.astype(np.int16)
    >>> np.diff(i16_arr)
    array([-1], dtype=int16)

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 4, 7, 0])
    >>> np.diff(x)
    array([ 1,  2,  3, -7])
    >>> np.diff(x, n=2)
    array([  1,   1, -10])

    >>> x = np.array([[1, 3, 6, 10], [0, 5, 6, 8]])
    >>> np.diff(x)
    array([[2, 3, 4],
           [5, 1, 2]])
    >>> np.diff(x, axis=0)
    array([[-1,  2,  0, -2]])

    >>> x = np.arange('1066-10-13', '1066-10-16', dtype=np.datetime64)
    >>> np.diff(x)
    array([1, 1], dtype='timedelta64[D]')

    """
    if n == 0:
        return a
    if n < 0:
        raise ValueError(
            "order must be non-negative but got " + repr(n))

    a = asanyarray(a)
    nd = a.ndim
    if nd == 0:
        raise ValueError("diff requires input that is at least one dimensional")
    axis = normalize_axis_index(axis, nd)

    combined = []
    if prepend is not np._NoValue:
        prepend = np.asanyarray(prepend)
        if prepend.ndim == 0:
            shape = list(a.shape)
            shape[axis] = 1
            prepend = np.broadcast_to(prepend, tuple(shape))
        combined.append(prepend)

    combined.append(a)

    if append is not np._NoValue:
        append = np.asanyarray(append)
        if append.ndim == 0:
            shape = list(a.shape)
            shape[axis] = 1
            append = np.broadcast_to(append, tuple(shape))
        combined.append(append)

    if len(combined) > 1:
        a = np.concatenate(combined, axis)

    slice1 = [slice(None)] * nd
    slice2 = [slice(None)] * nd
    slice1[axis] = slice(1, None)
    slice2[axis] = slice(None, -1)
    slice1 = tuple(slice1)
    slice2 = tuple(slice2)

    op = not_equal if a.dtype == np.bool else subtract
    for _ in range(n):
        a = op(a[slice1], a[slice2])

    return a


def _interp_dispatcher(x, xp, fp, left=None, right=None, period=None):
    return (x, xp, fp)


@array_function_dispatch(_interp_dispatcher)
def interp(x, xp, fp, left=None, right=None, period=None):
    """
    One-dimensional linear interpolation for monotonically increasing sample points.

    Returns the one-dimensional piecewise linear interpolant to a function
    with given discrete data points (`xp`, `fp`), evaluated at `x`.

    Parameters
    ----------
    x : array_like
        The x-coordinates at which to evaluate the interpolated values.

    xp : 1-D sequence of floats
        The x-coordinates of the data points, must be increasing if argument
        `period` is not specified. Otherwise, `xp` is internally sorted after
        normalizing the periodic boundaries with ``xp = xp % period``.

    fp : 1-D sequence of float or complex
        The y-coordinates of the data points, same length as `xp`.

    left : optional float or complex corresponding to fp
        Value to return for `x < xp[0]`, default is `fp[0]`.

    right : optional float or complex corresponding to fp
        Value to return for `x > xp[-1]`, default is `fp[-1]`.

    period : None or float, optional
        A period for the x-coordinates. This parameter allows the proper
        interpolation of angular x-coordinates. Parameters `left` and `right`
        are ignored if `period` is specified.

    Returns
    -------
    y : float or complex (corresponding to fp) or ndarray
        The interpolated values, same shape as `x`.

    Raises
    ------
    ValueError
        If `xp` and `fp` have different length
        If `xp` or `fp` are not 1-D sequences
        If `period == 0`

    See Also
    --------
    scipy.interpolate

    Warnings
    --------
    The x-coordinate sequence is expected to be increasing, but this is not
    explicitly enforced.  However, if the sequence `xp` is non-increasing,
    interpolation results are meaningless.

    Note that, since NaN is unsortable, `xp` also cannot contain NaNs.

    A simple check for `xp` being strictly increasing is::

        np.all(np.diff(xp) > 0)

    Examples
    --------
    >>> import numpy as np
    >>> xp = [1, 2, 3]
    >>> fp = [3, 2, 0]
    >>> np.interp(2.5, xp, fp)
    1.0
    >>> np.interp([0, 1, 1.5, 2.72, 3.14], xp, fp)
    array([3.  , 3.  , 2.5 , 0.56, 0.  ])
    >>> UNDEF = -99.0
    >>> np.interp(3.14, xp, fp, right=UNDEF)
    -99.0

    Plot an interpolant to the sine function:

    >>> x = np.linspace(0, 2*np.pi, 10)
    >>> y = np.sin(x)
    >>> xvals = np.linspace(0, 2*np.pi, 50)
    >>> yinterp = np.interp(xvals, x, y)
    >>> import matplotlib.pyplot as plt
    >>> plt.plot(x, y, 'o')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.plot(xvals, yinterp, '-x')
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.show()

    Interpolation with periodic x-coordinates:

    >>> x = [-180, -170, -185, 185, -10, -5, 0, 365]
    >>> xp = [190, -190, 350, -350]
    >>> fp = [5, 10, 3, 4]
    >>> np.interp(x, xp, fp, period=360)
    array([7.5 , 5.  , 8.75, 6.25, 3.  , 3.25, 3.5 , 3.75])

    Complex interpolation:

    >>> x = [1.5, 4.0]
    >>> xp = [2,3,5]
    >>> fp = [1.0j, 0, 2+3j]
    >>> np.interp(x, xp, fp)
    array([0.+1.j , 1.+1.5j])

    """

    fp = np.asarray(fp)

    if np.iscomplexobj(fp):
        interp_func = compiled_interp_complex
        input_dtype = np.complex128
    else:
        interp_func = compiled_interp
        input_dtype = np.float64

    if period is not None:
        if period == 0:
            raise ValueError("period must be a non-zero value")
        period = abs(period)
        left = None
        right = None

        x = np.asarray(x, dtype=np.float64)
        xp = np.asarray(xp, dtype=np.float64)
        fp = np.asarray(fp, dtype=input_dtype)

        if xp.ndim != 1 or fp.ndim != 1:
            raise ValueError("Data points must be 1-D sequences")
        if xp.shape[0] != fp.shape[0]:
            raise ValueError("fp and xp are not of the same length")
        # normalizing periodic boundaries
        x = x % period
        xp = xp % period
        asort_xp = np.argsort(xp)
        xp = xp[asort_xp]
        fp = fp[asort_xp]
        xp = np.concatenate((xp[-1:] - period, xp, xp[0:1] + period))
        fp = np.concatenate((fp[-1:], fp, fp[0:1]))

    return interp_func(x, xp, fp, left, right)


def _angle_dispatcher(z, deg=None):
    return (z,)


@array_function_dispatch(_angle_dispatcher)
def angle(z, deg=False):
    """
    Return the angle of the complex argument.

    Parameters
    ----------
    z : array_like
        A complex number or sequence of complex numbers.
    deg : bool, optional
        Return angle in degrees if True, radians if False (default).

    Returns
    -------
    angle : ndarray or scalar
        The counterclockwise angle from the positive real axis on the complex
        plane in the range ``(-pi, pi]``, with dtype as numpy.float64.

    See Also
    --------
    arctan2
    absolute

    Notes
    -----
    This function passes the imaginary and real parts of the argument to
    `arctan2` to compute the result; consequently, it follows the convention
    of `arctan2` when the magnitude of the argument is zero. See example.

    Examples
    --------
    >>> import numpy as np
    >>> np.angle([1.0, 1.0j, 1+1j])               # in radians
    array([ 0.        ,  1.57079633,  0.78539816]) # may vary
    >>> np.angle(1+1j, deg=True)                  # in degrees
    45.0
    >>> np.angle([0., -0., complex(0., -0.), complex(-0., -0.)])  # convention
    array([ 0.        ,  3.14159265, -0.        , -3.14159265])

    """
    z = asanyarray(z)
    if issubclass(z.dtype.type, _nx.complexfloating):
        zimag = z.imag
        zreal = z.real
    else:
        zimag = 0
        zreal = z

    a = arctan2(zimag, zreal)
    if deg:
        a *= 180 / pi
    return a


def _unwrap_dispatcher(p, discont=None, axis=None, *, period=None):
    return (p,)


@array_function_dispatch(_unwrap_dispatcher)
def unwrap(p, discont=None, axis=-1, *, period=2 * pi):
    r"""
    Unwrap by taking the complement of large deltas with respect to the period.

    This unwraps a signal `p` by changing elements which have an absolute
    difference from their predecessor of more than ``max(discont, period/2)``
    to their `period`-complementary values.

    For the default case where `period` is :math:`2\pi` and `discont` is
    :math:`\pi`, this unwraps a radian phase `p` such that adjacent differences
    are never greater than :math:`\pi` by adding :math:`2k\pi` for some
    integer :math:`k`.

    Parameters
    ----------
    p : array_like
        Input array.
    discont : float, optional
        Maximum discontinuity between values, default is ``period/2``.
        Values below ``period/2`` are treated as if they were ``period/2``.
        To have an effect different from the default, `discont` should be
        larger than ``period/2``.
    axis : int, optional
        Axis along which unwrap will operate, default is the last axis.
    period : float, optional
        Size of the range over which the input wraps. By default, it is
        ``2 pi``.

        .. versionadded:: 1.21.0

    Returns
    -------
    out : ndarray
        Output array.

    See Also
    --------
    rad2deg, deg2rad

    Notes
    -----
    If the discontinuity in `p` is smaller than ``period/2``,
    but larger than `discont`, no unwrapping is done because taking
    the complement would only make the discontinuity larger.

    Examples
    --------
    >>> import numpy as np
    >>> phase = np.linspace(0, np.pi, num=5)
    >>> phase[3:] += np.pi
    >>> phase
    array([ 0.        ,  0.78539816,  1.57079633,  5.49778714,  6.28318531]) # may vary
    >>> np.unwrap(phase)
    array([ 0.        ,  0.78539816,  1.57079633, -0.78539816,  0.        ]) # may vary
    >>> np.unwrap([0, 1, 2, -1, 0], period=4)
    array([0, 1, 2, 3, 4])
    >>> np.unwrap([ 1, 2, 3, 4, 5, 6, 1, 2, 3], period=6)
    array([1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> np.unwrap([2, 3, 4, 5, 2, 3, 4, 5], period=4)
    array([2, 3, 4, 5, 6, 7, 8, 9])
    >>> phase_deg = np.mod(np.linspace(0 ,720, 19), 360) - 180
    >>> np.unwrap(phase_deg, period=360)
    array([-180., -140., -100.,  -60.,  -20.,   20.,   60.,  100.,  140.,
            180.,  220.,  260.,  300.,  340.,  380.,  420.,  460.,  500.,
            540.])
    """
    p = asarray(p)
    nd = p.ndim
    dd = diff(p, axis=axis)
    if discont is None:
        discont = period / 2
    slice1 = [slice(None, None)] * nd     # full slices
    slice1[axis] = slice(1, None)
    slice1 = tuple(slice1)
    dtype = np.result_type(dd, period)
    if _nx.issubdtype(dtype, _nx.integer):
        interval_high, rem = divmod(period, 2)
        boundary_ambiguous = rem == 0
    else:
        interval_high = period / 2
        boundary_ambiguous = True
    interval_low = -interval_high
    ddmod = mod(dd - interval_low, period) + interval_low
    if boundary_ambiguous:
        # for `mask = (abs(dd) == period/2)`, the above line made
        # `ddmod[mask] == -period/2`. correct these such that
        # `ddmod[mask] == sign(dd[mask])*period/2`.
        _nx.copyto(ddmod, interval_high,
                   where=(ddmod == interval_low) & (dd > 0))
    ph_correct = ddmod - dd
    _nx.copyto(ph_correct, 0, where=abs(dd) < discont)
    up = array(p, copy=True, dtype=dtype)
    up[slice1] = p[slice1] + ph_correct.cumsum(axis)
    return up


def _sort_complex(a):
    return (a,)


@array_function_dispatch(_sort_complex)
def sort_complex(a):
    """
    Sort a complex array using the real part first, then the imaginary part.

    Parameters
    ----------
    a : array_like
        Input array

    Returns
    -------
    out : complex ndarray
        Always returns a sorted complex array.

    Examples
    --------
    >>> import numpy as np
    >>> np.sort_complex([5, 3, 6, 2, 1])
    array([1.+0.j, 2.+0.j, 3.+0.j, 5.+0.j, 6.+0.j])

    >>> np.sort_complex([1 + 2j, 2 - 1j, 3 - 2j, 3 - 3j, 3 + 5j])
    array([1.+2.j,  2.-1.j,  3.-3.j,  3.-2.j,  3.+5.j])

    """
    b = array(a, copy=True)
    b.sort()
    if not issubclass(b.dtype.type, _nx.complexfloating):
        if b.dtype.char in 'bhBH':
            return b.astype('F')
        elif b.dtype.char == 'g':
            return b.astype('G')
        else:
            return b.astype('D')
    else:
        return b


def _arg_trim_zeros(filt):
    """Return indices of the first and last non-zero element.

    Parameters
    ----------
    filt : array_like
        Input array.

    Returns
    -------
    start, stop : ndarray
        Two arrays containing the indices of the first and last non-zero
        element in each dimension.

    See also
    --------
    trim_zeros

    Examples
    --------
    >>> import numpy as np
    >>> _arg_trim_zeros(np.array([0, 0, 1, 1, 0]))
    (array([2]), array([3]))
    """
    nonzero = (
        np.argwhere(filt)
        if filt.dtype != np.object_
        # Historically, `trim_zeros` treats `None` in an object array
        # as non-zero while argwhere doesn't, account for that
        else np.argwhere(filt != 0)
    )
    if nonzero.size == 0:
        start = stop = np.array([], dtype=np.intp)
    else:
        start = nonzero.min(axis=0)
        stop = nonzero.max(axis=0)
    return start, stop


def _trim_zeros(filt, trim=None, axis=None):
    return (filt,)


@array_function_dispatch(_trim_zeros)
def trim_zeros(filt, trim='fb', axis=None):
    """Remove values along a dimension which are zero along all other.

    Parameters
    ----------
    filt : array_like
        Input array.
    trim : {"fb", "f", "b"}, optional
        A string with 'f' representing trim from front and 'b' to trim from
        back. By default, zeros are trimmed on both sides.
        Front and back refer to the edges of a dimension, with "front" referring
        to the side with the lowest index 0, and "back" referring to the highest
        index (or index -1).
    axis : int or sequence, optional
        If None, `filt` is cropped such that the smallest bounding box is
        returned that still contains all values which are not zero.
        If an axis is specified, `filt` will be sliced in that dimension only
        on the sides specified by `trim`. The remaining area will be the
        smallest that still contains all values wich are not zero.

        .. versionadded:: 2.2.0

    Returns
    -------
    trimmed : ndarray or sequence
        The result of trimming the input. The number of dimensions and the
        input data type are preserved.

    Notes
    -----
    For all-zero arrays, the first axis is trimmed first.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array((0, 0, 0, 1, 2, 3, 0, 2, 1, 0))
    >>> np.trim_zeros(a)
    array([1, 2, 3, 0, 2, 1])

    >>> np.trim_zeros(a, trim='b')
    array([0, 0, 0, ..., 0, 2, 1])

    Multiple dimensions are supported.

    >>> b = np.array([[0, 0, 2, 3, 0, 0],
    ...               [0, 1, 0, 3, 0, 0],
    ...               [0, 0, 0, 0, 0, 0]])
    >>> np.trim_zeros(b)
    array([[0, 2, 3],
           [1, 0, 3]])

    >>> np.trim_zeros(b, axis=-1)
    array([[0, 2, 3],
           [1, 0, 3],
           [0, 0, 0]])

    The input data type is preserved, list/tuple in means list/tuple out.

    >>> np.trim_zeros([0, 1, 2, 0])
    [1, 2]

    """
    filt_ = np.asarray(filt)

    trim = trim.lower()
    if trim not in {"fb", "bf", "f", "b"}:
        raise ValueError(f"unexpected character(s) in `trim`: {trim!r}")

    start, stop = _arg_trim_zeros(filt_)
    stop += 1  # Adjust for slicing

    if start.size == 0:
        # filt is all-zero -> assign same values to start and stop so that
        # resulting slice will be empty
        start = stop = np.zeros(filt_.ndim, dtype=np.intp)
    else:
        if 'f' not in trim:
            start = (None,) * filt_.ndim
        if 'b' not in trim:
            stop = (None,) * filt_.ndim

    if len(start) == 1:
        # filt is 1D -> don't use multi-dimensional slicing to preserve
        # non-array input types
        sl = slice(start[0], stop[0])
    elif axis is None:
        # trim all axes
        sl = tuple(slice(*x) for x in zip(start, stop))
    else:
        # only trim single axis
        axis = normalize_axis_index(axis, filt_.ndim)
        sl = (slice(None),) * axis + (slice(start[axis], stop[axis]),) + (...,)

    trimmed = filt[sl]
    return trimmed


def _extract_dispatcher(condition, arr):
    return (condition, arr)


@array_function_dispatch(_extract_dispatcher)
def extract(condition, arr):
    """
    Return the elements of an array that satisfy some condition.

    This is equivalent to ``np.compress(ravel(condition), ravel(arr))``.  If
    `condition` is boolean ``np.extract`` is equivalent to ``arr[condition]``.

    Note that `place` does the exact opposite of `extract`.

    Parameters
    ----------
    condition : array_like
        An array whose nonzero or True entries indicate the elements of `arr`
        to extract.
    arr : array_like
        Input array of the same size as `condition`.

    Returns
    -------
    extract : ndarray
        Rank 1 array of values from `arr` where `condition` is True.

    See Also
    --------
    take, put, copyto, compress, place

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.arange(12).reshape((3, 4))
    >>> arr
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11]])
    >>> condition = np.mod(arr, 3)==0
    >>> condition
    array([[ True, False, False,  True],
           [False, False,  True, False],
           [False,  True, False, False]])
    >>> np.extract(condition, arr)
    array([0, 3, 6, 9])


    If `condition` is boolean:

    >>> arr[condition]
    array([0, 3, 6, 9])

    """
    return _nx.take(ravel(arr), nonzero(ravel(condition))[0])


def _place_dispatcher(arr, mask, vals):
    return (arr, mask, vals)


@array_function_dispatch(_place_dispatcher)
def place(arr, mask, vals):
    """
    Change elements of an array based on conditional and input values.

    Similar to ``np.copyto(arr, vals, where=mask)``, the difference is that
    `place` uses the first N elements of `vals`, where N is the number of
    True values in `mask`, while `copyto` uses the elements where `mask`
    is True.

    Note that `extract` does the exact opposite of `place`.

    Parameters
    ----------
    arr : ndarray
        Array to put data into.
    mask : array_like
        Boolean mask array. Must have the same size as `a`.
    vals : 1-D sequence
        Values to put into `a`. Only the first N elements are used, where
        N is the number of True values in `mask`. If `vals` is smaller
        than N, it will be repeated, and if elements of `a` are to be masked,
        this sequence must be non-empty.

    See Also
    --------
    copyto, put, take, extract

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.arange(6).reshape(2, 3)
    >>> np.place(arr, arr>2, [44, 55])
    >>> arr
    array([[ 0,  1,  2],
           [44, 55, 44]])

    """
    return _place(arr, mask, vals)


def disp(mesg, device=None, linefeed=True):
    """
    Display a message on a device.

    .. deprecated:: 2.0
        Use your own printing function instead.

    Parameters
    ----------
    mesg : str
        Message to display.
    device : object
        Device to write message. If None, defaults to ``sys.stdout`` which is
        very similar to ``print``. `device` needs to have ``write()`` and
        ``flush()`` methods.
    linefeed : bool, optional
        Option whether to print a line feed or not. Defaults to True.

    Raises
    ------
    AttributeError
        If `device` does not have a ``write()`` or ``flush()`` method.

    Examples
    --------
    >>> import numpy as np

    Besides ``sys.stdout``, a file-like object can also be used as it has
    both required methods:

    >>> from io import StringIO
    >>> buf = StringIO()
    >>> np.disp('"Display" in a file', device=buf)
    >>> buf.getvalue()
    '"Display" in a file\\n'

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`disp` is deprecated, "
        "use your own printing function instead. "
        "(deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    if device is None:
        device = sys.stdout
    if linefeed:
        device.write(f'{mesg}\n')
    else:
        device.write(f'{mesg}')
    device.flush()


# See https://docs.scipy.org/doc/numpy/reference/c-api.generalized-ufuncs.html
_DIMENSION_NAME = r'\w+'
_CORE_DIMENSION_LIST = f'(?:{_DIMENSION_NAME}(?:,{_DIMENSION_NAME})*)?'
_ARGUMENT = fr'\({_CORE_DIMENSION_LIST}\)'
_ARGUMENT_LIST = f'{_ARGUMENT}(?:,{_ARGUMENT})*'
_SIGNATURE = f'^{_ARGUMENT_LIST}->{_ARGUMENT_LIST}$'


def _parse_gufunc_signature(signature):
    """
    Parse string signatures for a generalized universal function.

    Arguments
    ---------
    signature : string
        Generalized universal function signature, e.g., ``(m,n),(n,p)->(m,p)``
        for ``np.matmul``.

    Returns
    -------
    Tuple of input and output core dimensions parsed from the signature, each
    of the form List[Tuple[str, ...]].
    """
    signature = re.sub(r'\s+', '', signature)

    if not re.match(_SIGNATURE, signature):
        raise ValueError(
            f'not a valid gufunc signature: {signature}')
    return tuple([tuple(re.findall(_DIMENSION_NAME, arg))
                  for arg in re.findall(_ARGUMENT, arg_list)]
                 for arg_list in signature.split('->'))


def _update_dim_sizes(dim_sizes, arg, core_dims):
    """
    Incrementally check and update core dimension sizes for a single argument.

    Arguments
    ---------
    dim_sizes : Dict[str, int]
        Sizes of existing core dimensions. Will be updated in-place.
    arg : ndarray
        Argument to examine.
    core_dims : Tuple[str, ...]
        Core dimensions for this argument.
    """
    if not core_dims:
        return

    num_core_dims = len(core_dims)
    if arg.ndim < num_core_dims:
        raise ValueError(
            '%d-dimensional argument does not have enough '
            'dimensions for all core dimensions %r'
            % (arg.ndim, core_dims))

    core_shape = arg.shape[-num_core_dims:]
    for dim, size in zip(core_dims, core_shape):
        if dim in dim_sizes:
            if size != dim_sizes[dim]:
                raise ValueError(
                    'inconsistent size for core dimension %r: %r vs %r'
                    % (dim, size, dim_sizes[dim]))
        else:
            dim_sizes[dim] = size


def _parse_input_dimensions(args, input_core_dims):
    """
    Parse broadcast and core dimensions for vectorize with a signature.

    Arguments
    ---------
    args : Tuple[ndarray, ...]
        Tuple of input arguments to examine.
    input_core_dims : List[Tuple[str, ...]]
        List of core dimensions corresponding to each input.

    Returns
    -------
    broadcast_shape : Tuple[int, ...]
        Common shape to broadcast all non-core dimensions to.
    dim_sizes : Dict[str, int]
        Common sizes for named core dimensions.
    """
    broadcast_args = []
    dim_sizes = {}
    for arg, core_dims in zip(args, input_core_dims):
        _update_dim_sizes(dim_sizes, arg, core_dims)
        ndim = arg.ndim - len(core_dims)
        dummy_array = np.lib.stride_tricks.as_strided(0, arg.shape[:ndim])
        broadcast_args.append(dummy_array)
    broadcast_shape = np.lib._stride_tricks_impl._broadcast_shape(
        *broadcast_args
    )
    return broadcast_shape, dim_sizes


def _calculate_shapes(broadcast_shape, dim_sizes, list_of_core_dims):
    """Helper for calculating broadcast shapes with core dimensions."""
    return [broadcast_shape + tuple(dim_sizes[dim] for dim in core_dims)
            for core_dims in list_of_core_dims]


def _create_arrays(broadcast_shape, dim_sizes, list_of_core_dims, dtypes,
                   results=None):
    """Helper for creating output arrays in vectorize."""
    shapes = _calculate_shapes(broadcast_shape, dim_sizes, list_of_core_dims)
    if dtypes is None:
        dtypes = [None] * len(shapes)
    if results is None:
        arrays = tuple(np.empty(shape=shape, dtype=dtype)
                       for shape, dtype in zip(shapes, dtypes))
    else:
        arrays = tuple(np.empty_like(result, shape=shape, dtype=dtype)
                       for result, shape, dtype
                       in zip(results, shapes, dtypes))
    return arrays


def _get_vectorize_dtype(dtype):
    if dtype.char in "SU":
        return dtype.char
    return dtype


@set_module('numpy')
class vectorize:
    """
    vectorize(pyfunc=np._NoValue, otypes=None, doc=None, excluded=None,
    cache=False, signature=None)

    Returns an object that acts like pyfunc, but takes arrays as input.

    Define a vectorized function which takes a nested sequence of objects or
    numpy arrays as inputs and returns a single numpy array or a tuple of numpy
    arrays. The vectorized function evaluates `pyfunc` over successive tuples
    of the input arrays like the python map function, except it uses the
    broadcasting rules of numpy.

    The data type of the output of `vectorized` is determined by calling
    the function with the first element of the input.  This can be avoided
    by specifying the `otypes` argument.

    Parameters
    ----------
    pyfunc : callable, optional
        A python function or method.
        Can be omitted to produce a decorator with keyword arguments.
    otypes : str or list of dtypes, optional
        The output data type. It must be specified as either a string of
        typecode characters or a list of data type specifiers. There should
        be one data type specifier for each output.
    doc : str, optional
        The docstring for the function. If None, the docstring will be the
        ``pyfunc.__doc__``.
    excluded : set, optional
        Set of strings or integers representing the positional or keyword
        arguments for which the function will not be vectorized. These will be
        passed directly to `pyfunc` unmodified.

    cache : bool, optional
        If `True`, then cache the first function call that determines the number
        of outputs if `otypes` is not provided.

    signature : string, optional
        Generalized universal function signature, e.g., ``(m,n),(n)->(m)`` for
        vectorized matrix-vector multiplication. If provided, ``pyfunc`` will
        be called with (and expected to return) arrays with shapes given by the
        size of corresponding core dimensions. By default, ``pyfunc`` is
        assumed to take scalars as input and output.

    Returns
    -------
    out : callable
        A vectorized function if ``pyfunc`` was provided,
        a decorator otherwise.

    See Also
    --------
    frompyfunc : Takes an arbitrary Python function and returns a ufunc

    Notes
    -----
    The `vectorize` function is provided primarily for convenience, not for
    performance. The implementation is essentially a for loop.

    If `otypes` is not specified, then a call to the function with the
    first argument will be used to determine the number of outputs.  The
    results of this call will be cached if `cache` is `True` to prevent
    calling the function twice.  However, to implement the cache, the
    original function must be wrapped which will slow down subsequent
    calls, so only do this if your function is expensive.

    The new keyword argument interface and `excluded` argument support
    further degrades performance.

    References
    ----------
    .. [1] :doc:`/reference/c-api/generalized-ufuncs`

    Examples
    --------
    >>> import numpy as np
    >>> def myfunc(a, b):
    ...     "Return a-b if a>b, otherwise return a+b"
    ...     if a > b:
    ...         return a - b
    ...     else:
    ...         return a + b

    >>> vfunc = np.vectorize(myfunc)
    >>> vfunc([1, 2, 3, 4], 2)
    array([3, 4, 1, 2])

    The docstring is taken from the input function to `vectorize` unless it
    is specified:

    >>> vfunc.__doc__
    'Return a-b if a>b, otherwise return a+b'
    >>> vfunc = np.vectorize(myfunc, doc='Vectorized `myfunc`')
    >>> vfunc.__doc__
    'Vectorized `myfunc`'

    The output type is determined by evaluating the first element of the input,
    unless it is specified:

    >>> out = vfunc([1, 2, 3, 4], 2)
    >>> type(out[0])
    <class 'numpy.int64'>
    >>> vfunc = np.vectorize(myfunc, otypes=[float])
    >>> out = vfunc([1, 2, 3, 4], 2)
    >>> type(out[0])
    <class 'numpy.float64'>

    The `excluded` argument can be used to prevent vectorizing over certain
    arguments.  This can be useful for array-like arguments of a fixed length
    such as the coefficients for a polynomial as in `polyval`:

    >>> def mypolyval(p, x):
    ...     _p = list(p)
    ...     res = _p.pop(0)
    ...     while _p:
    ...         res = res*x + _p.pop(0)
    ...     return res

    Here, we exclude the zeroth argument from vectorization whether it is
    passed by position or keyword.

    >>> vpolyval = np.vectorize(mypolyval, excluded={0, 'p'})
    >>> vpolyval([1, 2, 3], x=[0, 1])
    array([3, 6])
    >>> vpolyval(p=[1, 2, 3], x=[0, 1])
    array([3, 6])

    The `signature` argument allows for vectorizing functions that act on
    non-scalar arrays of fixed length. For example, you can use it for a
    vectorized calculation of Pearson correlation coefficient and its p-value:

    >>> import scipy.stats
    >>> pearsonr = np.vectorize(scipy.stats.pearsonr,
    ...                 signature='(n),(n)->(),()')
    >>> pearsonr([[0, 1, 2, 3]], [[1, 2, 3, 4], [4, 3, 2, 1]])
    (array([ 1., -1.]), array([ 0.,  0.]))

    Or for a vectorized convolution:

    >>> convolve = np.vectorize(np.convolve, signature='(n),(m)->(k)')
    >>> convolve(np.eye(4), [1, 2, 1])
    array([[1., 2., 1., 0., 0., 0.],
           [0., 1., 2., 1., 0., 0.],
           [0., 0., 1., 2., 1., 0.],
           [0., 0., 0., 1., 2., 1.]])

    Decorator syntax is supported.  The decorator can be called as
    a function to provide keyword arguments:

    >>> @np.vectorize
    ... def identity(x):
    ...     return x
    ...
    >>> identity([0, 1, 2])
    array([0, 1, 2])
    >>> @np.vectorize(otypes=[float])
    ... def as_float(x):
    ...     return x
    ...
    >>> as_float([0, 1, 2])
    array([0., 1., 2.])
    """
    def __init__(self, pyfunc=np._NoValue, otypes=None, doc=None,
                 excluded=None, cache=False, signature=None):

        if (pyfunc != np._NoValue) and (not callable(pyfunc)):
            # Splitting the error message to keep
            # the length below 79 characters.
            part1 = "When used as a decorator, "
            part2 = "only accepts keyword arguments."
            raise TypeError(part1 + part2)

        self.pyfunc = pyfunc
        self.cache = cache
        self.signature = signature
        if pyfunc != np._NoValue and hasattr(pyfunc, '__name__'):
            self.__name__ = pyfunc.__name__

        self._ufunc = {}    # Caching to improve default performance
        self._doc = None
        self.__doc__ = doc
        if doc is None and hasattr(pyfunc, '__doc__'):
            self.__doc__ = pyfunc.__doc__
        else:
            self._doc = doc

        if isinstance(otypes, str):
            for char in otypes:
                if char not in typecodes['All']:
                    raise ValueError(f"Invalid otype specified: {char}")
        elif iterable(otypes):
            otypes = [_get_vectorize_dtype(_nx.dtype(x)) for x in otypes]
        elif otypes is not None:
            raise ValueError("Invalid otype specification")
        self.otypes = otypes

        # Excluded variable support
        if excluded is None:
            excluded = set()
        self.excluded = set(excluded)

        if signature is not None:
            self._in_and_out_core_dims = _parse_gufunc_signature(signature)
        else:
            self._in_and_out_core_dims = None

    def _init_stage_2(self, pyfunc, *args, **kwargs):
        self.__name__ = pyfunc.__name__
        self.pyfunc = pyfunc
        if self._doc is None:
            self.__doc__ = pyfunc.__doc__
        else:
            self.__doc__ = self._doc

    def _call_as_normal(self, *args, **kwargs):
        """
        Return arrays with the results of `pyfunc` broadcast (vectorized) over
        `args` and `kwargs` not in `excluded`.
        """
        excluded = self.excluded
        if not kwargs and not excluded:
            func = self.pyfunc
            vargs = args
        else:
            # The wrapper accepts only positional arguments: we use `names` and
            # `inds` to mutate `the_args` and `kwargs` to pass to the original
            # function.
            nargs = len(args)

            names = [_n for _n in kwargs if _n not in excluded]
            inds = [_i for _i in range(nargs) if _i not in excluded]
            the_args = list(args)

            def func(*vargs):
                for _n, _i in enumerate(inds):
                    the_args[_i] = vargs[_n]
                kwargs.update(zip(names, vargs[len(inds):]))
                return self.pyfunc(*the_args, **kwargs)

            vargs = [args[_i] for _i in inds]
            vargs.extend([kwargs[_n] for _n in names])

        return self._vectorize_call(func=func, args=vargs)

    def __call__(self, *args, **kwargs):
        if self.pyfunc is np._NoValue:
            self._init_stage_2(*args, **kwargs)
            return self

        return self._call_as_normal(*args, **kwargs)

    def _get_ufunc_and_otypes(self, func, args):
        """Return (ufunc, otypes)."""
        # frompyfunc will fail if args is empty
        if not args:
            raise ValueError('args can not be empty')

        if self.otypes is not None:
            otypes = self.otypes

            # self._ufunc is a dictionary whose keys are the number of
            # arguments (i.e. len(args)) and whose values are ufuncs created
            # by frompyfunc. len(args) can be different for different calls if
            # self.pyfunc has parameters with default values.  We only use the
            # cache when func is self.pyfunc, which occurs when the call uses
            # only positional arguments and no arguments are excluded.

            nin = len(args)
            nout = len(self.otypes)
            if func is not self.pyfunc or nin not in self._ufunc:
                ufunc = frompyfunc(func, nin, nout)
            else:
                ufunc = None  # We'll get it from self._ufunc
            if func is self.pyfunc:
                ufunc = self._ufunc.setdefault(nin, ufunc)
        else:
            # Get number of outputs and output types by calling the function on
            # the first entries of args.  We also cache the result to prevent
            # the subsequent call when the ufunc is evaluated.
            # Assumes that ufunc first evaluates the 0th elements in the input
            # arrays (the input values are not checked to ensure this)
            args = [asarray(a) for a in args]
            if builtins.any(arg.size == 0 for arg in args):
                raise ValueError('cannot call `vectorize` on size 0 inputs '
                                 'unless `otypes` is set')

            inputs = [arg.flat[0] for arg in args]
            outputs = func(*inputs)

            # Performance note: profiling indicates that -- for simple
            # functions at least -- this wrapping can almost double the
            # execution time.
            # Hence we make it optional.
            if self.cache:
                _cache = [outputs]

                def _func(*vargs):
                    if _cache:
                        return _cache.pop()
                    else:
                        return func(*vargs)
            else:
                _func = func

            if isinstance(outputs, tuple):
                nout = len(outputs)
            else:
                nout = 1
                outputs = (outputs,)

            otypes = ''.join([asarray(outputs[_k]).dtype.char
                              for _k in range(nout)])

            # Performance note: profiling indicates that creating the ufunc is
            # not a significant cost compared with wrapping so it seems not
            # worth trying to cache this.
            ufunc = frompyfunc(_func, len(args), nout)

        return ufunc, otypes

    def _vectorize_call(self, func, args):
        """Vectorized call to `func` over positional `args`."""
        if self.signature is not None:
            res = self._vectorize_call_with_signature(func, args)
        elif not args:
            res = func()
        else:
            ufunc, otypes = self._get_ufunc_and_otypes(func=func, args=args)
            # gh-29196: `dtype=object` should eventually be removed
            args = [asanyarray(a, dtype=object) for a in args]
            outputs = ufunc(*args, out=...)

            if ufunc.nout == 1:
                res = asanyarray(outputs, dtype=otypes[0])
            else:
                res = tuple(asanyarray(x, dtype=t)
                            for x, t in zip(outputs, otypes))
        return res

    def _vectorize_call_with_signature(self, func, args):
        """Vectorized call over positional arguments with a signature."""
        input_core_dims, output_core_dims = self._in_and_out_core_dims

        if len(args) != len(input_core_dims):
            raise TypeError('wrong number of positional arguments: '
                            'expected %r, got %r'
                            % (len(input_core_dims), len(args)))
        args = tuple(asanyarray(arg) for arg in args)

        broadcast_shape, dim_sizes = _parse_input_dimensions(
            args, input_core_dims)
        input_shapes = _calculate_shapes(broadcast_shape, dim_sizes,
                                         input_core_dims)
        args = [np.broadcast_to(arg, shape, subok=True)
                for arg, shape in zip(args, input_shapes)]

        outputs = None
        otypes = self.otypes
        nout = len(output_core_dims)

        for index in np.ndindex(*broadcast_shape):
            results = func(*(arg[index] for arg in args))

            n_results = len(results) if isinstance(results, tuple) else 1

            if nout != n_results:
                raise ValueError(
                    'wrong number of outputs from pyfunc: expected %r, got %r'
                    % (nout, n_results))

            if nout == 1:
                results = (results,)

            if outputs is None:
                for result, core_dims in zip(results, output_core_dims):
                    _update_dim_sizes(dim_sizes, result, core_dims)

                outputs = _create_arrays(broadcast_shape, dim_sizes,
                                         output_core_dims, otypes, results)

            for output, result in zip(outputs, results):
                output[index] = result

        if outputs is None:
            # did not call the function even once
            if otypes is None:
                raise ValueError('cannot call `vectorize` on size 0 inputs '
                                 'unless `otypes` is set')
            if builtins.any(dim not in dim_sizes
                            for dims in output_core_dims
                            for dim in dims):
                raise ValueError('cannot call `vectorize` with a signature '
                                 'including new output dimensions on size 0 '
                                 'inputs')
            outputs = _create_arrays(broadcast_shape, dim_sizes,
                                     output_core_dims, otypes)

        return outputs[0] if nout == 1 else outputs


def _cov_dispatcher(m, y=None, rowvar=None, bias=None, ddof=None,
                    fweights=None, aweights=None, *, dtype=None):
    return (m, y, fweights, aweights)


@array_function_dispatch(_cov_dispatcher)
def cov(m, y=None, rowvar=True, bias=False, ddof=None, fweights=None,
        aweights=None, *, dtype=None):
    """
    Estimate a covariance matrix, given data and weights.

    Covariance indicates the level to which two variables vary together.
    If we examine N-dimensional samples, :math:`X = [x_1, x_2, ... x_N]^T`,
    then the covariance matrix element :math:`C_{ij}` is the covariance of
    :math:`x_i` and :math:`x_j`. The element :math:`C_{ii}` is the variance
    of :math:`x_i`.

    See the notes for an outline of the algorithm.

    Parameters
    ----------
    m : array_like
        A 1-D or 2-D array containing multiple variables and observations.
        Each row of `m` represents a variable, and each column a single
        observation of all those variables. Also see `rowvar` below.
    y : array_like, optional
        An additional set of variables and observations. `y` has the same form
        as that of `m`.
    rowvar : bool, optional
        If `rowvar` is True (default), then each row represents a
        variable, with observations in the columns. Otherwise, the relationship
        is transposed: each column represents a variable, while the rows
        contain observations.
    bias : bool, optional
        Default normalization (False) is by ``(N - 1)``, where ``N`` is the
        number of observations given (unbiased estimate). If `bias` is True,
        then normalization is by ``N``. These values can be overridden by using
        the keyword ``ddof`` in numpy versions >= 1.5.
    ddof : int, optional
        If not ``None`` the default value implied by `bias` is overridden.
        Note that ``ddof=1`` will return the unbiased estimate, even if both
        `fweights` and `aweights` are specified, and ``ddof=0`` will return
        the simple average. See the notes for the details. The default value
        is ``None``.
    fweights : array_like, int, optional
        1-D array of integer frequency weights; the number of times each
        observation vector should be repeated.
    aweights : array_like, optional
        1-D array of observation vector weights. These relative weights are
        typically large for observations considered "important" and smaller for
        observations considered less "important". If ``ddof=0`` the array of
        weights can be used to assign probabilities to observation vectors.
    dtype : data-type, optional
        Data-type of the result. By default, the return data-type will have
        at least `numpy.float64` precision.

        .. versionadded:: 1.20

    Returns
    -------
    out : ndarray
        The covariance matrix of the variables.

    See Also
    --------
    corrcoef : Normalized covariance matrix

    Notes
    -----
    Assume that the observations are in the columns of the observation
    array `m` and let ``f = fweights`` and ``a = aweights`` for brevity. The
    steps to compute the weighted covariance are as follows::

        >>> m = np.arange(10, dtype=np.float64)
        >>> f = np.arange(10) * 2
        >>> a = np.arange(10) ** 2.
        >>> ddof = 1
        >>> w = f * a
        >>> v1 = np.sum(w)
        >>> v2 = np.sum(w * a)
        >>> m -= np.sum(m * w, axis=None, keepdims=True) / v1
        >>> cov = np.dot(m * w, m.T) * v1 / (v1**2 - ddof * v2)

    Note that when ``a == 1``, the normalization factor
    ``v1 / (v1**2 - ddof * v2)`` goes over to ``1 / (np.sum(f) - ddof)``
    as it should.

    Examples
    --------
    >>> import numpy as np

    Consider two variables, :math:`x_0` and :math:`x_1`, which
    correlate perfectly, but in opposite directions:

    >>> x = np.array([[0, 2], [1, 1], [2, 0]]).T
    >>> x
    array([[0, 1, 2],
           [2, 1, 0]])

    Note how :math:`x_0` increases while :math:`x_1` decreases. The covariance
    matrix shows this clearly:

    >>> np.cov(x)
    array([[ 1., -1.],
           [-1.,  1.]])

    Note that element :math:`C_{0,1}`, which shows the correlation between
    :math:`x_0` and :math:`x_1`, is negative.

    Further, note how `x` and `y` are combined:

    >>> x = [-2.1, -1,  4.3]
    >>> y = [3,  1.1,  0.12]
    >>> X = np.stack((x, y), axis=0)
    >>> np.cov(X)
    array([[11.71      , -4.286     ], # may vary
           [-4.286     ,  2.144133]])
    >>> np.cov(x, y)
    array([[11.71      , -4.286     ], # may vary
           [-4.286     ,  2.144133]])
    >>> np.cov(x)
    array(11.71)

    """
    # Check inputs
    if ddof is not None and ddof != int(ddof):
        raise ValueError(
            "ddof must be integer")

    # Handles complex arrays too
    m = np.asarray(m)
    if m.ndim > 2:
        raise ValueError("m has more than 2 dimensions")

    if y is not None:
        y = np.asarray(y)
        if y.ndim > 2:
            raise ValueError("y has more than 2 dimensions")

    if dtype is None:
        if y is None:
            dtype = np.result_type(m, np.float64)
        else:
            dtype = np.result_type(m, y, np.float64)

    X = array(m, ndmin=2, dtype=dtype)
    if not rowvar and m.ndim != 1:
        X = X.T
    if X.shape[0] == 0:
        return np.array([]).reshape(0, 0)
    if y is not None:
        y = array(y, copy=None, ndmin=2, dtype=dtype)
        if not rowvar and y.shape[0] != 1:
            y = y.T
        X = np.concatenate((X, y), axis=0)

    if ddof is None:
        if bias == 0:
            ddof = 1
        else:
            ddof = 0

    # Get the product of frequencies and weights
    w = None
    if fweights is not None:
        fweights = np.asarray(fweights, dtype=float)
        if not np.all(fweights == np.around(fweights)):
            raise TypeError(
                "fweights must be integer")
        if fweights.ndim > 1:
            raise RuntimeError(
                "cannot handle multidimensional fweights")
        if fweights.shape[0] != X.shape[1]:
            raise RuntimeError(
                "incompatible numbers of samples and fweights")
        if any(fweights < 0):
            raise ValueError(
                "fweights cannot be negative")
        w = fweights
    if aweights is not None:
        aweights = np.asarray(aweights, dtype=float)
        if aweights.ndim > 1:
            raise RuntimeError(
                "cannot handle multidimensional aweights")
        if aweights.shape[0] != X.shape[1]:
            raise RuntimeError(
                "incompatible numbers of samples and aweights")
        if any(aweights < 0):
            raise ValueError(
                "aweights cannot be negative")
        if w is None:
            w = aweights
        else:
            w *= aweights

    avg, w_sum = average(X, axis=1, weights=w, returned=True)
    w_sum = w_sum[0]

    # Determine the normalization
    if w is None:
        fact = X.shape[1] - ddof
    elif ddof == 0:
        fact = w_sum
    elif aweights is None:
        fact = w_sum - ddof
    else:
        fact = w_sum - ddof * sum(w * aweights) / w_sum

    if fact <= 0:
        warnings.warn("Degrees of freedom <= 0 for slice",
                      RuntimeWarning, stacklevel=2)
        fact = 0.0

    X -= avg[:, None]
    if w is None:
        X_T = X.T
    else:
        X_T = (X * w).T
    c = dot(X, X_T.conj())
    c *= np.true_divide(1, fact)
    return c.squeeze()


def _corrcoef_dispatcher(x, y=None, rowvar=None, bias=None, ddof=None, *,
                         dtype=None):
    return (x, y)


@array_function_dispatch(_corrcoef_dispatcher)
def corrcoef(x, y=None, rowvar=True, bias=np._NoValue, ddof=np._NoValue, *,
             dtype=None):
    """
    Return Pearson product-moment correlation coefficients.

    Please refer to the documentation for `cov` for more detail.  The
    relationship between the correlation coefficient matrix, `R`, and the
    covariance matrix, `C`, is

    .. math:: R_{ij} = \\frac{ C_{ij} } { \\sqrt{ C_{ii} C_{jj} } }

    The values of `R` are between -1 and 1, inclusive.

    Parameters
    ----------
    x : array_like
        A 1-D or 2-D array containing multiple variables and observations.
        Each row of `x` represents a variable, and each column a single
        observation of all those variables. Also see `rowvar` below.
    y : array_like, optional
        An additional set of variables and observations. `y` has the same
        shape as `x`.
    rowvar : bool, optional
        If `rowvar` is True (default), then each row represents a
        variable, with observations in the columns. Otherwise, the relationship
        is transposed: each column represents a variable, while the rows
        contain observations.
    bias : _NoValue, optional
        Has no effect, do not use.

        .. deprecated:: 1.10.0
    ddof : _NoValue, optional
        Has no effect, do not use.

        .. deprecated:: 1.10.0
    dtype : data-type, optional
        Data-type of the result. By default, the return data-type will have
        at least `numpy.float64` precision.

        .. versionadded:: 1.20

    Returns
    -------
    R : ndarray
        The correlation coefficient matrix of the variables.

    See Also
    --------
    cov : Covariance matrix

    Notes
    -----
    Due to floating point rounding the resulting array may not be Hermitian,
    the diagonal elements may not be 1, and the elements may not satisfy the
    inequality abs(a) <= 1. The real and imaginary parts are clipped to the
    interval [-1,  1] in an attempt to improve on that situation but is not
    much help in the complex case.

    This function accepts but discards arguments `bias` and `ddof`.  This is
    for backwards compatibility with previous versions of this function.  These
    arguments had no effect on the return values of the function and can be
    safely ignored in this and previous versions of numpy.

    Examples
    --------
    >>> import numpy as np

    In this example we generate two random arrays, ``xarr`` and ``yarr``, and
    compute the row-wise and column-wise Pearson correlation coefficients,
    ``R``. Since ``rowvar`` is  true by  default, we first find the row-wise
    Pearson correlation coefficients between the variables of ``xarr``.

    >>> import numpy as np
    >>> rng = np.random.default_rng(seed=42)
    >>> xarr = rng.random((3, 3))
    >>> xarr
    array([[0.77395605, 0.43887844, 0.85859792],
           [0.69736803, 0.09417735, 0.97562235],
           [0.7611397 , 0.78606431, 0.12811363]])
    >>> R1 = np.corrcoef(xarr)
    >>> R1
    array([[ 1.        ,  0.99256089, -0.68080986],
           [ 0.99256089,  1.        , -0.76492172],
           [-0.68080986, -0.76492172,  1.        ]])

    If we add another set of variables and observations ``yarr``, we can
    compute the row-wise Pearson correlation coefficients between the
    variables in ``xarr`` and ``yarr``.

    >>> yarr = rng.random((3, 3))
    >>> yarr
    array([[0.45038594, 0.37079802, 0.92676499],
           [0.64386512, 0.82276161, 0.4434142 ],
           [0.22723872, 0.55458479, 0.06381726]])
    >>> R2 = np.corrcoef(xarr, yarr)
    >>> R2
    array([[ 1.        ,  0.99256089, -0.68080986,  0.75008178, -0.934284  ,
            -0.99004057],
           [ 0.99256089,  1.        , -0.76492172,  0.82502011, -0.97074098,
            -0.99981569],
           [-0.68080986, -0.76492172,  1.        , -0.99507202,  0.89721355,
             0.77714685],
           [ 0.75008178,  0.82502011, -0.99507202,  1.        , -0.93657855,
            -0.83571711],
           [-0.934284  , -0.97074098,  0.89721355, -0.93657855,  1.        ,
             0.97517215],
           [-0.99004057, -0.99981569,  0.77714685, -0.83571711,  0.97517215,
             1.        ]])

    Finally if we use the option ``rowvar=False``, the columns are now
    being treated as the variables and we will find the column-wise Pearson
    correlation coefficients between variables in ``xarr`` and ``yarr``.

    >>> R3 = np.corrcoef(xarr, yarr, rowvar=False)
    >>> R3
    array([[ 1.        ,  0.77598074, -0.47458546, -0.75078643, -0.9665554 ,
             0.22423734],
           [ 0.77598074,  1.        , -0.92346708, -0.99923895, -0.58826587,
            -0.44069024],
           [-0.47458546, -0.92346708,  1.        ,  0.93773029,  0.23297648,
             0.75137473],
           [-0.75078643, -0.99923895,  0.93773029,  1.        ,  0.55627469,
             0.47536961],
           [-0.9665554 , -0.58826587,  0.23297648,  0.55627469,  1.        ,
            -0.46666491],
           [ 0.22423734, -0.44069024,  0.75137473,  0.47536961, -0.46666491,
             1.        ]])

    """
    if bias is not np._NoValue or ddof is not np._NoValue:
        # 2015-03-15, 1.10
        warnings.warn('bias and ddof have no effect and are deprecated',
                      DeprecationWarning, stacklevel=2)
    c = cov(x, y, rowvar, dtype=dtype)
    try:
        d = diag(c)
    except ValueError:
        # scalar covariance
        # nan if incorrect value (nan, inf, 0), 1 otherwise
        return c / c
    stddev = sqrt(d.real)
    c /= stddev[:, None]
    c /= stddev[None, :]

    # Clip real and imaginary parts to [-1, 1].  This does not guarantee
    # abs(a[i,j]) <= 1 for complex arrays, but is the best we can do without
    # excessive work.
    np.clip(c.real, -1, 1, out=c.real)
    if np.iscomplexobj(c):
        np.clip(c.imag, -1, 1, out=c.imag)

    return c


@set_module('numpy')
def blackman(M):
    """
    Return the Blackman window.

    The Blackman window is a taper formed by using the first three
    terms of a summation of cosines. It was designed to have close to the
    minimal leakage possible.  It is close to optimal, only slightly worse
    than a Kaiser window.

    Parameters
    ----------
    M : int
        Number of points in the output window. If zero or less, an empty
        array is returned.

    Returns
    -------
    out : ndarray
        The window, with the maximum value normalized to one (the value one
        appears only if the number of samples is odd).

    See Also
    --------
    bartlett, hamming, hanning, kaiser

    Notes
    -----
    The Blackman window is defined as

    .. math::  w(n) = 0.42 - 0.5 \\cos(2\\pi n/M) + 0.08 \\cos(4\\pi n/M)

    Most references to the Blackman window come from the signal processing
    literature, where it is used as one of many windowing functions for
    smoothing values.  It is also known as an apodization (which means
    "removing the foot", i.e. smoothing discontinuities at the beginning
    and end of the sampled signal) or tapering function. It is known as a
    "near optimal" tapering function, almost as good (by some measures)
    as the kaiser window.

    References
    ----------
    Blackman, R.B. and Tukey, J.W., (1958) The measurement of power spectra,
    Dover Publications, New York.

    Oppenheim, A.V., and R.W. Schafer. Discrete-Time Signal Processing.
    Upper Saddle River, NJ: Prentice-Hall, 1999, pp. 468-471.

    Examples
    --------
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> np.blackman(12)
    array([-1.38777878e-17,   3.26064346e-02,   1.59903635e-01, # may vary
            4.14397981e-01,   7.36045180e-01,   9.67046769e-01,
            9.67046769e-01,   7.36045180e-01,   4.14397981e-01,
            1.59903635e-01,   3.26064346e-02,  -1.38777878e-17])

    Plot the window and the frequency response.

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        from numpy.fft import fft, fftshift
        window = np.blackman(51)
        plt.plot(window)
        plt.title("Blackman window")
        plt.ylabel("Amplitude")
        plt.xlabel("Sample")
        plt.show()  # doctest: +SKIP

        plt.figure()
        A = fft(window, 2048) / 25.5
        mag = np.abs(fftshift(A))
        freq = np.linspace(-0.5, 0.5, len(A))
        with np.errstate(divide='ignore', invalid='ignore'):
            response = 20 * np.log10(mag)
        response = np.clip(response, -100, 100)
        plt.plot(freq, response)
        plt.title("Frequency response of Blackman window")
        plt.ylabel("Magnitude [dB]")
        plt.xlabel("Normalized frequency [cycles per sample]")
        plt.axis('tight')
        plt.show()

    """
    # Ensures at least float64 via 0.0.  M should be an integer, but conversion
    # to double is safe for a range.
    values = np.array([0.0, M])
    M = values[1]

    if M < 1:
        return array([], dtype=values.dtype)
    if M == 1:
        return ones(1, dtype=values.dtype)
    n = arange(1 - M, M, 2)
    return 0.42 + 0.5 * cos(pi * n / (M - 1)) + 0.08 * cos(2.0 * pi * n / (M - 1))


@set_module('numpy')
def bartlett(M):
    """
    Return the Bartlett window.

    The Bartlett window is very similar to a triangular window, except
    that the end points are at zero.  It is often used in signal
    processing for tapering a signal, without generating too much
    ripple in the frequency domain.

    Parameters
    ----------
    M : int
        Number of points in the output window. If zero or less, an
        empty array is returned.

    Returns
    -------
    out : array
        The triangular window, with the maximum value normalized to one
        (the value one appears only if the number of samples is odd), with
        the first and last samples equal to zero.

    See Also
    --------
    blackman, hamming, hanning, kaiser

    Notes
    -----
    The Bartlett window is defined as

    .. math:: w(n) = \\frac{2}{M-1} \\left(
              \\frac{M-1}{2} - \\left|n - \\frac{M-1}{2}\\right|
              \\right)

    Most references to the Bartlett window come from the signal processing
    literature, where it is used as one of many windowing functions for
    smoothing values.  Note that convolution with this window produces linear
    interpolation.  It is also known as an apodization (which means "removing
    the foot", i.e. smoothing discontinuities at the beginning and end of the
    sampled signal) or tapering function. The Fourier transform of the
    Bartlett window is the product of two sinc functions. Note the excellent
    discussion in Kanasewich [2]_.

    References
    ----------
    .. [1] M.S. Bartlett, "Periodogram Analysis and Continuous Spectra",
           Biometrika 37, 1-16, 1950.
    .. [2] E.R. Kanasewich, "Time Sequence Analysis in Geophysics",
           The University of Alberta Press, 1975, pp. 109-110.
    .. [3] A.V. Oppenheim and R.W. Schafer, "Discrete-Time Signal
           Processing", Prentice-Hall, 1999, pp. 468-471.
    .. [4] Wikipedia, "Window function",
           https://en.wikipedia.org/wiki/Window_function
    .. [5] W.H. Press,  B.P. Flannery, S.A. Teukolsky, and W.T. Vetterling,
           "Numerical Recipes", Cambridge University Press, 1986, page 429.

    Examples
    --------
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> np.bartlett(12)
    array([ 0.        ,  0.18181818,  0.36363636,  0.54545455,  0.72727273, # may vary
            0.90909091,  0.90909091,  0.72727273,  0.54545455,  0.36363636,
            0.18181818,  0.        ])

    Plot the window and its frequency response (requires SciPy and matplotlib).

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        from numpy.fft import fft, fftshift
        window = np.bartlett(51)
        plt.plot(window)
        plt.title("Bartlett window")
        plt.ylabel("Amplitude")
        plt.xlabel("Sample")
        plt.show()
        plt.figure()
        A = fft(window, 2048) / 25.5
        mag = np.abs(fftshift(A))
        freq = np.linspace(-0.5, 0.5, len(A))
        with np.errstate(divide='ignore', invalid='ignore'):
            response = 20 * np.log10(mag)
        response = np.clip(response, -100, 100)
        plt.plot(freq, response)
        plt.title("Frequency response of Bartlett window")
        plt.ylabel("Magnitude [dB]")
        plt.xlabel("Normalized frequency [cycles per sample]")
        plt.axis('tight')
        plt.show()

    """
    # Ensures at least float64 via 0.0.  M should be an integer, but conversion
    # to double is safe for a range.
    values = np.array([0.0, M])
    M = values[1]

    if M < 1:
        return array([], dtype=values.dtype)
    if M == 1:
        return ones(1, dtype=values.dtype)
    n = arange(1 - M, M, 2)
    return where(less_equal(n, 0), 1 + n / (M - 1), 1 - n / (M - 1))


@set_module('numpy')
def hanning(M):
    """
    Return the Hanning window.

    The Hanning window is a taper formed by using a weighted cosine.

    Parameters
    ----------
    M : int
        Number of points in the output window. If zero or less, an
        empty array is returned.

    Returns
    -------
    out : ndarray, shape(M,)
        The window, with the maximum value normalized to one (the value
        one appears only if `M` is odd).

    See Also
    --------
    bartlett, blackman, hamming, kaiser

    Notes
    -----
    The Hanning window is defined as

    .. math::  w(n) = 0.5 - 0.5\\cos\\left(\\frac{2\\pi{n}}{M-1}\\right)
               \\qquad 0 \\leq n \\leq M-1

    The Hanning was named for Julius von Hann, an Austrian meteorologist.
    It is also known as the Cosine Bell. Some authors prefer that it be
    called a Hann window, to help avoid confusion with the very similar
    Hamming window.

    Most references to the Hanning window come from the signal processing
    literature, where it is used as one of many windowing functions for
    smoothing values.  It is also known as an apodization (which means
    "removing the foot", i.e. smoothing discontinuities at the beginning
    and end of the sampled signal) or tapering function.

    References
    ----------
    .. [1] Blackman, R.B. and Tukey, J.W., (1958) The measurement of power
           spectra, Dover Publications, New York.
    .. [2] E.R. Kanasewich, "Time Sequence Analysis in Geophysics",
           The University of Alberta Press, 1975, pp. 106-108.
    .. [3] Wikipedia, "Window function",
           https://en.wikipedia.org/wiki/Window_function
    .. [4] W.H. Press,  B.P. Flannery, S.A. Teukolsky, and W.T. Vetterling,
           "Numerical Recipes", Cambridge University Press, 1986, page 425.

    Examples
    --------
    >>> import numpy as np
    >>> np.hanning(12)
    array([0.        , 0.07937323, 0.29229249, 0.57115742, 0.82743037,
           0.97974649, 0.97974649, 0.82743037, 0.57115742, 0.29229249,
           0.07937323, 0.        ])

    Plot the window and its frequency response.

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        from numpy.fft import fft, fftshift
        window = np.hanning(51)
        plt.plot(window)
        plt.title("Hann window")
        plt.ylabel("Amplitude")
        plt.xlabel("Sample")
        plt.show()

        plt.figure()
        A = fft(window, 2048) / 25.5
        mag = np.abs(fftshift(A))
        freq = np.linspace(-0.5, 0.5, len(A))
        with np.errstate(divide='ignore', invalid='ignore'):
            response = 20 * np.log10(mag)
        response = np.clip(response, -100, 100)
        plt.plot(freq, response)
        plt.title("Frequency response of the Hann window")
        plt.ylabel("Magnitude [dB]")
        plt.xlabel("Normalized frequency [cycles per sample]")
        plt.axis('tight')
        plt.show()

    """
    # Ensures at least float64 via 0.0.  M should be an integer, but conversion
    # to double is safe for a range.
    values = np.array([0.0, M])
    M = values[1]

    if M < 1:
        return array([], dtype=values.dtype)
    if M == 1:
        return ones(1, dtype=values.dtype)
    n = arange(1 - M, M, 2)
    return 0.5 + 0.5 * cos(pi * n / (M - 1))


@set_module('numpy')
def hamming(M):
    """
    Return the Hamming window.

    The Hamming window is a taper formed by using a weighted cosine.

    Parameters
    ----------
    M : int
        Number of points in the output window. If zero or less, an
        empty array is returned.

    Returns
    -------
    out : ndarray
        The window, with the maximum value normalized to one (the value
        one appears only if the number of samples is odd).

    See Also
    --------
    bartlett, blackman, hanning, kaiser

    Notes
    -----
    The Hamming window is defined as

    .. math::  w(n) = 0.54 - 0.46\\cos\\left(\\frac{2\\pi{n}}{M-1}\\right)
               \\qquad 0 \\leq n \\leq M-1

    The Hamming was named for R. W. Hamming, an associate of J. W. Tukey
    and is described in Blackman and Tukey. It was recommended for
    smoothing the truncated autocovariance function in the time domain.
    Most references to the Hamming window come from the signal processing
    literature, where it is used as one of many windowing functions for
    smoothing values.  It is also known as an apodization (which means
    "removing the foot", i.e. smoothing discontinuities at the beginning
    and end of the sampled signal) or tapering function.

    References
    ----------
    .. [1] Blackman, R.B. and Tukey, J.W., (1958) The measurement of power
           spectra, Dover Publications, New York.
    .. [2] E.R. Kanasewich, "Time Sequence Analysis in Geophysics", The
           University of Alberta Press, 1975, pp. 109-110.
    .. [3] Wikipedia, "Window function",
           https://en.wikipedia.org/wiki/Window_function
    .. [4] W.H. Press,  B.P. Flannery, S.A. Teukolsky, and W.T. Vetterling,
           "Numerical Recipes", Cambridge University Press, 1986, page 425.

    Examples
    --------
    >>> import numpy as np
    >>> np.hamming(12)
    array([ 0.08      ,  0.15302337,  0.34890909,  0.60546483,  0.84123594, # may vary
            0.98136677,  0.98136677,  0.84123594,  0.60546483,  0.34890909,
            0.15302337,  0.08      ])

    Plot the window and the frequency response.

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        from numpy.fft import fft, fftshift
        window = np.hamming(51)
        plt.plot(window)
        plt.title("Hamming window")
        plt.ylabel("Amplitude")
        plt.xlabel("Sample")
        plt.show()

        plt.figure()
        A = fft(window, 2048) / 25.5
        mag = np.abs(fftshift(A))
        freq = np.linspace(-0.5, 0.5, len(A))
        response = 20 * np.log10(mag)
        response = np.clip(response, -100, 100)
        plt.plot(freq, response)
        plt.title("Frequency response of Hamming window")
        plt.ylabel("Magnitude [dB]")
        plt.xlabel("Normalized frequency [cycles per sample]")
        plt.axis('tight')
        plt.show()

    """
    # Ensures at least float64 via 0.0.  M should be an integer, but conversion
    # to double is safe for a range.
    values = np.array([0.0, M])
    M = values[1]

    if M < 1:
        return array([], dtype=values.dtype)
    if M == 1:
        return ones(1, dtype=values.dtype)
    n = arange(1 - M, M, 2)
    return 0.54 + 0.46 * cos(pi * n / (M - 1))


## Code from cephes for i0

_i0A = [
    -4.41534164647933937950E-18,
    3.33079451882223809783E-17,
    -2.43127984654795469359E-16,
    1.71539128555513303061E-15,
    -1.16853328779934516808E-14,
    7.67618549860493561688E-14,
    -4.85644678311192946090E-13,
    2.95505266312963983461E-12,
    -1.72682629144155570723E-11,
    9.67580903537323691224E-11,
    -5.18979560163526290666E-10,
    2.65982372468238665035E-9,
    -1.30002500998624804212E-8,
    6.04699502254191894932E-8,
    -2.67079385394061173391E-7,
    1.11738753912010371815E-6,
    -4.41673835845875056359E-6,
    1.64484480707288970893E-5,
    -5.75419501008210370398E-5,
    1.88502885095841655729E-4,
    -5.76375574538582365885E-4,
    1.63947561694133579842E-3,
    -4.32430999505057594430E-3,
    1.05464603945949983183E-2,
    -2.37374148058994688156E-2,
    4.93052842396707084878E-2,
    -9.49010970480476444210E-2,
    1.71620901522208775349E-1,
    -3.04682672343198398683E-1,
    6.76795274409476084995E-1
    ]

_i0B = [
    -7.23318048787475395456E-18,
    -4.83050448594418207126E-18,
    4.46562142029675999901E-17,
    3.46122286769746109310E-17,
    -2.82762398051658348494E-16,
    -3.42548561967721913462E-16,
    1.77256013305652638360E-15,
    3.81168066935262242075E-15,
    -9.55484669882830764870E-15,
    -4.15056934728722208663E-14,
    1.54008621752140982691E-14,
    3.85277838274214270114E-13,
    7.18012445138366623367E-13,
    -1.79417853150680611778E-12,
    -1.32158118404477131188E-11,
    -3.14991652796324136454E-11,
    1.18891471078464383424E-11,
    4.94060238822496958910E-10,
    3.39623202570838634515E-9,
    2.26666899049817806459E-8,
    2.04891858946906374183E-7,
    2.89137052083475648297E-6,
    6.88975834691682398426E-5,
    3.36911647825569408990E-3,
    8.04490411014108831608E-1
    ]


def _chbevl(x, vals):
    b0 = vals[0]
    b1 = 0.0

    for i in range(1, len(vals)):
        b2 = b1
        b1 = b0
        b0 = x * b1 - b2 + vals[i]

    return 0.5 * (b0 - b2)


def _i0_1(x):
    return exp(x) * _chbevl(x / 2.0 - 2, _i0A)


def _i0_2(x):
    return exp(x) * _chbevl(32.0 / x - 2.0, _i0B) / sqrt(x)


def _i0_dispatcher(x):
    return (x,)


@array_function_dispatch(_i0_dispatcher)
def i0(x):
    """
    Modified Bessel function of the first kind, order 0.

    Usually denoted :math:`I_0`.

    Parameters
    ----------
    x : array_like of float
        Argument of the Bessel function.

    Returns
    -------
    out : ndarray, shape = x.shape, dtype = float
        The modified Bessel function evaluated at each of the elements of `x`.

    See Also
    --------
    scipy.special.i0, scipy.special.iv, scipy.special.ive

    Notes
    -----
    The scipy implementation is recommended over this function: it is a
    proper ufunc written in C, and more than an order of magnitude faster.

    We use the algorithm published by Clenshaw [1]_ and referenced by
    Abramowitz and Stegun [2]_, for which the function domain is
    partitioned into the two intervals [0,8] and (8,inf), and Chebyshev
    polynomial expansions are employed in each interval. Relative error on
    the domain [0,30] using IEEE arithmetic is documented [3]_ as having a
    peak of 5.8e-16 with an rms of 1.4e-16 (n = 30000).

    References
    ----------
    .. [1] C. W. Clenshaw, "Chebyshev series for mathematical functions", in
           *National Physical Laboratory Mathematical Tables*, vol. 5, London:
           Her Majesty's Stationery Office, 1962.
    .. [2] M. Abramowitz and I. A. Stegun, *Handbook of Mathematical
           Functions*, 10th printing, New York: Dover, 1964, pp. 379.
           https://personal.math.ubc.ca/~cbm/aands/page_379.htm
    .. [3] https://metacpan.org/pod/distribution/Math-Cephes/lib/Math/Cephes.pod#i0:-Modified-Bessel-function-of-order-zero

    Examples
    --------
    >>> import numpy as np
    >>> np.i0(0.)
    array(1.0)
    >>> np.i0([0, 1, 2, 3])
    array([1.        , 1.26606588, 2.2795853 , 4.88079259])

    """
    x = np.asanyarray(x)
    if x.dtype.kind == 'c':
        raise TypeError("i0 not supported for complex values")
    if x.dtype.kind != 'f':
        x = x.astype(float)
    x = np.abs(x)
    return piecewise(x, [x <= 8.0], [_i0_1, _i0_2])

## End of cephes code for i0


@set_module('numpy')
def kaiser(M, beta):
    """
    Return the Kaiser window.

    The Kaiser window is a taper formed by using a Bessel function.

    Parameters
    ----------
    M : int
        Number of points in the output window. If zero or less, an
        empty array is returned.
    beta : float
        Shape parameter for window.

    Returns
    -------
    out : array
        The window, with the maximum value normalized to one (the value
        one appears only if the number of samples is odd).

    See Also
    --------
    bartlett, blackman, hamming, hanning

    Notes
    -----
    The Kaiser window is defined as

    .. math::  w(n) = I_0\\left( \\beta \\sqrt{1-\\frac{4n^2}{(M-1)^2}}
               \\right)/I_0(\\beta)

    with

    .. math:: \\quad -\\frac{M-1}{2} \\leq n \\leq \\frac{M-1}{2},

    where :math:`I_0` is the modified zeroth-order Bessel function.

    The Kaiser was named for Jim Kaiser, who discovered a simple
    approximation to the DPSS window based on Bessel functions.  The Kaiser
    window is a very good approximation to the Digital Prolate Spheroidal
    Sequence, or Slepian window, which is the transform which maximizes the
    energy in the main lobe of the window relative to total energy.

    The Kaiser can approximate many other windows by varying the beta
    parameter.

    ====  =======================
    beta  Window shape
    ====  =======================
    0     Rectangular
    5     Similar to a Hamming
    6     Similar to a Hanning
    8.6   Similar to a Blackman
    ====  =======================

    A beta value of 14 is probably a good starting point. Note that as beta
    gets large, the window narrows, and so the number of samples needs to be
    large enough to sample the increasingly narrow spike, otherwise NaNs will
    get returned.

    Most references to the Kaiser window come from the signal processing
    literature, where it is used as one of many windowing functions for
    smoothing values.  It is also known as an apodization (which means
    "removing the foot", i.e. smoothing discontinuities at the beginning
    and end of the sampled signal) or tapering function.

    References
    ----------
    .. [1] J. F. Kaiser, "Digital Filters" - Ch 7 in "Systems analysis by
           digital computer", Editors: F.F. Kuo and J.F. Kaiser, p 218-285.
           John Wiley and Sons, New York, (1966).
    .. [2] E.R. Kanasewich, "Time Sequence Analysis in Geophysics", The
           University of Alberta Press, 1975, pp. 177-178.
    .. [3] Wikipedia, "Window function",
           https://en.wikipedia.org/wiki/Window_function

    Examples
    --------
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> np.kaiser(12, 14)
     array([7.72686684e-06, 3.46009194e-03, 4.65200189e-02, # may vary
            2.29737120e-01, 5.99885316e-01, 9.45674898e-01,
            9.45674898e-01, 5.99885316e-01, 2.29737120e-01,
            4.65200189e-02, 3.46009194e-03, 7.72686684e-06])


    Plot the window and the frequency response.

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        from numpy.fft import fft, fftshift
        window = np.kaiser(51, 14)
        plt.plot(window)
        plt.title("Kaiser window")
        plt.ylabel("Amplitude")
        plt.xlabel("Sample")
        plt.show()

        plt.figure()
        A = fft(window, 2048) / 25.5
        mag = np.abs(fftshift(A))
        freq = np.linspace(-0.5, 0.5, len(A))
        response = 20 * np.log10(mag)
        response = np.clip(response, -100, 100)
        plt.plot(freq, response)
        plt.title("Frequency response of Kaiser window")
        plt.ylabel("Magnitude [dB]")
        plt.xlabel("Normalized frequency [cycles per sample]")
        plt.axis('tight')
        plt.show()

    """
    # Ensures at least float64 via 0.0.  M should be an integer, but conversion
    # to double is safe for a range.  (Simplified result_type with 0.0
    # strongly typed.  result-type is not/less order sensitive, but that mainly
    # matters for integers anyway.)
    values = np.array([0.0, M, beta])
    M = values[1]
    beta = values[2]

    if M == 1:
        return np.ones(1, dtype=values.dtype)
    n = arange(0, M)
    alpha = (M - 1) / 2.0
    return i0(beta * sqrt(1 - ((n - alpha) / alpha)**2.0)) / i0(beta)


def _sinc_dispatcher(x):
    return (x,)


@array_function_dispatch(_sinc_dispatcher)
def sinc(x):
    r"""
    Return the normalized sinc function.

    The sinc function is equal to :math:`\sin(\pi x)/(\pi x)` for any argument
    :math:`x\ne 0`. ``sinc(0)`` takes the limit value 1, making ``sinc`` not
    only everywhere continuous but also infinitely differentiable.

    .. note::

        Note the normalization factor of ``pi`` used in the definition.
        This is the most commonly used definition in signal processing.
        Use ``sinc(x / np.pi)`` to obtain the unnormalized sinc function
        :math:`\sin(x)/x` that is more common in mathematics.

    Parameters
    ----------
    x : ndarray
        Array (possibly multi-dimensional) of values for which to calculate
        ``sinc(x)``.

    Returns
    -------
    out : ndarray
        ``sinc(x)``, which has the same shape as the input.

    Notes
    -----
    The name sinc is short for "sine cardinal" or "sinus cardinalis".

    The sinc function is used in various signal processing applications,
    including in anti-aliasing, in the construction of a Lanczos resampling
    filter, and in interpolation.

    For bandlimited interpolation of discrete-time signals, the ideal
    interpolation kernel is proportional to the sinc function.

    References
    ----------
    .. [1] Weisstein, Eric W. "Sinc Function." From MathWorld--A Wolfram Web
           Resource. https://mathworld.wolfram.com/SincFunction.html
    .. [2] Wikipedia, "Sinc function",
           https://en.wikipedia.org/wiki/Sinc_function

    Examples
    --------
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> x = np.linspace(-4, 4, 41)
    >>> np.sinc(x)
     array([-3.89804309e-17,  -4.92362781e-02,  -8.40918587e-02, # may vary
            -8.90384387e-02,  -5.84680802e-02,   3.89804309e-17,
            6.68206631e-02,   1.16434881e-01,   1.26137788e-01,
            8.50444803e-02,  -3.89804309e-17,  -1.03943254e-01,
            -1.89206682e-01,  -2.16236208e-01,  -1.55914881e-01,
            3.89804309e-17,   2.33872321e-01,   5.04551152e-01,
            7.56826729e-01,   9.35489284e-01,   1.00000000e+00,
            9.35489284e-01,   7.56826729e-01,   5.04551152e-01,
            2.33872321e-01,   3.89804309e-17,  -1.55914881e-01,
           -2.16236208e-01,  -1.89206682e-01,  -1.03943254e-01,
           -3.89804309e-17,   8.50444803e-02,   1.26137788e-01,
            1.16434881e-01,   6.68206631e-02,   3.89804309e-17,
            -5.84680802e-02,  -8.90384387e-02,  -8.40918587e-02,
            -4.92362781e-02,  -3.89804309e-17])

    >>> plt.plot(x, np.sinc(x))
    [<matplotlib.lines.Line2D object at 0x...>]
    >>> plt.title("Sinc Function")
    Text(0.5, 1.0, 'Sinc Function')
    >>> plt.ylabel("Amplitude")
    Text(0, 0.5, 'Amplitude')
    >>> plt.xlabel("X")
    Text(0.5, 0, 'X')
    >>> plt.show()

    """
    x = np.asanyarray(x)
    x = pi * x
    # Hope that 1e-20 is sufficient for objects...
    eps = np.finfo(x.dtype).eps if x.dtype.kind == "f" else 1e-20
    y = where(x, x, eps)
    return sin(y) / y


def _ureduce(a, func, keepdims=False, **kwargs):
    """
    Internal Function.
    Call `func` with `a` as first argument swapping the axes to use extended
    axis on functions that don't support it natively.

    Returns result and a.shape with axis dims set to 1.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array.
    func : callable
        Reduction function capable of receiving a single axis argument.
        It is called with `a` as first argument followed by `kwargs`.
    kwargs : keyword arguments
        additional keyword arguments to pass to `func`.

    Returns
    -------
    result : tuple
        Result of func(a, **kwargs) and a.shape with axis dims set to 1
        which can be used to reshape the result to the same shape a ufunc with
        keepdims=True would produce.

    """
    a = np.asanyarray(a)
    axis = kwargs.get('axis')
    out = kwargs.get('out')

    if keepdims is np._NoValue:
        keepdims = False

    nd = a.ndim
    if axis is not None:
        axis = _nx.normalize_axis_tuple(axis, nd)

        if keepdims and out is not None:
            index_out = tuple(
                0 if i in axis else slice(None) for i in range(nd))
            kwargs['out'] = out[(Ellipsis, ) + index_out]

        if len(axis) == 1:
            kwargs['axis'] = axis[0]
        else:
            keep = set(range(nd)) - set(axis)
            nkeep = len(keep)
            # swap axis that should not be reduced to front
            for i, s in enumerate(sorted(keep)):
                a = a.swapaxes(i, s)
            # merge reduced axis
            a = a.reshape(a.shape[:nkeep] + (-1,))
            kwargs['axis'] = -1
    elif keepdims and out is not None:
        index_out = (0, ) * nd
        kwargs['out'] = out[(Ellipsis, ) + index_out]

    r = func(a, **kwargs)

    if out is not None:
        return out

    if keepdims:
        if axis is None:
            index_r = (np.newaxis, ) * nd
        else:
            index_r = tuple(
                np.newaxis if i in axis else slice(None)
                for i in range(nd))
        r = r[(Ellipsis, ) + index_r]

    return r


def _median_dispatcher(
        a, axis=None, out=None, overwrite_input=None, keepdims=None):
    return (a, out)


@array_function_dispatch(_median_dispatcher)
def median(a, axis=None, out=None, overwrite_input=False, keepdims=False):
    """
    Compute the median along the specified axis.

    Returns the median of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array.
    axis : {int, sequence of int, None}, optional
        Axis or axes along which the medians are computed. The default,
        axis=None, will compute the median along a flattened version of
        the array. If a sequence of axes, the array is first flattened
        along the given axes, then the median is computed along the
        resulting flattened axis.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output,
        but the type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
       If True, then allow use of memory of input array `a` for
       calculations. The input array will be modified by the call to
       `median`. This will save memory when you do not need to preserve
       the contents of the input array. Treat the input as undefined,
       but it will probably be fully or partially sorted. Default is
       False. If `overwrite_input` is ``True`` and `a` is not already an
       `ndarray`, an error will be raised.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `arr`.

    Returns
    -------
    median : ndarray
        A new array holding the result. If the input contains integers
        or floats smaller than ``float64``, then the output data-type is
        ``np.float64``.  Otherwise, the data-type of the output is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    mean, percentile

    Notes
    -----
    Given a vector ``V`` of length ``N``, the median of ``V`` is the
    middle value of a sorted copy of ``V``, ``V_sorted`` - i
    e., ``V_sorted[(N-1)/2]``, when ``N`` is odd, and the average of the
    two middle values of ``V_sorted`` when ``N`` is even.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10, 7, 4], [3, 2, 1]])
    >>> a
    array([[10,  7,  4],
           [ 3,  2,  1]])
    >>> np.median(a)
    np.float64(3.5)
    >>> np.median(a, axis=0)
    array([6.5, 4.5, 2.5])
    >>> np.median(a, axis=1)
    array([7.,  2.])
    >>> np.median(a, axis=(0, 1))
    np.float64(3.5)
    >>> m = np.median(a, axis=0)
    >>> out = np.zeros_like(m)
    >>> np.median(a, axis=0, out=m)
    array([6.5,  4.5,  2.5])
    >>> m
    array([6.5,  4.5,  2.5])
    >>> b = a.copy()
    >>> np.median(b, axis=1, overwrite_input=True)
    array([7.,  2.])
    >>> assert not np.all(a==b)
    >>> b = a.copy()
    >>> np.median(b, axis=None, overwrite_input=True)
    np.float64(3.5)
    >>> assert not np.all(a==b)

    """
    return _ureduce(a, func=_median, keepdims=keepdims, axis=axis, out=out,
                    overwrite_input=overwrite_input)


def _median(a, axis=None, out=None, overwrite_input=False):
    # can't be reasonably be implemented in terms of percentile as we have to
    # call mean to not break astropy
    a = np.asanyarray(a)

    # Set the partition indexes
    if axis is None:
        sz = a.size
    else:
        sz = a.shape[axis]
    if sz % 2 == 0:
        szh = sz // 2
        kth = [szh - 1, szh]
    else:
        kth = [(sz - 1) // 2]

    # We have to check for NaNs (as of writing 'M' doesn't actually work).
    supports_nans = np.issubdtype(a.dtype, np.inexact) or a.dtype.kind in 'Mm'
    if supports_nans:
        kth.append(-1)

    if overwrite_input:
        if axis is None:
            part = a.ravel()
            part.partition(kth)
        else:
            a.partition(kth, axis=axis)
            part = a
    else:
        part = partition(a, kth, axis=axis)

    if part.shape == ():
        # make 0-D arrays work
        return part.item()
    if axis is None:
        axis = 0

    indexer = [slice(None)] * part.ndim
    index = part.shape[axis] // 2
    if part.shape[axis] % 2 == 1:
        # index with slice to allow mean (below) to work
        indexer[axis] = slice(index, index + 1)
    else:
        indexer[axis] = slice(index - 1, index + 1)
    indexer = tuple(indexer)

    # Use mean in both odd and even case to coerce data type,
    # using out array if needed.
    rout = mean(part[indexer], axis=axis, out=out)
    if supports_nans and sz > 0:
        # If nans are possible, warn and replace by nans like mean would.
        rout = np.lib._utils_impl._median_nancheck(part, rout, axis)

    return rout


def _percentile_dispatcher(a, q, axis=None, out=None, overwrite_input=None,
                           method=None, keepdims=None, *, weights=None,
                           interpolation=None):
    return (a, q, out, weights)


@array_function_dispatch(_percentile_dispatcher)
def percentile(a,
               q,
               axis=None,
               out=None,
               overwrite_input=False,
               method="linear",
               keepdims=False,
               *,
               weights=None,
               interpolation=None):
    """
    Compute the q-th percentile of the data along the specified axis.

    Returns the q-th percentile(s) of the array elements.

    Parameters
    ----------
    a : array_like of real numbers
        Input array or object that can be converted to an array.
    q : array_like of float
        Percentage or sequence of percentages for the percentiles to compute.
        Values must be between 0 and 100 inclusive.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the percentiles are computed. The
        default is to compute the percentile(s) along a flattened
        version of the array.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output,
        but the type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
        If True, then allow the input array `a` to be modified by intermediate
        calculations, to save memory. In this case, the contents of the input
        `a` after this function completes is undefined.
    method : str, optional
        This parameter specifies the method to use for estimating the
        percentile.  There are many different methods, some unique to NumPy.
        See the notes for explanation.  The options sorted by their R type
        as summarized in the H&F paper [1]_ are:

        1. 'inverted_cdf'
        2. 'averaged_inverted_cdf'
        3. 'closest_observation'
        4. 'interpolated_inverted_cdf'
        5. 'hazen'
        6. 'weibull'
        7. 'linear'  (default)
        8. 'median_unbiased'
        9. 'normal_unbiased'

        The first three methods are discontinuous.  NumPy further defines the
        following discontinuous variations of the default 'linear' (7.) option:

        * 'lower'
        * 'higher',
        * 'midpoint'
        * 'nearest'

        .. versionchanged:: 1.22.0
            This argument was previously called "interpolation" and only
            offered the "linear" default and last four options.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left in
        the result as dimensions with size one. With this option, the
        result will broadcast correctly against the original array `a`.

     weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the percentile according to its associated weight.
        The weights array can either be 1-D (in which case its length must be
        the size of `a` along the given axis) or of the same shape as `a`.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        Only `method="inverted_cdf"` supports weights.
        See the notes for more details.

        .. versionadded:: 2.0.0

    interpolation : str, optional
        Deprecated name for the method keyword argument.

        .. deprecated:: 1.22.0

    Returns
    -------
    percentile : scalar or ndarray
        If `q` is a single percentile and `axis=None`, then the result
        is a scalar. If multiple percentiles are given, first axis of
        the result corresponds to the percentiles. The other axes are
        the axes that remain after the reduction of `a`. If the input
        contains integers or floats smaller than ``float64``, the output
        data-type is ``float64``. Otherwise, the output data-type is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    mean
    median : equivalent to ``percentile(..., 50)``
    nanpercentile
    quantile : equivalent to percentile, except q in the range [0, 1].

    Notes
    -----
    The behavior of `numpy.percentile` with percentage `q` is
    that of `numpy.quantile` with argument ``q/100``.
    For more information, please see `numpy.quantile`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10, 7, 4], [3, 2, 1]])
    >>> a
    array([[10,  7,  4],
           [ 3,  2,  1]])
    >>> np.percentile(a, 50)
    3.5
    >>> np.percentile(a, 50, axis=0)
    array([6.5, 4.5, 2.5])
    >>> np.percentile(a, 50, axis=1)
    array([7.,  2.])
    >>> np.percentile(a, 50, axis=1, keepdims=True)
    array([[7.],
           [2.]])

    >>> m = np.percentile(a, 50, axis=0)
    >>> out = np.zeros_like(m)
    >>> np.percentile(a, 50, axis=0, out=out)
    array([6.5, 4.5, 2.5])
    >>> m
    array([6.5, 4.5, 2.5])

    >>> b = a.copy()
    >>> np.percentile(b, 50, axis=1, overwrite_input=True)
    array([7.,  2.])
    >>> assert not np.all(a == b)

    The different methods can be visualized graphically:

    .. plot::

        import matplotlib.pyplot as plt

        a = np.arange(4)
        p = np.linspace(0, 100, 6001)
        ax = plt.gca()
        lines = [
            ('linear', '-', 'C0'),
            ('inverted_cdf', ':', 'C1'),
            # Almost the same as `inverted_cdf`:
            ('averaged_inverted_cdf', '-.', 'C1'),
            ('closest_observation', ':', 'C2'),
            ('interpolated_inverted_cdf', '--', 'C1'),
            ('hazen', '--', 'C3'),
            ('weibull', '-.', 'C4'),
            ('median_unbiased', '--', 'C5'),
            ('normal_unbiased', '-.', 'C6'),
            ]
        for method, style, color in lines:
            ax.plot(
                p, np.percentile(a, p, method=method),
                label=method, linestyle=style, color=color)
        ax.set(
            title='Percentiles for different methods and data: ' + str(a),
            xlabel='Percentile',
            ylabel='Estimated percentile value',
            yticks=a)
        ax.legend(bbox_to_anchor=(1.03, 1))
        plt.tight_layout()
        plt.show()

    References
    ----------
    .. [1] R. J. Hyndman and Y. Fan,
       "Sample quantiles in statistical packages,"
       The American Statistician, 50(4), pp. 361-365, 1996

    """
    if interpolation is not None:
        method = _check_interpolation_as_method(
            method, interpolation, "percentile")

    a = np.asanyarray(a)
    if a.dtype.kind == "c":
        raise TypeError("a must be an array of real numbers")

    # Use dtype of array if possible (e.g., if q is a python int or float)
    # by making the divisor have the dtype of the data array.
    q = np.true_divide(q, a.dtype.type(100) if a.dtype.kind == "f" else 100, out=...)
    if not _quantile_is_valid(q):
        raise ValueError("Percentiles must be in the range [0, 100]")

    if weights is not None:
        if method != "inverted_cdf":
            msg = ("Only method 'inverted_cdf' supports weights. "
                   f"Got: {method}.")
            raise ValueError(msg)
        if axis is not None:
            axis = _nx.normalize_axis_tuple(axis, a.ndim, argname="axis")
        weights = _weights_are_valid(weights=weights, a=a, axis=axis)
        if np.any(weights < 0):
            raise ValueError("Weights must be non-negative.")

    return _quantile_unchecked(
        a, q, axis, out, overwrite_input, method, keepdims, weights)


def _quantile_dispatcher(a, q, axis=None, out=None, overwrite_input=None,
                         method=None, keepdims=None, *, weights=None,
                         interpolation=None):
    return (a, q, out, weights)


@array_function_dispatch(_quantile_dispatcher)
def quantile(a,
             q,
             axis=None,
             out=None,
             overwrite_input=False,
             method="linear",
             keepdims=False,
             *,
             weights=None,
             interpolation=None):
    """
    Compute the q-th quantile of the data along the specified axis.

    Parameters
    ----------
    a : array_like of real numbers
        Input array or object that can be converted to an array.
    q : array_like of float
        Probability or sequence of probabilities of the quantiles to compute.
        Values must be between 0 and 1 inclusive.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the quantiles are computed. The default is
        to compute the quantile(s) along a flattened version of the array.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape and buffer length as the expected output, but the
        type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
        If True, then allow the input array `a` to be modified by
        intermediate calculations, to save memory. In this case, the
        contents of the input `a` after this function completes is
        undefined.
    method : str, optional
        This parameter specifies the method to use for estimating the
        quantile.  There are many different methods, some unique to NumPy.
        The recommended options, numbered as they appear in [1]_, are:

        1. 'inverted_cdf'
        2. 'averaged_inverted_cdf'
        3. 'closest_observation'
        4. 'interpolated_inverted_cdf'
        5. 'hazen'
        6. 'weibull'
        7. 'linear'  (default)
        8. 'median_unbiased'
        9. 'normal_unbiased'

        The first three methods are discontinuous. For backward compatibility
        with previous versions of NumPy, the following discontinuous variations
        of the default 'linear' (7.) option are available:

        * 'lower'
        * 'higher',
        * 'midpoint'
        * 'nearest'

        See Notes for details.

        .. versionchanged:: 1.22.0
            This argument was previously called "interpolation" and only
            offered the "linear" default and last four options.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left in
        the result as dimensions with size one. With this option, the
        result will broadcast correctly against the original array `a`.

    weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the quantile according to its associated weight.
        The weights array can either be 1-D (in which case its length must be
        the size of `a` along the given axis) or of the same shape as `a`.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        Only `method="inverted_cdf"` supports weights.
        See the notes for more details.

        .. versionadded:: 2.0.0

    interpolation : str, optional
        Deprecated name for the method keyword argument.

        .. deprecated:: 1.22.0

    Returns
    -------
    quantile : scalar or ndarray
        If `q` is a single probability and `axis=None`, then the result
        is a scalar. If multiple probability levels are given, first axis
        of the result corresponds to the quantiles. The other axes are
        the axes that remain after the reduction of `a`. If the input
        contains integers or floats smaller than ``float64``, the output
        data-type is ``float64``. Otherwise, the output data-type is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    mean
    percentile : equivalent to quantile, but with q in the range [0, 100].
    median : equivalent to ``quantile(..., 0.5)``
    nanquantile

    Notes
    -----
    Given a sample `a` from an underlying distribution, `quantile` provides a
    nonparametric estimate of the inverse cumulative distribution function.

    By default, this is done by interpolating between adjacent elements in
    ``y``, a sorted copy of `a`::

        (1-g)*y[j] + g*y[j+1]

    where the index ``j`` and coefficient ``g`` are the integral and
    fractional components of ``q * (n-1)``, and ``n`` is the number of
    elements in the sample.

    This is a special case of Equation 1 of H&F [1]_. More generally,

    - ``j = (q*n + m - 1) // 1``, and
    - ``g = (q*n + m - 1) % 1``,

    where ``m`` may be defined according to several different conventions.
    The preferred convention may be selected using the ``method`` parameter:

    =============================== =============== ===============
    ``method``                      number in H&F   ``m``
    =============================== =============== ===============
    ``interpolated_inverted_cdf``   4               ``0``
    ``hazen``                       5               ``1/2``
    ``weibull``                     6               ``q``
    ``linear`` (default)            7               ``1 - q``
    ``median_unbiased``             8               ``q/3 + 1/3``
    ``normal_unbiased``             9               ``q/4 + 3/8``
    =============================== =============== ===============

    Note that indices ``j`` and ``j + 1`` are clipped to the range ``0`` to
    ``n - 1`` when the results of the formula would be outside the allowed
    range of non-negative indices. The ``- 1`` in the formulas for ``j`` and
    ``g`` accounts for Python's 0-based indexing.

    The table above includes only the estimators from H&F that are continuous
    functions of probability `q` (estimators 4-9). NumPy also provides the
    three discontinuous estimators from H&F (estimators 1-3), where ``j`` is
    defined as above, ``m`` is defined as follows, and ``g`` is a function
    of the real-valued ``index = q*n + m - 1`` and ``j``.

    1. ``inverted_cdf``: ``m = 0`` and ``g = int(index - j > 0)``
    2. ``averaged_inverted_cdf``: ``m = 0`` and
       ``g = (1 + int(index - j > 0)) / 2``
    3. ``closest_observation``: ``m = -1/2`` and
       ``g = 1 - int((index == j) & (j%2 == 1))``

    For backward compatibility with previous versions of NumPy, `quantile`
    provides four additional discontinuous estimators. Like
    ``method='linear'``, all have ``m = 1 - q`` so that ``j = q*(n-1) // 1``,
    but ``g`` is defined as follows.

    - ``lower``: ``g = 0``
    - ``midpoint``: ``g = 0.5``
    - ``higher``: ``g = 1``
    - ``nearest``: ``g = (q*(n-1) % 1) > 0.5``

    **Weighted quantiles:**
    More formally, the quantile at probability level :math:`q` of a cumulative
    distribution function :math:`F(y)=P(Y \\leq y)` with probability measure
    :math:`P` is defined as any number :math:`x` that fulfills the
    *coverage conditions*

    .. math:: P(Y < x) \\leq q \\quad\\text{and}\\quad P(Y \\leq x) \\geq q

    with random variable :math:`Y\\sim P`.
    Sample quantiles, the result of `quantile`, provide nonparametric
    estimation of the underlying population counterparts, represented by the
    unknown :math:`F`, given a data vector `a` of length ``n``.

    Some of the estimators above arise when one considers :math:`F` as the
    empirical distribution function of the data, i.e.
    :math:`F(y) = \\frac{1}{n} \\sum_i 1_{a_i \\leq y}`.
    Then, different methods correspond to different choices of :math:`x` that
    fulfill the above coverage conditions. Methods that follow this approach
    are ``inverted_cdf`` and ``averaged_inverted_cdf``.

    For weighted quantiles, the coverage conditions still hold. The
    empirical cumulative distribution is simply replaced by its weighted
    version, i.e.
    :math:`P(Y \\leq t) = \\frac{1}{\\sum_i w_i} \\sum_i w_i 1_{x_i \\leq t}`.
    Only ``method="inverted_cdf"`` supports weights.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10, 7, 4], [3, 2, 1]])
    >>> a
    array([[10,  7,  4],
           [ 3,  2,  1]])
    >>> np.quantile(a, 0.5)
    3.5
    >>> np.quantile(a, 0.5, axis=0)
    array([6.5, 4.5, 2.5])
    >>> np.quantile(a, 0.5, axis=1)
    array([7.,  2.])
    >>> np.quantile(a, 0.5, axis=1, keepdims=True)
    array([[7.],
           [2.]])
    >>> m = np.quantile(a, 0.5, axis=0)
    >>> out = np.zeros_like(m)
    >>> np.quantile(a, 0.5, axis=0, out=out)
    array([6.5, 4.5, 2.5])
    >>> m
    array([6.5, 4.5, 2.5])
    >>> b = a.copy()
    >>> np.quantile(b, 0.5, axis=1, overwrite_input=True)
    array([7.,  2.])
    >>> assert not np.all(a == b)

    See also `numpy.percentile` for a visualization of most methods.

    References
    ----------
    .. [1] R. J. Hyndman and Y. Fan,
       "Sample quantiles in statistical packages,"
       The American Statistician, 50(4), pp. 361-365, 1996

    """
    if interpolation is not None:
        method = _check_interpolation_as_method(
            method, interpolation, "quantile")

    a = np.asanyarray(a)
    if a.dtype.kind == "c":
        raise TypeError("a must be an array of real numbers")

    # Use dtype of array if possible (e.g., if q is a python int or float).
    if isinstance(q, (int, float)) and a.dtype.kind == "f":
        q = np.asanyarray(q, dtype=a.dtype)
    else:
        q = np.asanyarray(q)

    if not _quantile_is_valid(q):
        raise ValueError("Quantiles must be in the range [0, 1]")

    if weights is not None:
        if method != "inverted_cdf":
            msg = ("Only method 'inverted_cdf' supports weights. "
                   f"Got: {method}.")
            raise ValueError(msg)
        if axis is not None:
            axis = _nx.normalize_axis_tuple(axis, a.ndim, argname="axis")
        weights = _weights_are_valid(weights=weights, a=a, axis=axis)
        if np.any(weights < 0):
            raise ValueError("Weights must be non-negative.")

    return _quantile_unchecked(
        a, q, axis, out, overwrite_input, method, keepdims, weights)


def _quantile_unchecked(a,
                        q,
                        axis=None,
                        out=None,
                        overwrite_input=False,
                        method="linear",
                        keepdims=False,
                        weights=None):
    """Assumes that q is in [0, 1], and is an ndarray"""
    return _ureduce(a,
                    func=_quantile_ureduce_func,
                    q=q,
                    weights=weights,
                    keepdims=keepdims,
                    axis=axis,
                    out=out,
                    overwrite_input=overwrite_input,
                    method=method)


def _quantile_is_valid(q):
    # avoid expensive reductions, relevant for arrays with < O(1000) elements
    if q.ndim == 1 and q.size < 10:
        for i in range(q.size):
            if not (0.0 <= q[i] <= 1.0):
                return False
    elif not (q.min() >= 0 and q.max() <= 1):
        return False
    return True


def _check_interpolation_as_method(method, interpolation, fname):
    # Deprecated NumPy 1.22, 2021-11-08
    warnings.warn(
        f"the `interpolation=` argument to {fname} was renamed to "
        "`method=`, which has additional options.\n"
        "Users of the modes 'nearest', 'lower', 'higher', or "
        "'midpoint' are encouraged to review the method they used. "
        "(Deprecated NumPy 1.22)",
        DeprecationWarning, stacklevel=4)
    if method != "linear":
        # sanity check, we assume this basically never happens
        raise TypeError(
            "You shall not pass both `method` and `interpolation`!\n"
            "(`interpolation` is Deprecated in favor of `method`)")
    return interpolation


def _compute_virtual_index(n, quantiles, alpha: float, beta: float):
    """
    Compute the floating point indexes of an array for the linear
    interpolation of quantiles.
    n : array_like
        The sample sizes.
    quantiles : array_like
        The quantiles values.
    alpha : float
        A constant used to correct the index computed.
    beta : float
        A constant used to correct the index computed.

    alpha and beta values depend on the chosen method
    (see quantile documentation)

    Reference:
    Hyndman&Fan paper "Sample Quantiles in Statistical Packages",
    DOI: 10.1080/00031305.1996.10473566
    """
    return n * quantiles + (
            alpha + quantiles * (1 - alpha - beta)
    ) - 1


def _get_gamma(virtual_indexes, previous_indexes, method):
    """
    Compute gamma (a.k.a 'm' or 'weight') for the linear interpolation
    of quantiles.

    virtual_indexes : array_like
        The indexes where the percentile is supposed to be found in the sorted
        sample.
    previous_indexes : array_like
        The floor values of virtual_indexes.
    interpolation : dict
        The interpolation method chosen, which may have a specific rule
        modifying gamma.

    gamma is usually the fractional part of virtual_indexes but can be modified
    by the interpolation method.
    """
    gamma = np.asanyarray(virtual_indexes - previous_indexes)
    gamma = method["fix_gamma"](gamma, virtual_indexes)
    # Ensure both that we have an array, and that we keep the dtype
    # (which may have been matched to the input array).
    return np.asanyarray(gamma, dtype=virtual_indexes.dtype)


def _lerp(a, b, t, out=None):
    """
    Compute the linear interpolation weighted by gamma on each point of
    two same shape array.

    a : array_like
        Left bound.
    b : array_like
        Right bound.
    t : array_like
        The interpolation weight.
    out : array_like
        Output array.
    """
    diff_b_a = subtract(b, a)
    # asanyarray is a stop-gap until gh-13105
    lerp_interpolation = asanyarray(add(a, diff_b_a * t, out=out))
    subtract(b, diff_b_a * (1 - t), out=lerp_interpolation, where=t >= 0.5,
             casting='unsafe', dtype=type(lerp_interpolation.dtype))
    if lerp_interpolation.ndim == 0 and out is None:
        lerp_interpolation = lerp_interpolation[()]  # unpack 0d arrays
    return lerp_interpolation


def _get_gamma_mask(shape, default_value, conditioned_value, where):
    out = np.full(shape, default_value)
    np.copyto(out, conditioned_value, where=where, casting="unsafe")
    return out


def _discrete_interpolation_to_boundaries(index, gamma_condition_fun):
    previous = np.floor(index)
    next = previous + 1
    gamma = index - previous
    res = _get_gamma_mask(shape=index.shape,
                          default_value=next,
                          conditioned_value=previous,
                          where=gamma_condition_fun(gamma, index)
                          ).astype(np.intp)
    # Some methods can lead to out-of-bound integers, clip them:
    res[res < 0] = 0
    return res


def _closest_observation(n, quantiles):
    # "choose the nearest even order statistic at g=0" (H&F (1996) pp. 362).
    # Order is 1-based so for zero-based indexing round to nearest odd index.
    gamma_fun = lambda gamma, index: (gamma == 0) & (np.floor(index) % 2 == 1)
    return _discrete_interpolation_to_boundaries((n * quantiles) - 1 - 0.5,
                                                 gamma_fun)


def _inverted_cdf(n, quantiles):
    gamma_fun = lambda gamma, _: (gamma == 0)
    return _discrete_interpolation_to_boundaries((n * quantiles) - 1,
                                                 gamma_fun)


def _quantile_ureduce_func(
        a: np.array,
        q: np.array,
        weights: np.array,
        axis: int | None = None,
        out=None,
        overwrite_input: bool = False,
        method="linear",
) -> np.array:
    if q.ndim > 2:
        # The code below works fine for nd, but it might not have useful
        # semantics. For now, keep the supported dimensions the same as it was
        # before.
        raise ValueError("q must be a scalar or 1d")
    if overwrite_input:
        if axis is None:
            axis = 0
            arr = a.ravel()
            wgt = None if weights is None else weights.ravel()
        else:
            arr = a
            wgt = weights
    elif axis is None:
        axis = 0
        arr = a.flatten()
        wgt = None if weights is None else weights.flatten()
    else:
        arr = a.copy()
        wgt = weights
    result = _quantile(arr,
                       quantiles=q,
                       axis=axis,
                       method=method,
                       out=out,
                       weights=wgt)
    return result


def _get_indexes(arr, virtual_indexes, valid_values_count):
    """
    Get the valid indexes of arr neighbouring virtual_indexes.
    Note
    This is a companion function to linear interpolation of
    Quantiles

    Returns
    -------
    (previous_indexes, next_indexes): Tuple
        A Tuple of virtual_indexes neighbouring indexes
    """
    previous_indexes = np.asanyarray(np.floor(virtual_indexes))
    next_indexes = np.asanyarray(previous_indexes + 1)
    indexes_above_bounds = virtual_indexes >= valid_values_count - 1
    # When indexes is above max index, take the max value of the array
    if indexes_above_bounds.any():
        previous_indexes[indexes_above_bounds] = -1
        next_indexes[indexes_above_bounds] = -1
    # When indexes is below min index, take the min value of the array
    indexes_below_bounds = virtual_indexes < 0
    if indexes_below_bounds.any():
        previous_indexes[indexes_below_bounds] = 0
        next_indexes[indexes_below_bounds] = 0
    if np.issubdtype(arr.dtype, np.inexact):
        # After the sort, slices having NaNs will have for last element a NaN
        virtual_indexes_nans = np.isnan(virtual_indexes)
        if virtual_indexes_nans.any():
            previous_indexes[virtual_indexes_nans] = -1
            next_indexes[virtual_indexes_nans] = -1
    previous_indexes = previous_indexes.astype(np.intp)
    next_indexes = next_indexes.astype(np.intp)
    return previous_indexes, next_indexes


def _quantile(
        arr: np.array,
        quantiles: np.array,
        axis: int = -1,
        method="linear",
        out=None,
        weights=None,
):
    """
    Private function that doesn't support extended axis or keepdims.
    These methods are extended to this function using _ureduce
    See nanpercentile for parameter usage
    It computes the quantiles of the array for the given axis.
    A linear interpolation is performed based on the `interpolation`.

    By default, the method is "linear" where alpha == beta == 1 which
    performs the 7th method of Hyndman&Fan.
    With "median_unbiased" we get alpha == beta == 1/3
    thus the 8th method of Hyndman&Fan.
    """
    # --- Setup
    arr = np.asanyarray(arr)
    values_count = arr.shape[axis]
    # The dimensions of `q` are prepended to the output shape, so we need the
    # axis being sampled from `arr` to be last.
    if axis != 0:  # But moveaxis is slow, so only call it if necessary.
        arr = np.moveaxis(arr, axis, destination=0)
    supports_nans = (
        np.issubdtype(arr.dtype, np.inexact) or arr.dtype.kind in 'Mm'
    )

    if weights is None:
        # --- Computation of indexes
        # Index where to find the value in the sorted array.
        # Virtual because it is a floating point value, not an valid index.
        # The nearest neighbours are used for interpolation
        try:
            method_props = _QuantileMethods[method]
        except KeyError:
            raise ValueError(
                f"{method!r} is not a valid method. Use one of: "
                f"{_QuantileMethods.keys()}") from None
        virtual_indexes = method_props["get_virtual_index"](values_count,
                                                            quantiles)
        virtual_indexes = np.asanyarray(virtual_indexes)

        if method_props["fix_gamma"] is None:
            supports_integers = True
        else:
            int_virtual_indices = np.issubdtype(virtual_indexes.dtype,
                                                np.integer)
            supports_integers = method == 'linear' and int_virtual_indices

        if supports_integers:
            # No interpolation needed, take the points along axis
            if supports_nans:
                # may contain nan, which would sort to the end
                arr.partition(
                    concatenate((virtual_indexes.ravel(), [-1])), axis=0,
                )
                slices_having_nans = np.isnan(arr[-1, ...])
            else:
                # cannot contain nan
                arr.partition(virtual_indexes.ravel(), axis=0)
                slices_having_nans = np.array(False, dtype=bool)
            result = take(arr, virtual_indexes, axis=0, out=out)
        else:
            previous_indexes, next_indexes = _get_indexes(arr,
                                                          virtual_indexes,
                                                          values_count)
            # --- Sorting
            arr.partition(
                np.unique(np.concatenate(([0, -1],
                                          previous_indexes.ravel(),
                                          next_indexes.ravel(),
                                          ))),
                axis=0)
            if supports_nans:
                slices_having_nans = np.isnan(arr[-1, ...])
            else:
                slices_having_nans = None
            # --- Get values from indexes
            previous = arr[previous_indexes]
            next = arr[next_indexes]
            # --- Linear interpolation
            gamma = _get_gamma(virtual_indexes, previous_indexes, method_props)
            result_shape = virtual_indexes.shape + (1,) * (arr.ndim - 1)
            gamma = gamma.reshape(result_shape)
            result = _lerp(previous,
                        next,
                        gamma,
                        out=out)
    else:
        # Weighted case
        # This implements method="inverted_cdf", the only supported weighted
        # method, which needs to sort anyway.
        weights = np.asanyarray(weights)
        if axis != 0:
            weights = np.moveaxis(weights, axis, destination=0)
        index_array = np.argsort(arr, axis=0, kind="stable")

        # arr = arr[index_array, ...]  # but this adds trailing dimensions of
        # 1.
        arr = np.take_along_axis(arr, index_array, axis=0)
        if weights.shape == arr.shape:
            weights = np.take_along_axis(weights, index_array, axis=0)
        else:
            # weights is 1d
            weights = weights.reshape(-1)[index_array, ...]

        if supports_nans:
            # may contain nan, which would sort to the end
            slices_having_nans = np.isnan(arr[-1, ...])
        else:
            # cannot contain nan
            slices_having_nans = np.array(False, dtype=bool)

        # We use the weights to calculate the empirical cumulative
        # distribution function cdf
        cdf = weights.cumsum(axis=0, dtype=np.float64)
        cdf /= cdf[-1, ...]  # normalization to 1
        # Search index i such that
        #   sum(weights[j], j=0..i-1) < quantile <= sum(weights[j], j=0..i)
        # is then equivalent to
        #   cdf[i-1] < quantile <= cdf[i]
        # Unfortunately, searchsorted only accepts 1-d arrays as first
        # argument, so we will need to iterate over dimensions.

        # Without the following cast, searchsorted can return surprising
        # results, e.g.
        #   np.searchsorted(np.array([0.2, 0.4, 0.6, 0.8, 1.]),
        #                   np.array(0.4, dtype=np.float32), side="left")
        # returns 2 instead of 1 because 0.4 is not binary representable.
        if quantiles.dtype.kind == "f":
            cdf = cdf.astype(quantiles.dtype)
        # Weights must be non-negative, so we might have zero weights at the
        # beginning leading to some leading zeros in cdf. The call to
        # np.searchsorted for quantiles=0 will then pick the first element,
        # but should pick the first one larger than zero. We
        # therefore simply set 0 values in cdf to -1.
        if np.any(cdf[0, ...] == 0):
            cdf[cdf == 0] = -1

        def find_cdf_1d(arr, cdf):
            indices = np.searchsorted(cdf, quantiles, side="left")
            # We might have reached the maximum with i = len(arr), e.g. for
            # quantiles = 1, and need to cut it to len(arr) - 1.
            indices = minimum(indices, values_count - 1)
            result = take(arr, indices, axis=0)
            return result

        r_shape = arr.shape[1:]
        if quantiles.ndim > 0:
            r_shape = quantiles.shape + r_shape
        if out is None:
            result = np.empty_like(arr, shape=r_shape)
        else:
            if out.shape != r_shape:
                msg = (f"Wrong shape of argument 'out', shape={r_shape} is "
                       f"required; got shape={out.shape}.")
                raise ValueError(msg)
            result = out

        # See apply_along_axis, which we do for axis=0. Note that Ni = (,)
        # always, so we remove it here.
        Nk = arr.shape[1:]
        for kk in np.ndindex(Nk):
            result[(...,) + kk] = find_cdf_1d(
                arr[np.s_[:, ] + kk], cdf[np.s_[:, ] + kk]
            )

        # Make result the same as in unweighted inverted_cdf.
        if result.shape == () and result.dtype == np.dtype("O"):
            result = result.item()

    if np.any(slices_having_nans):
        if result.ndim == 0 and out is None:
            # can't write to a scalar, but indexing will be correct
            result = arr[-1]
        else:
            np.copyto(result, arr[-1, ...], where=slices_having_nans)
    return result


def _trapezoid_dispatcher(y, x=None, dx=None, axis=None):
    return (y, x)


@array_function_dispatch(_trapezoid_dispatcher)
def trapezoid(y, x=None, dx=1.0, axis=-1):
    r"""
    Integrate along the given axis using the composite trapezoidal rule.

    If `x` is provided, the integration happens in sequence along its
    elements - they are not sorted.

    Integrate `y` (`x`) along each 1d slice on the given axis, compute
    :math:`\int y(x) dx`.
    When `x` is specified, this integrates along the parametric curve,
    computing :math:`\int_t y(t) dt =
    \int_t y(t) \left.\frac{dx}{dt}\right|_{x=x(t)} dt`.

    .. versionadded:: 2.0.0

    Parameters
    ----------
    y : array_like
        Input array to integrate.
    x : array_like, optional
        The sample points corresponding to the `y` values. If `x` is None,
        the sample points are assumed to be evenly spaced `dx` apart. The
        default is None.
    dx : scalar, optional
        The spacing between sample points when `x` is None. The default is 1.
    axis : int, optional
        The axis along which to integrate.

    Returns
    -------
    trapezoid : float or ndarray
        Definite integral of `y` = n-dimensional array as approximated along
        a single axis by the trapezoidal rule. If `y` is a 1-dimensional array,
        then the result is a float. If `n` is greater than 1, then the result
        is an `n`-1 dimensional array.

    See Also
    --------
    sum, cumsum

    Notes
    -----
    Image [2]_ illustrates trapezoidal rule -- y-axis locations of points
    will be taken from `y` array, by default x-axis distances between
    points will be 1.0, alternatively they can be provided with `x` array
    or with `dx` scalar.  Return value will be equal to combined area under
    the red lines.


    References
    ----------
    .. [1] Wikipedia page: https://en.wikipedia.org/wiki/Trapezoidal_rule

    .. [2] Illustration image:
           https://en.wikipedia.org/wiki/File:Composite_trapezoidal_rule_illustration.png

    Examples
    --------
    >>> import numpy as np

    Use the trapezoidal rule on evenly spaced points:

    >>> np.trapezoid([1, 2, 3])
    4.0

    The spacing between sample points can be selected by either the
    ``x`` or ``dx`` arguments:

    >>> np.trapezoid([1, 2, 3], x=[4, 6, 8])
    8.0
    >>> np.trapezoid([1, 2, 3], dx=2)
    8.0

    Using a decreasing ``x`` corresponds to integrating in reverse:

    >>> np.trapezoid([1, 2, 3], x=[8, 6, 4])
    -8.0

    More generally ``x`` is used to integrate along a parametric curve. We can
    estimate the integral :math:`\int_0^1 x^2 = 1/3` using:

    >>> x = np.linspace(0, 1, num=50)
    >>> y = x**2
    >>> np.trapezoid(y, x)
    0.33340274885464394

    Or estimate the area of a circle, noting we repeat the sample which closes
    the curve:

    >>> theta = np.linspace(0, 2 * np.pi, num=1000, endpoint=True)
    >>> np.trapezoid(np.cos(theta), x=np.sin(theta))
    3.141571941375841

    ``np.trapezoid`` can be applied along a specified axis to do multiple
    computations in one call:

    >>> a = np.arange(6).reshape(2, 3)
    >>> a
    array([[0, 1, 2],
           [3, 4, 5]])
    >>> np.trapezoid(a, axis=0)
    array([1.5, 2.5, 3.5])
    >>> np.trapezoid(a, axis=1)
    array([2.,  8.])
    """

    y = asanyarray(y)
    if x is None:
        d = dx
    else:
        x = asanyarray(x)
        if x.ndim == 1:
            d = diff(x)
            # reshape to correct shape
            shape = [1] * y.ndim
            shape[axis] = d.shape[0]
            d = d.reshape(shape)
        else:
            d = diff(x, axis=axis)
    nd = y.ndim
    slice1 = [slice(None)] * nd
    slice2 = [slice(None)] * nd
    slice1[axis] = slice(1, None)
    slice2[axis] = slice(None, -1)
    try:
        ret = (d * (y[tuple(slice1)] + y[tuple(slice2)]) / 2.0).sum(axis)
    except ValueError:
        # Operations didn't work, cast to ndarray
        d = np.asarray(d)
        y = np.asarray(y)
        ret = add.reduce(d * (y[tuple(slice1)] + y[tuple(slice2)]) / 2.0, axis)
    return ret


@set_module('numpy')
def trapz(y, x=None, dx=1.0, axis=-1):
    """
    `trapz` is deprecated in NumPy 2.0.

    Please use `trapezoid` instead, or one of the numerical integration
    functions in `scipy.integrate`.
    """
    # Deprecated in NumPy 2.0, 2023-08-18
    warnings.warn(
        "`trapz` is deprecated. Use `trapezoid` instead, or one of the "
        "numerical integration functions in `scipy.integrate`.",
        DeprecationWarning,
        stacklevel=2
    )
    return trapezoid(y, x=x, dx=dx, axis=axis)


def _meshgrid_dispatcher(*xi, copy=None, sparse=None, indexing=None):
    return xi


# Based on scitools meshgrid
@array_function_dispatch(_meshgrid_dispatcher)
def meshgrid(*xi, copy=True, sparse=False, indexing='xy'):
    """
    Return a tuple of coordinate matrices from coordinate vectors.

    Make N-D coordinate arrays for vectorized evaluations of
    N-D scalar/vector fields over N-D grids, given
    one-dimensional coordinate arrays x1, x2,..., xn.

    Parameters
    ----------
    x1, x2,..., xn : array_like
        1-D arrays representing the coordinates of a grid.
    indexing : {'xy', 'ij'}, optional
        Cartesian ('xy', default) or matrix ('ij') indexing of output.
        See Notes for more details.
    sparse : bool, optional
        If True the shape of the returned coordinate array for dimension *i*
        is reduced from ``(N1, ..., Ni, ... Nn)`` to
        ``(1, ..., 1, Ni, 1, ..., 1)``.  These sparse coordinate grids are
        intended to be used with :ref:`basics.broadcasting`.  When all
        coordinates are used in an expression, broadcasting still leads to a
        fully-dimensonal result array.

        Default is False.

    copy : bool, optional
        If False, a view into the original arrays are returned in order to
        conserve memory.  Default is True.  Please note that
        ``sparse=False, copy=False`` will likely return non-contiguous
        arrays.  Furthermore, more than one element of a broadcast array
        may refer to a single memory location.  If you need to write to the
        arrays, make copies first.

    Returns
    -------
    X1, X2,..., XN : tuple of ndarrays
        For vectors `x1`, `x2`,..., `xn` with lengths ``Ni=len(xi)``,
        returns ``(N1, N2, N3,..., Nn)`` shaped arrays if indexing='ij'
        or ``(N2, N1, N3,..., Nn)`` shaped arrays if indexing='xy'
        with the elements of `xi` repeated to fill the matrix along
        the first dimension for `x1`, the second for `x2` and so on.

    Notes
    -----
    This function supports both indexing conventions through the indexing
    keyword argument.  Giving the string 'ij' returns a meshgrid with
    matrix indexing, while 'xy' returns a meshgrid with Cartesian indexing.
    In the 2-D case with inputs of length M and N, the outputs are of shape
    (N, M) for 'xy' indexing and (M, N) for 'ij' indexing.  In the 3-D case
    with inputs of length M, N and P, outputs are of shape (N, M, P) for
    'xy' indexing and (M, N, P) for 'ij' indexing.  The difference is
    illustrated by the following code snippet::

        xv, yv = np.meshgrid(x, y, indexing='ij')
        for i in range(nx):
            for j in range(ny):
                # treat xv[i,j], yv[i,j]

        xv, yv = np.meshgrid(x, y, indexing='xy')
        for i in range(nx):
            for j in range(ny):
                # treat xv[j,i], yv[j,i]

    In the 1-D and 0-D case, the indexing and sparse keywords have no effect.

    See Also
    --------
    mgrid : Construct a multi-dimensional "meshgrid" using indexing notation.
    ogrid : Construct an open multi-dimensional "meshgrid" using indexing
            notation.
    :ref:`how-to-index`

    Examples
    --------
    >>> import numpy as np
    >>> nx, ny = (3, 2)
    >>> x = np.linspace(0, 1, nx)
    >>> y = np.linspace(0, 1, ny)
    >>> xv, yv = np.meshgrid(x, y)
    >>> xv
    array([[0. , 0.5, 1. ],
           [0. , 0.5, 1. ]])
    >>> yv
    array([[0.,  0.,  0.],
           [1.,  1.,  1.]])

    The result of `meshgrid` is a coordinate grid:

    >>> import matplotlib.pyplot as plt
    >>> plt.plot(xv, yv, marker='o', color='k', linestyle='none')
    >>> plt.show()

    You can create sparse output arrays to save memory and computation time.

    >>> xv, yv = np.meshgrid(x, y, sparse=True)
    >>> xv
    array([[0. ,  0.5,  1. ]])
    >>> yv
    array([[0.],
           [1.]])

    `meshgrid` is very useful to evaluate functions on a grid. If the
    function depends on all coordinates, both dense and sparse outputs can be
    used.

    >>> x = np.linspace(-5, 5, 101)
    >>> y = np.linspace(-5, 5, 101)
    >>> # full coordinate arrays
    >>> xx, yy = np.meshgrid(x, y)
    >>> zz = np.sqrt(xx**2 + yy**2)
    >>> xx.shape, yy.shape, zz.shape
    ((101, 101), (101, 101), (101, 101))
    >>> # sparse coordinate arrays
    >>> xs, ys = np.meshgrid(x, y, sparse=True)
    >>> zs = np.sqrt(xs**2 + ys**2)
    >>> xs.shape, ys.shape, zs.shape
    ((1, 101), (101, 1), (101, 101))
    >>> np.array_equal(zz, zs)
    True

    >>> h = plt.contourf(x, y, zs)
    >>> plt.axis('scaled')
    >>> plt.colorbar()
    >>> plt.show()
    """
    ndim = len(xi)

    if indexing not in ['xy', 'ij']:
        raise ValueError(
            "Valid values for `indexing` are 'xy' and 'ij'.")

    s0 = (1,) * ndim
    output = [np.asanyarray(x).reshape(s0[:i] + (-1,) + s0[i + 1:])
              for i, x in enumerate(xi)]

    if indexing == 'xy' and ndim > 1:
        # switch first and second axis
        output[0].shape = (1, -1) + s0[2:]
        output[1].shape = (-1, 1) + s0[2:]

    if not sparse:
        # Return the full N-D matrix (not only the 1-D vector)
        output = np.broadcast_arrays(*output, subok=True)

    if copy:
        output = tuple(x.copy() for x in output)

    return output


def _delete_dispatcher(arr, obj, axis=None):
    return (arr, obj)


@array_function_dispatch(_delete_dispatcher)
def delete(arr, obj, axis=None):
    """
    Return a new array with sub-arrays along an axis deleted. For a one
    dimensional array, this returns those entries not returned by
    `arr[obj]`.

    Parameters
    ----------
    arr : array_like
        Input array.
    obj : slice, int, array-like of ints or bools
        Indicate indices of sub-arrays to remove along the specified axis.

        .. versionchanged:: 1.19.0
            Boolean indices are now treated as a mask of elements to remove,
            rather than being cast to the integers 0 and 1.

    axis : int, optional
        The axis along which to delete the subarray defined by `obj`.
        If `axis` is None, `obj` is applied to the flattened array.

    Returns
    -------
    out : ndarray
        A copy of `arr` with the elements specified by `obj` removed. Note
        that `delete` does not occur in-place. If `axis` is None, `out` is
        a flattened array.

    See Also
    --------
    insert : Insert elements into an array.
    append : Append elements at the end of an array.

    Notes
    -----
    Often it is preferable to use a boolean mask. For example:

    >>> arr = np.arange(12) + 1
    >>> mask = np.ones(len(arr), dtype=bool)
    >>> mask[[0,2,4]] = False
    >>> result = arr[mask,...]

    Is equivalent to ``np.delete(arr, [0,2,4], axis=0)``, but allows further
    use of `mask`.

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.array([[1,2,3,4], [5,6,7,8], [9,10,11,12]])
    >>> arr
    array([[ 1,  2,  3,  4],
           [ 5,  6,  7,  8],
           [ 9, 10, 11, 12]])
    >>> np.delete(arr, 1, 0)
    array([[ 1,  2,  3,  4],
           [ 9, 10, 11, 12]])

    >>> np.delete(arr, np.s_[::2], 1)
    array([[ 2,  4],
           [ 6,  8],
           [10, 12]])
    >>> np.delete(arr, [1,3,5], None)
    array([ 1,  3,  5,  7,  8,  9, 10, 11, 12])

    """
    conv = _array_converter(arr)
    arr, = conv.as_arrays(subok=False)

    ndim = arr.ndim
    arrorder = 'F' if arr.flags.fnc else 'C'
    if axis is None:
        if ndim != 1:
            arr = arr.ravel()
        # needed for np.matrix, which is still not 1d after being ravelled
        ndim = arr.ndim
        axis = ndim - 1
    else:
        axis = normalize_axis_index(axis, ndim)

    slobj = [slice(None)] * ndim
    N = arr.shape[axis]
    newshape = list(arr.shape)

    if isinstance(obj, slice):
        start, stop, step = obj.indices(N)
        xr = range(start, stop, step)
        numtodel = len(xr)

        if numtodel <= 0:
            return conv.wrap(arr.copy(order=arrorder), to_scalar=False)

        # Invert if step is negative:
        if step < 0:
            step = -step
            start = xr[-1]
            stop = xr[0] + 1

        newshape[axis] -= numtodel
        new = empty(newshape, arr.dtype, arrorder)
        # copy initial chunk
        if start == 0:
            pass
        else:
            slobj[axis] = slice(None, start)
            new[tuple(slobj)] = arr[tuple(slobj)]
        # copy end chunk
        if stop == N:
            pass
        else:
            slobj[axis] = slice(stop - numtodel, None)
            slobj2 = [slice(None)] * ndim
            slobj2[axis] = slice(stop, None)
            new[tuple(slobj)] = arr[tuple(slobj2)]
        # copy middle pieces
        if step == 1:
            pass
        else:  # use array indexing.
            keep = ones(stop - start, dtype=bool)
            keep[:stop - start:step] = False
            slobj[axis] = slice(start, stop - numtodel)
            slobj2 = [slice(None)] * ndim
            slobj2[axis] = slice(start, stop)
            arr = arr[tuple(slobj2)]
            slobj2[axis] = keep
            new[tuple(slobj)] = arr[tuple(slobj2)]

        return conv.wrap(new, to_scalar=False)

    if isinstance(obj, (int, integer)) and not isinstance(obj, bool):
        single_value = True
    else:
        single_value = False
        _obj = obj
        obj = np.asarray(obj)
        # `size == 0` to allow empty lists similar to indexing, but (as there)
        # is really too generic:
        if obj.size == 0 and not isinstance(_obj, np.ndarray):
            obj = obj.astype(intp)
        elif obj.size == 1 and obj.dtype.kind in "ui":
            # For a size 1 integer array we can use the single-value path
            # (most dtypes, except boolean, should just fail later).
            obj = obj.item()
            single_value = True

    if single_value:
        # optimization for a single value
        if (obj < -N or obj >= N):
            raise IndexError(
                f"index {obj} is out of bounds for axis {axis} with "
                f"size {N}")
        if (obj < 0):
            obj += N
        newshape[axis] -= 1
        new = empty(newshape, arr.dtype, arrorder)
        slobj[axis] = slice(None, obj)
        new[tuple(slobj)] = arr[tuple(slobj)]
        slobj[axis] = slice(obj, None)
        slobj2 = [slice(None)] * ndim
        slobj2[axis] = slice(obj + 1, None)
        new[tuple(slobj)] = arr[tuple(slobj2)]
    else:
        if obj.dtype == bool:
            if obj.shape != (N,):
                raise ValueError('boolean array argument obj to delete '
                                 'must be one dimensional and match the axis '
                                 f'length of {N}')

            # optimization, the other branch is slower
            keep = ~obj
        else:
            keep = ones(N, dtype=bool)
            keep[obj,] = False

        slobj[axis] = keep
        new = arr[tuple(slobj)]

    return conv.wrap(new, to_scalar=False)


def _insert_dispatcher(arr, obj, values, axis=None):
    return (arr, obj, values)


@array_function_dispatch(_insert_dispatcher)
def insert(arr, obj, values, axis=None):
    """
    Insert values along the given axis before the given indices.

    Parameters
    ----------
    arr : array_like
        Input array.
    obj : slice, int, array-like of ints or bools
        Object that defines the index or indices before which `values` is
        inserted.

        .. versionchanged:: 2.1.2
            Boolean indices are now treated as a mask of elements to insert,
            rather than being cast to the integers 0 and 1.

        Support for multiple insertions when `obj` is a single scalar or a
        sequence with one element (similar to calling insert multiple
        times).
    values : array_like
        Values to insert into `arr`. If the type of `values` is different
        from that of `arr`, `values` is converted to the type of `arr`.
        `values` should be shaped so that ``arr[...,obj,...] = values``
        is legal.
    axis : int, optional
        Axis along which to insert `values`.  If `axis` is None then `arr`
        is flattened first.

    Returns
    -------
    out : ndarray
        A copy of `arr` with `values` inserted.  Note that `insert`
        does not occur in-place: a new array is returned. If
        `axis` is None, `out` is a flattened array.

    See Also
    --------
    append : Append elements at the end of an array.
    concatenate : Join a sequence of arrays along an existing axis.
    delete : Delete elements from an array.

    Notes
    -----
    Note that for higher dimensional inserts ``obj=0`` behaves very different
    from ``obj=[0]`` just like ``arr[:,0,:] = values`` is different from
    ``arr[:,[0],:] = values``. This is because of the difference between basic
    and advanced :ref:`indexing <basics.indexing>`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(6).reshape(3, 2)
    >>> a
    array([[0, 1],
           [2, 3],
           [4, 5]])
    >>> np.insert(a, 1, 6)
    array([0, 6, 1, 2, 3, 4, 5])
    >>> np.insert(a, 1, 6, axis=1)
    array([[0, 6, 1],
           [2, 6, 3],
           [4, 6, 5]])

    Difference between sequence and scalars,
    showing how ``obj=[1]`` behaves different from ``obj=1``:

    >>> np.insert(a, [1], [[7],[8],[9]], axis=1)
    array([[0, 7, 1],
           [2, 8, 3],
           [4, 9, 5]])
    >>> np.insert(a, 1, [[7],[8],[9]], axis=1)
    array([[0, 7, 8, 9, 1],
           [2, 7, 8, 9, 3],
           [4, 7, 8, 9, 5]])
    >>> np.array_equal(np.insert(a, 1, [7, 8, 9], axis=1),
    ...                np.insert(a, [1], [[7],[8],[9]], axis=1))
    True

    >>> b = a.flatten()
    >>> b
    array([0, 1, 2, 3, 4, 5])
    >>> np.insert(b, [2, 2], [6, 7])
    array([0, 1, 6, 7, 2, 3, 4, 5])

    >>> np.insert(b, slice(2, 4), [7, 8])
    array([0, 1, 7, 2, 8, 3, 4, 5])

    >>> np.insert(b, [2, 2], [7.13, False]) # type casting
    array([0, 1, 7, 0, 2, 3, 4, 5])

    >>> x = np.arange(8).reshape(2, 4)
    >>> idx = (1, 3)
    >>> np.insert(x, idx, 999, axis=1)
    array([[  0, 999,   1,   2, 999,   3],
           [  4, 999,   5,   6, 999,   7]])

    """
    conv = _array_converter(arr)
    arr, = conv.as_arrays(subok=False)

    ndim = arr.ndim
    arrorder = 'F' if arr.flags.fnc else 'C'
    if axis is None:
        if ndim != 1:
            arr = arr.ravel()
        # needed for np.matrix, which is still not 1d after being ravelled
        ndim = arr.ndim
        axis = ndim - 1
    else:
        axis = normalize_axis_index(axis, ndim)
    slobj = [slice(None)] * ndim
    N = arr.shape[axis]
    newshape = list(arr.shape)

    if isinstance(obj, slice):
        # turn it into a range object
        indices = arange(*obj.indices(N), dtype=intp)
    else:
        # need to copy obj, because indices will be changed in-place
        indices = np.array(obj)
        if indices.dtype == bool:
            if obj.ndim != 1:
                raise ValueError('boolean array argument obj to insert '
                                'must be one dimensional')
            indices = np.flatnonzero(obj)
        elif indices.ndim > 1:
            raise ValueError(
                "index array argument obj to insert must be one dimensional "
                "or scalar")
    if indices.size == 1:
        index = indices.item()
        if index < -N or index > N:
            raise IndexError(f"index {obj} is out of bounds for axis {axis} "
                             f"with size {N}")
        if (index < 0):
            index += N

        # There are some object array corner cases here, but we cannot avoid
        # that:
        values = array(values, copy=None, ndmin=arr.ndim, dtype=arr.dtype)
        if indices.ndim == 0:
            # broadcasting is very different here, since a[:,0,:] = ... behaves
            # very different from a[:,[0],:] = ...! This changes values so that
            # it works likes the second case. (here a[:,0:1,:])
            values = np.moveaxis(values, 0, axis)
        numnew = values.shape[axis]
        newshape[axis] += numnew
        new = empty(newshape, arr.dtype, arrorder)
        slobj[axis] = slice(None, index)
        new[tuple(slobj)] = arr[tuple(slobj)]
        slobj[axis] = slice(index, index + numnew)
        new[tuple(slobj)] = values
        slobj[axis] = slice(index + numnew, None)
        slobj2 = [slice(None)] * ndim
        slobj2[axis] = slice(index, None)
        new[tuple(slobj)] = arr[tuple(slobj2)]

        return conv.wrap(new, to_scalar=False)

    elif indices.size == 0 and not isinstance(obj, np.ndarray):
        # Can safely cast the empty list to intp
        indices = indices.astype(intp)

    indices[indices < 0] += N

    numnew = len(indices)
    order = indices.argsort(kind='mergesort')   # stable sort
    indices[order] += np.arange(numnew)

    newshape[axis] += numnew
    old_mask = ones(newshape[axis], dtype=bool)
    old_mask[indices] = False

    new = empty(newshape, arr.dtype, arrorder)
    slobj2 = [slice(None)] * ndim
    slobj[axis] = indices
    slobj2[axis] = old_mask
    new[tuple(slobj)] = values
    new[tuple(slobj2)] = arr

    return conv.wrap(new, to_scalar=False)


def _append_dispatcher(arr, values, axis=None):
    return (arr, values)


@array_function_dispatch(_append_dispatcher)
def append(arr, values, axis=None):
    """
    Append values to the end of an array.

    Parameters
    ----------
    arr : array_like
        Values are appended to a copy of this array.
    values : array_like
        These values are appended to a copy of `arr`.  It must be of the
        correct shape (the same shape as `arr`, excluding `axis`).  If
        `axis` is not specified, `values` can be any shape and will be
        flattened before use.
    axis : int, optional
        The axis along which `values` are appended.  If `axis` is not
        given, both `arr` and `values` are flattened before use.

    Returns
    -------
    append : ndarray
        A copy of `arr` with `values` appended to `axis`.  Note that
        `append` does not occur in-place: a new array is allocated and
        filled.  If `axis` is None, `out` is a flattened array.

    See Also
    --------
    insert : Insert elements into an array.
    delete : Delete elements from an array.

    Examples
    --------
    >>> import numpy as np
    >>> np.append([1, 2, 3], [[4, 5, 6], [7, 8, 9]])
    array([1, 2, 3, ..., 7, 8, 9])

    When `axis` is specified, `values` must have the correct shape.

    >>> np.append([[1, 2, 3], [4, 5, 6]], [[7, 8, 9]], axis=0)
    array([[1, 2, 3],
           [4, 5, 6],
           [7, 8, 9]])

    >>> np.append([[1, 2, 3], [4, 5, 6]], [7, 8, 9], axis=0)
    Traceback (most recent call last):
        ...
    ValueError: all the input arrays must have same number of dimensions, but
    the array at index 0 has 2 dimension(s) and the array at index 1 has 1
    dimension(s)

    >>> a = np.array([1, 2], dtype=int)
    >>> c = np.append(a, [])
    >>> c
    array([1., 2.])
    >>> c.dtype
    float64

    Default dtype for empty ndarrays is `float64` thus making the output of dtype
    `float64` when appended with dtype `int64`

    """
    arr = asanyarray(arr)
    if axis is None:
        if arr.ndim != 1:
            arr = arr.ravel()
        values = ravel(values)
        axis = arr.ndim - 1
    return concatenate((arr, values), axis=axis)


def _digitize_dispatcher(x, bins, right=None):
    return (x, bins)


@array_function_dispatch(_digitize_dispatcher)
def digitize(x, bins, right=False):
    """
    Return the indices of the bins to which each value in input array belongs.

    =========  =============  ============================
    `right`    order of bins  returned index `i` satisfies
    =========  =============  ============================
    ``False``  increasing     ``bins[i-1] <= x < bins[i]``
    ``True``   increasing     ``bins[i-1] < x <= bins[i]``
    ``False``  decreasing     ``bins[i-1] > x >= bins[i]``
    ``True``   decreasing     ``bins[i-1] >= x > bins[i]``
    =========  =============  ============================

    If values in `x` are beyond the bounds of `bins`, 0 or ``len(bins)`` is
    returned as appropriate.

    Parameters
    ----------
    x : array_like
        Input array to be binned. Prior to NumPy 1.10.0, this array had to
        be 1-dimensional, but can now have any shape.
    bins : array_like
        Array of bins. It has to be 1-dimensional and monotonic.
    right : bool, optional
        Indicating whether the intervals include the right or the left bin
        edge. Default behavior is (right==False) indicating that the interval
        does not include the right edge. The left bin end is open in this
        case, i.e., bins[i-1] <= x < bins[i] is the default behavior for
        monotonically increasing bins.

    Returns
    -------
    indices : ndarray of ints
        Output array of indices, of same shape as `x`.

    Raises
    ------
    ValueError
        If `bins` is not monotonic.
    TypeError
        If the type of the input is complex.

    See Also
    --------
    bincount, histogram, unique, searchsorted

    Notes
    -----
    If values in `x` are such that they fall outside the bin range,
    attempting to index `bins` with the indices that `digitize` returns
    will result in an IndexError.

    .. versionadded:: 1.10.0

    `numpy.digitize` is  implemented in terms of `numpy.searchsorted`.
    This means that a binary search is used to bin the values, which scales
    much better for larger number of bins than the previous linear search.
    It also removes the requirement for the input array to be 1-dimensional.

    For monotonically *increasing* `bins`, the following are equivalent::

        np.digitize(x, bins, right=True)
        np.searchsorted(bins, x, side='left')

    Note that as the order of the arguments are reversed, the side must be too.
    The `searchsorted` call is marginally faster, as it does not do any
    monotonicity checks. Perhaps more importantly, it supports all dtypes.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([0.2, 6.4, 3.0, 1.6])
    >>> bins = np.array([0.0, 1.0, 2.5, 4.0, 10.0])
    >>> inds = np.digitize(x, bins)
    >>> inds
    array([1, 4, 3, 2])
    >>> for n in range(x.size):
    ...   print(bins[inds[n]-1], "<=", x[n], "<", bins[inds[n]])
    ...
    0.0 <= 0.2 < 1.0
    4.0 <= 6.4 < 10.0
    2.5 <= 3.0 < 4.0
    1.0 <= 1.6 < 2.5

    >>> x = np.array([1.2, 10.0, 12.4, 15.5, 20.])
    >>> bins = np.array([0, 5, 10, 15, 20])
    >>> np.digitize(x,bins,right=True)
    array([1, 2, 3, 4, 4])
    >>> np.digitize(x,bins,right=False)
    array([1, 3, 3, 4, 5])
    """
    x = _nx.asarray(x)
    bins = _nx.asarray(bins)

    # here for compatibility, searchsorted below is happy to take this
    if np.issubdtype(x.dtype, _nx.complexfloating):
        raise TypeError("x may not be complex")

    mono = _monotonicity(bins)
    if mono == 0:
        raise ValueError("bins must be monotonically increasing or decreasing")

    # this is backwards because the arguments below are swapped
    side = 'left' if right else 'right'
    if mono == -1:
        # reverse the bins, and invert the results
        return len(bins) - _nx.searchsorted(bins[::-1], x, side=side)
    else:
        return _nx.searchsorted(bins, x, side=side)

# === NexusCore/openenv\Lib\site-packages\nltk\app\nemo_app.py ===
# Finding (and Replacing) Nemo, Version 1.1, Aristide Grange 2006/06/06
# https://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496783

"""
Finding (and Replacing) Nemo

Instant Regular Expressions
Created by Aristide Grange
"""
import itertools
import re
from tkinter import SEL_FIRST, SEL_LAST, Frame, Label, PhotoImage, Scrollbar, Text, Tk

windowTitle = "Finding (and Replacing) Nemo"
initialFind = r"n(.*?)e(.*?)m(.*?)o"
initialRepl = r"M\1A\2K\3I"
initialText = """\
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
"""
images = {
    "FIND": "R0lGODlhMAAiAPcAMf/////37//35//n1v97Off///f/9/f37/fexvfOvfeEQvd7QvdrQvdrKfdaKfdSMfdSIe/v9+/v7+/v5+/n3u/e1u/Wxu/Gre+1lO+tnO+thO+Ua+97Y+97Oe97Me9rOe9rMe9jOe9jMe9jIe9aMefe5+fe3ufezuece+eEWudzQudaIedSIedKMedKIedCKedCId7e1t7Wzt7Oxt7Gvd69vd69rd61pd6ljN6UjN6Ue96EY95zY95rUt5rQt5jMd5SId5KIdbn59be3tbGztbGvda1rdaEa9Z7a9Z7WtZzQtZzOdZzMdZjMdZaQtZSOdZSMdZKMdZCKdZCGNY5Ic7W1s7Oxs7Gtc69xs69tc69rc6tpc6llM6clM6cjM6Ue86EY85zWs5rSs5SKc5KKc5KGMa1tcatrcalvcalnMaUpcZ7c8ZzMcZrUsZrOcZrMcZaQsZSOcZSMcZKMcZCKcZCGMYxIcYxGL3Gxr21tb21rb2lpb2crb2cjL2UnL2UlL2UhL2Ec717Wr17Ur1zWr1rMb1jUr1KMb1KIb1CIb0xGLWlrbWlpbWcnLWEe7V7c7VzY7VzUrVSKbVKMbVCMbVCIbU5KbUxIbUxEK2lta2lpa2clK2UjK2MnK2MlK2Ea617e61za61rY61rMa1jSq1aUq1aSq1SQq1KKa0xEKWlnKWcnKWUnKWUhKWMjKWEa6Vza6VrWqVjMaVaUqVaKaVSMaVCMaU5KaUxIaUxGJyclJyMe5yElJyEhJx7e5x7c5xrOZxaQpxSOZxKQpw5IZSMhJSEjJR7c5Rre5RrY5RrUpRSQpRSKZRCOZRCKZQxKZQxIYyEhIx7hIxza4xzY4xrc4xjUoxaa4xaUoxSSoxKQoxCMYw5GIR7c4Rzc4Rre4RjY4RjWoRaa4RSWoRSUoRSMYRKQoRCOYQ5KYQxIXtra3taY3taSntKOXtCMXtCKXNCMXM5MXMxIWtSUmtKSmtKQmtCOWs5MWs5KWs5IWNCKWMxIVIxKUIQCDkhGAAAACH+AS4ALAAAAAAwACIAAAj/AAEIHEiwoMGDCBMqXMiwoUOHMqxIeEiRoZVp7cpZ29WrF4WKIAd208dGAQEVbiTVChUjZMU9+pYQmPmBZpxgvVw+nDdKwQICNVcIXQEkTgKdDdUJ+/nggVAXK1xI3TEA6UIr2uJ8iBqka1cXXTlkqGoVYRZ7iLyqBSs0iiEtZQVKiDGxBI1u3NR6lUpGDKg8MSgEQCphU7Z22vhg0dILXRCpYLuSCcYJT4wqXASBQaBzU7klHxC127OHD7ZDJFpERqRt0x5OnwQpmZmCLEhrbgg4WIHO1RY+nbQ9WRGEDJlmnXwJ+9FBgXMCIzYMVijBBgYMFxIMqJBMSc0Ht7qh/+Gjpte2rnYsYeNlasWIBgQ6yCewIoPCCp/cyP/wgUGbXVu0QcADZNBDnh98gHMLGXYQUw02w61QU3wdbNWDbQVVIIhMMwFF1DaZiPLBAy7E04kafrjSizaK3LFNNc0AAYRQDsAHHQlJ2IDQJ2zE1+EKDjiAijShkECCC8Qgw4cr7ZgyzC2WaHPNLWWoNeNWPiRAw0QFWQFMhz8C+QQ20yAiVSrY+MGOJCsccsst2GCzoHFxxEGGC+8hgs0MB2kyCpgzrUDCbs1Es41UdtATHFFkWELMOtsoQsYcgvRRQw5RSDgGOjZMR1AvPQIq6KCo9AKOJWDd48owQlHR4DXEKP9iyRrK+DNNBTu4RwIPFeTAGUG7hAomkA84gEg1m6ADljy9PBKGGJY4ig0xlsTBRSn98FOFDUC8pwQOPkgHbCGAzhTkA850s0c7j6Hjix9+gBIrMXLeAccWXUCyiRBcBEECdEJ98KtAqtBCYQc/OvDENnl4gYpUxISCIjjzylkGGV9okYUVNogRhAOBuuAEhjG08wOgDYzAgA5bCjIoCe5uwUk80RKTTSppPREGGGCIISOQ9AXBg6cC6WIywvCpoMHAocRBwhP4bHLFLujYkV42xNxBRhAyGrc113EgYtRBerDDDHMoDCyQEL5sE083EkgwQyBhxGFHMM206DUixGxmE0wssbQjCQ4JCaFKFwgQTVAVVhQUwAVPIFJKrHfYYRwi6OCDzzuIJIFhXAD0EccPsYRiSyqKSDpFcWSMIcZRoBMkQyA2BGZDIKSYcggih8TRRg4VxM5QABVYYLxgwiev/PLMCxQQADs=",
    "find": "R0lGODlhMAAiAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OSkpKRgYGAAAAAAAAAAAAAAAAAAAACH+AS4ALAAAAAAwACIAAAX/ICCOZGmeaKquY2AGLiuvMCAUBuHWc48Kh0iFInEYCb4kSQCxPBiMxkMigRQEgJiSFVBYHNGG0RiZOHjblWAiiY4fkDhEYoBp06dAWfyAQyKAgAwDaHgnB0RwgYASgQ0IhDuGJDAIFhMRVFSLEX8QCJJ4AQM5AgQHTZqqjBAOCQQEkWkCDRMUFQsICQ4Vm5maEwwHOAsPDTpKMAsUDlO4CssTcb+2DAp8YGCyNFoCEsZwFQ3QDRTTVBRS0g1QbgsCd5QAAwgIBwYFAwStzQ8UEdCKVchky0yVBw7YuXkAKt4IAg74vXHVagqFBRgXSCAyYWAVCH0SNhDTitCJfSL5/4RbAPKPhQYYjVCYYAvCP0BxEDaD8CheAAHNwqh8MMGPSwgLeJWhwHSjqkYI+xg4MMCEgQjtRvZ7UAYCpghMF7CxONOWJkYR+rCpY4JlVpVxKDwYWEactKW9mhYRtqCTgwgWEMArERSK1j5q//6T8KXonFsShpiJkAECgQYVjykooCVA0JGHEWNiYCHThTFeb3UkoiCCBgwGEKQ1kuAJlhFwhA71h5SukwUM5qqeCSGBgicEWkfNiWSERtBad4JNIBaQBaQah1ToyGZBAnsIuIJs1qnqiAIVjIE2gnAB1T5x0icgzXT79ipgMOOEH6HBbREBMJCeGEY08IoLAkzB1YYFwjxwSUGSNULQJnNUwRYlCcyEkALIxECAP9cNMMABYpRhy3ZsSLDaR70oUAiABGCkAxowCGCAAfDYIQACXoElGRsdXWDBdg2Y90IWktDYGYAB9PWHP0PMdFZaF07SQgAFNDAMAQg0QA1UC8xoZQl22JGFPgWkOUCOL1pZQyhjxinnnCWEAAA7",
    "REPL": "R0lGODlhMAAjAPcAMf/////3//+lOf+UKf+MEPf///f39/f35/fv7/ecQvecOfecKfeUIfeUGPeUEPeUCPeMAO/37+/v9+/v3u/n3u/n1u+9jO+9c++1hO+ta++tY++tWu+tUu+tSu+lUu+lQu+lMe+UMe+UKe+UGO+UEO+UAO+MCOfv5+fvxufn7+fn5+fnzue9lOe9c+e1jOe1e+e1c+e1a+etWuetUuelQuecOeeUUueUCN7e597e3t7e1t7ezt7evd7Wzt7Oxt7Ovd7Otd7Opd7OnN7Gtd7Gpd69lN61hN6ta96lStbextberdbW3tbWztbWxtbOvdbOrda1hNalUtaECM7W1s7Ozs7Oxs7Otc7Gxs7Gvc69tc69rc69pc61jM6lc8bWlMbOvcbGxsbGpca9tca9pca1nMaMAL3OhL3Gtb21vb21tb2tpb2tnL2tlLW9tbW9pbW9e7W1pbWtjLWcKa21nK2tra2tnK2tlK2lpa2llK2ljK2le6WlnKWljKWUe6WUc6WUY5y1QpyclJycjJychJyUc5yMY5StY5SUe5SMhJSMe5SMc5SMWpSEa5SESoyUe4yMhIyEY4SlKYScWoSMe4SEe4SEa4R7c4R7Y3uMY3uEe3t7e3t7c3tza3tzY3trKXtjIXOcAHOUMXOEY3Nzc3NzWnNrSmulCGuUMWuMGGtzWmtrY2taMWtaGGOUOWOMAGNzUmNjWmNjSmNaUmNaQmNaOWNaIWNSCFqcAFpjUlpSMVpSIVpSEFpKKVKMAFJSUlJSSlJSMVJKMVJKGFJKAFI5CEqUAEqEAEpzQkpKIUpCQkpCGEpCAEo5EEoxAEJjOUJCOUJCAEI5IUIxADl7ADlaITlCOTkxMTkxKTkxEDkhADFzADFrGDE5OTExADEpEClrCCkxKSkpKSkpISkpACkhCCkhACkYACFzACFrACEhCCEYGBhjEBhjABghABgYCBgYABgQEBgQABAQABAIAAhjAAhSAAhKAAgIEAgICABaAABCAAAhAAAQAAAIAAAAAAAAACH+AS4ALAAAAAAwACMAAAj/AAEIHEiwoMGDCBMqXMiwocOHAA4cgEixIIIJO3JMmAjADIqKFU/8MHIkg5EgYXx4iaTkI0iHE6wE2TCggYILQayEAgXIy8uGCKz8sDCAQAMRG3iEcXULlJkJPwli3OFjh9UdYYLE6NBhA04UXHoVA2XoTZgfPKBWlOBDphAWOdfMcfMDLloeO3hIMjbWVCQ5Fn6E2UFxgpsgFjYIEBADrZU6luqEEfqjTqpt54z1uuWqTIcgWAk7PECGzIUQDRosDmxlUrVJkwQJkqVuX71v06YZcyUlROAdbnLAJKPFyAYFAhoMwFlnEh0rWkpz8raPHm7dqKKc/KFFkBUrVn1M/ziBcEIeLUEQI8/AYk0i9Be4sqjsrN66c9/OnbobhpR3HkIUoZ0WVnBE0AGLFKKFD0HAFUQe77HQgQI1hRBDEHMcY0899bBzihZuCPILJD8EccEGGzwAQhFaUHHQH82sUkgeNHISDBk8WCCCcsqFUEQWmOyzjz3sUGNNOO5Y48YOEgowAAQhnBScQV00k82V47jzjy9CXZBcjziFoco//4CDiSOyhPMPLkJZkEBqJmRQxA9uZGEQD8Ncmc044/zzDF2IZQBCCDYE8QMZz/iiCSx0neHGI7BIhhhNn+1gxRpokEcQAp7seWU7/PwTyxqG/iCEEVzQmUombnDRxRExzP9nBR2PCKLFD3UJwcMPa/SRqUGNWJmNOVn+M44ukMRB4KGcWDNLVhuUMEIJAlzwA3DJBHMJIXm4sQYhqyxCRQQGLSIsn1qac2UzysQSyzX/hLMGD0F0IMCODYAQBA9W/PKPOcRiw0wzwxTiokF9dLMnuv/Mo+fCZF7jBr0xbDDCACWEYKgb1vzjDp/jZNOMLX0IZxAKq2TZTjtaOjwOsXyG+s8sZJTIQsUdIGHoJPf8w487QI/TDSt5mGwQFZxc406o8HiDJchk/ltLHpSlJwSvz5DpTjvmuGNOM57koelBOaAhiCaaPBLL0wwbm003peRBnBZqJMJL1ECz/HXYYx/NdAIOOVCxQyLorswymU93o0wuwfAiTDNR/xz0MLXU0XdCE+UwSTRZAq2lsSATu+4wkGvt+TjNzPLrQyegAUku2Hij5cd8LhxyM8QIg4w18HgcdC6BTBFSDmfQqsovttveDcG7lFLHI75cE841sARCxeWsnxC4G9HADPK6ywzDCRqBo0EHHWhMgT1IJzziNci1N7PMKnSYfML96/90AiJKey/0KtbLX1QK0rrNnQ541xugQ7SHhkXBghN0SKACWRc4KlAhBwKcIOYymJCAAAA7",
    "repl": "R0lGODlhMAAjAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OTExMSkpKSEhIRgYGBAQEAgICAAAACH+AS4ALAAAAAAwACMAAAX/ICCOZGmeaKqubOu+gCDANBkIQ1EMQhAghFptYEAkEgjEwXBo7ISvweGgWCwUysPjwTgEoCafTySYIhYMxgLBjEQgCULvCw0QdAZdoVhUIJUFChISEAxYeQM1N1OMTAp+UwZ5eA4TEhFbDWYFdC4ECVMJjwl5BwsQa0umEhUVlhESDgqlBp0rAn5nVpBMDxeZDRQbHBgWFBSWDgtLBnFjKwRYCI9VqQsPs0YKEcMXFq0UEalFDWx4BAO2IwPjppAKDkrTWKYUGd7fEJJFEZpM00cOzCgh4EE8SaoWxKNixQooBRMyZMBwAYIRBhUgLDGS4MoBJeoANMhAgQsaCRZm/5lqaCUJhA4cNHjDoKEDBlJUHqkBlYBTiQUZNGjYMMxDhY3VWk6R4MEDBoMUak5AqoYBqANIBo4wcGGDUKIeLlzVZmWJggsVIkwAZaQSA3kdZzlKkIiEAAlDvW5oOkEBs488JTw44oeUIwdvVTFTUK7uiAAPgubt8GFDhQepqETAQCFU1UMGzlqAgFhUsAcCS0AO6lUDhw8xNRSbENGDhgWSHjWUe6ACbKITizmopZoBa6KvOwj9uuHDhwxyj3xekgDDhw5EvWKo0IB4iQLCOCC/njc7ZQ8UeGvza+ABZZgcxJNc4FO1gc0cOsCUrHevc8tdIMTIAhc4F198G2Qwwd8CBIQUAwEINABBBJUwR9R5wElgVRLwWODBBx4cGB8GEzDQIAo33CGJA8gh+JoH/clUgQU0YvDhdfmJdwEFC6Sjgg8yEPAABsPkh2F22cl2AQbn6QdTghTQ5eAJAQyQAAQV0MSBB9gRVZ4GE1mw5JZOAmiAVi1UWcAZDrDyZXYTeaOhA/bIVuIBPtKQ4h7ViYekUPdcEAEbzTzCRp5CADmAAwj+ORGPBcgwAAHo9ABGCYtm0ChwFHShlRiXhmHlkAcCiOeUodqQw5W0oXLAiamy4MOkjOyAaqxUymApDCEAADs=",
}
colors = ["#FF7B39", "#80F121"]
emphColors = ["#DAFC33", "#F42548"]
fieldParams = {
    "height": 3,
    "width": 70,
    "font": ("monaco", 14),
    "highlightthickness": 0,
    "borderwidth": 0,
    "background": "white",
}
textParams = {
    "bg": "#F7E0D4",
    "fg": "#2321F1",
    "highlightthickness": 0,
    "width": 1,
    "height": 10,
    "font": ("verdana", 16),
    "wrap": "word",
}


class Zone:
    def __init__(self, image, initialField, initialText):
        frm = Frame(root)
        frm.config(background="white")
        self.image = PhotoImage(format="gif", data=images[image.upper()])
        self.imageDimmed = PhotoImage(format="gif", data=images[image])
        self.img = Label(frm)
        self.img.config(borderwidth=0)
        self.img.pack(side="left")
        self.fld = Text(frm, **fieldParams)
        self.initScrollText(frm, self.fld, initialField)
        frm = Frame(root)
        self.txt = Text(frm, **textParams)
        self.initScrollText(frm, self.txt, initialText)
        for i in range(2):
            self.txt.tag_config(colors[i], background=colors[i])
            self.txt.tag_config("emph" + colors[i], foreground=emphColors[i])

    def initScrollText(self, frm, txt, contents):
        scl = Scrollbar(frm)
        scl.config(command=txt.yview)
        scl.pack(side="right", fill="y")
        txt.pack(side="left", expand=True, fill="x")
        txt.config(yscrollcommand=scl.set)
        txt.insert("1.0", contents)
        frm.pack(fill="x")
        Frame(height=2, bd=1, relief="ridge").pack(fill="x")

    def refresh(self):
        self.colorCycle = itertools.cycle(colors)
        try:
            self.substitute()
            self.img.config(image=self.image)
        except re.error:
            self.img.config(image=self.imageDimmed)


class FindZone(Zone):
    def addTags(self, m):
        color = next(self.colorCycle)
        self.txt.tag_add(color, "1.0+%sc" % m.start(), "1.0+%sc" % m.end())
        try:
            self.txt.tag_add(
                "emph" + color, "1.0+%sc" % m.start("emph"), "1.0+%sc" % m.end("emph")
            )
        except:
            pass

    def substitute(self, *args):
        for color in colors:
            self.txt.tag_remove(color, "1.0", "end")
            self.txt.tag_remove("emph" + color, "1.0", "end")
        self.rex = re.compile("")  # default value in case of malformed regexp
        self.rex = re.compile(self.fld.get("1.0", "end")[:-1], re.MULTILINE)
        try:
            re.compile("(?P<emph>%s)" % self.fld.get(SEL_FIRST, SEL_LAST))
            self.rexSel = re.compile(
                "%s(?P<emph>%s)%s"
                % (
                    self.fld.get("1.0", SEL_FIRST),
                    self.fld.get(SEL_FIRST, SEL_LAST),
                    self.fld.get(SEL_LAST, "end")[:-1],
                ),
                re.MULTILINE,
            )
        except:
            self.rexSel = self.rex
        self.rexSel.sub(self.addTags, self.txt.get("1.0", "end"))


class ReplaceZone(Zone):
    def addTags(self, m):
        s = sz.rex.sub(self.repl, m.group())
        self.txt.delete(
            "1.0+%sc" % (m.start() + self.diff), "1.0+%sc" % (m.end() + self.diff)
        )
        self.txt.insert("1.0+%sc" % (m.start() + self.diff), s, next(self.colorCycle))
        self.diff += len(s) - (m.end() - m.start())

    def substitute(self):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", sz.txt.get("1.0", "end")[:-1])
        self.diff = 0
        self.repl = rex0.sub(r"\\g<\1>", self.fld.get("1.0", "end")[:-1])
        sz.rex.sub(self.addTags, sz.txt.get("1.0", "end")[:-1])


def launchRefresh(_):
    sz.fld.after_idle(sz.refresh)
    rz.fld.after_idle(rz.refresh)


def app():
    global root, sz, rz, rex0
    root = Tk()
    root.resizable(height=False, width=True)
    root.title(windowTitle)
    root.minsize(width=250, height=0)
    sz = FindZone("find", initialFind, initialText)
    sz.fld.bind("<Button-1>", launchRefresh)
    sz.fld.bind("<ButtonRelease-1>", launchRefresh)
    sz.fld.bind("<B1-Motion>", launchRefresh)
    sz.rexSel = re.compile("")
    rz = ReplaceZone("repl", initialRepl, "")
    rex0 = re.compile(r"(?<!\\)\\([0-9]+)")
    root.bind_all("<Key>", launchRefresh)
    launchRefresh(None)
    root.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\nemo_app.py ===
# Finding (and Replacing) Nemo, Version 1.1, Aristide Grange 2006/06/06
# https://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496783

"""
Finding (and Replacing) Nemo

Instant Regular Expressions
Created by Aristide Grange
"""
import itertools
import re
from tkinter import SEL_FIRST, SEL_LAST, Frame, Label, PhotoImage, Scrollbar, Text, Tk

windowTitle = "Finding (and Replacing) Nemo"
initialFind = r"n(.*?)e(.*?)m(.*?)o"
initialRepl = r"M\1A\2K\3I"
initialText = """\
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
"""
images = {
    "FIND": "R0lGODlhMAAiAPcAMf/////37//35//n1v97Off///f/9/f37/fexvfOvfeEQvd7QvdrQvdrKfdaKfdSMfdSIe/v9+/v7+/v5+/n3u/e1u/Wxu/Gre+1lO+tnO+thO+Ua+97Y+97Oe97Me9rOe9rMe9jOe9jMe9jIe9aMefe5+fe3ufezuece+eEWudzQudaIedSIedKMedKIedCKedCId7e1t7Wzt7Oxt7Gvd69vd69rd61pd6ljN6UjN6Ue96EY95zY95rUt5rQt5jMd5SId5KIdbn59be3tbGztbGvda1rdaEa9Z7a9Z7WtZzQtZzOdZzMdZjMdZaQtZSOdZSMdZKMdZCKdZCGNY5Ic7W1s7Oxs7Gtc69xs69tc69rc6tpc6llM6clM6cjM6Ue86EY85zWs5rSs5SKc5KKc5KGMa1tcatrcalvcalnMaUpcZ7c8ZzMcZrUsZrOcZrMcZaQsZSOcZSMcZKMcZCKcZCGMYxIcYxGL3Gxr21tb21rb2lpb2crb2cjL2UnL2UlL2UhL2Ec717Wr17Ur1zWr1rMb1jUr1KMb1KIb1CIb0xGLWlrbWlpbWcnLWEe7V7c7VzY7VzUrVSKbVKMbVCMbVCIbU5KbUxIbUxEK2lta2lpa2clK2UjK2MnK2MlK2Ea617e61za61rY61rMa1jSq1aUq1aSq1SQq1KKa0xEKWlnKWcnKWUnKWUhKWMjKWEa6Vza6VrWqVjMaVaUqVaKaVSMaVCMaU5KaUxIaUxGJyclJyMe5yElJyEhJx7e5x7c5xrOZxaQpxSOZxKQpw5IZSMhJSEjJR7c5Rre5RrY5RrUpRSQpRSKZRCOZRCKZQxKZQxIYyEhIx7hIxza4xzY4xrc4xjUoxaa4xaUoxSSoxKQoxCMYw5GIR7c4Rzc4Rre4RjY4RjWoRaa4RSWoRSUoRSMYRKQoRCOYQ5KYQxIXtra3taY3taSntKOXtCMXtCKXNCMXM5MXMxIWtSUmtKSmtKQmtCOWs5MWs5KWs5IWNCKWMxIVIxKUIQCDkhGAAAACH+AS4ALAAAAAAwACIAAAj/AAEIHEiwoMGDCBMqXMiwoUOHMqxIeEiRoZVp7cpZ29WrF4WKIAd208dGAQEVbiTVChUjZMU9+pYQmPmBZpxgvVw+nDdKwQICNVcIXQEkTgKdDdUJ+/nggVAXK1xI3TEA6UIr2uJ8iBqka1cXXTlkqGoVYRZ7iLyqBSs0iiEtZQVKiDGxBI1u3NR6lUpGDKg8MSgEQCphU7Z22vhg0dILXRCpYLuSCcYJT4wqXASBQaBzU7klHxC127OHD7ZDJFpERqRt0x5OnwQpmZmCLEhrbgg4WIHO1RY+nbQ9WRGEDJlmnXwJ+9FBgXMCIzYMVijBBgYMFxIMqJBMSc0Ht7qh/+Gjpte2rnYsYeNlasWIBgQ6yCewIoPCCp/cyP/wgUGbXVu0QcADZNBDnh98gHMLGXYQUw02w61QU3wdbNWDbQVVIIhMMwFF1DaZiPLBAy7E04kafrjSizaK3LFNNc0AAYRQDsAHHQlJ2IDQJ2zE1+EKDjiAijShkECCC8Qgw4cr7ZgyzC2WaHPNLWWoNeNWPiRAw0QFWQFMhz8C+QQ20yAiVSrY+MGOJCsccsst2GCzoHFxxEGGC+8hgs0MB2kyCpgzrUDCbs1Es41UdtATHFFkWELMOtsoQsYcgvRRQw5RSDgGOjZMR1AvPQIq6KCo9AKOJWDd48owQlHR4DXEKP9iyRrK+DNNBTu4RwIPFeTAGUG7hAomkA84gEg1m6ADljy9PBKGGJY4ig0xlsTBRSn98FOFDUC8pwQOPkgHbCGAzhTkA850s0c7j6Hjix9+gBIrMXLeAccWXUCyiRBcBEECdEJ98KtAqtBCYQc/OvDENnl4gYpUxISCIjjzylkGGV9okYUVNogRhAOBuuAEhjG08wOgDYzAgA5bCjIoCe5uwUk80RKTTSppPREGGGCIISOQ9AXBg6cC6WIywvCpoMHAocRBwhP4bHLFLujYkV42xNxBRhAyGrc113EgYtRBerDDDHMoDCyQEL5sE083EkgwQyBhxGFHMM206DUixGxmE0wssbQjCQ4JCaFKFwgQTVAVVhQUwAVPIFJKrHfYYRwi6OCDzzuIJIFhXAD0EccPsYRiSyqKSDpFcWSMIcZRoBMkQyA2BGZDIKSYcggih8TRRg4VxM5QABVYYLxgwiev/PLMCxQQADs=",
    "find": "R0lGODlhMAAiAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OSkpKRgYGAAAAAAAAAAAAAAAAAAAACH+AS4ALAAAAAAwACIAAAX/ICCOZGmeaKquY2AGLiuvMCAUBuHWc48Kh0iFInEYCb4kSQCxPBiMxkMigRQEgJiSFVBYHNGG0RiZOHjblWAiiY4fkDhEYoBp06dAWfyAQyKAgAwDaHgnB0RwgYASgQ0IhDuGJDAIFhMRVFSLEX8QCJJ4AQM5AgQHTZqqjBAOCQQEkWkCDRMUFQsICQ4Vm5maEwwHOAsPDTpKMAsUDlO4CssTcb+2DAp8YGCyNFoCEsZwFQ3QDRTTVBRS0g1QbgsCd5QAAwgIBwYFAwStzQ8UEdCKVchky0yVBw7YuXkAKt4IAg74vXHVagqFBRgXSCAyYWAVCH0SNhDTitCJfSL5/4RbAPKPhQYYjVCYYAvCP0BxEDaD8CheAAHNwqh8MMGPSwgLeJWhwHSjqkYI+xg4MMCEgQjtRvZ7UAYCpghMF7CxONOWJkYR+rCpY4JlVpVxKDwYWEactKW9mhYRtqCTgwgWEMArERSK1j5q//6T8KXonFsShpiJkAECgQYVjykooCVA0JGHEWNiYCHThTFeb3UkoiCCBgwGEKQ1kuAJlhFwhA71h5SukwUM5qqeCSGBgicEWkfNiWSERtBad4JNIBaQBaQah1ToyGZBAnsIuIJs1qnqiAIVjIE2gnAB1T5x0icgzXT79ipgMOOEH6HBbREBMJCeGEY08IoLAkzB1YYFwjxwSUGSNULQJnNUwRYlCcyEkALIxECAP9cNMMABYpRhy3ZsSLDaR70oUAiABGCkAxowCGCAAfDYIQACXoElGRsdXWDBdg2Y90IWktDYGYAB9PWHP0PMdFZaF07SQgAFNDAMAQg0QA1UC8xoZQl22JGFPgWkOUCOL1pZQyhjxinnnCWEAAA7",
    "REPL": "R0lGODlhMAAjAPcAMf/////3//+lOf+UKf+MEPf///f39/f35/fv7/ecQvecOfecKfeUIfeUGPeUEPeUCPeMAO/37+/v9+/v3u/n3u/n1u+9jO+9c++1hO+ta++tY++tWu+tUu+tSu+lUu+lQu+lMe+UMe+UKe+UGO+UEO+UAO+MCOfv5+fvxufn7+fn5+fnzue9lOe9c+e1jOe1e+e1c+e1a+etWuetUuelQuecOeeUUueUCN7e597e3t7e1t7ezt7evd7Wzt7Oxt7Ovd7Otd7Opd7OnN7Gtd7Gpd69lN61hN6ta96lStbextberdbW3tbWztbWxtbOvdbOrda1hNalUtaECM7W1s7Ozs7Oxs7Otc7Gxs7Gvc69tc69rc69pc61jM6lc8bWlMbOvcbGxsbGpca9tca9pca1nMaMAL3OhL3Gtb21vb21tb2tpb2tnL2tlLW9tbW9pbW9e7W1pbWtjLWcKa21nK2tra2tnK2tlK2lpa2llK2ljK2le6WlnKWljKWUe6WUc6WUY5y1QpyclJycjJychJyUc5yMY5StY5SUe5SMhJSMe5SMc5SMWpSEa5SESoyUe4yMhIyEY4SlKYScWoSMe4SEe4SEa4R7c4R7Y3uMY3uEe3t7e3t7c3tza3tzY3trKXtjIXOcAHOUMXOEY3Nzc3NzWnNrSmulCGuUMWuMGGtzWmtrY2taMWtaGGOUOWOMAGNzUmNjWmNjSmNaUmNaQmNaOWNaIWNSCFqcAFpjUlpSMVpSIVpSEFpKKVKMAFJSUlJSSlJSMVJKMVJKGFJKAFI5CEqUAEqEAEpzQkpKIUpCQkpCGEpCAEo5EEoxAEJjOUJCOUJCAEI5IUIxADl7ADlaITlCOTkxMTkxKTkxEDkhADFzADFrGDE5OTExADEpEClrCCkxKSkpKSkpISkpACkhCCkhACkYACFzACFrACEhCCEYGBhjEBhjABghABgYCBgYABgQEBgQABAQABAIAAhjAAhSAAhKAAgIEAgICABaAABCAAAhAAAQAAAIAAAAAAAAACH+AS4ALAAAAAAwACMAAAj/AAEIHEiwoMGDCBMqXMiwocOHAA4cgEixIIIJO3JMmAjADIqKFU/8MHIkg5EgYXx4iaTkI0iHE6wE2TCggYILQayEAgXIy8uGCKz8sDCAQAMRG3iEcXULlJkJPwli3OFjh9UdYYLE6NBhA04UXHoVA2XoTZgfPKBWlOBDphAWOdfMcfMDLloeO3hIMjbWVCQ5Fn6E2UFxgpsgFjYIEBADrZU6luqEEfqjTqpt54z1uuWqTIcgWAk7PECGzIUQDRosDmxlUrVJkwQJkqVuX71v06YZcyUlROAdbnLAJKPFyAYFAhoMwFlnEh0rWkpz8raPHm7dqKKc/KFFkBUrVn1M/ziBcEIeLUEQI8/AYk0i9Be4sqjsrN66c9/OnbobhpR3HkIUoZ0WVnBE0AGLFKKFD0HAFUQe77HQgQI1hRBDEHMcY0899bBzihZuCPILJD8EccEGGzwAQhFaUHHQH82sUkgeNHISDBk8WCCCcsqFUEQWmOyzjz3sUGNNOO5Y48YOEgowAAQhnBScQV00k82V47jzjy9CXZBcjziFoco//4CDiSOyhPMPLkJZkEBqJmRQxA9uZGEQD8Ncmc044/zzDF2IZQBCCDYE8QMZz/iiCSx0neHGI7BIhhhNn+1gxRpokEcQAp7seWU7/PwTyxqG/iCEEVzQmUombnDRxRExzP9nBR2PCKLFD3UJwcMPa/SRqUGNWJmNOVn+M44ukMRB4KGcWDNLVhuUMEIJAlzwA3DJBHMJIXm4sQYhqyxCRQQGLSIsn1qac2UzysQSyzX/hLMGD0F0IMCODYAQBA9W/PKPOcRiw0wzwxTiokF9dLMnuv/Mo+fCZF7jBr0xbDDCACWEYKgb1vzjDp/jZNOMLX0IZxAKq2TZTjtaOjwOsXyG+s8sZJTIQsUdIGHoJPf8w487QI/TDSt5mGwQFZxc406o8HiDJchk/ltLHpSlJwSvz5DpTjvmuGNOM57koelBOaAhiCaaPBLL0wwbm003peRBnBZqJMJL1ECz/HXYYx/NdAIOOVCxQyLorswymU93o0wuwfAiTDNR/xz0MLXU0XdCE+UwSTRZAq2lsSATu+4wkGvt+TjNzPLrQyegAUku2Hij5cd8LhxyM8QIg4w18HgcdC6BTBFSDmfQqsovttveDcG7lFLHI75cE841sARCxeWsnxC4G9HADPK6ywzDCRqBo0EHHWhMgT1IJzziNci1N7PMKnSYfML96/90AiJKey/0KtbLX1QK0rrNnQ541xugQ7SHhkXBghN0SKACWRc4KlAhBwKcIOYymJCAAAA7",
    "repl": "R0lGODlhMAAjAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OTExMSkpKSEhIRgYGBAQEAgICAAAACH+AS4ALAAAAAAwACMAAAX/ICCOZGmeaKqubOu+gCDANBkIQ1EMQhAghFptYEAkEgjEwXBo7ISvweGgWCwUysPjwTgEoCafTySYIhYMxgLBjEQgCULvCw0QdAZdoVhUIJUFChISEAxYeQM1N1OMTAp+UwZ5eA4TEhFbDWYFdC4ECVMJjwl5BwsQa0umEhUVlhESDgqlBp0rAn5nVpBMDxeZDRQbHBgWFBSWDgtLBnFjKwRYCI9VqQsPs0YKEcMXFq0UEalFDWx4BAO2IwPjppAKDkrTWKYUGd7fEJJFEZpM00cOzCgh4EE8SaoWxKNixQooBRMyZMBwAYIRBhUgLDGS4MoBJeoANMhAgQsaCRZm/5lqaCUJhA4cNHjDoKEDBlJUHqkBlYBTiQUZNGjYMMxDhY3VWk6R4MEDBoMUak5AqoYBqANIBo4wcGGDUKIeLlzVZmWJggsVIkwAZaQSA3kdZzlKkIiEAAlDvW5oOkEBs488JTw44oeUIwdvVTFTUK7uiAAPgubt8GFDhQepqETAQCFU1UMGzlqAgFhUsAcCS0AO6lUDhw8xNRSbENGDhgWSHjWUe6ACbKITizmopZoBa6KvOwj9uuHDhwxyj3xekgDDhw5EvWKo0IB4iQLCOCC/njc7ZQ8UeGvza+ABZZgcxJNc4FO1gc0cOsCUrHevc8tdIMTIAhc4F198G2Qwwd8CBIQUAwEINABBBJUwR9R5wElgVRLwWODBBx4cGB8GEzDQIAo33CGJA8gh+JoH/clUgQU0YvDhdfmJdwEFC6Sjgg8yEPAABsPkh2F22cl2AQbn6QdTghTQ5eAJAQyQAAQV0MSBB9gRVZ4GE1mw5JZOAmiAVi1UWcAZDrDyZXYTeaOhA/bIVuIBPtKQ4h7ViYekUPdcEAEbzTzCRp5CADmAAwj+ORGPBcgwAAHo9ABGCYtm0ChwFHShlRiXhmHlkAcCiOeUodqQw5W0oXLAiamy4MOkjOyAaqxUymApDCEAADs=",
}
colors = ["#FF7B39", "#80F121"]
emphColors = ["#DAFC33", "#F42548"]
fieldParams = {
    "height": 3,
    "width": 70,
    "font": ("monaco", 14),
    "highlightthickness": 0,
    "borderwidth": 0,
    "background": "white",
}
textParams = {
    "bg": "#F7E0D4",
    "fg": "#2321F1",
    "highlightthickness": 0,
    "width": 1,
    "height": 10,
    "font": ("verdana", 16),
    "wrap": "word",
}


class Zone:
    def __init__(self, image, initialField, initialText):
        frm = Frame(root)
        frm.config(background="white")
        self.image = PhotoImage(format="gif", data=images[image.upper()])
        self.imageDimmed = PhotoImage(format="gif", data=images[image])
        self.img = Label(frm)
        self.img.config(borderwidth=0)
        self.img.pack(side="left")
        self.fld = Text(frm, **fieldParams)
        self.initScrollText(frm, self.fld, initialField)
        frm = Frame(root)
        self.txt = Text(frm, **textParams)
        self.initScrollText(frm, self.txt, initialText)
        for i in range(2):
            self.txt.tag_config(colors[i], background=colors[i])
            self.txt.tag_config("emph" + colors[i], foreground=emphColors[i])

    def initScrollText(self, frm, txt, contents):
        scl = Scrollbar(frm)
        scl.config(command=txt.yview)
        scl.pack(side="right", fill="y")
        txt.pack(side="left", expand=True, fill="x")
        txt.config(yscrollcommand=scl.set)
        txt.insert("1.0", contents)
        frm.pack(fill="x")
        Frame(height=2, bd=1, relief="ridge").pack(fill="x")

    def refresh(self):
        self.colorCycle = itertools.cycle(colors)
        try:
            self.substitute()
            self.img.config(image=self.image)
        except re.error:
            self.img.config(image=self.imageDimmed)


class FindZone(Zone):
    def addTags(self, m):
        color = next(self.colorCycle)
        self.txt.tag_add(color, "1.0+%sc" % m.start(), "1.0+%sc" % m.end())
        try:
            self.txt.tag_add(
                "emph" + color, "1.0+%sc" % m.start("emph"), "1.0+%sc" % m.end("emph")
            )
        except:
            pass

    def substitute(self, *args):
        for color in colors:
            self.txt.tag_remove(color, "1.0", "end")
            self.txt.tag_remove("emph" + color, "1.0", "end")
        self.rex = re.compile("")  # default value in case of malformed regexp
        self.rex = re.compile(self.fld.get("1.0", "end")[:-1], re.MULTILINE)
        try:
            re.compile("(?P<emph>%s)" % self.fld.get(SEL_FIRST, SEL_LAST))
            self.rexSel = re.compile(
                "%s(?P<emph>%s)%s"
                % (
                    self.fld.get("1.0", SEL_FIRST),
                    self.fld.get(SEL_FIRST, SEL_LAST),
                    self.fld.get(SEL_LAST, "end")[:-1],
                ),
                re.MULTILINE,
            )
        except:
            self.rexSel = self.rex
        self.rexSel.sub(self.addTags, self.txt.get("1.0", "end"))


class ReplaceZone(Zone):
    def addTags(self, m):
        s = sz.rex.sub(self.repl, m.group())
        self.txt.delete(
            "1.0+%sc" % (m.start() + self.diff), "1.0+%sc" % (m.end() + self.diff)
        )
        self.txt.insert("1.0+%sc" % (m.start() + self.diff), s, next(self.colorCycle))
        self.diff += len(s) - (m.end() - m.start())

    def substitute(self):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", sz.txt.get("1.0", "end")[:-1])
        self.diff = 0
        self.repl = rex0.sub(r"\\g<\1>", self.fld.get("1.0", "end")[:-1])
        sz.rex.sub(self.addTags, sz.txt.get("1.0", "end")[:-1])


def launchRefresh(_):
    sz.fld.after_idle(sz.refresh)
    rz.fld.after_idle(rz.refresh)


def app():
    global root, sz, rz, rex0
    root = Tk()
    root.resizable(height=False, width=True)
    root.title(windowTitle)
    root.minsize(width=250, height=0)
    sz = FindZone("find", initialFind, initialText)
    sz.fld.bind("<Button-1>", launchRefresh)
    sz.fld.bind("<ButtonRelease-1>", launchRefresh)
    sz.fld.bind("<B1-Motion>", launchRefresh)
    sz.rexSel = re.compile("")
    rz = ReplaceZone("repl", initialRepl, "")
    rex0 = re.compile(r"(?<!\\)\\([0-9]+)")
    root.bind_all("<Key>", launchRefresh)
    launchRefresh(None)
    root.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\nemo_app.py ===
# Finding (and Replacing) Nemo, Version 1.1, Aristide Grange 2006/06/06
# https://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496783

"""
Finding (and Replacing) Nemo

Instant Regular Expressions
Created by Aristide Grange
"""
import itertools
import re
from tkinter import SEL_FIRST, SEL_LAST, Frame, Label, PhotoImage, Scrollbar, Text, Tk

windowTitle = "Finding (and Replacing) Nemo"
initialFind = r"n(.*?)e(.*?)m(.*?)o"
initialRepl = r"M\1A\2K\3I"
initialText = """\
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
"""
images = {
    "FIND": "R0lGODlhMAAiAPcAMf/////37//35//n1v97Off///f/9/f37/fexvfOvfeEQvd7QvdrQvdrKfdaKfdSMfdSIe/v9+/v7+/v5+/n3u/e1u/Wxu/Gre+1lO+tnO+thO+Ua+97Y+97Oe97Me9rOe9rMe9jOe9jMe9jIe9aMefe5+fe3ufezuece+eEWudzQudaIedSIedKMedKIedCKedCId7e1t7Wzt7Oxt7Gvd69vd69rd61pd6ljN6UjN6Ue96EY95zY95rUt5rQt5jMd5SId5KIdbn59be3tbGztbGvda1rdaEa9Z7a9Z7WtZzQtZzOdZzMdZjMdZaQtZSOdZSMdZKMdZCKdZCGNY5Ic7W1s7Oxs7Gtc69xs69tc69rc6tpc6llM6clM6cjM6Ue86EY85zWs5rSs5SKc5KKc5KGMa1tcatrcalvcalnMaUpcZ7c8ZzMcZrUsZrOcZrMcZaQsZSOcZSMcZKMcZCKcZCGMYxIcYxGL3Gxr21tb21rb2lpb2crb2cjL2UnL2UlL2UhL2Ec717Wr17Ur1zWr1rMb1jUr1KMb1KIb1CIb0xGLWlrbWlpbWcnLWEe7V7c7VzY7VzUrVSKbVKMbVCMbVCIbU5KbUxIbUxEK2lta2lpa2clK2UjK2MnK2MlK2Ea617e61za61rY61rMa1jSq1aUq1aSq1SQq1KKa0xEKWlnKWcnKWUnKWUhKWMjKWEa6Vza6VrWqVjMaVaUqVaKaVSMaVCMaU5KaUxIaUxGJyclJyMe5yElJyEhJx7e5x7c5xrOZxaQpxSOZxKQpw5IZSMhJSEjJR7c5Rre5RrY5RrUpRSQpRSKZRCOZRCKZQxKZQxIYyEhIx7hIxza4xzY4xrc4xjUoxaa4xaUoxSSoxKQoxCMYw5GIR7c4Rzc4Rre4RjY4RjWoRaa4RSWoRSUoRSMYRKQoRCOYQ5KYQxIXtra3taY3taSntKOXtCMXtCKXNCMXM5MXMxIWtSUmtKSmtKQmtCOWs5MWs5KWs5IWNCKWMxIVIxKUIQCDkhGAAAACH+AS4ALAAAAAAwACIAAAj/AAEIHEiwoMGDCBMqXMiwoUOHMqxIeEiRoZVp7cpZ29WrF4WKIAd208dGAQEVbiTVChUjZMU9+pYQmPmBZpxgvVw+nDdKwQICNVcIXQEkTgKdDdUJ+/nggVAXK1xI3TEA6UIr2uJ8iBqka1cXXTlkqGoVYRZ7iLyqBSs0iiEtZQVKiDGxBI1u3NR6lUpGDKg8MSgEQCphU7Z22vhg0dILXRCpYLuSCcYJT4wqXASBQaBzU7klHxC127OHD7ZDJFpERqRt0x5OnwQpmZmCLEhrbgg4WIHO1RY+nbQ9WRGEDJlmnXwJ+9FBgXMCIzYMVijBBgYMFxIMqJBMSc0Ht7qh/+Gjpte2rnYsYeNlasWIBgQ6yCewIoPCCp/cyP/wgUGbXVu0QcADZNBDnh98gHMLGXYQUw02w61QU3wdbNWDbQVVIIhMMwFF1DaZiPLBAy7E04kafrjSizaK3LFNNc0AAYRQDsAHHQlJ2IDQJ2zE1+EKDjiAijShkECCC8Qgw4cr7ZgyzC2WaHPNLWWoNeNWPiRAw0QFWQFMhz8C+QQ20yAiVSrY+MGOJCsccsst2GCzoHFxxEGGC+8hgs0MB2kyCpgzrUDCbs1Es41UdtATHFFkWELMOtsoQsYcgvRRQw5RSDgGOjZMR1AvPQIq6KCo9AKOJWDd48owQlHR4DXEKP9iyRrK+DNNBTu4RwIPFeTAGUG7hAomkA84gEg1m6ADljy9PBKGGJY4ig0xlsTBRSn98FOFDUC8pwQOPkgHbCGAzhTkA850s0c7j6Hjix9+gBIrMXLeAccWXUCyiRBcBEECdEJ98KtAqtBCYQc/OvDENnl4gYpUxISCIjjzylkGGV9okYUVNogRhAOBuuAEhjG08wOgDYzAgA5bCjIoCe5uwUk80RKTTSppPREGGGCIISOQ9AXBg6cC6WIywvCpoMHAocRBwhP4bHLFLujYkV42xNxBRhAyGrc113EgYtRBerDDDHMoDCyQEL5sE083EkgwQyBhxGFHMM206DUixGxmE0wssbQjCQ4JCaFKFwgQTVAVVhQUwAVPIFJKrHfYYRwi6OCDzzuIJIFhXAD0EccPsYRiSyqKSDpFcWSMIcZRoBMkQyA2BGZDIKSYcggih8TRRg4VxM5QABVYYLxgwiev/PLMCxQQADs=",
    "find": "R0lGODlhMAAiAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OSkpKRgYGAAAAAAAAAAAAAAAAAAAACH+AS4ALAAAAAAwACIAAAX/ICCOZGmeaKquY2AGLiuvMCAUBuHWc48Kh0iFInEYCb4kSQCxPBiMxkMigRQEgJiSFVBYHNGG0RiZOHjblWAiiY4fkDhEYoBp06dAWfyAQyKAgAwDaHgnB0RwgYASgQ0IhDuGJDAIFhMRVFSLEX8QCJJ4AQM5AgQHTZqqjBAOCQQEkWkCDRMUFQsICQ4Vm5maEwwHOAsPDTpKMAsUDlO4CssTcb+2DAp8YGCyNFoCEsZwFQ3QDRTTVBRS0g1QbgsCd5QAAwgIBwYFAwStzQ8UEdCKVchky0yVBw7YuXkAKt4IAg74vXHVagqFBRgXSCAyYWAVCH0SNhDTitCJfSL5/4RbAPKPhQYYjVCYYAvCP0BxEDaD8CheAAHNwqh8MMGPSwgLeJWhwHSjqkYI+xg4MMCEgQjtRvZ7UAYCpghMF7CxONOWJkYR+rCpY4JlVpVxKDwYWEactKW9mhYRtqCTgwgWEMArERSK1j5q//6T8KXonFsShpiJkAECgQYVjykooCVA0JGHEWNiYCHThTFeb3UkoiCCBgwGEKQ1kuAJlhFwhA71h5SukwUM5qqeCSGBgicEWkfNiWSERtBad4JNIBaQBaQah1ToyGZBAnsIuIJs1qnqiAIVjIE2gnAB1T5x0icgzXT79ipgMOOEH6HBbREBMJCeGEY08IoLAkzB1YYFwjxwSUGSNULQJnNUwRYlCcyEkALIxECAP9cNMMABYpRhy3ZsSLDaR70oUAiABGCkAxowCGCAAfDYIQACXoElGRsdXWDBdg2Y90IWktDYGYAB9PWHP0PMdFZaF07SQgAFNDAMAQg0QA1UC8xoZQl22JGFPgWkOUCOL1pZQyhjxinnnCWEAAA7",
    "REPL": "R0lGODlhMAAjAPcAMf/////3//+lOf+UKf+MEPf///f39/f35/fv7/ecQvecOfecKfeUIfeUGPeUEPeUCPeMAO/37+/v9+/v3u/n3u/n1u+9jO+9c++1hO+ta++tY++tWu+tUu+tSu+lUu+lQu+lMe+UMe+UKe+UGO+UEO+UAO+MCOfv5+fvxufn7+fn5+fnzue9lOe9c+e1jOe1e+e1c+e1a+etWuetUuelQuecOeeUUueUCN7e597e3t7e1t7ezt7evd7Wzt7Oxt7Ovd7Otd7Opd7OnN7Gtd7Gpd69lN61hN6ta96lStbextberdbW3tbWztbWxtbOvdbOrda1hNalUtaECM7W1s7Ozs7Oxs7Otc7Gxs7Gvc69tc69rc69pc61jM6lc8bWlMbOvcbGxsbGpca9tca9pca1nMaMAL3OhL3Gtb21vb21tb2tpb2tnL2tlLW9tbW9pbW9e7W1pbWtjLWcKa21nK2tra2tnK2tlK2lpa2llK2ljK2le6WlnKWljKWUe6WUc6WUY5y1QpyclJycjJychJyUc5yMY5StY5SUe5SMhJSMe5SMc5SMWpSEa5SESoyUe4yMhIyEY4SlKYScWoSMe4SEe4SEa4R7c4R7Y3uMY3uEe3t7e3t7c3tza3tzY3trKXtjIXOcAHOUMXOEY3Nzc3NzWnNrSmulCGuUMWuMGGtzWmtrY2taMWtaGGOUOWOMAGNzUmNjWmNjSmNaUmNaQmNaOWNaIWNSCFqcAFpjUlpSMVpSIVpSEFpKKVKMAFJSUlJSSlJSMVJKMVJKGFJKAFI5CEqUAEqEAEpzQkpKIUpCQkpCGEpCAEo5EEoxAEJjOUJCOUJCAEI5IUIxADl7ADlaITlCOTkxMTkxKTkxEDkhADFzADFrGDE5OTExADEpEClrCCkxKSkpKSkpISkpACkhCCkhACkYACFzACFrACEhCCEYGBhjEBhjABghABgYCBgYABgQEBgQABAQABAIAAhjAAhSAAhKAAgIEAgICABaAABCAAAhAAAQAAAIAAAAAAAAACH+AS4ALAAAAAAwACMAAAj/AAEIHEiwoMGDCBMqXMiwocOHAA4cgEixIIIJO3JMmAjADIqKFU/8MHIkg5EgYXx4iaTkI0iHE6wE2TCggYILQayEAgXIy8uGCKz8sDCAQAMRG3iEcXULlJkJPwli3OFjh9UdYYLE6NBhA04UXHoVA2XoTZgfPKBWlOBDphAWOdfMcfMDLloeO3hIMjbWVCQ5Fn6E2UFxgpsgFjYIEBADrZU6luqEEfqjTqpt54z1uuWqTIcgWAk7PECGzIUQDRosDmxlUrVJkwQJkqVuX71v06YZcyUlROAdbnLAJKPFyAYFAhoMwFlnEh0rWkpz8raPHm7dqKKc/KFFkBUrVn1M/ziBcEIeLUEQI8/AYk0i9Be4sqjsrN66c9/OnbobhpR3HkIUoZ0WVnBE0AGLFKKFD0HAFUQe77HQgQI1hRBDEHMcY0899bBzihZuCPILJD8EccEGGzwAQhFaUHHQH82sUkgeNHISDBk8WCCCcsqFUEQWmOyzjz3sUGNNOO5Y48YOEgowAAQhnBScQV00k82V47jzjy9CXZBcjziFoco//4CDiSOyhPMPLkJZkEBqJmRQxA9uZGEQD8Ncmc044/zzDF2IZQBCCDYE8QMZz/iiCSx0neHGI7BIhhhNn+1gxRpokEcQAp7seWU7/PwTyxqG/iCEEVzQmUombnDRxRExzP9nBR2PCKLFD3UJwcMPa/SRqUGNWJmNOVn+M44ukMRB4KGcWDNLVhuUMEIJAlzwA3DJBHMJIXm4sQYhqyxCRQQGLSIsn1qac2UzysQSyzX/hLMGD0F0IMCODYAQBA9W/PKPOcRiw0wzwxTiokF9dLMnuv/Mo+fCZF7jBr0xbDDCACWEYKgb1vzjDp/jZNOMLX0IZxAKq2TZTjtaOjwOsXyG+s8sZJTIQsUdIGHoJPf8w487QI/TDSt5mGwQFZxc406o8HiDJchk/ltLHpSlJwSvz5DpTjvmuGNOM57koelBOaAhiCaaPBLL0wwbm003peRBnBZqJMJL1ECz/HXYYx/NdAIOOVCxQyLorswymU93o0wuwfAiTDNR/xz0MLXU0XdCE+UwSTRZAq2lsSATu+4wkGvt+TjNzPLrQyegAUku2Hij5cd8LhxyM8QIg4w18HgcdC6BTBFSDmfQqsovttveDcG7lFLHI75cE841sARCxeWsnxC4G9HADPK6ywzDCRqBo0EHHWhMgT1IJzziNci1N7PMKnSYfML96/90AiJKey/0KtbLX1QK0rrNnQ541xugQ7SHhkXBghN0SKACWRc4KlAhBwKcIOYymJCAAAA7",
    "repl": "R0lGODlhMAAjAPQAMf////f39+/v7+fn597e3tbW1s7OzsbGxr29vbW1ta2traWlpZycnJSUlIyMjISEhHt7e3Nzc2tra2NjY1paWlJSUkpKSkJCQjk5OTExMSkpKSEhIRgYGBAQEAgICAAAACH+AS4ALAAAAAAwACMAAAX/ICCOZGmeaKqubOu+gCDANBkIQ1EMQhAghFptYEAkEgjEwXBo7ISvweGgWCwUysPjwTgEoCafTySYIhYMxgLBjEQgCULvCw0QdAZdoVhUIJUFChISEAxYeQM1N1OMTAp+UwZ5eA4TEhFbDWYFdC4ECVMJjwl5BwsQa0umEhUVlhESDgqlBp0rAn5nVpBMDxeZDRQbHBgWFBSWDgtLBnFjKwRYCI9VqQsPs0YKEcMXFq0UEalFDWx4BAO2IwPjppAKDkrTWKYUGd7fEJJFEZpM00cOzCgh4EE8SaoWxKNixQooBRMyZMBwAYIRBhUgLDGS4MoBJeoANMhAgQsaCRZm/5lqaCUJhA4cNHjDoKEDBlJUHqkBlYBTiQUZNGjYMMxDhY3VWk6R4MEDBoMUak5AqoYBqANIBo4wcGGDUKIeLlzVZmWJggsVIkwAZaQSA3kdZzlKkIiEAAlDvW5oOkEBs488JTw44oeUIwdvVTFTUK7uiAAPgubt8GFDhQepqETAQCFU1UMGzlqAgFhUsAcCS0AO6lUDhw8xNRSbENGDhgWSHjWUe6ACbKITizmopZoBa6KvOwj9uuHDhwxyj3xekgDDhw5EvWKo0IB4iQLCOCC/njc7ZQ8UeGvza+ABZZgcxJNc4FO1gc0cOsCUrHevc8tdIMTIAhc4F198G2Qwwd8CBIQUAwEINABBBJUwR9R5wElgVRLwWODBBx4cGB8GEzDQIAo33CGJA8gh+JoH/clUgQU0YvDhdfmJdwEFC6Sjgg8yEPAABsPkh2F22cl2AQbn6QdTghTQ5eAJAQyQAAQV0MSBB9gRVZ4GE1mw5JZOAmiAVi1UWcAZDrDyZXYTeaOhA/bIVuIBPtKQ4h7ViYekUPdcEAEbzTzCRp5CADmAAwj+ORGPBcgwAAHo9ABGCYtm0ChwFHShlRiXhmHlkAcCiOeUodqQw5W0oXLAiamy4MOkjOyAaqxUymApDCEAADs=",
}
colors = ["#FF7B39", "#80F121"]
emphColors = ["#DAFC33", "#F42548"]
fieldParams = {
    "height": 3,
    "width": 70,
    "font": ("monaco", 14),
    "highlightthickness": 0,
    "borderwidth": 0,
    "background": "white",
}
textParams = {
    "bg": "#F7E0D4",
    "fg": "#2321F1",
    "highlightthickness": 0,
    "width": 1,
    "height": 10,
    "font": ("verdana", 16),
    "wrap": "word",
}


class Zone:
    def __init__(self, image, initialField, initialText):
        frm = Frame(root)
        frm.config(background="white")
        self.image = PhotoImage(format="gif", data=images[image.upper()])
        self.imageDimmed = PhotoImage(format="gif", data=images[image])
        self.img = Label(frm)
        self.img.config(borderwidth=0)
        self.img.pack(side="left")
        self.fld = Text(frm, **fieldParams)
        self.initScrollText(frm, self.fld, initialField)
        frm = Frame(root)
        self.txt = Text(frm, **textParams)
        self.initScrollText(frm, self.txt, initialText)
        for i in range(2):
            self.txt.tag_config(colors[i], background=colors[i])
            self.txt.tag_config("emph" + colors[i], foreground=emphColors[i])

    def initScrollText(self, frm, txt, contents):
        scl = Scrollbar(frm)
        scl.config(command=txt.yview)
        scl.pack(side="right", fill="y")
        txt.pack(side="left", expand=True, fill="x")
        txt.config(yscrollcommand=scl.set)
        txt.insert("1.0", contents)
        frm.pack(fill="x")
        Frame(height=2, bd=1, relief="ridge").pack(fill="x")

    def refresh(self):
        self.colorCycle = itertools.cycle(colors)
        try:
            self.substitute()
            self.img.config(image=self.image)
        except re.error:
            self.img.config(image=self.imageDimmed)


class FindZone(Zone):
    def addTags(self, m):
        color = next(self.colorCycle)
        self.txt.tag_add(color, "1.0+%sc" % m.start(), "1.0+%sc" % m.end())
        try:
            self.txt.tag_add(
                "emph" + color, "1.0+%sc" % m.start("emph"), "1.0+%sc" % m.end("emph")
            )
        except:
            pass

    def substitute(self, *args):
        for color in colors:
            self.txt.tag_remove(color, "1.0", "end")
            self.txt.tag_remove("emph" + color, "1.0", "end")
        self.rex = re.compile("")  # default value in case of malformed regexp
        self.rex = re.compile(self.fld.get("1.0", "end")[:-1], re.MULTILINE)
        try:
            re.compile("(?P<emph>%s)" % self.fld.get(SEL_FIRST, SEL_LAST))
            self.rexSel = re.compile(
                "%s(?P<emph>%s)%s"
                % (
                    self.fld.get("1.0", SEL_FIRST),
                    self.fld.get(SEL_FIRST, SEL_LAST),
                    self.fld.get(SEL_LAST, "end")[:-1],
                ),
                re.MULTILINE,
            )
        except:
            self.rexSel = self.rex
        self.rexSel.sub(self.addTags, self.txt.get("1.0", "end"))


class ReplaceZone(Zone):
    def addTags(self, m):
        s = sz.rex.sub(self.repl, m.group())
        self.txt.delete(
            "1.0+%sc" % (m.start() + self.diff), "1.0+%sc" % (m.end() + self.diff)
        )
        self.txt.insert("1.0+%sc" % (m.start() + self.diff), s, next(self.colorCycle))
        self.diff += len(s) - (m.end() - m.start())

    def substitute(self):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", sz.txt.get("1.0", "end")[:-1])
        self.diff = 0
        self.repl = rex0.sub(r"\\g<\1>", self.fld.get("1.0", "end")[:-1])
        sz.rex.sub(self.addTags, sz.txt.get("1.0", "end")[:-1])


def launchRefresh(_):
    sz.fld.after_idle(sz.refresh)
    rz.fld.after_idle(rz.refresh)


def app():
    global root, sz, rz, rex0
    root = Tk()
    root.resizable(height=False, width=True)
    root.title(windowTitle)
    root.minsize(width=250, height=0)
    sz = FindZone("find", initialFind, initialText)
    sz.fld.bind("<Button-1>", launchRefresh)
    sz.fld.bind("<ButtonRelease-1>", launchRefresh)
    sz.fld.bind("<B1-Motion>", launchRefresh)
    sz.rexSel = re.compile("")
    rz = ReplaceZone("repl", initialRepl, "")
    rex0 = re.compile(r"(?<!\\)\\([0-9]+)")
    root.bind_all("<Key>", launchRefresh)
    launchRefresh(None)
    root.mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/exported_projects\app_20250703_223016\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/src\nexuscore\gradio_app\interactive_generator.py ===
# src/gradio_app/interactive_generator.py
import gradio as gr
import os
import re
import difflib
import subprocess
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_OUTPUT_DIR = "../sandbox_output"
DEFAULT_FILENAME = "sample.py"
LOG_FILE = "../logs/save_log.txt"
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
os.makedirs("../logs", exist_ok=True)

# === GPT呼び出し ===
def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# === コードと理由の抽出 ===
def extract_code_and_reason(full_response):
    code_match = re.search(r"```(?:python)?\n(.*?)```", full_response, re.DOTALL)
    reason_match = re.split(r"```.*?```", full_response, maxsplit=1)
    code = code_match.group(1).strip() if code_match else ""
    reason = reason_match[1].strip() if len(reason_match) > 1 else ""
    return code, reason

# === ファイルパス抽出 ===
def extract_file_path_from_code(code: str, default_path: str = os.path.join(DEFAULT_OUTPUT_DIR, DEFAULT_FILENAME)) -> str:
    match = re.search(r"#\s*filepath\s*:\s*(.+\.py)", code)
    if match:
        return match.group(1).strip()
    return default_path

# === 差分取得 ===
def get_diff(old, new):
    diff = difflib.HtmlDiff().make_file(old.splitlines(), new.splitlines(), context=True)
    return diff

# === バージョン番号付与 ===
def get_versioned_path(path):
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(path):
        path = f"{base}_v{i}{ext}"
        i += 1
    return path

# === ファイル保存 ===
def save_code_with_backup_and_diff(code: str, user_path: str):
    try:
        save_path = extract_file_path_from_code(code, default_path=user_path)
        full_path = os.path.join("..", save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        diff_html = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                old_code = f.read()
            diff_html = get_diff(old_code, code)
            backup_path = full_path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(old_code)
            save_path = get_versioned_path(full_path)  # avoid overwrite

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now()} - Saved: {save_path}\n")

        return f"✅ 保存成功: {save_path}", diff_html

    except Exception as e:
        return f"❌ 保存失敗: {str(e)}", ""

# === Gradio UI ===
with gr.Blocks() as app:
    gr.Markdown("### 🧐 自然文からAI補足付き 初期コード自動生成")

    initial_input = gr.Textbox(label="📝 やりたいこと（自然文）")
    output_path_input = gr.Textbox(label="📂 保存先（例: src/utils/my_func.py）", value="src/generated/sample.py")
    submit_btn = gr.Button("🔍 質問を開始")
    gpt_question = gr.Textbox(label="🤠 GPTの補足質問", lines=2)
    user_reply = gr.Textbox(label="✍️ 回答を記入")
    loop_again_btn = gr.Button("🔁 さらに質問してほしい")
    generate_code_btn = gr.Button("✅ これでコード生成してよい")
    code_output = gr.Code(label="📄 GPTによる初期コード", language="python")
    save_result = gr.Textbox(label="✅ 保存結果メッセージ", interactive=False)
    file_list = gr.Dropdown(label="🗂 保存済みファイル一覧", choices=[])
    open_in_vscode_btn = gr.Button("🖥 VSCodeで開く")
    diff_output = gr.HTML(label="📌 差分表示（HTML強調）")
    history = gr.State("")

    def ask_gpt_question(user_goal, prev_answers):
        prompt = f"""
以下はユーザーの目的です。
これに基づいて、実装前に補足確認すべき点を最大3点、質問形式で出力してください。
すでに以下の回答が得られています：
{prev_answers}

【ユーザー目的】
{user_goal}
"""
        return call_gpt(prompt)

    def update_history(history_text, question, answer):
        return history_text + f"【GPTの質問】\n{question}\n【ユーザーの回答】\n{answer}\n\n"

    def ask_more_questions(user_goal, current_answer, prev_q, hist):
        new_hist = update_history(hist, prev_q, current_answer)
        next_q = ask_gpt_question(user_goal, new_hist)
        return next_q, new_hist

    def generate_final_code(user_goal, hist, output_path):
        final_prompt = f"""
以下はユーザーの実施目的と、事前の質問・回答のやりとり履歴です。
この情報に基づき、docstring付きのPython関数を一つ作成してください。

【目的】
{user_goal}

【補足内容】
{hist}
"""
        response = call_gpt(final_prompt)
        code, _ = extract_code_and_reason(response)
        result, diff = save_code_with_backup_and_diff(code, output_path)
        return code, result, diff

    def list_saved_files():
        file_paths = []
        for root, _, files in os.walk("../src"):
            for f in files:
                if f.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, f), "../")
                    file_paths.append(rel_path)
        return sorted(file_paths)

    def open_file_in_vscode(file_path):
        try:
            subprocess.Popen(["code", os.path.join("..", file_path)])
            return f"🖥 VSCodeで開きました: {file_path}"
        except Exception as e:
            return f"❌ VSCode起動失敗: {str(e)}"

    submit_btn.click(fn=ask_gpt_question, inputs=[initial_input, history], outputs=[gpt_question])
    loop_again_btn.click(fn=ask_more_questions, inputs=[initial_input, user_reply, gpt_question, history], outputs=[gpt_question, history])
    generate_code_btn.click(fn=generate_final_code, inputs=[initial_input, history, output_path_input], outputs=[code_output, save_result, diff_output])
    generate_code_btn.click(fn=list_saved_files, inputs=[], outputs=[file_list])
    open_in_vscode_btn.click(fn=open_file_in_vscode, inputs=[file_list], outputs=[save_result])

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\interactive_generator.py ===
# src/gradio_app/interactive_generator.py
import gradio as gr
import os
import re
import difflib
import subprocess
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_OUTPUT_DIR = "../sandbox_output"
DEFAULT_FILENAME = "sample.py"
LOG_FILE = "../logs/save_log.txt"
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
os.makedirs("../logs", exist_ok=True)

# === GPT呼び出し ===
def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# === コードと理由の抽出 ===
def extract_code_and_reason(full_response):
    code_match = re.search(r"```(?:python)?\n(.*?)```", full_response, re.DOTALL)
    reason_match = re.split(r"```.*?```", full_response, maxsplit=1)
    code = code_match.group(1).strip() if code_match else ""
    reason = reason_match[1].strip() if len(reason_match) > 1 else ""
    return code, reason

# === ファイルパス抽出 ===
def extract_file_path_from_code(code: str, default_path: str = os.path.join(DEFAULT_OUTPUT_DIR, DEFAULT_FILENAME)) -> str:
    match = re.search(r"#\s*filepath\s*:\s*(.+\.py)", code)
    if match:
        return match.group(1).strip()
    return default_path

# === 差分取得 ===
def get_diff(old, new):
    diff = difflib.HtmlDiff().make_file(old.splitlines(), new.splitlines(), context=True)
    return diff

# === バージョン番号付与 ===
def get_versioned_path(path):
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(path):
        path = f"{base}_v{i}{ext}"
        i += 1
    return path

# === ファイル保存 ===
def save_code_with_backup_and_diff(code: str, user_path: str):
    try:
        save_path = extract_file_path_from_code(code, default_path=user_path)
        full_path = os.path.join("..", save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        diff_html = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                old_code = f.read()
            diff_html = get_diff(old_code, code)
            backup_path = full_path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(old_code)
            save_path = get_versioned_path(full_path)  # avoid overwrite

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now()} - Saved: {save_path}\n")

        return f"✅ 保存成功: {save_path}", diff_html

    except Exception as e:
        return f"❌ 保存失敗: {str(e)}", ""

# === Gradio UI ===
with gr.Blocks() as app:
    gr.Markdown("### 🧐 自然文からAI補足付き 初期コード自動生成")

    initial_input = gr.Textbox(label="📝 やりたいこと（自然文）")
    output_path_input = gr.Textbox(label="📂 保存先（例: src/utils/my_func.py）", value="src/generated/sample.py")
    submit_btn = gr.Button("🔍 質問を開始")
    gpt_question = gr.Textbox(label="🤠 GPTの補足質問", lines=2)
    user_reply = gr.Textbox(label="✍️ 回答を記入")
    loop_again_btn = gr.Button("🔁 さらに質問してほしい")
    generate_code_btn = gr.Button("✅ これでコード生成してよい")
    code_output = gr.Code(label="📄 GPTによる初期コード", language="python")
    save_result = gr.Textbox(label="✅ 保存結果メッセージ", interactive=False)
    file_list = gr.Dropdown(label="🗂 保存済みファイル一覧", choices=[])
    open_in_vscode_btn = gr.Button("🖥 VSCodeで開く")
    diff_output = gr.HTML(label="📌 差分表示（HTML強調）")
    history = gr.State("")

    def ask_gpt_question(user_goal, prev_answers):
        prompt = f"""
以下はユーザーの目的です。
これに基づいて、実装前に補足確認すべき点を最大3点、質問形式で出力してください。
すでに以下の回答が得られています：
{prev_answers}

【ユーザー目的】
{user_goal}
"""
        return call_gpt(prompt)

    def update_history(history_text, question, answer):
        return history_text + f"【GPTの質問】\n{question}\n【ユーザーの回答】\n{answer}\n\n"

    def ask_more_questions(user_goal, current_answer, prev_q, hist):
        new_hist = update_history(hist, prev_q, current_answer)
        next_q = ask_gpt_question(user_goal, new_hist)
        return next_q, new_hist

    def generate_final_code(user_goal, hist, output_path):
        final_prompt = f"""
以下はユーザーの実施目的と、事前の質問・回答のやりとり履歴です。
この情報に基づき、docstring付きのPython関数を一つ作成してください。

【目的】
{user_goal}

【補足内容】
{hist}
"""
        response = call_gpt(final_prompt)
        code, _ = extract_code_and_reason(response)
        result, diff = save_code_with_backup_and_diff(code, output_path)
        return code, result, diff

    def list_saved_files():
        file_paths = []
        for root, _, files in os.walk("../src"):
            for f in files:
                if f.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, f), "../")
                    file_paths.append(rel_path)
        return sorted(file_paths)

    def open_file_in_vscode(file_path):
        try:
            subprocess.Popen(["code", os.path.join("..", file_path)])
            return f"🖥 VSCodeで開きました: {file_path}"
        except Exception as e:
            return f"❌ VSCode起動失敗: {str(e)}"

    submit_btn.click(fn=ask_gpt_question, inputs=[initial_input, history], outputs=[gpt_question])
    loop_again_btn.click(fn=ask_more_questions, inputs=[initial_input, user_reply, gpt_question, history], outputs=[gpt_question, history])
    generate_code_btn.click(fn=generate_final_code, inputs=[initial_input, history, output_path_input], outputs=[code_output, save_result, diff_output])
    generate_code_btn.click(fn=list_saved_files, inputs=[], outputs=[file_list])
    open_in_vscode_btn.click(fn=open_file_in_vscode, inputs=[file_list], outputs=[save_result])

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\app_20250703_223016\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\utils\existing_image_processor.py ===
# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\gradio_app\interactive_generator.py ===
# src/gradio_app/interactive_generator.py
import gradio as gr
import os
import re
import difflib
import subprocess
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_OUTPUT_DIR = "../sandbox_output"
DEFAULT_FILENAME = "sample.py"
LOG_FILE = "../logs/save_log.txt"
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
os.makedirs("../logs", exist_ok=True)

# === GPT呼び出し ===
def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# === コードと理由の抽出 ===
def extract_code_and_reason(full_response):
    code_match = re.search(r"```(?:python)?\n(.*?)```", full_response, re.DOTALL)
    reason_match = re.split(r"```.*?```", full_response, maxsplit=1)
    code = code_match.group(1).strip() if code_match else ""
    reason = reason_match[1].strip() if len(reason_match) > 1 else ""
    return code, reason

# === ファイルパス抽出 ===
def extract_file_path_from_code(code: str, default_path: str = os.path.join(DEFAULT_OUTPUT_DIR, DEFAULT_FILENAME)) -> str:
    match = re.search(r"#\s*filepath\s*:\s*(.+\.py)", code)
    if match:
        return match.group(1).strip()
    return default_path

# === 差分取得 ===
def get_diff(old, new):
    diff = difflib.HtmlDiff().make_file(old.splitlines(), new.splitlines(), context=True)
    return diff

# === バージョン番号付与 ===
def get_versioned_path(path):
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(path):
        path = f"{base}_v{i}{ext}"
        i += 1
    return path

# === ファイル保存 ===
def save_code_with_backup_and_diff(code: str, user_path: str):
    try:
        save_path = extract_file_path_from_code(code, default_path=user_path)
        full_path = os.path.join("..", save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        diff_html = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                old_code = f.read()
            diff_html = get_diff(old_code, code)
            backup_path = full_path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(old_code)
            save_path = get_versioned_path(full_path)  # avoid overwrite

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(code)

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now()} - Saved: {save_path}\n")

        return f"✅ 保存成功: {save_path}", diff_html

    except Exception as e:
        return f"❌ 保存失敗: {str(e)}", ""

# === Gradio UI ===
with gr.Blocks() as app:
    gr.Markdown("### 🧐 自然文からAI補足付き 初期コード自動生成")

    initial_input = gr.Textbox(label="📝 やりたいこと（自然文）")
    output_path_input = gr.Textbox(label="📂 保存先（例: src/utils/my_func.py）", value="src/generated/sample.py")
    submit_btn = gr.Button("🔍 質問を開始")
    gpt_question = gr.Textbox(label="🤠 GPTの補足質問", lines=2)
    user_reply = gr.Textbox(label="✍️ 回答を記入")
    loop_again_btn = gr.Button("🔁 さらに質問してほしい")
    generate_code_btn = gr.Button("✅ これでコード生成してよい")
    code_output = gr.Code(label="📄 GPTによる初期コード", language="python")
    save_result = gr.Textbox(label="✅ 保存結果メッセージ", interactive=False)
    file_list = gr.Dropdown(label="🗂 保存済みファイル一覧", choices=[])
    open_in_vscode_btn = gr.Button("🖥 VSCodeで開く")
    diff_output = gr.HTML(label="📌 差分表示（HTML強調）")
    history = gr.State("")

    def ask_gpt_question(user_goal, prev_answers):
        prompt = f"""
以下はユーザーの目的です。
これに基づいて、実装前に補足確認すべき点を最大3点、質問形式で出力してください。
すでに以下の回答が得られています：
{prev_answers}

【ユーザー目的】
{user_goal}
"""
        return call_gpt(prompt)

    def update_history(history_text, question, answer):
        return history_text + f"【GPTの質問】\n{question}\n【ユーザーの回答】\n{answer}\n\n"

    def ask_more_questions(user_goal, current_answer, prev_q, hist):
        new_hist = update_history(hist, prev_q, current_answer)
        next_q = ask_gpt_question(user_goal, new_hist)
        return next_q, new_hist

    def generate_final_code(user_goal, hist, output_path):
        final_prompt = f"""
以下はユーザーの実施目的と、事前の質問・回答のやりとり履歴です。
この情報に基づき、docstring付きのPython関数を一つ作成してください。

【目的】
{user_goal}

【補足内容】
{hist}
"""
        response = call_gpt(final_prompt)
        code, _ = extract_code_and_reason(response)
        result, diff = save_code_with_backup_and_diff(code, output_path)
        return code, result, diff

    def list_saved_files():
        file_paths = []
        for root, _, files in os.walk("../src"):
            for f in files:
                if f.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, f), "../")
                    file_paths.append(rel_path)
        return sorted(file_paths)

    def open_file_in_vscode(file_path):
        try:
            subprocess.Popen(["code", os.path.join("..", file_path)])
            return f"🖥 VSCodeで開きました: {file_path}"
        except Exception as e:
            return f"❌ VSCode起動失敗: {str(e)}"

    submit_btn.click(fn=ask_gpt_question, inputs=[initial_input, history], outputs=[gpt_question])
    loop_again_btn.click(fn=ask_more_questions, inputs=[initial_input, user_reply, gpt_question, history], outputs=[gpt_question, history])
    generate_code_btn.click(fn=generate_final_code, inputs=[initial_input, history, output_path_input], outputs=[code_output, save_result, diff_output])
    generate_code_btn.click(fn=list_saved_files, inputs=[], outputs=[file_list])
    open_in_vscode_btn.click(fn=open_file_in_vscode, inputs=[file_list], outputs=[save_result])

# === NexusCore/src\nexuscore\gradio_app\revision_tab.py ===
# ファイル: src/nexuscore/gradio_app/revision_tab.py

import gradio as gr
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SAMPLE_FILE = "./sandbox_output/sample.py"
TEST_FILE = "./sandbox_output/test_sample.py"
HISTORY_FILE = "./sandbox_output/patch_history.txt"


def read_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def save_file(file_path: str, content: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def save_patch_history(code: str, reason: str, prompt: str):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write("\n=== 新しい修正案 ===\n")
        f.write("[📝 修正理由]:\n" + reason + "\n")
        f.write("[📤 GPTプロンプト]:\n" + prompt + "\n")
        f.write("[💻 修正コード]:\n" + code + "\n")


def run_pytest() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["pytest", TEST_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output
    except Exception as e:
        return f"❌ pytest 実行エラー: {str(e)}"


def generate_prompt(sample_path: str, test_path: str, summary: str, history: str, error_log: str, user_note: str) -> str:
    sample_code = read_file(sample_path)
    test_code = read_file(test_path)

    return f"""# Context
以下はPython関数（sample.py）と対応するテスト（test_sample.py）です。

# sample.py
{sample_code}

# test_sample.py
{test_code}

# ユーザーの目的
{user_note}

# バージョン要約（最新版）
{summary}

# 修正履歴（直近）
{history}

# テスト結果
{error_log}

# 指示
上記情報を踏まえて、ユーザーが意図した動作を達成できるように `sample.py` の修正コードを提案してください。

- コードのみを返してください
- 余計な説明文、Markdown記法、```python や ``` は不要です
- すべてのコードは sample.py に直接書き込める内容にしてください
- コメントを付けるのは歓迎です
- 既存コードの行番号や差分ではなく、完全な最新コードを提示してください
"""


def extract_code_and_reason(response: str) -> tuple[str, str]:
    """
    GPTレスポンスからコード部分と修正理由を抽出。
    """
    match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
    code = match.group(1).strip() if match else response.strip()

    reason_match = re.search(r"(?:(?:修正理由|Reason)[：:]?)(.*)", response)
    reason = reason_match.group(1).strip() if reason_match else "（理由が抽出できませんでした）"

    return code, reason


def call_gpt(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()


def tab_revision():
    """
    Gradioタブを返す：反復修正UI
    """
    with gr.Blocks() as tab:
        gr.Markdown("## 🔁 AIによる反復コード修正とpytest実行")

        code_input = gr.Code(label="📝 修正対象のPython関数コード", language="python")
        user_instruction = gr.Textbox(label="💡 ユーザーからの要望・補足", placeholder="例：引数nが負のときはFalseを返すようにしてください")
        test_failures = gr.Textbox(label="❌ テスト失敗ログ", placeholder="pytestの失敗出力を貼り付けてください", lines=5)

        generated_code = gr.Code(label="✅ GPTが生成した修正コード", language="python")
        explanation = gr.Textbox(label="📄 修正理由と要約", lines=3)
        test_result = gr.Textbox(label="🧪 pytest 実行結果", lines=10)

        revise_btn = gr.Button("🔁 修正案を生成")
        approve_btn = gr.Button("✅ 修正案を適用して上書き")

        def generate_revision(user_code: str, user_note: str, fail_log: str):
            save_file(SAMPLE_FILE, user_code)
            prompt = generate_prompt(SAMPLE_FILE, TEST_FILE, "現行バージョンはユーザー入力", "直近の1件のみ", fail_log, user_note)
            gpt_response = call_gpt(prompt)
            code, reason = extract_code_and_reason(gpt_response)
            return code, reason, prompt

        def apply_patch(code: str, reason: str, prompt: str):
            save_file(SAMPLE_FILE, code)
            save_patch_history(code, reason, prompt)
            return run_pytest()

        revise_btn.click(
            fn=generate_revision,
            inputs=[code_input, user_instruction, test_failures],
            outputs=[generated_code, explanation, user_instruction]
        )

        approve_btn.click(
            fn=apply_patch,
            inputs=[generated_code, explanation, user_instruction],
            outputs=test_result
        )

    return tab

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32con.py ===
# Generated by h2py from commdlg.h (plus modifications 4jan98)
WINVER = 1280
WM_USER = 1024
PY_0U = 0
OFN_READONLY = 1
OFN_OVERWRITEPROMPT = 2
OFN_HIDEREADONLY = 4
OFN_NOCHANGEDIR = 8
OFN_SHOWHELP = 16
OFN_ENABLEHOOK = 32
OFN_ENABLETEMPLATE = 64
OFN_ENABLETEMPLATEHANDLE = 128
OFN_NOVALIDATE = 256
OFN_ALLOWMULTISELECT = 512
OFN_EXTENSIONDIFFERENT = 1024
OFN_PATHMUSTEXIST = 2048
OFN_FILEMUSTEXIST = 4096
OFN_CREATEPROMPT = 8192
OFN_SHAREAWARE = 16384
OFN_NOREADONLYRETURN = 32768
OFN_NOTESTFILECREATE = 65536
OFN_NONETWORKBUTTON = 131072
OFN_NOLONGNAMES = 262144
OFN_EXPLORER = 524288  # new look commdlg
OFN_NODEREFERENCELINKS = 1048576
OFN_LONGNAMES = 2097152  # force long names for Python 3 modules
OFN_ENABLEINCLUDENOTIFY = 4194304  # send include message to callback
OFN_ENABLESIZING = 8388608
OFN_DONTADDTORECENT = 33554432
OFN_FORCESHOWHIDDEN = 268435456  # Show All files including System and hidden files
OFN_EX_NOPLACESBAR = 1
OFN_SHAREFALLTHROUGH = 2
OFN_SHARENOWARN = 1
OFN_SHAREWARN = 0
CDN_FIRST = PY_0U - 601
CDN_LAST = PY_0U - 699
CDN_INITDONE = CDN_FIRST - 0
CDN_SELCHANGE = CDN_FIRST - 1
CDN_FOLDERCHANGE = CDN_FIRST - 2
CDN_SHAREVIOLATION = CDN_FIRST - 3
CDN_HELP = CDN_FIRST - 4
CDN_FILEOK = CDN_FIRST - 5
CDN_TYPECHANGE = CDN_FIRST - 6
CDN_INCLUDEITEM = CDN_FIRST - 7
CDM_FIRST = WM_USER + 100
CDM_LAST = WM_USER + 200
CDM_GETSPEC = CDM_FIRST + 0
CDM_GETFILEPATH = CDM_FIRST + 1
CDM_GETFOLDERPATH = CDM_FIRST + 2
CDM_GETFOLDERIDLIST = CDM_FIRST + 3
CDM_SETCONTROLTEXT = CDM_FIRST + 4
CDM_HIDECONTROL = CDM_FIRST + 5
CDM_SETDEFEXT = CDM_FIRST + 6
CC_RGBINIT = 1
CC_FULLOPEN = 2
CC_PREVENTFULLOPEN = 4
CC_SHOWHELP = 8
CC_ENABLEHOOK = 16
CC_ENABLETEMPLATE = 32
CC_ENABLETEMPLATEHANDLE = 64
CC_SOLIDCOLOR = 128
CC_ANYCOLOR = 256
FR_DOWN = 1
FR_WHOLEWORD = 2
FR_MATCHCASE = 4
FR_FINDNEXT = 8
FR_REPLACE = 16
FR_REPLACEALL = 32
FR_DIALOGTERM = 64
FR_SHOWHELP = 128
FR_ENABLEHOOK = 256
FR_ENABLETEMPLATE = 512
FR_NOUPDOWN = 1024
FR_NOMATCHCASE = 2048
FR_NOWHOLEWORD = 4096
FR_ENABLETEMPLATEHANDLE = 8192
FR_HIDEUPDOWN = 16384
FR_HIDEMATCHCASE = 32768
FR_HIDEWHOLEWORD = 65536
CF_SCREENFONTS = 1
CF_PRINTERFONTS = 2
CF_BOTH = CF_SCREENFONTS | CF_PRINTERFONTS
CF_SHOWHELP = 4
CF_ENABLEHOOK = 8
CF_ENABLETEMPLATE = 16
CF_ENABLETEMPLATEHANDLE = 32
CF_INITTOLOGFONTSTRUCT = 64
CF_USESTYLE = 128
CF_EFFECTS = 256
CF_APPLY = 512
CF_ANSIONLY = 1024
CF_SCRIPTSONLY = CF_ANSIONLY
CF_NOVECTORFONTS = 2048
CF_NOOEMFONTS = CF_NOVECTORFONTS
CF_NOSIMULATIONS = 4096
CF_LIMITSIZE = 8192
CF_FIXEDPITCHONLY = 16384
CF_WYSIWYG = 32768  # must also have CF_SCREENFONTS & CF_PRINTERFONTS
CF_FORCEFONTEXIST = 65536
CF_SCALABLEONLY = 131072
CF_TTONLY = 262144
CF_NOFACESEL = 524288
CF_NOSTYLESEL = 1048576
CF_NOSIZESEL = 2097152
CF_SELECTSCRIPT = 4194304
CF_NOSCRIPTSEL = 8388608
CF_NOVERTFONTS = 16777216
SIMULATED_FONTTYPE = 32768
PRINTER_FONTTYPE = 16384
SCREEN_FONTTYPE = 8192
BOLD_FONTTYPE = 256
ITALIC_FONTTYPE = 512
REGULAR_FONTTYPE = 1024
OPENTYPE_FONTTYPE = 65536
TYPE1_FONTTYPE = 131072
DSIG_FONTTYPE = 262144
WM_CHOOSEFONT_GETLOGFONT = WM_USER + 1
WM_CHOOSEFONT_SETLOGFONT = WM_USER + 101
WM_CHOOSEFONT_SETFLAGS = WM_USER + 102
LBSELCHSTRINGA = "commdlg_LBSelChangedNotify"
SHAREVISTRINGA = "commdlg_ShareViolation"
FILEOKSTRINGA = "commdlg_FileNameOK"
COLOROKSTRINGA = "commdlg_ColorOK"
SETRGBSTRINGA = "commdlg_SetRGBColor"
HELPMSGSTRINGA = "commdlg_help"
FINDMSGSTRINGA = "commdlg_FindReplace"
LBSELCHSTRING = LBSELCHSTRINGA
SHAREVISTRING = SHAREVISTRINGA
FILEOKSTRING = FILEOKSTRINGA
COLOROKSTRING = COLOROKSTRINGA
SETRGBSTRING = SETRGBSTRINGA
HELPMSGSTRING = HELPMSGSTRINGA
FINDMSGSTRING = FINDMSGSTRINGA
CD_LBSELNOITEMS = -1
CD_LBSELCHANGE = 0
CD_LBSELSUB = 1
CD_LBSELADD = 2
PD_ALLPAGES = 0
PD_SELECTION = 1
PD_PAGENUMS = 2
PD_NOSELECTION = 4
PD_NOPAGENUMS = 8
PD_COLLATE = 16
PD_PRINTTOFILE = 32
PD_PRINTSETUP = 64
PD_NOWARNING = 128
PD_RETURNDC = 256
PD_RETURNIC = 512
PD_RETURNDEFAULT = 1024
PD_SHOWHELP = 2048
PD_ENABLEPRINTHOOK = 4096
PD_ENABLESETUPHOOK = 8192
PD_ENABLEPRINTTEMPLATE = 16384
PD_ENABLESETUPTEMPLATE = 32768
PD_ENABLEPRINTTEMPLATEHANDLE = 65536
PD_ENABLESETUPTEMPLATEHANDLE = 131072
PD_USEDEVMODECOPIES = 262144
PD_DISABLEPRINTTOFILE = 524288
PD_HIDEPRINTTOFILE = 1048576
PD_NONETWORKBUTTON = 2097152
DN_DEFAULTPRN = 1
WM_PSD_PAGESETUPDLG = WM_USER
WM_PSD_FULLPAGERECT = WM_USER + 1
WM_PSD_MINMARGINRECT = WM_USER + 2
WM_PSD_MARGINRECT = WM_USER + 3
WM_PSD_GREEKTEXTRECT = WM_USER + 4
WM_PSD_ENVSTAMPRECT = WM_USER + 5
WM_PSD_YAFULLPAGERECT = WM_USER + 6
PSD_DEFAULTMINMARGINS = 0  # default (printer's)
PSD_INWININIINTLMEASURE = 0  # 1st of 4 possible
PSD_MINMARGINS = 1  # use caller's
PSD_MARGINS = 2  # use caller's
PSD_INTHOUSANDTHSOFINCHES = 4  # 2nd of 4 possible
PSD_INHUNDREDTHSOFMILLIMETERS = 8  # 3rd of 4 possible
PSD_DISABLEMARGINS = 16
PSD_DISABLEPRINTER = 32
PSD_NOWARNING = 128  # must be same as PD_*
PSD_DISABLEORIENTATION = 256
PSD_RETURNDEFAULT = 1024  # must be same as PD_*
PSD_DISABLEPAPER = 512
PSD_SHOWHELP = 2048  # must be same as PD_*
PSD_ENABLEPAGESETUPHOOK = 8192  # must be same as PD_*
PSD_ENABLEPAGESETUPTEMPLATE = 32768  # must be same as PD_*
PSD_ENABLEPAGESETUPTEMPLATEHANDLE = 131072  # must be same as PD_*
PSD_ENABLEPAGEPAINTHOOK = 262144
PSD_DISABLEPAGEPAINTING = 524288
PSD_NONETWORKBUTTON = 2097152  # must be same as PD_*

# Generated by h2py from winreg.h
HKEY_CLASSES_ROOT = -2147483648
HKEY_CURRENT_USER = -2147483647
HKEY_LOCAL_MACHINE = -2147483646
HKEY_USERS = -2147483645
HKEY_PERFORMANCE_DATA = -2147483644
HKEY_CURRENT_CONFIG = -2147483643
HKEY_DYN_DATA = -2147483642
HKEY_PERFORMANCE_TEXT = -2147483568  # ?? 4Jan98
HKEY_PERFORMANCE_NLSTEXT = -2147483552  # ?? 4Jan98

# Generated by h2py from winuser.h
HWND_BROADCAST = 65535
HWND_DESKTOP = 0
HWND_TOP = 0
HWND_BOTTOM = 1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_MESSAGE = -3

# winuser.h line 4601
SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_CXVSCROLL = 2
SM_CYHSCROLL = 3
SM_CYCAPTION = 4
SM_CXBORDER = 5
SM_CYBORDER = 6
SM_CXDLGFRAME = 7
SM_CYDLGFRAME = 8
SM_CYVTHUMB = 9
SM_CXHTHUMB = 10
SM_CXICON = 11
SM_CYICON = 12
SM_CXCURSOR = 13
SM_CYCURSOR = 14
SM_CYMENU = 15
SM_CXFULLSCREEN = 16
SM_CYFULLSCREEN = 17
SM_CYKANJIWINDOW = 18
SM_MOUSEPRESENT = 19
SM_CYVSCROLL = 20
SM_CXHSCROLL = 21
SM_DEBUG = 22
SM_SWAPBUTTON = 23
SM_RESERVED1 = 24
SM_RESERVED2 = 25
SM_RESERVED3 = 26
SM_RESERVED4 = 27
SM_CXMIN = 28
SM_CYMIN = 29
SM_CXSIZE = 30
SM_CYSIZE = 31
SM_CXFRAME = 32
SM_CYFRAME = 33
SM_CXMINTRACK = 34
SM_CYMINTRACK = 35
SM_CXDOUBLECLK = 36
SM_CYDOUBLECLK = 37
SM_CXICONSPACING = 38
SM_CYICONSPACING = 39
SM_MENUDROPALIGNMENT = 40
SM_PENWINDOWS = 41
SM_DBCSENABLED = 42
SM_CMOUSEBUTTONS = 43
SM_CXFIXEDFRAME = SM_CXDLGFRAME
SM_CYFIXEDFRAME = SM_CYDLGFRAME
SM_CXSIZEFRAME = SM_CXFRAME
SM_CYSIZEFRAME = SM_CYFRAME
SM_SECURE = 44
SM_CXEDGE = 45
SM_CYEDGE = 46
SM_CXMINSPACING = 47
SM_CYMINSPACING = 48
SM_CXSMICON = 49
SM_CYSMICON = 50
SM_CYSMCAPTION = 51
SM_CXSMSIZE = 52
SM_CYSMSIZE = 53
SM_CXMENUSIZE = 54
SM_CYMENUSIZE = 55
SM_ARRANGE = 56
SM_CXMINIMIZED = 57
SM_CYMINIMIZED = 58
SM_CXMAXTRACK = 59
SM_CYMAXTRACK = 60
SM_CXMAXIMIZED = 61
SM_CYMAXIMIZED = 62
SM_NETWORK = 63
SM_CLEANBOOT = 67
SM_CXDRAG = 68
SM_CYDRAG = 69
SM_SHOWSOUNDS = 70
SM_CXMENUCHECK = 71
SM_CYMENUCHECK = 72
SM_SLOWMACHINE = 73
SM_MIDEASTENABLED = 74
SM_MOUSEWHEELPRESENT = 75
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80
SM_SAMEDISPLAYFORMAT = 81
SM_CMETRICS = 83
MNC_IGNORE = 0
MNC_CLOSE = 1
MNC_EXECUTE = 2
MNC_SELECT = 3
MNS_NOCHECK = -2147483648
MNS_MODELESS = 1073741824
MNS_DRAGDROP = 536870912
MNS_AUTODISMISS = 268435456
MNS_NOTIFYBYPOS = 134217728
MNS_CHECKORBMP = 67108864
MIM_MAXHEIGHT = 1
MIM_BACKGROUND = 2
MIM_HELPID = 4
MIM_MENUDATA = 8
MIM_STYLE = 16
MIM_APPLYTOSUBMENUS = -2147483648
MND_CONTINUE = 0
MND_ENDMENU = 1
MNGOF_GAP = 3
MNGO_NOINTERFACE = 0
MNGO_NOERROR = 1
MIIM_STATE = 1
MIIM_ID = 2
MIIM_SUBMENU = 4
MIIM_CHECKMARKS = 8
MIIM_TYPE = 16
MIIM_DATA = 32
MIIM_STRING = 64
MIIM_BITMAP = 128
MIIM_FTYPE = 256
HBMMENU_CALLBACK = -1
HBMMENU_SYSTEM = 1
HBMMENU_MBAR_RESTORE = 2
HBMMENU_MBAR_MINIMIZE = 3
HBMMENU_MBAR_CLOSE = 5
HBMMENU_MBAR_CLOSE_D = 6
HBMMENU_MBAR_MINIMIZE_D = 7
HBMMENU_POPUP_CLOSE = 8
HBMMENU_POPUP_RESTORE = 9
HBMMENU_POPUP_MAXIMIZE = 10
HBMMENU_POPUP_MINIMIZE = 11
GMDI_USEDISABLED = 1
GMDI_GOINTOPOPUPS = 2
TPM_LEFTBUTTON = 0
TPM_RIGHTBUTTON = 2
TPM_LEFTALIGN = 0
TPM_CENTERALIGN = 4
TPM_RIGHTALIGN = 8
TPM_TOPALIGN = 0
TPM_VCENTERALIGN = 16
TPM_BOTTOMALIGN = 32
TPM_HORIZONTAL = 0
TPM_VERTICAL = 64
TPM_NONOTIFY = 128
TPM_RETURNCMD = 256
TPM_RECURSE = 1
DOF_EXECUTABLE = 32769
DOF_DOCUMENT = 32770
DOF_DIRECTORY = 32771
DOF_MULTIPLE = 32772
DOF_PROGMAN = 1
DOF_SHELLDATA = 2
DO_DROPFILE = 1162627398
DO_PRINTFILE = 1414419024
DT_TOP = 0
DT_LEFT = 0
DT_CENTER = 1
DT_RIGHT = 2
DT_VCENTER = 4
DT_BOTTOM = 8
DT_WORDBREAK = 16
DT_SINGLELINE = 32
DT_EXPANDTABS = 64
DT_TABSTOP = 128
DT_NOCLIP = 256
DT_EXTERNALLEADING = 512
DT_CALCRECT = 1024
DT_NOPREFIX = 2048
DT_INTERNAL = 4096
DT_EDITCONTROL = 8192
DT_PATH_ELLIPSIS = 16384
DT_END_ELLIPSIS = 32768
DT_MODIFYSTRING = 65536
DT_RTLREADING = 131072
DT_WORD_ELLIPSIS = 262144
DST_COMPLEX = 0
DST_TEXT = 1
DST_PREFIXTEXT = 2
DST_ICON = 3
DST_BITMAP = 4
DSS_NORMAL = 0
DSS_UNION = 16
DSS_DISABLED = 32
DSS_MONO = 128
DSS_RIGHT = 32768
DCX_WINDOW = 1
DCX_CACHE = 2
DCX_NORESETATTRS = 4
DCX_CLIPCHILDREN = 8
DCX_CLIPSIBLINGS = 16
DCX_PARENTCLIP = 32
DCX_EXCLUDERGN = 64
DCX_INTERSECTRGN = 128
DCX_EXCLUDEUPDATE = 256
DCX_INTERSECTUPDATE = 512
DCX_LOCKWINDOWUPDATE = 1024
DCX_VALIDATE = 2097152
CUDR_NORMAL = 0
CUDR_NOSNAPTOGRID = 1
CUDR_NORESOLVEPOSITIONS = 2
CUDR_NOCLOSEGAPS = 4
CUDR_NEGATIVECOORDS = 8
CUDR_NOPRIMARY = 16
RDW_INVALIDATE = 1
RDW_INTERNALPAINT = 2
RDW_ERASE = 4
RDW_VALIDATE = 8
RDW_NOINTERNALPAINT = 16
RDW_NOERASE = 32
RDW_NOCHILDREN = 64
RDW_ALLCHILDREN = 128
RDW_UPDATENOW = 256
RDW_ERASENOW = 512
RDW_FRAME = 1024
RDW_NOFRAME = 2048
SW_SCROLLCHILDREN = 1
SW_INVALIDATE = 2
SW_ERASE = 4
SW_SMOOTHSCROLL = 16  # Use smooth scrolling
ESB_ENABLE_BOTH = 0
ESB_DISABLE_BOTH = 3
ESB_DISABLE_LEFT = 1
ESB_DISABLE_RIGHT = 2
ESB_DISABLE_UP = 1
ESB_DISABLE_DOWN = 2
ESB_DISABLE_LTUP = ESB_DISABLE_LEFT
ESB_DISABLE_RTDN = ESB_DISABLE_RIGHT
HELPINFO_WINDOW = 1
HELPINFO_MENUITEM = 2
MB_OK = 0
MB_OKCANCEL = 1
MB_ABORTRETRYIGNORE = 2
MB_YESNOCANCEL = 3
MB_YESNO = 4
MB_RETRYCANCEL = 5
MB_ICONHAND = 16
MB_ICONQUESTION = 32
MB_ICONEXCLAMATION = 48
MB_ICONASTERISK = 64
MB_ICONWARNING = MB_ICONEXCLAMATION
MB_ICONERROR = MB_ICONHAND
MB_ICONINFORMATION = MB_ICONASTERISK
MB_ICONSTOP = MB_ICONHAND
MB_DEFBUTTON1 = 0
MB_DEFBUTTON2 = 256
MB_DEFBUTTON3 = 512
MB_DEFBUTTON4 = 768
MB_APPLMODAL = 0
MB_SYSTEMMODAL = 4096
MB_TASKMODAL = 8192
MB_HELP = 16384
MB_NOFOCUS = 32768
MB_SETFOREGROUND = 65536
MB_DEFAULT_DESKTOP_ONLY = 131072
MB_TOPMOST = 262144
MB_RIGHT = 524288
MB_RTLREADING = 1048576
MB_SERVICE_NOTIFICATION = 2097152
MB_TYPEMASK = 15
MB_USERICON = 128
MB_ICONMASK = 240
MB_DEFMASK = 3840
MB_MODEMASK = 12288
MB_MISCMASK = 49152
# winuser.h line 6373
CWP_ALL = 0
CWP_SKIPINVISIBLE = 1
CWP_SKIPDISABLED = 2
CWP_SKIPTRANSPARENT = 4
CTLCOLOR_MSGBOX = 0
CTLCOLOR_EDIT = 1
CTLCOLOR_LISTBOX = 2
CTLCOLOR_BTN = 3
CTLCOLOR_DLG = 4
CTLCOLOR_SCROLLBAR = 5
CTLCOLOR_STATIC = 6
CTLCOLOR_MAX = 7
COLOR_SCROLLBAR = 0
COLOR_BACKGROUND = 1
COLOR_ACTIVECAPTION = 2
COLOR_INACTIVECAPTION = 3
COLOR_MENU = 4
COLOR_WINDOW = 5
COLOR_WINDOWFRAME = 6
COLOR_MENUTEXT = 7
COLOR_WINDOWTEXT = 8
COLOR_CAPTIONTEXT = 9
COLOR_ACTIVEBORDER = 10
COLOR_INACTIVEBORDER = 11
COLOR_APPWORKSPACE = 12
COLOR_HIGHLIGHT = 13
COLOR_HIGHLIGHTTEXT = 14
COLOR_BTNFACE = 15
COLOR_BTNSHADOW = 16
COLOR_GRAYTEXT = 17
COLOR_BTNTEXT = 18
COLOR_INACTIVECAPTIONTEXT = 19
COLOR_BTNHIGHLIGHT = 20
COLOR_3DDKSHADOW = 21
COLOR_3DLIGHT = 22
COLOR_INFOTEXT = 23
COLOR_INFOBK = 24
COLOR_HOTLIGHT = 26
COLOR_GRADIENTACTIVECAPTION = 27
COLOR_GRADIENTINACTIVECAPTION = 28
COLOR_DESKTOP = COLOR_BACKGROUND
COLOR_3DFACE = COLOR_BTNFACE
COLOR_3DSHADOW = COLOR_BTNSHADOW
COLOR_3DHIGHLIGHT = COLOR_BTNHIGHLIGHT
COLOR_3DHILIGHT = COLOR_BTNHIGHLIGHT
COLOR_BTNHILIGHT = COLOR_BTNHIGHLIGHT
GW_HWNDFIRST = 0
GW_HWNDLAST = 1
GW_HWNDNEXT = 2
GW_HWNDPREV = 3
GW_OWNER = 4
GW_CHILD = 5
GW_ENABLEDPOPUP = 6
GW_MAX = 6
MF_INSERT = 0
MF_CHANGE = 128
MF_APPEND = 256
MF_DELETE = 512
MF_REMOVE = 4096
MF_BYCOMMAND = 0
MF_BYPOSITION = 1024
MF_SEPARATOR = 2048
MF_ENABLED = 0
MF_GRAYED = 1
MF_DISABLED = 2
MF_UNCHECKED = 0
MF_CHECKED = 8
MF_USECHECKBITMAPS = 512
MF_STRING = 0
MF_BITMAP = 4
MF_OWNERDRAW = 256
MF_POPUP = 16
MF_MENUBARBREAK = 32
MF_MENUBREAK = 64
MF_UNHILITE = 0
MF_HILITE = 128
MF_DEFAULT = 4096
MF_SYSMENU = 8192
MF_HELP = 16384
MF_RIGHTJUSTIFY = 16384
MF_MOUSESELECT = 32768
MF_END = 128
MFT_STRING = MF_STRING
MFT_BITMAP = MF_BITMAP
MFT_MENUBARBREAK = MF_MENUBARBREAK
MFT_MENUBREAK = MF_MENUBREAK
MFT_OWNERDRAW = MF_OWNERDRAW
MFT_RADIOCHECK = 512
MFT_SEPARATOR = MF_SEPARATOR
MFT_RIGHTORDER = 8192
MFT_RIGHTJUSTIFY = MF_RIGHTJUSTIFY
MFS_GRAYED = 3
MFS_DISABLED = MFS_GRAYED
MFS_CHECKED = MF_CHECKED
MFS_HILITE = MF_HILITE
MFS_ENABLED = MF_ENABLED
MFS_UNCHECKED = MF_UNCHECKED
MFS_UNHILITE = MF_UNHILITE
MFS_DEFAULT = MF_DEFAULT
MFS_MASK = 4235
MFS_HOTTRACKDRAWN = 268435456
MFS_CACHEDBMP = 536870912
MFS_BOTTOMGAPDROP = 1073741824
MFS_TOPGAPDROP = -2147483648
MFS_GAPDROP = -1073741824
SC_SIZE = 61440
SC_MOVE = 61456
SC_MINIMIZE = 61472
SC_MAXIMIZE = 61488
SC_NEXTWINDOW = 61504
SC_PREVWINDOW = 61520
SC_CLOSE = 61536
SC_VSCROLL = 61552
SC_HSCROLL = 61568
SC_MOUSEMENU = 61584
SC_KEYMENU = 61696
SC_ARRANGE = 61712
SC_RESTORE = 61728
SC_TASKLIST = 61744
SC_SCREENSAVE = 61760
SC_HOTKEY = 61776
SC_DEFAULT = 61792
SC_MONITORPOWER = 61808
SC_CONTEXTHELP = 61824
SC_SEPARATOR = 61455
SC_ICON = SC_MINIMIZE
SC_ZOOM = SC_MAXIMIZE
IDC_ARROW = 32512
IDC_IBEAM = 32513
IDC_WAIT = 32514
IDC_CROSS = 32515
IDC_UPARROW = 32516
IDC_SIZE = 32640  # OBSOLETE: use IDC_SIZEALL
IDC_ICON = 32641  # OBSOLETE: use IDC_ARROW
IDC_SIZENWSE = 32642
IDC_SIZENESW = 32643
IDC_SIZEWE = 32644
IDC_SIZENS = 32645
IDC_SIZEALL = 32646
IDC_NO = 32648
IDC_HAND = 32649
IDC_APPSTARTING = 32650
IDC_HELP = 32651
IMAGE_BITMAP = 0
IMAGE_ICON = 1
IMAGE_CURSOR = 2
IMAGE_ENHMETAFILE = 3
LR_DEFAULTCOLOR = 0
LR_MONOCHROME = 1
LR_COLOR = 2
LR_COPYRETURNORG = 4
LR_COPYDELETEORG = 8
LR_LOADFROMFILE = 16
LR_LOADTRANSPARENT = 32
LR_DEFAULTSIZE = 64
LR_LOADREALSIZE = 128
LR_LOADMAP3DCOLORS = 4096
LR_CREATEDIBSECTION = 8192
LR_COPYFROMRESOURCE = 16384
LR_SHARED = 32768
DI_MASK = 1
DI_IMAGE = 2
DI_NORMAL = 3
DI_COMPAT = 4
DI_DEFAULTSIZE = 8
RES_ICON = 1
RES_CURSOR = 2
OBM_CLOSE = 32754
OBM_UPARROW = 32753
OBM_DNARROW = 32752
OBM_RGARROW = 32751
OBM_LFARROW = 32750
OBM_REDUCE = 32749
OBM_ZOOM = 32748
OBM_RESTORE = 32747
OBM_REDUCED = 32746
OBM_ZOOMD = 32745
OBM_RESTORED = 32744
OBM_UPARROWD = 32743
OBM_DNARROWD = 32742
OBM_RGARROWD = 32741
OBM_LFARROWD = 32740
OBM_MNARROW = 32739
OBM_COMBO = 32738
OBM_UPARROWI = 32737
OBM_DNARROWI = 32736
OBM_RGARROWI = 32735
OBM_LFARROWI = 32734
OBM_OLD_CLOSE = 32767
OBM_SIZE = 32766
OBM_OLD_UPARROW = 32765
OBM_OLD_DNARROW = 32764
OBM_OLD_RGARROW = 32763
OBM_OLD_LFARROW = 32762
OBM_BTSIZE = 32761
OBM_CHECK = 32760
OBM_CHECKBOXES = 32759
OBM_BTNCORNERS = 32758
OBM_OLD_REDUCE = 32757
OBM_OLD_ZOOM = 32756
OBM_OLD_RESTORE = 32755
OCR_NORMAL = 32512
OCR_IBEAM = 32513
OCR_WAIT = 32514
OCR_CROSS = 32515
OCR_UP = 32516
OCR_SIZE = 32640
OCR_ICON = 32641
OCR_SIZENWSE = 32642
OCR_SIZENESW = 32643
OCR_SIZEWE = 32644
OCR_SIZENS = 32645
OCR_SIZEALL = 32646
OCR_ICOCUR = 32647
OCR_NO = 32648
OCR_HAND = 32649
OCR_APPSTARTING = 32650
# winuser.h line 7455
OIC_SAMPLE = 32512
OIC_HAND = 32513
OIC_QUES = 32514
OIC_BANG = 32515
OIC_NOTE = 32516
OIC_WINLOGO = 32517
OIC_WARNING = OIC_BANG
OIC_ERROR = OIC_HAND
OIC_INFORMATION = OIC_NOTE
ORD_LANGDRIVER = 1
IDI_APPLICATION = 32512
IDI_HAND = 32513
IDI_QUESTION = 32514
IDI_EXCLAMATION = 32515
IDI_ASTERISK = 32516
IDI_WINLOGO = 32517
IDI_WARNING = IDI_EXCLAMATION
IDI_ERROR = IDI_HAND
IDI_INFORMATION = IDI_ASTERISK
IDOK = 1
IDCANCEL = 2
IDABORT = 3
IDRETRY = 4
IDIGNORE = 5
IDYES = 6
IDNO = 7
IDCLOSE = 8
IDHELP = 9
ES_LEFT = 0
ES_CENTER = 1
ES_RIGHT = 2
ES_MULTILINE = 4
ES_UPPERCASE = 8
ES_LOWERCASE = 16
ES_PASSWORD = 32
ES_AUTOVSCROLL = 64
ES_AUTOHSCROLL = 128
ES_NOHIDESEL = 256
ES_OEMCONVERT = 1024
ES_READONLY = 2048
ES_WANTRETURN = 4096
ES_NUMBER = 8192
EN_SETFOCUS = 256
EN_KILLFOCUS = 512
EN_CHANGE = 768
EN_UPDATE = 1024
EN_ERRSPACE = 1280
EN_MAXTEXT = 1281
EN_HSCROLL = 1537
EN_VSCROLL = 1538
EC_LEFTMARGIN = 1
EC_RIGHTMARGIN = 2
EC_USEFONTINFO = 65535
EMSIS_COMPOSITIONSTRING = 1
EIMES_GETCOMPSTRATONCE = 1
EIMES_CANCELCOMPSTRINFOCUS = 2
EIMES_COMPLETECOMPSTRKILLFOCUS = 4
EM_GETSEL = 176
EM_SETSEL = 177
EM_GETRECT = 178
EM_SETRECT = 179
EM_SETRECTNP = 180
EM_SCROLL = 181
EM_LINESCROLL = 182
EM_SCROLLCARET = 183
EM_GETMODIFY = 184
EM_SETMODIFY = 185
EM_GETLINECOUNT = 186
EM_LINEINDEX = 187
EM_SETHANDLE = 188
EM_GETHANDLE = 189
EM_GETTHUMB = 190
EM_LINELENGTH = 193
EM_REPLACESEL = 194
EM_GETLINE = 196
EM_LIMITTEXT = 197
EM_CANUNDO = 198
EM_UNDO = 199
EM_FMTLINES = 200
EM_LINEFROMCHAR = 201
EM_SETTABSTOPS = 203
EM_SETPASSWORDCHAR = 204
EM_EMPTYUNDOBUFFER = 205
EM_GETFIRSTVISIBLELINE = 206
EM_SETREADONLY = 207
EM_SETWORDBREAKPROC = 208
EM_GETWORDBREAKPROC = 209
EM_GETPASSWORDCHAR = 210
EM_SETMARGINS = 211
EM_GETMARGINS = 212
EM_SETLIMITTEXT = EM_LIMITTEXT
EM_GETLIMITTEXT = 213
EM_POSFROMCHAR = 214
EM_CHARFROMPOS = 215
EM_SETIMESTATUS = 216
EM_GETIMESTATUS = 217
WB_LEFT = 0
WB_RIGHT = 1
WB_ISDELIMITER = 2
BS_PUSHBUTTON = 0
BS_DEFPUSHBUTTON = 1
BS_CHECKBOX = 2
BS_AUTOCHECKBOX = 3
BS_RADIOBUTTON = 4
BS_3STATE = 5
BS_AUTO3STATE = 6
BS_GROUPBOX = 7
BS_USERBUTTON = 8
BS_AUTORADIOBUTTON = 9
BS_OWNERDRAW = 11
BS_LEFTTEXT = 32
BS_TEXT = 0
BS_ICON = 64
BS_BITMAP = 128
BS_LEFT = 256
BS_RIGHT = 512
BS_CENTER = 768
BS_TOP = 1024
BS_BOTTOM = 2048
BS_VCENTER = 3072
BS_PUSHLIKE = 4096
BS_MULTILINE = 8192
BS_NOTIFY = 16384
BS_FLAT = 32768
BS_RIGHTBUTTON = BS_LEFTTEXT
BN_CLICKED = 0
BN_PAINT = 1
BN_HILITE = 2
BN_UNHILITE = 3
BN_DISABLE = 4
BN_DOUBLECLICKED = 5
BN_PUSHED = BN_HILITE
BN_UNPUSHED = BN_UNHILITE
BN_DBLCLK = BN_DOUBLECLICKED
BN_SETFOCUS = 6
BN_KILLFOCUS = 7
BM_GETCHECK = 240
BM_SETCHECK = 241
BM_GETSTATE = 242
BM_SETSTATE = 243
BM_SETSTYLE = 244
BM_CLICK = 245
BM_GETIMAGE = 246
BM_SETIMAGE = 247
BST_UNCHECKED = 0
BST_CHECKED = 1
BST_INDETERMINATE = 2
BST_PUSHED = 4
BST_FOCUS = 8
SS_LEFT = 0
SS_CENTER = 1
SS_RIGHT = 2
SS_ICON = 3
SS_BLACKRECT = 4
SS_GRAYRECT = 5
SS_WHITERECT = 6
SS_BLACKFRAME = 7
SS_GRAYFRAME = 8
SS_WHITEFRAME = 9
SS_USERITEM = 10
SS_SIMPLE = 11
SS_LEFTNOWORDWRAP = 12
SS_BITMAP = 14
SS_OWNERDRAW = 13
SS_ENHMETAFILE = 15
SS_ETCHEDHORZ = 16
SS_ETCHEDVERT = 17
SS_ETCHEDFRAME = 18
SS_TYPEMASK = 31
SS_NOPREFIX = 128
SS_NOTIFY = 256
SS_CENTERIMAGE = 512
SS_RIGHTJUST = 1024
SS_REALSIZEIMAGE = 2048
SS_SUNKEN = 4096
SS_ENDELLIPSIS = 16384
SS_PATHELLIPSIS = 32768
SS_WORDELLIPSIS = 49152
SS_ELLIPSISMASK = 49152
STM_SETICON = 368
STM_GETICON = 369
STM_SETIMAGE = 370
STM_GETIMAGE = 371
STN_CLICKED = 0
STN_DBLCLK = 1
STN_ENABLE = 2
STN_DISABLE = 3
STM_MSGMAX = 372
DWL_MSGRESULT = 0
DWL_DLGPROC = 4
DWL_USER = 8
DDL_READWRITE = 0
DDL_READONLY = 1
DDL_HIDDEN = 2
DDL_SYSTEM = 4
DDL_DIRECTORY = 16
DDL_ARCHIVE = 32
DDL_POSTMSGS = 8192
DDL_DRIVES = 16384
DDL_EXCLUSIVE = 32768

# from winuser.h line 153
RT_CURSOR = 1
RT_BITMAP = 2
RT_ICON = 3
RT_MENU = 4
RT_DIALOG = 5
RT_STRING = 6
RT_FONTDIR = 7
RT_FONT = 8
RT_ACCELERATOR = 9
RT_RCDATA = 10
RT_MESSAGETABLE = 11
DIFFERENCE = 11
RT_GROUP_CURSOR = RT_CURSOR + DIFFERENCE
RT_GROUP_ICON = RT_ICON + DIFFERENCE
RT_VERSION = 16
RT_DLGINCLUDE = 17
RT_PLUGPLAY = 19
RT_VXD = 20
RT_ANICURSOR = 21
RT_ANIICON = 22
RT_HTML = 23
# from winuser.h line 218
SB_HORZ = 0
SB_VERT = 1
SB_CTL = 2
SB_BOTH = 3
SB_LINEUP = 0
SB_LINELEFT = 0
SB_LINEDOWN = 1
SB_LINERIGHT = 1
SB_PAGEUP = 2
SB_PAGELEFT = 2
SB_PAGEDOWN = 3
SB_PAGERIGHT = 3
SB_THUMBPOSITION = 4
SB_THUMBTRACK = 5
SB_TOP = 6
SB_LEFT = 6
SB_BOTTOM = 7
SB_RIGHT = 7
SB_ENDSCROLL = 8
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_NORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_MAXIMIZE = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_SHOWMINNOACTIVE = 7
SW_SHOWNA = 8
SW_RESTORE = 9
SW_SHOWDEFAULT = 10
SW_FORCEMINIMIZE = 11
SW_MAX = 11
HIDE_WINDOW = 0
SHOW_OPENWINDOW = 1
SHOW_ICONWINDOW = 2
SHOW_FULLSCREEN = 3
SHOW_OPENNOACTIVATE = 4
SW_PARENTCLOSING = 1
SW_OTHERZOOM = 2
SW_PARENTOPENING = 3
SW_OTHERUNZOOM = 4
AW_HOR_POSITIVE = 1
AW_HOR_NEGATIVE = 2
AW_VER_POSITIVE = 4
AW_VER_NEGATIVE = 8
AW_CENTER = 16
AW_HIDE = 65536
AW_ACTIVATE = 131072
AW_SLIDE = 262144
AW_BLEND = 524288
KF_EXTENDED = 256
KF_DLGMODE = 2048
KF_MENUMODE = 4096
KF_ALTDOWN = 8192
KF_REPEAT = 16384
KF_UP = 32768
VK_LBUTTON = 1
VK_RBUTTON = 2
VK_CANCEL = 3
VK_MBUTTON = 4
VK_BACK = 8
VK_TAB = 9
VK_CLEAR = 12
VK_RETURN = 13
VK_SHIFT = 16
VK_CONTROL = 17
VK_MENU = 18
VK_PAUSE = 19
VK_CAPITAL = 20
VK_KANA = 21
VK_HANGEUL = 21  # old name - should be here for compatibility
VK_HANGUL = 21
VK_JUNJA = 23
VK_FINAL = 24
VK_HANJA = 25
VK_KANJI = 25
VK_ESCAPE = 27
VK_CONVERT = 28
VK_NONCONVERT = 29
VK_ACCEPT = 30
VK_MODECHANGE = 31
VK_SPACE = 32
VK_PRIOR = 33
VK_NEXT = 34
VK_END = 35
VK_HOME = 36
VK_LEFT = 37
VK_UP = 38
VK_RIGHT = 39
VK_DOWN = 40
VK_SELECT = 41
VK_PRINT = 42
VK_EXECUTE = 43
VK_SNAPSHOT = 44
VK_INSERT = 45
VK_DELETE = 46
VK_HELP = 47
VK_LWIN = 91
VK_RWIN = 92
VK_APPS = 93
VK_NUMPAD0 = 96
VK_NUMPAD1 = 97
VK_NUMPAD2 = 98
VK_NUMPAD3 = 99
VK_NUMPAD4 = 100
VK_NUMPAD5 = 101
VK_NUMPAD6 = 102
VK_NUMPAD7 = 103
VK_NUMPAD8 = 104
VK_NUMPAD9 = 105
VK_MULTIPLY = 106
VK_ADD = 107
VK_SEPARATOR = 108
VK_SUBTRACT = 109
VK_DECIMAL = 110
VK_DIVIDE = 111
VK_F1 = 112
VK_F2 = 113
VK_F3 = 114
VK_F4 = 115
VK_F5 = 116
VK_F6 = 117
VK_F7 = 118
VK_F8 = 119
VK_F9 = 120
VK_F10 = 121
VK_F11 = 122
VK_F12 = 123
VK_F13 = 124
VK_F14 = 125
VK_F15 = 126
VK_F16 = 127
VK_F17 = 128
VK_F18 = 129
VK_F19 = 130
VK_F20 = 131
VK_F21 = 132
VK_F22 = 133
VK_F23 = 134
VK_F24 = 135
VK_NUMLOCK = 144
VK_SCROLL = 145
VK_LSHIFT = 160
VK_RSHIFT = 161
VK_LCONTROL = 162
VK_RCONTROL = 163
VK_LMENU = 164
VK_RMENU = 165
VK_PROCESSKEY = 229
VK_ATTN = 246
VK_CRSEL = 247
VK_EXSEL = 248
VK_EREOF = 249
VK_PLAY = 250
VK_ZOOM = 251
VK_NONAME = 252
VK_PA1 = 253
VK_OEM_CLEAR = 254
# multi-media related "keys"
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_BROWSER_BACK = 0xA6
VK_BROWSER_FORWARD = 0xA7
WH_MIN = -1
WH_MSGFILTER = -1
WH_JOURNALRECORD = 0
WH_JOURNALPLAYBACK = 1
WH_KEYBOARD = 2
WH_GETMESSAGE = 3
WH_CALLWNDPROC = 4
WH_CBT = 5
WH_SYSMSGFILTER = 6
WH_MOUSE = 7
WH_HARDWARE = 8
WH_DEBUG = 9
WH_SHELL = 10
WH_FOREGROUNDIDLE = 11
WH_CALLWNDPROCRET = 12
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WH_MAX = 14
WH_MINHOOK = WH_MIN
WH_MAXHOOK = WH_MAX
HC_ACTION = 0
HC_GETNEXT = 1
HC_SKIP = 2
HC_NOREMOVE = 3
HC_NOREM = HC_NOREMOVE
HC_SYSMODALON = 4
HC_SYSMODALOFF = 5
HCBT_MOVESIZE = 0
HCBT_MINMAX = 1
HCBT_QS = 2
HCBT_CREATEWND = 3
HCBT_DESTROYWND = 4
HCBT_ACTIVATE = 5
HCBT_CLICKSKIPPED = 6
HCBT_KEYSKIPPED = 7
HCBT_SYSCOMMAND = 8
HCBT_SETFOCUS = 9
MSGF_DIALOGBOX = 0
MSGF_MESSAGEBOX = 1
MSGF_MENU = 2
# MSGF_MOVE = 3
# MSGF_SIZE = 4
MSGF_SCROLLBAR = 5
MSGF_NEXTWINDOW = 6
# MSGF_MAINLOOP = 8
MSGF_MAX = 8
MSGF_USER = 4096
HSHELL_WINDOWCREATED = 1
HSHELL_WINDOWDESTROYED = 2
HSHELL_ACTIVATESHELLWINDOW = 3
HSHELL_WINDOWACTIVATED = 4
HSHELL_GETMINRECT = 5
HSHELL_REDRAW = 6
HSHELL_TASKMAN = 7
HSHELL_LANGUAGE = 8
HSHELL_ACCESSIBILITYSTATE = 11
ACCESS_STICKYKEYS = 1
ACCESS_FILTERKEYS = 2
ACCESS_MOUSEKEYS = 3
# winuser.h line 624
LLKHF_EXTENDED = 1
LLKHF_INJECTED = 16
LLKHF_ALTDOWN = 32
LLKHF_UP = 128
LLKHF_LOWER_IL_INJECTED = 2
LLMHF_INJECTED = 1
LLMHF_LOWER_IL_INJECTED = 2
# line 692
HKL_PREV = 0
HKL_NEXT = 1
KLF_ACTIVATE = 1
KLF_SUBSTITUTE_OK = 2
KLF_UNLOADPREVIOUS = 4
KLF_REORDER = 8
KLF_REPLACELANG = 16
KLF_NOTELLSHELL = 128
KLF_SETFORPROCESS = 256
KL_NAMELENGTH = 9
DESKTOP_READOBJECTS = 1
DESKTOP_CREATEWINDOW = 2
DESKTOP_CREATEMENU = 4
DESKTOP_HOOKCONTROL = 8
DESKTOP_JOURNALRECORD = 16
DESKTOP_JOURNALPLAYBACK = 32
DESKTOP_ENUMERATE = 64
DESKTOP_WRITEOBJECTS = 128
DESKTOP_SWITCHDESKTOP = 256
DF_ALLOWOTHERACCOUNTHOOK = 1
WINSTA_ENUMDESKTOPS = 1
WINSTA_READATTRIBUTES = 2
WINSTA_ACCESSCLIPBOARD = 4
WINSTA_CREATEDESKTOP = 8
WINSTA_WRITEATTRIBUTES = 16
WINSTA_ACCESSGLOBALATOMS = 32
WINSTA_EXITWINDOWS = 64
WINSTA_ENUMERATE = 256
WINSTA_READSCREEN = 512
WSF_VISIBLE = 1
UOI_FLAGS = 1
UOI_NAME = 2
UOI_TYPE = 3
UOI_USER_SID = 4
GWL_WNDPROC = -4
GWL_HINSTANCE = -6
GWL_HWNDPARENT = -8
GWL_STYLE = -16
GWL_EXSTYLE = -20
GWL_USERDATA = -21
GWL_ID = -12
GCL_MENUNAME = -8
GCL_HBRBACKGROUND = -10
GCL_HCURSOR = -12
GCL_HICON = -14
GCL_HMODULE = -16
GCL_CBWNDEXTRA = -18
GCL_CBCLSEXTRA = -20
GCL_WNDPROC = -24
GCL_STYLE = -26
GCW_ATOM = -32
GCL_HICONSM = -34
# line 1291
WM_NULL = 0
WM_CREATE = 1
WM_DESTROY = 2
WM_MOVE = 3
WM_SIZE = 5
WM_ACTIVATE = 6
WA_INACTIVE = 0
WA_ACTIVE = 1
WA_CLICKACTIVE = 2
WM_SETFOCUS = 7
WM_KILLFOCUS = 8
WM_ENABLE = 10
WM_SETREDRAW = 11
WM_SETTEXT = 12
WM_GETTEXT = 13
WM_GETTEXTLENGTH = 14
WM_PAINT = 15
WM_CLOSE = 16
WM_QUERYENDSESSION = 17
WM_QUIT = 18
WM_QUERYOPEN = 19
WM_ERASEBKGND = 20
WM_SYSCOLORCHANGE = 21
WM_ENDSESSION = 22
WM_SHOWWINDOW = 24
WM_WININICHANGE = 26
WM_SETTINGCHANGE = WM_WININICHANGE
WM_DEVMODECHANGE = 27
WM_ACTIVATEAPP = 28
WM_FONTCHANGE = 29
WM_TIMECHANGE = 30
WM_CANCELMODE = 31
WM_SETCURSOR = 32
WM_MOUSEACTIVATE = 33
WM_CHILDACTIVATE = 34
WM_QUEUESYNC = 35
WM_GETMINMAXINFO = 36
WM_PAINTICON = 38
WM_ICONERASEBKGND = 39
WM_NEXTDLGCTL = 40
WM_SPOOLERSTATUS = 42
WM_DRAWITEM = 43
WM_MEASUREITEM = 44
WM_DELETEITEM = 45
WM_VKEYTOITEM = 46
WM_CHARTOITEM = 47
WM_SETFONT = 48
WM_GETFONT = 49
WM_SETHOTKEY = 50
WM_GETHOTKEY = 51
WM_QUERYDRAGICON = 55
WM_COMPAREITEM = 57
WM_GETOBJECT = 61
WM_COMPACTING = 65
WM_COMMNOTIFY = 68
WM_WINDOWPOSCHANGING = 70
WM_WINDOWPOSCHANGED = 71
WM_POWER = 72
PWR_OK = 1
PWR_FAIL = -1
PWR_SUSPENDREQUEST = 1
PWR_SUSPENDRESUME = 2
PWR_CRITICALRESUME = 3
WM_COPYDATA = 74
WM_CANCELJOURNAL = 75
WM_INPUTLANGCHANGEREQUEST = 80
WM_INPUTLANGCHANGE = 81
WM_TCARD = 82
WM_HELP = 83
WM_USERCHANGED = 84
WM_NOTIFYFORMAT = 85
NFR_ANSI = 1
NFR_UNICODE = 2
NF_QUERY = 3
NF_REQUERY = 4
WM_STYLECHANGING = 124
WM_STYLECHANGED = 125
WM_DISPLAYCHANGE = 126
WM_GETICON = 127
WM_SETICON = 128
WM_NCCREATE = 129
WM_NCDESTROY = 130
WM_NCCALCSIZE = 131
WM_NCHITTEST = 132
WM_NCPAINT = 133
WM_NCACTIVATE = 134
WM_GETDLGCODE = 135
WM_SYNCPAINT = 136
WM_NCMOUSEMOVE = 160
WM_NCLBUTTONDOWN = 161
WM_NCLBUTTONUP = 162
WM_NCLBUTTONDBLCLK = 163
WM_NCRBUTTONDOWN = 164
WM_NCRBUTTONUP = 165
WM_NCRBUTTONDBLCLK = 166
WM_NCMBUTTONDOWN = 167
WM_NCMBUTTONUP = 168
WM_NCMBUTTONDBLCLK = 169
WM_KEYFIRST = 256
WM_KEYDOWN = 256
WM_KEYUP = 257
WM_CHAR = 258
WM_DEADCHAR = 259
WM_SYSKEYDOWN = 260
WM_SYSKEYUP = 261
WM_SYSCHAR = 262
WM_SYSDEADCHAR = 263
WM_KEYLAST = 264
WM_IME_STARTCOMPOSITION = 269
WM_IME_ENDCOMPOSITION = 270
WM_IME_COMPOSITION = 271
WM_IME_KEYLAST = 271
WM_INITDIALOG = 272
WM_COMMAND = 273
WM_SYSCOMMAND = 274
WM_TIMER = 275
WM_HSCROLL = 276
WM_VSCROLL = 277
WM_INITMENU = 278
WM_INITMENUPOPUP = 279
WM_MENUSELECT = 287
WM_MENUCHAR = 288
WM_ENTERIDLE = 289
WM_MENURBUTTONUP = 290
WM_MENUDRAG = 291
WM_MENUGETOBJECT = 292
WM_UNINITMENUPOPUP = 293
WM_MENUCOMMAND = 294
WM_CTLCOLORMSGBOX = 306
WM_CTLCOLOREDIT = 307
WM_CTLCOLORLISTBOX = 308
WM_CTLCOLORBTN = 309
WM_CTLCOLORDLG = 310
WM_CTLCOLORSCROLLBAR = 311
WM_CTLCOLORSTATIC = 312
WM_MOUSEFIRST = 512
WM_MOUSEMOVE = 512
WM_LBUTTONDOWN = 513
WM_LBUTTONUP = 514
WM_LBUTTONDBLCLK = 515
WM_RBUTTONDOWN = 516
WM_RBUTTONUP = 517
WM_RBUTTONDBLCLK = 518
WM_MBUTTONDOWN = 519
WM_MBUTTONUP = 520
WM_MBUTTONDBLCLK = 521
WM_MOUSEWHEEL = 522
WM_MOUSELAST = 522
WHEEL_DELTA = 120  # Value for rolling one detent
WHEEL_PAGESCROLL = -1  # Scroll one page
WM_PARENTNOTIFY = 528
MENULOOP_WINDOW = 0
MENULOOP_POPUP = 1
WM_ENTERMENULOOP = 529
WM_EXITMENULOOP = 530
WM_NEXTMENU = 531
WM_SIZING = 532
WM_CAPTURECHANGED = 533
WM_MOVING = 534
WM_POWERBROADCAST = 536
PBT_APMQUERYSUSPEND = 0
PBT_APMQUERYSTANDBY = 1
PBT_APMQUERYSUSPENDFAILED = 2
PBT_APMQUERYSTANDBYFAILED = 3
PBT_APMSUSPEND = 4
PBT_APMSTANDBY = 5
PBT_APMRESUMECRITICAL = 6
PBT_APMRESUMESUSPEND = 7
PBT_APMRESUMESTANDBY = 8
PBTF_APMRESUMEFROMFAILURE = 1
PBT_APMBATTERYLOW = 9
PBT_APMPOWERSTATUSCHANGE = 10
PBT_APMOEMEVENT = 11
PBT_APMRESUMEAUTOMATIC = 18
WM_MDICREATE = 544
WM_MDIDESTROY = 545
WM_MDIACTIVATE = 546
WM_MDIRESTORE = 547
WM_MDINEXT = 548
WM_MDIMAXIMIZE = 549
WM_MDITILE = 550
WM_MDICASCADE = 551
WM_MDIICONARRANGE = 552
WM_MDIGETACTIVE = 553
WM_MDISETMENU = 560
WM_ENTERSIZEMOVE = 561
WM_EXITSIZEMOVE = 562
WM_DROPFILES = 563
WM_MDIREFRESHMENU = 564
WM_IME_SETCONTEXT = 641
WM_IME_NOTIFY = 642
WM_IME_CONTROL = 643
WM_IME_COMPOSITIONFULL = 644
WM_IME_SELECT = 645
WM_IME_CHAR = 646
WM_IME_REQUEST = 648
WM_IME_KEYDOWN = 656
WM_IME_KEYUP = 657
WM_MOUSEHOVER = 673
WM_MOUSELEAVE = 675
WM_CUT = 768
WM_COPY = 769
WM_PASTE = 770
WM_CLEAR = 771
WM_UNDO = 772
WM_RENDERFORMAT = 773
WM_RENDERALLFORMATS = 774
WM_DESTROYCLIPBOARD = 775
WM_DRAWCLIPBOARD = 776
WM_PAINTCLIPBOARD = 777
WM_VSCROLLCLIPBOARD = 778
WM_SIZECLIPBOARD = 779
WM_ASKCBFORMATNAME = 780
WM_CHANGECBCHAIN = 781
WM_HSCROLLCLIPBOARD = 782
WM_QUERYNEWPALETTE = 783
WM_PALETTEISCHANGING = 784
WM_PALETTECHANGED = 785
WM_HOTKEY = 786
WM_PRINT = 791
WM_HANDHELDFIRST = 856
WM_HANDHELDLAST = 863
WM_AFXFIRST = 864
WM_AFXLAST = 895
WM_PENWINFIRST = 896
WM_PENWINLAST = 911
WM_APP = 32768
WMSZ_LEFT = 1
WMSZ_RIGHT = 2
WMSZ_TOP = 3
WMSZ_TOPLEFT = 4
WMSZ_TOPRIGHT = 5
WMSZ_BOTTOM = 6
WMSZ_BOTTOMLEFT = 7
WMSZ_BOTTOMRIGHT = 8
# ST_BEGINSWP = 0
# ST_ENDSWP = 1
HTERROR = -2
HTTRANSPARENT = -1
HTNOWHERE = 0
HTCLIENT = 1
HTCAPTION = 2
HTSYSMENU = 3
HTGROWBOX = 4
HTSIZE = HTGROWBOX
HTMENU = 5
HTHSCROLL = 6
HTVSCROLL = 7
HTMINBUTTON = 8
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
HTBORDER = 18
HTREDUCE = HTMINBUTTON
HTZOOM = HTMAXBUTTON
HTSIZEFIRST = HTLEFT
HTSIZELAST = HTBOTTOMRIGHT
HTOBJECT = 19
HTCLOSE = 20
HTHELP = 21
SMTO_NORMAL = 0
SMTO_BLOCK = 1
SMTO_ABORTIFHUNG = 2
SMTO_NOTIMEOUTIFNOTHUNG = 8
MA_ACTIVATE = 1
MA_ACTIVATEANDEAT = 2
MA_NOACTIVATE = 3
MA_NOACTIVATEANDEAT = 4
ICON_SMALL = 0
ICON_BIG = 1
SIZE_RESTORED = 0
SIZE_MINIMIZED = 1
SIZE_MAXIMIZED = 2
SIZE_MAXSHOW = 3
SIZE_MAXHIDE = 4
SIZENORMAL = SIZE_RESTORED
SIZEICONIC = SIZE_MINIMIZED
SIZEFULLSCREEN = SIZE_MAXIMIZED
SIZEZOOMSHOW = SIZE_MAXSHOW
SIZEZOOMHIDE = SIZE_MAXHIDE
WVR_ALIGNTOP = 16
WVR_ALIGNLEFT = 32
WVR_ALIGNBOTTOM = 64
WVR_ALIGNRIGHT = 128
WVR_HREDRAW = 256
WVR_VREDRAW = 512
WVR_REDRAW = WVR_HREDRAW | WVR_VREDRAW
WVR_VALIDRECTS = 1024
MK_LBUTTON = 1
MK_RBUTTON = 2
MK_SHIFT = 4
MK_CONTROL = 8
MK_MBUTTON = 16
TME_HOVER = 1
TME_LEAVE = 2
TME_QUERY = 1073741824
TME_CANCEL = -2147483648
HOVER_DEFAULT = -1
WS_OVERLAPPED = 0
WS_POPUP = -2147483648
WS_CHILD = 1073741824
WS_MINIMIZE = 536870912
WS_VISIBLE = 268435456
WS_DISABLED = 134217728
WS_CLIPSIBLINGS = 67108864
WS_CLIPCHILDREN = 33554432
WS_MAXIMIZE = 16777216
WS_CAPTION = 12582912
WS_BORDER = 8388608
WS_DLGFRAME = 4194304
WS_VSCROLL = 2097152
WS_HSCROLL = 1048576
WS_SYSMENU = 524288
WS_THICKFRAME = 262144
WS_GROUP = 131072
WS_TABSTOP = 65536
WS_MINIMIZEBOX = 131072
WS_MAXIMIZEBOX = 65536
WS_TILED = WS_OVERLAPPED
WS_ICONIC = WS_MINIMIZE
WS_SIZEBOX = WS_THICKFRAME
WS_OVERLAPPEDWINDOW = (
    WS_OVERLAPPED
    | WS_CAPTION
    | WS_SYSMENU
    | WS_THICKFRAME
    | WS_MINIMIZEBOX
    | WS_MAXIMIZEBOX
)
WS_POPUPWINDOW = WS_POPUP | WS_BORDER | WS_SYSMENU
WS_CHILDWINDOW = WS_CHILD
WS_TILEDWINDOW = WS_OVERLAPPEDWINDOW
WS_EX_DLGMODALFRAME = 1
WS_EX_NOPARENTNOTIFY = 4
WS_EX_TOPMOST = 8
WS_EX_ACCEPTFILES = 16
WS_EX_TRANSPARENT = 32
WS_EX_MDICHILD = 64
WS_EX_TOOLWINDOW = 128
WS_EX_WINDOWEDGE = 256
WS_EX_CLIENTEDGE = 512
WS_EX_CONTEXTHELP = 1024
WS_EX_RIGHT = 4096
WS_EX_LEFT = 0
WS_EX_RTLREADING = 8192
WS_EX_LTRREADING = 0
WS_EX_LEFTSCROLLBAR = 16384
WS_EX_RIGHTSCROLLBAR = 0
WS_EX_CONTROLPARENT = 65536
WS_EX_STATICEDGE = 131072
WS_EX_APPWINDOW = 262144
WS_EX_OVERLAPPEDWINDOW = WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE
WS_EX_PALETTEWINDOW = WS_EX_WINDOWEDGE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
WS_EX_LAYERED = 0x00080000
WS_EX_NOINHERITLAYOUT = 0x00100000
WS_EX_LAYOUTRTL = 0x00400000
WS_EX_COMPOSITED = 0x02000000
WS_EX_NOACTIVATE = 0x08000000

CS_VREDRAW = 1
CS_HREDRAW = 2
# CS_KEYCVTWINDOW = 0x0004
CS_DBLCLKS = 8
CS_OWNDC = 32
CS_CLASSDC = 64
CS_PARENTDC = 128
# CS_NOKEYCVT = 0x0100
CS_NOCLOSE = 512
CS_SAVEBITS = 2048
CS_BYTEALIGNCLIENT = 4096
CS_BYTEALIGNWINDOW = 8192
CS_GLOBALCLASS = 16384
CS_IME = 65536
PRF_CHECKVISIBLE = 1
PRF_NONCLIENT = 2
PRF_CLIENT = 4
PRF_ERASEBKGND = 8
PRF_CHILDREN = 16
PRF_OWNED = 32
BDR_RAISEDOUTER = 1
BDR_SUNKENOUTER = 2
BDR_RAISEDINNER = 4
BDR_SUNKENINNER = 8
BDR_OUTER = 3
BDR_INNER = 12
# BDR_RAISED = 0x0005
# BDR_SUNKEN = 0x000a
EDGE_RAISED = BDR_RAISEDOUTER | BDR_RAISEDINNER
EDGE_SUNKEN = BDR_SUNKENOUTER | BDR_SUNKENINNER
EDGE_ETCHED = BDR_SUNKENOUTER | BDR_RAISEDINNER
EDGE_BUMP = BDR_RAISEDOUTER | BDR_SUNKENINNER

# winuser.h line 2879
ISMEX_NOSEND = 0
ISMEX_SEND = 1
ISMEX_NOTIFY = 2
ISMEX_CALLBACK = 4
ISMEX_REPLIED = 8
CW_USEDEFAULT = -2147483648
FLASHW_STOP = 0
FLASHW_CAPTION = 1
FLASHW_TRAY = 2
FLASHW_ALL = FLASHW_CAPTION | FLASHW_TRAY
FLASHW_TIMER = 4
FLASHW_TIMERNOFG = 12

# winuser.h line 7963
DS_ABSALIGN = 1
DS_SYSMODAL = 2
DS_LOCALEDIT = 32
DS_SETFONT = 64
DS_MODALFRAME = 128
DS_NOIDLEMSG = 256
DS_SETFOREGROUND = 512
DS_3DLOOK = 4
DS_FIXEDSYS = 8
DS_NOFAILCREATE = 16
DS_CONTROL = 1024
DS_CENTER = 2048
DS_CENTERMOUSE = 4096
DS_CONTEXTHELP = 8192
DM_GETDEFID = WM_USER + 0
DM_SETDEFID = WM_USER + 1
DM_REPOSITION = WM_USER + 2
# PSM_PAGEINFO = (WM_USER+100)
# PSM_SHEETINFO = (WM_USER+101)
# PSI_SETACTIVE = 0x0001
# PSI_KILLACTIVE = 0x0002
# PSI_APPLY = 0x0003
# PSI_RESET = 0x0004
# PSI_HASHELP = 0x0005
# PSI_HELP = 0x0006
# PSI_CHANGED = 0x0001
# PSI_GUISTART = 0x0002
# PSI_REBOOT = 0x0003
# PSI_GETSIBLINGS = 0x0004
DC_HASDEFID = 21323
DLGC_WANTARROWS = 1
DLGC_WANTTAB = 2
DLGC_WANTALLKEYS = 4
DLGC_WANTMESSAGE = 4
DLGC_HASSETSEL = 8
DLGC_DEFPUSHBUTTON = 16
DLGC_UNDEFPUSHBUTTON = 32
DLGC_RADIOBUTTON = 64
DLGC_WANTCHARS = 128
DLGC_STATIC = 256
DLGC_BUTTON = 8192
LB_CTLCODE = 0
LB_OKAY = 0
LB_ERR = -1
LB_ERRSPACE = -2
LBN_ERRSPACE = -2
LBN_SELCHANGE = 1
LBN_DBLCLK = 2
LBN_SELCANCEL = 3
LBN_SETFOCUS = 4
LBN_KILLFOCUS = 5
LB_ADDSTRING = 384
LB_INSERTSTRING = 385
LB_DELETESTRING = 386
LB_SELITEMRANGEEX = 387
LB_RESETCONTENT = 388
LB_SETSEL = 389
LB_SETCURSEL = 390
LB_GETSEL = 391
LB_GETCURSEL = 392
LB_GETTEXT = 393
LB_GETTEXTLEN = 394
LB_GETCOUNT = 395
LB_SELECTSTRING = 396
LB_DIR = 397
LB_GETTOPINDEX = 398
LB_FINDSTRING = 399
LB_GETSELCOUNT = 400
LB_GETSELITEMS = 401
LB_SETTABSTOPS = 402
LB_GETHORIZONTALEXTENT = 403
LB_SETHORIZONTALEXTENT = 404
LB_SETCOLUMNWIDTH = 405
LB_ADDFILE = 406
LB_SETTOPINDEX = 407
LB_GETITEMRECT = 408
LB_GETITEMDATA = 409
LB_SETITEMDATA = 410
LB_SELITEMRANGE = 411
LB_SETANCHORINDEX = 412
LB_GETANCHORINDEX = 413
LB_SETCARETINDEX = 414
LB_GETCARETINDEX = 415
LB_SETITEMHEIGHT = 416
LB_GETITEMHEIGHT = 417
LB_FINDSTRINGEXACT = 418
LB_SETLOCALE = 421
LB_GETLOCALE = 422
LB_SETCOUNT = 423
LB_INITSTORAGE = 424
LB_ITEMFROMPOINT = 425
LB_MSGMAX = 432
LBS_NOTIFY = 1
LBS_SORT = 2
LBS_NOREDRAW = 4
LBS_MULTIPLESEL = 8
LBS_OWNERDRAWFIXED = 16
LBS_OWNERDRAWVARIABLE = 32
LBS_HASSTRINGS = 64
LBS_USETABSTOPS = 128
LBS_NOINTEGRALHEIGHT = 256
LBS_MULTICOLUMN = 512
LBS_WANTKEYBOARDINPUT = 1024
LBS_EXTENDEDSEL = 2048
LBS_DISABLENOSCROLL = 4096
LBS_NODATA = 8192
LBS_NOSEL = 16384
LBS_STANDARD = LBS_NOTIFY | LBS_SORT | WS_VSCROLL | WS_BORDER
CB_OKAY = 0
CB_ERR = -1
CB_ERRSPACE = -2
CBN_ERRSPACE = -1
CBN_SELCHANGE = 1
CBN_DBLCLK = 2
CBN_SETFOCUS = 3
CBN_KILLFOCUS = 4
CBN_EDITCHANGE = 5
CBN_EDITUPDATE = 6
CBN_DROPDOWN = 7
CBN_CLOSEUP = 8
CBN_SELENDOK = 9
CBN_SELENDCANCEL = 10
CBS_SIMPLE = 1
CBS_DROPDOWN = 2
CBS_DROPDOWNLIST = 3
CBS_OWNERDRAWFIXED = 16
CBS_OWNERDRAWVARIABLE = 32
CBS_AUTOHSCROLL = 64
CBS_OEMCONVERT = 128
CBS_SORT = 256
CBS_HASSTRINGS = 512
CBS_NOINTEGRALHEIGHT = 1024
CBS_DISABLENOSCROLL = 2048
CBS_UPPERCASE = 8192
CBS_LOWERCASE = 16384
CB_GETEDITSEL = 320
CB_LIMITTEXT = 321
CB_SETEDITSEL = 322
CB_ADDSTRING = 323
CB_DELETESTRING = 324
CB_DIR = 325
CB_GETCOUNT = 326
CB_GETCURSEL = 327
CB_GETLBTEXT = 328
CB_GETLBTEXTLEN = 329
CB_INSERTSTRING = 330
CB_RESETCONTENT = 331
CB_FINDSTRING = 332
CB_SELECTSTRING = 333
CB_SETCURSEL = 334
CB_SHOWDROPDOWN = 335
CB_GETITEMDATA = 336
CB_SETITEMDATA = 337
CB_GETDROPPEDCONTROLRECT = 338
CB_SETITEMHEIGHT = 339
CB_GETITEMHEIGHT = 340
CB_SETEXTENDEDUI = 341
CB_GETEXTENDEDUI = 342
CB_GETDROPPEDSTATE = 343
CB_FINDSTRINGEXACT = 344
CB_SETLOCALE = 345
CB_GETLOCALE = 346
CB_GETTOPINDEX = 347
CB_SETTOPINDEX = 348
CB_GETHORIZONTALEXTENT = 349
CB_SETHORIZONTALEXTENT = 350
CB_GETDROPPEDWIDTH = 351
CB_SETDROPPEDWIDTH = 352
CB_INITSTORAGE = 353
CB_MSGMAX = 354
SBS_HORZ = 0
SBS_VERT = 1
SBS_TOPALIGN = 2
SBS_LEFTALIGN = 2
SBS_BOTTOMALIGN = 4
SBS_RIGHTALIGN = 4
SBS_SIZEBOXTOPLEFTALIGN = 2
SBS_SIZEBOXBOTTOMRIGHTALIGN = 4
SBS_SIZEBOX = 8
SBS_SIZEGRIP = 16
SBM_SETPOS = 224
SBM_GETPOS = 225
SBM_SETRANGE = 226
SBM_SETRANGEREDRAW = 230
SBM_GETRANGE = 227
SBM_ENABLE_ARROWS = 228
SBM_SETSCROLLINFO = 233
SBM_GETSCROLLINFO = 234
SIF_RANGE = 1
SIF_PAGE = 2
SIF_POS = 4
SIF_DISABLENOSCROLL = 8
SIF_TRACKPOS = 16
SIF_ALL = SIF_RANGE | SIF_PAGE | SIF_POS | SIF_TRACKPOS
MDIS_ALLCHILDSTYLES = 1
MDITILE_VERTICAL = 0
MDITILE_HORIZONTAL = 1
MDITILE_SKIPDISABLED = 2
MDITILE_ZORDER = 4

IMC_GETCANDIDATEPOS = 7
IMC_SETCANDIDATEPOS = 8
IMC_GETCOMPOSITIONFONT = 9
IMC_SETCOMPOSITIONFONT = 10
IMC_GETCOMPOSITIONWINDOW = 11
IMC_SETCOMPOSITIONWINDOW = 12
IMC_GETSTATUSWINDOWPOS = 15
IMC_SETSTATUSWINDOWPOS = 16
IMC_CLOSESTATUSWINDOW = 33
IMC_OPENSTATUSWINDOW = 34
# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
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

SERVICE_KERNEL_DRIVER = 1
SERVICE_FILE_SYSTEM_DRIVER = 2
SERVICE_ADAPTER = 4
SERVICE_RECOGNIZER_DRIVER = 8
SERVICE_DRIVER = (
    SERVICE_KERNEL_DRIVER | SERVICE_FILE_SYSTEM_DRIVER | SERVICE_RECOGNIZER_DRIVER
)
SERVICE_WIN32_OWN_PROCESS = 16
SERVICE_WIN32_SHARE_PROCESS = 32
SERVICE_WIN32 = SERVICE_WIN32_OWN_PROCESS | SERVICE_WIN32_SHARE_PROCESS
SERVICE_INTERACTIVE_PROCESS = 256
SERVICE_TYPE_ALL = (
    SERVICE_WIN32 | SERVICE_ADAPTER | SERVICE_DRIVER | SERVICE_INTERACTIVE_PROCESS
)
SERVICE_BOOT_START = 0
SERVICE_SYSTEM_START = 1
SERVICE_AUTO_START = 2
SERVICE_DEMAND_START = 3
SERVICE_DISABLED = 4
SERVICE_ERROR_IGNORE = 0
SERVICE_ERROR_NORMAL = 1
SERVICE_ERROR_SEVERE = 2
SERVICE_ERROR_CRITICAL = 3
TAPE_ERASE_SHORT = 0
TAPE_ERASE_LONG = 1
TAPE_LOAD = 0
TAPE_UNLOAD = 1
TAPE_TENSION = 2
TAPE_LOCK = 3
TAPE_UNLOCK = 4
TAPE_FORMAT = 5
TAPE_SETMARKS = 0
TAPE_FILEMARKS = 1
TAPE_SHORT_FILEMARKS = 2
TAPE_LONG_FILEMARKS = 3
TAPE_ABSOLUTE_POSITION = 0
TAPE_LOGICAL_POSITION = 1
TAPE_PSEUDO_LOGICAL_POSITION = 2
TAPE_REWIND = 0
TAPE_ABSOLUTE_BLOCK = 1
TAPE_LOGICAL_BLOCK = 2
TAPE_PSEUDO_LOGICAL_BLOCK = 3
TAPE_SPACE_END_OF_DATA = 4
TAPE_SPACE_RELATIVE_BLOCKS = 5
TAPE_SPACE_FILEMARKS = 6
TAPE_SPACE_SEQUENTIAL_FMKS = 7
TAPE_SPACE_SETMARKS = 8
TAPE_SPACE_SEQUENTIAL_SMKS = 9
TAPE_DRIVE_FIXED = 1
TAPE_DRIVE_SELECT = 2
TAPE_DRIVE_INITIATOR = 4
TAPE_DRIVE_ERASE_SHORT = 16
TAPE_DRIVE_ERASE_LONG = 32
TAPE_DRIVE_ERASE_BOP_ONLY = 64
TAPE_DRIVE_ERASE_IMMEDIATE = 128
TAPE_DRIVE_TAPE_CAPACITY = 256
TAPE_DRIVE_TAPE_REMAINING = 512
TAPE_DRIVE_FIXED_BLOCK = 1024
TAPE_DRIVE_VARIABLE_BLOCK = 2048
TAPE_DRIVE_WRITE_PROTECT = 4096
TAPE_DRIVE_EOT_WZ_SIZE = 8192
TAPE_DRIVE_ECC = 65536
TAPE_DRIVE_COMPRESSION = 131072
TAPE_DRIVE_PADDING = 262144
TAPE_DRIVE_REPORT_SMKS = 524288
TAPE_DRIVE_GET_ABSOLUTE_BLK = 1048576
TAPE_DRIVE_GET_LOGICAL_BLK = 2097152
TAPE_DRIVE_SET_EOT_WZ_SIZE = 4194304
TAPE_DRIVE_LOAD_UNLOAD = -2147483647
TAPE_DRIVE_TENSION = -2147483646
TAPE_DRIVE_LOCK_UNLOCK = -2147483644
TAPE_DRIVE_REWIND_IMMEDIATE = -2147483640
TAPE_DRIVE_SET_BLOCK_SIZE = -2147483632
TAPE_DRIVE_LOAD_UNLD_IMMED = -2147483616
TAPE_DRIVE_TENSION_IMMED = -2147483584
TAPE_DRIVE_LOCK_UNLK_IMMED = -2147483520
TAPE_DRIVE_SET_ECC = -2147483392
TAPE_DRIVE_SET_COMPRESSION = -2147483136
TAPE_DRIVE_SET_PADDING = -2147482624
TAPE_DRIVE_SET_REPORT_SMKS = -2147481600
TAPE_DRIVE_ABSOLUTE_BLK = -2147479552
TAPE_DRIVE_ABS_BLK_IMMED = -2147475456
TAPE_DRIVE_LOGICAL_BLK = -2147467264
TAPE_DRIVE_LOG_BLK_IMMED = -2147450880
TAPE_DRIVE_END_OF_DATA = -2147418112
TAPE_DRIVE_RELATIVE_BLKS = -2147352576
TAPE_DRIVE_FILEMARKS = -2147221504
TAPE_DRIVE_SEQUENTIAL_FMKS = -2146959360
TAPE_DRIVE_SETMARKS = -2146435072
TAPE_DRIVE_SEQUENTIAL_SMKS = -2145386496
TAPE_DRIVE_REVERSE_POSITION = -2143289344
TAPE_DRIVE_SPACE_IMMEDIATE = -2139095040
TAPE_DRIVE_WRITE_SETMARKS = -2130706432
TAPE_DRIVE_WRITE_FILEMARKS = -2113929216
TAPE_DRIVE_WRITE_SHORT_FMKS = -2080374784
TAPE_DRIVE_WRITE_LONG_FMKS = -2013265920
TAPE_DRIVE_WRITE_MARK_IMMED = -1879048192
TAPE_DRIVE_FORMAT = -1610612736
TAPE_DRIVE_FORMAT_IMMEDIATE = -1073741824
TAPE_FIXED_PARTITIONS = 0
TAPE_SELECT_PARTITIONS = 1
TAPE_INITIATOR_PARTITIONS = 2
# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.

APPLICATION_ERROR_MASK = 536870912
ERROR_SEVERITY_SUCCESS = 0
ERROR_SEVERITY_INFORMATIONAL = 1073741824
ERROR_SEVERITY_WARNING = -2147483648
ERROR_SEVERITY_ERROR = -1073741824
MINCHAR = 128
MAXCHAR = 127
MINSHORT = 32768
MAXSHORT = 32767
MINLONG = -2147483648
MAXLONG = 2147483647
MAXBYTE = 255
MAXWORD = 65535
MAXDWORD = -1
LANG_NEUTRAL = 0
LANG_BULGARIAN = 2
LANG_CHINESE = 4
LANG_CROATIAN = 26
LANG_CZECH = 5
LANG_DANISH = 6
LANG_DUTCH = 19
LANG_ENGLISH = 9
LANG_FINNISH = 11
LANG_FRENCH = 12
LANG_GERMAN = 7
LANG_GREEK = 8
LANG_HUNGARIAN = 14
LANG_ICELANDIC = 15
LANG_ITALIAN = 16
LANG_JAPANESE = 17
LANG_KOREAN = 18
LANG_NORWEGIAN = 20
LANG_POLISH = 21
LANG_PORTUGUESE = 22
LANG_ROMANIAN = 24
LANG_RUSSIAN = 25
LANG_SLOVAK = 27
LANG_SLOVENIAN = 36
LANG_SPANISH = 10
LANG_SWEDISH = 29
LANG_TURKISH = 31
SUBLANG_NEUTRAL = 0
SUBLANG_DEFAULT = 1
SUBLANG_SYS_DEFAULT = 2
SUBLANG_CHINESE_TRADITIONAL = 1
SUBLANG_CHINESE_SIMPLIFIED = 2
SUBLANG_CHINESE_HONGKONG = 3
SUBLANG_CHINESE_SINGAPORE = 4
SUBLANG_DUTCH = 1
SUBLANG_DUTCH_BELGIAN = 2
SUBLANG_ENGLISH_US = 1
SUBLANG_ENGLISH_UK = 2
SUBLANG_ENGLISH_AUS = 3
SUBLANG_ENGLISH_CAN = 4
SUBLANG_ENGLISH_NZ = 5
SUBLANG_ENGLISH_EIRE = 6
SUBLANG_FRENCH = 1
SUBLANG_FRENCH_BELGIAN = 2
SUBLANG_FRENCH_CANADIAN = 3
SUBLANG_FRENCH_SWISS = 4
SUBLANG_GERMAN = 1
SUBLANG_GERMAN_SWISS = 2
SUBLANG_GERMAN_AUSTRIAN = 3
SUBLANG_ITALIAN = 1
SUBLANG_ITALIAN_SWISS = 2
SUBLANG_NORWEGIAN_BOKMAL = 1
SUBLANG_NORWEGIAN_NYNORSK = 2
SUBLANG_PORTUGUESE = 2
SUBLANG_PORTUGUESE_BRAZILIAN = 1
SUBLANG_SPANISH = 1
SUBLANG_SPANISH_MEXICAN = 2
SUBLANG_SPANISH_MODERN = 3
SORT_DEFAULT = 0
SORT_JAPANESE_XJIS = 0
SORT_JAPANESE_UNICODE = 1
SORT_CHINESE_BIG5 = 0
SORT_CHINESE_UNICODE = 1
SORT_KOREAN_KSC = 0
SORT_KOREAN_UNICODE = 1


def PRIMARYLANGID(lgid):
    return (lgid) & 1023


def SUBLANGID(lgid):
    return (lgid) >> 10


NLS_VALID_LOCALE_MASK = 1048575
CONTEXT_PORTABLE_32BIT = 1048576
CONTEXT_ALPHA = 131072
SIZE_OF_80387_REGISTERS = 80
CONTEXT_CONTROL = 1
CONTEXT_FLOATING_POINT = 2
CONTEXT_INTEGER = 4
CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_FLOATING_POINT | CONTEXT_INTEGER
PROCESS_TERMINATE = 1
PROCESS_CREATE_THREAD = 2
PROCESS_VM_OPERATION = 8
PROCESS_VM_READ = 16
PROCESS_VM_WRITE = 32
PROCESS_DUP_HANDLE = 64
PROCESS_CREATE_PROCESS = 128
PROCESS_SET_QUOTA = 256
PROCESS_SET_INFORMATION = 512
PROCESS_QUERY_INFORMATION = 1024
PROCESS_SUSPEND_RESUME = 2048
PROCESS_QUERY_LIMITED_INFORMATION = 4096
PROCESS_SET_LIMITED_INFORMATION = 8192
PROCESS_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 4095
THREAD_TERMINATE = 1
THREAD_SUSPEND_RESUME = 2
THREAD_GET_CONTEXT = 8
THREAD_SET_CONTEXT = 16
THREAD_SET_INFORMATION = 32
THREAD_QUERY_INFORMATION = 64
THREAD_SET_THREAD_TOKEN = 128
THREAD_IMPERSONATE = 256
THREAD_DIRECT_IMPERSONATION = 512
THREAD_SET_LIMITED_INFORMATION = 1024
THREAD_QUERY_LIMITED_INFORMATION = 2048
THREAD_RESUME = 4096
TLS_MINIMUM_AVAILABLE = 64
EVENT_MODIFY_STATE = 2
MUTANT_QUERY_STATE = 1
SEMAPHORE_MODIFY_STATE = 2
TIME_ZONE_ID_UNKNOWN = 0
TIME_ZONE_ID_STANDARD = 1
TIME_ZONE_ID_DAYLIGHT = 2
PROCESSOR_INTEL_386 = 386
PROCESSOR_INTEL_486 = 486
PROCESSOR_INTEL_PENTIUM = 586
PROCESSOR_INTEL_860 = 860
PROCESSOR_MIPS_R2000 = 2000
PROCESSOR_MIPS_R3000 = 3000
PROCESSOR_MIPS_R4000 = 4000
PROCESSOR_ALPHA_21064 = 21064
PROCESSOR_PPC_601 = 601
PROCESSOR_PPC_603 = 603
PROCESSOR_PPC_604 = 604
PROCESSOR_PPC_620 = 620
SECTION_QUERY = 1
SECTION_MAP_WRITE = 2
SECTION_MAP_READ = 4
SECTION_MAP_EXECUTE = 8
SECTION_EXTEND_SIZE = 16
PAGE_NOACCESS = 1
PAGE_READONLY = 2
PAGE_READWRITE = 4
PAGE_WRITECOPY = 8
PAGE_EXECUTE = 16
PAGE_EXECUTE_READ = 32
PAGE_EXECUTE_READWRITE = 64
PAGE_EXECUTE_WRITECOPY = 128
PAGE_GUARD = 256
PAGE_NOCACHE = 512
MEM_COMMIT = 4096
MEM_RESERVE = 8192
MEM_DECOMMIT = 16384
MEM_RELEASE = 32768
MEM_FREE = 65536
MEM_PRIVATE = 131072
MEM_MAPPED = 262144
MEM_TOP_DOWN = 1048576

# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
SEC_FILE = 8388608
SEC_IMAGE = 16777216
SEC_RESERVE = 67108864
SEC_COMMIT = 134217728
SEC_NOCACHE = 268435456
MEM_IMAGE = SEC_IMAGE
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
FILE_ATTRIBUTE_READONLY = 1
FILE_ATTRIBUTE_HIDDEN = 2
FILE_ATTRIBUTE_SYSTEM = 4
FILE_ATTRIBUTE_DIRECTORY = 16
FILE_ATTRIBUTE_ARCHIVE = 32
FILE_ATTRIBUTE_DEVICE = 64
FILE_ATTRIBUTE_NORMAL = 128
FILE_ATTRIBUTE_TEMPORARY = 256
FILE_ATTRIBUTE_SPARSE_FILE = 512
FILE_ATTRIBUTE_REPARSE_POINT = 1024
FILE_ATTRIBUTE_COMPRESSED = 2048
FILE_ATTRIBUTE_OFFLINE = 4096
FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 8192
FILE_ATTRIBUTE_ENCRYPTED = 16384
FILE_ATTRIBUTE_VIRTUAL = 65536
# These FILE_ATTRIBUTE_* flags  are apparently old definitions from Windows 95
# and conflict with current values above - but they live on for b/w compat...
FILE_ATTRIBUTE_ATOMIC_WRITE = 512
FILE_ATTRIBUTE_XACTION_WRITE = 1024

FILE_NOTIFY_CHANGE_FILE_NAME = 1
FILE_NOTIFY_CHANGE_DIR_NAME = 2
FILE_NOTIFY_CHANGE_ATTRIBUTES = 4
FILE_NOTIFY_CHANGE_SIZE = 8
FILE_NOTIFY_CHANGE_LAST_WRITE = 16
FILE_NOTIFY_CHANGE_SECURITY = 256
FILE_CASE_SENSITIVE_SEARCH = 1
FILE_CASE_PRESERVED_NAMES = 2
FILE_FILE_COMPRESSION = 16
FILE_NAMED_STREAMS = 262144
FILE_PERSISTENT_ACLS = 0x00000008
FILE_READ_ONLY_VOLUME = 0x00080000
FILE_SEQUENTIAL_WRITE_ONCE = 0x00100000
FILE_SUPPORTS_ENCRYPTION = 0x00020000
FILE_SUPPORTS_EXTENDED_ATTRIBUTES = 0x00800000
FILE_SUPPORTS_HARD_LINKS = 0x00400000
FILE_SUPPORTS_OBJECT_IDS = 0x00010000
FILE_SUPPORTS_OPEN_BY_FILE_ID = 0x01000000
FILE_SUPPORTS_REPARSE_POINTS = 0x00000080
FILE_SUPPORTS_SPARSE_FILES = 0x00000040
FILE_SUPPORTS_TRANSACTIONS = 0x00200000
FILE_SUPPORTS_USN_JOURNAL = 0x02000000
FILE_UNICODE_ON_DISK = 0x00000004
FILE_VOLUME_QUOTAS = 0x00000020
FILE_VOLUME_IS_COMPRESSED = 32768
IO_COMPLETION_MODIFY_STATE = 2
DUPLICATE_CLOSE_SOURCE = 1
DUPLICATE_SAME_ACCESS = 2
SID_MAX_SUB_AUTHORITIES = 15
SECURITY_NULL_RID = 0
SECURITY_WORLD_RID = 0
SECURITY_LOCAL_RID = 0x00000000
SECURITY_CREATOR_OWNER_RID = 0
SECURITY_CREATOR_GROUP_RID = 1
SECURITY_DIALUP_RID = 1
SECURITY_NETWORK_RID = 2
SECURITY_BATCH_RID = 3
SECURITY_INTERACTIVE_RID = 4
SECURITY_SERVICE_RID = 6
SECURITY_ANONYMOUS_LOGON_RID = 7
SECURITY_LOGON_IDS_RID = 5
SECURITY_LOGON_IDS_RID_COUNT = 3
SECURITY_LOCAL_SYSTEM_RID = 18
SECURITY_NT_NON_UNIQUE = 21
SECURITY_BUILTIN_DOMAIN_RID = 32
DOMAIN_USER_RID_ADMIN = 500
DOMAIN_USER_RID_GUEST = 501
DOMAIN_GROUP_RID_ADMINS = 512
DOMAIN_GROUP_RID_USERS = 513
DOMAIN_GROUP_RID_GUESTS = 514
DOMAIN_ALIAS_RID_ADMINS = 544
DOMAIN_ALIAS_RID_USERS = 545
DOMAIN_ALIAS_RID_GUESTS = 546
DOMAIN_ALIAS_RID_POWER_USERS = 547
DOMAIN_ALIAS_RID_ACCOUNT_OPS = 548
DOMAIN_ALIAS_RID_SYSTEM_OPS = 549
DOMAIN_ALIAS_RID_PRINT_OPS = 550
DOMAIN_ALIAS_RID_BACKUP_OPS = 551
DOMAIN_ALIAS_RID_REPLICATOR = 552
SE_GROUP_MANDATORY = 1
SE_GROUP_ENABLED_BY_DEFAULT = 2
SE_GROUP_ENABLED = 4
SE_GROUP_OWNER = 8
SE_GROUP_LOGON_ID = -1073741824
ACL_REVISION = 2
ACL_REVISION1 = 1
ACL_REVISION2 = 2
ACCESS_ALLOWED_ACE_TYPE = 0
ACCESS_DENIED_ACE_TYPE = 1
SYSTEM_AUDIT_ACE_TYPE = 2
SYSTEM_ALARM_ACE_TYPE = 3
OBJECT_INHERIT_ACE = 1
CONTAINER_INHERIT_ACE = 2
NO_PROPAGATE_INHERIT_ACE = 4
INHERIT_ONLY_ACE = 8
VALID_INHERIT_FLAGS = 15
SUCCESSFUL_ACCESS_ACE_FLAG = 64
FAILED_ACCESS_ACE_FLAG = 128
SECURITY_DESCRIPTOR_REVISION = 1
SECURITY_DESCRIPTOR_REVISION1 = 1
SECURITY_DESCRIPTOR_MIN_LENGTH = 20
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

TOKEN_ASSIGN_PRIMARY = 1
TOKEN_DUPLICATE = 2
TOKEN_IMPERSONATE = 4
TOKEN_QUERY = 8
TOKEN_QUERY_SOURCE = 16
TOKEN_ADJUST_PRIVILEGES = 32
TOKEN_ADJUST_GROUPS = 64
TOKEN_ADJUST_DEFAULT = 128
TOKEN_ADJUST_SESSIONID = 256
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
    | TOKEN_ADJUST_SESSIONID
)
TOKEN_READ = STANDARD_RIGHTS_READ | TOKEN_QUERY
TOKEN_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)
TOKEN_EXECUTE = STANDARD_RIGHTS_EXECUTE
TOKEN_SOURCE_LENGTH = 8

KEY_QUERY_VALUE = 1
KEY_SET_VALUE = 2
KEY_CREATE_SUB_KEY = 4
KEY_ENUMERATE_SUB_KEYS = 8
KEY_NOTIFY = 16
KEY_CREATE_LINK = 32
KEY_WOW64_32KEY = 512
KEY_WOW64_64KEY = 256
KEY_WOW64_RES = 768
KEY_READ = (
    STANDARD_RIGHTS_READ | KEY_QUERY_VALUE | KEY_ENUMERATE_SUB_KEYS | KEY_NOTIFY
) & (~SYNCHRONIZE)
KEY_WRITE = (STANDARD_RIGHTS_WRITE | KEY_SET_VALUE | KEY_CREATE_SUB_KEY) & (
    ~SYNCHRONIZE
)
KEY_EXECUTE = (KEY_READ) & (~SYNCHRONIZE)
KEY_ALL_ACCESS = (
    STANDARD_RIGHTS_ALL
    | KEY_QUERY_VALUE
    | KEY_SET_VALUE
    | KEY_CREATE_SUB_KEY
    | KEY_ENUMERATE_SUB_KEYS
    | KEY_NOTIFY
    | KEY_CREATE_LINK
) & (~SYNCHRONIZE)
REG_NOTIFY_CHANGE_ATTRIBUTES = 2
REG_NOTIFY_CHANGE_SECURITY = 8
REG_NONE = 0  # No value type
REG_SZ = 1  # Unicode nul terminated string
REG_EXPAND_SZ = 2  # Unicode nul terminated string
# (with environment variable references)
REG_BINARY = 3  # Free form binary
REG_DWORD = 4  # 32-bit number
REG_DWORD_LITTLE_ENDIAN = 4  # 32-bit number (same as REG_DWORD)
REG_DWORD_BIG_ENDIAN = 5  # 32-bit number
REG_LINK = 6  # Symbolic Link (unicode)
REG_MULTI_SZ = 7  # Multiple Unicode strings
REG_RESOURCE_LIST = 8  # Resource list in the resource map
REG_FULL_RESOURCE_DESCRIPTOR = 9  # Resource list in the hardware description
REG_RESOURCE_REQUIREMENTS_LIST = 10
REG_QWORD = 11  # 64-bit number
REG_QWORD_LITTLE_ENDIAN = 11  # 64-bit number (same as REG_QWORD)


# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
# Included from string.h
_NLSCMPERROR = 2147483647
NULL = 0
HEAP_NO_SERIALIZE = 1
HEAP_GROWABLE = 2
HEAP_GENERATE_EXCEPTIONS = 4
HEAP_ZERO_MEMORY = 8
HEAP_REALLOC_IN_PLACE_ONLY = 16
HEAP_TAIL_CHECKING_ENABLED = 32
HEAP_FREE_CHECKING_ENABLED = 64
HEAP_DISABLE_COALESCE_ON_FREE = 128
IS_TEXT_UNICODE_ASCII16 = 1
IS_TEXT_UNICODE_REVERSE_ASCII16 = 16
IS_TEXT_UNICODE_STATISTICS = 2
IS_TEXT_UNICODE_REVERSE_STATISTICS = 32
IS_TEXT_UNICODE_CONTROLS = 4
IS_TEXT_UNICODE_REVERSE_CONTROLS = 64
IS_TEXT_UNICODE_SIGNATURE = 8
IS_TEXT_UNICODE_REVERSE_SIGNATURE = 128
IS_TEXT_UNICODE_ILLEGAL_CHARS = 256
IS_TEXT_UNICODE_ODD_LENGTH = 512
IS_TEXT_UNICODE_DBCS_LEADBYTE = 1024
IS_TEXT_UNICODE_NULL_BYTES = 4096
IS_TEXT_UNICODE_UNICODE_MASK = 15
IS_TEXT_UNICODE_REVERSE_MASK = 240
IS_TEXT_UNICODE_NOT_UNICODE_MASK = 3840
IS_TEXT_UNICODE_NOT_ASCII_MASK = 61440
COMPRESSION_FORMAT_NONE = 0
COMPRESSION_FORMAT_DEFAULT = 1
COMPRESSION_FORMAT_LZNT1 = 2
COMPRESSION_ENGINE_STANDARD = 0
COMPRESSION_ENGINE_MAXIMUM = 256
MESSAGE_RESOURCE_UNICODE = 1
RTL_CRITSECT_TYPE = 0
RTL_RESOURCE_TYPE = 1
DLL_PROCESS_ATTACH = 1
DLL_THREAD_ATTACH = 2
DLL_THREAD_DETACH = 3
DLL_PROCESS_DETACH = 0
EVENTLOG_SEQUENTIAL_READ = 0x0001
EVENTLOG_SEEK_READ = 0x0002
EVENTLOG_FORWARDS_READ = 0x0004
EVENTLOG_BACKWARDS_READ = 0x0008
EVENTLOG_SUCCESS = 0x0000
EVENTLOG_ERROR_TYPE = 1
EVENTLOG_WARNING_TYPE = 2
EVENTLOG_INFORMATION_TYPE = 4
EVENTLOG_AUDIT_SUCCESS = 8
EVENTLOG_AUDIT_FAILURE = 16
EVENTLOG_START_PAIRED_EVENT = 1
EVENTLOG_END_PAIRED_EVENT = 2
EVENTLOG_END_ALL_PAIRED_EVENTS = 4
EVENTLOG_PAIRED_EVENT_ACTIVE = 8
EVENTLOG_PAIRED_EVENT_INACTIVE = 16
# Generated by h2py from \msvc20\include\winnt.h
# hacked and split by mhammond.
OWNER_SECURITY_INFORMATION = 0x00000001
GROUP_SECURITY_INFORMATION = 0x00000002
DACL_SECURITY_INFORMATION = 0x00000004
SACL_SECURITY_INFORMATION = 0x00000008
IMAGE_SIZEOF_FILE_HEADER = 20
IMAGE_FILE_MACHINE_UNKNOWN = 0
IMAGE_NUMBEROF_DIRECTORY_ENTRIES = 16
IMAGE_SIZEOF_ROM_OPTIONAL_HEADER = 56
IMAGE_SIZEOF_STD_OPTIONAL_HEADER = 28
IMAGE_SIZEOF_NT_OPTIONAL_HEADER = 224
IMAGE_NT_OPTIONAL_HDR_MAGIC = 267
IMAGE_ROM_OPTIONAL_HDR_MAGIC = 263
IMAGE_SIZEOF_SHORT_NAME = 8
IMAGE_SIZEOF_SECTION_HEADER = 40
IMAGE_SIZEOF_SYMBOL = 18
IMAGE_SYM_CLASS_NULL = 0
IMAGE_SYM_CLASS_AUTOMATIC = 1
IMAGE_SYM_CLASS_EXTERNAL = 2
IMAGE_SYM_CLASS_STATIC = 3
IMAGE_SYM_CLASS_REGISTER = 4
IMAGE_SYM_CLASS_EXTERNAL_DEF = 5
IMAGE_SYM_CLASS_LABEL = 6
IMAGE_SYM_CLASS_UNDEFINED_LABEL = 7
IMAGE_SYM_CLASS_MEMBER_OF_STRUCT = 8
IMAGE_SYM_CLASS_ARGUMENT = 9
IMAGE_SYM_CLASS_STRUCT_TAG = 10
IMAGE_SYM_CLASS_MEMBER_OF_UNION = 11
IMAGE_SYM_CLASS_UNION_TAG = 12
IMAGE_SYM_CLASS_TYPE_DEFINITION = 13
IMAGE_SYM_CLASS_UNDEFINED_STATIC = 14
IMAGE_SYM_CLASS_ENUM_TAG = 15
IMAGE_SYM_CLASS_MEMBER_OF_ENUM = 16
IMAGE_SYM_CLASS_REGISTER_PARAM = 17
IMAGE_SYM_CLASS_BIT_FIELD = 18
IMAGE_SYM_CLASS_BLOCK = 100
IMAGE_SYM_CLASS_FUNCTION = 101
IMAGE_SYM_CLASS_END_OF_STRUCT = 102
IMAGE_SYM_CLASS_FILE = 103
IMAGE_SYM_CLASS_SECTION = 104
IMAGE_SYM_CLASS_WEAK_EXTERNAL = 105
N_BTMASK = 15
N_TMASK = 48
N_TMASK1 = 192
N_TMASK2 = 240
N_BTSHFT = 4
N_TSHIFT = 2
IMAGE_SIZEOF_AUX_SYMBOL = 18
IMAGE_COMDAT_SELECT_NODUPLICATES = 1
IMAGE_COMDAT_SELECT_ANY = 2
IMAGE_COMDAT_SELECT_SAME_SIZE = 3
IMAGE_COMDAT_SELECT_EXACT_MATCH = 4
IMAGE_COMDAT_SELECT_ASSOCIATIVE = 5
IMAGE_WEAK_EXTERN_SEARCH_NOLIBRARY = 1
IMAGE_WEAK_EXTERN_SEARCH_LIBRARY = 2
IMAGE_WEAK_EXTERN_SEARCH_ALIAS = 3
IMAGE_SIZEOF_RELOCATION = 10
IMAGE_REL_I386_SECTION = 10
IMAGE_REL_I386_SECREL = 11
IMAGE_REL_MIPS_REFHALF = 1
IMAGE_REL_MIPS_REFWORD = 2
IMAGE_REL_MIPS_JMPADDR = 3
IMAGE_REL_MIPS_REFHI = 4
IMAGE_REL_MIPS_REFLO = 5
IMAGE_REL_MIPS_GPREL = 6
IMAGE_REL_MIPS_LITERAL = 7
IMAGE_REL_MIPS_SECTION = 10
IMAGE_REL_MIPS_SECREL = 11
IMAGE_REL_MIPS_REFWORDNB = 34
IMAGE_REL_MIPS_PAIR = 37
IMAGE_REL_ALPHA_ABSOLUTE = 0
IMAGE_REL_ALPHA_REFLONG = 1
IMAGE_REL_ALPHA_REFQUAD = 2
IMAGE_REL_ALPHA_GPREL32 = 3
IMAGE_REL_ALPHA_LITERAL = 4
IMAGE_REL_ALPHA_LITUSE = 5
IMAGE_REL_ALPHA_GPDISP = 6
IMAGE_REL_ALPHA_BRADDR = 7
IMAGE_REL_ALPHA_HINT = 8
IMAGE_REL_ALPHA_INLINE_REFLONG = 9
IMAGE_REL_ALPHA_REFHI = 10
IMAGE_REL_ALPHA_REFLO = 11
IMAGE_REL_ALPHA_PAIR = 12
IMAGE_REL_ALPHA_MATCH = 13
IMAGE_REL_ALPHA_SECTION = 14
IMAGE_REL_ALPHA_SECREL = 15
IMAGE_REL_ALPHA_REFLONGNB = 16
IMAGE_SIZEOF_BASE_RELOCATION = 8
IMAGE_REL_BASED_ABSOLUTE = 0
IMAGE_REL_BASED_HIGH = 1
IMAGE_REL_BASED_LOW = 2
IMAGE_REL_BASED_HIGHLOW = 3
IMAGE_REL_BASED_HIGHADJ = 4
IMAGE_REL_BASED_MIPS_JMPADDR = 5
IMAGE_SIZEOF_LINENUMBER = 6
IMAGE_ARCHIVE_START_SIZE = 8
IMAGE_ARCHIVE_START = "!<arch>\n"
IMAGE_ARCHIVE_END = "`\n"
IMAGE_ARCHIVE_PAD = "\n"
IMAGE_ARCHIVE_LINKER_MEMBER = "/               "
IMAGE_ARCHIVE_LONGNAMES_MEMBER = "//              "
IMAGE_SIZEOF_ARCHIVE_MEMBER_HDR = 60
IMAGE_ORDINAL_FLAG = -2147483648


def IMAGE_SNAP_BY_ORDINAL(Ordinal):
    return (Ordinal & IMAGE_ORDINAL_FLAG) != 0


def IMAGE_ORDINAL(Ordinal):
    return Ordinal & 65535


IMAGE_RESOURCE_NAME_IS_STRING = -2147483648
IMAGE_RESOURCE_DATA_IS_DIRECTORY = -2147483648
IMAGE_DEBUG_TYPE_UNKNOWN = 0
IMAGE_DEBUG_TYPE_COFF = 1
IMAGE_DEBUG_TYPE_CODEVIEW = 2
IMAGE_DEBUG_TYPE_FPO = 3
IMAGE_DEBUG_TYPE_MISC = 4
IMAGE_DEBUG_TYPE_EXCEPTION = 5
IMAGE_DEBUG_TYPE_FIXUP = 6
IMAGE_DEBUG_TYPE_OMAP_TO_SRC = 7
IMAGE_DEBUG_TYPE_OMAP_FROM_SRC = 8
FRAME_FPO = 0
FRAME_TRAP = 1
FRAME_TSS = 2
SIZEOF_RFPO_DATA = 16
IMAGE_DEBUG_MISC_EXENAME = 1
IMAGE_SEPARATE_DEBUG_SIGNATURE = 18756
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
NEWFRAME = 1
ABORTDOC = 2
NEXTBAND = 3
SETCOLORTABLE = 4
GETCOLORTABLE = 5
FLUSHOUTPUT = 6
DRAFTMODE = 7
QUERYESCSUPPORT = 8
SETABORTPROC = 9
STARTDOC = 10
ENDDOC = 11
GETPHYSPAGESIZE = 12
GETPRINTINGOFFSET = 13
GETSCALINGFACTOR = 14
MFCOMMENT = 15
GETPENWIDTH = 16
SETCOPYCOUNT = 17
SELECTPAPERSOURCE = 18
DEVICEDATA = 19
PASSTHROUGH = 19
GETTECHNOLGY = 20
GETTECHNOLOGY = 20
SETLINECAP = 21
SETLINEJOIN = 22
SETMITERLIMIT = 23
BANDINFO = 24
DRAWPATTERNRECT = 25
GETVECTORPENSIZE = 26
GETVECTORBRUSHSIZE = 27
ENABLEDUPLEX = 28
GETSETPAPERBINS = 29
GETSETPRINTORIENT = 30
ENUMPAPERBINS = 31
SETDIBSCALING = 32
EPSPRINTING = 33
ENUMPAPERMETRICS = 34
GETSETPAPERMETRICS = 35
POSTSCRIPT_DATA = 37
POSTSCRIPT_IGNORE = 38
MOUSETRAILS = 39
GETDEVICEUNITS = 42
GETEXTENDEDTEXTMETRICS = 256
GETEXTENTTABLE = 257
GETPAIRKERNTABLE = 258
GETTRACKKERNTABLE = 259
EXTTEXTOUT = 512
GETFACENAME = 513
DOWNLOADFACE = 514
ENABLERELATIVEWIDTHS = 768
ENABLEPAIRKERNING = 769
SETKERNTRACK = 770
SETALLJUSTVALUES = 771
SETCHARSET = 772
STRETCHBLT = 2048
GETSETSCREENPARAMS = 3072
BEGIN_PATH = 4096
CLIP_TO_PATH = 4097
END_PATH = 4098
EXT_DEVICE_CAPS = 4099
RESTORE_CTM = 4100
SAVE_CTM = 4101
SET_ARC_DIRECTION = 4102
SET_BACKGROUND_COLOR = 4103
SET_POLY_MODE = 4104
SET_SCREEN_ANGLE = 4105
SET_SPREAD = 4106
TRANSFORM_CTM = 4107
SET_CLIP_BOX = 4108
SET_BOUNDS = 4109
SET_MIRROR_MODE = 4110
OPENCHANNEL = 4110
DOWNLOADHEADER = 4111
CLOSECHANNEL = 4112
POSTSCRIPT_PASSTHROUGH = 4115
ENCAPSULATED_POSTSCRIPT = 4116
SP_NOTREPORTED = 16384
SP_ERROR = -1
SP_APPABORT = -2
SP_USERABORT = -3
SP_OUTOFDISK = -4
SP_OUTOFMEMORY = -5
PR_JOBSTATUS = 0

## GDI object types
OBJ_PEN = 1
OBJ_BRUSH = 2
OBJ_DC = 3
OBJ_METADC = 4
OBJ_PAL = 5
OBJ_FONT = 6
OBJ_BITMAP = 7
OBJ_REGION = 8
OBJ_METAFILE = 9
OBJ_MEMDC = 10
OBJ_EXTPEN = 11
OBJ_ENHMETADC = 12
OBJ_ENHMETAFILE = 13
OBJ_COLORSPACE = 14

MWT_IDENTITY = 1
MWT_LEFTMULTIPLY = 2
MWT_RIGHTMULTIPLY = 3
MWT_MIN = MWT_IDENTITY
MWT_MAX = MWT_RIGHTMULTIPLY
BI_RGB = 0
BI_RLE8 = 1
BI_RLE4 = 2
BI_BITFIELDS = 3
TMPF_FIXED_PITCH = 1
TMPF_VECTOR = 2
TMPF_DEVICE = 8
TMPF_TRUETYPE = 4
NTM_REGULAR = 64
NTM_BOLD = 32
NTM_ITALIC = 1
LF_FACESIZE = 32
LF_FULLFACESIZE = 64
OUT_DEFAULT_PRECIS = 0
OUT_STRING_PRECIS = 1
OUT_CHARACTER_PRECIS = 2
OUT_STROKE_PRECIS = 3
OUT_TT_PRECIS = 4
OUT_DEVICE_PRECIS = 5
OUT_RASTER_PRECIS = 6
OUT_TT_ONLY_PRECIS = 7
OUT_OUTLINE_PRECIS = 8
CLIP_DEFAULT_PRECIS = 0
CLIP_CHARACTER_PRECIS = 1
CLIP_STROKE_PRECIS = 2
CLIP_MASK = 15
CLIP_LH_ANGLES = 1 << 4
CLIP_TT_ALWAYS = 2 << 4
CLIP_EMBEDDED = 8 << 4
DEFAULT_QUALITY = 0
DRAFT_QUALITY = 1
PROOF_QUALITY = 2
NONANTIALIASED_QUALITY = 3
ANTIALIASED_QUALITY = 4
CLEARTYPE_QUALITY = 5
CLEARTYPE_NATURAL_QUALITY = 6
DEFAULT_PITCH = 0
FIXED_PITCH = 1
VARIABLE_PITCH = 2
ANSI_CHARSET = 0
DEFAULT_CHARSET = 1
SYMBOL_CHARSET = 2
SHIFTJIS_CHARSET = 128
HANGEUL_CHARSET = 129
CHINESEBIG5_CHARSET = 136
OEM_CHARSET = 255
JOHAB_CHARSET = 130
HEBREW_CHARSET = 177
ARABIC_CHARSET = 178
GREEK_CHARSET = 161
TURKISH_CHARSET = 162
VIETNAMESE_CHARSET = 163
THAI_CHARSET = 222
EASTEUROPE_CHARSET = 238
RUSSIAN_CHARSET = 204
MAC_CHARSET = 77
BALTIC_CHARSET = 186
FF_DONTCARE = 0 << 4
FF_ROMAN = 1 << 4
FF_SWISS = 2 << 4
FF_MODERN = 3 << 4
FF_SCRIPT = 4 << 4
FF_DECORATIVE = 5 << 4
FW_DONTCARE = 0
FW_THIN = 100
FW_EXTRALIGHT = 200
FW_LIGHT = 300
FW_NORMAL = 400
FW_MEDIUM = 500
FW_SEMIBOLD = 600
FW_BOLD = 700
FW_EXTRABOLD = 800
FW_HEAVY = 900
FW_ULTRALIGHT = FW_EXTRALIGHT
FW_REGULAR = FW_NORMAL
FW_DEMIBOLD = FW_SEMIBOLD
FW_ULTRABOLD = FW_EXTRABOLD
FW_BLACK = FW_HEAVY
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
BS_SOLID = 0
BS_NULL = 1
BS_HOLLOW = BS_NULL
BS_HATCHED = 2
BS_PATTERN = 3
BS_INDEXED = 4
BS_DIBPATTERN = 5
BS_DIBPATTERNPT = 6
BS_PATTERN8X8 = 7
BS_DIBPATTERN8X8 = 8
HS_HORIZONTAL = 0
HS_VERTICAL = 1
HS_FDIAGONAL = 2
HS_BDIAGONAL = 3
HS_CROSS = 4
HS_DIAGCROSS = 5
HS_FDIAGONAL1 = 6
HS_BDIAGONAL1 = 7
HS_SOLID = 8
HS_DENSE1 = 9
HS_DENSE2 = 10
HS_DENSE3 = 11
HS_DENSE4 = 12
HS_DENSE5 = 13
HS_DENSE6 = 14
HS_DENSE7 = 15
HS_DENSE8 = 16
HS_NOSHADE = 17
HS_HALFTONE = 18
HS_SOLIDCLR = 19
HS_DITHEREDCLR = 20
HS_SOLIDTEXTCLR = 21
HS_DITHEREDTEXTCLR = 22
HS_SOLIDBKCLR = 23
HS_DITHEREDBKCLR = 24
HS_API_MAX = 25
PS_SOLID = 0
PS_DASH = 1
PS_DOT = 2
PS_DASHDOT = 3
PS_DASHDOTDOT = 4
PS_NULL = 5
PS_INSIDEFRAME = 6
PS_USERSTYLE = 7
PS_ALTERNATE = 8
PS_STYLE_MASK = 15
PS_ENDCAP_ROUND = 0
PS_ENDCAP_SQUARE = 256
PS_ENDCAP_FLAT = 512
PS_ENDCAP_MASK = 3840
PS_JOIN_ROUND = 0
PS_JOIN_BEVEL = 4096
PS_JOIN_MITER = 8192
PS_JOIN_MASK = 61440
PS_COSMETIC = 0
PS_GEOMETRIC = 65536
PS_TYPE_MASK = 983040
AD_COUNTERCLOCKWISE = 1
AD_CLOCKWISE = 2
DRIVERVERSION = 0
TECHNOLOGY = 2
HORZSIZE = 4
VERTSIZE = 6
HORZRES = 8
VERTRES = 10
BITSPIXEL = 12
PLANES = 14
NUMBRUSHES = 16
NUMPENS = 18
NUMMARKERS = 20
NUMFONTS = 22
NUMCOLORS = 24
PDEVICESIZE = 26
CURVECAPS = 28
LINECAPS = 30
POLYGONALCAPS = 32
TEXTCAPS = 34
CLIPCAPS = 36
RASTERCAPS = 38
ASPECTX = 40
ASPECTY = 42
ASPECTXY = 44
LOGPIXELSX = 88
LOGPIXELSY = 90
SIZEPALETTE = 104
NUMRESERVED = 106
COLORRES = 108

PHYSICALWIDTH = 110
PHYSICALHEIGHT = 111
PHYSICALOFFSETX = 112
PHYSICALOFFSETY = 113
SCALINGFACTORX = 114
SCALINGFACTORY = 115
VREFRESH = 116
DESKTOPVERTRES = 117
DESKTOPHORZRES = 118
BLTALIGNMENT = 119
SHADEBLENDCAPS = 120
COLORMGMTCAPS = 121

DT_PLOTTER = 0
DT_RASDISPLAY = 1
DT_RASPRINTER = 2
DT_RASCAMERA = 3
DT_CHARSTREAM = 4
DT_METAFILE = 5
DT_DISPFILE = 6
CC_NONE = 0
CC_CIRCLES = 1
CC_PIE = 2
CC_CHORD = 4
CC_ELLIPSES = 8
CC_WIDE = 16
CC_STYLED = 32
CC_WIDESTYLED = 64
CC_INTERIORS = 128
CC_ROUNDRECT = 256
LC_NONE = 0
LC_POLYLINE = 2
LC_MARKER = 4
LC_POLYMARKER = 8
LC_WIDE = 16
LC_STYLED = 32
LC_WIDESTYLED = 64
LC_INTERIORS = 128
PC_NONE = 0
PC_POLYGON = 1
PC_RECTANGLE = 2
PC_WINDPOLYGON = 4
PC_TRAPEZOID = 4
PC_SCANLINE = 8
PC_WIDE = 16
PC_STYLED = 32
PC_WIDESTYLED = 64
PC_INTERIORS = 128
CP_NONE = 0
CP_RECTANGLE = 1
CP_REGION = 2
TC_OP_CHARACTER = 1
TC_OP_STROKE = 2
TC_CP_STROKE = 4
TC_CR_90 = 8
TC_CR_ANY = 16
TC_SF_X_YINDEP = 32
TC_SA_DOUBLE = 64
TC_SA_INTEGER = 128
TC_SA_CONTIN = 256
TC_EA_DOUBLE = 512
TC_IA_ABLE = 1024
TC_UA_ABLE = 2048
TC_SO_ABLE = 4096
TC_RA_ABLE = 8192
TC_VA_ABLE = 16384
TC_RESERVED = 32768
TC_SCROLLBLT = 65536
RC_BITBLT = 1
RC_BANDING = 2
RC_SCALING = 4
RC_BITMAP64 = 8
RC_GDI20_OUTPUT = 16
RC_GDI20_STATE = 32
RC_SAVEBITMAP = 64
RC_DI_BITMAP = 128
RC_PALETTE = 256
RC_DIBTODEV = 512
RC_BIGFONT = 1024
RC_STRETCHBLT = 2048
RC_FLOODFILL = 4096
RC_STRETCHDIB = 8192
RC_OP_DX_OUTPUT = 16384
RC_DEVBITS = 32768
DIB_RGB_COLORS = 0
DIB_PAL_COLORS = 1
DIB_PAL_INDICES = 2
DIB_PAL_PHYSINDICES = 2
DIB_PAL_LOGINDICES = 4
SYSPAL_ERROR = 0
SYSPAL_STATIC = 1
SYSPAL_NOSTATIC = 2
CBM_CREATEDIB = 2
CBM_INIT = 4
FLOODFILLBORDER = 0
FLOODFILLSURFACE = 1
CCHFORMNAME = 32
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.

# DEVMODE.dmFields
DM_SPECVERSION = 800
DM_ORIENTATION = 1
DM_PAPERSIZE = 2
DM_PAPERLENGTH = 4
DM_PAPERWIDTH = 8
DM_SCALE = 16
DM_POSITION = 32
DM_NUP = 64
DM_DISPLAYORIENTATION = 128
DM_COPIES = 256
DM_DEFAULTSOURCE = 512
DM_PRINTQUALITY = 1024
DM_COLOR = 2048
DM_DUPLEX = 4096
DM_YRESOLUTION = 8192
DM_TTOPTION = 16384
DM_COLLATE = 32768
DM_FORMNAME = 65536
DM_LOGPIXELS = 131072
DM_BITSPERPEL = 262144
DM_PELSWIDTH = 524288
DM_PELSHEIGHT = 1048576
DM_DISPLAYFLAGS = 2097152
DM_DISPLAYFREQUENCY = 4194304
DM_ICMMETHOD = 8388608
DM_ICMINTENT = 16777216
DM_MEDIATYPE = 33554432
DM_DITHERTYPE = 67108864
DM_PANNINGWIDTH = 134217728
DM_PANNINGHEIGHT = 268435456
DM_DISPLAYFIXEDOUTPUT = 536870912

# DEVMODE.dmOrientation
DMORIENT_PORTRAIT = 1
DMORIENT_LANDSCAPE = 2

# DEVMODE.dmDisplayOrientation
DMDO_DEFAULT = 0
DMDO_90 = 1
DMDO_180 = 2
DMDO_270 = 3

# DEVMODE.dmDisplayFixedOutput
DMDFO_DEFAULT = 0
DMDFO_STRETCH = 1
DMDFO_CENTER = 2

# DEVMODE.dmPaperSize
DMPAPER_LETTER = 1
DMPAPER_LETTERSMALL = 2
DMPAPER_TABLOID = 3
DMPAPER_LEDGER = 4
DMPAPER_LEGAL = 5
DMPAPER_STATEMENT = 6
DMPAPER_EXECUTIVE = 7
DMPAPER_A3 = 8
DMPAPER_A4 = 9
DMPAPER_A4SMALL = 10
DMPAPER_A5 = 11
DMPAPER_B4 = 12
DMPAPER_B5 = 13
DMPAPER_FOLIO = 14
DMPAPER_QUARTO = 15
DMPAPER_10X14 = 16
DMPAPER_11X17 = 17
DMPAPER_NOTE = 18
DMPAPER_ENV_9 = 19
DMPAPER_ENV_10 = 20
DMPAPER_ENV_11 = 21
DMPAPER_ENV_12 = 22
DMPAPER_ENV_14 = 23
DMPAPER_CSHEET = 24
DMPAPER_DSHEET = 25
DMPAPER_ESHEET = 26
DMPAPER_ENV_DL = 27
DMPAPER_ENV_C5 = 28
DMPAPER_ENV_C3 = 29
DMPAPER_ENV_C4 = 30
DMPAPER_ENV_C6 = 31
DMPAPER_ENV_C65 = 32
DMPAPER_ENV_B4 = 33
DMPAPER_ENV_B5 = 34
DMPAPER_ENV_B6 = 35
DMPAPER_ENV_ITALY = 36
DMPAPER_ENV_MONARCH = 37
DMPAPER_ENV_PERSONAL = 38
DMPAPER_FANFOLD_US = 39
DMPAPER_FANFOLD_STD_GERMAN = 40
DMPAPER_FANFOLD_LGL_GERMAN = 41
DMPAPER_ISO_B4 = 42
DMPAPER_JAPANESE_POSTCARD = 43
DMPAPER_9X11 = 44
DMPAPER_10X11 = 45
DMPAPER_15X11 = 46
DMPAPER_ENV_INVITE = 47
DMPAPER_RESERVED_48 = 48
DMPAPER_RESERVED_49 = 49
DMPAPER_LETTER_EXTRA = 50
DMPAPER_LEGAL_EXTRA = 51
DMPAPER_TABLOID_EXTRA = 52
DMPAPER_A4_EXTRA = 53
DMPAPER_LETTER_TRANSVERSE = 54
DMPAPER_A4_TRANSVERSE = 55
DMPAPER_LETTER_EXTRA_TRANSVERSE = 56
DMPAPER_A_PLUS = 57
DMPAPER_B_PLUS = 58
DMPAPER_LETTER_PLUS = 59
DMPAPER_A4_PLUS = 60
DMPAPER_A5_TRANSVERSE = 61
DMPAPER_B5_TRANSVERSE = 62
DMPAPER_A3_EXTRA = 63
DMPAPER_A5_EXTRA = 64
DMPAPER_B5_EXTRA = 65
DMPAPER_A2 = 66
DMPAPER_A3_TRANSVERSE = 67
DMPAPER_A3_EXTRA_TRANSVERSE = 68
DMPAPER_DBL_JAPANESE_POSTCARD = 69
DMPAPER_A6 = 70
DMPAPER_JENV_KAKU2 = 71
DMPAPER_JENV_KAKU3 = 72
DMPAPER_JENV_CHOU3 = 73
DMPAPER_JENV_CHOU4 = 74
DMPAPER_LETTER_ROTATED = 75
DMPAPER_A3_ROTATED = 76
DMPAPER_A4_ROTATED = 77
DMPAPER_A5_ROTATED = 78
DMPAPER_B4_JIS_ROTATED = 79
DMPAPER_B5_JIS_ROTATED = 80
DMPAPER_JAPANESE_POSTCARD_ROTATED = 81
DMPAPER_DBL_JAPANESE_POSTCARD_ROTATED = 82
DMPAPER_A6_ROTATED = 83
DMPAPER_JENV_KAKU2_ROTATED = 84
DMPAPER_JENV_KAKU3_ROTATED = 85
DMPAPER_JENV_CHOU3_ROTATED = 86
DMPAPER_JENV_CHOU4_ROTATED = 87
DMPAPER_B6_JIS = 88
DMPAPER_B6_JIS_ROTATED = 89
DMPAPER_12X11 = 90
DMPAPER_JENV_YOU4 = 91
DMPAPER_JENV_YOU4_ROTATED = 92
DMPAPER_P16K = 93
DMPAPER_P32K = 94
DMPAPER_P32KBIG = 95
DMPAPER_PENV_1 = 96
DMPAPER_PENV_2 = 97
DMPAPER_PENV_3 = 98
DMPAPER_PENV_4 = 99
DMPAPER_PENV_5 = 100
DMPAPER_PENV_6 = 101
DMPAPER_PENV_7 = 102
DMPAPER_PENV_8 = 103
DMPAPER_PENV_9 = 104
DMPAPER_PENV_10 = 105
DMPAPER_P16K_ROTATED = 106
DMPAPER_P32K_ROTATED = 107
DMPAPER_P32KBIG_ROTATED = 108
DMPAPER_PENV_1_ROTATED = 109
DMPAPER_PENV_2_ROTATED = 110
DMPAPER_PENV_3_ROTATED = 111
DMPAPER_PENV_4_ROTATED = 112
DMPAPER_PENV_5_ROTATED = 113
DMPAPER_PENV_6_ROTATED = 114
DMPAPER_PENV_7_ROTATED = 115
DMPAPER_PENV_8_ROTATED = 116
DMPAPER_PENV_9_ROTATED = 117
DMPAPER_PENV_10_ROTATED = 118
DMPAPER_LAST = DMPAPER_PENV_10_ROTATED
DMPAPER_USER = 256

# DEVMODE.dmDefaultSource
DMBIN_UPPER = 1
DMBIN_ONLYONE = 1
DMBIN_LOWER = 2
DMBIN_MIDDLE = 3
DMBIN_MANUAL = 4
DMBIN_ENVELOPE = 5
DMBIN_ENVMANUAL = 6
DMBIN_AUTO = 7
DMBIN_TRACTOR = 8
DMBIN_SMALLFMT = 9
DMBIN_LARGEFMT = 10
DMBIN_LARGECAPACITY = 11
DMBIN_CASSETTE = 14
DMBIN_FORMSOURCE = 15
DMBIN_LAST = DMBIN_FORMSOURCE
DMBIN_USER = 256

# DEVMODE.dmPrintQuality
DMRES_DRAFT = -1
DMRES_LOW = -2
DMRES_MEDIUM = -3
DMRES_HIGH = -4

# DEVMODE.dmColor
DMCOLOR_MONOCHROME = 1
DMCOLOR_COLOR = 2

# DEVMODE.dmDuplex
DMDUP_SIMPLEX = 1
DMDUP_VERTICAL = 2
DMDUP_HORIZONTAL = 3

# DEVMODE.dmTTOption
DMTT_BITMAP = 1
DMTT_DOWNLOAD = 2
DMTT_SUBDEV = 3
DMTT_DOWNLOAD_OUTLINE = 4

# DEVMODE.dmCollate
DMCOLLATE_FALSE = 0
DMCOLLATE_TRUE = 1

# DEVMODE.dmDisplayFlags
DM_GRAYSCALE = 1
DM_INTERLACED = 2

# DEVMODE.dmICMMethod
DMICMMETHOD_NONE = 1
DMICMMETHOD_SYSTEM = 2
DMICMMETHOD_DRIVER = 3
DMICMMETHOD_DEVICE = 4
DMICMMETHOD_USER = 256

# DEVMODE.dmICMIntent
DMICM_SATURATE = 1
DMICM_CONTRAST = 2
DMICM_COLORIMETRIC = 3
DMICM_ABS_COLORIMETRIC = 4
DMICM_USER = 256

# DEVMODE.dmMediaType
DMMEDIA_STANDARD = 1
DMMEDIA_TRANSPARENCY = 2
DMMEDIA_GLOSSY = 3
DMMEDIA_USER = 256

# DEVMODE.dmDitherType
DMDITHER_NONE = 1
DMDITHER_COARSE = 2
DMDITHER_FINE = 3
DMDITHER_LINEART = 4
DMDITHER_ERRORDIFFUSION = 5
DMDITHER_RESERVED6 = 6
DMDITHER_RESERVED7 = 7
DMDITHER_RESERVED8 = 8
DMDITHER_RESERVED9 = 9
DMDITHER_GRAYSCALE = 10
DMDITHER_USER = 256

# DEVMODE.dmNup
DMNUP_SYSTEM = 1
DMNUP_ONEUP = 2

# used with ExtEscape
FEATURESETTING_NUP = 0
FEATURESETTING_OUTPUT = 1
FEATURESETTING_PSLEVEL = 2
FEATURESETTING_CUSTPAPER = 3
FEATURESETTING_MIRROR = 4
FEATURESETTING_NEGATIVE = 5
FEATURESETTING_PROTOCOL = 6
FEATURESETTING_PRIVATE_BEGIN = 0x1000
FEATURESETTING_PRIVATE_END = 0x1FFF

RDH_RECTANGLES = 1
GGO_METRICS = 0
GGO_BITMAP = 1
GGO_NATIVE = 2
TT_POLYGON_TYPE = 24
TT_PRIM_LINE = 1
TT_PRIM_QSPLINE = 2
TT_AVAILABLE = 1
TT_ENABLED = 2
DM_UPDATE = 1
DM_COPY = 2
DM_PROMPT = 4
DM_MODIFY = 8
DM_IN_BUFFER = DM_MODIFY
DM_IN_PROMPT = DM_PROMPT
DM_OUT_BUFFER = DM_COPY
DM_OUT_DEFAULT = DM_UPDATE

# DISPLAY_DEVICE.StateFlags
DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 1
DISPLAY_DEVICE_MULTI_DRIVER = 2
DISPLAY_DEVICE_PRIMARY_DEVICE = 4
DISPLAY_DEVICE_MIRRORING_DRIVER = 8
DISPLAY_DEVICE_VGA_COMPATIBLE = 16
DISPLAY_DEVICE_REMOVABLE = 32
DISPLAY_DEVICE_MODESPRUNED = 134217728
DISPLAY_DEVICE_REMOTE = 67108864
DISPLAY_DEVICE_DISCONNECT = 33554432

# DeviceCapabilities types
DC_FIELDS = 1
DC_PAPERS = 2
DC_PAPERSIZE = 3
DC_MINEXTENT = 4
DC_MAXEXTENT = 5
DC_BINS = 6
DC_DUPLEX = 7
DC_SIZE = 8
DC_EXTRA = 9
DC_VERSION = 10
DC_DRIVER = 11
DC_BINNAMES = 12
DC_ENUMRESOLUTIONS = 13
DC_FILEDEPENDENCIES = 14
DC_TRUETYPE = 15
DC_PAPERNAMES = 16
DC_ORIENTATION = 17
DC_COPIES = 18
DC_BINADJUST = 19
DC_EMF_COMPLIANT = 20
DC_DATATYPE_PRODUCED = 21
DC_COLLATE = 22
DC_MANUFACTURER = 23
DC_MODEL = 24
DC_PERSONALITY = 25
DC_PRINTRATE = 26
DC_PRINTRATEUNIT = 27
DC_PRINTERMEM = 28
DC_MEDIAREADY = 29
DC_STAPLE = 30
DC_PRINTRATEPPM = 31
DC_COLORDEVICE = 32
DC_NUP = 33
DC_MEDIATYPENAMES = 34
DC_MEDIATYPES = 35

PRINTRATEUNIT_PPM = 1
PRINTRATEUNIT_CPS = 2
PRINTRATEUNIT_LPM = 3
PRINTRATEUNIT_IPM = 4

# TrueType constants
DCTT_BITMAP = 1
DCTT_DOWNLOAD = 2
DCTT_SUBDEV = 4
DCTT_DOWNLOAD_OUTLINE = 8

DCBA_FACEUPNONE = 0
DCBA_FACEUPCENTER = 1
DCBA_FACEUPLEFT = 2
DCBA_FACEUPRIGHT = 3
DCBA_FACEDOWNNONE = 256
DCBA_FACEDOWNCENTER = 257
DCBA_FACEDOWNLEFT = 258
DCBA_FACEDOWNRIGHT = 259

CA_NEGATIVE = 1
CA_LOG_FILTER = 2
ILLUMINANT_DEVICE_DEFAULT = 0
ILLUMINANT_A = 1
ILLUMINANT_B = 2
ILLUMINANT_C = 3
ILLUMINANT_D50 = 4
ILLUMINANT_D55 = 5
ILLUMINANT_D65 = 6
ILLUMINANT_D75 = 7
ILLUMINANT_F2 = 8
ILLUMINANT_MAX_INDEX = ILLUMINANT_F2
ILLUMINANT_TUNGSTEN = ILLUMINANT_A
ILLUMINANT_DAYLIGHT = ILLUMINANT_C
ILLUMINANT_FLUORESCENT = ILLUMINANT_F2
ILLUMINANT_NTSC = ILLUMINANT_C

# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
FONTMAPPER_MAX = 10
ENHMETA_SIGNATURE = 1179469088
ENHMETA_STOCK_OBJECT = -2147483648
EMR_HEADER = 1
EMR_POLYBEZIER = 2
EMR_POLYGON = 3
EMR_POLYLINE = 4
EMR_POLYBEZIERTO = 5
EMR_POLYLINETO = 6
EMR_POLYPOLYLINE = 7
EMR_POLYPOLYGON = 8
EMR_SETWINDOWEXTEX = 9
EMR_SETWINDOWORGEX = 10
EMR_SETVIEWPORTEXTEX = 11
EMR_SETVIEWPORTORGEX = 12
EMR_SETBRUSHORGEX = 13
EMR_EOF = 14
EMR_SETPIXELV = 15
EMR_SETMAPPERFLAGS = 16
EMR_SETMAPMODE = 17
EMR_SETBKMODE = 18
EMR_SETPOLYFILLMODE = 19
EMR_SETROP2 = 20
EMR_SETSTRETCHBLTMODE = 21
EMR_SETTEXTALIGN = 22
EMR_SETCOLORADJUSTMENT = 23
EMR_SETTEXTCOLOR = 24
EMR_SETBKCOLOR = 25
EMR_OFFSETCLIPRGN = 26
EMR_MOVETOEX = 27
EMR_SETMETARGN = 28
EMR_EXCLUDECLIPRECT = 29
EMR_INTERSECTCLIPRECT = 30
EMR_SCALEVIEWPORTEXTEX = 31
EMR_SCALEWINDOWEXTEX = 32
EMR_SAVEDC = 33
EMR_RESTOREDC = 34
EMR_SETWORLDTRANSFORM = 35
EMR_MODIFYWORLDTRANSFORM = 36
EMR_SELECTOBJECT = 37
EMR_CREATEPEN = 38
EMR_CREATEBRUSHINDIRECT = 39
EMR_DELETEOBJECT = 40
EMR_ANGLEARC = 41
EMR_ELLIPSE = 42
EMR_RECTANGLE = 43
EMR_ROUNDRECT = 44
EMR_ARC = 45
EMR_CHORD = 46
EMR_PIE = 47
EMR_SELECTPALETTE = 48
EMR_CREATEPALETTE = 49
EMR_SETPALETTEENTRIES = 50
EMR_RESIZEPALETTE = 51
EMR_REALIZEPALETTE = 52
EMR_EXTFLOODFILL = 53
EMR_LINETO = 54
EMR_ARCTO = 55
EMR_POLYDRAW = 56
EMR_SETARCDIRECTION = 57
EMR_SETMITERLIMIT = 58
EMR_BEGINPATH = 59
EMR_ENDPATH = 60
EMR_CLOSEFIGURE = 61
EMR_FILLPATH = 62
EMR_STROKEANDFILLPATH = 63
EMR_STROKEPATH = 64
EMR_FLATTENPATH = 65
EMR_WIDENPATH = 66
EMR_SELECTCLIPPATH = 67
EMR_ABORTPATH = 68
EMR_GDICOMMENT = 70
EMR_FILLRGN = 71
EMR_FRAMERGN = 72
EMR_INVERTRGN = 73
EMR_PAINTRGN = 74
EMR_EXTSELECTCLIPRGN = 75
EMR_BITBLT = 76
EMR_STRETCHBLT = 77
EMR_MASKBLT = 78
EMR_PLGBLT = 79
EMR_SETDIBITSTODEVICE = 80
EMR_STRETCHDIBITS = 81
EMR_EXTCREATEFONTINDIRECTW = 82
EMR_EXTTEXTOUTA = 83
EMR_EXTTEXTOUTW = 84
EMR_POLYBEZIER16 = 85
EMR_POLYGON16 = 86
EMR_POLYLINE16 = 87
EMR_POLYBEZIERTO16 = 88
EMR_POLYLINETO16 = 89
EMR_POLYPOLYLINE16 = 90
EMR_POLYPOLYGON16 = 91
EMR_POLYDRAW16 = 92
EMR_CREATEMONOBRUSH = 93
EMR_CREATEDIBPATTERNBRUSHPT = 94
EMR_EXTCREATEPEN = 95
EMR_POLYTEXTOUTA = 96
EMR_POLYTEXTOUTW = 97
EMR_MIN = 1
EMR_MAX = 97
# Generated by h2py from \msvcnt\include\wingdi.h
# hacked and split manually by mhammond.
PANOSE_COUNT = 10
PAN_FAMILYTYPE_INDEX = 0
PAN_SERIFSTYLE_INDEX = 1
PAN_WEIGHT_INDEX = 2
PAN_PROPORTION_INDEX = 3
PAN_CONTRAST_INDEX = 4
PAN_STROKEVARIATION_INDEX = 5
PAN_ARMSTYLE_INDEX = 6
PAN_LETTERFORM_INDEX = 7
PAN_MIDLINE_INDEX = 8
PAN_XHEIGHT_INDEX = 9
PAN_CULTURE_LATIN = 0
PAN_ANY = 0
PAN_NO_FIT = 1
PAN_FAMILY_TEXT_DISPLAY = 2
PAN_FAMILY_SCRIPT = 3
PAN_FAMILY_DECORATIVE = 4
PAN_FAMILY_PICTORIAL = 5
PAN_SERIF_COVE = 2
PAN_SERIF_OBTUSE_COVE = 3
PAN_SERIF_SQUARE_COVE = 4
PAN_SERIF_OBTUSE_SQUARE_COVE = 5
PAN_SERIF_SQUARE = 6
PAN_SERIF_THIN = 7
PAN_SERIF_BONE = 8
PAN_SERIF_EXAGGERATED = 9
PAN_SERIF_TRIANGLE = 10
PAN_SERIF_NORMAL_SANS = 11
PAN_SERIF_OBTUSE_SANS = 12
PAN_SERIF_PERP_SANS = 13
PAN_SERIF_FLARED = 14
PAN_SERIF_ROUNDED = 15
PAN_WEIGHT_VERY_LIGHT = 2
PAN_WEIGHT_LIGHT = 3
PAN_WEIGHT_THIN = 4
PAN_WEIGHT_BOOK = 5
PAN_WEIGHT_MEDIUM = 6
PAN_WEIGHT_DEMI = 7
PAN_WEIGHT_BOLD = 8
PAN_WEIGHT_HEAVY = 9
PAN_WEIGHT_BLACK = 10
PAN_WEIGHT_NORD = 11
PAN_PROP_OLD_STYLE = 2
PAN_PROP_MODERN = 3
PAN_PROP_EVEN_WIDTH = 4
PAN_PROP_EXPANDED = 5
PAN_PROP_CONDENSED = 6
PAN_PROP_VERY_EXPANDED = 7
PAN_PROP_VERY_CONDENSED = 8
PAN_PROP_MONOSPACED = 9
PAN_CONTRAST_NONE = 2
PAN_CONTRAST_VERY_LOW = 3
PAN_CONTRAST_LOW = 4
PAN_CONTRAST_MEDIUM_LOW = 5
PAN_CONTRAST_MEDIUM = 6
PAN_CONTRAST_MEDIUM_HIGH = 7
PAN_CONTRAST_HIGH = 8
PAN_CONTRAST_VERY_HIGH = 9
PAN_STROKE_GRADUAL_DIAG = 2
PAN_STROKE_GRADUAL_TRAN = 3
PAN_STROKE_GRADUAL_VERT = 4
PAN_STROKE_GRADUAL_HORZ = 5
PAN_STROKE_RAPID_VERT = 6
PAN_STROKE_RAPID_HORZ = 7
PAN_STROKE_INSTANT_VERT = 8
PAN_STRAIGHT_ARMS_HORZ = 2
PAN_STRAIGHT_ARMS_WEDGE = 3
PAN_STRAIGHT_ARMS_VERT = 4
PAN_STRAIGHT_ARMS_SINGLE_SERIF = 5
PAN_STRAIGHT_ARMS_DOUBLE_SERIF = 6
PAN_BENT_ARMS_HORZ = 7
PAN_BENT_ARMS_WEDGE = 8
PAN_BENT_ARMS_VERT = 9
PAN_BENT_ARMS_SINGLE_SERIF = 10
PAN_BENT_ARMS_DOUBLE_SERIF = 11
PAN_LETT_NORMAL_CONTACT = 2
PAN_LETT_NORMAL_WEIGHTED = 3
PAN_LETT_NORMAL_BOXED = 4
PAN_LETT_NORMAL_FLATTENED = 5
PAN_LETT_NORMAL_ROUNDED = 6
PAN_LETT_NORMAL_OFF_CENTER = 7
PAN_LETT_NORMAL_SQUARE = 8
PAN_LETT_OBLIQUE_CONTACT = 9
PAN_LETT_OBLIQUE_WEIGHTED = 10
PAN_LETT_OBLIQUE_BOXED = 11
PAN_LETT_OBLIQUE_FLATTENED = 12
PAN_LETT_OBLIQUE_ROUNDED = 13
PAN_LETT_OBLIQUE_OFF_CENTER = 14
PAN_LETT_OBLIQUE_SQUARE = 15
PAN_MIDLINE_STANDARD_TRIMMED = 2
PAN_MIDLINE_STANDARD_POINTED = 3
PAN_MIDLINE_STANDARD_SERIFED = 4
PAN_MIDLINE_HIGH_TRIMMED = 5
PAN_MIDLINE_HIGH_POINTED = 6
PAN_MIDLINE_HIGH_SERIFED = 7
PAN_MIDLINE_CONSTANT_TRIMMED = 8
PAN_MIDLINE_CONSTANT_POINTED = 9
PAN_MIDLINE_CONSTANT_SERIFED = 10
PAN_MIDLINE_LOW_TRIMMED = 11
PAN_MIDLINE_LOW_POINTED = 12
PAN_MIDLINE_LOW_SERIFED = 13
PAN_XHEIGHT_CONSTANT_SMALL = 2
PAN_XHEIGHT_CONSTANT_STD = 3
PAN_XHEIGHT_CONSTANT_LARGE = 4
PAN_XHEIGHT_DUCKING_SMALL = 5
PAN_XHEIGHT_DUCKING_STD = 6
PAN_XHEIGHT_DUCKING_LARGE = 7
ELF_VENDOR_SIZE = 4
ELF_VERSION = 0
ELF_CULTURE_LATIN = 0
RASTER_FONTTYPE = 1
DEVICE_FONTTYPE = 2
TRUETYPE_FONTTYPE = 4


def PALETTEINDEX(i):
    return 16777216 | (i)


PC_RESERVED = 1
PC_EXPLICIT = 2
PC_NOCOLLAPSE = 4


def GetRValue(rgb):
    return rgb & 0xFF


def GetGValue(rgb):
    return (rgb >> 8) & 0xFF


def GetBValue(rgb):
    return (rgb >> 16) & 0xFF


TRANSPARENT = 1
OPAQUE = 2
BKMODE_LAST = 2
GM_COMPATIBLE = 1
GM_ADVANCED = 2
GM_LAST = 2
PT_CLOSEFIGURE = 1
PT_LINETO = 2
PT_BEZIERTO = 4
PT_MOVETO = 6
MM_TEXT = 1
MM_LOMETRIC = 2
MM_HIMETRIC = 3
MM_LOENGLISH = 4
MM_HIENGLISH = 5
MM_TWIPS = 6
MM_ISOTROPIC = 7
MM_ANISOTROPIC = 8
MM_MIN = MM_TEXT
MM_MAX = MM_ANISOTROPIC
MM_MAX_FIXEDSCALE = MM_TWIPS
ABSOLUTE = 1
RELATIVE = 2
WHITE_BRUSH = 0
LTGRAY_BRUSH = 1
GRAY_BRUSH = 2
DKGRAY_BRUSH = 3
BLACK_BRUSH = 4
NULL_BRUSH = 5
HOLLOW_BRUSH = NULL_BRUSH
WHITE_PEN = 6
BLACK_PEN = 7
NULL_PEN = 8
OEM_FIXED_FONT = 10
ANSI_FIXED_FONT = 11
ANSI_VAR_FONT = 12
SYSTEM_FONT = 13
DEVICE_DEFAULT_FONT = 14
DEFAULT_PALETTE = 15
SYSTEM_FIXED_FONT = 16
STOCK_LAST = 16
CLR_INVALID = -1

DC_BRUSH = 18
DC_PEN = 19

# Exception/Status codes from winuser.h and winnt.h
STATUS_WAIT_0 = 0
STATUS_ABANDONED_WAIT_0 = 128
STATUS_USER_APC = 192
STATUS_TIMEOUT = 258
STATUS_PENDING = 259
STATUS_SEGMENT_NOTIFICATION = 1073741829
STATUS_GUARD_PAGE_VIOLATION = -2147483647
STATUS_DATATYPE_MISALIGNMENT = -2147483646
STATUS_BREAKPOINT = -2147483645
STATUS_SINGLE_STEP = -2147483644
STATUS_ACCESS_VIOLATION = -1073741819
STATUS_IN_PAGE_ERROR = -1073741818
STATUS_INVALID_HANDLE = -1073741816
STATUS_NO_MEMORY = -1073741801
STATUS_ILLEGAL_INSTRUCTION = -1073741795
STATUS_NONCONTINUABLE_EXCEPTION = -1073741787
STATUS_INVALID_DISPOSITION = -1073741786
STATUS_ARRAY_BOUNDS_EXCEEDED = -1073741684
STATUS_FLOAT_DENORMAL_OPERAND = -1073741683
STATUS_FLOAT_DIVIDE_BY_ZERO = -1073741682
STATUS_FLOAT_INEXACT_RESULT = -1073741681
STATUS_FLOAT_INVALID_OPERATION = -1073741680
STATUS_FLOAT_OVERFLOW = -1073741679
STATUS_FLOAT_STACK_CHECK = -1073741678
STATUS_FLOAT_UNDERFLOW = -1073741677
STATUS_INTEGER_DIVIDE_BY_ZERO = -1073741676
STATUS_INTEGER_OVERFLOW = -1073741675
STATUS_PRIVILEGED_INSTRUCTION = -1073741674
STATUS_STACK_OVERFLOW = -1073741571
STATUS_CONTROL_C_EXIT = -1073741510


WAIT_FAILED = -1
WAIT_OBJECT_0 = STATUS_WAIT_0 + 0

WAIT_ABANDONED = STATUS_ABANDONED_WAIT_0 + 0
WAIT_ABANDONED_0 = STATUS_ABANDONED_WAIT_0 + 0

WAIT_TIMEOUT = STATUS_TIMEOUT
WAIT_IO_COMPLETION = STATUS_USER_APC
STILL_ACTIVE = STATUS_PENDING
EXCEPTION_ACCESS_VIOLATION = STATUS_ACCESS_VIOLATION
EXCEPTION_DATATYPE_MISALIGNMENT = STATUS_DATATYPE_MISALIGNMENT
EXCEPTION_BREAKPOINT = STATUS_BREAKPOINT
EXCEPTION_SINGLE_STEP = STATUS_SINGLE_STEP
EXCEPTION_ARRAY_BOUNDS_EXCEEDED = STATUS_ARRAY_BOUNDS_EXCEEDED
EXCEPTION_FLT_DENORMAL_OPERAND = STATUS_FLOAT_DENORMAL_OPERAND
EXCEPTION_FLT_DIVIDE_BY_ZERO = STATUS_FLOAT_DIVIDE_BY_ZERO
EXCEPTION_FLT_INEXACT_RESULT = STATUS_FLOAT_INEXACT_RESULT
EXCEPTION_FLT_INVALID_OPERATION = STATUS_FLOAT_INVALID_OPERATION
EXCEPTION_FLT_OVERFLOW = STATUS_FLOAT_OVERFLOW
EXCEPTION_FLT_STACK_CHECK = STATUS_FLOAT_STACK_CHECK
EXCEPTION_FLT_UNDERFLOW = STATUS_FLOAT_UNDERFLOW
EXCEPTION_INT_DIVIDE_BY_ZERO = STATUS_INTEGER_DIVIDE_BY_ZERO
EXCEPTION_INT_OVERFLOW = STATUS_INTEGER_OVERFLOW
EXCEPTION_PRIV_INSTRUCTION = STATUS_PRIVILEGED_INSTRUCTION
EXCEPTION_IN_PAGE_ERROR = STATUS_IN_PAGE_ERROR
EXCEPTION_ILLEGAL_INSTRUCTION = STATUS_ILLEGAL_INSTRUCTION
EXCEPTION_NONCONTINUABLE_EXCEPTION = STATUS_NONCONTINUABLE_EXCEPTION
EXCEPTION_STACK_OVERFLOW = STATUS_STACK_OVERFLOW
EXCEPTION_INVALID_DISPOSITION = STATUS_INVALID_DISPOSITION
EXCEPTION_GUARD_PAGE = STATUS_GUARD_PAGE_VIOLATION
EXCEPTION_INVALID_HANDLE = STATUS_INVALID_HANDLE
CONTROL_C_EXIT = STATUS_CONTROL_C_EXIT

# winuser.h line 8594
# constants used with SystemParametersInfo
SPI_GETBEEP = 1
SPI_SETBEEP = 2
SPI_GETMOUSE = 3
SPI_SETMOUSE = 4
SPI_GETBORDER = 5
SPI_SETBORDER = 6
SPI_GETKEYBOARDSPEED = 10
SPI_SETKEYBOARDSPEED = 11
SPI_LANGDRIVER = 12
SPI_ICONHORIZONTALSPACING = 13
SPI_GETSCREENSAVETIMEOUT = 14
SPI_SETSCREENSAVETIMEOUT = 15
SPI_GETSCREENSAVEACTIVE = 16
SPI_SETSCREENSAVEACTIVE = 17
SPI_GETGRIDGRANULARITY = 18
SPI_SETGRIDGRANULARITY = 19
SPI_SETDESKWALLPAPER = 20
SPI_SETDESKPATTERN = 21
SPI_GETKEYBOARDDELAY = 22
SPI_SETKEYBOARDDELAY = 23
SPI_ICONVERTICALSPACING = 24
SPI_GETICONTITLEWRAP = 25
SPI_SETICONTITLEWRAP = 26
SPI_GETMENUDROPALIGNMENT = 27
SPI_SETMENUDROPALIGNMENT = 28
SPI_SETDOUBLECLKWIDTH = 29
SPI_SETDOUBLECLKHEIGHT = 30
SPI_GETICONTITLELOGFONT = 31
SPI_SETDOUBLECLICKTIME = 32
SPI_SETMOUSEBUTTONSWAP = 33
SPI_SETICONTITLELOGFONT = 34
SPI_GETFASTTASKSWITCH = 35
SPI_SETFASTTASKSWITCH = 36
SPI_SETDRAGFULLWINDOWS = 37
SPI_GETDRAGFULLWINDOWS = 38
SPI_GETNONCLIENTMETRICS = 41
SPI_SETNONCLIENTMETRICS = 42
SPI_GETMINIMIZEDMETRICS = 43
SPI_SETMINIMIZEDMETRICS = 44
SPI_GETICONMETRICS = 45
SPI_SETICONMETRICS = 46
SPI_SETWORKAREA = 47
SPI_GETWORKAREA = 48
SPI_SETPENWINDOWS = 49
SPI_GETFILTERKEYS = 50
SPI_SETFILTERKEYS = 51
SPI_GETTOGGLEKEYS = 52
SPI_SETTOGGLEKEYS = 53
SPI_GETMOUSEKEYS = 54
SPI_SETMOUSEKEYS = 55
SPI_GETSHOWSOUNDS = 56
SPI_SETSHOWSOUNDS = 57
SPI_GETSTICKYKEYS = 58
SPI_SETSTICKYKEYS = 59
SPI_GETACCESSTIMEOUT = 60
SPI_SETACCESSTIMEOUT = 61
SPI_GETSERIALKEYS = 62
SPI_SETSERIALKEYS = 63
SPI_GETSOUNDSENTRY = 64
SPI_SETSOUNDSENTRY = 65
SPI_GETHIGHCONTRAST = 66
SPI_SETHIGHCONTRAST = 67
SPI_GETKEYBOARDPREF = 68
SPI_SETKEYBOARDPREF = 69
SPI_GETSCREENREADER = 70
SPI_SETSCREENREADER = 71
SPI_GETANIMATION = 72
SPI_SETANIMATION = 73
SPI_GETFONTSMOOTHING = 74
SPI_SETFONTSMOOTHING = 75
SPI_SETDRAGWIDTH = 76
SPI_SETDRAGHEIGHT = 77
SPI_SETHANDHELD = 78
SPI_GETLOWPOWERTIMEOUT = 79
SPI_GETPOWEROFFTIMEOUT = 80
SPI_SETLOWPOWERTIMEOUT = 81
SPI_SETPOWEROFFTIMEOUT = 82
SPI_GETLOWPOWERACTIVE = 83
SPI_GETPOWEROFFACTIVE = 84
SPI_SETLOWPOWERACTIVE = 85
SPI_SETPOWEROFFACTIVE = 86
SPI_SETCURSORS = 87
SPI_SETICONS = 88
SPI_GETDEFAULTINPUTLANG = 89
SPI_SETDEFAULTINPUTLANG = 90
SPI_SETLANGTOGGLE = 91
SPI_GETWINDOWSEXTENSION = 92
SPI_SETMOUSETRAILS = 93
SPI_GETMOUSETRAILS = 94
SPI_GETSNAPTODEFBUTTON = 95
SPI_SETSNAPTODEFBUTTON = 96
SPI_SETSCREENSAVERRUNNING = 97
SPI_SCREENSAVERRUNNING = SPI_SETSCREENSAVERRUNNING
SPI_GETMOUSEHOVERWIDTH = 98
SPI_SETMOUSEHOVERWIDTH = 99
SPI_GETMOUSEHOVERHEIGHT = 100
SPI_SETMOUSEHOVERHEIGHT = 101
SPI_GETMOUSEHOVERTIME = 102
SPI_SETMOUSEHOVERTIME = 103
SPI_GETWHEELSCROLLLINES = 104
SPI_SETWHEELSCROLLLINES = 105
SPI_GETMENUSHOWDELAY = 106
SPI_SETMENUSHOWDELAY = 107

SPI_GETSHOWIMEUI = 110
SPI_SETSHOWIMEUI = 111
SPI_GETMOUSESPEED = 112
SPI_SETMOUSESPEED = 113
SPI_GETSCREENSAVERRUNNING = 114
SPI_GETDESKWALLPAPER = 115

SPI_GETACTIVEWINDOWTRACKING = 4096
SPI_SETACTIVEWINDOWTRACKING = 4097
SPI_GETMENUANIMATION = 4098
SPI_SETMENUANIMATION = 4099
SPI_GETCOMBOBOXANIMATION = 4100
SPI_SETCOMBOBOXANIMATION = 4101
SPI_GETLISTBOXSMOOTHSCROLLING = 4102
SPI_SETLISTBOXSMOOTHSCROLLING = 4103
SPI_GETGRADIENTCAPTIONS = 4104
SPI_SETGRADIENTCAPTIONS = 4105
SPI_GETKEYBOARDCUES = 4106
SPI_SETKEYBOARDCUES = 4107
SPI_GETMENUUNDERLINES = 4106
SPI_SETMENUUNDERLINES = 4107
SPI_GETACTIVEWNDTRKZORDER = 4108
SPI_SETACTIVEWNDTRKZORDER = 4109
SPI_GETHOTTRACKING = 4110
SPI_SETHOTTRACKING = 4111

SPI_GETMENUFADE = 4114
SPI_SETMENUFADE = 4115
SPI_GETSELECTIONFADE = 4116
SPI_SETSELECTIONFADE = 4117
SPI_GETTOOLTIPANIMATION = 4118
SPI_SETTOOLTIPANIMATION = 4119
SPI_GETTOOLTIPFADE = 4120
SPI_SETTOOLTIPFADE = 4121
SPI_GETCURSORSHADOW = 4122
SPI_SETCURSORSHADOW = 4123
SPI_GETMOUSESONAR = 4124
SPI_SETMOUSESONAR = 4125
SPI_GETMOUSECLICKLOCK = 4126
SPI_SETMOUSECLICKLOCK = 4127
SPI_GETMOUSEVANISH = 4128
SPI_SETMOUSEVANISH = 4129
SPI_GETFLATMENU = 4130
SPI_SETFLATMENU = 4131
SPI_GETDROPSHADOW = 4132
SPI_SETDROPSHADOW = 4133
SPI_GETBLOCKSENDINPUTRESETS = 4134
SPI_SETBLOCKSENDINPUTRESETS = 4135
SPI_GETUIEFFECTS = 4158
SPI_SETUIEFFECTS = 4159

SPI_GETFOREGROUNDLOCKTIMEOUT = 8192
SPI_SETFOREGROUNDLOCKTIMEOUT = 8193
SPI_GETACTIVEWNDTRKTIMEOUT = 8194
SPI_SETACTIVEWNDTRKTIMEOUT = 8195
SPI_GETFOREGROUNDFLASHCOUNT = 8196
SPI_SETFOREGROUNDFLASHCOUNT = 8197
SPI_GETCARETWIDTH = 8198
SPI_SETCARETWIDTH = 8199
SPI_GETMOUSECLICKLOCKTIME = 8200
SPI_SETMOUSECLICKLOCKTIME = 8201
SPI_GETFONTSMOOTHINGTYPE = 8202
SPI_SETFONTSMOOTHINGTYPE = 8203
SPI_GETFONTSMOOTHINGCONTRAST = 8204
SPI_SETFONTSMOOTHINGCONTRAST = 8205
SPI_GETFOCUSBORDERWIDTH = 8206
SPI_SETFOCUSBORDERWIDTH = 8207
SPI_GETFOCUSBORDERHEIGHT = 8208
SPI_SETFOCUSBORDERHEIGHT = 8209
SPI_GETFONTSMOOTHINGORIENTATION = 8210
SPI_SETFONTSMOOTHINGORIENTATION = 8211

# fWinIni flags for SystemParametersInfo
SPIF_UPDATEINIFILE = 1
SPIF_SENDWININICHANGE = 2
SPIF_SENDCHANGE = SPIF_SENDWININICHANGE

# used with SystemParametersInfo and SPI_GETFONTSMOOTHINGTYPE/SPI_SETFONTSMOOTHINGTYPE
FE_FONTSMOOTHINGSTANDARD = 1
FE_FONTSMOOTHINGCLEARTYPE = 2
FE_FONTSMOOTHINGDOCKING = 32768

METRICS_USEDEFAULT = -1
ARW_BOTTOMLEFT = 0
ARW_BOTTOMRIGHT = 1
ARW_TOPLEFT = 2
ARW_TOPRIGHT = 3
ARW_STARTMASK = 3
ARW_STARTRIGHT = 1
ARW_STARTTOP = 2
ARW_LEFT = 0
ARW_RIGHT = 0
ARW_UP = 4
ARW_DOWN = 4
ARW_HIDE = 8
# ARW_VALID = 0x000F
SERKF_SERIALKEYSON = 1
SERKF_AVAILABLE = 2
SERKF_INDICATOR = 4
HCF_HIGHCONTRASTON = 1
HCF_AVAILABLE = 2
HCF_HOTKEYACTIVE = 4
HCF_CONFIRMHOTKEY = 8
HCF_HOTKEYSOUND = 16
HCF_INDICATOR = 32
HCF_HOTKEYAVAILABLE = 64
CDS_UPDATEREGISTRY = 1
CDS_TEST = 2
CDS_FULLSCREEN = 4
CDS_GLOBAL = 8
CDS_SET_PRIMARY = 16
CDS_RESET = 1073741824
CDS_SETRECT = 536870912
CDS_NORESET = 268435456

# return values from ChangeDisplaySettings and ChangeDisplaySettingsEx
DISP_CHANGE_SUCCESSFUL = 0
DISP_CHANGE_RESTART = 1
DISP_CHANGE_FAILED = -1
DISP_CHANGE_BADMODE = -2
DISP_CHANGE_NOTUPDATED = -3
DISP_CHANGE_BADFLAGS = -4
DISP_CHANGE_BADPARAM = -5
DISP_CHANGE_BADDUALVIEW = -6

ENUM_CURRENT_SETTINGS = -1
ENUM_REGISTRY_SETTINGS = -2
FKF_FILTERKEYSON = 1
FKF_AVAILABLE = 2
FKF_HOTKEYACTIVE = 4
FKF_CONFIRMHOTKEY = 8
FKF_HOTKEYSOUND = 16
FKF_INDICATOR = 32
FKF_CLICKON = 64
SKF_STICKYKEYSON = 1
SKF_AVAILABLE = 2
SKF_HOTKEYACTIVE = 4
SKF_CONFIRMHOTKEY = 8
SKF_HOTKEYSOUND = 16
SKF_INDICATOR = 32
SKF_AUDIBLEFEEDBACK = 64
SKF_TRISTATE = 128
SKF_TWOKEYSOFF = 256
SKF_LALTLATCHED = 268435456
SKF_LCTLLATCHED = 67108864
SKF_LSHIFTLATCHED = 16777216
SKF_RALTLATCHED = 536870912
SKF_RCTLLATCHED = 134217728
SKF_RSHIFTLATCHED = 33554432
SKF_LWINLATCHED = 1073741824
SKF_RWINLATCHED = -2147483648
SKF_LALTLOCKED = 1048576
SKF_LCTLLOCKED = 262144
SKF_LSHIFTLOCKED = 65536
SKF_RALTLOCKED = 2097152
SKF_RCTLLOCKED = 524288
SKF_RSHIFTLOCKED = 131072
SKF_LWINLOCKED = 4194304
SKF_RWINLOCKED = 8388608
MKF_MOUSEKEYSON = 1
MKF_AVAILABLE = 2
MKF_HOTKEYACTIVE = 4
MKF_CONFIRMHOTKEY = 8
MKF_HOTKEYSOUND = 16
MKF_INDICATOR = 32
MKF_MODIFIERS = 64
MKF_REPLACENUMBERS = 128
MKF_LEFTBUTTONSEL = 268435456
MKF_RIGHTBUTTONSEL = 536870912
MKF_LEFTBUTTONDOWN = 16777216
MKF_RIGHTBUTTONDOWN = 33554432
MKF_MOUSEMODE = -2147483648
ATF_TIMEOUTON = 1
ATF_ONOFFFEEDBACK = 2
SSGF_NONE = 0
SSGF_DISPLAY = 3
SSTF_NONE = 0
SSTF_CHARS = 1
SSTF_BORDER = 2
SSTF_DISPLAY = 3
SSWF_NONE = 0
SSWF_TITLE = 1
SSWF_WINDOW = 2
SSWF_DISPLAY = 3
SSWF_CUSTOM = 4
SSF_SOUNDSENTRYON = 1
SSF_AVAILABLE = 2
SSF_INDICATOR = 4
TKF_TOGGLEKEYSON = 1
TKF_AVAILABLE = 2
TKF_HOTKEYACTIVE = 4
TKF_CONFIRMHOTKEY = 8
TKF_HOTKEYSOUND = 16
TKF_INDICATOR = 32
SLE_ERROR = 1
SLE_MINORERROR = 2
SLE_WARNING = 3
MONITOR_DEFAULTTONULL = 0
MONITOR_DEFAULTTOPRIMARY = 1
MONITOR_DEFAULTTONEAREST = 2
MONITORINFOF_PRIMARY = 1
CCHDEVICENAME = 32
CHILDID_SELF = 0
INDEXID_OBJECT = 0
INDEXID_CONTAINER = 0
OBJID_WINDOW = 0
OBJID_SYSMENU = -1
OBJID_TITLEBAR = -2
OBJID_MENU = -3
OBJID_CLIENT = -4
OBJID_VSCROLL = -5
OBJID_HSCROLL = -6
OBJID_SIZEGRIP = -7
OBJID_CARET = -8
OBJID_CURSOR = -9
OBJID_ALERT = -10
OBJID_SOUND = -11
EVENT_MIN = 1
EVENT_MAX = 2147483647
EVENT_SYSTEM_SOUND = 1
EVENT_SYSTEM_ALERT = 2
EVENT_SYSTEM_FOREGROUND = 3
EVENT_SYSTEM_MENUSTART = 4
EVENT_SYSTEM_MENUEND = 5
EVENT_SYSTEM_MENUPOPUPSTART = 6
EVENT_SYSTEM_MENUPOPUPEND = 7
EVENT_SYSTEM_CAPTURESTART = 8
EVENT_SYSTEM_CAPTUREEND = 9
EVENT_SYSTEM_MOVESIZESTART = 10
EVENT_SYSTEM_MOVESIZEEND = 11
EVENT_SYSTEM_CONTEXTHELPSTART = 12
EVENT_SYSTEM_CONTEXTHELPEND = 13
EVENT_SYSTEM_DRAGDROPSTART = 14
EVENT_SYSTEM_DRAGDROPEND = 15
EVENT_SYSTEM_DIALOGSTART = 16
EVENT_SYSTEM_DIALOGEND = 17
EVENT_SYSTEM_SCROLLINGSTART = 18
EVENT_SYSTEM_SCROLLINGEND = 19
EVENT_SYSTEM_SWITCHSTART = 20
EVENT_SYSTEM_SWITCHEND = 21
EVENT_SYSTEM_MINIMIZESTART = 22
EVENT_SYSTEM_MINIMIZEEND = 23
EVENT_OBJECT_CREATE = 32768
EVENT_OBJECT_DESTROY = 32769
EVENT_OBJECT_SHOW = 32770
EVENT_OBJECT_HIDE = 32771
EVENT_OBJECT_REORDER = 32772
EVENT_OBJECT_FOCUS = 32773
EVENT_OBJECT_SELECTION = 32774
EVENT_OBJECT_SELECTIONADD = 32775
EVENT_OBJECT_SELECTIONREMOVE = 32776
EVENT_OBJECT_SELECTIONWITHIN = 32777
EVENT_OBJECT_STATECHANGE = 32778
EVENT_OBJECT_LOCATIONCHANGE = 32779
EVENT_OBJECT_NAMECHANGE = 32780
EVENT_OBJECT_DESCRIPTIONCHANGE = 32781
EVENT_OBJECT_VALUECHANGE = 32782
EVENT_OBJECT_PARENTCHANGE = 32783
EVENT_OBJECT_HELPCHANGE = 32784
EVENT_OBJECT_DEFACTIONCHANGE = 32785
EVENT_OBJECT_ACCELERATORCHANGE = 32786
SOUND_SYSTEM_STARTUP = 1
SOUND_SYSTEM_SHUTDOWN = 2
SOUND_SYSTEM_BEEP = 3
SOUND_SYSTEM_ERROR = 4
SOUND_SYSTEM_QUESTION = 5
SOUND_SYSTEM_WARNING = 6
SOUND_SYSTEM_INFORMATION = 7
SOUND_SYSTEM_MAXIMIZE = 8
SOUND_SYSTEM_MINIMIZE = 9
SOUND_SYSTEM_RESTOREUP = 10
SOUND_SYSTEM_RESTOREDOWN = 11
SOUND_SYSTEM_APPSTART = 12
SOUND_SYSTEM_FAULT = 13
SOUND_SYSTEM_APPEND = 14
SOUND_SYSTEM_MENUCOMMAND = 15
SOUND_SYSTEM_MENUPOPUP = 16
CSOUND_SYSTEM = 16
ALERT_SYSTEM_INFORMATIONAL = 1
ALERT_SYSTEM_WARNING = 2
ALERT_SYSTEM_ERROR = 3
ALERT_SYSTEM_QUERY = 4
ALERT_SYSTEM_CRITICAL = 5
CALERT_SYSTEM = 6
WINEVENT_OUTOFCONTEXT = 0
WINEVENT_SKIPOWNTHREAD = 1
WINEVENT_SKIPOWNPROCESS = 2
WINEVENT_INCONTEXT = 4
GUI_CARETBLINKING = 1
GUI_INMOVESIZE = 2
GUI_INMENUMODE = 4
GUI_SYSTEMMENUMODE = 8
GUI_POPUPMENUMODE = 16
STATE_SYSTEM_UNAVAILABLE = 1
STATE_SYSTEM_SELECTED = 2
STATE_SYSTEM_FOCUSED = 4
STATE_SYSTEM_PRESSED = 8
STATE_SYSTEM_CHECKED = 16
STATE_SYSTEM_MIXED = 32
STATE_SYSTEM_READONLY = 64
STATE_SYSTEM_HOTTRACKED = 128
STATE_SYSTEM_DEFAULT = 256
STATE_SYSTEM_EXPANDED = 512
STATE_SYSTEM_COLLAPSED = 1024
STATE_SYSTEM_BUSY = 2048
STATE_SYSTEM_FLOATING = 4096
STATE_SYSTEM_MARQUEED = 8192
STATE_SYSTEM_ANIMATED = 16384
STATE_SYSTEM_INVISIBLE = 32768
STATE_SYSTEM_OFFSCREEN = 65536
STATE_SYSTEM_SIZEABLE = 131072
STATE_SYSTEM_MOVEABLE = 262144
STATE_SYSTEM_SELFVOICING = 524288
STATE_SYSTEM_FOCUSABLE = 1048576
STATE_SYSTEM_SELECTABLE = 2097152
STATE_SYSTEM_LINKED = 4194304
STATE_SYSTEM_TRAVERSED = 8388608
STATE_SYSTEM_MULTISELECTABLE = 16777216
STATE_SYSTEM_EXTSELECTABLE = 33554432
STATE_SYSTEM_ALERT_LOW = 67108864
STATE_SYSTEM_ALERT_MEDIUM = 134217728
STATE_SYSTEM_ALERT_HIGH = 268435456
STATE_SYSTEM_VALID = 536870911
CCHILDREN_TITLEBAR = 5
CCHILDREN_SCROLLBAR = 5
CURSOR_SHOWING = 1
WS_ACTIVECAPTION = 1
GA_MIC = 1
GA_PARENT = 1
GA_ROOT = 2
GA_ROOTOWNER = 3
GA_MAC = 4

# winuser.h line 1979
BF_LEFT = 1
BF_TOP = 2
BF_RIGHT = 4
BF_BOTTOM = 8
BF_TOPLEFT = BF_TOP | BF_LEFT
BF_TOPRIGHT = BF_TOP | BF_RIGHT
BF_BOTTOMLEFT = BF_BOTTOM | BF_LEFT
BF_BOTTOMRIGHT = BF_BOTTOM | BF_RIGHT
BF_RECT = BF_LEFT | BF_TOP | BF_RIGHT | BF_BOTTOM
BF_DIAGONAL = 16
BF_DIAGONAL_ENDTOPRIGHT = BF_DIAGONAL | BF_TOP | BF_RIGHT
BF_DIAGONAL_ENDTOPLEFT = BF_DIAGONAL | BF_TOP | BF_LEFT
BF_DIAGONAL_ENDBOTTOMLEFT = BF_DIAGONAL | BF_BOTTOM | BF_LEFT
BF_DIAGONAL_ENDBOTTOMRIGHT = BF_DIAGONAL | BF_BOTTOM | BF_RIGHT
BF_MIDDLE = 2048
BF_SOFT = 4096
BF_ADJUST = 8192
BF_FLAT = 16384
BF_MONO = 32768
DFC_CAPTION = 1
DFC_MENU = 2
DFC_SCROLL = 3
DFC_BUTTON = 4
DFC_POPUPMENU = 5
DFCS_CAPTIONCLOSE = 0
DFCS_CAPTIONMIN = 1
DFCS_CAPTIONMAX = 2
DFCS_CAPTIONRESTORE = 3
DFCS_CAPTIONHELP = 4
DFCS_MENUARROW = 0
DFCS_MENUCHECK = 1
DFCS_MENUBULLET = 2
DFCS_MENUARROWRIGHT = 4
DFCS_SCROLLUP = 0
DFCS_SCROLLDOWN = 1
DFCS_SCROLLLEFT = 2
DFCS_SCROLLRIGHT = 3
DFCS_SCROLLCOMBOBOX = 5
DFCS_SCROLLSIZEGRIP = 8
DFCS_SCROLLSIZEGRIPRIGHT = 16
DFCS_BUTTONCHECK = 0
DFCS_BUTTONRADIOIMAGE = 1
DFCS_BUTTONRADIOMASK = 2
DFCS_BUTTONRADIO = 4
DFCS_BUTTON3STATE = 8
DFCS_BUTTONPUSH = 16
DFCS_INACTIVE = 256
DFCS_PUSHED = 512
DFCS_CHECKED = 1024
DFCS_TRANSPARENT = 2048
DFCS_HOT = 4096
DFCS_ADJUSTRECT = 8192
DFCS_FLAT = 16384
DFCS_MONO = 32768
DC_ACTIVE = 1
DC_SMALLCAP = 2
DC_ICON = 4
DC_TEXT = 8
DC_INBUTTON = 16
DC_GRADIENT = 32
IDANI_OPEN = 1
IDANI_CLOSE = 2
IDANI_CAPTION = 3
CF_TEXT = 1
CF_BITMAP = 2
CF_METAFILEPICT = 3
CF_SYLK = 4
CF_DIF = 5
CF_TIFF = 6
CF_OEMTEXT = 7
CF_DIB = 8
CF_PALETTE = 9
CF_PENDATA = 10
CF_RIFF = 11
CF_WAVE = 12
CF_UNICODETEXT = 13
CF_ENHMETAFILE = 14
CF_HDROP = 15
CF_LOCALE = 16
CF_DIBV5 = 17
CF_MAX = 18
CF_OWNERDISPLAY = 128
CF_DSPTEXT = 129
CF_DSPBITMAP = 130
CF_DSPMETAFILEPICT = 131
CF_DSPENHMETAFILE = 142
CF_PRIVATEFIRST = 512
CF_PRIVATELAST = 767
CF_GDIOBJFIRST = 768
CF_GDIOBJLAST = 1023
FVIRTKEY = 1
FNOINVERT = 2
FSHIFT = 4
FCONTROL = 8
FALT = 16
WPF_SETMINPOSITION = 1
WPF_RESTORETOMAXIMIZED = 2
ODT_MENU = 1
ODT_LISTBOX = 2
ODT_COMBOBOX = 3
ODT_BUTTON = 4
ODT_STATIC = 5
ODA_DRAWENTIRE = 1
ODA_SELECT = 2
ODA_FOCUS = 4
ODS_SELECTED = 1
ODS_GRAYED = 2
ODS_DISABLED = 4
ODS_CHECKED = 8
ODS_FOCUS = 16
ODS_DEFAULT = 32
ODS_COMBOBOXEDIT = 4096
ODS_HOTLIGHT = 64
ODS_INACTIVE = 128
PM_NOREMOVE = 0
PM_REMOVE = 1
PM_NOYIELD = 2
MOD_ALT = 1
MOD_CONTROL = 2
MOD_SHIFT = 4
MOD_WIN = 8
MOD_NOREPEAT = 16384
IDHOT_SNAPWINDOW = -1
IDHOT_SNAPDESKTOP = -2
# EW_RESTARTWINDOWS = 0x0042
# EW_REBOOTSYSTEM = 0x0043
# EW_EXITANDEXECAPP = 0x0044
ENDSESSION_LOGOFF = -2147483648
EWX_LOGOFF = 0
EWX_SHUTDOWN = 1
EWX_REBOOT = 2
EWX_FORCE = 4
EWX_POWEROFF = 8
EWX_FORCEIFHUNG = 16
BSM_ALLDESKTOPS = 16
BROADCAST_QUERY_DENY = 1112363332  # Return this value to deny a query.

DBWF_LPARAMPOINTER = 32768

# winuser.h line 3232
SWP_NOSIZE = 1
SWP_NOMOVE = 2
SWP_NOZORDER = 4
SWP_NOREDRAW = 8
SWP_NOACTIVATE = 16
SWP_FRAMECHANGED = 32
SWP_SHOWWINDOW = 64
SWP_HIDEWINDOW = 128
SWP_NOCOPYBITS = 256
SWP_NOOWNERZORDER = 512
SWP_NOSENDCHANGING = 1024
SWP_DRAWFRAME = SWP_FRAMECHANGED
SWP_NOREPOSITION = SWP_NOOWNERZORDER
SWP_DEFERERASE = 8192
SWP_ASYNCWINDOWPOS = 16384

DLGWINDOWEXTRA = 30
# winuser.h line 4249
KEYEVENTF_EXTENDEDKEY = 1
KEYEVENTF_KEYUP = 2
KEYEVENTF_UNICODE = 4
KEYEVENTF_SCANCODE = 8
MOUSEEVENTF_MOVE = 1
MOUSEEVENTF_LEFTDOWN = 2
MOUSEEVENTF_LEFTUP = 4
MOUSEEVENTF_RIGHTDOWN = 8
MOUSEEVENTF_RIGHTUP = 16
MOUSEEVENTF_MIDDLEDOWN = 32
MOUSEEVENTF_MIDDLEUP = 64
MOUSEEVENTF_XDOWN = 128
MOUSEEVENTF_XUP = 256
MOUSEEVENTF_WHEEL = 2048
MOUSEEVENTF_HWHEEL = 4096
MOUSEEVENTF_MOVE_NOCOALESCE = 8192
MOUSEEVENTF_VIRTUALDESK = 16384
MOUSEEVENTF_ABSOLUTE = 32768
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2
MWMO_WAITALL = 1
MWMO_ALERTABLE = 2
MWMO_INPUTAVAILABLE = 4
QS_KEY = 1
QS_MOUSEMOVE = 2
QS_MOUSEBUTTON = 4
QS_POSTMESSAGE = 8
QS_TIMER = 16
QS_PAINT = 32
QS_SENDMESSAGE = 64
QS_HOTKEY = 128
QS_MOUSE = QS_MOUSEMOVE | QS_MOUSEBUTTON
QS_INPUT = QS_MOUSE | QS_KEY
QS_ALLEVENTS = QS_INPUT | QS_POSTMESSAGE | QS_TIMER | QS_PAINT | QS_HOTKEY
QS_ALLINPUT = (
    QS_INPUT | QS_POSTMESSAGE | QS_TIMER | QS_PAINT | QS_HOTKEY | QS_SENDMESSAGE
)


IMN_CLOSESTATUSWINDOW = 1
IMN_OPENSTATUSWINDOW = 2
IMN_CHANGECANDIDATE = 3
IMN_CLOSECANDIDATE = 4
IMN_OPENCANDIDATE = 5
IMN_SETCONVERSIONMODE = 6
IMN_SETSENTENCEMODE = 7
IMN_SETOPENSTATUS = 8
IMN_SETCANDIDATEPOS = 9
IMN_SETCOMPOSITIONFONT = 10
IMN_SETCOMPOSITIONWINDOW = 11
IMN_SETSTATUSWINDOWPOS = 12
IMN_GUIDELINE = 13
IMN_PRIVATE = 14

# winuser.h line 8518
HELP_CONTEXT = 1
HELP_QUIT = 2
HELP_INDEX = 3
HELP_CONTENTS = 3
HELP_HELPONHELP = 4
HELP_SETINDEX = 5
HELP_SETCONTENTS = 5
HELP_CONTEXTPOPUP = 8
HELP_FORCEFILE = 9
HELP_KEY = 257
HELP_COMMAND = 258
HELP_PARTIALKEY = 261
HELP_MULTIKEY = 513
HELP_SETWINPOS = 515
HELP_CONTEXTMENU = 10
HELP_FINDER = 11
HELP_WM_HELP = 12
HELP_SETPOPUP_POS = 13
HELP_TCARD = 32768
HELP_TCARD_DATA = 16
HELP_TCARD_OTHER_CALLER = 17
IDH_NO_HELP = 28440
IDH_MISSING_CONTEXT = 28441  # Control doesn't have matching help context
IDH_GENERIC_HELP_BUTTON = 28442  # Property sheet help button
IDH_OK = 28443
IDH_CANCEL = 28444
IDH_HELP = 28445
GR_GDIOBJECTS = 0  # Count of GDI objects
GR_USEROBJECTS = 1  # Count of USER objects
# Generated by h2py from \msvcnt\include\wingdi.h
# manually added (missed by generation some how!
SRCCOPY = 13369376  # dest = source
SRCPAINT = 15597702  # dest = source OR dest
SRCAND = 8913094  # dest = source AND dest
SRCINVERT = 6684742  # dest = source XOR dest
SRCERASE = 4457256  # dest = source AND (NOT dest )
NOTSRCCOPY = 3342344  # dest = (NOT source)
NOTSRCERASE = 1114278  # dest = (NOT src) AND (NOT dest)
MERGECOPY = 12583114  # dest = (source AND pattern)
MERGEPAINT = 12255782  # dest = (NOT source) OR dest
PATCOPY = 15728673  # dest = pattern
PATPAINT = 16452105  # dest = DPSnoo
PATINVERT = 5898313  # dest = pattern XOR dest
DSTINVERT = 5570569  # dest = (NOT dest)
BLACKNESS = 66  # dest = BLACK
WHITENESS = 16711778  # dest = WHITE

# hacked and split manually by mhammond.
R2_BLACK = 1
R2_NOTMERGEPEN = 2
R2_MASKNOTPEN = 3
R2_NOTCOPYPEN = 4
R2_MASKPENNOT = 5
R2_NOT = 6
R2_XORPEN = 7
R2_NOTMASKPEN = 8
R2_MASKPEN = 9
R2_NOTXORPEN = 10
R2_NOP = 11
R2_MERGENOTPEN = 12
R2_COPYPEN = 13
R2_MERGEPENNOT = 14
R2_MERGEPEN = 15
R2_WHITE = 16
R2_LAST = 16
GDI_ERROR = -1
ERROR = 0
NULLREGION = 1
SIMPLEREGION = 2
COMPLEXREGION = 3
RGN_ERROR = ERROR
RGN_AND = 1
RGN_OR = 2
RGN_XOR = 3
RGN_DIFF = 4
RGN_COPY = 5
RGN_MIN = RGN_AND
RGN_MAX = RGN_COPY

## Stretching modes used with Get/SetStretchBltMode
BLACKONWHITE = 1
WHITEONBLACK = 2
COLORONCOLOR = 3
HALFTONE = 4
MAXSTRETCHBLTMODE = 4
STRETCH_ANDSCANS = BLACKONWHITE
STRETCH_ORSCANS = WHITEONBLACK
STRETCH_DELETESCANS = COLORONCOLOR
STRETCH_HALFTONE = HALFTONE

ALTERNATE = 1
WINDING = 2
POLYFILL_LAST = 2

## flags used with SetLayout
LAYOUT_RTL = 1
LAYOUT_BTT = 2
LAYOUT_VBH = 4
LAYOUT_ORIENTATIONMASK = LAYOUT_RTL | LAYOUT_BTT | LAYOUT_VBH
LAYOUT_BITMAPORIENTATIONPRESERVED = 8

TA_NOUPDATECP = 0
TA_UPDATECP = 1
TA_LEFT = 0
TA_RIGHT = 2
TA_CENTER = 6
TA_TOP = 0
TA_BOTTOM = 8
TA_BASELINE = 24
TA_MASK = TA_BASELINE + TA_CENTER + TA_UPDATECP
VTA_BASELINE = TA_BASELINE
VTA_LEFT = TA_BOTTOM
VTA_RIGHT = TA_TOP
VTA_CENTER = TA_CENTER
VTA_BOTTOM = TA_RIGHT
VTA_TOP = TA_LEFT
ETO_GRAYED = 1
ETO_OPAQUE = 2
ETO_CLIPPED = 4
ASPECT_FILTERING = 1
DCB_RESET = 1
DCB_ACCUMULATE = 2
DCB_DIRTY = DCB_ACCUMULATE
DCB_SET = DCB_RESET | DCB_ACCUMULATE
DCB_ENABLE = 4
DCB_DISABLE = 8
META_SETBKCOLOR = 513
META_SETBKMODE = 258
META_SETMAPMODE = 259
META_SETROP2 = 260
META_SETRELABS = 261
META_SETPOLYFILLMODE = 262
META_SETSTRETCHBLTMODE = 263
META_SETTEXTCHAREXTRA = 264
META_SETTEXTCOLOR = 521
META_SETTEXTJUSTIFICATION = 522
META_SETWINDOWORG = 523
META_SETWINDOWEXT = 524
META_SETVIEWPORTORG = 525
META_SETVIEWPORTEXT = 526
META_OFFSETWINDOWORG = 527
META_SCALEWINDOWEXT = 1040
META_OFFSETVIEWPORTORG = 529
META_SCALEVIEWPORTEXT = 1042
META_LINETO = 531
META_MOVETO = 532
META_EXCLUDECLIPRECT = 1045
META_INTERSECTCLIPRECT = 1046
META_ARC = 2071
META_ELLIPSE = 1048
META_FLOODFILL = 1049
META_PIE = 2074
META_RECTANGLE = 1051
META_ROUNDRECT = 1564
META_PATBLT = 1565
META_SAVEDC = 30
META_SETPIXEL = 1055
META_OFFSETCLIPRGN = 544
META_TEXTOUT = 1313
META_BITBLT = 2338
META_STRETCHBLT = 2851
META_POLYGON = 804
META_POLYLINE = 805
META_ESCAPE = 1574
META_RESTOREDC = 295
META_FILLREGION = 552
META_FRAMEREGION = 1065
META_INVERTREGION = 298
META_PAINTREGION = 299
META_SELECTCLIPREGION = 300
META_SELECTOBJECT = 301
META_SETTEXTALIGN = 302
META_CHORD = 2096
META_SETMAPPERFLAGS = 561
META_EXTTEXTOUT = 2610
META_SETDIBTODEV = 3379
META_SELECTPALETTE = 564
META_REALIZEPALETTE = 53
META_ANIMATEPALETTE = 1078
META_SETPALENTRIES = 55
META_POLYPOLYGON = 1336
META_RESIZEPALETTE = 313
META_DIBBITBLT = 2368
META_DIBSTRETCHBLT = 2881
META_DIBCREATEPATTERNBRUSH = 322
META_STRETCHDIB = 3907
META_EXTFLOODFILL = 1352
META_DELETEOBJECT = 496
META_CREATEPALETTE = 247
META_CREATEPATTERNBRUSH = 505
META_CREATEPENINDIRECT = 762
META_CREATEFONTINDIRECT = 763
META_CREATEBRUSHINDIRECT = 764
META_CREATEREGION = 1791
FILE_BEGIN = 0
FILE_CURRENT = 1
FILE_END = 2
FILE_FLAG_WRITE_THROUGH = -2147483648
FILE_FLAG_OVERLAPPED = 1073741824
FILE_FLAG_NO_BUFFERING = 536870912
FILE_FLAG_RANDOM_ACCESS = 268435456
FILE_FLAG_SEQUENTIAL_SCAN = 134217728
FILE_FLAG_DELETE_ON_CLOSE = 67108864
FILE_FLAG_BACKUP_SEMANTICS = 33554432
FILE_FLAG_POSIX_SEMANTICS = 16777216
CREATE_NEW = 1
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
TRUNCATE_EXISTING = 5
PIPE_ACCESS_INBOUND = 1
PIPE_ACCESS_OUTBOUND = 2
PIPE_ACCESS_DUPLEX = 3
PIPE_CLIENT_END = 0
PIPE_SERVER_END = 1
PIPE_WAIT = 0
PIPE_NOWAIT = 1
PIPE_READMODE_BYTE = 0
PIPE_READMODE_MESSAGE = 2
PIPE_TYPE_BYTE = 0
PIPE_TYPE_MESSAGE = 4
PIPE_UNLIMITED_INSTANCES = 255
SECURITY_CONTEXT_TRACKING = 262144
SECURITY_EFFECTIVE_ONLY = 524288
SECURITY_SQOS_PRESENT = 1048576
SECURITY_VALID_SQOS_FLAGS = 2031616
DTR_CONTROL_DISABLE = 0
DTR_CONTROL_ENABLE = 1
DTR_CONTROL_HANDSHAKE = 2
RTS_CONTROL_DISABLE = 0
RTS_CONTROL_ENABLE = 1
RTS_CONTROL_HANDSHAKE = 2
RTS_CONTROL_TOGGLE = 3
GMEM_FIXED = 0
GMEM_MOVEABLE = 2
GMEM_NOCOMPACT = 16
GMEM_NODISCARD = 32
GMEM_ZEROINIT = 64
GMEM_MODIFY = 128
GMEM_DISCARDABLE = 256
GMEM_NOT_BANKED = 4096
GMEM_SHARE = 8192
GMEM_DDESHARE = 8192
GMEM_NOTIFY = 16384
GMEM_LOWER = GMEM_NOT_BANKED
GMEM_VALID_FLAGS = 32626
GMEM_INVALID_HANDLE = 32768
GHND = GMEM_MOVEABLE | GMEM_ZEROINIT
GPTR = GMEM_FIXED | GMEM_ZEROINIT
GMEM_DISCARDED = 16384
GMEM_LOCKCOUNT = 255
LMEM_FIXED = 0
LMEM_MOVEABLE = 2
LMEM_NOCOMPACT = 16
LMEM_NODISCARD = 32
LMEM_ZEROINIT = 64
LMEM_MODIFY = 128
LMEM_DISCARDABLE = 3840
LMEM_VALID_FLAGS = 3954
LMEM_INVALID_HANDLE = 32768
LHND = LMEM_MOVEABLE | LMEM_ZEROINIT
LPTR = LMEM_FIXED | LMEM_ZEROINIT
NONZEROLHND = LMEM_MOVEABLE
NONZEROLPTR = LMEM_FIXED
LMEM_DISCARDED = 16384
LMEM_LOCKCOUNT = 255
DEBUG_PROCESS = 1
DEBUG_ONLY_THIS_PROCESS = 2
CREATE_SUSPENDED = 4
DETACHED_PROCESS = 8
CREATE_NEW_CONSOLE = 16
NORMAL_PRIORITY_CLASS = 32
IDLE_PRIORITY_CLASS = 64
HIGH_PRIORITY_CLASS = 128
REALTIME_PRIORITY_CLASS = 256
CREATE_NEW_PROCESS_GROUP = 512
CREATE_UNICODE_ENVIRONMENT = 1024
CREATE_SEPARATE_WOW_VDM = 2048
CREATE_SHARED_WOW_VDM = 4096
CREATE_DEFAULT_ERROR_MODE = 67108864
CREATE_NO_WINDOW = 134217728
PROFILE_USER = 268435456
PROFILE_KERNEL = 536870912
PROFILE_SERVER = 1073741824
THREAD_BASE_PRIORITY_LOWRT = 15
THREAD_BASE_PRIORITY_MAX = 2
THREAD_BASE_PRIORITY_MIN = -2
THREAD_BASE_PRIORITY_IDLE = -15
THREAD_PRIORITY_LOWEST = THREAD_BASE_PRIORITY_MIN
THREAD_PRIORITY_BELOW_NORMAL = THREAD_PRIORITY_LOWEST + 1
THREAD_PRIORITY_HIGHEST = THREAD_BASE_PRIORITY_MAX
THREAD_PRIORITY_ABOVE_NORMAL = THREAD_PRIORITY_HIGHEST - 1
THREAD_PRIORITY_ERROR_RETURN = MAXLONG
THREAD_PRIORITY_TIME_CRITICAL = THREAD_BASE_PRIORITY_LOWRT
THREAD_PRIORITY_IDLE = THREAD_BASE_PRIORITY_IDLE
THREAD_PRIORITY_NORMAL = 0
THREAD_MODE_BACKGROUND_BEGIN = 0x00010000
THREAD_MODE_BACKGROUND_END = 0x00020000

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
RIP_EVENT = 9
DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_REMOTE = 4
DRIVE_CDROM = 5
DRIVE_RAMDISK = 6
FILE_TYPE_UNKNOWN = 0
FILE_TYPE_DISK = 1
FILE_TYPE_CHAR = 2
FILE_TYPE_PIPE = 3
FILE_TYPE_REMOTE = 32768
NOPARITY = 0
ODDPARITY = 1
EVENPARITY = 2
MARKPARITY = 3
SPACEPARITY = 4
ONESTOPBIT = 0
ONE5STOPBITS = 1
TWOSTOPBITS = 2
CBR_110 = 110
CBR_300 = 300
CBR_600 = 600
CBR_1200 = 1200
CBR_2400 = 2400
CBR_4800 = 4800
CBR_9600 = 9600
CBR_14400 = 14400
CBR_19200 = 19200
CBR_38400 = 38400
CBR_56000 = 56000
CBR_57600 = 57600
CBR_115200 = 115200
CBR_128000 = 128000
CBR_256000 = 256000
S_QUEUEEMPTY = 0
S_THRESHOLD = 1
S_ALLTHRESHOLD = 2
S_NORMAL = 0
S_LEGATO = 1
S_STACCATO = 2
NMPWAIT_WAIT_FOREVER = -1
NMPWAIT_NOWAIT = 1
NMPWAIT_USE_DEFAULT_WAIT = 0
OF_READ = 0
OF_WRITE = 1
OF_READWRITE = 2
OF_SHARE_COMPAT = 0
OF_SHARE_EXCLUSIVE = 16
OF_SHARE_DENY_WRITE = 32
OF_SHARE_DENY_READ = 48
OF_SHARE_DENY_NONE = 64
OF_PARSE = 256
OF_DELETE = 512
OF_VERIFY = 1024
OF_CANCEL = 2048
OF_CREATE = 4096
OF_PROMPT = 8192
OF_EXIST = 16384
OF_REOPEN = 32768
OFS_MAXPATHNAME = 128
MAXINTATOM = 49152

# winbase.h
PROCESS_HEAP_REGION = 1
PROCESS_HEAP_UNCOMMITTED_RANGE = 2
PROCESS_HEAP_ENTRY_BUSY = 4
PROCESS_HEAP_ENTRY_MOVEABLE = 16
PROCESS_HEAP_ENTRY_DDESHARE = 32
SCS_32BIT_BINARY = 0
SCS_DOS_BINARY = 1
SCS_WOW_BINARY = 2
SCS_PIF_BINARY = 3
SCS_POSIX_BINARY = 4
SCS_OS216_BINARY = 5
SEM_FAILCRITICALERRORS = 1
SEM_NOGPFAULTERRORBOX = 2
SEM_NOALIGNMENTFAULTEXCEPT = 4
SEM_NOOPENFILEERRORBOX = 32768
LOCKFILE_FAIL_IMMEDIATELY = 1
LOCKFILE_EXCLUSIVE_LOCK = 2
HANDLE_FLAG_INHERIT = 1
HANDLE_FLAG_PROTECT_FROM_CLOSE = 2
HINSTANCE_ERROR = 32
GET_TAPE_MEDIA_INFORMATION = 0
GET_TAPE_DRIVE_INFORMATION = 1
SET_TAPE_MEDIA_INFORMATION = 0
SET_TAPE_DRIVE_INFORMATION = 1
FORMAT_MESSAGE_ALLOCATE_BUFFER = 256
FORMAT_MESSAGE_IGNORE_INSERTS = 512
FORMAT_MESSAGE_FROM_STRING = 1024
FORMAT_MESSAGE_FROM_HMODULE = 2048
FORMAT_MESSAGE_FROM_SYSTEM = 4096
FORMAT_MESSAGE_ARGUMENT_ARRAY = 8192
FORMAT_MESSAGE_MAX_WIDTH_MASK = 255
BACKUP_INVALID = 0
BACKUP_DATA = 1
BACKUP_EA_DATA = 2
BACKUP_SECURITY_DATA = 3
BACKUP_ALTERNATE_DATA = 4
BACKUP_LINK = 5
BACKUP_PROPERTY_DATA = 6
BACKUP_OBJECT_ID = 7
BACKUP_REPARSE_DATA = 8
BACKUP_SPARSE_BLOCK = 9

STREAM_NORMAL_ATTRIBUTE = 0
STREAM_MODIFIED_WHEN_READ = 1
STREAM_CONTAINS_SECURITY = 2
STREAM_CONTAINS_PROPERTIES = 4
STARTF_USESHOWWINDOW = 1
STARTF_USESIZE = 2
STARTF_USEPOSITION = 4
STARTF_USECOUNTCHARS = 8
STARTF_USEFILLATTRIBUTE = 16
STARTF_FORCEONFEEDBACK = 64
STARTF_FORCEOFFFEEDBACK = 128
STARTF_USESTDHANDLES = 256
STARTF_USEHOTKEY = 512
SHUTDOWN_NORETRY = 1
DONT_RESOLVE_DLL_REFERENCES = 1
LOAD_LIBRARY_AS_DATAFILE = 2
LOAD_WITH_ALTERED_SEARCH_PATH = 8
DDD_RAW_TARGET_PATH = 1
DDD_REMOVE_DEFINITION = 2
DDD_EXACT_MATCH_ON_REMOVE = 4
MOVEFILE_REPLACE_EXISTING = 1
MOVEFILE_COPY_ALLOWED = 2
MOVEFILE_DELAY_UNTIL_REBOOT = 4
MAX_COMPUTERNAME_LENGTH = 15
LOGON32_LOGON_INTERACTIVE = 2
LOGON32_LOGON_NETWORK = 3
LOGON32_LOGON_BATCH = 4
LOGON32_LOGON_SERVICE = 5
LOGON32_LOGON_UNLOCK = 7
LOGON32_LOGON_NETWORK_CLEARTEXT = 8
LOGON32_LOGON_NEW_CREDENTIALS = 9
LOGON32_PROVIDER_DEFAULT = 0
LOGON32_PROVIDER_WINNT35 = 1
LOGON32_PROVIDER_WINNT40 = 2
LOGON32_PROVIDER_WINNT50 = 3
VER_PLATFORM_WIN32s = 0
VER_PLATFORM_WIN32_WINDOWS = 1
VER_PLATFORM_WIN32_NT = 2
TC_NORMAL = 0
TC_HARDERR = 1
TC_GP_TRAP = 2
TC_SIGNAL = 3
AC_LINE_OFFLINE = 0
AC_LINE_ONLINE = 1
AC_LINE_BACKUP_POWER = 2
AC_LINE_UNKNOWN = 255
BATTERY_FLAG_HIGH = 1
BATTERY_FLAG_LOW = 2
BATTERY_FLAG_CRITICAL = 4
BATTERY_FLAG_CHARGING = 8
BATTERY_FLAG_NO_BATTERY = 128
BATTERY_FLAG_UNKNOWN = 255
BATTERY_PERCENTAGE_UNKNOWN = 255
BATTERY_LIFE_UNKNOWN = -1

# Generated by h2py from d:\msdev\include\richedit.h
cchTextLimitDefault = 32767
WM_CONTEXTMENU = 123
WM_PRINTCLIENT = 792
EN_MSGFILTER = 1792
EN_REQUESTRESIZE = 1793
EN_SELCHANGE = 1794
EN_DROPFILES = 1795
EN_PROTECTED = 1796
EN_CORRECTTEXT = 1797
EN_STOPNOUNDO = 1798
EN_IMECHANGE = 1799
EN_SAVECLIPBOARD = 1800
EN_OLEOPFAILED = 1801
ENM_NONE = 0
ENM_CHANGE = 1
ENM_UPDATE = 2
ENM_SCROLL = 4
ENM_KEYEVENTS = 65536
ENM_MOUSEEVENTS = 131072
ENM_REQUESTRESIZE = 262144
ENM_SELCHANGE = 524288
ENM_DROPFILES = 1048576
ENM_PROTECTED = 2097152
ENM_CORRECTTEXT = 4194304
ENM_IMECHANGE = 8388608
ES_SAVESEL = 32768
ES_SUNKEN = 16384
ES_DISABLENOSCROLL = 8192
ES_SELECTIONBAR = 16777216
ES_EX_NOCALLOLEINIT = 16777216
ES_VERTICAL = 4194304
ES_NOIME = 524288
ES_SELFIME = 262144
ECO_AUTOWORDSELECTION = 1
ECO_AUTOVSCROLL = 64
ECO_AUTOHSCROLL = 128
ECO_NOHIDESEL = 256
ECO_READONLY = 2048
ECO_WANTRETURN = 4096
ECO_SAVESEL = 32768
ECO_SELECTIONBAR = 16777216
ECO_VERTICAL = 4194304
ECOOP_SET = 1
ECOOP_OR = 2
ECOOP_AND = 3
ECOOP_XOR = 4
WB_CLASSIFY = 3
WB_MOVEWORDLEFT = 4
WB_MOVEWORDRIGHT = 5
WB_LEFTBREAK = 6
WB_RIGHTBREAK = 7
WB_MOVEWORDPREV = 4
WB_MOVEWORDNEXT = 5
WB_PREVBREAK = 6
WB_NEXTBREAK = 7
PC_FOLLOWING = 1
PC_LEADING = 2
PC_OVERFLOW = 3
PC_DELIMITER = 4
WBF_WORDWRAP = 16
WBF_WORDBREAK = 32
WBF_OVERFLOW = 64
WBF_LEVEL1 = 128
WBF_LEVEL2 = 256
WBF_CUSTOM = 512
CFM_BOLD = 1
CFM_ITALIC = 2
CFM_UNDERLINE = 4
CFM_STRIKEOUT = 8
CFM_PROTECTED = 16
CFM_SIZE = -2147483648
CFM_COLOR = 1073741824
CFM_FACE = 536870912
CFM_OFFSET = 268435456
CFM_CHARSET = 134217728
CFE_BOLD = 1
CFE_ITALIC = 2
CFE_UNDERLINE = 4
CFE_STRIKEOUT = 8
CFE_PROTECTED = 16
CFE_AUTOCOLOR = 1073741824
yHeightCharPtsMost = 1638
SCF_SELECTION = 1
SCF_WORD = 2
SF_TEXT = 1
SF_RTF = 2
SF_RTFNOOBJS = 3
SF_TEXTIZED = 4
SFF_SELECTION = 32768
SFF_PLAINRTF = 16384
MAX_TAB_STOPS = 32
lDefaultTab = 720
PFM_STARTINDENT = 1
PFM_RIGHTINDENT = 2
PFM_OFFSET = 4
PFM_ALIGNMENT = 8
PFM_TABSTOPS = 16
PFM_NUMBERING = 32
PFM_OFFSETINDENT = -2147483648
PFN_BULLET = 1
PFA_LEFT = 1
PFA_RIGHT = 2
PFA_CENTER = 3
WM_NOTIFY = 78
SEL_EMPTY = 0
SEL_TEXT = 1
SEL_OBJECT = 2
SEL_MULTICHAR = 4
SEL_MULTIOBJECT = 8
OLEOP_DOVERB = 1
CF_RTF = "Rich Text Format"
CF_RTFNOOBJS = "Rich Text Format Without Objects"
CF_RETEXTOBJ = "RichEdit Text and Objects"

# From wincon.h
RIGHT_ALT_PRESSED = 1  # the right alt key is pressed.
LEFT_ALT_PRESSED = 2  # the left alt key is pressed.
RIGHT_CTRL_PRESSED = 4  # the right ctrl key is pressed.
LEFT_CTRL_PRESSED = 8  # the left ctrl key is pressed.
SHIFT_PRESSED = 16  # the shift key is pressed.
NUMLOCK_ON = 32  # the numlock light is on.
SCROLLLOCK_ON = 64  # the scrolllock light is on.
CAPSLOCK_ON = 128  # the capslock light is on.
ENHANCED_KEY = 256  # the key is enhanced.
NLS_DBCSCHAR = 65536  # DBCS for JPN: SBCS/DBCS mode.
NLS_ALPHANUMERIC = 0  # DBCS for JPN: Alphanumeric mode.
NLS_KATAKANA = 131072  # DBCS for JPN: Katakana mode.
NLS_HIRAGANA = 262144  # DBCS for JPN: Hiragana mode.
NLS_ROMAN = 4194304  # DBCS for JPN: Roman/Noroman mode.
NLS_IME_CONVERSION = 8388608  # DBCS for JPN: IME conversion.
NLS_IME_DISABLE = 536870912  # DBCS for JPN: IME enable/disable.

FROM_LEFT_1ST_BUTTON_PRESSED = 1
RIGHTMOST_BUTTON_PRESSED = 2
FROM_LEFT_2ND_BUTTON_PRESSED = 4
FROM_LEFT_3RD_BUTTON_PRESSED = 8
FROM_LEFT_4TH_BUTTON_PRESSED = 16

CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2
CTRL_LOGOFF_EVENT = 5
CTRL_SHUTDOWN_EVENT = 6

MOUSE_MOVED = 1
DOUBLE_CLICK = 2
MOUSE_WHEELED = 4

# property sheet window messages from prsht.h
PSM_SETCURSEL = WM_USER + 101
PSM_REMOVEPAGE = WM_USER + 102
PSM_ADDPAGE = WM_USER + 103
PSM_CHANGED = WM_USER + 104
PSM_RESTARTWINDOWS = WM_USER + 105
PSM_REBOOTSYSTEM = WM_USER + 106
PSM_CANCELTOCLOSE = WM_USER + 107
PSM_QUERYSIBLINGS = WM_USER + 108
PSM_UNCHANGED = WM_USER + 109
PSM_APPLY = WM_USER + 110
PSM_SETTITLEA = WM_USER + 111
PSM_SETTITLEW = WM_USER + 120
PSM_SETWIZBUTTONS = WM_USER + 112
PSM_PRESSBUTTON = WM_USER + 113
PSM_SETCURSELID = WM_USER + 114
PSM_SETFINISHTEXTA = WM_USER + 115
PSM_SETFINISHTEXTW = WM_USER + 121
PSM_GETTABCONTROL = WM_USER + 116
PSM_ISDIALOGMESSAGE = WM_USER + 117
PSM_GETCURRENTPAGEHWND = WM_USER + 118
PSM_INSERTPAGE = WM_USER + 119
PSM_SETHEADERTITLEA = WM_USER + 125
PSM_SETHEADERTITLEW = WM_USER + 126
PSM_SETHEADERSUBTITLEA = WM_USER + 127
PSM_SETHEADERSUBTITLEW = WM_USER + 128
PSM_HWNDTOINDEX = WM_USER + 129
PSM_INDEXTOHWND = WM_USER + 130
PSM_PAGETOINDEX = WM_USER + 131
PSM_INDEXTOPAGE = WM_USER + 132
PSM_IDTOINDEX = WM_USER + 133
PSM_INDEXTOID = WM_USER + 134
PSM_GETRESULT = WM_USER + 135
PSM_RECALCPAGESIZES = WM_USER + 136

# GetUserNameEx/GetComputerNameEx
NameUnknown = 0
NameFullyQualifiedDN = 1
NameSamCompatible = 2
NameDisplay = 3
NameUniqueId = 6
NameCanonical = 7
NameUserPrincipal = 8
NameCanonicalEx = 9
NameServicePrincipal = 10
NameDnsDomain = 12

ComputerNameNetBIOS = 0
ComputerNameDnsHostname = 1
ComputerNameDnsDomain = 2
ComputerNameDnsFullyQualified = 3
ComputerNamePhysicalNetBIOS = 4
ComputerNamePhysicalDnsHostname = 5
ComputerNamePhysicalDnsDomain = 6
ComputerNamePhysicalDnsFullyQualified = 7

LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002
ULW_COLORKEY = 0x00000001
ULW_ALPHA = 0x00000002
ULW_OPAQUE = 0x00000004

# WinDef.h
TRUE = 1
FALSE = 0
MAX_PATH = 260
# WinGDI.h
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
GRADIENT_FILL_RECT_H = 0
GRADIENT_FILL_RECT_V = 1
GRADIENT_FILL_TRIANGLE = 2
GRADIENT_FILL_OP_FLAG = 255

## flags used with Get/SetSystemFileCacheSize
MM_WORKING_SET_MAX_HARD_ENABLE = 1
MM_WORKING_SET_MAX_HARD_DISABLE = 2
MM_WORKING_SET_MIN_HARD_ENABLE = 4
MM_WORKING_SET_MIN_HARD_DISABLE = 8

## Flags for GetFinalPathNameByHandle
VOLUME_NAME_DOS = 0
VOLUME_NAME_GUID = 1
VOLUME_NAME_NT = 2
VOLUME_NAME_NONE = 4
FILE_NAME_NORMALIZED = 0
FILE_NAME_OPENED = 8

DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000
DEVICE_NOTIFY_SERVICE_HANDLE = 0x00000001

# From Dbt.h
# Generated by h2py from Dbt.h
WM_DEVICECHANGE = 0x0219
BSF_QUERY = 0x00000001
BSF_IGNORECURRENTTASK = 0x00000002
BSF_FLUSHDISK = 0x00000004
BSF_NOHANG = 0x00000008
BSF_POSTMESSAGE = 0x00000010
BSF_FORCEIFHUNG = 0x00000020
BSF_NOTIMEOUTIFNOTHUNG = 0x00000040
BSF_MSGSRV32ISOK = -2147483648
BSF_MSGSRV32ISOK_BIT = 31
BSM_ALLCOMPONENTS = 0x00000000
BSM_VXDS = 0x00000001
BSM_NETDRIVER = 0x00000002
BSM_INSTALLABLEDRIVERS = 0x00000004
BSM_APPLICATIONS = 0x00000008
DBT_APPYBEGIN = 0x0000
DBT_APPYEND = 0x0001
DBT_DEVNODES_CHANGED = 0x0007
DBT_QUERYCHANGECONFIG = 0x0017
DBT_CONFIGCHANGED = 0x0018
DBT_CONFIGCHANGECANCELED = 0x0019
DBT_MONITORCHANGE = 0x001B
DBT_SHELLLOGGEDON = 0x0020
DBT_CONFIGMGAPI32 = 0x0022
DBT_VXDINITCOMPLETE = 0x0023
DBT_VOLLOCKQUERYLOCK = 0x8041
DBT_VOLLOCKLOCKTAKEN = 0x8042
DBT_VOLLOCKLOCKFAILED = 0x8043
DBT_VOLLOCKQUERYUNLOCK = 0x8044
DBT_VOLLOCKLOCKRELEASED = 0x8045
DBT_VOLLOCKUNLOCKFAILED = 0x8046
LOCKP_ALLOW_WRITES = 0x01
LOCKP_FAIL_WRITES = 0x00
LOCKP_FAIL_MEM_MAPPING = 0x02
LOCKP_ALLOW_MEM_MAPPING = 0x00
LOCKP_USER_MASK = 0x03
LOCKP_LOCK_FOR_FORMAT = 0x04
LOCKF_LOGICAL_LOCK = 0x00
LOCKF_PHYSICAL_LOCK = 0x01
DBT_NO_DISK_SPACE = 0x0047
DBT_LOW_DISK_SPACE = 0x0048
DBT_CONFIGMGPRIVATE = 0x7FFF
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEQUERYREMOVE = 0x8001
DBT_DEVICEQUERYREMOVEFAILED = 0x8002
DBT_DEVICEREMOVEPENDING = 0x8003
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVICETYPESPECIFIC = 0x8005
DBT_CUSTOMEVENT = 0x8006
DBT_DEVTYP_OEM = 0x00000000
DBT_DEVTYP_DEVNODE = 0x00000001
DBT_DEVTYP_VOLUME = 0x00000002
DBT_DEVTYP_PORT = 0x00000003
DBT_DEVTYP_NET = 0x00000004
DBT_DEVTYP_DEVICEINTERFACE = 0x00000005
DBT_DEVTYP_HANDLE = 0x00000006
DBTF_MEDIA = 0x0001
DBTF_NET = 0x0002
DBTF_RESOURCE = 0x00000001
DBTF_XPORT = 0x00000002
DBTF_SLOWNET = 0x00000004
DBT_VPOWERDAPI = 0x8100
DBT_USERDEFINED = 0xFFFF

# From ime_cmodes.h
# bit field for conversion mode
IME_CMODE_ALPHANUMERIC = 0x0000
IME_CMODE_NATIVE = 0x0001
IME_CMODE_CHINESE = IME_CMODE_NATIVE
IME_CMODE_HANGUL = IME_CMODE_NATIVE
IME_CMODE_JAPANESE = IME_CMODE_NATIVE
IME_CMODE_KATAKANA = 0x0002  # only effect under IME_CMODE_NATIVE
IME_CMODE_LANGUAGE = 0x0003
IME_CMODE_FULLSHAPE = 0x0008
IME_CMODE_ROMAN = 0x0010
IME_CMODE_CHARCODE = 0x0020
IME_CMODE_HANJACONVERT = 0x0040
IME_CMODE_NATIVESYMBOL = 0x0080