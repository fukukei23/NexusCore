
# === NexusCore/tools\exports\export_20250803_114325\combined_27.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\_core\fromnumeric.py ===
"""Module containing non-deprecated functions borrowed from Numeric.

"""
import functools
import types
import warnings

import numpy as np
from numpy._utils import set_module

from . import _methods, overrides
from . import multiarray as mu
from . import numerictypes as nt
from . import umath as um
from ._multiarray_umath import _array_converter
from .multiarray import asanyarray, asarray, concatenate

_dt_ = nt.sctype2char

# functions that are methods
__all__ = [
    'all', 'amax', 'amin', 'any', 'argmax',
    'argmin', 'argpartition', 'argsort', 'around', 'choose', 'clip',
    'compress', 'cumprod', 'cumsum', 'cumulative_prod', 'cumulative_sum',
    'diagonal', 'mean', 'max', 'min', 'matrix_transpose',
    'ndim', 'nonzero', 'partition', 'prod', 'ptp', 'put',
    'ravel', 'repeat', 'reshape', 'resize', 'round',
    'searchsorted', 'shape', 'size', 'sort', 'squeeze',
    'std', 'sum', 'swapaxes', 'take', 'trace', 'transpose', 'var',
]

_gentype = types.GeneratorType
# save away Python sum
_sum_ = sum

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


# functions that are now methods
def _wrapit(obj, method, *args, **kwds):
    conv = _array_converter(obj)
    # As this already tried the method, subok is maybe quite reasonable here
    # but this follows what was done before. TODO: revisit this.
    arr, = conv.as_arrays(subok=False)
    result = getattr(arr, method)(*args, **kwds)

    return conv.wrap(result, to_scalar=False)


def _wrapfunc(obj, method, *args, **kwds):
    bound = getattr(obj, method, None)
    if bound is None:
        return _wrapit(obj, method, *args, **kwds)

    try:
        return bound(*args, **kwds)
    except TypeError:
        # A TypeError occurs if the object does have such a method in its
        # class, but its signature is not identical to that of NumPy's. This
        # situation has occurred in the case of a downstream library like
        # 'pandas'.
        #
        # Call _wrapit from within the except clause to ensure a potential
        # exception has a traceback chain.
        return _wrapit(obj, method, *args, **kwds)


def _wrapreduction(obj, ufunc, method, axis, dtype, out, **kwargs):
    passkwargs = {k: v for k, v in kwargs.items()
                  if v is not np._NoValue}

    if type(obj) is not mu.ndarray:
        try:
            reduction = getattr(obj, method)
        except AttributeError:
            pass
        else:
            # This branch is needed for reductions like any which don't
            # support a dtype.
            if dtype is not None:
                return reduction(axis=axis, dtype=dtype, out=out, **passkwargs)
            else:
                return reduction(axis=axis, out=out, **passkwargs)

    return ufunc.reduce(obj, axis, dtype, out, **passkwargs)


def _wrapreduction_any_all(obj, ufunc, method, axis, out, **kwargs):
    # Same as above function, but dtype is always bool (but never passed on)
    passkwargs = {k: v for k, v in kwargs.items()
                  if v is not np._NoValue}

    if type(obj) is not mu.ndarray:
        try:
            reduction = getattr(obj, method)
        except AttributeError:
            pass
        else:
            return reduction(axis=axis, out=out, **passkwargs)

    return ufunc.reduce(obj, axis, bool, out, **passkwargs)


def _take_dispatcher(a, indices, axis=None, out=None, mode=None):
    return (a, out)


@array_function_dispatch(_take_dispatcher)
def take(a, indices, axis=None, out=None, mode='raise'):
    """
    Take elements from an array along an axis.

    When axis is not None, this function does the same thing as "fancy"
    indexing (indexing arrays using arrays); however, it can be easier to use
    if you need elements along a given axis. A call such as
    ``np.take(arr, indices, axis=3)`` is equivalent to
    ``arr[:,:,:,indices,...]``.

    Explained without fancy indexing, this is equivalent to the following use
    of `ndindex`, which sets each of ``ii``, ``jj``, and ``kk`` to a tuple of
    indices::

        Ni, Nk = a.shape[:axis], a.shape[axis+1:]
        Nj = indices.shape
        for ii in ndindex(Ni):
            for jj in ndindex(Nj):
                for kk in ndindex(Nk):
                    out[ii + jj + kk] = a[ii + (indices[jj],) + kk]

    Parameters
    ----------
    a : array_like (Ni..., M, Nk...)
        The source array.
    indices : array_like (Nj...)
        The indices of the values to extract.
        Also allow scalars for indices.
    axis : int, optional
        The axis over which to select values. By default, the flattened
        input array is used.
    out : ndarray, optional (Ni..., Nj..., Nk...)
        If provided, the result will be placed in this array. It should
        be of the appropriate shape and dtype. Note that `out` is always
        buffered if `mode='raise'`; use other modes for better performance.
    mode : {'raise', 'wrap', 'clip'}, optional
        Specifies how out-of-bounds indices will behave.

        * 'raise' -- raise an error (default)
        * 'wrap' -- wrap around
        * 'clip' -- clip to the range

        'clip' mode means that all indices that are too large are replaced
        by the index that addresses the last element along that axis. Note
        that this disables indexing with negative numbers.

    Returns
    -------
    out : ndarray (Ni..., Nj..., Nk...)
        The returned array has the same type as `a`.

    See Also
    --------
    compress : Take elements using a boolean mask
    ndarray.take : equivalent method
    take_along_axis : Take elements by matching the array and the index arrays

    Notes
    -----
    By eliminating the inner loop in the description above, and using `s_` to
    build simple slice objects, `take` can be expressed  in terms of applying
    fancy indexing to each 1-d slice::

        Ni, Nk = a.shape[:axis], a.shape[axis+1:]
        for ii in ndindex(Ni):
            for kk in ndindex(Nj):
                out[ii + s_[...,] + kk] = a[ii + s_[:,] + kk][indices]

    For this reason, it is equivalent to (but faster than) the following use
    of `apply_along_axis`::

        out = np.apply_along_axis(lambda a_1d: a_1d[indices], axis, a)

    Examples
    --------
    >>> import numpy as np
    >>> a = [4, 3, 5, 7, 6, 8]
    >>> indices = [0, 1, 4]
    >>> np.take(a, indices)
    array([4, 3, 6])

    In this example if `a` is an ndarray, "fancy" indexing can be used.

    >>> a = np.array(a)
    >>> a[indices]
    array([4, 3, 6])

    If `indices` is not one dimensional, the output also has these dimensions.

    >>> np.take(a, [[0, 1], [2, 3]])
    array([[4, 3],
           [5, 7]])
    """
    return _wrapfunc(a, 'take', indices, axis=axis, out=out, mode=mode)


def _reshape_dispatcher(a, /, shape=None, order=None, *, newshape=None,
                        copy=None):
    return (a,)


@array_function_dispatch(_reshape_dispatcher)
def reshape(a, /, shape=None, order='C', *, newshape=None, copy=None):
    """
    Gives a new shape to an array without changing its data.

    Parameters
    ----------
    a : array_like
        Array to be reshaped.
    shape : int or tuple of ints
        The new shape should be compatible with the original shape. If
        an integer, then the result will be a 1-D array of that length.
        One shape dimension can be -1. In this case, the value is
        inferred from the length of the array and remaining dimensions.
    order : {'C', 'F', 'A'}, optional
        Read the elements of ``a`` using this index order, and place the
        elements into the reshaped array using this index order. 'C'
        means to read / write the elements using C-like index order,
        with the last axis index changing fastest, back to the first
        axis index changing slowest. 'F' means to read / write the
        elements using Fortran-like index order, with the first index
        changing fastest, and the last index changing slowest. Note that
        the 'C' and 'F' options take no account of the memory layout of
        the underlying array, and only refer to the order of indexing.
        'A' means to read / write the elements in Fortran-like index
        order if ``a`` is Fortran *contiguous* in memory, C-like order
        otherwise.
    newshape : int or tuple of ints
        .. deprecated:: 2.1
            Replaced by ``shape`` argument. Retained for backward
            compatibility.
    copy : bool, optional
        If ``True``, then the array data is copied. If ``None``, a copy will
        only be made if it's required by ``order``. For ``False`` it raises
        a ``ValueError`` if a copy cannot be avoided. Default: ``None``.

    Returns
    -------
    reshaped_array : ndarray
        This will be a new view object if possible; otherwise, it will
        be a copy.  Note there is no guarantee of the *memory layout* (C- or
        Fortran- contiguous) of the returned array.

    See Also
    --------
    ndarray.reshape : Equivalent method.

    Notes
    -----
    It is not always possible to change the shape of an array without copying
    the data.

    The ``order`` keyword gives the index ordering both for *fetching*
    the values from ``a``, and then *placing* the values into the output
    array. For example, let's say you have an array:

    >>> a = np.arange(6).reshape((3, 2))
    >>> a
    array([[0, 1],
           [2, 3],
           [4, 5]])

    You can think of reshaping as first raveling the array (using the given
    index order), then inserting the elements from the raveled array into the
    new array using the same kind of index ordering as was used for the
    raveling.

    >>> np.reshape(a, (2, 3)) # C-like index ordering
    array([[0, 1, 2],
           [3, 4, 5]])
    >>> np.reshape(np.ravel(a), (2, 3)) # equivalent to C ravel then C reshape
    array([[0, 1, 2],
           [3, 4, 5]])
    >>> np.reshape(a, (2, 3), order='F') # Fortran-like index ordering
    array([[0, 4, 3],
           [2, 1, 5]])
    >>> np.reshape(np.ravel(a, order='F'), (2, 3), order='F')
    array([[0, 4, 3],
           [2, 1, 5]])

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1,2,3], [4,5,6]])
    >>> np.reshape(a, 6)
    array([1, 2, 3, 4, 5, 6])
    >>> np.reshape(a, 6, order='F')
    array([1, 4, 2, 5, 3, 6])

    >>> np.reshape(a, (3,-1))       # the unspecified value is inferred to be 2
    array([[1, 2],
           [3, 4],
           [5, 6]])
    """
    if newshape is None and shape is None:
        raise TypeError(
            "reshape() missing 1 required positional argument: 'shape'")
    if newshape is not None:
        if shape is not None:
            raise TypeError(
                "You cannot specify 'newshape' and 'shape' arguments "
                "at the same time.")
        # Deprecated in NumPy 2.1, 2024-04-18
        warnings.warn(
            "`newshape` keyword argument is deprecated, "
            "use `shape=...` or pass shape positionally instead. "
            "(deprecated in NumPy 2.1)",
            DeprecationWarning,
            stacklevel=2,
        )
        shape = newshape
    if copy is not None:
        return _wrapfunc(a, 'reshape', shape, order=order, copy=copy)
    return _wrapfunc(a, 'reshape', shape, order=order)


def _choose_dispatcher(a, choices, out=None, mode=None):
    yield a
    yield from choices
    yield out


@array_function_dispatch(_choose_dispatcher)
def choose(a, choices, out=None, mode='raise'):
    """
    Construct an array from an index array and a list of arrays to choose from.

    First of all, if confused or uncertain, definitely look at the Examples -
    in its full generality, this function is less simple than it might
    seem from the following code description::

        np.choose(a,c) == np.array([c[a[I]][I] for I in np.ndindex(a.shape)])

    But this omits some subtleties.  Here is a fully general summary:

    Given an "index" array (`a`) of integers and a sequence of ``n`` arrays
    (`choices`), `a` and each choice array are first broadcast, as necessary,
    to arrays of a common shape; calling these *Ba* and *Bchoices[i], i =
    0,...,n-1* we have that, necessarily, ``Ba.shape == Bchoices[i].shape``
    for each ``i``.  Then, a new array with shape ``Ba.shape`` is created as
    follows:

    * if ``mode='raise'`` (the default), then, first of all, each element of
      ``a`` (and thus ``Ba``) must be in the range ``[0, n-1]``; now, suppose
      that ``i`` (in that range) is the value at the ``(j0, j1, ..., jm)``
      position in ``Ba`` - then the value at the same position in the new array
      is the value in ``Bchoices[i]`` at that same position;

    * if ``mode='wrap'``, values in `a` (and thus `Ba`) may be any (signed)
      integer; modular arithmetic is used to map integers outside the range
      `[0, n-1]` back into that range; and then the new array is constructed
      as above;

    * if ``mode='clip'``, values in `a` (and thus ``Ba``) may be any (signed)
      integer; negative integers are mapped to 0; values greater than ``n-1``
      are mapped to ``n-1``; and then the new array is constructed as above.

    Parameters
    ----------
    a : int array
        This array must contain integers in ``[0, n-1]``, where ``n`` is the
        number of choices, unless ``mode=wrap`` or ``mode=clip``, in which
        cases any integers are permissible.
    choices : sequence of arrays
        Choice arrays. `a` and all of the choices must be broadcastable to the
        same shape.  If `choices` is itself an array (not recommended), then
        its outermost dimension (i.e., the one corresponding to
        ``choices.shape[0]``) is taken as defining the "sequence".
    out : array, optional
        If provided, the result will be inserted into this array. It should
        be of the appropriate shape and dtype. Note that `out` is always
        buffered if ``mode='raise'``; use other modes for better performance.
    mode : {'raise' (default), 'wrap', 'clip'}, optional
        Specifies how indices outside ``[0, n-1]`` will be treated:

        * 'raise' : an exception is raised
        * 'wrap' : value becomes value mod ``n``
        * 'clip' : values < 0 are mapped to 0, values > n-1 are mapped to n-1

    Returns
    -------
    merged_array : array
        The merged result.

    Raises
    ------
    ValueError: shape mismatch
        If `a` and each choice array are not all broadcastable to the same
        shape.

    See Also
    --------
    ndarray.choose : equivalent method
    numpy.take_along_axis : Preferable if `choices` is an array

    Notes
    -----
    To reduce the chance of misinterpretation, even though the following
    "abuse" is nominally supported, `choices` should neither be, nor be
    thought of as, a single array, i.e., the outermost sequence-like container
    should be either a list or a tuple.

    Examples
    --------

    >>> import numpy as np
    >>> choices = [[0, 1, 2, 3], [10, 11, 12, 13],
    ...   [20, 21, 22, 23], [30, 31, 32, 33]]
    >>> np.choose([2, 3, 1, 0], choices
    ... # the first element of the result will be the first element of the
    ... # third (2+1) "array" in choices, namely, 20; the second element
    ... # will be the second element of the fourth (3+1) choice array, i.e.,
    ... # 31, etc.
    ... )
    array([20, 31, 12,  3])
    >>> np.choose([2, 4, 1, 0], choices, mode='clip') # 4 goes to 3 (4-1)
    array([20, 31, 12,  3])
    >>> # because there are 4 choice arrays
    >>> np.choose([2, 4, 1, 0], choices, mode='wrap') # 4 goes to (4 mod 4)
    array([20,  1, 12,  3])
    >>> # i.e., 0

    A couple examples illustrating how choose broadcasts:

    >>> a = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
    >>> choices = [-10, 10]
    >>> np.choose(a, choices)
    array([[ 10, -10,  10],
           [-10,  10, -10],
           [ 10, -10,  10]])

    >>> # With thanks to Anne Archibald
    >>> a = np.array([0, 1]).reshape((2,1,1))
    >>> c1 = np.array([1, 2, 3]).reshape((1,3,1))
    >>> c2 = np.array([-1, -2, -3, -4, -5]).reshape((1,1,5))
    >>> np.choose(a, (c1, c2)) # result is 2x3x5, res[0,:,:]=c1, res[1,:,:]=c2
    array([[[ 1,  1,  1,  1,  1],
            [ 2,  2,  2,  2,  2],
            [ 3,  3,  3,  3,  3]],
           [[-1, -2, -3, -4, -5],
            [-1, -2, -3, -4, -5],
            [-1, -2, -3, -4, -5]]])

    """
    return _wrapfunc(a, 'choose', choices, out=out, mode=mode)


def _repeat_dispatcher(a, repeats, axis=None):
    return (a,)


@array_function_dispatch(_repeat_dispatcher)
def repeat(a, repeats, axis=None):
    """
    Repeat each element of an array after themselves

    Parameters
    ----------
    a : array_like
        Input array.
    repeats : int or array of ints
        The number of repetitions for each element.  `repeats` is broadcasted
        to fit the shape of the given axis.
    axis : int, optional
        The axis along which to repeat values.  By default, use the
        flattened input array, and return a flat output array.

    Returns
    -------
    repeated_array : ndarray
        Output array which has the same shape as `a`, except along
        the given axis.

    See Also
    --------
    tile : Tile an array.
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> np.repeat(3, 4)
    array([3, 3, 3, 3])
    >>> x = np.array([[1,2],[3,4]])
    >>> np.repeat(x, 2)
    array([1, 1, 2, 2, 3, 3, 4, 4])
    >>> np.repeat(x, 3, axis=1)
    array([[1, 1, 1, 2, 2, 2],
           [3, 3, 3, 4, 4, 4]])
    >>> np.repeat(x, [1, 2], axis=0)
    array([[1, 2],
           [3, 4],
           [3, 4]])

    """
    return _wrapfunc(a, 'repeat', repeats, axis=axis)


def _put_dispatcher(a, ind, v, mode=None):
    return (a, ind, v)


@array_function_dispatch(_put_dispatcher)
def put(a, ind, v, mode='raise'):
    """
    Replaces specified elements of an array with given values.

    The indexing works on the flattened target array. `put` is roughly
    equivalent to:

    ::

        a.flat[ind] = v

    Parameters
    ----------
    a : ndarray
        Target array.
    ind : array_like
        Target indices, interpreted as integers.
    v : array_like
        Values to place in `a` at target indices. If `v` is shorter than
        `ind` it will be repeated as necessary.
    mode : {'raise', 'wrap', 'clip'}, optional
        Specifies how out-of-bounds indices will behave.

        * 'raise' -- raise an error (default)
        * 'wrap' -- wrap around
        * 'clip' -- clip to the range

        'clip' mode means that all indices that are too large are replaced
        by the index that addresses the last element along that axis. Note
        that this disables indexing with negative numbers. In 'raise' mode,
        if an exception occurs the target array may still be modified.

    See Also
    --------
    putmask, place
    put_along_axis : Put elements by matching the array and the index arrays

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(5)
    >>> np.put(a, [0, 2], [-44, -55])
    >>> a
    array([-44,   1, -55,   3,   4])

    >>> a = np.arange(5)
    >>> np.put(a, 22, -5, mode='clip')
    >>> a
    array([ 0,  1,  2,  3, -5])

    """
    try:
        put = a.put
    except AttributeError as e:
        raise TypeError(f"argument 1 must be numpy.ndarray, not {type(a)}") from e

    return put(ind, v, mode=mode)


def _swapaxes_dispatcher(a, axis1, axis2):
    return (a,)


@array_function_dispatch(_swapaxes_dispatcher)
def swapaxes(a, axis1, axis2):
    """
    Interchange two axes of an array.

    Parameters
    ----------
    a : array_like
        Input array.
    axis1 : int
        First axis.
    axis2 : int
        Second axis.

    Returns
    -------
    a_swapped : ndarray
        For NumPy >= 1.10.0, if `a` is an ndarray, then a view of `a` is
        returned; otherwise a new array is created. For earlier NumPy
        versions a view of `a` is returned only if the order of the
        axes is changed, otherwise the input array is returned.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[1,2,3]])
    >>> np.swapaxes(x,0,1)
    array([[1],
           [2],
           [3]])

    >>> x = np.array([[[0,1],[2,3]],[[4,5],[6,7]]])
    >>> x
    array([[[0, 1],
            [2, 3]],
           [[4, 5],
            [6, 7]]])

    >>> np.swapaxes(x,0,2)
    array([[[0, 4],
            [2, 6]],
           [[1, 5],
            [3, 7]]])

    """
    return _wrapfunc(a, 'swapaxes', axis1, axis2)


def _transpose_dispatcher(a, axes=None):
    return (a,)


@array_function_dispatch(_transpose_dispatcher)
def transpose(a, axes=None):
    """
    Returns an array with axes transposed.

    For a 1-D array, this returns an unchanged view of the original array, as a
    transposed vector is simply the same vector.
    To convert a 1-D array into a 2-D column vector, an additional dimension
    must be added, e.g., ``np.atleast_2d(a).T`` achieves this, as does
    ``a[:, np.newaxis]``.
    For a 2-D array, this is the standard matrix transpose.
    For an n-D array, if axes are given, their order indicates how the
    axes are permuted (see Examples). If axes are not provided, then
    ``transpose(a).shape == a.shape[::-1]``.

    Parameters
    ----------
    a : array_like
        Input array.
    axes : tuple or list of ints, optional
        If specified, it must be a tuple or list which contains a permutation
        of [0, 1, ..., N-1] where N is the number of axes of `a`. Negative
        indices can also be used to specify axes. The i-th axis of the returned
        array will correspond to the axis numbered ``axes[i]`` of the input.
        If not specified, defaults to ``range(a.ndim)[::-1]``, which reverses
        the order of the axes.

    Returns
    -------
    p : ndarray
        `a` with its axes permuted. A view is returned whenever possible.

    See Also
    --------
    ndarray.transpose : Equivalent method.
    moveaxis : Move axes of an array to new positions.
    argsort : Return the indices that would sort an array.

    Notes
    -----
    Use ``transpose(a, argsort(axes))`` to invert the transposition of tensors
    when using the `axes` keyword argument.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> a
    array([[1, 2],
           [3, 4]])
    >>> np.transpose(a)
    array([[1, 3],
           [2, 4]])

    >>> a = np.array([1, 2, 3, 4])
    >>> a
    array([1, 2, 3, 4])
    >>> np.transpose(a)
    array([1, 2, 3, 4])

    >>> a = np.ones((1, 2, 3))
    >>> np.transpose(a, (1, 0, 2)).shape
    (2, 1, 3)

    >>> a = np.ones((2, 3, 4, 5))
    >>> np.transpose(a).shape
    (5, 4, 3, 2)

    >>> a = np.arange(3*4*5).reshape((3, 4, 5))
    >>> np.transpose(a, (-1, 0, -2)).shape
    (5, 3, 4)

    """
    return _wrapfunc(a, 'transpose', axes)


def _matrix_transpose_dispatcher(x):
    return (x,)

@array_function_dispatch(_matrix_transpose_dispatcher)
def matrix_transpose(x, /):
    """
    Transposes a matrix (or a stack of matrices) ``x``.

    This function is Array API compatible.

    Parameters
    ----------
    x : array_like
        Input array having shape (..., M, N) and whose two innermost
        dimensions form ``MxN`` matrices.

    Returns
    -------
    out : ndarray
        An array containing the transpose for each matrix and having shape
        (..., N, M).

    See Also
    --------
    transpose : Generic transpose method.

    Examples
    --------
    >>> import numpy as np
    >>> np.matrix_transpose([[1, 2], [3, 4]])
    array([[1, 3],
           [2, 4]])

    >>> np.matrix_transpose([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
    array([[[1, 3],
            [2, 4]],
           [[5, 7],
            [6, 8]]])

    """
    x = asanyarray(x)
    if x.ndim < 2:
        raise ValueError(
            f"Input array must be at least 2-dimensional, but it is {x.ndim}"
        )
    return swapaxes(x, -1, -2)


def _partition_dispatcher(a, kth, axis=None, kind=None, order=None):
    return (a,)


@array_function_dispatch(_partition_dispatcher)
def partition(a, kth, axis=-1, kind='introselect', order=None):
    """
    Return a partitioned copy of an array.

    Creates a copy of the array and partially sorts it in such a way that
    the value of the element in k-th position is in the position it would be
    in a sorted array. In the output array, all elements smaller than the k-th
    element are located to the left of this element and all equal or greater
    are located to its right. The ordering of the elements in the two
    partitions on the either side of the k-th element in the output array is
    undefined.

    Parameters
    ----------
    a : array_like
        Array to be sorted.
    kth : int or sequence of ints
        Element index to partition by. The k-th value of the element
        will be in its final sorted position and all smaller elements
        will be moved before it and all equal or greater elements behind
        it. The order of all elements in the partitions is undefined. If
        provided with a sequence of k-th it will partition all elements
        indexed by k-th  of them into their sorted position at once.

        .. deprecated:: 1.22.0
            Passing booleans as index is deprecated.
    axis : int or None, optional
        Axis along which to sort. If None, the array is flattened before
        sorting. The default is -1, which sorts along the last axis.
    kind : {'introselect'}, optional
        Selection algorithm. Default is 'introselect'.
    order : str or list of str, optional
        When `a` is an array with fields defined, this argument
        specifies which fields to compare first, second, etc.  A single
        field can be specified as a string.  Not all fields need be
        specified, but unspecified fields will still be used, in the
        order in which they come up in the dtype, to break ties.

    Returns
    -------
    partitioned_array : ndarray
        Array of the same type and shape as `a`.

    See Also
    --------
    ndarray.partition : Method to sort an array in-place.
    argpartition : Indirect partition.
    sort : Full sorting

    Notes
    -----
    The various selection algorithms are characterized by their average
    speed, worst case performance, work space size, and whether they are
    stable. A stable sort keeps items with the same key in the same
    relative order. The available algorithms have the following
    properties:

    ================= ======= ============= ============ =======
       kind            speed   worst case    work space  stable
    ================= ======= ============= ============ =======
    'introselect'        1        O(n)           0         no
    ================= ======= ============= ============ =======

    All the partition algorithms make temporary copies of the data when
    partitioning along any but the last axis.  Consequently,
    partitioning along the last axis is faster and uses less space than
    partitioning along any other axis.

    The sort order for complex numbers is lexicographic. If both the
    real and imaginary parts are non-nan then the order is determined by
    the real parts except when they are equal, in which case the order
    is determined by the imaginary parts.

    The sort order of ``np.nan`` is bigger than ``np.inf``.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([7, 1, 7, 7, 1, 5, 7, 2, 3, 2, 6, 2, 3, 0])
    >>> p = np.partition(a, 4)
    >>> p
    array([0, 1, 2, 1, 2, 5, 2, 3, 3, 6, 7, 7, 7, 7]) # may vary

    ``p[4]`` is 2;  all elements in ``p[:4]`` are less than or equal
    to ``p[4]``, and all elements in ``p[5:]`` are greater than or
    equal to ``p[4]``.  The partition is::

        [0, 1, 2, 1], [2], [5, 2, 3, 3, 6, 7, 7, 7, 7]

    The next example shows the use of multiple values passed to `kth`.

    >>> p2 = np.partition(a, (4, 8))
    >>> p2
    array([0, 1, 2, 1, 2, 3, 3, 2, 5, 6, 7, 7, 7, 7])

    ``p2[4]`` is 2  and ``p2[8]`` is 5.  All elements in ``p2[:4]``
    are less than or equal to ``p2[4]``, all elements in ``p2[5:8]``
    are greater than or equal to ``p2[4]`` and less than or equal to
    ``p2[8]``, and all elements in ``p2[9:]`` are greater than or
    equal to ``p2[8]``.  The partition is::

        [0, 1, 2, 1], [2], [3, 3, 2], [5], [6, 7, 7, 7, 7]
    """
    if axis is None:
        # flatten returns (1, N) for np.matrix, so always use the last axis
        a = asanyarray(a).flatten()
        axis = -1
    else:
        a = asanyarray(a).copy(order="K")
    a.partition(kth, axis=axis, kind=kind, order=order)
    return a


def _argpartition_dispatcher(a, kth, axis=None, kind=None, order=None):
    return (a,)


@array_function_dispatch(_argpartition_dispatcher)
def argpartition(a, kth, axis=-1, kind='introselect', order=None):
    """
    Perform an indirect partition along the given axis using the
    algorithm specified by the `kind` keyword. It returns an array of
    indices of the same shape as `a` that index data along the given
    axis in partitioned order.

    Parameters
    ----------
    a : array_like
        Array to sort.
    kth : int or sequence of ints
        Element index to partition by. The k-th element will be in its
        final sorted position and all smaller elements will be moved
        before it and all larger elements behind it. The order of all
        elements in the partitions is undefined. If provided with a
        sequence of k-th it will partition all of them into their sorted
        position at once.

        .. deprecated:: 1.22.0
            Passing booleans as index is deprecated.
    axis : int or None, optional
        Axis along which to sort. The default is -1 (the last axis). If
        None, the flattened array is used.
    kind : {'introselect'}, optional
        Selection algorithm. Default is 'introselect'
    order : str or list of str, optional
        When `a` is an array with fields defined, this argument
        specifies which fields to compare first, second, etc. A single
        field can be specified as a string, and not all fields need be
        specified, but unspecified fields will still be used, in the
        order in which they come up in the dtype, to break ties.

    Returns
    -------
    index_array : ndarray, int
        Array of indices that partition `a` along the specified axis.
        If `a` is one-dimensional, ``a[index_array]`` yields a partitioned `a`.
        More generally, ``np.take_along_axis(a, index_array, axis=axis)``
        always yields the partitioned `a`, irrespective of dimensionality.

    See Also
    --------
    partition : Describes partition algorithms used.
    ndarray.partition : Inplace partition.
    argsort : Full indirect sort.
    take_along_axis : Apply ``index_array`` from argpartition
                      to an array as if by calling partition.

    Notes
    -----
    The returned indices are not guaranteed to be sorted according to
    the values. Furthermore, the default selection algorithm ``introselect``
    is unstable, and hence the returned indices are not guaranteed
    to be the earliest/latest occurrence of the element.

    `argpartition` works for real/complex inputs with nan values,
    see `partition` for notes on the enhanced sort order and
    different selection algorithms.

    Examples
    --------
    One dimensional array:

    >>> import numpy as np
    >>> x = np.array([3, 4, 2, 1])
    >>> x[np.argpartition(x, 3)]
    array([2, 1, 3, 4]) # may vary
    >>> x[np.argpartition(x, (1, 3))]
    array([1, 2, 3, 4]) # may vary

    >>> x = [3, 4, 2, 1]
    >>> np.array(x)[np.argpartition(x, 3)]
    array([2, 1, 3, 4]) # may vary

    Multi-dimensional array:

    >>> x = np.array([[3, 4, 2], [1, 3, 1]])
    >>> index_array = np.argpartition(x, kth=1, axis=-1)
    >>> # below is the same as np.partition(x, kth=1)
    >>> np.take_along_axis(x, index_array, axis=-1)
    array([[2, 3, 4],
           [1, 1, 3]])

    """
    return _wrapfunc(a, 'argpartition', kth, axis=axis, kind=kind, order=order)


def _sort_dispatcher(a, axis=None, kind=None, order=None, *, stable=None):
    return (a,)


@array_function_dispatch(_sort_dispatcher)
def sort(a, axis=-1, kind=None, order=None, *, stable=None):
    """
    Return a sorted copy of an array.

    Parameters
    ----------
    a : array_like
        Array to be sorted.
    axis : int or None, optional
        Axis along which to sort. If None, the array is flattened before
        sorting. The default is -1, which sorts along the last axis.
    kind : {'quicksort', 'mergesort', 'heapsort', 'stable'}, optional
        Sorting algorithm. The default is 'quicksort'. Note that both 'stable'
        and 'mergesort' use timsort or radix sort under the covers and,
        in general, the actual implementation will vary with data type.
        The 'mergesort' option is retained for backwards compatibility.
    order : str or list of str, optional
        When `a` is an array with fields defined, this argument specifies
        which fields to compare first, second, etc.  A single field can
        be specified as a string, and not all fields need be specified,
        but unspecified fields will still be used, in the order in which
        they come up in the dtype, to break ties.
    stable : bool, optional
        Sort stability. If ``True``, the returned array will maintain
        the relative order of ``a`` values which compare as equal.
        If ``False`` or ``None``, this is not guaranteed. Internally,
        this option selects ``kind='stable'``. Default: ``None``.

        .. versionadded:: 2.0.0

    Returns
    -------
    sorted_array : ndarray
        Array of the same type and shape as `a`.

    See Also
    --------
    ndarray.sort : Method to sort an array in-place.
    argsort : Indirect sort.
    lexsort : Indirect stable sort on multiple keys.
    searchsorted : Find elements in a sorted array.
    partition : Partial sort.

    Notes
    -----
    The various sorting algorithms are characterized by their average speed,
    worst case performance, work space size, and whether they are stable. A
    stable sort keeps items with the same key in the same relative
    order. The four algorithms implemented in NumPy have the following
    properties:

    =========== ======= ============= ============ ========
       kind      speed   worst case    work space   stable
    =========== ======= ============= ============ ========
    'quicksort'    1     O(n^2)            0          no
    'heapsort'     3     O(n*log(n))       0          no
    'mergesort'    2     O(n*log(n))      ~n/2        yes
    'timsort'      2     O(n*log(n))      ~n/2        yes
    =========== ======= ============= ============ ========

    .. note:: The datatype determines which of 'mergesort' or 'timsort'
       is actually used, even if 'mergesort' is specified. User selection
       at a finer scale is not currently available.

    For performance, ``sort`` makes a temporary copy if needed to make the data
    `contiguous <https://numpy.org/doc/stable/glossary.html#term-contiguous>`_
    in memory along the sort axis. For even better performance and reduced
    memory consumption, ensure that the array is already contiguous along the
    sort axis.

    The sort order for complex numbers is lexicographic. If both the real
    and imaginary parts are non-nan then the order is determined by the
    real parts except when they are equal, in which case the order is
    determined by the imaginary parts.

    Previous to numpy 1.4.0 sorting real and complex arrays containing nan
    values led to undefined behaviour. In numpy versions >= 1.4.0 nan
    values are sorted to the end. The extended sort order is:

      * Real: [R, nan]
      * Complex: [R + Rj, R + nanj, nan + Rj, nan + nanj]

    where R is a non-nan real value. Complex values with the same nan
    placements are sorted according to the non-nan part if it exists.
    Non-nan values are sorted as before.

    quicksort has been changed to:
    `introsort <https://en.wikipedia.org/wiki/Introsort>`_.
    When sorting does not make enough progress it switches to
    `heapsort <https://en.wikipedia.org/wiki/Heapsort>`_.
    This implementation makes quicksort O(n*log(n)) in the worst case.

    'stable' automatically chooses the best stable sorting algorithm
    for the data type being sorted.
    It, along with 'mergesort' is currently mapped to
    `timsort <https://en.wikipedia.org/wiki/Timsort>`_
    or `radix sort <https://en.wikipedia.org/wiki/Radix_sort>`_
    depending on the data type.
    API forward compatibility currently limits the
    ability to select the implementation and it is hardwired for the different
    data types.

    Timsort is added for better performance on already or nearly
    sorted data. On random data timsort is almost identical to
    mergesort. It is now used for stable sort while quicksort is still the
    default sort if none is chosen. For timsort details, refer to
    `CPython listsort.txt
    <https://github.com/python/cpython/blob/3.7/Objects/listsort.txt>`_
    'mergesort' and 'stable' are mapped to radix sort for integer data types.
    Radix sort is an O(n) sort instead of O(n log n).

    NaT now sorts to the end of arrays for consistency with NaN.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1,4],[3,1]])
    >>> np.sort(a)                # sort along the last axis
    array([[1, 4],
           [1, 3]])
    >>> np.sort(a, axis=None)     # sort the flattened array
    array([1, 1, 3, 4])
    >>> np.sort(a, axis=0)        # sort along the first axis
    array([[1, 1],
           [3, 4]])

    Use the `order` keyword to specify a field to use when sorting a
    structured array:

    >>> dtype = [('name', 'S10'), ('height', float), ('age', int)]
    >>> values = [('Arthur', 1.8, 41), ('Lancelot', 1.9, 38),
    ...           ('Galahad', 1.7, 38)]
    >>> a = np.array(values, dtype=dtype)       # create a structured array
    >>> np.sort(a, order='height')                        # doctest: +SKIP
    array([('Galahad', 1.7, 38), ('Arthur', 1.8, 41),
           ('Lancelot', 1.8999999999999999, 38)],
          dtype=[('name', '|S10'), ('height', '<f8'), ('age', '<i4')])

    Sort by age, then height if ages are equal:

    >>> np.sort(a, order=['age', 'height'])               # doctest: +SKIP
    array([('Galahad', 1.7, 38), ('Lancelot', 1.8999999999999999, 38),
           ('Arthur', 1.8, 41)],
          dtype=[('name', '|S10'), ('height', '<f8'), ('age', '<i4')])

    """
    if axis is None:
        # flatten returns (1, N) for np.matrix, so always use the last axis
        a = asanyarray(a).flatten()
        axis = -1
    else:
        a = asanyarray(a).copy(order="K")
    a.sort(axis=axis, kind=kind, order=order, stable=stable)
    return a


def _argsort_dispatcher(a, axis=None, kind=None, order=None, *, stable=None):
    return (a,)


@array_function_dispatch(_argsort_dispatcher)
def argsort(a, axis=-1, kind=None, order=None, *, stable=None):
    """
    Returns the indices that would sort an array.

    Perform an indirect sort along the given axis using the algorithm specified
    by the `kind` keyword. It returns an array of indices of the same shape as
    `a` that index data along the given axis in sorted order.

    Parameters
    ----------
    a : array_like
        Array to sort.
    axis : int or None, optional
        Axis along which to sort.  The default is -1 (the last axis). If None,
        the flattened array is used.
    kind : {'quicksort', 'mergesort', 'heapsort', 'stable'}, optional
        Sorting algorithm. The default is 'quicksort'. Note that both 'stable'
        and 'mergesort' use timsort under the covers and, in general, the
        actual implementation will vary with data type. The 'mergesort' option
        is retained for backwards compatibility.
    order : str or list of str, optional
        When `a` is an array with fields defined, this argument specifies
        which fields to compare first, second, etc.  A single field can
        be specified as a string, and not all fields need be specified,
        but unspecified fields will still be used, in the order in which
        they come up in the dtype, to break ties.
    stable : bool, optional
        Sort stability. If ``True``, the returned array will maintain
        the relative order of ``a`` values which compare as equal.
        If ``False`` or ``None``, this is not guaranteed. Internally,
        this option selects ``kind='stable'``. Default: ``None``.

        .. versionadded:: 2.0.0

    Returns
    -------
    index_array : ndarray, int
        Array of indices that sort `a` along the specified `axis`.
        If `a` is one-dimensional, ``a[index_array]`` yields a sorted `a`.
        More generally, ``np.take_along_axis(a, index_array, axis=axis)``
        always yields the sorted `a`, irrespective of dimensionality.

    See Also
    --------
    sort : Describes sorting algorithms used.
    lexsort : Indirect stable sort with multiple keys.
    ndarray.sort : Inplace sort.
    argpartition : Indirect partial sort.
    take_along_axis : Apply ``index_array`` from argsort
                      to an array as if by calling sort.

    Notes
    -----
    See `sort` for notes on the different sorting algorithms.

    As of NumPy 1.4.0 `argsort` works with real/complex arrays containing
    nan values. The enhanced sort order is documented in `sort`.

    Examples
    --------
    One dimensional array:

    >>> import numpy as np
    >>> x = np.array([3, 1, 2])
    >>> np.argsort(x)
    array([1, 2, 0])

    Two-dimensional array:

    >>> x = np.array([[0, 3], [2, 2]])
    >>> x
    array([[0, 3],
           [2, 2]])

    >>> ind = np.argsort(x, axis=0)  # sorts along first axis (down)
    >>> ind
    array([[0, 1],
           [1, 0]])
    >>> np.take_along_axis(x, ind, axis=0)  # same as np.sort(x, axis=0)
    array([[0, 2],
           [2, 3]])

    >>> ind = np.argsort(x, axis=1)  # sorts along last axis (across)
    >>> ind
    array([[0, 1],
           [0, 1]])
    >>> np.take_along_axis(x, ind, axis=1)  # same as np.sort(x, axis=1)
    array([[0, 3],
           [2, 2]])

    Indices of the sorted elements of a N-dimensional array:

    >>> ind = np.unravel_index(np.argsort(x, axis=None), x.shape)
    >>> ind
    (array([0, 1, 1, 0]), array([0, 0, 1, 1]))
    >>> x[ind]  # same as np.sort(x, axis=None)
    array([0, 2, 2, 3])

    Sorting with keys:

    >>> x = np.array([(1, 0), (0, 1)], dtype=[('x', '<i4'), ('y', '<i4')])
    >>> x
    array([(1, 0), (0, 1)],
          dtype=[('x', '<i4'), ('y', '<i4')])

    >>> np.argsort(x, order=('x','y'))
    array([1, 0])

    >>> np.argsort(x, order=('y','x'))
    array([0, 1])

    """
    return _wrapfunc(
        a, 'argsort', axis=axis, kind=kind, order=order, stable=stable
    )

def _argmax_dispatcher(a, axis=None, out=None, *, keepdims=np._NoValue):
    return (a, out)


@array_function_dispatch(_argmax_dispatcher)
def argmax(a, axis=None, out=None, *, keepdims=np._NoValue):
    """
    Returns the indices of the maximum values along an axis.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        By default, the index is into the flattened array, otherwise
        along the specified axis.
    out : array, optional
        If provided, the result will be inserted into this array. It should
        be of the appropriate shape and dtype.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the array.

        .. versionadded:: 1.22.0

    Returns
    -------
    index_array : ndarray of ints
        Array of indices into the array. It has the same shape as ``a.shape``
        with the dimension along `axis` removed. If `keepdims` is set to True,
        then the size of `axis` will be 1 with the resulting array having same
        shape as ``a.shape``.

    See Also
    --------
    ndarray.argmax, argmin
    amax : The maximum value along a given axis.
    unravel_index : Convert a flat index into an index tuple.
    take_along_axis : Apply ``np.expand_dims(index_array, axis)``
                      from argmax to an array as if by calling max.

    Notes
    -----
    In case of multiple occurrences of the maximum values, the indices
    corresponding to the first occurrence are returned.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(6).reshape(2,3) + 10
    >>> a
    array([[10, 11, 12],
           [13, 14, 15]])
    >>> np.argmax(a)
    5
    >>> np.argmax(a, axis=0)
    array([1, 1, 1])
    >>> np.argmax(a, axis=1)
    array([2, 2])

    Indexes of the maximal elements of a N-dimensional array:

    >>> ind = np.unravel_index(np.argmax(a, axis=None), a.shape)
    >>> ind
    (1, 2)
    >>> a[ind]
    15

    >>> b = np.arange(6)
    >>> b[1] = 5
    >>> b
    array([0, 5, 2, 3, 4, 5])
    >>> np.argmax(b)  # Only the first occurrence is returned.
    1

    >>> x = np.array([[4,2,3], [1,0,3]])
    >>> index_array = np.argmax(x, axis=-1)
    >>> # Same as np.amax(x, axis=-1, keepdims=True)
    >>> np.take_along_axis(x, np.expand_dims(index_array, axis=-1), axis=-1)
    array([[4],
           [3]])
    >>> # Same as np.amax(x, axis=-1)
    >>> np.take_along_axis(x, np.expand_dims(index_array, axis=-1),
    ...     axis=-1).squeeze(axis=-1)
    array([4, 3])

    Setting `keepdims` to `True`,

    >>> x = np.arange(24).reshape((2, 3, 4))
    >>> res = np.argmax(x, axis=1, keepdims=True)
    >>> res.shape
    (2, 1, 4)
    """
    kwds = {'keepdims': keepdims} if keepdims is not np._NoValue else {}
    return _wrapfunc(a, 'argmax', axis=axis, out=out, **kwds)


def _argmin_dispatcher(a, axis=None, out=None, *, keepdims=np._NoValue):
    return (a, out)


@array_function_dispatch(_argmin_dispatcher)
def argmin(a, axis=None, out=None, *, keepdims=np._NoValue):
    """
    Returns the indices of the minimum values along an axis.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        By default, the index is into the flattened array, otherwise
        along the specified axis.
    out : array, optional
        If provided, the result will be inserted into this array. It should
        be of the appropriate shape and dtype.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the array.

        .. versionadded:: 1.22.0

    Returns
    -------
    index_array : ndarray of ints
        Array of indices into the array. It has the same shape as `a.shape`
        with the dimension along `axis` removed. If `keepdims` is set to True,
        then the size of `axis` will be 1 with the resulting array having same
        shape as `a.shape`.

    See Also
    --------
    ndarray.argmin, argmax
    amin : The minimum value along a given axis.
    unravel_index : Convert a flat index into an index tuple.
    take_along_axis : Apply ``np.expand_dims(index_array, axis)``
                      from argmin to an array as if by calling min.

    Notes
    -----
    In case of multiple occurrences of the minimum values, the indices
    corresponding to the first occurrence are returned.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(6).reshape(2,3) + 10
    >>> a
    array([[10, 11, 12],
           [13, 14, 15]])
    >>> np.argmin(a)
    0
    >>> np.argmin(a, axis=0)
    array([0, 0, 0])
    >>> np.argmin(a, axis=1)
    array([0, 0])

    Indices of the minimum elements of a N-dimensional array:

    >>> ind = np.unravel_index(np.argmin(a, axis=None), a.shape)
    >>> ind
    (0, 0)
    >>> a[ind]
    10

    >>> b = np.arange(6) + 10
    >>> b[4] = 10
    >>> b
    array([10, 11, 12, 13, 10, 15])
    >>> np.argmin(b)  # Only the first occurrence is returned.
    0

    >>> x = np.array([[4,2,3], [1,0,3]])
    >>> index_array = np.argmin(x, axis=-1)
    >>> # Same as np.amin(x, axis=-1, keepdims=True)
    >>> np.take_along_axis(x, np.expand_dims(index_array, axis=-1), axis=-1)
    array([[2],
           [0]])
    >>> # Same as np.amax(x, axis=-1)
    >>> np.take_along_axis(x, np.expand_dims(index_array, axis=-1),
    ...     axis=-1).squeeze(axis=-1)
    array([2, 0])

    Setting `keepdims` to `True`,

    >>> x = np.arange(24).reshape((2, 3, 4))
    >>> res = np.argmin(x, axis=1, keepdims=True)
    >>> res.shape
    (2, 1, 4)
    """
    kwds = {'keepdims': keepdims} if keepdims is not np._NoValue else {}
    return _wrapfunc(a, 'argmin', axis=axis, out=out, **kwds)


def _searchsorted_dispatcher(a, v, side=None, sorter=None):
    return (a, v, sorter)


@array_function_dispatch(_searchsorted_dispatcher)
def searchsorted(a, v, side='left', sorter=None):
    """
    Find indices where elements should be inserted to maintain order.

    Find the indices into a sorted array `a` such that, if the
    corresponding elements in `v` were inserted before the indices, the
    order of `a` would be preserved.

    Assuming that `a` is sorted:

    ======  ============================
    `side`  returned index `i` satisfies
    ======  ============================
    left    ``a[i-1] < v <= a[i]``
    right   ``a[i-1] <= v < a[i]``
    ======  ============================

    Parameters
    ----------
    a : 1-D array_like
        Input array. If `sorter` is None, then it must be sorted in
        ascending order, otherwise `sorter` must be an array of indices
        that sort it.
    v : array_like
        Values to insert into `a`.
    side : {'left', 'right'}, optional
        If 'left', the index of the first suitable location found is given.
        If 'right', return the last such index.  If there is no suitable
        index, return either 0 or N (where N is the length of `a`).
    sorter : 1-D array_like, optional
        Optional array of integer indices that sort array a into ascending
        order. They are typically the result of argsort.

    Returns
    -------
    indices : int or array of ints
        Array of insertion points with the same shape as `v`,
        or an integer if `v` is a scalar.

    See Also
    --------
    sort : Return a sorted copy of an array.
    histogram : Produce histogram from 1-D data.

    Notes
    -----
    Binary search is used to find the required insertion points.

    As of NumPy 1.4.0 `searchsorted` works with real/complex arrays containing
    `nan` values. The enhanced sort order is documented in `sort`.

    This function uses the same algorithm as the builtin python
    `bisect.bisect_left` (``side='left'``) and `bisect.bisect_right`
    (``side='right'``) functions, which is also vectorized
    in the `v` argument.

    Examples
    --------
    >>> import numpy as np
    >>> np.searchsorted([11,12,13,14,15], 13)
    2
    >>> np.searchsorted([11,12,13,14,15], 13, side='right')
    3
    >>> np.searchsorted([11,12,13,14,15], [-10, 20, 12, 13])
    array([0, 5, 1, 2])

    When `sorter` is used, the returned indices refer to the sorted
    array of `a` and not `a` itself:

    >>> a = np.array([40, 10, 20, 30])
    >>> sorter = np.argsort(a)
    >>> sorter
    array([1, 2, 3, 0])  # Indices that would sort the array 'a'
    >>> result = np.searchsorted(a, 25, sorter=sorter)
    >>> result
    2
    >>> a[sorter[result]]
    30  # The element at index 2 of the sorted array is 30.
    """
    return _wrapfunc(a, 'searchsorted', v, side=side, sorter=sorter)


def _resize_dispatcher(a, new_shape):
    return (a,)


@array_function_dispatch(_resize_dispatcher)
def resize(a, new_shape):
    """
    Return a new array with the specified shape.

    If the new array is larger than the original array, then the new
    array is filled with repeated copies of `a`.  Note that this behavior
    is different from a.resize(new_shape) which fills with zeros instead
    of repeated copies of `a`.

    Parameters
    ----------
    a : array_like
        Array to be resized.

    new_shape : int or tuple of int
        Shape of resized array.

    Returns
    -------
    reshaped_array : ndarray
        The new array is formed from the data in the old array, repeated
        if necessary to fill out the required number of elements.  The
        data are repeated iterating over the array in C-order.

    See Also
    --------
    numpy.reshape : Reshape an array without changing the total size.
    numpy.pad : Enlarge and pad an array.
    numpy.repeat : Repeat elements of an array.
    ndarray.resize : resize an array in-place.

    Notes
    -----
    When the total size of the array does not change `~numpy.reshape` should
    be used.  In most other cases either indexing (to reduce the size)
    or padding (to increase the size) may be a more appropriate solution.

    Warning: This functionality does **not** consider axes separately,
    i.e. it does not apply interpolation/extrapolation.
    It fills the return array with the required number of elements, iterating
    over `a` in C-order, disregarding axes (and cycling back from the start if
    the new shape is larger).  This functionality is therefore not suitable to
    resize images, or data where each axis represents a separate and distinct
    entity.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[0,1],[2,3]])
    >>> np.resize(a,(2,3))
    array([[0, 1, 2],
           [3, 0, 1]])
    >>> np.resize(a,(1,4))
    array([[0, 1, 2, 3]])
    >>> np.resize(a,(2,4))
    array([[0, 1, 2, 3],
           [0, 1, 2, 3]])

    """
    if isinstance(new_shape, (int, nt.integer)):
        new_shape = (new_shape,)

    a = ravel(a)

    new_size = 1
    for dim_length in new_shape:
        new_size *= dim_length
        if dim_length < 0:
            raise ValueError(
                'all elements of `new_shape` must be non-negative'
            )

    if a.size == 0 or new_size == 0:
        # First case must zero fill. The second would have repeats == 0.
        return np.zeros_like(a, shape=new_shape)

    # ceiling division without negating new_size
    repeats = (new_size + a.size - 1) // a.size
    a = concatenate((a,) * repeats)[:new_size]

    return reshape(a, new_shape)


def _squeeze_dispatcher(a, axis=None):
    return (a,)


@array_function_dispatch(_squeeze_dispatcher)
def squeeze(a, axis=None):
    """
    Remove axes of length one from `a`.

    Parameters
    ----------
    a : array_like
        Input data.
    axis : None or int or tuple of ints, optional
        Selects a subset of the entries of length one in the
        shape. If an axis is selected with shape entry greater than
        one, an error is raised.

    Returns
    -------
    squeezed : ndarray
        The input array, but with all or a subset of the
        dimensions of length 1 removed. This is always `a` itself
        or a view into `a`. Note that if all axes are squeezed,
        the result is a 0d array and not a scalar.

    Raises
    ------
    ValueError
        If `axis` is not None, and an axis being squeezed is not of length 1

    See Also
    --------
    expand_dims : The inverse operation, adding entries of length one
    reshape : Insert, remove, and combine dimensions, and resize existing ones

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[[0], [1], [2]]])
    >>> x.shape
    (1, 3, 1)
    >>> np.squeeze(x).shape
    (3,)
    >>> np.squeeze(x, axis=0).shape
    (3, 1)
    >>> np.squeeze(x, axis=1).shape
    Traceback (most recent call last):
    ...
    ValueError: cannot select an axis to squeeze out which has size
    not equal to one
    >>> np.squeeze(x, axis=2).shape
    (1, 3)
    >>> x = np.array([[1234]])
    >>> x.shape
    (1, 1)
    >>> np.squeeze(x)
    array(1234)  # 0d array
    >>> np.squeeze(x).shape
    ()
    >>> np.squeeze(x)[()]
    1234

    """
    try:
        squeeze = a.squeeze
    except AttributeError:
        return _wrapit(a, 'squeeze', axis=axis)
    if axis is None:
        return squeeze()
    else:
        return squeeze(axis=axis)


def _diagonal_dispatcher(a, offset=None, axis1=None, axis2=None):
    return (a,)


@array_function_dispatch(_diagonal_dispatcher)
def diagonal(a, offset=0, axis1=0, axis2=1):
    """
    Return specified diagonals.

    If `a` is 2-D, returns the diagonal of `a` with the given offset,
    i.e., the collection of elements of the form ``a[i, i+offset]``.  If
    `a` has more than two dimensions, then the axes specified by `axis1`
    and `axis2` are used to determine the 2-D sub-array whose diagonal is
    returned.  The shape of the resulting array can be determined by
    removing `axis1` and `axis2` and appending an index to the right equal
    to the size of the resulting diagonals.

    In versions of NumPy prior to 1.7, this function always returned a new,
    independent array containing a copy of the values in the diagonal.

    In NumPy 1.7 and 1.8, it continues to return a copy of the diagonal,
    but depending on this fact is deprecated. Writing to the resulting
    array continues to work as it used to, but a FutureWarning is issued.

    Starting in NumPy 1.9 it returns a read-only view on the original array.
    Attempting to write to the resulting array will produce an error.

    In some future release, it will return a read/write view and writing to
    the returned array will alter your original array.  The returned array
    will have the same type as the input array.

    If you don't write to the array returned by this function, then you can
    just ignore all of the above.

    If you depend on the current behavior, then we suggest copying the
    returned array explicitly, i.e., use ``np.diagonal(a).copy()`` instead
    of just ``np.diagonal(a)``. This will work with both past and future
    versions of NumPy.

    Parameters
    ----------
    a : array_like
        Array from which the diagonals are taken.
    offset : int, optional
        Offset of the diagonal from the main diagonal.  Can be positive or
        negative.  Defaults to main diagonal (0).
    axis1 : int, optional
        Axis to be used as the first axis of the 2-D sub-arrays from which
        the diagonals should be taken.  Defaults to first axis (0).
    axis2 : int, optional
        Axis to be used as the second axis of the 2-D sub-arrays from
        which the diagonals should be taken. Defaults to second axis (1).

    Returns
    -------
    array_of_diagonals : ndarray
        If `a` is 2-D, then a 1-D array containing the diagonal and of the
        same type as `a` is returned unless `a` is a `matrix`, in which case
        a 1-D array rather than a (2-D) `matrix` is returned in order to
        maintain backward compatibility.

        If ``a.ndim > 2``, then the dimensions specified by `axis1` and `axis2`
        are removed, and a new axis inserted at the end corresponding to the
        diagonal.

    Raises
    ------
    ValueError
        If the dimension of `a` is less than 2.

    See Also
    --------
    diag : MATLAB work-a-like for 1-D and 2-D arrays.
    diagflat : Create diagonal arrays.
    trace : Sum along diagonals.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(4).reshape(2,2)
    >>> a
    array([[0, 1],
           [2, 3]])
    >>> a.diagonal()
    array([0, 3])
    >>> a.diagonal(1)
    array([1])

    A 3-D example:

    >>> a = np.arange(8).reshape(2,2,2); a
    array([[[0, 1],
            [2, 3]],
           [[4, 5],
            [6, 7]]])
    >>> a.diagonal(0,  # Main diagonals of two arrays created by skipping
    ...            0,  # across the outer(left)-most axis last and
    ...            1)  # the "middle" (row) axis first.
    array([[0, 6],
           [1, 7]])

    The sub-arrays whose main diagonals we just obtained; note that each
    corresponds to fixing the right-most (column) axis, and that the
    diagonals are "packed" in rows.

    >>> a[:,:,0]  # main diagonal is [0 6]
    array([[0, 2],
           [4, 6]])
    >>> a[:,:,1]  # main diagonal is [1 7]
    array([[1, 3],
           [5, 7]])

    The anti-diagonal can be obtained by reversing the order of elements
    using either `numpy.flipud` or `numpy.fliplr`.

    >>> a = np.arange(9).reshape(3, 3)
    >>> a
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])
    >>> np.fliplr(a).diagonal()  # Horizontal flip
    array([2, 4, 6])
    >>> np.flipud(a).diagonal()  # Vertical flip
    array([6, 4, 2])

    Note that the order in which the diagonal is retrieved varies depending
    on the flip function.
    """
    if isinstance(a, np.matrix):
        # Make diagonal of matrix 1-D to preserve backward compatibility.
        return asarray(a).diagonal(offset=offset, axis1=axis1, axis2=axis2)
    else:
        return asanyarray(a).diagonal(offset=offset, axis1=axis1, axis2=axis2)


def _trace_dispatcher(
        a, offset=None, axis1=None, axis2=None, dtype=None, out=None):
    return (a, out)


@array_function_dispatch(_trace_dispatcher)
def trace(a, offset=0, axis1=0, axis2=1, dtype=None, out=None):
    """
    Return the sum along diagonals of the array.

    If `a` is 2-D, the sum along its diagonal with the given offset
    is returned, i.e., the sum of elements ``a[i,i+offset]`` for all i.

    If `a` has more than two dimensions, then the axes specified by axis1 and
    axis2 are used to determine the 2-D sub-arrays whose traces are returned.
    The shape of the resulting array is the same as that of `a` with `axis1`
    and `axis2` removed.

    Parameters
    ----------
    a : array_like
        Input array, from which the diagonals are taken.
    offset : int, optional
        Offset of the diagonal from the main diagonal. Can be both positive
        and negative. Defaults to 0.
    axis1, axis2 : int, optional
        Axes to be used as the first and second axis of the 2-D sub-arrays
        from which the diagonals should be taken. Defaults are the first two
        axes of `a`.
    dtype : dtype, optional
        Determines the data-type of the returned array and of the accumulator
        where the elements are summed. If dtype has the value None and `a` is
        of integer type of precision less than the default integer
        precision, then the default integer precision is used. Otherwise,
        the precision is the same as that of `a`.
    out : ndarray, optional
        Array into which the output is placed. Its type is preserved and
        it must be of the right shape to hold the output.

    Returns
    -------
    sum_along_diagonals : ndarray
        If `a` is 2-D, the sum along the diagonal is returned.  If `a` has
        larger dimensions, then an array of sums along diagonals is returned.

    See Also
    --------
    diag, diagonal, diagflat

    Examples
    --------
    >>> import numpy as np
    >>> np.trace(np.eye(3))
    3.0
    >>> a = np.arange(8).reshape((2,2,2))
    >>> np.trace(a)
    array([6, 8])

    >>> a = np.arange(24).reshape((2,2,2,3))
    >>> np.trace(a).shape
    (2, 3)

    """
    if isinstance(a, np.matrix):
        # Get trace of matrix via an array to preserve backward compatibility.
        return asarray(a).trace(
            offset=offset, axis1=axis1, axis2=axis2, dtype=dtype, out=out
        )
    else:
        return asanyarray(a).trace(
            offset=offset, axis1=axis1, axis2=axis2, dtype=dtype, out=out
        )


def _ravel_dispatcher(a, order=None):
    return (a,)


@array_function_dispatch(_ravel_dispatcher)
def ravel(a, order='C'):
    """Return a contiguous flattened array.

    A 1-D array, containing the elements of the input, is returned.  A copy is
    made only if needed.

    As of NumPy 1.10, the returned array will have the same type as the input
    array. (for example, a masked array will be returned for a masked array
    input)

    Parameters
    ----------
    a : array_like
        Input array.  The elements in `a` are read in the order specified by
        `order`, and packed as a 1-D array.
    order : {'C','F', 'A', 'K'}, optional

        The elements of `a` are read using this index order. 'C' means
        to index the elements in row-major, C-style order,
        with the last axis index changing fastest, back to the first
        axis index changing slowest.  'F' means to index the elements
        in column-major, Fortran-style order, with the
        first index changing fastest, and the last index changing
        slowest. Note that the 'C' and 'F' options take no account of
        the memory layout of the underlying array, and only refer to
        the order of axis indexing.  'A' means to read the elements in
        Fortran-like index order if `a` is Fortran *contiguous* in
        memory, C-like order otherwise.  'K' means to read the
        elements in the order they occur in memory, except for
        reversing the data when strides are negative.  By default, 'C'
        index order is used.

    Returns
    -------
    y : array_like
        y is a contiguous 1-D array of the same subtype as `a`,
        with shape ``(a.size,)``.
        Note that matrices are special cased for backward compatibility,
        if `a` is a matrix, then y is a 1-D ndarray.

    See Also
    --------
    ndarray.flat : 1-D iterator over an array.
    ndarray.flatten : 1-D array copy of the elements of an array
                      in row-major order.
    ndarray.reshape : Change the shape of an array without changing its data.

    Notes
    -----
    In row-major, C-style order, in two dimensions, the row index
    varies the slowest, and the column index the quickest.  This can
    be generalized to multiple dimensions, where row-major order
    implies that the index along the first axis varies slowest, and
    the index along the last quickest.  The opposite holds for
    column-major, Fortran-style index ordering.

    When a view is desired in as many cases as possible, ``arr.reshape(-1)``
    may be preferable. However, ``ravel`` supports ``K`` in the optional
    ``order`` argument while ``reshape`` does not.

    Examples
    --------
    It is equivalent to ``reshape(-1, order=order)``.

    >>> import numpy as np
    >>> x = np.array([[1, 2, 3], [4, 5, 6]])
    >>> np.ravel(x)
    array([1, 2, 3, 4, 5, 6])

    >>> x.reshape(-1)
    array([1, 2, 3, 4, 5, 6])

    >>> np.ravel(x, order='F')
    array([1, 4, 2, 5, 3, 6])

    When ``order`` is 'A', it will preserve the array's 'C' or 'F' ordering:

    >>> np.ravel(x.T)
    array([1, 4, 2, 5, 3, 6])
    >>> np.ravel(x.T, order='A')
    array([1, 2, 3, 4, 5, 6])

    When ``order`` is 'K', it will preserve orderings that are neither 'C'
    nor 'F', but won't reverse axes:

    >>> a = np.arange(3)[::-1]; a
    array([2, 1, 0])
    >>> a.ravel(order='C')
    array([2, 1, 0])
    >>> a.ravel(order='K')
    array([2, 1, 0])

    >>> a = np.arange(12).reshape(2,3,2).swapaxes(1,2); a
    array([[[ 0,  2,  4],
            [ 1,  3,  5]],
           [[ 6,  8, 10],
            [ 7,  9, 11]]])
    >>> a.ravel(order='C')
    array([ 0,  2,  4,  1,  3,  5,  6,  8, 10,  7,  9, 11])
    >>> a.ravel(order='K')
    array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11])

    """
    if isinstance(a, np.matrix):
        return asarray(a).ravel(order=order)
    else:
        return asanyarray(a).ravel(order=order)


def _nonzero_dispatcher(a):
    return (a,)


@array_function_dispatch(_nonzero_dispatcher)
def nonzero(a):
    """
    Return the indices of the elements that are non-zero.

    Returns a tuple of arrays, one for each dimension of `a`,
    containing the indices of the non-zero elements in that
    dimension. The values in `a` are always tested and returned in
    row-major, C-style order.

    To group the indices by element, rather than dimension, use `argwhere`,
    which returns a row for each non-zero element.

    .. note::

       When called on a zero-d array or scalar, ``nonzero(a)`` is treated
       as ``nonzero(atleast_1d(a))``.

       .. deprecated:: 1.17.0

          Use `atleast_1d` explicitly if this behavior is deliberate.

    Parameters
    ----------
    a : array_like
        Input array.

    Returns
    -------
    tuple_of_arrays : tuple
        Indices of elements that are non-zero.

    See Also
    --------
    flatnonzero :
        Return indices that are non-zero in the flattened version of the input
        array.
    ndarray.nonzero :
        Equivalent ndarray method.
    count_nonzero :
        Counts the number of non-zero elements in the input array.

    Notes
    -----
    While the nonzero values can be obtained with ``a[nonzero(a)]``, it is
    recommended to use ``x[x.astype(bool)]`` or ``x[x != 0]`` instead, which
    will correctly handle 0-d arrays.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[3, 0, 0], [0, 4, 0], [5, 6, 0]])
    >>> x
    array([[3, 0, 0],
           [0, 4, 0],
           [5, 6, 0]])
    >>> np.nonzero(x)
    (array([0, 1, 2, 2]), array([0, 1, 0, 1]))

    >>> x[np.nonzero(x)]
    array([3, 4, 5, 6])
    >>> np.transpose(np.nonzero(x))
    array([[0, 0],
           [1, 1],
           [2, 0],
           [2, 1]])

    A common use for ``nonzero`` is to find the indices of an array, where
    a condition is True.  Given an array `a`, the condition `a` > 3 is a
    boolean array and since False is interpreted as 0, np.nonzero(a > 3)
    yields the indices of the `a` where the condition is true.

    >>> a = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    >>> a > 3
    array([[False, False, False],
           [ True,  True,  True],
           [ True,  True,  True]])
    >>> np.nonzero(a > 3)
    (array([1, 1, 1, 2, 2, 2]), array([0, 1, 2, 0, 1, 2]))

    Using this result to index `a` is equivalent to using the mask directly:

    >>> a[np.nonzero(a > 3)]
    array([4, 5, 6, 7, 8, 9])
    >>> a[a > 3]  # prefer this spelling
    array([4, 5, 6, 7, 8, 9])

    ``nonzero`` can also be called as a method of the array.

    >>> (a > 3).nonzero()
    (array([1, 1, 1, 2, 2, 2]), array([0, 1, 2, 0, 1, 2]))

    """
    return _wrapfunc(a, 'nonzero')


def _shape_dispatcher(a):
    return (a,)


@array_function_dispatch(_shape_dispatcher)
def shape(a):
    """
    Return the shape of an array.

    Parameters
    ----------
    a : array_like
        Input array.

    Returns
    -------
    shape : tuple of ints
        The elements of the shape tuple give the lengths of the
        corresponding array dimensions.

    See Also
    --------
    len : ``len(a)`` is equivalent to ``np.shape(a)[0]`` for N-D arrays with
          ``N>=1``.
    ndarray.shape : Equivalent array method.

    Examples
    --------
    >>> import numpy as np
    >>> np.shape(np.eye(3))
    (3, 3)
    >>> np.shape([[1, 3]])
    (1, 2)
    >>> np.shape([0])
    (1,)
    >>> np.shape(0)
    ()

    >>> a = np.array([(1, 2), (3, 4), (5, 6)],
    ...              dtype=[('x', 'i4'), ('y', 'i4')])
    >>> np.shape(a)
    (3,)
    >>> a.shape
    (3,)

    """
    try:
        result = a.shape
    except AttributeError:
        result = asarray(a).shape
    return result


def _compress_dispatcher(condition, a, axis=None, out=None):
    return (condition, a, out)


@array_function_dispatch(_compress_dispatcher)
def compress(condition, a, axis=None, out=None):
    """
    Return selected slices of an array along given axis.

    When working along a given axis, a slice along that axis is returned in
    `output` for each index where `condition` evaluates to True. When
    working on a 1-D array, `compress` is equivalent to `extract`.

    Parameters
    ----------
    condition : 1-D array of bools
        Array that selects which entries to return. If len(condition)
        is less than the size of `a` along the given axis, then output is
        truncated to the length of the condition array.
    a : array_like
        Array from which to extract a part.
    axis : int, optional
        Axis along which to take slices. If None (default), work on the
        flattened array.
    out : ndarray, optional
        Output array.  Its type is preserved and it must be of the right
        shape to hold the output.

    Returns
    -------
    compressed_array : ndarray
        A copy of `a` without the slices along axis for which `condition`
        is false.

    See Also
    --------
    take, choose, diag, diagonal, select
    ndarray.compress : Equivalent method in ndarray
    extract : Equivalent method when working on 1-D arrays
    :ref:`ufuncs-output-type`

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4], [5, 6]])
    >>> a
    array([[1, 2],
           [3, 4],
           [5, 6]])
    >>> np.compress([0, 1], a, axis=0)
    array([[3, 4]])
    >>> np.compress([False, True, True], a, axis=0)
    array([[3, 4],
           [5, 6]])
    >>> np.compress([False, True], a, axis=1)
    array([[2],
           [4],
           [6]])

    Working on the flattened array does not return slices along an axis but
    selects elements.

    >>> np.compress([False, True], a)
    array([2])

    """
    return _wrapfunc(a, 'compress', condition, axis=axis, out=out)


def _clip_dispatcher(a, a_min=None, a_max=None, out=None, *, min=None,
                     max=None, **kwargs):
    return (a, a_min, a_max, out, min, max)


@array_function_dispatch(_clip_dispatcher)
def clip(a, a_min=np._NoValue, a_max=np._NoValue, out=None, *,
         min=np._NoValue, max=np._NoValue, **kwargs):
    """
    Clip (limit) the values in an array.

    Given an interval, values outside the interval are clipped to
    the interval edges.  For example, if an interval of ``[0, 1]``
    is specified, values smaller than 0 become 0, and values larger
    than 1 become 1.

    Equivalent to but faster than ``np.minimum(a_max, np.maximum(a, a_min))``.

    No check is performed to ensure ``a_min < a_max``.

    Parameters
    ----------
    a : array_like
        Array containing elements to clip.
    a_min, a_max : array_like or None
        Minimum and maximum value. If ``None``, clipping is not performed on
        the corresponding edge. If both ``a_min`` and ``a_max`` are ``None``,
        the elements of the returned array stay the same. Both are broadcasted
        against ``a``.
    out : ndarray, optional
        The results will be placed in this array. It may be the input
        array for in-place clipping.  `out` must be of the right shape
        to hold the output.  Its type is preserved.
    min, max : array_like or None
        Array API compatible alternatives for ``a_min`` and ``a_max``
        arguments. Either ``a_min`` and ``a_max`` or ``min`` and ``max``
        can be passed at the same time. Default: ``None``.

        .. versionadded:: 2.1.0
    **kwargs
        For other keyword-only arguments, see the
        :ref:`ufunc docs <ufuncs.kwargs>`.

    Returns
    -------
    clipped_array : ndarray
        An array with the elements of `a`, but where values
        < `a_min` are replaced with `a_min`, and those > `a_max`
        with `a_max`.

    See Also
    --------
    :ref:`ufuncs-output-type`

    Notes
    -----
    When `a_min` is greater than `a_max`, `clip` returns an
    array in which all values are equal to `a_max`,
    as shown in the second example.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10)
    >>> a
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> np.clip(a, 1, 8)
    array([1, 1, 2, 3, 4, 5, 6, 7, 8, 8])
    >>> np.clip(a, 8, 1)
    array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    >>> np.clip(a, 3, 6, out=a)
    array([3, 3, 3, 3, 4, 5, 6, 6, 6, 6])
    >>> a
    array([3, 3, 3, 3, 4, 5, 6, 6, 6, 6])
    >>> a = np.arange(10)
    >>> a
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> np.clip(a, [3, 4, 1, 1, 1, 4, 4, 4, 4, 4], 8)
    array([3, 4, 2, 3, 4, 5, 6, 7, 8, 8])

    """
    if a_min is np._NoValue and a_max is np._NoValue:
        a_min = None if min is np._NoValue else min
        a_max = None if max is np._NoValue else max
    elif a_min is np._NoValue:
        raise TypeError("clip() missing 1 required positional "
                        "argument: 'a_min'")
    elif a_max is np._NoValue:
        raise TypeError("clip() missing 1 required positional "
                        "argument: 'a_max'")
    elif min is not np._NoValue or max is not np._NoValue:
        raise ValueError("Passing `min` or `max` keyword argument when "
                         "`a_min` and `a_max` are provided is forbidden.")

    return _wrapfunc(a, 'clip', a_min, a_max, out=out, **kwargs)


def _sum_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                    initial=None, where=None):
    return (a, out)


@array_function_dispatch(_sum_dispatcher)
def sum(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
        initial=np._NoValue, where=np._NoValue):
    """
    Sum of array elements over a given axis.

    Parameters
    ----------
    a : array_like
        Elements to sum.
    axis : None or int or tuple of ints, optional
        Axis or axes along which a sum is performed.  The default,
        axis=None, will sum all of the elements of the input array.  If
        axis is negative it counts from the last to the first axis. If
        axis is a tuple of ints, a sum is performed on all of the axes
        specified in the tuple instead of a single axis or all the axes as
        before.
    dtype : dtype, optional
        The type of the returned array and of the accumulator in which the
        elements are summed.  The dtype of `a` is used by default unless `a`
        has an integer dtype of less precision than the default platform
        integer.  In that case, if `a` is signed then the platform integer
        is used while if `a` is unsigned then an unsigned integer of the
        same precision as the platform integer is used.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape as the expected output, but the type of the output
        values will be cast if necessary.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `sum` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.
    initial : scalar, optional
        Starting value for the sum. See `~numpy.ufunc.reduce` for details.
    where : array_like of bool, optional
        Elements to include in the sum. See `~numpy.ufunc.reduce` for details.

    Returns
    -------
    sum_along_axis : ndarray
        An array with the same shape as `a`, with the specified
        axis removed.   If `a` is a 0-d array, or if `axis` is None, a scalar
        is returned.  If an output array is specified, a reference to
        `out` is returned.

    See Also
    --------
    ndarray.sum : Equivalent method.
    add: ``numpy.add.reduce`` equivalent function.
    cumsum : Cumulative sum of array elements.
    trapezoid : Integration of array values using composite trapezoidal rule.

    mean, average

    Notes
    -----
    Arithmetic is modular when using integer types, and no error is
    raised on overflow.

    The sum of an empty array is the neutral element 0:

    >>> np.sum([])
    0.0

    For floating point numbers the numerical precision of sum (and
    ``np.add.reduce``) is in general limited by directly adding each number
    individually to the result causing rounding errors in every step.
    However, often numpy will use a  numerically better approach (partial
    pairwise summation) leading to improved precision in many use-cases.
    This improved precision is always provided when no ``axis`` is given.
    When ``axis`` is given, it will depend on which axis is summed.
    Technically, to provide the best speed possible, the improved precision
    is only used when the summation is along the fast axis in memory.
    Note that the exact precision may vary depending on other parameters.
    In contrast to NumPy, Python's ``math.fsum`` function uses a slower but
    more precise approach to summation.
    Especially when summing a large number of lower precision floating point
    numbers, such as ``float32``, numerical errors can become significant.
    In such cases it can be advisable to use `dtype="float64"` to use a higher
    precision for the output.

    Examples
    --------
    >>> import numpy as np
    >>> np.sum([0.5, 1.5])
    2.0
    >>> np.sum([0.5, 0.7, 0.2, 1.5], dtype=np.int32)
    np.int32(1)
    >>> np.sum([[0, 1], [0, 5]])
    6
    >>> np.sum([[0, 1], [0, 5]], axis=0)
    array([0, 6])
    >>> np.sum([[0, 1], [0, 5]], axis=1)
    array([1, 5])
    >>> np.sum([[0, 1], [np.nan, 5]], where=[False, True], axis=1)
    array([1., 5.])

    If the accumulator is too small, overflow occurs:

    >>> np.ones(128, dtype=np.int8).sum(dtype=np.int8)
    np.int8(-128)

    You can also start the sum with a value other than zero:

    >>> np.sum([10], initial=5)
    15
    """
    if isinstance(a, _gentype):
        # 2018-02-25, 1.15.0
        warnings.warn(
            "Calling np.sum(generator) is deprecated, and in the future will "
            "give a different result. Use np.sum(np.fromiter(generator)) or "
            "the python sum builtin instead.",
            DeprecationWarning, stacklevel=2
        )

        res = _sum_(a)
        if out is not None:
            out[...] = res
            return out
        return res

    return _wrapreduction(
        a, np.add, 'sum', axis, dtype, out,
        keepdims=keepdims, initial=initial, where=where
    )


def _any_dispatcher(a, axis=None, out=None, keepdims=None, *,
                    where=np._NoValue):
    return (a, where, out)


@array_function_dispatch(_any_dispatcher)
def any(a, axis=None, out=None, keepdims=np._NoValue, *, where=np._NoValue):
    """
    Test whether any array element along a given axis evaluates to True.

    Returns single boolean if `axis` is ``None``

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array.
    axis : None or int or tuple of ints, optional
        Axis or axes along which a logical OR reduction is performed.
        The default (``axis=None``) is to perform a logical OR over all
        the dimensions of the input array. `axis` may be negative, in
        which case it counts from the last to the first axis. If this
        is a tuple of ints, a reduction is performed on multiple
        axes, instead of a single axis or all the axes as before.
    out : ndarray, optional
        Alternate output array in which to place the result.  It must have
        the same shape as the expected output and its type is preserved
        (e.g., if it is of type float, then it will remain so, returning
        1.0 for True and 0.0 for False, regardless of the type of `a`).
        See :ref:`ufuncs-output-type` for more details.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `any` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.

    where : array_like of bool, optional
        Elements to include in checking for any `True` values.
        See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.20.0

    Returns
    -------
    any : bool or ndarray
        A new boolean or `ndarray` is returned unless `out` is specified,
        in which case a reference to `out` is returned.

    See Also
    --------
    ndarray.any : equivalent method

    all : Test whether all elements along a given axis evaluate to True.

    Notes
    -----
    Not a Number (NaN), positive infinity and negative infinity evaluate
    to `True` because these are not equal to zero.

    .. versionchanged:: 2.0
       Before NumPy 2.0, ``any`` did not return booleans for object dtype
       input arrays.
       This behavior is still available via ``np.logical_or.reduce``.

    Examples
    --------
    >>> import numpy as np
    >>> np.any([[True, False], [True, True]])
    True

    >>> np.any([[True,  False, True ],
    ...         [False, False, False]], axis=0)
    array([ True, False, True])

    >>> np.any([-1, 0, 5])
    True

    >>> np.any([[np.nan], [np.inf]], axis=1, keepdims=True)
    array([[ True],
           [ True]])

    >>> np.any([[True, False], [False, False]], where=[[False], [True]])
    False

    >>> a = np.array([[1, 0, 0],
    ...               [0, 0, 1],
    ...               [0, 0, 0]])
    >>> np.any(a, axis=0)
    array([ True, False,  True])
    >>> np.any(a, axis=1)
    array([ True,  True, False])

    >>> o=np.array(False)
    >>> z=np.any([-1, 4, 5], out=o)
    >>> z, o
    (array(True), array(True))
    >>> # Check now that z is a reference to o
    >>> z is o
    True
    >>> id(z), id(o) # identity of z and o              # doctest: +SKIP
    (191614240, 191614240)

    """
    return _wrapreduction_any_all(a, np.logical_or, 'any', axis, out,
                                  keepdims=keepdims, where=where)


def _all_dispatcher(a, axis=None, out=None, keepdims=None, *,
                    where=None):
    return (a, where, out)


@array_function_dispatch(_all_dispatcher)
def all(a, axis=None, out=None, keepdims=np._NoValue, *, where=np._NoValue):
    """
    Test whether all array elements along a given axis evaluate to True.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array.
    axis : None or int or tuple of ints, optional
        Axis or axes along which a logical AND reduction is performed.
        The default (``axis=None``) is to perform a logical AND over all
        the dimensions of the input array. `axis` may be negative, in
        which case it counts from the last to the first axis. If this
        is a tuple of ints, a reduction is performed on multiple
        axes, instead of a single axis or all the axes as before.
    out : ndarray, optional
        Alternate output array in which to place the result.
        It must have the same shape as the expected output and its
        type is preserved (e.g., if ``dtype(out)`` is float, the result
        will consist of 0.0's and 1.0's). See :ref:`ufuncs-output-type`
        for more details.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `all` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.

    where : array_like of bool, optional
        Elements to include in checking for all `True` values.
        See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.20.0

    Returns
    -------
    all : ndarray, bool
        A new boolean or array is returned unless `out` is specified,
        in which case a reference to `out` is returned.

    See Also
    --------
    ndarray.all : equivalent method

    any : Test whether any element along a given axis evaluates to True.

    Notes
    -----
    Not a Number (NaN), positive infinity and negative infinity
    evaluate to `True` because these are not equal to zero.

    .. versionchanged:: 2.0
       Before NumPy 2.0, ``all`` did not return booleans for object dtype
       input arrays.
       This behavior is still available via ``np.logical_and.reduce``.

    Examples
    --------
    >>> import numpy as np
    >>> np.all([[True,False],[True,True]])
    False

    >>> np.all([[True,False],[True,True]], axis=0)
    array([ True, False])

    >>> np.all([-1, 4, 5])
    True

    >>> np.all([1.0, np.nan])
    True

    >>> np.all([[True, True], [False, True]], where=[[True], [False]])
    True

    >>> o=np.array(False)
    >>> z=np.all([-1, 4, 5], out=o)
    >>> id(z), id(o), z
    (28293632, 28293632, array(True)) # may vary

    """
    return _wrapreduction_any_all(a, np.logical_and, 'all', axis, out,
                                  keepdims=keepdims, where=where)


def _cumulative_func(x, func, axis, dtype, out, include_initial):
    x = np.atleast_1d(x)
    x_ndim = x.ndim
    if axis is None:
        if x_ndim >= 2:
            raise ValueError("For arrays which have more than one dimension "
                            "``axis`` argument is required.")
        axis = 0

    if out is not None and include_initial:
        item = [slice(None)] * x_ndim
        item[axis] = slice(1, None)
        func.accumulate(x, axis=axis, dtype=dtype, out=out[tuple(item)])
        item[axis] = 0
        out[tuple(item)] = func.identity
        return out

    res = func.accumulate(x, axis=axis, dtype=dtype, out=out)
    if include_initial:
        initial_shape = list(x.shape)
        initial_shape[axis] = 1
        res = np.concat(
            [np.full_like(res, func.identity, shape=initial_shape), res],
            axis=axis,
        )

    return res


def _cumulative_prod_dispatcher(x, /, *, axis=None, dtype=None, out=None,
                                include_initial=None):
    return (x, out)


@array_function_dispatch(_cumulative_prod_dispatcher)
def cumulative_prod(x, /, *, axis=None, dtype=None, out=None,
                    include_initial=False):
    """
    Return the cumulative product of elements along a given axis.

    This function is an Array API compatible alternative to `numpy.cumprod`.

    Parameters
    ----------
    x : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative product is computed. The default
        (None) is only allowed for one-dimensional arrays. For arrays
        with more than one dimension ``axis`` is required.
    dtype : dtype, optional
        Type of the returned array, as well as of the accumulator in which
        the elements are multiplied.  If ``dtype`` is not specified, it
        defaults to the dtype of ``x``, unless ``x`` has an integer dtype
        with a precision less than that of the default platform integer.
        In that case, the default platform integer is used instead.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type of the resulting values will be cast if necessary.
        See :ref:`ufuncs-output-type` for more details.
    include_initial : bool, optional
        Boolean indicating whether to include the initial value (ones) as
        the first value in the output. With ``include_initial=True``
        the shape of the output is different than the shape of the input.
        Default: ``False``.

    Returns
    -------
    cumulative_prod_along_axis : ndarray
        A new array holding the result is returned unless ``out`` is
        specified, in which case a reference to ``out`` is returned. The
        result has the same shape as ``x`` if ``include_initial=False``.

    Notes
    -----
    Arithmetic is modular when using integer types, and no error is
    raised on overflow.

    Examples
    --------
    >>> a = np.array([1, 2, 3])
    >>> np.cumulative_prod(a)  # intermediate results 1, 1*2
    ...                        # total product 1*2*3 = 6
    array([1, 2, 6])
    >>> a = np.array([1, 2, 3, 4, 5, 6])
    >>> np.cumulative_prod(a, dtype=float) # specify type of output
    array([   1.,    2.,    6.,   24.,  120.,  720.])

    The cumulative product for each column (i.e., over the rows) of ``b``:

    >>> b = np.array([[1, 2, 3], [4, 5, 6]])
    >>> np.cumulative_prod(b, axis=0)
    array([[ 1,  2,  3],
           [ 4, 10, 18]])

    The cumulative product for each row (i.e. over the columns) of ``b``:

    >>> np.cumulative_prod(b, axis=1)
    array([[  1,   2,   6],
           [  4,  20, 120]])

    """
    return _cumulative_func(x, um.multiply, axis, dtype, out, include_initial)


def _cumulative_sum_dispatcher(x, /, *, axis=None, dtype=None, out=None,
                               include_initial=None):
    return (x, out)


@array_function_dispatch(_cumulative_sum_dispatcher)
def cumulative_sum(x, /, *, axis=None, dtype=None, out=None,
                   include_initial=False):
    """
    Return the cumulative sum of the elements along a given axis.

    This function is an Array API compatible alternative to `numpy.cumsum`.

    Parameters
    ----------
    x : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative sum is computed. The default
        (None) is only allowed for one-dimensional arrays. For arrays
        with more than one dimension ``axis`` is required.
    dtype : dtype, optional
        Type of the returned array and of the accumulator in which the
        elements are summed.  If ``dtype`` is not specified, it defaults
        to the dtype of ``x``, unless ``x`` has an integer dtype with
        a precision less than that of the default platform integer.
        In that case, the default platform integer is used.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type will be cast if necessary. See :ref:`ufuncs-output-type`
        for more details.
    include_initial : bool, optional
        Boolean indicating whether to include the initial value (zeros) as
        the first value in the output. With ``include_initial=True``
        the shape of the output is different than the shape of the input.
        Default: ``False``.

    Returns
    -------
    cumulative_sum_along_axis : ndarray
        A new array holding the result is returned unless ``out`` is
        specified, in which case a reference to ``out`` is returned. The
        result has the same shape as ``x`` if ``include_initial=False``.

    See Also
    --------
    sum : Sum array elements.
    trapezoid : Integration of array values using composite trapezoidal rule.
    diff : Calculate the n-th discrete difference along given axis.

    Notes
    -----
    Arithmetic is modular when using integer types, and no error is
    raised on overflow.

    ``cumulative_sum(a)[-1]`` may not be equal to ``sum(a)`` for
    floating-point values since ``sum`` may use a pairwise summation routine,
    reducing the roundoff-error. See `sum` for more information.

    Examples
    --------
    >>> a = np.array([1, 2, 3, 4, 5, 6])
    >>> a
    array([1, 2, 3, 4, 5, 6])
    >>> np.cumulative_sum(a)
    array([ 1,  3,  6, 10, 15, 21])
    >>> np.cumulative_sum(a, dtype=float)  # specifies type of output value(s)
    array([  1.,   3.,   6.,  10.,  15.,  21.])

    >>> b = np.array([[1, 2, 3], [4, 5, 6]])
    >>> np.cumulative_sum(b,axis=0)  # sum over rows for each of the 3 columns
    array([[1, 2, 3],
           [5, 7, 9]])
    >>> np.cumulative_sum(b,axis=1)  # sum over columns for each of the 2 rows
    array([[ 1,  3,  6],
           [ 4,  9, 15]])

    ``cumulative_sum(c)[-1]`` may not be equal to ``sum(c)``

    >>> c = np.array([1, 2e-9, 3e-9] * 1000000)
    >>> np.cumulative_sum(c)[-1]
    1000000.0050045159
    >>> c.sum()
    1000000.0050000029

    """
    return _cumulative_func(x, um.add, axis, dtype, out, include_initial)


def _cumsum_dispatcher(a, axis=None, dtype=None, out=None):
    return (a, out)


@array_function_dispatch(_cumsum_dispatcher)
def cumsum(a, axis=None, dtype=None, out=None):
    """
    Return the cumulative sum of the elements along a given axis.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative sum is computed. The default
        (None) is to compute the cumsum over the flattened array.
    dtype : dtype, optional
        Type of the returned array and of the accumulator in which the
        elements are summed.  If `dtype` is not specified, it defaults
        to the dtype of `a`, unless `a` has an integer dtype with a
        precision less than that of the default platform integer.  In
        that case, the default platform integer is used.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type will be cast if necessary. See :ref:`ufuncs-output-type`
        for more details.

    Returns
    -------
    cumsum_along_axis : ndarray.
        A new array holding the result is returned unless `out` is
        specified, in which case a reference to `out` is returned. The
        result has the same size as `a`, and the same shape as `a` if
        `axis` is not None or `a` is a 1-d array.

    See Also
    --------
    cumulative_sum : Array API compatible alternative for ``cumsum``.
    sum : Sum array elements.
    trapezoid : Integration of array values using composite trapezoidal rule.
    diff : Calculate the n-th discrete difference along given axis.

    Notes
    -----
    Arithmetic is modular when using integer types, and no error is
    raised on overflow.

    ``cumsum(a)[-1]`` may not be equal to ``sum(a)`` for floating-point
    values since ``sum`` may use a pairwise summation routine, reducing
    the roundoff-error. See `sum` for more information.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1,2,3], [4,5,6]])
    >>> a
    array([[1, 2, 3],
           [4, 5, 6]])
    >>> np.cumsum(a)
    array([ 1,  3,  6, 10, 15, 21])
    >>> np.cumsum(a, dtype=float)     # specifies type of output value(s)
    array([  1.,   3.,   6.,  10.,  15.,  21.])

    >>> np.cumsum(a,axis=0)      # sum over rows for each of the 3 columns
    array([[1, 2, 3],
           [5, 7, 9]])
    >>> np.cumsum(a,axis=1)      # sum over columns for each of the 2 rows
    array([[ 1,  3,  6],
           [ 4,  9, 15]])

    ``cumsum(b)[-1]`` may not be equal to ``sum(b)``

    >>> b = np.array([1, 2e-9, 3e-9] * 1000000)
    >>> b.cumsum()[-1]
    1000000.0050045159
    >>> b.sum()
    1000000.0050000029

    """
    return _wrapfunc(a, 'cumsum', axis=axis, dtype=dtype, out=out)


def _ptp_dispatcher(a, axis=None, out=None, keepdims=None):
    return (a, out)


@array_function_dispatch(_ptp_dispatcher)
def ptp(a, axis=None, out=None, keepdims=np._NoValue):
    """
    Range of values (maximum - minimum) along an axis.

    The name of the function comes from the acronym for 'peak to peak'.

    .. warning::
        `ptp` preserves the data type of the array. This means the
        return value for an input of signed integers with n bits
        (e.g. `numpy.int8`, `numpy.int16`, etc) is also a signed integer
        with n bits.  In that case, peak-to-peak values greater than
        ``2**(n-1)-1`` will be returned as negative values. An example
        with a work-around is shown below.

    Parameters
    ----------
    a : array_like
        Input values.
    axis : None or int or tuple of ints, optional
        Axis along which to find the peaks.  By default, flatten the
        array.  `axis` may be negative, in
        which case it counts from the last to the first axis.
        If this is a tuple of ints, a reduction is performed on multiple
        axes, instead of a single axis or all the axes as before.
    out : array_like
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output,
        but the type of the output values will be cast if necessary.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `ptp` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.

    Returns
    -------
    ptp : ndarray or scalar
        The range of a given array - `scalar` if array is one-dimensional
        or a new array holding the result along the given axis

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[4, 9, 2, 10],
    ...               [6, 9, 7, 12]])

    >>> np.ptp(x, axis=1)
    array([8, 6])

    >>> np.ptp(x, axis=0)
    array([2, 0, 5, 2])

    >>> np.ptp(x)
    10

    This example shows that a negative value can be returned when
    the input is an array of signed integers.

    >>> y = np.array([[1, 127],
    ...               [0, 127],
    ...               [-1, 127],
    ...               [-2, 127]], dtype=np.int8)
    >>> np.ptp(y, axis=1)
    array([ 126,  127, -128, -127], dtype=int8)

    A work-around is to use the `view()` method to view the result as
    unsigned integers with the same bit width:

    >>> np.ptp(y, axis=1).view(np.uint8)
    array([126, 127, 128, 129], dtype=uint8)

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    return _methods._ptp(a, axis=axis, out=out, **kwargs)


def _max_dispatcher(a, axis=None, out=None, keepdims=None, initial=None,
                    where=None):
    return (a, out)


@array_function_dispatch(_max_dispatcher)
@set_module('numpy')
def max(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
         where=np._NoValue):
    """
    Return the maximum of an array or maximum along an axis.

    Parameters
    ----------
    a : array_like
        Input data.
    axis : None or int or tuple of ints, optional
        Axis or axes along which to operate.  By default, flattened input is
        used. If this is a tuple of ints, the maximum is selected over
        multiple axes, instead of a single axis or all the axes as before.

    out : ndarray, optional
        Alternative output array in which to place the result.  Must
        be of the same shape and buffer length as the expected output.
        See :ref:`ufuncs-output-type` for more details.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the ``max`` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.

    initial : scalar, optional
        The minimum value of an output element. Must be present to allow
        computation on empty slice. See `~numpy.ufunc.reduce` for details.

    where : array_like of bool, optional
        Elements to compare for the maximum. See `~numpy.ufunc.reduce`
        for details.

    Returns
    -------
    max : ndarray or scalar
        Maximum of `a`. If `axis` is None, the result is a scalar value.
        If `axis` is an int, the result is an array of dimension
        ``a.ndim - 1``. If `axis` is a tuple, the result is an array of
        dimension ``a.ndim - len(axis)``.

    See Also
    --------
    amin :
        The minimum value of an array along a given axis, propagating any NaNs.
    nanmax :
        The maximum value of an array along a given axis, ignoring any NaNs.
    maximum :
        Element-wise maximum of two arrays, propagating any NaNs.
    fmax :
        Element-wise maximum of two arrays, ignoring any NaNs.
    argmax :
        Return the indices of the maximum values.

    nanmin, minimum, fmin

    Notes
    -----
    NaN values are propagated, that is if at least one item is NaN, the
    corresponding max value will be NaN as well. To ignore NaN values
    (MATLAB behavior), please use nanmax.

    Don't use `~numpy.max` for element-wise comparison of 2 arrays; when
    ``a.shape[0]`` is 2, ``maximum(a[0], a[1])`` is faster than
    ``max(a, axis=0)``.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(4).reshape((2,2))
    >>> a
    array([[0, 1],
           [2, 3]])
    >>> np.max(a)           # Maximum of the flattened array
    3
    >>> np.max(a, axis=0)   # Maxima along the first axis
    array([2, 3])
    >>> np.max(a, axis=1)   # Maxima along the second axis
    array([1, 3])
    >>> np.max(a, where=[False, True], initial=-1, axis=0)
    array([-1,  3])
    >>> b = np.arange(5, dtype=float)
    >>> b[2] = np.nan
    >>> np.max(b)
    np.float64(nan)
    >>> np.max(b, where=~np.isnan(b), initial=-1)
    4.0
    >>> np.nanmax(b)
    4.0

    You can use an initial value to compute the maximum of an empty slice, or
    to initialize it to a different value:

    >>> np.max([[-50], [10]], axis=-1, initial=0)
    array([ 0, 10])

    Notice that the initial value is used as one of the elements for which the
    maximum is determined, unlike for the default argument Python's max
    function, which is only used for empty iterables.

    >>> np.max([5], initial=6)
    6
    >>> max([5], default=6)
    5
    """
    return _wrapreduction(a, np.maximum, 'max', axis, None, out,
                          keepdims=keepdims, initial=initial, where=where)


@array_function_dispatch(_max_dispatcher)
def amax(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
         where=np._NoValue):
    """
    Return the maximum of an array or maximum along an axis.

    `amax` is an alias of `~numpy.max`.

    See Also
    --------
    max : alias of this function
    ndarray.max : equivalent method
    """
    return _wrapreduction(a, np.maximum, 'max', axis, None, out,
                          keepdims=keepdims, initial=initial, where=where)


def _min_dispatcher(a, axis=None, out=None, keepdims=None, initial=None,
                    where=None):
    return (a, out)


@array_function_dispatch(_min_dispatcher)
def min(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
        where=np._NoValue):
    """
    Return the minimum of an array or minimum along an axis.

    Parameters
    ----------
    a : array_like
        Input data.
    axis : None or int or tuple of ints, optional
        Axis or axes along which to operate.  By default, flattened input is
        used.

        If this is a tuple of ints, the minimum is selected over multiple axes,
        instead of a single axis or all the axes as before.
    out : ndarray, optional
        Alternative output array in which to place the result.  Must
        be of the same shape and buffer length as the expected output.
        See :ref:`ufuncs-output-type` for more details.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the ``min`` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.

    initial : scalar, optional
        The maximum value of an output element. Must be present to allow
        computation on empty slice. See `~numpy.ufunc.reduce` for details.

    where : array_like of bool, optional
        Elements to compare for the minimum. See `~numpy.ufunc.reduce`
        for details.

    Returns
    -------
    min : ndarray or scalar
        Minimum of `a`. If `axis` is None, the result is a scalar value.
        If `axis` is an int, the result is an array of dimension
        ``a.ndim - 1``.  If `axis` is a tuple, the result is an array of
        dimension ``a.ndim - len(axis)``.

    See Also
    --------
    amax :
        The maximum value of an array along a given axis, propagating any NaNs.
    nanmin :
        The minimum value of an array along a given axis, ignoring any NaNs.
    minimum :
        Element-wise minimum of two arrays, propagating any NaNs.
    fmin :
        Element-wise minimum of two arrays, ignoring any NaNs.
    argmin :
        Return the indices of the minimum values.

    nanmax, maximum, fmax

    Notes
    -----
    NaN values are propagated, that is if at least one item is NaN, the
    corresponding min value will be NaN as well. To ignore NaN values
    (MATLAB behavior), please use nanmin.

    Don't use `~numpy.min` for element-wise comparison of 2 arrays; when
    ``a.shape[0]`` is 2, ``minimum(a[0], a[1])`` is faster than
    ``min(a, axis=0)``.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(4).reshape((2,2))
    >>> a
    array([[0, 1],
           [2, 3]])
    >>> np.min(a)           # Minimum of the flattened array
    0
    >>> np.min(a, axis=0)   # Minima along the first axis
    array([0, 1])
    >>> np.min(a, axis=1)   # Minima along the second axis
    array([0, 2])
    >>> np.min(a, where=[False, True], initial=10, axis=0)
    array([10,  1])

    >>> b = np.arange(5, dtype=float)
    >>> b[2] = np.nan
    >>> np.min(b)
    np.float64(nan)
    >>> np.min(b, where=~np.isnan(b), initial=10)
    0.0
    >>> np.nanmin(b)
    0.0

    >>> np.min([[-50], [10]], axis=-1, initial=0)
    array([-50,   0])

    Notice that the initial value is used as one of the elements for which the
    minimum is determined, unlike for the default argument Python's max
    function, which is only used for empty iterables.

    Notice that this isn't the same as Python's ``default`` argument.

    >>> np.min([6], initial=5)
    5
    >>> min([6], default=5)
    6
    """
    return _wrapreduction(a, np.minimum, 'min', axis, None, out,
                          keepdims=keepdims, initial=initial, where=where)


@array_function_dispatch(_min_dispatcher)
def amin(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
         where=np._NoValue):
    """
    Return the minimum of an array or minimum along an axis.

    `amin` is an alias of `~numpy.min`.

    See Also
    --------
    min : alias of this function
    ndarray.min : equivalent method
    """
    return _wrapreduction(a, np.minimum, 'min', axis, None, out,
                          keepdims=keepdims, initial=initial, where=where)


def _prod_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                     initial=None, where=None):
    return (a, out)


@array_function_dispatch(_prod_dispatcher)
def prod(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
         initial=np._NoValue, where=np._NoValue):
    """
    Return the product of array elements over a given axis.

    Parameters
    ----------
    a : array_like
        Input data.
    axis : None or int or tuple of ints, optional
        Axis or axes along which a product is performed.  The default,
        axis=None, will calculate the product of all the elements in the
        input array. If axis is negative it counts from the last to the
        first axis.

        If axis is a tuple of ints, a product is performed on all of the
        axes specified in the tuple instead of a single axis or all the
        axes as before.
    dtype : dtype, optional
        The type of the returned array, as well as of the accumulator in
        which the elements are multiplied.  The dtype of `a` is used by
        default unless `a` has an integer dtype of less precision than the
        default platform integer.  In that case, if `a` is signed then the
        platform integer is used while if `a` is unsigned then an unsigned
        integer of the same precision as the platform integer is used.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape as the expected output, but the type of the output
        values will be cast if necessary.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left in the
        result as dimensions with size one. With this option, the result
        will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `prod` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.
    initial : scalar, optional
        The starting value for this product. See `~numpy.ufunc.reduce`
        for details.
    where : array_like of bool, optional
        Elements to include in the product. See `~numpy.ufunc.reduce`
        for details.

    Returns
    -------
    product_along_axis : ndarray, see `dtype` parameter above.
        An array shaped as `a` but with the specified axis removed.
        Returns a reference to `out` if specified.

    See Also
    --------
    ndarray.prod : equivalent method
    :ref:`ufuncs-output-type`

    Notes
    -----
    Arithmetic is modular when using integer types, and no error is
    raised on overflow.  That means that, on a 32-bit platform:

    >>> x = np.array([536870910, 536870910, 536870910, 536870910])
    >>> np.prod(x)
    16 # may vary

    The product of an empty array is the neutral element 1:

    >>> np.prod([])
    1.0

    Examples
    --------
    By default, calculate the product of all elements:

    >>> import numpy as np
    >>> np.prod([1.,2.])
    2.0

    Even when the input array is two-dimensional:

    >>> a = np.array([[1., 2.], [3., 4.]])
    >>> np.prod(a)
    24.0

    But we can also specify the axis over which to multiply:

    >>> np.prod(a, axis=1)
    array([  2.,  12.])
    >>> np.prod(a, axis=0)
    array([3., 8.])

    Or select specific elements to include:

    >>> np.prod([1., np.nan, 3.], where=[True, False, True])
    3.0

    If the type of `x` is unsigned, then the output type is
    the unsigned platform integer:

    >>> x = np.array([1, 2, 3], dtype=np.uint8)
    >>> np.prod(x).dtype == np.uint
    True

    If `x` is of a signed integer type, then the output type
    is the default platform integer:

    >>> x = np.array([1, 2, 3], dtype=np.int8)
    >>> np.prod(x).dtype == int
    True

    You can also start the product with a value other than one:

    >>> np.prod([1, 2], initial=5)
    10
    """
    return _wrapreduction(a, np.multiply, 'prod', axis, dtype, out,
                          keepdims=keepdims, initial=initial, where=where)


def _cumprod_dispatcher(a, axis=None, dtype=None, out=None):
    return (a, out)


@array_function_dispatch(_cumprod_dispatcher)
def cumprod(a, axis=None, dtype=None, out=None):
    """
    Return the cumulative product of elements along a given axis.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative product is computed.  By default
        the input is flattened.
    dtype : dtype, optional
        Type of the returned array, as well as of the accumulator in which
        the elements are multiplied.  If *dtype* is not specified, it
        defaults to the dtype of `a`, unless `a` has an integer dtype with
        a precision less than that of the default platform integer.  In
        that case, the default platform integer is used instead.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type of the resulting values will be cast if necessary.

    Returns
    -------
    cumprod : ndarray
        A new array holding the result is returned unless `out` is
        specified, in which case a reference to out is returned.

    See Also
    --------
    cumulative_prod : Array API compatible alternative for ``cumprod``.
    :ref:`ufuncs-output-type`

    Notes
    -----
    Arithmetic is modular when using integer types, and no error is
    raised on overflow.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1,2,3])
    >>> np.cumprod(a) # intermediate results 1, 1*2
    ...               # total product 1*2*3 = 6
    array([1, 2, 6])
    >>> a = np.array([[1, 2, 3], [4, 5, 6]])
    >>> np.cumprod(a, dtype=float) # specify type of output
    array([   1.,    2.,    6.,   24.,  120.,  720.])

    The cumulative product for each column (i.e., over the rows) of `a`:

    >>> np.cumprod(a, axis=0)
    array([[ 1,  2,  3],
           [ 4, 10, 18]])

    The cumulative product for each row (i.e. over the columns) of `a`:

    >>> np.cumprod(a,axis=1)
    array([[  1,   2,   6],
           [  4,  20, 120]])

    """
    return _wrapfunc(a, 'cumprod', axis=axis, dtype=dtype, out=out)


def _ndim_dispatcher(a):
    return (a,)


@array_function_dispatch(_ndim_dispatcher)
def ndim(a):
    """
    Return the number of dimensions of an array.

    Parameters
    ----------
    a : array_like
        Input array.  If it is not already an ndarray, a conversion is
        attempted.

    Returns
    -------
    number_of_dimensions : int
        The number of dimensions in `a`.  Scalars are zero-dimensional.

    See Also
    --------
    ndarray.ndim : equivalent method
    shape : dimensions of array
    ndarray.shape : dimensions of array

    Examples
    --------
    >>> import numpy as np
    >>> np.ndim([[1,2,3],[4,5,6]])
    2
    >>> np.ndim(np.array([[1,2,3],[4,5,6]]))
    2
    >>> np.ndim(1)
    0

    """
    try:
        return a.ndim
    except AttributeError:
        return asarray(a).ndim


def _size_dispatcher(a, axis=None):
    return (a,)


@array_function_dispatch(_size_dispatcher)
def size(a, axis=None):
    """
    Return the number of elements along a given axis.

    Parameters
    ----------
    a : array_like
        Input data.
    axis : int, optional
        Axis along which the elements are counted.  By default, give
        the total number of elements.

    Returns
    -------
    element_count : int
        Number of elements along the specified axis.

    See Also
    --------
    shape : dimensions of array
    ndarray.shape : dimensions of array
    ndarray.size : number of elements in array

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1,2,3],[4,5,6]])
    >>> np.size(a)
    6
    >>> np.size(a,1)
    3
    >>> np.size(a,0)
    2

    """
    if axis is None:
        try:
            return a.size
        except AttributeError:
            return asarray(a).size
    else:
        try:
            return a.shape[axis]
        except AttributeError:
            return asarray(a).shape[axis]


def _round_dispatcher(a, decimals=None, out=None):
    return (a, out)


@array_function_dispatch(_round_dispatcher)
def round(a, decimals=0, out=None):
    """
    Evenly round to the given number of decimals.

    Parameters
    ----------
    a : array_like
        Input data.
    decimals : int, optional
        Number of decimal places to round to (default: 0).  If
        decimals is negative, it specifies the number of positions to
        the left of the decimal point.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape as the expected output, but the type of the output
        values will be cast if necessary. See :ref:`ufuncs-output-type`
        for more details.

    Returns
    -------
    rounded_array : ndarray
        An array of the same type as `a`, containing the rounded values.
        Unless `out` was specified, a new array is created.  A reference to
        the result is returned.

        The real and imaginary parts of complex numbers are rounded
        separately.  The result of rounding a float is a float.

    See Also
    --------
    ndarray.round : equivalent method
    around : an alias for this function
    ceil, fix, floor, rint, trunc


    Notes
    -----
    For values exactly halfway between rounded decimal values, NumPy
    rounds to the nearest even value. Thus 1.5 and 2.5 round to 2.0,
    -0.5 and 0.5 round to 0.0, etc.

    ``np.round`` uses a fast but sometimes inexact algorithm to round
    floating-point datatypes. For positive `decimals` it is equivalent to
    ``np.true_divide(np.rint(a * 10**decimals), 10**decimals)``, which has
    error due to the inexact representation of decimal fractions in the IEEE
    floating point standard [1]_ and errors introduced when scaling by powers
    of ten. For instance, note the extra "1" in the following:

        >>> np.round(56294995342131.5, 3)
        56294995342131.51

    If your goal is to print such values with a fixed number of decimals, it is
    preferable to use numpy's float printing routines to limit the number of
    printed decimals:

        >>> np.format_float_positional(56294995342131.5, precision=3)
        '56294995342131.5'

    The float printing routines use an accurate but much more computationally
    demanding algorithm to compute the number of digits after the decimal
    point.

    Alternatively, Python's builtin `round` function uses a more accurate
    but slower algorithm for 64-bit floating point values:

        >>> round(56294995342131.5, 3)
        56294995342131.5
        >>> np.round(16.055, 2), round(16.055, 2)  # equals 16.0549999999999997
        (16.06, 16.05)


    References
    ----------
    .. [1] "Lecture Notes on the Status of IEEE 754", William Kahan,
           https://people.eecs.berkeley.edu/~wkahan/ieee754status/IEEE754.PDF

    Examples
    --------
    >>> import numpy as np
    >>> np.round([0.37, 1.64])
    array([0., 2.])
    >>> np.round([0.37, 1.64], decimals=1)
    array([0.4, 1.6])
    >>> np.round([.5, 1.5, 2.5, 3.5, 4.5]) # rounds to nearest even value
    array([0., 2., 2., 4., 4.])
    >>> np.round([1,2,3,11], decimals=1) # ndarray of ints is returned
    array([ 1,  2,  3, 11])
    >>> np.round([1,2,3,11], decimals=-1)
    array([ 0,  0,  0, 10])

    """
    return _wrapfunc(a, 'round', decimals=decimals, out=out)


@array_function_dispatch(_round_dispatcher)
def around(a, decimals=0, out=None):
    """
    Round an array to the given number of decimals.

    `around` is an alias of `~numpy.round`.

    See Also
    --------
    ndarray.round : equivalent method
    round : alias for this function
    ceil, fix, floor, rint, trunc

    """
    return _wrapfunc(a, 'round', decimals=decimals, out=out)


def _mean_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None, *,
                     where=None):
    return (a, where, out)


@array_function_dispatch(_mean_dispatcher)
def mean(a, axis=None, dtype=None, out=None, keepdims=np._NoValue, *,
         where=np._NoValue):
    """
    Compute the arithmetic mean along the specified axis.

    Returns the average of the array elements.  The average is taken over
    the flattened array by default, otherwise over the specified axis.
    `float64` intermediate and return values are used for integer inputs.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose mean is desired. If `a` is not an
        array, a conversion is attempted.
    axis : None or int or tuple of ints, optional
        Axis or axes along which the means are computed. The default is to
        compute the mean of the flattened array.

        If this is a tuple of ints, a mean is performed over multiple axes,
        instead of a single axis or all the axes as before.
    dtype : data-type, optional
        Type to use in computing the mean.  For integer inputs, the default
        is `float64`; for floating point inputs, it is the same as the
        input dtype.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary.
        See :ref:`ufuncs-output-type` for more details.
        See :ref:`ufuncs-output-type` for more details.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `mean` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.

    where : array_like of bool, optional
        Elements to include in the mean. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.20.0

    Returns
    -------
    m : ndarray, see dtype parameter above
        If `out=None`, returns a new array containing the mean values,
        otherwise a reference to the output array is returned.

    See Also
    --------
    average : Weighted average
    std, var, nanmean, nanstd, nanvar

    Notes
    -----
    The arithmetic mean is the sum of the elements along the axis divided
    by the number of elements.

    Note that for floating-point input, the mean is computed using the
    same precision the input has.  Depending on the input data, this can
    cause the results to be inaccurate, especially for `float32` (see
    example below).  Specifying a higher-precision accumulator using the
    `dtype` keyword can alleviate this issue.

    By default, `float16` results are computed using `float32` intermediates
    for extra precision.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> np.mean(a)
    2.5
    >>> np.mean(a, axis=0)
    array([2., 3.])
    >>> np.mean(a, axis=1)
    array([1.5, 3.5])

    In single precision, `mean` can be inaccurate:

    >>> a = np.zeros((2, 512*512), dtype=np.float32)
    >>> a[0, :] = 1.0
    >>> a[1, :] = 0.1
    >>> np.mean(a)
    np.float32(0.54999924)

    Computing the mean in float64 is more accurate:

    >>> np.mean(a, dtype=np.float64)
    0.55000000074505806 # may vary

    Computing the mean in timedelta64 is available:

    >>> b = np.array([1, 3], dtype="timedelta64[D]")
    >>> np.mean(b)
    np.timedelta64(2,'D')

    Specifying a where argument:

    >>> a = np.array([[5, 9, 13], [14, 10, 12], [11, 15, 19]])
    >>> np.mean(a)
    12.0
    >>> np.mean(a, where=[[True], [False], [False]])
    9.0

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if where is not np._NoValue:
        kwargs['where'] = where
    if type(a) is not mu.ndarray:
        try:
            mean = a.mean
        except AttributeError:
            pass
        else:
            return mean(axis=axis, dtype=dtype, out=out, **kwargs)

    return _methods._mean(a, axis=axis, dtype=dtype,
                          out=out, **kwargs)


def _std_dispatcher(a, axis=None, dtype=None, out=None, ddof=None,
                    keepdims=None, *, where=None, mean=None, correction=None):
    return (a, where, out, mean)


@array_function_dispatch(_std_dispatcher)
def std(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue, *,
        where=np._NoValue, mean=np._NoValue, correction=np._NoValue):
    r"""
    Compute the standard deviation along the specified axis.

    Returns the standard deviation, a measure of the spread of a distribution,
    of the array elements. The standard deviation is computed for the
    flattened array by default, otherwise over the specified axis.

    Parameters
    ----------
    a : array_like
        Calculate the standard deviation of these values.
    axis : None or int or tuple of ints, optional
        Axis or axes along which the standard deviation is computed. The
        default is to compute the standard deviation of the flattened array.
        If this is a tuple of ints, a standard deviation is performed over
        multiple axes, instead of a single axis or all the axes as before.
    dtype : dtype, optional
        Type to use in computing the standard deviation. For arrays of
        integer type the default is float64, for arrays of float types it is
        the same as the array type.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape as the expected output but the type (of the calculated
        values) will be cast if necessary.
        See :ref:`ufuncs-output-type` for more details.
    ddof : {int, float}, optional
        Means Delta Degrees of Freedom.  The divisor used in calculations
        is ``N - ddof``, where ``N`` represents the number of elements.
        By default `ddof` is zero. See Notes for details about use of `ddof`.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `std` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.
    where : array_like of bool, optional
        Elements to include in the standard deviation.
        See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.20.0

    mean : array_like, optional
        Provide the mean to prevent its recalculation. The mean should have
        a shape as if it was calculated with ``keepdims=True``.
        The axis for the calculation of the mean should be the same as used in
        the call to this std function.

        .. versionadded:: 2.0.0

    correction : {int, float}, optional
        Array API compatible name for the ``ddof`` parameter. Only one of them
        can be provided at the same time.

        .. versionadded:: 2.0.0

    Returns
    -------
    standard_deviation : ndarray, see dtype parameter above.
        If `out` is None, return a new array containing the standard deviation,
        otherwise return a reference to the output array.

    See Also
    --------
    var, mean, nanmean, nanstd, nanvar
    :ref:`ufuncs-output-type`

    Notes
    -----
    There are several common variants of the array standard deviation
    calculation. Assuming the input `a` is a one-dimensional NumPy array
    and ``mean`` is either provided as an argument or computed as
    ``a.mean()``, NumPy computes the standard deviation of an array as::

        N = len(a)
        d2 = abs(a - mean)**2  # abs is for complex `a`
        var = d2.sum() / (N - ddof)  # note use of `ddof`
        std = var**0.5

    Different values of the argument `ddof` are useful in different
    contexts. NumPy's default ``ddof=0`` corresponds with the expression:

    .. math::

        \sqrt{\frac{\sum_i{|a_i - \bar{a}|^2 }}{N}}

    which is sometimes called the "population standard deviation" in the field
    of statistics because it applies the definition of standard deviation to
    `a` as if `a` were a complete population of possible observations.

    Many other libraries define the standard deviation of an array
    differently, e.g.:

    .. math::

        \sqrt{\frac{\sum_i{|a_i - \bar{a}|^2 }}{N - 1}}

    In statistics, the resulting quantity is sometimes called the "sample
    standard deviation" because if `a` is a random sample from a larger
    population, this calculation provides the square root of an unbiased
    estimate of the variance of the population. The use of :math:`N-1` in the
    denominator is often called "Bessel's correction" because it corrects for
    bias (toward lower values) in the variance estimate introduced when the
    sample mean of `a` is used in place of the true mean of the population.
    The resulting estimate of the standard deviation is still biased, but less
    than it would have been without the correction. For this quantity, use
    ``ddof=1``.

    Note that, for complex numbers, `std` takes the absolute
    value before squaring, so that the result is always real and nonnegative.

    For floating-point input, the standard deviation is computed using the same
    precision the input has. Depending on the input data, this can cause
    the results to be inaccurate, especially for float32 (see example below).
    Specifying a higher-accuracy accumulator using the `dtype` keyword can
    alleviate this issue.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> np.std(a)
    1.1180339887498949 # may vary
    >>> np.std(a, axis=0)
    array([1.,  1.])
    >>> np.std(a, axis=1)
    array([0.5,  0.5])

    In single precision, std() can be inaccurate:

    >>> a = np.zeros((2, 512*512), dtype=np.float32)
    >>> a[0, :] = 1.0
    >>> a[1, :] = 0.1
    >>> np.std(a)
    np.float32(0.45000005)

    Computing the standard deviation in float64 is more accurate:

    >>> np.std(a, dtype=np.float64)
    0.44999999925494177 # may vary

    Specifying a where argument:

    >>> a = np.array([[14, 8, 11, 10], [7, 9, 10, 11], [10, 15, 5, 10]])
    >>> np.std(a)
    2.614064523559687 # may vary
    >>> np.std(a, where=[[True], [True], [False]])
    2.0

    Using the mean keyword to save computation time:

    >>> import numpy as np
    >>> from timeit import timeit
    >>> a = np.array([[14, 8, 11, 10], [7, 9, 10, 11], [10, 15, 5, 10]])
    >>> mean = np.mean(a, axis=1, keepdims=True)
    >>>
    >>> g = globals()
    >>> n = 10000
    >>> t1 = timeit("std = np.std(a, axis=1, mean=mean)", globals=g, number=n)
    >>> t2 = timeit("std = np.std(a, axis=1)", globals=g, number=n)
    >>> print(f'Percentage execution time saved {100*(t2-t1)/t2:.0f}%')
    #doctest: +SKIP
    Percentage execution time saved 30%

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if where is not np._NoValue:
        kwargs['where'] = where
    if mean is not np._NoValue:
        kwargs['mean'] = mean

    if correction != np._NoValue:
        if ddof != 0:
            raise ValueError(
                "ddof and correction can't be provided simultaneously."
            )
        else:
            ddof = correction

    if type(a) is not mu.ndarray:
        try:
            std = a.std
        except AttributeError:
            pass
        else:
            return std(axis=axis, dtype=dtype, out=out, ddof=ddof, **kwargs)

    return _methods._std(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
                         **kwargs)


def _var_dispatcher(a, axis=None, dtype=None, out=None, ddof=None,
                    keepdims=None, *, where=None, mean=None, correction=None):
    return (a, where, out, mean)


@array_function_dispatch(_var_dispatcher)
def var(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue, *,
        where=np._NoValue, mean=np._NoValue, correction=np._NoValue):
    r"""
    Compute the variance along the specified axis.

    Returns the variance of the array elements, a measure of the spread of a
    distribution.  The variance is computed for the flattened array by
    default, otherwise over the specified axis.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose variance is desired.  If `a` is not an
        array, a conversion is attempted.
    axis : None or int or tuple of ints, optional
        Axis or axes along which the variance is computed.  The default is to
        compute the variance of the flattened array.
        If this is a tuple of ints, a variance is performed over multiple axes,
        instead of a single axis or all the axes as before.
    dtype : data-type, optional
        Type to use in computing the variance.  For arrays of integer type
        the default is `float64`; for arrays of float types it is the same as
        the array type.
    out : ndarray, optional
        Alternate output array in which to place the result.  It must have
        the same shape as the expected output, but the type is cast if
        necessary.
    ddof : {int, float}, optional
        "Delta Degrees of Freedom": the divisor used in the calculation is
        ``N - ddof``, where ``N`` represents the number of elements. By
        default `ddof` is zero. See notes for details about use of `ddof`.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

        If the default value is passed, then `keepdims` will not be
        passed through to the `var` method of sub-classes of
        `ndarray`, however any non-default value will be.  If the
        sub-class' method does not implement `keepdims` any
        exceptions will be raised.
    where : array_like of bool, optional
        Elements to include in the variance. See `~numpy.ufunc.reduce` for
        details.

        .. versionadded:: 1.20.0

    mean : array like, optional
        Provide the mean to prevent its recalculation. The mean should have
        a shape as if it was calculated with ``keepdims=True``.
        The axis for the calculation of the mean should be the same as used in
        the call to this var function.

        .. versionadded:: 2.0.0

    correction : {int, float}, optional
        Array API compatible name for the ``ddof`` parameter. Only one of them
        can be provided at the same time.

        .. versionadded:: 2.0.0

    Returns
    -------
    variance : ndarray, see dtype parameter above
        If ``out=None``, returns a new array containing the variance;
        otherwise, a reference to the output array is returned.

    See Also
    --------
    std, mean, nanmean, nanstd, nanvar
    :ref:`ufuncs-output-type`

    Notes
    -----
    There are several common variants of the array variance calculation.
    Assuming the input `a` is a one-dimensional NumPy array and ``mean`` is
    either provided as an argument or computed as ``a.mean()``, NumPy
    computes the variance of an array as::

        N = len(a)
        d2 = abs(a - mean)**2  # abs is for complex `a`
        var = d2.sum() / (N - ddof)  # note use of `ddof`

    Different values of the argument `ddof` are useful in different
    contexts. NumPy's default ``ddof=0`` corresponds with the expression:

    .. math::

        \frac{\sum_i{|a_i - \bar{a}|^2 }}{N}

    which is sometimes called the "population variance" in the field of
    statistics because it applies the definition of variance to `a` as if `a`
    were a complete population of possible observations.

    Many other libraries define the variance of an array differently, e.g.:

    .. math::

        \frac{\sum_i{|a_i - \bar{a}|^2}}{N - 1}

    In statistics, the resulting quantity is sometimes called the "sample
    variance" because if `a` is a random sample from a larger population,
    this calculation provides an unbiased estimate of the variance of the
    population.  The use of :math:`N-1` in the denominator is often called
    "Bessel's correction" because it corrects for bias (toward lower values)
    in the variance estimate introduced when the sample mean of `a` is used
    in place of the true mean of the population. For this quantity, use
    ``ddof=1``.

    Note that for complex numbers, the absolute value is taken before
    squaring, so that the result is always real and nonnegative.

    For floating-point input, the variance is computed using the same
    precision the input has.  Depending on the input data, this can cause
    the results to be inaccurate, especially for `float32` (see example
    below).  Specifying a higher-accuracy accumulator using the ``dtype``
    keyword can alleviate this issue.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> np.var(a)
    1.25
    >>> np.var(a, axis=0)
    array([1.,  1.])
    >>> np.var(a, axis=1)
    array([0.25,  0.25])

    In single precision, var() can be inaccurate:

    >>> a = np.zeros((2, 512*512), dtype=np.float32)
    >>> a[0, :] = 1.0
    >>> a[1, :] = 0.1
    >>> np.var(a)
    np.float32(0.20250003)

    Computing the variance in float64 is more accurate:

    >>> np.var(a, dtype=np.float64)
    0.20249999932944759 # may vary
    >>> ((1-0.55)**2 + (0.1-0.55)**2)/2
    0.2025

    Specifying a where argument:

    >>> a = np.array([[14, 8, 11, 10], [7, 9, 10, 11], [10, 15, 5, 10]])
    >>> np.var(a)
    6.833333333333333 # may vary
    >>> np.var(a, where=[[True], [True], [False]])
    4.0

    Using the mean keyword to save computation time:

    >>> import numpy as np
    >>> from timeit import timeit
    >>>
    >>> a = np.array([[14, 8, 11, 10], [7, 9, 10, 11], [10, 15, 5, 10]])
    >>> mean = np.mean(a, axis=1, keepdims=True)
    >>>
    >>> g = globals()
    >>> n = 10000
    >>> t1 = timeit("var = np.var(a, axis=1, mean=mean)", globals=g, number=n)
    >>> t2 = timeit("var = np.var(a, axis=1)", globals=g, number=n)
    >>> print(f'Percentage execution time saved {100*(t2-t1)/t2:.0f}%')
    #doctest: +SKIP
    Percentage execution time saved 32%

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if where is not np._NoValue:
        kwargs['where'] = where
    if mean is not np._NoValue:
        kwargs['mean'] = mean

    if correction != np._NoValue:
        if ddof != 0:
            raise ValueError(
                "ddof and correction can't be provided simultaneously."
            )
        else:
            ddof = correction

    if type(a) is not mu.ndarray:
        try:
            var = a.var

        except AttributeError:
            pass
        else:
            return var(axis=axis, dtype=dtype, out=out, ddof=ddof, **kwargs)

    return _methods._var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
                         **kwargs)

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\litellm_logging.py ===
# What is this?
## Common Utility file for Logging handler
# Logging function -> log the exact model details + what's being sent | Non-Blocking
import copy
import datetime
import json
import os
import re
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime as dt_object
from functools import lru_cache
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic import BaseModel

import litellm
from litellm import (
    _custom_logger_compatible_callbacks_literal,
    json_logs,
    log_raw_request_response,
    turn_off_message_logging,
)
from litellm._logging import _is_debugging_on, verbose_logger
from litellm.batches.batch_utils import _handle_completed_batch
from litellm.caching.caching import DualCache, InMemoryCache
from litellm.caching.caching_handler import LLMCachingHandler
from litellm.constants import (
    DEFAULT_MOCK_RESPONSE_COMPLETION_TOKEN_COUNT,
    DEFAULT_MOCK_RESPONSE_PROMPT_TOKEN_COUNT,
)
from litellm.cost_calculator import (
    RealtimeAPITokenUsageProcessor,
    _select_model_name_for_cost_calc,
)
from litellm.integrations.agentops import AgentOps
from litellm.integrations.anthropic_cache_control_hook import AnthropicCacheControlHook
from litellm.integrations.arize.arize import ArizeLogger
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.integrations.custom_logger import CustomLogger
from litellm.integrations.deepeval.deepeval import DeepEvalLogger
from litellm.integrations.mlflow import MlflowLogger
from litellm.integrations.vector_stores.bedrock_vector_store import BedrockVectorStore
from litellm.litellm_core_utils.get_litellm_params import get_litellm_params
from litellm.litellm_core_utils.llm_cost_calc.tool_call_cost_tracking import (
    StandardBuiltInToolCostTracking,
)
from litellm.litellm_core_utils.model_param_helper import ModelParamHelper
from litellm.litellm_core_utils.redact_messages import (
    redact_message_input_output_from_custom_logger,
    redact_message_input_output_from_logging,
)
from litellm.responses.utils import ResponseAPILoggingUtils
from litellm.types.llms.openai import (
    AllMessageValues,
    Batch,
    FineTuningJob,
    HttpxBinaryResponseContent,
    OpenAIFileObject,
    OpenAIModerationResponse,
    ResponseCompletedEvent,
    ResponsesAPIResponse,
)
from litellm.types.rerank import RerankResponse
from litellm.types.router import CustomPricingLiteLLMParams
from litellm.types.utils import (
    CallTypes,
    DynamicPromptManagementParamLiteral,
    EmbeddingResponse,
    ImageResponse,
    LiteLLMBatch,
    LiteLLMLoggingBaseClass,
    LiteLLMRealtimeStreamLoggingObject,
    ModelResponse,
    ModelResponseStream,
    RawRequestTypedDict,
    StandardBuiltInToolsParams,
    StandardCallbackDynamicParams,
    StandardLoggingAdditionalHeaders,
    StandardLoggingHiddenParams,
    StandardLoggingMCPToolCall,
    StandardLoggingMetadata,
    StandardLoggingModelCostFailureDebugInformation,
    StandardLoggingModelInformation,
    StandardLoggingPayload,
    StandardLoggingPayloadErrorInformation,
    StandardLoggingPayloadStatus,
    StandardLoggingPromptManagementMetadata,
    StandardLoggingVectorStoreRequest,
    TextCompletionResponse,
    TranscriptionResponse,
    Usage,
)
from litellm.utils import _get_base_model_from_metadata, executor, print_verbose

from ..integrations.argilla import ArgillaLogger
from ..integrations.arize.arize_phoenix import ArizePhoenixLogger
from ..integrations.athina import AthinaLogger
from ..integrations.azure_storage.azure_storage import AzureBlobStorageLogger
from ..integrations.braintrust_logging import BraintrustLogger
from ..integrations.custom_prompt_management import CustomPromptManagement
from ..integrations.datadog.datadog import DataDogLogger
from ..integrations.datadog.datadog_llm_obs import DataDogLLMObsLogger
from ..integrations.dynamodb import DyanmoDBLogger
from ..integrations.galileo import GalileoObserve
from ..integrations.gcs_bucket.gcs_bucket import GCSBucketLogger
from ..integrations.gcs_pubsub.pub_sub import GcsPubSubLogger
from ..integrations.greenscale import GreenscaleLogger
from ..integrations.helicone import HeliconeLogger
from ..integrations.humanloop import HumanloopLogger
from ..integrations.lago import LagoLogger
from ..integrations.langfuse.langfuse import LangFuseLogger
from ..integrations.langfuse.langfuse_handler import LangFuseHandler
from ..integrations.langfuse.langfuse_otel import LangfuseOtelLogger
from ..integrations.langfuse.langfuse_prompt_management import LangfusePromptManagement
from ..integrations.langsmith import LangsmithLogger
from ..integrations.literal_ai import LiteralAILogger
from ..integrations.logfire_logger import LogfireLevel, LogfireLogger
from ..integrations.lunary import LunaryLogger
from ..integrations.openmeter import OpenMeterLogger
from ..integrations.opik.opik import OpikLogger
from ..integrations.prometheus import PrometheusLogger
from ..integrations.prompt_layer import PromptLayerLogger
from ..integrations.s3 import S3Logger
from ..integrations.s3_v2 import S3Logger as S3V2Logger
from ..integrations.supabase import Supabase
from ..integrations.traceloop import TraceloopLogger
from ..integrations.weights_biases import WeightsBiasesLogger
from .exception_mapping_utils import _get_response_headers
from .initialize_dynamic_callback_params import (
    initialize_standard_callback_dynamic_params as _initialize_standard_callback_dynamic_params,
)
from .specialty_caches.dynamic_logging_cache import DynamicLoggingCache

try:
    from litellm_enterprise.enterprise_callbacks.generic_api_callback import (
        GenericAPILogger,
    )
    from litellm_enterprise.enterprise_callbacks.pagerduty.pagerduty import (
        PagerDutyAlerting,
    )
    from litellm_enterprise.enterprise_callbacks.send_emails.resend_email import (
        ResendEmailLogger,
    )
    from litellm_enterprise.enterprise_callbacks.send_emails.smtp_email import (
        SMTPEmailLogger,
    )
    from litellm_enterprise.litellm_core_utils.litellm_logging import (
        StandardLoggingPayloadSetup as EnterpriseStandardLoggingPayloadSetup,
    )

    EnterpriseStandardLoggingPayloadSetupVAR: Optional[
        Type[EnterpriseStandardLoggingPayloadSetup]
    ] = EnterpriseStandardLoggingPayloadSetup
except Exception as e:
    verbose_logger.debug(
        f"[Non-Blocking] Unable to import GenericAPILogger - LiteLLM Enterprise Feature - {str(e)}"
    )
    GenericAPILogger = CustomLogger  # type: ignore
    ResendEmailLogger = CustomLogger  # type: ignore
    SMTPEmailLogger = CustomLogger  # type: ignore
    PagerDutyAlerting = CustomLogger  # type: ignore
    EnterpriseStandardLoggingPayloadSetupVAR = None
_in_memory_loggers: List[Any] = []

### GLOBAL VARIABLES ###

sentry_sdk_instance = None
capture_exception = None
add_breadcrumb = None
posthog = None
slack_app = None
alerts_channel = None
heliconeLogger = None
athinaLogger = None
promptLayerLogger = None
logfireLogger = None
weightsBiasesLogger = None
customLogger = None
langFuseLogger = None
openMeterLogger = None
lagoLogger = None
dataDogLogger = None
prometheusLogger = None
dynamoLogger = None
s3Logger = None
greenscaleLogger = None
lunaryLogger = None
supabaseClient = None
deepevalLogger = None
callback_list: Optional[List[str]] = []
user_logger_fn = None
additional_details: Optional[Dict[str, str]] = {}
local_cache: Optional[Dict[str, str]] = {}
last_fetched_at = None
last_fetched_at_keys = None


####
class ServiceTraceIDCache:
    def __init__(self) -> None:
        self.cache = InMemoryCache()

    def get_cache(self, litellm_call_id: str, service_name: str) -> Optional[str]:
        key_name = "{}:{}".format(service_name, litellm_call_id)
        response = self.cache.get_cache(key=key_name)
        return response

    def set_cache(self, litellm_call_id: str, service_name: str, trace_id: str) -> None:
        key_name = "{}:{}".format(service_name, litellm_call_id)
        self.cache.set_cache(key=key_name, value=trace_id)
        return None


in_memory_trace_id_cache = ServiceTraceIDCache()
in_memory_dynamic_logger_cache = DynamicLoggingCache()


class Logging(LiteLLMLoggingBaseClass):
    global supabaseClient, promptLayerLogger, weightsBiasesLogger, logfireLogger, capture_exception, add_breadcrumb, lunaryLogger, logfireLogger, prometheusLogger, slack_app
    custom_pricing: bool = False
    stream_options = None

    def __init__(
        self,
        model: str,
        messages,
        stream,
        call_type,
        start_time,
        litellm_call_id: str,
        function_id: str,
        litellm_trace_id: Optional[str] = None,
        dynamic_input_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None,
        dynamic_success_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None,
        dynamic_async_success_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None,
        dynamic_failure_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None,
        dynamic_async_failure_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None,
        applied_guardrails: Optional[List[str]] = None,
        kwargs: Optional[Dict] = None,
        log_raw_request_response: bool = False,
    ):
        _input: Optional[str] = messages  # save original value of messages
        if messages is not None:
            if isinstance(messages, str):
                messages = [
                    {"role": "user", "content": messages}
                ]  # convert text completion input to the chat completion format
            elif (
                isinstance(messages, list)
                and len(messages) > 0
                and isinstance(messages[0], str)
            ):
                new_messages = []
                for m in messages:
                    new_messages.append({"role": "user", "content": m})
                messages = new_messages
        self.model = model
        self.messages = copy.deepcopy(messages)
        self.stream = stream
        self.start_time = start_time  # log the call start time
        self.call_type = call_type
        self.litellm_call_id = litellm_call_id
        self.litellm_trace_id: str = litellm_trace_id or str(uuid.uuid4())
        self.function_id = function_id
        self.streaming_chunks: List[Any] = []  # for generating complete stream response
        self.sync_streaming_chunks: List[Any] = (
            []
        )  # for generating complete stream response
        self.log_raw_request_response = log_raw_request_response

        # Initialize dynamic callbacks
        self.dynamic_input_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = dynamic_input_callbacks
        self.dynamic_success_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = dynamic_success_callbacks
        self.dynamic_async_success_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = dynamic_async_success_callbacks
        self.dynamic_failure_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = dynamic_failure_callbacks
        self.dynamic_async_failure_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = dynamic_async_failure_callbacks

        # Process dynamic callbacks
        self.process_dynamic_callbacks()

        ## DYNAMIC LANGFUSE / GCS / logging callback KEYS ##
        self.standard_callback_dynamic_params: StandardCallbackDynamicParams = (
            self.initialize_standard_callback_dynamic_params(kwargs)
        )
        self.standard_built_in_tools_params: StandardBuiltInToolsParams = (
            self.initialize_standard_built_in_tools_params(kwargs)
        )
        ## TIME TO FIRST TOKEN LOGGING ##
        self.completion_start_time: Optional[datetime.datetime] = None
        self._llm_caching_handler: Optional[LLMCachingHandler] = None

        # INITIAL LITELLM_PARAMS
        litellm_params = {}
        if kwargs is not None:
            litellm_params = get_litellm_params(**kwargs)
            litellm_params = scrub_sensitive_keys_in_metadata(litellm_params)

        self.litellm_params = litellm_params

        self.model_call_details: Dict[str, Any] = {
            "litellm_trace_id": litellm_trace_id,
            "litellm_call_id": litellm_call_id,
            "input": _input,
            "litellm_params": litellm_params,
            "applied_guardrails": applied_guardrails,
            "model": model,
        }

    def process_dynamic_callbacks(self):
        """
        Initializes CustomLogger compatible callbacks in self.dynamic_* callbacks

        If a callback is in litellm._known_custom_logger_compatible_callbacks, it needs to be intialized and added to the respective dynamic_* callback list.
        """
        # Process input callbacks
        self.dynamic_input_callbacks = self._process_dynamic_callback_list(
            self.dynamic_input_callbacks, dynamic_callbacks_type="input"
        )

        # Process failure callbacks
        self.dynamic_failure_callbacks = self._process_dynamic_callback_list(
            self.dynamic_failure_callbacks, dynamic_callbacks_type="failure"
        )

        # Process async failure callbacks
        self.dynamic_async_failure_callbacks = self._process_dynamic_callback_list(
            self.dynamic_async_failure_callbacks, dynamic_callbacks_type="async_failure"
        )

        # Process success callbacks
        self.dynamic_success_callbacks = self._process_dynamic_callback_list(
            self.dynamic_success_callbacks, dynamic_callbacks_type="success"
        )

        # Process async success callbacks
        self.dynamic_async_success_callbacks = self._process_dynamic_callback_list(
            self.dynamic_async_success_callbacks, dynamic_callbacks_type="async_success"
        )

    def _process_dynamic_callback_list(
        self,
        callback_list: Optional[List[Union[str, Callable, CustomLogger]]],
        dynamic_callbacks_type: Literal[
            "input", "success", "failure", "async_success", "async_failure"
        ],
    ) -> Optional[List[Union[str, Callable, CustomLogger]]]:
        """
        Helper function to initialize CustomLogger compatible callbacks in self.dynamic_* callbacks

        - If a callback is in litellm._known_custom_logger_compatible_callbacks,
        replace the string with the initialized callback class.
        - If dynamic callback is a "success" callback that is a known_custom_logger_compatible_callbacks then add it to dynamic_async_success_callbacks
        - If dynamic callback is a "failure" callback that is a known_custom_logger_compatible_callbacks then add it to dynamic_failure_callbacks
        """
        if callback_list is None:
            return None

        processed_list: List[Union[str, Callable, CustomLogger]] = []
        for callback in callback_list:
            if (
                isinstance(callback, str)
                and callback in litellm._known_custom_logger_compatible_callbacks
            ):
                callback_class = _init_custom_logger_compatible_class(
                    callback, internal_usage_cache=None, llm_router=None  # type: ignore
                )
                if callback_class is not None:
                    processed_list.append(callback_class)

                    # If processing dynamic_success_callbacks, add to dynamic_async_success_callbacks
                    if dynamic_callbacks_type == "success":
                        if self.dynamic_async_success_callbacks is None:
                            self.dynamic_async_success_callbacks = []
                        self.dynamic_async_success_callbacks.append(callback_class)
                    elif dynamic_callbacks_type == "failure":
                        if self.dynamic_async_failure_callbacks is None:
                            self.dynamic_async_failure_callbacks = []
                        self.dynamic_async_failure_callbacks.append(callback_class)
            else:
                processed_list.append(callback)
        return processed_list

    def initialize_standard_callback_dynamic_params(
        self, kwargs: Optional[Dict] = None
    ) -> StandardCallbackDynamicParams:
        """
        Initialize the standard callback dynamic params from the kwargs

        checks if langfuse_secret_key, gcs_bucket_name in kwargs and sets the corresponding attributes in StandardCallbackDynamicParams
        """
        return _initialize_standard_callback_dynamic_params(kwargs)

    def initialize_standard_built_in_tools_params(
        self, kwargs: Optional[Dict] = None
    ) -> StandardBuiltInToolsParams:
        """
        Initialize the standard built-in tools params from the kwargs

        checks if web_search_options in kwargs or tools and sets the corresponding attribute in StandardBuiltInToolsParams
        """
        return StandardBuiltInToolsParams(
            web_search_options=StandardBuiltInToolCostTracking._get_web_search_options(
                kwargs or {}
            ),
            file_search=StandardBuiltInToolCostTracking._get_file_search_tool_call(
                kwargs or {}
            ),
        )

    def update_environment_variables(
        self,
        litellm_params: Dict,
        optional_params: Dict,
        model: Optional[str] = None,
        user: Optional[str] = None,
        **additional_params,
    ):
        self.optional_params = optional_params
        if model is not None:
            self.model = model
        self.user = user
        self.litellm_params = {
            **self.litellm_params,
            **scrub_sensitive_keys_in_metadata(litellm_params),
        }
        self.logger_fn = litellm_params.get("logger_fn", None)
        verbose_logger.debug(f"self.optional_params: {self.optional_params}")

        self.model_call_details.update(
            {
                "model": self.model,
                "messages": self.messages,
                "optional_params": self.optional_params,
                "litellm_params": self.litellm_params,
                "start_time": self.start_time,
                "stream": self.stream,
                "user": user,
                "call_type": str(self.call_type),
                "litellm_call_id": self.litellm_call_id,
                "completion_start_time": self.completion_start_time,
                "standard_callback_dynamic_params": self.standard_callback_dynamic_params,
                **self.optional_params,
                **additional_params,
            }
        )

        ## check if stream options is set ##  - used by CustomStreamWrapper for easy instrumentation
        if "stream_options" in additional_params:
            self.stream_options = additional_params["stream_options"]
        ## check if custom pricing set ##
        custom_pricing_keys = CustomPricingLiteLLMParams.model_fields.keys()
        for key in custom_pricing_keys:
            if litellm_params.get(key) is not None:
                self.custom_pricing = True

        if "custom_llm_provider" in self.model_call_details:
            self.custom_llm_provider = self.model_call_details["custom_llm_provider"]

    def should_run_prompt_management_hooks(
        self,
        non_default_params: Dict,
        prompt_id: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Return True if prompt management hooks should be run
        """
        if prompt_id:
            return True

        if self._should_run_prompt_management_hooks_without_prompt_id(
            non_default_params=non_default_params,
            tools=tools,
        ):
            return True

        return False

    def _should_run_prompt_management_hooks_without_prompt_id(
        self,
        non_default_params: Dict,
        tools: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Certain prompt management hooks don't need a `prompt_id` to be passed in, they are triggered by dynamic params

        eg. AnthropicCacheControlHook and BedrockKnowledgeBaseHook both don't require a `prompt_id` to be passed in, they are triggered by dynamic params
        """
        for param in non_default_params:
            if param in DynamicPromptManagementParamLiteral.list_all_params():
                return True

        #############################################################################
        # Check if Vector Store / Knowledge Base hooks should be applied to the prompt
        #############################################################################
        if litellm.vector_store_registry is not None:
            if litellm.vector_store_registry.get_vector_store_to_run(
                non_default_params=non_default_params, tools=tools
            ):
                return True
        return False

    def get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: Dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        prompt_management_logger: Optional[CustomLogger] = None,
        prompt_label: Optional[str] = None,
    ) -> Tuple[str, List[AllMessageValues], dict]:
        custom_logger = (
            prompt_management_logger
            or self.get_custom_logger_for_prompt_management(
                model=model, non_default_params=non_default_params
            )
        )

        if custom_logger:
            (
                model,
                messages,
                non_default_params,
            ) = custom_logger.get_chat_completion_prompt(
                model=model,
                messages=messages,
                non_default_params=non_default_params or {},
                prompt_id=prompt_id,
                prompt_variables=prompt_variables,
                dynamic_callback_params=self.standard_callback_dynamic_params,
                prompt_label=prompt_label,
            )
        self.messages = messages
        return model, messages, non_default_params

    async def async_get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: Dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        prompt_management_logger: Optional[CustomLogger] = None,
        tools: Optional[List[Dict]] = None,
        prompt_label: Optional[str] = None,
    ) -> Tuple[str, List[AllMessageValues], dict]:
        custom_logger = (
            prompt_management_logger
            or self.get_custom_logger_for_prompt_management(
                model=model, non_default_params=non_default_params
            )
        )

        if custom_logger:
            (
                model,
                messages,
                non_default_params,
            ) = await custom_logger.async_get_chat_completion_prompt(
                model=model,
                messages=messages,
                non_default_params=non_default_params or {},
                prompt_id=prompt_id,
                prompt_variables=prompt_variables,
                dynamic_callback_params=self.standard_callback_dynamic_params,
                litellm_logging_obj=self,
                tools=tools,
                prompt_label=prompt_label,
            )
        self.messages = messages
        return model, messages, non_default_params

    def get_custom_logger_for_prompt_management(
        self, model: str, non_default_params: Dict
    ) -> Optional[CustomLogger]:
        """
        Get a custom logger for prompt management based on model name or available callbacks.

        Args:
            model: The model name to check for prompt management integration

        Returns:
            A CustomLogger instance if one is found, None otherwise
        """
        # First check if model starts with a known custom logger compatible callback
        for callback_name in litellm._known_custom_logger_compatible_callbacks:
            if model.startswith(callback_name):
                custom_logger = _init_custom_logger_compatible_class(
                    logging_integration=callback_name,
                    internal_usage_cache=None,
                    llm_router=None,
                )
                if custom_logger is not None:
                    self.model_call_details["prompt_integration"] = model.split("/")[0]
                    return custom_logger

        # Then check for any registered CustomPromptManagement loggers
        prompt_management_loggers = (
            litellm.logging_callback_manager.get_custom_loggers_for_type(
                callback_type=CustomPromptManagement
            )
        )

        if prompt_management_loggers:
            logger = prompt_management_loggers[0]
            self.model_call_details["prompt_integration"] = logger.__class__.__name__
            return logger

        if anthropic_cache_control_logger := AnthropicCacheControlHook.get_custom_logger_for_anthropic_cache_control_hook(
            non_default_params
        ):
            self.model_call_details["prompt_integration"] = (
                anthropic_cache_control_logger.__class__.__name__
            )
            return anthropic_cache_control_logger

        #########################################################
        # Vector Store / Knowledge Base hooks
        #########################################################
        if litellm.vector_store_registry is not None:
            if vector_store_to_run := litellm.vector_store_registry.get_vector_store_to_run(
                non_default_params=non_default_params
            ):
                vector_store_custom_logger = (
                    litellm.ProviderConfigManager.get_provider_vector_store_config(
                        provider=cast(
                            litellm.LlmProviders,
                            vector_store_to_run.get("custom_llm_provider"),
                        ),
                    )
                )
                self.model_call_details["prompt_integration"] = (
                    vector_store_custom_logger.__class__.__name__
                )
                return vector_store_custom_logger

        return None

    def get_custom_logger_for_anthropic_cache_control_hook(
        self, non_default_params: Dict
    ) -> Optional[CustomLogger]:
        if non_default_params.get("cache_control_injection_points", None):
            custom_logger = _init_custom_logger_compatible_class(
                logging_integration="anthropic_cache_control_hook",
                internal_usage_cache=None,
                llm_router=None,
            )
            return custom_logger
        return None

    def _get_raw_request_body(self, data: Optional[Union[dict, str]]) -> dict:
        if data is None:
            return {"error": "Received empty dictionary for raw request body"}
        if isinstance(data, str):
            try:
                return json.loads(data)
            except Exception:
                return {
                    "error": "Unable to parse raw request body. Got - {}".format(data)
                }
        return data

    def _get_masked_api_base(self, api_base: str) -> str:
        if "key=" in api_base:
            # Find the position of "key=" in the string
            key_index = api_base.find("key=") + 4
            # Mask the last 5 characters after "key="
            masked_api_base = api_base[:key_index] + "*" * 5 + api_base[-4:]
        else:
            masked_api_base = api_base
        return str(masked_api_base)

    def _pre_call(self, input, api_key, model=None, additional_args={}):
        """
        Common helper function across the sync + async pre-call function
        """

        self.model_call_details["input"] = input
        self.model_call_details["api_key"] = api_key
        self.model_call_details["additional_args"] = additional_args
        self.model_call_details["log_event_type"] = "pre_api_call"
        if (
            model
        ):  # if model name was changes pre-call, overwrite the initial model call name with the new one
            self.model_call_details["model"] = model
        self.model_call_details["litellm_params"]["api_base"] = (
            self._get_masked_api_base(additional_args.get("api_base", ""))
        )

    def pre_call(self, input, api_key, model=None, additional_args={}):  # noqa: PLR0915
        # Log the exact input to the LLM API
        litellm.error_logs["PRE_CALL"] = locals()
        try:
            self._pre_call(
                input=input,
                api_key=api_key,
                model=model,
                additional_args=additional_args,
            )

            # User Logging -> if you pass in a custom logging function
            self._print_llm_call_debugging_log(
                api_base=additional_args.get("api_base", ""),
                headers=additional_args.get("headers", {}),
                additional_args=additional_args,
            )
            # log raw request to provider (like LangFuse) -- if opted in.
            if (
                self.log_raw_request_response is True
                or log_raw_request_response is True
            ):
                _litellm_params = self.model_call_details.get("litellm_params", {})
                _metadata = _litellm_params.get("metadata", {}) or {}
                try:
                    # [Non-blocking Extra Debug Information in metadata]
                    if turn_off_message_logging is True:
                        _metadata["raw_request"] = (
                            "redacted by litellm. \
                            'litellm.turn_off_message_logging=True'"
                        )
                    else:
                        curl_command = self._get_request_curl_command(
                            api_base=additional_args.get("api_base", ""),
                            headers=additional_args.get("headers", {}),
                            additional_args=additional_args,
                            data=additional_args.get("complete_input_dict", {}),
                        )

                        _metadata["raw_request"] = str(curl_command)
                        # split up, so it's easier to parse in the UI
                        self.model_call_details["raw_request_typed_dict"] = (
                            RawRequestTypedDict(
                                raw_request_api_base=str(
                                    additional_args.get("api_base") or ""
                                ),
                                raw_request_body=self._get_raw_request_body(
                                    additional_args.get("complete_input_dict", {})
                                ),
                                raw_request_headers=self._get_masked_headers(
                                    additional_args.get("headers", {}) or {},
                                    ignore_sensitive_headers=True,
                                ),
                                error=None,
                            )
                        )
                except Exception as e:
                    self.model_call_details["raw_request_typed_dict"] = (
                        RawRequestTypedDict(
                            error=str(e),
                        )
                    )
                    _metadata["raw_request"] = (
                        "Unable to Log \
                        raw request: {}".format(
                            str(e)
                        )
                    )
            if self.logger_fn and callable(self.logger_fn):
                try:
                    self.logger_fn(
                        self.model_call_details
                    )  # Expectation: any logger function passed in by the user should accept a dict object
                except Exception as e:
                    verbose_logger.exception(
                        "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while logging {}".format(
                            str(e)
                        )
                    )

            self.model_call_details["api_call_start_time"] = datetime.datetime.now()
            # Input Integration Logging -> If you want to log the fact that an attempt to call the model was made
            callbacks = litellm.input_callback + (self.dynamic_input_callbacks or [])
            for callback in callbacks:
                try:
                    if callback == "supabase" and supabaseClient is not None:
                        verbose_logger.debug("reaches supabase for logging!")
                        model = self.model_call_details["model"]
                        messages = self.model_call_details["input"]
                        verbose_logger.debug(f"supabaseClient: {supabaseClient}")
                        supabaseClient.input_log_event(
                            model=model,
                            messages=messages,
                            end_user=self.model_call_details.get("user", "default"),
                            litellm_call_id=self.litellm_params["litellm_call_id"],
                            print_verbose=print_verbose,
                        )
                    elif callback == "sentry" and add_breadcrumb:
                        try:
                            details_to_log = copy.deepcopy(self.model_call_details)
                        except Exception:
                            details_to_log = self.model_call_details
                        if litellm.turn_off_message_logging:
                            # make a copy of the _model_Call_details and log it
                            details_to_log.pop("messages", None)
                            details_to_log.pop("input", None)
                            details_to_log.pop("prompt", None)

                        add_breadcrumb(
                            category="litellm.llm_call",
                            message=f"Model Call Details pre-call: {details_to_log}",
                            level="info",
                        )

                    elif isinstance(callback, CustomLogger):  # custom logger class
                        callback.log_pre_api_call(
                            model=self.model,
                            messages=self.messages,
                            kwargs=self.model_call_details,
                        )
                    elif (
                        callable(callback) and customLogger is not None
                    ):  # custom logger functions
                        customLogger.log_input_event(
                            model=self.model,
                            messages=self.messages,
                            kwargs=self.model_call_details,
                            print_verbose=print_verbose,
                            callback_func=callback,
                        )
                except Exception as e:
                    verbose_logger.exception(
                        "litellm.Logging.pre_call(): Exception occured - {}".format(
                            str(e)
                        )
                    )
                    verbose_logger.debug(
                        f"LiteLLM.Logging: is sentry capture exception initialized {capture_exception}"
                    )
                    if capture_exception:  # log this error to sentry for debugging
                        capture_exception(e)
        except Exception as e:
            verbose_logger.exception(
                "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while logging {}".format(
                    str(e)
                )
            )
            verbose_logger.error(
                f"LiteLLM.Logging: is sentry capture exception initialized {capture_exception}"
            )
            if capture_exception:  # log this error to sentry for debugging
                capture_exception(e)

    def _print_llm_call_debugging_log(
        self,
        api_base: str,
        headers: dict,
        additional_args: dict,
    ):
        """
        Internal debugging helper function

        Prints the RAW curl command sent from LiteLLM
        """
        if _is_debugging_on():
            if json_logs:
                masked_headers = self._get_masked_headers(headers)
                verbose_logger.debug(
                    "POST Request Sent from LiteLLM",
                    extra={"api_base": {api_base}, **masked_headers},
                )
            else:
                headers = additional_args.get("headers", {})
                if headers is None:
                    headers = {}
                data = additional_args.get("complete_input_dict", {})
                api_base = str(additional_args.get("api_base", ""))
                curl_command = self._get_request_curl_command(
                    api_base=api_base,
                    headers=headers,
                    additional_args=additional_args,
                    data=data,
                )
                verbose_logger.debug(f"\033[92m{curl_command}\033[0m\n")

    def _get_request_body(self, data: dict) -> str:
        return str(data)

    def _get_request_curl_command(
        self, api_base: str, headers: Optional[dict], additional_args: dict, data: dict
    ) -> str:
        masked_api_base = self._get_masked_api_base(api_base)
        if headers is None:
            headers = {}
        curl_command = "\n\nPOST Request Sent from LiteLLM:\n"
        curl_command += "curl -X POST \\\n"
        curl_command += f"{masked_api_base} \\\n"
        masked_headers = self._get_masked_headers(headers)
        formatted_headers = " ".join(
            [f"-H '{k}: {v}'" for k, v in masked_headers.items()]
        )
        curl_command += (
            f"{formatted_headers} \\\n" if formatted_headers.strip() != "" else ""
        )
        curl_command += f"-d '{self._get_request_body(data)}'\n"
        if additional_args.get("request_str", None) is not None:
            # print the sagemaker / bedrock client request
            curl_command = "\nRequest Sent from LiteLLM:\n"
            curl_command += additional_args.get("request_str", None)
        elif api_base == "":
            curl_command = str(self.model_call_details)
        return curl_command

    def _get_masked_headers(
        self, headers: dict, ignore_sensitive_headers: bool = False
    ) -> dict:
        """
        Internal debugging helper function

        Masks the headers of the request sent from LiteLLM
        """
        return _get_masked_values(
            headers, ignore_sensitive_values=ignore_sensitive_headers
        )

    def post_call(
        self, original_response, input=None, api_key=None, additional_args={}
    ):
        # Log the exact result from the LLM API, for streaming - log the type of response received
        litellm.error_logs["POST_CALL"] = locals()
        if isinstance(original_response, dict):
            original_response = json.dumps(original_response)
        try:
            self.model_call_details["input"] = input
            self.model_call_details["api_key"] = api_key
            self.model_call_details["original_response"] = original_response
            self.model_call_details["additional_args"] = additional_args
            self.model_call_details["log_event_type"] = "post_api_call"

            if json_logs:
                verbose_logger.debug(
                    "RAW RESPONSE:\n{}\n\n".format(
                        self.model_call_details.get(
                            "original_response", self.model_call_details
                        )
                    ),
                )
            else:
                print_verbose(
                    "RAW RESPONSE:\n{}\n\n".format(
                        self.model_call_details.get(
                            "original_response", self.model_call_details
                        )
                    )
                )
            if self.logger_fn and callable(self.logger_fn):
                try:
                    self.logger_fn(
                        self.model_call_details
                    )  # Expectation: any logger function passed in by the user should accept a dict object
                except Exception as e:
                    verbose_logger.exception(
                        "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while logging {}".format(
                            str(e)
                        )
                    )
            original_response = redact_message_input_output_from_logging(
                model_call_details=(
                    self.model_call_details
                    if hasattr(self, "model_call_details")
                    else {}
                ),
                result=original_response,
            )
            # Input Integration Logging -> If you want to log the fact that an attempt to call the model was made

            callbacks = litellm.input_callback + (self.dynamic_input_callbacks or [])
            for callback in callbacks:
                try:
                    if callback == "sentry" and add_breadcrumb:
                        verbose_logger.debug("reaches sentry breadcrumbing")
                        try:
                            details_to_log = copy.deepcopy(self.model_call_details)
                        except Exception:
                            details_to_log = self.model_call_details
                        if litellm.turn_off_message_logging:
                            # make a copy of the _model_Call_details and log it
                            details_to_log.pop("messages", None)
                            details_to_log.pop("input", None)
                            details_to_log.pop("prompt", None)

                        add_breadcrumb(
                            category="litellm.llm_call",
                            message=f"Model Call Details post-call: {details_to_log}",
                            level="info",
                        )
                    elif isinstance(callback, CustomLogger):  # custom logger class
                        callback.log_post_api_call(
                            kwargs=self.model_call_details,
                            response_obj=None,
                            start_time=self.start_time,
                            end_time=None,
                        )
                except Exception as e:
                    verbose_logger.exception(
                        "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while post-call logging with integrations {}".format(
                            str(e)
                        )
                    )
                    verbose_logger.debug(
                        f"LiteLLM.Logging: is sentry capture exception initialized {capture_exception}"
                    )
                    if capture_exception:  # log this error to sentry for debugging
                        capture_exception(e)
        except Exception as e:
            verbose_logger.exception(
                "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while logging {}".format(
                    str(e)
                )
            )

    def get_response_ms(self) -> float:
        return (
            self.model_call_details.get("end_time", datetime.datetime.now())
            - self.model_call_details.get("start_time", datetime.datetime.now())
        ).total_seconds() * 1000

    def _response_cost_calculator(
        self,
        result: Union[
            ModelResponse,
            ModelResponseStream,
            EmbeddingResponse,
            ImageResponse,
            TranscriptionResponse,
            TextCompletionResponse,
            HttpxBinaryResponseContent,
            RerankResponse,
            Batch,
            FineTuningJob,
            ResponsesAPIResponse,
            ResponseCompletedEvent,
            OpenAIFileObject,
            LiteLLMRealtimeStreamLoggingObject,
            OpenAIModerationResponse,
        ],
        cache_hit: Optional[bool] = None,
        litellm_model_name: Optional[str] = None,
        router_model_id: Optional[str] = None,
    ) -> Optional[float]:
        """
        Calculate response cost using result + logging object variables.

        used for consistent cost calculation across response headers + logging integrations.
        """

        ## RESPONSE COST ##
        custom_pricing = use_custom_pricing_for_model(
            litellm_params=(
                self.litellm_params if hasattr(self, "litellm_params") else None
            )
        )

        prompt = ""  # use for tts cost calc
        _input = self.model_call_details.get("input", None)
        if _input is not None and isinstance(_input, str):
            prompt = _input

        if cache_hit is None:
            cache_hit = self.model_call_details.get("cache_hit", False)

        try:
            response_cost_calculator_kwargs = {
                "response_object": result,
                "model": litellm_model_name or self.model,
                "cache_hit": cache_hit,
                "custom_llm_provider": self.model_call_details.get(
                    "custom_llm_provider", None
                ),
                "base_model": _get_base_model_from_metadata(
                    model_call_details=self.model_call_details
                ),
                "call_type": self.call_type,
                "optional_params": self.optional_params,
                "custom_pricing": custom_pricing,
                "prompt": prompt,
                "standard_built_in_tools_params": self.standard_built_in_tools_params,
                "router_model_id": router_model_id,
            }
        except Exception as e:  # error creating kwargs for cost calculation
            debug_info = StandardLoggingModelCostFailureDebugInformation(
                error_str=str(e),
                traceback_str=_get_traceback_str_for_error(str(e)),
            )
            verbose_logger.debug(
                f"response_cost_failure_debug_information: {debug_info}"
            )
            self.model_call_details["response_cost_failure_debug_information"] = (
                debug_info
            )
            return None

        try:
            response_cost = litellm.response_cost_calculator(
                **response_cost_calculator_kwargs
            )
            verbose_logger.debug(f"response_cost: {response_cost}")
            return response_cost
        except Exception as e:  # error calculating cost
            debug_info = StandardLoggingModelCostFailureDebugInformation(
                error_str=str(e),
                traceback_str=_get_traceback_str_for_error(str(e)),
                model=response_cost_calculator_kwargs["model"],
                cache_hit=response_cost_calculator_kwargs["cache_hit"],
                custom_llm_provider=response_cost_calculator_kwargs[
                    "custom_llm_provider"
                ],
                base_model=response_cost_calculator_kwargs["base_model"],
                call_type=response_cost_calculator_kwargs["call_type"],
                custom_pricing=response_cost_calculator_kwargs["custom_pricing"],
            )
            verbose_logger.debug(
                f"response_cost_failure_debug_information: {debug_info}"
            )
            self.model_call_details["response_cost_failure_debug_information"] = (
                debug_info
            )

        return None

    async def _response_cost_calculator_async(
        self,
        result: Union[
            ModelResponse,
            ModelResponseStream,
            EmbeddingResponse,
            ImageResponse,
            TranscriptionResponse,
            TextCompletionResponse,
            HttpxBinaryResponseContent,
            RerankResponse,
            Batch,
            FineTuningJob,
        ],
        cache_hit: Optional[bool] = None,
    ) -> Optional[float]:
        return self._response_cost_calculator(result=result, cache_hit=cache_hit)

    def should_run_logging(
        self,
        event_type: Literal[
            "async_success", "sync_success", "async_failure", "sync_failure"
        ],
        stream: bool = False,
    ) -> bool:
        try:
            if self.model_call_details.get(f"has_logged_{event_type}", False) is True:
                return False

            return True
        except Exception:
            return True

    def has_run_logging(
        self,
        event_type: Literal[
            "async_success", "sync_success", "async_failure", "sync_failure"
        ],
    ) -> None:
        if self.stream is not None and self.stream is True:
            """
            Ignore check on stream, as there can be multiple chunks
            """
            return
        self.model_call_details[f"has_logged_{event_type}"] = True
        return

    def should_run_callback(
        self, callback: litellm.CALLBACK_TYPES, litellm_params: dict, event_hook: str
    ) -> bool:
        if litellm.global_disable_no_log_param:
            return True

        if litellm_params.get("no-log", False) is True:
            # proxy cost tracking cal backs should run

            if not (
                isinstance(callback, CustomLogger)
                and "_PROXY_" in callback.__class__.__name__
            ):
                verbose_logger.debug(
                    f"no-log request, skipping logging for {event_hook} event"
                )
                return False
        return True

    def _update_completion_start_time(self, completion_start_time: datetime.datetime):
        self.completion_start_time = completion_start_time
        self.model_call_details["completion_start_time"] = self.completion_start_time

    def _success_handler_helper_fn(
        self,
        result=None,
        start_time=None,
        end_time=None,
        cache_hit=None,
        standard_logging_object: Optional[StandardLoggingPayload] = None,
    ):
        try:
            if start_time is None:
                start_time = self.start_time
            if end_time is None:
                end_time = datetime.datetime.now()
            if self.completion_start_time is None:
                self.completion_start_time = end_time
                self.model_call_details["completion_start_time"] = (
                    self.completion_start_time
                )
            self.model_call_details["log_event_type"] = "successful_api_call"
            self.model_call_details["end_time"] = end_time
            self.model_call_details["cache_hit"] = cache_hit

            if self.call_type == CallTypes.anthropic_messages.value:
                result = self._handle_anthropic_messages_response_logging(result=result)
            ## if model in model cost map - log the response cost
            ## else set cost to None

            logging_result = result

            if self.call_type == CallTypes.arealtime.value and isinstance(result, list):
                combined_usage_object = RealtimeAPITokenUsageProcessor.collect_and_combine_usage_from_realtime_stream_results(
                    results=result
                )
                logging_result = (
                    RealtimeAPITokenUsageProcessor.create_logging_realtime_object(
                        usage=combined_usage_object,
                        results=result,
                    )
                )

                # self.model_call_details[
                #     "response_cost"
                # ] = handle_realtime_stream_cost_calculation(
                #     results=result,
                #     combined_usage_object=combined_usage_object,
                #     custom_llm_provider=self.custom_llm_provider,
                #     litellm_model_name=self.model,
                # )
                # self.model_call_details["combined_usage_object"] = combined_usage_object
            if (
                standard_logging_object is None
                and result is not None
                and self.stream is not True
            ):
                if (
                    isinstance(logging_result, ModelResponse)
                    or isinstance(logging_result, ModelResponseStream)
                    or isinstance(logging_result, EmbeddingResponse)
                    or isinstance(logging_result, ImageResponse)
                    or isinstance(logging_result, TranscriptionResponse)
                    or isinstance(logging_result, TextCompletionResponse)
                    or isinstance(logging_result, HttpxBinaryResponseContent)  # tts
                    or isinstance(logging_result, RerankResponse)
                    or isinstance(logging_result, FineTuningJob)
                    or isinstance(logging_result, LiteLLMBatch)
                    or isinstance(logging_result, ResponsesAPIResponse)
                    or isinstance(logging_result, OpenAIFileObject)
                    or isinstance(logging_result, LiteLLMRealtimeStreamLoggingObject)
                    or isinstance(logging_result, OpenAIModerationResponse)
                ):
                    ## HIDDEN PARAMS ##
                    hidden_params = getattr(logging_result, "_hidden_params", {})
                    if hidden_params:
                        # add to metadata for logging
                        if self.model_call_details.get("litellm_params") is not None:
                            self.model_call_details["litellm_params"].setdefault(
                                "metadata", {}
                            )
                            if (
                                self.model_call_details["litellm_params"]["metadata"]
                                is None
                            ):
                                self.model_call_details["litellm_params"][
                                    "metadata"
                                ] = {}

                            self.model_call_details["litellm_params"]["metadata"][  # type: ignore
                                "hidden_params"
                            ] = getattr(
                                logging_result, "_hidden_params", {}
                            )
                    ## RESPONSE COST - Only calculate if not in hidden_params ##
                    if "response_cost" in hidden_params:
                        self.model_call_details["response_cost"] = hidden_params[
                            "response_cost"
                        ]
                    else:
                        self.model_call_details["response_cost"] = (
                            self._response_cost_calculator(result=logging_result)
                        )
                    ## STANDARDIZED LOGGING PAYLOAD

                    self.model_call_details["standard_logging_object"] = (
                        get_standard_logging_object_payload(
                            kwargs=self.model_call_details,
                            init_response_obj=logging_result,
                            start_time=start_time,
                            end_time=end_time,
                            logging_obj=self,
                            status="success",
                            standard_built_in_tools_params=self.standard_built_in_tools_params,
                        )
                    )
                elif isinstance(result, dict) or isinstance(result, list):
                    ## STANDARDIZED LOGGING PAYLOAD
                    self.model_call_details["standard_logging_object"] = (
                        get_standard_logging_object_payload(
                            kwargs=self.model_call_details,
                            init_response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            logging_obj=self,
                            status="success",
                            standard_built_in_tools_params=self.standard_built_in_tools_params,
                        )
                    )
            elif standard_logging_object is not None:
                self.model_call_details["standard_logging_object"] = (
                    standard_logging_object
                )
            else:  # streaming chunks + image gen.
                self.model_call_details["response_cost"] = None

            ## RESPONSES API USAGE OBJECT TRANSFORMATION ##
            # MAP RESPONSES API USAGE OBJECT TO LITELLM USAGE OBJECT
            if isinstance(result, ResponsesAPIResponse):
                result = result.model_copy()
                setattr(
                    result,
                    "usage",
                    ResponseAPILoggingUtils._transform_response_api_usage_to_chat_usage(
                        result.usage
                    ),
                )

            if (
                litellm.max_budget
                and self.stream is False
                and result is not None
                and isinstance(result, dict)
                and "content" in result
            ):
                time_diff = (end_time - start_time).total_seconds()
                float_diff = float(time_diff)
                litellm._current_cost += litellm.completion_cost(
                    model=self.model,
                    prompt="",
                    completion=getattr(result, "content", ""),
                    total_time=float_diff,
                    standard_built_in_tools_params=self.standard_built_in_tools_params,
                )

            return start_time, end_time, result
        except Exception as e:
            raise Exception(f"[Non-Blocking] LiteLLM.Success_Call Error: {str(e)}")

    def success_handler(  # noqa: PLR0915
        self, result=None, start_time=None, end_time=None, cache_hit=None, **kwargs
    ):
        verbose_logger.debug(
            f"Logging Details LiteLLM-Success Call: Cache_hit={cache_hit}"
        )
        if not self.should_run_logging(
            event_type="sync_success"
        ):  # prevent double logging
            return
        start_time, end_time, result = self._success_handler_helper_fn(
            start_time=start_time,
            end_time=end_time,
            result=result,
            cache_hit=cache_hit,
            standard_logging_object=kwargs.get("standard_logging_object", None),
        )
        try:
            ## BUILD COMPLETE STREAMED RESPONSE
            complete_streaming_response: Optional[
                Union[ModelResponse, TextCompletionResponse, ResponsesAPIResponse]
            ] = None
            if "complete_streaming_response" in self.model_call_details:
                return  # break out of this.
            complete_streaming_response = self._get_assembled_streaming_response(
                result=result,
                start_time=start_time,
                end_time=end_time,
                is_async=False,
                streaming_chunks=self.sync_streaming_chunks,
            )
            if complete_streaming_response is not None:
                verbose_logger.debug(
                    "Logging Details LiteLLM-Success Call streaming complete"
                )
                self.model_call_details["complete_streaming_response"] = (
                    complete_streaming_response
                )
                self.model_call_details["response_cost"] = (
                    self._response_cost_calculator(result=complete_streaming_response)
                )
                ## STANDARDIZED LOGGING PAYLOAD
                self.model_call_details["standard_logging_object"] = (
                    get_standard_logging_object_payload(
                        kwargs=self.model_call_details,
                        init_response_obj=complete_streaming_response,
                        start_time=start_time,
                        end_time=end_time,
                        logging_obj=self,
                        status="success",
                        standard_built_in_tools_params=self.standard_built_in_tools_params,
                    )
                )
            callbacks = self.get_combined_callback_list(
                dynamic_success_callbacks=self.dynamic_success_callbacks,
                global_callbacks=litellm.success_callback,
            )

            ## REDACT MESSAGES ##
            result = redact_message_input_output_from_logging(
                model_call_details=(
                    self.model_call_details
                    if hasattr(self, "model_call_details")
                    else {}
                ),
                result=result,
            )
            ## LOGGING HOOK ##
            for callback in callbacks:
                if isinstance(callback, CustomLogger):
                    self.model_call_details, result = callback.logging_hook(
                        kwargs=self.model_call_details,
                        result=result,
                        call_type=self.call_type,
                    )

            self.has_run_logging(event_type="sync_success")
            for callback in callbacks:
                try:
                    litellm_params = self.model_call_details.get("litellm_params", {})
                    should_run = self.should_run_callback(
                        callback=callback,
                        litellm_params=litellm_params,
                        event_hook="success_handler",
                    )
                    if not should_run:
                        continue
                    if callback == "promptlayer" and promptLayerLogger is not None:
                        print_verbose("reaches promptlayer for logging!")
                        promptLayerLogger.log_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                        )
                    if callback == "supabase" and supabaseClient is not None:
                        print_verbose("reaches supabase for logging!")
                        kwargs = self.model_call_details

                        # this only logs streaming once, complete_streaming_response exists i.e when stream ends
                        if self.stream:
                            if "complete_streaming_response" not in kwargs:
                                continue
                            else:
                                print_verbose("reaches supabase for streaming logging!")
                                result = kwargs["complete_streaming_response"]

                        model = kwargs["model"]
                        messages = kwargs["messages"]
                        optional_params = kwargs.get("optional_params", {})
                        litellm_params = kwargs.get("litellm_params", {})
                        supabaseClient.log_event(
                            model=model,
                            messages=messages,
                            end_user=optional_params.get("user", "default"),
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            litellm_call_id=litellm_params.get(
                                "litellm_call_id", str(uuid.uuid4())
                            ),
                            print_verbose=print_verbose,
                        )
                    if callback == "wandb" and weightsBiasesLogger is not None:
                        print_verbose("reaches wandb for logging!")
                        weightsBiasesLogger.log_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                        )
                    if callback == "logfire" and logfireLogger is not None:
                        verbose_logger.debug("reaches logfire for success logging!")
                        kwargs = {}
                        for k, v in self.model_call_details.items():
                            if (
                                k != "original_response"
                            ):  # copy.deepcopy raises errors as this could be a coroutine
                                kwargs[k] = v

                        # this only logs streaming once, complete_streaming_response exists i.e when stream ends
                        if self.stream:
                            if "complete_streaming_response" not in kwargs:
                                continue
                            else:
                                print_verbose("reaches logfire for streaming logging!")
                                result = kwargs["complete_streaming_response"]

                        logfireLogger.log_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                            level=LogfireLevel.INFO.value,  # type: ignore
                        )

                    if callback == "lunary" and lunaryLogger is not None:
                        print_verbose("reaches lunary for logging!")
                        model = self.model
                        kwargs = self.model_call_details

                        input = kwargs.get("messages", kwargs.get("input", None))

                        type = (
                            "embed"
                            if self.call_type == CallTypes.embedding.value
                            else "llm"
                        )

                        # this only logs streaming once, complete_streaming_response exists i.e when stream ends
                        if self.stream:
                            if "complete_streaming_response" not in kwargs:
                                continue
                            else:
                                result = kwargs["complete_streaming_response"]

                        lunaryLogger.log_event(
                            type=type,
                            kwargs=kwargs,
                            event="end",
                            model=model,
                            input=input,
                            user_id=kwargs.get("user", None),
                            # user_props=self.model_call_details.get("user_props", None),
                            extra=kwargs.get("optional_params", {}),
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            run_id=self.litellm_call_id,
                            print_verbose=print_verbose,
                        )
                    if callback == "helicone" and heliconeLogger is not None:
                        print_verbose("reaches helicone for logging!")
                        model = self.model
                        messages = self.model_call_details["input"]
                        kwargs = self.model_call_details

                        # this only logs streaming once, complete_streaming_response exists i.e when stream ends
                        if self.stream:
                            if "complete_streaming_response" not in kwargs:
                                continue
                            else:
                                print_verbose("reaches helicone for streaming logging!")
                                result = kwargs["complete_streaming_response"]

                        heliconeLogger.log_success(
                            model=model,
                            messages=messages,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                            kwargs=kwargs,
                        )
                    if callback == "langfuse":
                        global langFuseLogger
                        print_verbose("reaches langfuse for success logging!")
                        kwargs = {}
                        for k, v in self.model_call_details.items():
                            if (
                                k != "original_response"
                            ):  # copy.deepcopy raises errors as this could be a coroutine
                                kwargs[k] = v
                        # this only logs streaming once, complete_streaming_response exists i.e when stream ends
                        if self.stream:
                            verbose_logger.debug(
                                f"is complete_streaming_response in kwargs: {kwargs.get('complete_streaming_response', None)}"
                            )
                            if complete_streaming_response is None:
                                continue
                            else:
                                print_verbose("reaches langfuse for streaming logging!")
                                result = kwargs["complete_streaming_response"]

                        langfuse_logger_to_use = LangFuseHandler.get_langfuse_logger_for_request(
                            globalLangfuseLogger=langFuseLogger,
                            standard_callback_dynamic_params=self.standard_callback_dynamic_params,
                            in_memory_dynamic_logger_cache=in_memory_dynamic_logger_cache,
                        )
                        if langfuse_logger_to_use is not None:
                            _response = langfuse_logger_to_use.log_event_on_langfuse(
                                kwargs=kwargs,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                                user_id=kwargs.get("user", None),
                            )
                            if _response is not None and isinstance(_response, dict):
                                _trace_id = _response.get("trace_id", None)
                                if _trace_id is not None:
                                    in_memory_trace_id_cache.set_cache(
                                        litellm_call_id=self.litellm_call_id,
                                        service_name="langfuse",
                                        trace_id=_trace_id,
                                    )
                    if callback == "greenscale" and greenscaleLogger is not None:
                        kwargs = {}
                        for k, v in self.model_call_details.items():
                            if (
                                k != "original_response"
                            ):  # copy.deepcopy raises errors as this could be a coroutine
                                kwargs[k] = v
                        # this only logs streaming once, complete_streaming_response exists i.e when stream ends
                        if self.stream:
                            verbose_logger.debug(
                                f"is complete_streaming_response in kwargs: {kwargs.get('complete_streaming_response', None)}"
                            )
                            if complete_streaming_response is None:
                                continue
                            else:
                                print_verbose(
                                    "reaches greenscale for streaming logging!"
                                )
                                result = kwargs["complete_streaming_response"]

                        greenscaleLogger.log_event(
                            kwargs=kwargs,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                        )
                    if callback == "athina" and athinaLogger is not None:
                        deep_copy = {}
                        for k, v in self.model_call_details.items():
                            deep_copy[k] = v
                        athinaLogger.log_event(
                            kwargs=deep_copy,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                        )
                    if callback == "traceloop":
                        deep_copy = {}
                        for k, v in self.model_call_details.items():
                            if k != "original_response":
                                deep_copy[k] = v
                        traceloopLogger.log_event(
                            kwargs=deep_copy,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            user_id=kwargs.get("user", None),
                            print_verbose=print_verbose,
                        )
                    if callback == "s3":
                        global s3Logger
                        if s3Logger is None:
                            s3Logger = S3Logger()
                        if self.stream:
                            if "complete_streaming_response" in self.model_call_details:
                                print_verbose(
                                    "S3Logger Logger: Got Stream Event - Completed Stream Response"
                                )
                                s3Logger.log_event(
                                    kwargs=self.model_call_details,
                                    response_obj=self.model_call_details[
                                        "complete_streaming_response"
                                    ],
                                    start_time=start_time,
                                    end_time=end_time,
                                    print_verbose=print_verbose,
                                )
                            else:
                                print_verbose(
                                    "S3Logger Logger: Got Stream Event - No complete stream response as yet"
                                )
                        else:
                            s3Logger.log_event(
                                kwargs=self.model_call_details,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                                print_verbose=print_verbose,
                            )

                    if (
                        callback == "openmeter"
                        and self.model_call_details.get("litellm_params", {}).get(
                            "acompletion", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "aembedding", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "aimage_generation", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "atranscription", False
                        )
                        is not True
                    ):
                        global openMeterLogger
                        if openMeterLogger is None:
                            print_verbose("Instantiates openmeter client")
                            openMeterLogger = OpenMeterLogger()
                        if self.stream and complete_streaming_response is None:
                            openMeterLogger.log_stream_event(
                                kwargs=self.model_call_details,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                            )
                        else:
                            if self.stream and complete_streaming_response:
                                self.model_call_details["complete_response"] = (
                                    self.model_call_details.get(
                                        "complete_streaming_response", {}
                                    )
                                )
                                result = self.model_call_details["complete_response"]
                            openMeterLogger.log_success_event(
                                kwargs=self.model_call_details,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                            )
                    if (
                        isinstance(callback, CustomLogger)
                        and self.model_call_details.get("litellm_params", {}).get(
                            "acompletion", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "aembedding", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "aimage_generation", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "atranscription", False
                        )
                        is not True
                        and self.call_type
                        != CallTypes.pass_through.value  # pass-through endpoints call async_log_success_event
                    ):  # custom logger class
                        if self.stream and complete_streaming_response is None:
                            callback.log_stream_event(
                                kwargs=self.model_call_details,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                            )
                        else:
                            if self.stream and complete_streaming_response:
                                self.model_call_details["complete_response"] = (
                                    self.model_call_details.get(
                                        "complete_streaming_response", {}
                                    )
                                )
                                result = self.model_call_details["complete_response"]

                            callback.log_success_event(
                                kwargs=self.model_call_details,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                            )
                    if (
                        callable(callback) is True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "acompletion", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "aembedding", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "aimage_generation", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "atranscription", False
                        )
                        is not True
                        and customLogger is not None
                    ):  # custom logger functions
                        print_verbose(
                            "success callbacks: Running Custom Callback Function - {}".format(
                                callback
                            )
                        )

                        customLogger.log_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                            callback_func=callback,
                        )

                except Exception as e:
                    print_verbose(
                        f"LiteLLM.LoggingError: [Non-Blocking] Exception occurred while success logging with integrations {traceback.format_exc()}"
                    )
                    print_verbose(
                        f"LiteLLM.Logging: is sentry capture exception initialized {capture_exception}"
                    )
                    if capture_exception:  # log this error to sentry for debugging
                        capture_exception(e)
        except Exception as e:
            verbose_logger.exception(
                "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while success logging {}".format(
                    str(e)
                ),
            )

    async def async_success_handler(  # noqa: PLR0915
        self, result=None, start_time=None, end_time=None, cache_hit=None, **kwargs
    ):
        """
        Implementing async callbacks, to handle asyncio event loop issues when custom integrations need to use async functions.
        """
        print_verbose(
            "Logging Details LiteLLM-Async Success Call, cache_hit={}".format(cache_hit)
        )
        if not self.should_run_logging(
            event_type="async_success"
        ):  # prevent double logging
            return

        ## CALCULATE COST FOR BATCH JOBS
        if self.call_type == CallTypes.aretrieve_batch.value and isinstance(
            result, LiteLLMBatch
        ):
            response_cost, batch_usage, batch_models = await _handle_completed_batch(
                batch=result, custom_llm_provider=self.custom_llm_provider
            )

            result._hidden_params["response_cost"] = response_cost
            result._hidden_params["batch_models"] = batch_models
            result.usage = batch_usage

        start_time, end_time, result = self._success_handler_helper_fn(
            start_time=start_time,
            end_time=end_time,
            result=result,
            cache_hit=cache_hit,
            standard_logging_object=kwargs.get("standard_logging_object", None),
        )

        ## BUILD COMPLETE STREAMED RESPONSE
        if "async_complete_streaming_response" in self.model_call_details:
            return  # break out of this.
        complete_streaming_response: Optional[
            Union[ModelResponse, TextCompletionResponse, ResponsesAPIResponse]
        ] = self._get_assembled_streaming_response(
            result=result,
            start_time=start_time,
            end_time=end_time,
            is_async=True,
            streaming_chunks=self.streaming_chunks,
        )

        if complete_streaming_response is not None:
            print_verbose("Async success callbacks: Got a complete streaming response")

            self.model_call_details["async_complete_streaming_response"] = (
                complete_streaming_response
            )
            try:
                if self.model_call_details.get("cache_hit", False) is True:
                    self.model_call_details["response_cost"] = 0.0
                else:
                    # check if base_model set on azure
                    _get_base_model_from_metadata(
                        model_call_details=self.model_call_details
                    )
                    # base_model defaults to None if not set on model_info
                    self.model_call_details["response_cost"] = (
                        self._response_cost_calculator(
                            result=complete_streaming_response
                        )
                    )

                verbose_logger.debug(
                    f"Model={self.model}; cost={self.model_call_details['response_cost']}"
                )
            except litellm.NotFoundError:
                verbose_logger.warning(
                    f"Model={self.model} not found in completion cost map. Setting 'response_cost' to None"
                )
                self.model_call_details["response_cost"] = None

            ## STANDARDIZED LOGGING PAYLOAD
            self.model_call_details["standard_logging_object"] = (
                get_standard_logging_object_payload(
                    kwargs=self.model_call_details,
                    init_response_obj=complete_streaming_response,
                    start_time=start_time,
                    end_time=end_time,
                    logging_obj=self,
                    status="success",
                    standard_built_in_tools_params=self.standard_built_in_tools_params,
                )
            )
        callbacks = self.get_combined_callback_list(
            dynamic_success_callbacks=self.dynamic_async_success_callbacks,
            global_callbacks=litellm._async_success_callback,
        )

        result = redact_message_input_output_from_logging(
            model_call_details=(
                self.model_call_details if hasattr(self, "model_call_details") else {}
            ),
            result=result,
        )

        ## LOGGING HOOK ##

        for callback in callbacks:
            if isinstance(callback, CustomGuardrail):
                from litellm.types.guardrails import GuardrailEventHooks

                if (
                    callback.should_run_guardrail(
                        data=self.model_call_details,
                        event_type=GuardrailEventHooks.logging_only,
                    )
                    is not True
                ):
                    continue

                self.model_call_details, result = await callback.async_logging_hook(
                    kwargs=self.model_call_details,
                    result=result,
                    call_type=self.call_type,
                )
            elif isinstance(callback, CustomLogger):
                result = redact_message_input_output_from_custom_logger(
                    result=result, litellm_logging_obj=self, custom_logger=callback
                )
                self.model_call_details, result = await callback.async_logging_hook(
                    kwargs=self.model_call_details,
                    result=result,
                    call_type=self.call_type,
                )

        self.has_run_logging(event_type="async_success")
        for callback in callbacks:
            # check if callback can run for this request
            litellm_params = self.model_call_details.get("litellm_params", {})
            should_run = self.should_run_callback(
                callback=callback,
                litellm_params=litellm_params,
                event_hook="async_success_handler",
            )
            if not should_run:
                continue
            try:
                if callback == "openmeter" and openMeterLogger is not None:
                    if self.stream is True:
                        if (
                            "async_complete_streaming_response"
                            in self.model_call_details
                        ):
                            await openMeterLogger.async_log_success_event(
                                kwargs=self.model_call_details,
                                response_obj=self.model_call_details[
                                    "async_complete_streaming_response"
                                ],
                                start_time=start_time,
                                end_time=end_time,
                            )
                        else:
                            await openMeterLogger.async_log_stream_event(  # [TODO]: move this to being an async log stream event function
                                kwargs=self.model_call_details,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                            )
                    else:
                        await openMeterLogger.async_log_success_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                        )
                if isinstance(callback, CustomLogger):  # custom logger class
                    if self.stream is True:
                        if (
                            "async_complete_streaming_response"
                            in self.model_call_details
                        ):
                            await callback.async_log_success_event(
                                kwargs=self.model_call_details,
                                response_obj=self.model_call_details[
                                    "async_complete_streaming_response"
                                ],
                                start_time=start_time,
                                end_time=end_time,
                            )
                        else:
                            await callback.async_log_stream_event(  # [TODO]: move this to being an async log stream event function
                                kwargs=self.model_call_details,
                                response_obj=result,
                                start_time=start_time,
                                end_time=end_time,
                            )
                    else:
                        await callback.async_log_success_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                        )
                if callable(callback):  # custom logger functions
                    global customLogger
                    if customLogger is None:
                        customLogger = CustomLogger()
                    if self.stream:
                        if (
                            "async_complete_streaming_response"
                            in self.model_call_details
                        ):
                            await customLogger.async_log_event(
                                kwargs=self.model_call_details,
                                response_obj=self.model_call_details[
                                    "async_complete_streaming_response"
                                ],
                                start_time=start_time,
                                end_time=end_time,
                                print_verbose=print_verbose,
                                callback_func=callback,
                            )
                    else:
                        await customLogger.async_log_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                            callback_func=callback,
                        )
                if callback == "dynamodb":
                    global dynamoLogger
                    if dynamoLogger is None:
                        dynamoLogger = DyanmoDBLogger()
                    if self.stream:
                        if (
                            "async_complete_streaming_response"
                            in self.model_call_details
                        ):
                            print_verbose(
                                "DynamoDB Logger: Got Stream Event - Completed Stream Response"
                            )
                            await dynamoLogger._async_log_event(
                                kwargs=self.model_call_details,
                                response_obj=self.model_call_details[
                                    "async_complete_streaming_response"
                                ],
                                start_time=start_time,
                                end_time=end_time,
                                print_verbose=print_verbose,
                            )
                        else:
                            print_verbose(
                                "DynamoDB Logger: Got Stream Event - No complete stream response as yet"
                            )
                    else:
                        await dynamoLogger._async_log_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                        )
            except Exception:
                verbose_logger.error(
                    f"LiteLLM.LoggingError: [Non-Blocking] Exception occurred while success logging {traceback.format_exc()}"
                )
                pass

    def _failure_handler_helper_fn(
        self, exception, traceback_exception, start_time=None, end_time=None
    ):
        if start_time is None:
            start_time = self.start_time
        if end_time is None:
            end_time = datetime.datetime.now()

        # on some exceptions, model_call_details is not always initialized, this ensures that we still log those exceptions
        if not hasattr(self, "model_call_details"):
            self.model_call_details = {}

        self.model_call_details["log_event_type"] = "failed_api_call"
        self.model_call_details["exception"] = exception
        self.model_call_details["traceback_exception"] = traceback_exception
        self.model_call_details["end_time"] = end_time
        self.model_call_details.setdefault("original_response", None)
        self.model_call_details["response_cost"] = 0

        if hasattr(exception, "headers") and isinstance(exception.headers, dict):
            self.model_call_details.setdefault("litellm_params", {})
            metadata = (
                self.model_call_details["litellm_params"].get("metadata", {}) or {}
            )
            metadata.update(exception.headers)

        ## STANDARDIZED LOGGING PAYLOAD

        self.model_call_details["standard_logging_object"] = (
            get_standard_logging_object_payload(
                kwargs=self.model_call_details,
                init_response_obj={},
                start_time=start_time,
                end_time=end_time,
                logging_obj=self,
                status="failure",
                error_str=str(exception),
                original_exception=exception,
                standard_built_in_tools_params=self.standard_built_in_tools_params,
            )
        )
        return start_time, end_time

    async def special_failure_handlers(self, exception: Exception):
        """
        Custom events, emitted for specific failures.

        Currently just for router model group rate limit error
        """
        from litellm.types.router import RouterErrors

        litellm_params: dict = self.model_call_details.get("litellm_params") or {}
        metadata = litellm_params.get("metadata") or {}

        ## BASE CASE ## check if rate limit error for model group size 1
        is_base_case = False
        if metadata.get("model_group_size") is not None:
            model_group_size = metadata.get("model_group_size")
            if isinstance(model_group_size, int) and model_group_size == 1:
                is_base_case = True
        ## check if special error ##
        if (
            RouterErrors.no_deployments_available.value not in str(exception)
            and is_base_case is False
        ):
            return

        ## get original model group ##

        model_group = metadata.get("model_group") or None
        for callback in litellm._async_failure_callback:
            if isinstance(callback, CustomLogger):  # custom logger class
                await callback.log_model_group_rate_limit_error(
                    exception=exception,
                    original_model_group=model_group,
                    kwargs=self.model_call_details,
                )  # type: ignore

    def failure_handler(  # noqa: PLR0915
        self, exception, traceback_exception, start_time=None, end_time=None
    ):
        verbose_logger.debug(
            f"Logging Details LiteLLM-Failure Call: {litellm.failure_callback}"
        )
        if not self.should_run_logging(
            event_type="sync_failure"
        ):  # prevent double logging
            return
        try:
            start_time, end_time = self._failure_handler_helper_fn(
                exception=exception,
                traceback_exception=traceback_exception,
                start_time=start_time,
                end_time=end_time,
            )
            callbacks = self.get_combined_callback_list(
                dynamic_success_callbacks=self.dynamic_failure_callbacks,
                global_callbacks=litellm.failure_callback,
            )

            result = None  # result sent to all loggers, init this to None incase it's not created

            result = redact_message_input_output_from_logging(
                model_call_details=(
                    self.model_call_details
                    if hasattr(self, "model_call_details")
                    else {}
                ),
                result=result,
            )
            self.has_run_logging(event_type="sync_failure")
            for callback in callbacks:
                try:
                    if callback == "lunary" and lunaryLogger is not None:
                        print_verbose("reaches lunary for logging error!")

                        model = self.model

                        input = self.model_call_details["input"]

                        _type = (
                            "embed"
                            if self.call_type == CallTypes.embedding.value
                            else "llm"
                        )

                        lunaryLogger.log_event(
                            kwargs=self.model_call_details,
                            type=_type,
                            event="error",
                            user_id=self.model_call_details.get("user", "default"),
                            model=model,
                            input=input,
                            error=traceback_exception,
                            run_id=self.litellm_call_id,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                        )
                    if callback == "sentry":
                        print_verbose("sending exception to sentry")
                        if capture_exception:
                            capture_exception(exception)
                        else:
                            print_verbose(
                                f"capture exception not initialized: {capture_exception}"
                            )
                    elif callback == "supabase" and supabaseClient is not None:
                        print_verbose("reaches supabase for logging!")
                        print_verbose(f"supabaseClient: {supabaseClient}")
                        supabaseClient.log_event(
                            model=self.model if hasattr(self, "model") else "",
                            messages=self.messages,
                            end_user=self.model_call_details.get("user", "default"),
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            litellm_call_id=self.model_call_details["litellm_call_id"],
                            print_verbose=print_verbose,
                        )
                    if (
                        callable(callback) and customLogger is not None
                    ):  # custom logger functions
                        customLogger.log_event(
                            kwargs=self.model_call_details,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            print_verbose=print_verbose,
                            callback_func=callback,
                        )
                    if (
                        isinstance(callback, CustomLogger)
                        and self.model_call_details.get("litellm_params", {}).get(
                            "acompletion", False
                        )
                        is not True
                        and self.model_call_details.get("litellm_params", {}).get(
                            "aembedding", False
                        )
                        is not True
                    ):  # custom logger class
                        callback.log_failure_event(
                            start_time=start_time,
                            end_time=end_time,
                            response_obj=result,
                            kwargs=self.model_call_details,
                        )
                    if callback == "langfuse":
                        global langFuseLogger
                        verbose_logger.debug("reaches langfuse for logging failure")
                        kwargs = {}
                        for k, v in self.model_call_details.items():
                            if (
                                k != "original_response"
                            ):  # copy.deepcopy raises errors as this could be a coroutine
                                kwargs[k] = v
                        # this only logs streaming once, complete_streaming_response exists i.e when stream ends
                        langfuse_logger_to_use = LangFuseHandler.get_langfuse_logger_for_request(
                            globalLangfuseLogger=langFuseLogger,
                            standard_callback_dynamic_params=self.standard_callback_dynamic_params,
                            in_memory_dynamic_logger_cache=in_memory_dynamic_logger_cache,
                        )
                        _response = langfuse_logger_to_use.log_event_on_langfuse(
                            start_time=start_time,
                            end_time=end_time,
                            response_obj=None,
                            user_id=kwargs.get("user", None),
                            status_message=str(exception),
                            level="ERROR",
                            kwargs=self.model_call_details,
                        )
                        if _response is not None and isinstance(_response, dict):
                            _trace_id = _response.get("trace_id", None)
                            if _trace_id is not None:
                                in_memory_trace_id_cache.set_cache(
                                    litellm_call_id=self.litellm_call_id,
                                    service_name="langfuse",
                                    trace_id=_trace_id,
                                )
                    if callback == "traceloop":
                        traceloopLogger.log_event(
                            start_time=start_time,
                            end_time=end_time,
                            response_obj=None,
                            user_id=self.model_call_details.get("user", None),
                            print_verbose=print_verbose,
                            status_message=str(exception),
                            level="ERROR",
                            kwargs=self.model_call_details,
                        )
                    if callback == "logfire" and logfireLogger is not None:
                        verbose_logger.debug("reaches logfire for failure logging!")
                        kwargs = {}
                        for k, v in self.model_call_details.items():
                            if (
                                k != "original_response"
                            ):  # copy.deepcopy raises errors as this could be a coroutine
                                kwargs[k] = v
                        kwargs["exception"] = exception

                        logfireLogger.log_event(
                            kwargs=kwargs,
                            response_obj=result,
                            start_time=start_time,
                            end_time=end_time,
                            level=LogfireLevel.ERROR.value,  # type: ignore
                            print_verbose=print_verbose,
                        )

                except Exception as e:
                    print_verbose(
                        f"LiteLLM.LoggingError: [Non-Blocking] Exception occurred while failure logging with integrations {str(e)}"
                    )
                    print_verbose(
                        f"LiteLLM.Logging: is sentry capture exception initialized {capture_exception}"
                    )
                    if capture_exception:  # log this error to sentry for debugging
                        capture_exception(e)
        except Exception as e:
            verbose_logger.exception(
                "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while failure logging {}".format(
                    str(e)
                )
            )

    async def async_failure_handler(
        self, exception, traceback_exception, start_time=None, end_time=None
    ):
        """
        Implementing async callbacks, to handle asyncio event loop issues when custom integrations need to use async functions.
        """
        await self.special_failure_handlers(exception=exception)
        if not self.should_run_logging(
            event_type="async_failure"
        ):  # prevent double logging
            return
        start_time, end_time = self._failure_handler_helper_fn(
            exception=exception,
            traceback_exception=traceback_exception,
            start_time=start_time,
            end_time=end_time,
        )

        callbacks = self.get_combined_callback_list(
            dynamic_success_callbacks=self.dynamic_async_failure_callbacks,
            global_callbacks=litellm._async_failure_callback,
        )

        result = None  # result sent to all loggers, init this to None incase it's not created

        self.has_run_logging(event_type="async_failure")
        for callback in callbacks:
            try:
                if isinstance(callback, CustomLogger):  # custom logger class
                    await callback.async_log_failure_event(
                        kwargs=self.model_call_details,
                        response_obj=result,
                        start_time=start_time,
                        end_time=end_time,
                    )  # type: ignore
                if (
                    callable(callback) and customLogger is not None
                ):  # custom logger functions
                    await customLogger.async_log_event(
                        kwargs=self.model_call_details,
                        response_obj=result,
                        start_time=start_time,
                        end_time=end_time,
                        print_verbose=print_verbose,
                        callback_func=callback,
                    )
            except Exception as e:
                verbose_logger.exception(
                    "LiteLLM.LoggingError: [Non-Blocking] Exception occurred while failure \
                        logging {}\nCallback={}".format(
                        str(e), callback
                    )
                )

    def _get_trace_id(self, service_name: Literal["langfuse"]) -> Optional[str]:
        """
        For the given service (e.g. langfuse), return the trace_id actually logged.

        Used for constructing the url in slack alerting.

        Returns:
            - str: The logged trace id
            - None: If trace id not yet emitted.
        """
        trace_id: Optional[str] = None
        if service_name == "langfuse":
            trace_id = in_memory_trace_id_cache.get_cache(
                litellm_call_id=self.litellm_call_id, service_name=service_name
            )

        return trace_id

    def _get_callback_object(self, service_name: Literal["langfuse"]) -> Optional[Any]:
        """
        Return dynamic callback object.

        Meant to solve issue when doing key-based/team-based logging
        """
        global langFuseLogger

        if service_name == "langfuse":
            if langFuseLogger is None or (
                (
                    self.standard_callback_dynamic_params.get("langfuse_public_key")
                    is not None
                    and self.standard_callback_dynamic_params.get("langfuse_public_key")
                    != langFuseLogger.public_key
                )
                or (
                    self.standard_callback_dynamic_params.get("langfuse_public_key")
                    is not None
                    and self.standard_callback_dynamic_params.get("langfuse_public_key")
                    != langFuseLogger.public_key
                )
                or (
                    self.standard_callback_dynamic_params.get("langfuse_host")
                    is not None
                    and self.standard_callback_dynamic_params.get("langfuse_host")
                    != langFuseLogger.langfuse_host
                )
            ):
                return LangFuseLogger(
                    langfuse_public_key=self.standard_callback_dynamic_params.get(
                        "langfuse_public_key"
                    ),
                    langfuse_secret=self.standard_callback_dynamic_params.get(
                        "langfuse_secret"
                    ),
                    langfuse_host=self.standard_callback_dynamic_params.get(
                        "langfuse_host"
                    ),
                )
            return langFuseLogger

        return None

    def handle_sync_success_callbacks_for_async_calls(
        self,
        result: Any,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ) -> None:
        """
        Handles calling success callbacks for Async calls.

        Why: Some callbacks - `langfuse`, `s3` are sync callbacks. We need to call them in the executor.
        """
        if self._should_run_sync_callbacks_for_async_calls() is False:
            return

        executor.submit(
            self.success_handler,
            result,
            start_time,
            end_time,
        )

    def _should_run_sync_callbacks_for_async_calls(self) -> bool:
        """
        Returns:
            - bool: True if sync callbacks should be run for async calls. eg. `langfuse`, `s3`
        """
        _combined_sync_callbacks = self.get_combined_callback_list(
            dynamic_success_callbacks=self.dynamic_success_callbacks,
            global_callbacks=litellm.success_callback,
        )
        _filtered_success_callbacks = self._remove_internal_custom_logger_callbacks(
            _combined_sync_callbacks
        )
        _filtered_success_callbacks = self._remove_internal_litellm_callbacks(
            _filtered_success_callbacks
        )
        return len(_filtered_success_callbacks) > 0

    def get_combined_callback_list(
        self, dynamic_success_callbacks: Optional[List], global_callbacks: List
    ) -> List:
        if dynamic_success_callbacks is None:
            return global_callbacks
        return list(set(dynamic_success_callbacks + global_callbacks))

    def _remove_internal_litellm_callbacks(self, callbacks: List) -> List:
        """
        Creates a filtered list of callbacks, excluding internal LiteLLM callbacks.

        Args:
            callbacks: List of callback functions/strings to filter

        Returns:
            List of filtered callbacks with internal ones removed
        """
        filtered = [
            cb for cb in callbacks if not self._is_internal_litellm_proxy_callback(cb)
        ]

        verbose_logger.debug(f"Filtered callbacks: {filtered}")
        return filtered

    def _get_callback_name(self, cb) -> str:
        """
        Helper to get the name of a callback function

        Args:
            cb: The callback function/string to get the name of

        Returns:
            The name of the callback
        """
        if hasattr(cb, "__name__"):
            return cb.__name__
        if hasattr(cb, "__func__"):
            return cb.__func__.__name__
        return str(cb)

    def _is_internal_litellm_proxy_callback(self, cb) -> bool:
        """Helper to check if a callback is internal"""
        INTERNAL_PREFIXES = [
            "_PROXY",
            "_service_logger.ServiceLogging",
            "sync_deployment_callback_on_success",
        ]
        if isinstance(cb, str):
            return False

        if not callable(cb):
            return True

        cb_name = self._get_callback_name(cb)
        return any(prefix in cb_name for prefix in INTERNAL_PREFIXES)

    def _remove_internal_custom_logger_callbacks(self, callbacks: List) -> List:
        """
        Removes internal custom logger callbacks from the list.
        """
        _new_callbacks = []
        for _c in callbacks:
            if isinstance(_c, CustomLogger):
                continue
            elif (
                isinstance(_c, str)
                and _c in litellm._known_custom_logger_compatible_callbacks
            ):
                continue
            _new_callbacks.append(_c)
        return _new_callbacks

    def _get_assembled_streaming_response(
        self,
        result: Union[
            ModelResponse,
            TextCompletionResponse,
            ModelResponseStream,
            ResponseCompletedEvent,
            Any,
        ],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        is_async: bool,
        streaming_chunks: List[Any],
    ) -> Optional[Union[ModelResponse, TextCompletionResponse, ResponsesAPIResponse]]:
        if isinstance(result, ModelResponse):
            return result
        elif isinstance(result, TextCompletionResponse):
            return result
        elif isinstance(result, ResponseCompletedEvent):
            return result.response
        return None

    def _handle_anthropic_messages_response_logging(self, result: Any) -> ModelResponse:
        """
        Handles logging for Anthropic messages responses.

        Args:
            result: The response object from the model call

        Returns:
            The the response object from the model call

        - For Non-streaming responses, we need to transform the response to a ModelResponse object.
        - For streaming responses, anthropic_messages handler calls success_handler with a assembled ModelResponse.
        """
        if self.stream and isinstance(result, ModelResponse):
            return result
        elif isinstance(result, ModelResponse):
            return result

        if "httpx_response" in self.model_call_details:
            result = litellm.AnthropicConfig().transform_response(
                raw_response=self.model_call_details.get("httpx_response", None),
                model_response=litellm.ModelResponse(),
                model=self.model,
                messages=[],
                logging_obj=self,
                optional_params={},
                api_key="",
                request_data={},
                encoding=litellm.encoding,
                json_mode=False,
                litellm_params={},
            )
        else:
            from litellm.types.llms.anthropic import AnthropicResponse

            pydantic_result = AnthropicResponse.model_validate(result)
            import httpx

            result = litellm.AnthropicConfig().transform_parsed_response(
                completion_response=pydantic_result.model_dump(),
                raw_response=httpx.Response(
                    status_code=200,
                    headers={},
                ),
                model_response=litellm.ModelResponse(),
                json_mode=None,
            )
        return result


def _get_masked_values(
    sensitive_object: dict,
    ignore_sensitive_values: bool = False,
    mask_all_values: bool = False,
    unmasked_length: int = 4,
    number_of_asterisks: Optional[int] = 4,
) -> dict:
    """
    Internal debugging helper function

    Masks the headers of the request sent from LiteLLM

    Args:
        masked_length: Optional length for the masked portion (number of *). If set, will use exactly this many *
                     regardless of original string length. The total length will be unmasked_length + masked_length.
    """
    sensitive_keywords = [
        "authorization",
        "token",
        "key",
        "secret",
    ]
    return {
        k: (
            (
                v[: unmasked_length // 2]
                + "*" * number_of_asterisks
                + v[-unmasked_length // 2 :]
            )
            if (
                isinstance(v, str)
                and len(v) > unmasked_length
                and number_of_asterisks is not None
            )
            else (
                (
                    v[: unmasked_length // 2]
                    + "*" * (len(v) - unmasked_length)
                    + v[-unmasked_length // 2 :]
                )
                if (isinstance(v, str) and len(v) > unmasked_length)
                else "*****"
            )
        )
        for k, v in sensitive_object.items()
        if not ignore_sensitive_values
        or not any(
            sensitive_keyword in k.lower() for sensitive_keyword in sensitive_keywords
        )
    }


def set_callbacks(callback_list, function_id=None):  # noqa: PLR0915
    """
    Globally sets the callback client
    """
    global sentry_sdk_instance, capture_exception, add_breadcrumb, posthog, slack_app, alerts_channel, traceloopLogger, athinaLogger, heliconeLogger, supabaseClient, lunaryLogger, promptLayerLogger, langFuseLogger, customLogger, weightsBiasesLogger, logfireLogger, dynamoLogger, s3Logger, dataDogLogger, prometheusLogger, greenscaleLogger, openMeterLogger, deepevalLogger

    try:
        for callback in callback_list:
            if callback == "sentry":
                try:
                    import sentry_sdk
                except ImportError:
                    print_verbose("Package 'sentry_sdk' is missing. Installing it...")
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", "sentry_sdk"]
                    )
                    import sentry_sdk
                sentry_sdk_instance = sentry_sdk
                sentry_trace_rate = (
                    os.environ.get("SENTRY_API_TRACE_RATE")
                    if "SENTRY_API_TRACE_RATE" in os.environ
                    else "1.0"
                )
                sentry_sample_rate = (
                    os.environ.get("SENTRY_API_SAMPLE_RATE")
                    if "SENTRY_API_SAMPLE_RATE" in os.environ
                    else "1.0"
                )
                sentry_sdk_instance.init(
                    dsn=os.environ.get("SENTRY_DSN"),
                    traces_sample_rate=float(sentry_trace_rate),  # type: ignore
                    sample_rate=float(
                        sentry_sample_rate if sentry_sample_rate else 1.0
                    ),
                )
                capture_exception = sentry_sdk_instance.capture_exception
                add_breadcrumb = sentry_sdk_instance.add_breadcrumb
            elif callback == "posthog":
                try:
                    from posthog import Posthog
                except ImportError:
                    print_verbose("Package 'posthog' is missing. Installing it...")
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", "posthog"]
                    )
                    from posthog import Posthog
                posthog = Posthog(
                    project_api_key=os.environ.get("POSTHOG_API_KEY"),
                    host=os.environ.get("POSTHOG_API_URL"),
                )
            elif callback == "slack":
                try:
                    from slack_bolt import App
                except ImportError:
                    print_verbose("Package 'slack_bolt' is missing. Installing it...")
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", "slack_bolt"]
                    )
                    from slack_bolt import App
                slack_app = App(
                    token=os.environ.get("SLACK_API_TOKEN"),
                    signing_secret=os.environ.get("SLACK_API_SECRET"),
                )
                alerts_channel = os.environ["SLACK_API_CHANNEL"]
                print_verbose(f"Initialized Slack App: {slack_app}")
            elif callback == "traceloop":
                traceloopLogger = TraceloopLogger()
            elif callback == "athina":
                athinaLogger = AthinaLogger()
                print_verbose("Initialized Athina Logger")
            elif callback == "helicone":
                heliconeLogger = HeliconeLogger()
            elif callback == "lunary":
                lunaryLogger = LunaryLogger()
            elif callback == "promptlayer":
                promptLayerLogger = PromptLayerLogger()
            elif callback == "langfuse":
                langFuseLogger = LangFuseLogger(
                    langfuse_public_key=None, langfuse_secret=None, langfuse_host=None
                )
            elif callback == "openmeter":
                openMeterLogger = OpenMeterLogger()
            elif callback == "datadog":
                dataDogLogger = DataDogLogger()
            elif callback == "dynamodb":
                dynamoLogger = DyanmoDBLogger()
            elif callback == "s3":
                s3Logger = S3Logger()
            elif callback == "wandb":
                weightsBiasesLogger = WeightsBiasesLogger()
            elif callback == "logfire":
                logfireLogger = LogfireLogger()
            elif callback == "supabase":
                print_verbose("instantiating supabase")
                supabaseClient = Supabase()
            elif callback == "greenscale":
                greenscaleLogger = GreenscaleLogger()
                print_verbose("Initialized Greenscale Logger")
            elif callable(callback):
                customLogger = CustomLogger()
    except Exception as e:
        raise e


def _init_custom_logger_compatible_class(  # noqa: PLR0915
    logging_integration: _custom_logger_compatible_callbacks_literal,
    internal_usage_cache: Optional[DualCache],
    llm_router: Optional[
        Any
    ],  # expect litellm.Router, but typing errors due to circular import
    custom_logger_init_args: Optional[dict] = {},
) -> Optional[CustomLogger]:
    """
    Initialize a custom logger compatible class
    """
    try:
        custom_logger_init_args = custom_logger_init_args or {}
        if logging_integration == "agentops":  # Add AgentOps initialization
            for callback in _in_memory_loggers:
                if isinstance(callback, AgentOps):
                    return callback  # type: ignore

            agentops_logger = AgentOps()
            _in_memory_loggers.append(agentops_logger)
            return agentops_logger  # type: ignore
        elif logging_integration == "lago":
            for callback in _in_memory_loggers:
                if isinstance(callback, LagoLogger):
                    return callback  # type: ignore

            lago_logger = LagoLogger()
            _in_memory_loggers.append(lago_logger)
            return lago_logger  # type: ignore
        elif logging_integration == "openmeter":
            for callback in _in_memory_loggers:
                if isinstance(callback, OpenMeterLogger):
                    return callback  # type: ignore

            _openmeter_logger = OpenMeterLogger()
            _in_memory_loggers.append(_openmeter_logger)
            return _openmeter_logger  # type: ignore
        elif logging_integration == "braintrust":
            for callback in _in_memory_loggers:
                if isinstance(callback, BraintrustLogger):
                    return callback  # type: ignore

            braintrust_logger = BraintrustLogger()
            _in_memory_loggers.append(braintrust_logger)
            return braintrust_logger  # type: ignore
        elif logging_integration == "langsmith":
            for callback in _in_memory_loggers:
                if isinstance(callback, LangsmithLogger):
                    return callback  # type: ignore

            _langsmith_logger = LangsmithLogger()
            _in_memory_loggers.append(_langsmith_logger)
            return _langsmith_logger  # type: ignore
        elif logging_integration == "argilla":
            for callback in _in_memory_loggers:
                if isinstance(callback, ArgillaLogger):
                    return callback  # type: ignore

            _argilla_logger = ArgillaLogger()
            _in_memory_loggers.append(_argilla_logger)
            return _argilla_logger  # type: ignore
        elif logging_integration == "literalai":
            for callback in _in_memory_loggers:
                if isinstance(callback, LiteralAILogger):
                    return callback  # type: ignore

            _literalai_logger = LiteralAILogger()
            _in_memory_loggers.append(_literalai_logger)
            return _literalai_logger  # type: ignore
        elif logging_integration == "prometheus":
            for callback in _in_memory_loggers:
                if isinstance(callback, PrometheusLogger):
                    return callback  # type: ignore

            _prometheus_logger = PrometheusLogger()
            _in_memory_loggers.append(_prometheus_logger)
            return _prometheus_logger  # type: ignore
        elif logging_integration == "datadog":
            for callback in _in_memory_loggers:
                if isinstance(callback, DataDogLogger):
                    return callback  # type: ignore

            _datadog_logger = DataDogLogger()
            _in_memory_loggers.append(_datadog_logger)
            return _datadog_logger  # type: ignore
        elif logging_integration == "datadog_llm_observability":
            _datadog_llm_obs_logger = DataDogLLMObsLogger()
            _in_memory_loggers.append(_datadog_llm_obs_logger)
            return _datadog_llm_obs_logger  # type: ignore
        elif logging_integration == "gcs_bucket":
            for callback in _in_memory_loggers:
                if isinstance(callback, GCSBucketLogger):
                    return callback  # type: ignore

            _gcs_bucket_logger = GCSBucketLogger()
            _in_memory_loggers.append(_gcs_bucket_logger)
            return _gcs_bucket_logger  # type: ignore
        elif logging_integration == "s3_v2":
            for callback in _in_memory_loggers:
                if isinstance(callback, S3V2Logger):
                    return callback  # type: ignore

            _s3_v2_logger = S3V2Logger()
            _in_memory_loggers.append(_s3_v2_logger)
            return _s3_v2_logger  # type: ignore
        elif logging_integration == "azure_storage":
            for callback in _in_memory_loggers:
                if isinstance(callback, AzureBlobStorageLogger):
                    return callback  # type: ignore

            _azure_storage_logger = AzureBlobStorageLogger()
            _in_memory_loggers.append(_azure_storage_logger)
            return _azure_storage_logger  # type: ignore
        elif logging_integration == "opik":
            for callback in _in_memory_loggers:
                if isinstance(callback, OpikLogger):
                    return callback  # type: ignore

            _opik_logger = OpikLogger()
            _in_memory_loggers.append(_opik_logger)
            return _opik_logger  # type: ignore
        elif logging_integration == "arize":
            from litellm.integrations.opentelemetry import (
                OpenTelemetry,
                OpenTelemetryConfig,
            )

            arize_config = ArizeLogger.get_arize_config()
            if arize_config.endpoint is None:
                raise ValueError(
                    "No valid endpoint found for Arize, please set 'ARIZE_ENDPOINT' to your GRPC endpoint or 'ARIZE_HTTP_ENDPOINT' to your HTTP endpoint"
                )
            otel_config = OpenTelemetryConfig(
                exporter=arize_config.protocol,
                endpoint=arize_config.endpoint,
            )

            os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = (
                f"space_id={arize_config.space_key},api_key={arize_config.api_key}"
            )
            for callback in _in_memory_loggers:
                if (
                    isinstance(callback, ArizeLogger)
                    and callback.callback_name == "arize"
                ):
                    return callback  # type: ignore
            _arize_otel_logger = ArizeLogger(config=otel_config, callback_name="arize")
            _in_memory_loggers.append(_arize_otel_logger)
            return _arize_otel_logger  # type: ignore
        elif logging_integration == "arize_phoenix":
            from litellm.integrations.opentelemetry import (
                OpenTelemetry,
                OpenTelemetryConfig,
            )

            arize_phoenix_config = ArizePhoenixLogger.get_arize_phoenix_config()
            otel_config = OpenTelemetryConfig(
                exporter=arize_phoenix_config.protocol,
                endpoint=arize_phoenix_config.endpoint,
            )

            # auth can be disabled on local deployments of arize phoenix
            if arize_phoenix_config.otlp_auth_headers is not None:
                os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = (
                    arize_phoenix_config.otlp_auth_headers
                )

            for callback in _in_memory_loggers:
                if (
                    isinstance(callback, OpenTelemetry)
                    and callback.callback_name == "arize_phoenix"
                ):
                    return callback  # type: ignore
            _otel_logger = OpenTelemetry(
                config=otel_config, callback_name="arize_phoenix"
            )
            _in_memory_loggers.append(_otel_logger)
            return _otel_logger  # type: ignore
        elif logging_integration == "otel":
            from litellm.integrations.opentelemetry import OpenTelemetry

            for callback in _in_memory_loggers:
                if isinstance(callback, OpenTelemetry):
                    return callback  # type: ignore
            otel_logger = OpenTelemetry(
                **_get_custom_logger_settings_from_proxy_server(
                    callback_name=logging_integration
                )
            )
            _in_memory_loggers.append(otel_logger)
            return otel_logger  # type: ignore

        elif logging_integration == "galileo":
            for callback in _in_memory_loggers:
                if isinstance(callback, GalileoObserve):
                    return callback  # type: ignore

            galileo_logger = GalileoObserve()
            _in_memory_loggers.append(galileo_logger)
            return galileo_logger  # type: ignore

        elif logging_integration == "deepeval":
            for callback in _in_memory_loggers:
                if isinstance(callback, DeepEvalLogger):
                    return callback  # type: ignore
            deepeval_logger = DeepEvalLogger()
            _in_memory_loggers.append(deepeval_logger)
            return deepeval_logger  # type: ignore

        elif logging_integration == "logfire":
            if "LOGFIRE_TOKEN" not in os.environ:
                raise ValueError("LOGFIRE_TOKEN not found in environment variables")
            from litellm.integrations.opentelemetry import (
                OpenTelemetry,
                OpenTelemetryConfig,
            )

            otel_config = OpenTelemetryConfig(
                exporter="otlp_http",
                endpoint="https://logfire-api.pydantic.dev/v1/traces",
                headers=f"Authorization={os.getenv('LOGFIRE_TOKEN')}",
            )
            for callback in _in_memory_loggers:
                if isinstance(callback, OpenTelemetry):
                    return callback  # type: ignore
            _otel_logger = OpenTelemetry(config=otel_config)
            _in_memory_loggers.append(_otel_logger)
            return _otel_logger  # type: ignore
        elif logging_integration == "dynamic_rate_limiter":
            from litellm.proxy.hooks.dynamic_rate_limiter import (
                _PROXY_DynamicRateLimitHandler,
            )

            for callback in _in_memory_loggers:
                if isinstance(callback, _PROXY_DynamicRateLimitHandler):
                    return callback  # type: ignore

            if internal_usage_cache is None:
                raise Exception(
                    "Internal Error: Cache cannot be empty - internal_usage_cache={}".format(
                        internal_usage_cache
                    )
                )

            dynamic_rate_limiter_obj = _PROXY_DynamicRateLimitHandler(
                internal_usage_cache=internal_usage_cache
            )

            if llm_router is not None and isinstance(llm_router, litellm.Router):
                dynamic_rate_limiter_obj.update_variables(llm_router=llm_router)
            _in_memory_loggers.append(dynamic_rate_limiter_obj)
            return dynamic_rate_limiter_obj  # type: ignore
        elif logging_integration == "langtrace":
            if "LANGTRACE_API_KEY" not in os.environ:
                raise ValueError("LANGTRACE_API_KEY not found in environment variables")

            from litellm.integrations.opentelemetry import (
                OpenTelemetry,
                OpenTelemetryConfig,
            )

            otel_config = OpenTelemetryConfig(
                exporter="otlp_http",
                endpoint="https://langtrace.ai/api/trace",
            )
            os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = (
                f"api_key={os.getenv('LANGTRACE_API_KEY')}"
            )
            for callback in _in_memory_loggers:
                if (
                    isinstance(callback, OpenTelemetry)
                    and callback.callback_name == "langtrace"
                ):
                    return callback  # type: ignore
            _otel_logger = OpenTelemetry(config=otel_config, callback_name="langtrace")
            _in_memory_loggers.append(_otel_logger)
            return _otel_logger  # type: ignore

        elif logging_integration == "mlflow":
            for callback in _in_memory_loggers:
                if isinstance(callback, MlflowLogger):
                    return callback  # type: ignore

            _mlflow_logger = MlflowLogger()
            _in_memory_loggers.append(_mlflow_logger)
            return _mlflow_logger  # type: ignore
        elif logging_integration == "langfuse":
            for callback in _in_memory_loggers:
                if isinstance(callback, LangfusePromptManagement):
                    return callback

            langfuse_logger = LangfusePromptManagement()
            _in_memory_loggers.append(langfuse_logger)
            return langfuse_logger  # type: ignore
        elif logging_integration == "langfuse_otel":
            from litellm.integrations.opentelemetry import (
                OpenTelemetry,
                OpenTelemetryConfig,
            )

            langfuse_otel_config = LangfuseOtelLogger.get_langfuse_otel_config()

            # The endpoint and headers are now set as environment variables by get_langfuse_otel_config()
            otel_config = OpenTelemetryConfig(
                exporter=langfuse_otel_config.protocol,
            )

            for callback in _in_memory_loggers:
                if (
                    isinstance(callback, OpenTelemetry)
                    and callback.callback_name == "langfuse_otel"
                ):
                    return callback  # type: ignore
            _otel_logger = OpenTelemetry(
                config=otel_config, callback_name="langfuse_otel"
            )
            _in_memory_loggers.append(_otel_logger)
            return _otel_logger  # type: ignore
        elif logging_integration == "pagerduty":
            for callback in _in_memory_loggers:
                if isinstance(callback, PagerDutyAlerting):
                    return callback
            pagerduty_logger = PagerDutyAlerting(**custom_logger_init_args)
            _in_memory_loggers.append(pagerduty_logger)
            return pagerduty_logger  # type: ignore
        elif logging_integration == "anthropic_cache_control_hook":
            for callback in _in_memory_loggers:
                if isinstance(callback, AnthropicCacheControlHook):
                    return callback
            anthropic_cache_control_hook = AnthropicCacheControlHook()
            _in_memory_loggers.append(anthropic_cache_control_hook)
            return anthropic_cache_control_hook  # type: ignore
        elif logging_integration == "bedrock_vector_store":
            for callback in _in_memory_loggers:
                if isinstance(callback, BedrockVectorStore):
                    return callback
            bedrock_vector_store = BedrockVectorStore()
            _in_memory_loggers.append(bedrock_vector_store)
            return bedrock_vector_store  # type: ignore
        elif logging_integration == "gcs_pubsub":
            for callback in _in_memory_loggers:
                if isinstance(callback, GcsPubSubLogger):
                    return callback
            _gcs_pubsub_logger = GcsPubSubLogger()
            _in_memory_loggers.append(_gcs_pubsub_logger)
            return _gcs_pubsub_logger  # type: ignore
        elif logging_integration == "generic_api":
            for callback in _in_memory_loggers:
                if isinstance(callback, GenericAPILogger):
                    return callback
            generic_api_logger = GenericAPILogger()
            _in_memory_loggers.append(generic_api_logger)
            return generic_api_logger  # type: ignore
        elif logging_integration == "resend_email":
            for callback in _in_memory_loggers:
                if isinstance(callback, ResendEmailLogger):
                    return callback
            resend_email_logger = ResendEmailLogger()
            _in_memory_loggers.append(resend_email_logger)
            return resend_email_logger  # type: ignore
        elif logging_integration == "smtp_email":
            for callback in _in_memory_loggers:
                if isinstance(callback, SMTPEmailLogger):
                    return callback
            smtp_email_logger = SMTPEmailLogger()
            _in_memory_loggers.append(smtp_email_logger)
            return smtp_email_logger  # type: ignore
        elif logging_integration == "humanloop":
            for callback in _in_memory_loggers:
                if isinstance(callback, HumanloopLogger):
                    return callback

            humanloop_logger = HumanloopLogger()
            _in_memory_loggers.append(humanloop_logger)
            return humanloop_logger  # type: ignore
    except Exception as e:
        verbose_logger.exception(
            f"[Non-Blocking Error] Error initializing custom logger: {e}"
        )
        return None


def get_custom_logger_compatible_class(  # noqa: PLR0915
    logging_integration: _custom_logger_compatible_callbacks_literal,
) -> Optional[CustomLogger]:
    try:
        if logging_integration == "lago":
            for callback in _in_memory_loggers:
                if isinstance(callback, LagoLogger):
                    return callback
        elif logging_integration == "openmeter":
            for callback in _in_memory_loggers:
                if isinstance(callback, OpenMeterLogger):
                    return callback
        elif logging_integration == "braintrust":
            for callback in _in_memory_loggers:
                if isinstance(callback, BraintrustLogger):
                    return callback
        elif logging_integration == "galileo":
            for callback in _in_memory_loggers:
                if isinstance(callback, GalileoObserve):
                    return callback
        elif logging_integration == "deepeval":
            for callback in _in_memory_loggers:
                if isinstance(callback, DeepEvalLogger):
                    return callback
        elif logging_integration == "langsmith":
            for callback in _in_memory_loggers:
                if isinstance(callback, LangsmithLogger):
                    return callback
        elif logging_integration == "argilla":
            for callback in _in_memory_loggers:
                if isinstance(callback, ArgillaLogger):
                    return callback
        elif logging_integration == "literalai":
            for callback in _in_memory_loggers:
                if isinstance(callback, LiteralAILogger):
                    return callback
        elif logging_integration == "prometheus":
            for callback in _in_memory_loggers:
                if isinstance(callback, PrometheusLogger):
                    return callback
        elif logging_integration == "datadog":
            for callback in _in_memory_loggers:
                if isinstance(callback, DataDogLogger):
                    return callback
        elif logging_integration == "datadog_llm_observability":
            for callback in _in_memory_loggers:
                if isinstance(callback, DataDogLLMObsLogger):
                    return callback
        elif logging_integration == "gcs_bucket":
            for callback in _in_memory_loggers:
                if isinstance(callback, GCSBucketLogger):
                    return callback
        elif logging_integration == "s3_v2":
            for callback in _in_memory_loggers:
                if isinstance(callback, S3V2Logger):
                    return callback
        elif logging_integration == "azure_storage":
            for callback in _in_memory_loggers:
                if isinstance(callback, AzureBlobStorageLogger):
                    return callback
        elif logging_integration == "opik":
            for callback in _in_memory_loggers:
                if isinstance(callback, OpikLogger):
                    return callback
        elif logging_integration == "langfuse":
            for callback in _in_memory_loggers:
                if isinstance(callback, LangfusePromptManagement):
                    return callback
        elif logging_integration == "otel":
            from litellm.integrations.opentelemetry import OpenTelemetry

            for callback in _in_memory_loggers:
                if isinstance(callback, OpenTelemetry):
                    return callback
        elif logging_integration == "arize":
            if "ARIZE_SPACE_KEY" not in os.environ:
                raise ValueError("ARIZE_SPACE_KEY not found in environment variables")
            if "ARIZE_API_KEY" not in os.environ:
                raise ValueError("ARIZE_API_KEY not found in environment variables")
            for callback in _in_memory_loggers:
                if (
                    isinstance(callback, ArizeLogger)
                    and callback.callback_name == "arize"
                ):
                    return callback
        elif logging_integration == "logfire":
            if "LOGFIRE_TOKEN" not in os.environ:
                raise ValueError("LOGFIRE_TOKEN not found in environment variables")
            from litellm.integrations.opentelemetry import OpenTelemetry

            for callback in _in_memory_loggers:
                if isinstance(callback, OpenTelemetry):
                    return callback  # type: ignore

        elif logging_integration == "dynamic_rate_limiter":
            from litellm.proxy.hooks.dynamic_rate_limiter import (
                _PROXY_DynamicRateLimitHandler,
            )

            for callback in _in_memory_loggers:
                if isinstance(callback, _PROXY_DynamicRateLimitHandler):
                    return callback  # type: ignore

        elif logging_integration == "langtrace":
            from litellm.integrations.opentelemetry import OpenTelemetry

            if "LANGTRACE_API_KEY" not in os.environ:
                raise ValueError("LANGTRACE_API_KEY not found in environment variables")

            for callback in _in_memory_loggers:
                if (
                    isinstance(callback, OpenTelemetry)
                    and callback.callback_name == "langtrace"
                ):
                    return callback

        elif logging_integration == "mlflow":
            for callback in _in_memory_loggers:
                if isinstance(callback, MlflowLogger):
                    return callback
        elif logging_integration == "pagerduty":
            for callback in _in_memory_loggers:
                if isinstance(callback, PagerDutyAlerting):
                    return callback
        elif logging_integration == "anthropic_cache_control_hook":
            for callback in _in_memory_loggers:
                if isinstance(callback, AnthropicCacheControlHook):
                    return callback
        elif logging_integration == "bedrock_vector_store":
            for callback in _in_memory_loggers:
                if isinstance(callback, BedrockVectorStore):
                    return callback
        elif logging_integration == "gcs_pubsub":
            for callback in _in_memory_loggers:
                if isinstance(callback, GcsPubSubLogger):
                    return callback
        elif logging_integration == "generic_api":
            for callback in _in_memory_loggers:
                if isinstance(callback, GenericAPILogger):
                    return callback
        elif logging_integration == "resend_email":
            for callback in _in_memory_loggers:
                if isinstance(callback, ResendEmailLogger):
                    return callback
        elif logging_integration == "smtp_email":
            for callback in _in_memory_loggers:
                if isinstance(callback, SMTPEmailLogger):
                    return callback
        return None

    except Exception as e:
        verbose_logger.exception(
            f"[Non-Blocking Error] Error getting custom logger: {e}"
        )
        return None


def _get_custom_logger_settings_from_proxy_server(callback_name: str) -> Dict:
    """
    Get the settings for a custom logger from the proxy server config.yaml

    Proxy server config.yaml defines callback_settings as:

    callback_settings:
        otel:
            message_logging: False
    """
    from litellm.proxy.proxy_server import callback_settings

    if callback_settings:
        return dict(callback_settings.get(callback_name, {}))
    return {}


def use_custom_pricing_for_model(litellm_params: Optional[dict]) -> bool:
    """
    Check if the model uses custom pricing

    Returns True if any of `SPECIAL_MODEL_INFO_PARAMS` are present in `litellm_params` or `model_info`
    """
    if litellm_params is None:
        return False

    metadata: dict = litellm_params.get("metadata", {}) or {}
    model_info: dict = metadata.get("model_info", {}) or {}

    custom_pricing_keys = CustomPricingLiteLLMParams.model_fields.keys()
    for key in custom_pricing_keys:
        if litellm_params.get(key, None) is not None:
            return True
        elif model_info.get(key, None) is not None:
            return True

    return False


def is_valid_sha256_hash(value: str) -> bool:
    # Check if the value is a valid SHA-256 hash (64 hexadecimal characters)
    return bool(re.fullmatch(r"[a-fA-F0-9]{64}", value))


class StandardLoggingPayloadSetup:
    @staticmethod
    def cleanup_timestamps(
        start_time: Union[dt_object, float],
        end_time: Union[dt_object, float],
        completion_start_time: Union[dt_object, float],
    ) -> Tuple[float, float, float]:
        """
        Convert datetime objects to floats

        Args:
            start_time: Union[dt_object, float]
            end_time: Union[dt_object, float]
            completion_start_time: Union[dt_object, float]

        Returns:
            Tuple[float, float, float]: A tuple containing the start time, end time, and completion start time as floats.
        """

        if isinstance(start_time, datetime.datetime):
            start_time_float = start_time.timestamp()
        elif isinstance(start_time, float):
            start_time_float = start_time
        else:
            raise ValueError(
                f"start_time is required, got={start_time} of type {type(start_time)}"
            )

        if isinstance(end_time, datetime.datetime):
            end_time_float = end_time.timestamp()
        elif isinstance(end_time, float):
            end_time_float = end_time
        else:
            raise ValueError(
                f"end_time is required, got={end_time} of type {type(end_time)}"
            )

        if isinstance(completion_start_time, datetime.datetime):
            completion_start_time_float = completion_start_time.timestamp()
        elif isinstance(completion_start_time, float):
            completion_start_time_float = completion_start_time
        else:
            completion_start_time_float = end_time_float

        return start_time_float, end_time_float, completion_start_time_float

    @staticmethod
    def get_standard_logging_metadata(
        metadata: Optional[Dict[str, Any]],
        litellm_params: Optional[dict] = None,
        prompt_integration: Optional[str] = None,
        applied_guardrails: Optional[List[str]] = None,
        mcp_tool_call_metadata: Optional[StandardLoggingMCPToolCall] = None,
        vector_store_request_metadata: Optional[
            List[StandardLoggingVectorStoreRequest]
        ] = None,
        usage_object: Optional[dict] = None,
        proxy_server_request: Optional[dict] = None,
    ) -> StandardLoggingMetadata:
        """
        Clean and filter the metadata dictionary to include only the specified keys in StandardLoggingMetadata.

        Args:
            metadata (Optional[Dict[str, Any]]): The original metadata dictionary.

        Returns:
            StandardLoggingMetadata: A StandardLoggingMetadata object containing the cleaned metadata.

        Note:
            - If the input metadata is None or not a dictionary, an empty StandardLoggingMetadata object is returned.
            - If 'user_api_key' is present in metadata and is a valid SHA256 hash, it's stored as 'user_api_key_hash'.
        """

        prompt_management_metadata: Optional[
            StandardLoggingPromptManagementMetadata
        ] = None
        if litellm_params is not None:
            prompt_id = cast(Optional[str], litellm_params.get("prompt_id", None))
            prompt_variables = cast(
                Optional[dict], litellm_params.get("prompt_variables", None)
            )

            if prompt_id is not None and prompt_integration is not None:
                prompt_management_metadata = StandardLoggingPromptManagementMetadata(
                    prompt_id=prompt_id,
                    prompt_variables=prompt_variables,
                    prompt_integration=prompt_integration,
                )

        # Initialize with default values
        clean_metadata = StandardLoggingMetadata(
            user_api_key_hash=None,
            user_api_key_alias=None,
            user_api_key_team_id=None,
            user_api_key_org_id=None,
            user_api_key_user_id=None,
            user_api_key_team_alias=None,
            user_api_key_user_email=None,
            spend_logs_metadata=None,
            requester_ip_address=None,
            requester_metadata=None,
            user_api_key_end_user_id=None,
            prompt_management_metadata=prompt_management_metadata,
            applied_guardrails=applied_guardrails,
            mcp_tool_call_metadata=mcp_tool_call_metadata,
            vector_store_request_metadata=vector_store_request_metadata,
            usage_object=usage_object,
            requester_custom_headers=None,
            user_api_key_request_route=None,
        )
        if isinstance(metadata, dict):
            # Filter the metadata dictionary to include only the specified keys
            supported_keys = StandardLoggingMetadata.__annotations__.keys()
            for key in supported_keys:
                if key in metadata:
                    clean_metadata[key] = metadata[key]  # type: ignore

            if metadata.get("user_api_key") is not None:
                if is_valid_sha256_hash(str(metadata.get("user_api_key"))):
                    clean_metadata["user_api_key_hash"] = metadata.get(
                        "user_api_key"
                    )  # this is the hash
            _potential_requester_metadata = metadata.get(
                "metadata", None
            )  # check if user passed metadata in the sdk request - e.g. metadata for langsmith logging - https://docs.litellm.ai/docs/observability/langsmith_integration#set-langsmith-fields
            if (
                clean_metadata["requester_metadata"] is None
                and _potential_requester_metadata is not None
                and isinstance(_potential_requester_metadata, dict)
            ):
                clean_metadata["requester_metadata"] = _potential_requester_metadata

        if (
            EnterpriseStandardLoggingPayloadSetupVAR
            and proxy_server_request is not None
        ):
            clean_metadata = EnterpriseStandardLoggingPayloadSetupVAR.apply_enterprise_specific_metadata(
                standard_logging_metadata=clean_metadata,
                proxy_server_request=proxy_server_request,
            )

        return clean_metadata

    @staticmethod
    def get_usage_from_response_obj(
        response_obj: Optional[dict], combined_usage_object: Optional[Usage] = None
    ) -> Usage:
        ## BASE CASE ##
        if combined_usage_object is not None:
            return combined_usage_object
        if response_obj is None:
            return Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )

        usage = response_obj.get("usage", None) or {}
        if usage is None or (
            not isinstance(usage, dict) and not isinstance(usage, Usage)
        ):
            return Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )
        elif isinstance(usage, Usage):
            return usage
        elif isinstance(usage, dict):
            if ResponseAPILoggingUtils._is_response_api_usage(usage):
                return (
                    ResponseAPILoggingUtils._transform_response_api_usage_to_chat_usage(
                        usage
                    )
                )
            return Usage(**usage)

        raise ValueError(f"usage is required, got={usage} of type {type(usage)}")

    @staticmethod
    def get_model_cost_information(
        base_model: Optional[str],
        custom_pricing: Optional[bool],
        custom_llm_provider: Optional[str],
        init_response_obj: Union[Any, BaseModel, dict],
    ) -> StandardLoggingModelInformation:
        model_cost_name = _select_model_name_for_cost_calc(
            model=None,
            completion_response=init_response_obj,  # type: ignore
            base_model=base_model,
            custom_pricing=custom_pricing,
        )
        if model_cost_name is None:
            model_cost_information = StandardLoggingModelInformation(
                model_map_key="", model_map_value=None
            )
        else:
            try:
                _model_cost_information = litellm.get_model_info(
                    model=model_cost_name, custom_llm_provider=custom_llm_provider
                )
                model_cost_information = StandardLoggingModelInformation(
                    model_map_key=model_cost_name,
                    model_map_value=_model_cost_information,
                )
            except Exception:
                verbose_logger.debug(  # keep in debug otherwise it will trigger on every call
                    "Model={} is not mapped in model cost map. Defaulting to None model_cost_information for standard_logging_payload".format(
                        model_cost_name
                    )
                )
                model_cost_information = StandardLoggingModelInformation(
                    model_map_key=model_cost_name, model_map_value=None
                )
        return model_cost_information

    @staticmethod
    def get_final_response_obj(
        response_obj: dict, init_response_obj: Union[Any, BaseModel, dict], kwargs: dict
    ) -> Optional[Union[dict, str, list]]:
        """
        Get final response object after redacting the message input/output from logging
        """
        if response_obj is not None:
            final_response_obj: Optional[Union[dict, str, list]] = response_obj
        elif isinstance(init_response_obj, list) or isinstance(init_response_obj, str):
            final_response_obj = init_response_obj
        else:
            final_response_obj = None

        modified_final_response_obj = redact_message_input_output_from_logging(
            model_call_details=kwargs,
            result=final_response_obj,
        )

        if modified_final_response_obj is not None and isinstance(
            modified_final_response_obj, BaseModel
        ):
            final_response_obj = modified_final_response_obj.model_dump()
        else:
            final_response_obj = modified_final_response_obj

        return final_response_obj

    @staticmethod
    def get_additional_headers(
        additiona_headers: Optional[dict],
    ) -> Optional[StandardLoggingAdditionalHeaders]:
        if additiona_headers is None:
            return None

        additional_logging_headers: StandardLoggingAdditionalHeaders = {}

        for key in StandardLoggingAdditionalHeaders.__annotations__.keys():
            _key = key.lower()
            _key = _key.replace("_", "-")
            if _key in additiona_headers:
                try:
                    additional_logging_headers[key] = int(additiona_headers[_key])  # type: ignore
                except (ValueError, TypeError):
                    verbose_logger.debug(
                        f"Could not convert {additiona_headers[_key]} to int for key {key}."
                    )
        return additional_logging_headers

    @staticmethod
    def get_hidden_params(
        hidden_params: Optional[dict],
    ) -> StandardLoggingHiddenParams:
        clean_hidden_params = StandardLoggingHiddenParams(
            model_id=None,
            cache_key=None,
            api_base=None,
            response_cost=None,
            additional_headers=None,
            litellm_overhead_time_ms=None,
            batch_models=None,
            litellm_model_name=None,
            usage_object=None,
        )
        if hidden_params is not None:
            for key in StandardLoggingHiddenParams.__annotations__.keys():
                if key in hidden_params:
                    if key == "additional_headers":
                        clean_hidden_params["additional_headers"] = (
                            StandardLoggingPayloadSetup.get_additional_headers(
                                hidden_params[key]
                            )
                        )
                    else:
                        clean_hidden_params[key] = hidden_params[key]  # type: ignore
        return clean_hidden_params

    @staticmethod
    def strip_trailing_slash(api_base: Optional[str]) -> Optional[str]:
        if api_base:
            return api_base.rstrip("/")
        return api_base

    @staticmethod
    def get_error_information(
        original_exception: Optional[Exception],
        traceback_str: Optional[str] = None,
    ) -> StandardLoggingPayloadErrorInformation:
        from litellm.constants import MAXIMUM_TRACEBACK_LINES_TO_LOG

        error_status: str = str(getattr(original_exception, "status_code", ""))
        error_class: str = (
            str(original_exception.__class__.__name__) if original_exception else ""
        )
        _llm_provider_in_exception = getattr(original_exception, "llm_provider", "")

        # Get traceback information (first 100 lines)
        traceback_info = traceback_str or ""
        if original_exception:
            tb = getattr(original_exception, "__traceback__", None)
            if tb:
                tb_lines = traceback.format_tb(tb)
                traceback_info += "".join(
                    tb_lines[:MAXIMUM_TRACEBACK_LINES_TO_LOG]
                )  # Limit to first 100 lines

        # Get additional error details
        error_message = str(original_exception)

        return StandardLoggingPayloadErrorInformation(
            error_code=error_status,
            error_class=error_class,
            llm_provider=_llm_provider_in_exception,
            traceback=traceback_info,
            error_message=error_message if original_exception else "",
        )

    @staticmethod
    def get_response_time(
        start_time_float: float,
        end_time_float: float,
        completion_start_time_float: float,
        stream: bool,
    ) -> float:
        """
        Get the response time for the LLM response

        Args:
            start_time_float: float - start time of the LLM call
            end_time_float: float - end time of the LLM call
            completion_start_time_float: float - time to first token of the LLM response (for streaming responses)
            stream: bool - True when a stream response is returned

        Returns:
            float: The response time for the LLM response
        """
        if stream is True:
            return completion_start_time_float - start_time_float
        else:
            return end_time_float - start_time_float

    @staticmethod
    def _get_standard_logging_payload_trace_id(
        logging_obj: Logging,
        litellm_params: dict,
    ) -> str:
        """
        Returns the `litellm_trace_id` for this request

        This helps link sessions when multiple requests are made in a single session
        """
        dynamic_litellm_session_id = litellm_params.get("litellm_session_id")
        dynamic_litellm_trace_id = litellm_params.get("litellm_trace_id")

        # Note: we recommend using `litellm_session_id` for session tracking
        # `litellm_trace_id` is an internal litellm param
        if dynamic_litellm_session_id:
            return str(dynamic_litellm_session_id)
        elif dynamic_litellm_trace_id:
            return str(dynamic_litellm_trace_id)
        else:
            return logging_obj.litellm_trace_id

    @staticmethod
    def _get_user_agent_tags(proxy_server_request: dict) -> Optional[List[str]]:
        """
        Return the user agent tags from the proxy server request for spend tracking
        """
        if litellm.disable_add_user_agent_to_request_tags is True:
            return None
        user_agent_tags: Optional[List[str]] = None
        headers = proxy_server_request.get("headers", {})
        if headers is not None and isinstance(headers, dict):
            if "user-agent" in headers:
                user_agent = headers["user-agent"]
                if user_agent is not None:
                    if user_agent_tags is None:
                        user_agent_tags = []
                    user_agent_part: Optional[str] = None
                    if "/" in user_agent:
                        user_agent_part = user_agent.split("/")[0]
                    if user_agent_part is not None:
                        user_agent_tags.append("User-Agent: " + user_agent_part)
                    if user_agent is not None:
                        user_agent_tags.append("User-Agent: " + user_agent)
        return user_agent_tags

    @staticmethod
    def _get_request_tags(metadata: dict, proxy_server_request: dict) -> List[str]:
        request_tags = (
            metadata.get("tags", [])
            if isinstance(metadata.get("tags", []), list)
            else []
        )
        user_agent_tags = StandardLoggingPayloadSetup._get_user_agent_tags(
            proxy_server_request
        )
        if user_agent_tags is not None:
            request_tags.extend(user_agent_tags)
        return request_tags


def get_standard_logging_object_payload(
    kwargs: Optional[dict],
    init_response_obj: Union[Any, BaseModel, dict],
    start_time: dt_object,
    end_time: dt_object,
    logging_obj: Logging,
    status: StandardLoggingPayloadStatus,
    error_str: Optional[str] = None,
    original_exception: Optional[Exception] = None,
    standard_built_in_tools_params: Optional[StandardBuiltInToolsParams] = None,
) -> Optional[StandardLoggingPayload]:
    try:
        kwargs = kwargs or {}

        hidden_params: Optional[dict] = None
        if init_response_obj is None:
            response_obj = {}
        elif isinstance(init_response_obj, BaseModel):
            response_obj = init_response_obj.model_dump()
            hidden_params = getattr(init_response_obj, "_hidden_params", None)
        elif isinstance(init_response_obj, dict):
            response_obj = init_response_obj
        else:
            response_obj = {}

        if original_exception is not None and hidden_params is None:
            response_headers = _get_response_headers(original_exception)
            if response_headers is not None:
                hidden_params = dict(
                    StandardLoggingHiddenParams(
                        additional_headers=StandardLoggingPayloadSetup.get_additional_headers(
                            dict(response_headers)
                        ),
                        model_id=None,
                        cache_key=None,
                        api_base=None,
                        response_cost=None,
                        litellm_overhead_time_ms=None,
                        batch_models=None,
                        litellm_model_name=None,
                        usage_object=None,
                    )
                )

        # standardize this function to be used across, s3, dynamoDB, langfuse logging
        litellm_params = kwargs.get("litellm_params", {})
        proxy_server_request = litellm_params.get("proxy_server_request") or {}

        metadata: dict = (
            litellm_params.get("litellm_metadata")
            or litellm_params.get("metadata", None)
            or {}
        )

        completion_start_time = kwargs.get("completion_start_time", end_time)
        call_type = kwargs.get("call_type")
        cache_hit = kwargs.get("cache_hit", False)
        usage = StandardLoggingPayloadSetup.get_usage_from_response_obj(
            response_obj=response_obj,
            combined_usage_object=cast(
                Optional[Usage], kwargs.get("combined_usage_object")
            ),
        )

        id = response_obj.get("id", kwargs.get("litellm_call_id"))

        _model_id = metadata.get("model_info", {}).get("id", "")
        _model_group = metadata.get("model_group", "")

        request_tags = StandardLoggingPayloadSetup._get_request_tags(
            metadata=metadata, proxy_server_request=proxy_server_request
        )

        # cleanup timestamps
        (
            start_time_float,
            end_time_float,
            completion_start_time_float,
        ) = StandardLoggingPayloadSetup.cleanup_timestamps(
            start_time=start_time,
            end_time=end_time,
            completion_start_time=completion_start_time,
        )
        response_time = StandardLoggingPayloadSetup.get_response_time(
            start_time_float=start_time_float,
            end_time_float=end_time_float,
            completion_start_time_float=completion_start_time_float,
            stream=kwargs.get("stream", False),
        )
        # clean up litellm hidden params
        clean_hidden_params = StandardLoggingPayloadSetup.get_hidden_params(
            hidden_params
        )

        # clean up litellm metadata
        clean_metadata = StandardLoggingPayloadSetup.get_standard_logging_metadata(
            metadata=metadata,
            litellm_params=litellm_params,
            prompt_integration=kwargs.get("prompt_integration", None),
            applied_guardrails=kwargs.get("applied_guardrails", None),
            mcp_tool_call_metadata=kwargs.get("mcp_tool_call_metadata", None),
            vector_store_request_metadata=kwargs.get(
                "vector_store_request_metadata", None
            ),
            usage_object=usage.model_dump(),
            proxy_server_request=proxy_server_request,
        )

        _request_body = proxy_server_request.get("body", {})
        end_user_id = clean_metadata["user_api_key_end_user_id"] or _request_body.get(
            "user", None
        )  # maintain backwards compatibility with old request body check

        saved_cache_cost: float = 0.0
        if cache_hit is True:
            id = f"{id}_cache_hit{time.time()}"  # do not duplicate the request id
            saved_cache_cost = (
                logging_obj._response_cost_calculator(
                    result=init_response_obj, cache_hit=False  # type: ignore
                )
                or 0.0
            )

        ## Get model cost information ##
        base_model = _get_base_model_from_metadata(model_call_details=kwargs)
        custom_pricing = use_custom_pricing_for_model(litellm_params=litellm_params)

        model_cost_information = StandardLoggingPayloadSetup.get_model_cost_information(
            base_model=base_model,
            custom_pricing=custom_pricing,
            custom_llm_provider=kwargs.get("custom_llm_provider"),
            init_response_obj=init_response_obj,
        )
        response_cost: float = kwargs.get("response_cost", 0) or 0.0

        error_information = StandardLoggingPayloadSetup.get_error_information(
            original_exception=original_exception,
        )

        ## get final response object ##
        final_response_obj = StandardLoggingPayloadSetup.get_final_response_obj(
            response_obj=response_obj,
            init_response_obj=init_response_obj,
            kwargs=kwargs,
        )

        stream: Optional[bool] = None
        if (
            kwargs.get("complete_streaming_response") is not None
            or kwargs.get("async_complete_streaming_response") is not None
        ) and kwargs.get("stream") is True:
            stream = True

        payload: StandardLoggingPayload = StandardLoggingPayload(
            id=str(id),
            trace_id=StandardLoggingPayloadSetup._get_standard_logging_payload_trace_id(
                logging_obj=logging_obj,
                litellm_params=litellm_params,
            ),
            call_type=call_type or "",
            cache_hit=cache_hit,
            stream=stream,
            status=status,
            custom_llm_provider=cast(Optional[str], kwargs.get("custom_llm_provider")),
            saved_cache_cost=saved_cache_cost,
            startTime=start_time_float,
            endTime=end_time_float,
            completionStartTime=completion_start_time_float,
            response_time=response_time,
            model=kwargs.get("model", "") or "",
            metadata=clean_metadata,
            cache_key=clean_hidden_params["cache_key"],
            response_cost=response_cost,
            total_tokens=usage.total_tokens,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            request_tags=request_tags,
            end_user=end_user_id or "",
            api_base=StandardLoggingPayloadSetup.strip_trailing_slash(
                litellm_params.get("api_base", "")
            )
            or "",
            model_group=_model_group,
            model_id=_model_id,
            requester_ip_address=clean_metadata.get("requester_ip_address", None),
            messages=kwargs.get("messages"),
            response=final_response_obj,
            model_parameters=ModelParamHelper.get_standard_logging_model_parameters(
                kwargs.get("optional_params", None) or {}
            ),
            hidden_params=clean_hidden_params,
            model_map_information=model_cost_information,
            error_str=error_str,
            error_information=error_information,
            response_cost_failure_debug_info=kwargs.get(
                "response_cost_failure_debug_information"
            ),
            guardrail_information=metadata.get(
                "standard_logging_guardrail_information", None
            ),
            standard_built_in_tools_params=standard_built_in_tools_params,
        )

        emit_standard_logging_payload(payload)
        return payload
    except Exception as e:
        verbose_logger.exception(
            "Error creating standard logging object - {}".format(str(e))
        )
        return None


def emit_standard_logging_payload(payload: StandardLoggingPayload):
    if os.getenv("LITELLM_PRINT_STANDARD_LOGGING_PAYLOAD"):
        verbose_logger.info(json.dumps(payload, indent=4))


def get_standard_logging_metadata(
    metadata: Optional[Dict[str, Any]],
) -> StandardLoggingMetadata:
    """
    Clean and filter the metadata dictionary to include only the specified keys in StandardLoggingMetadata.

    Args:
        metadata (Optional[Dict[str, Any]]): The original metadata dictionary.

    Returns:
        StandardLoggingMetadata: A StandardLoggingMetadata object containing the cleaned metadata.

    Note:
        - If the input metadata is None or not a dictionary, an empty StandardLoggingMetadata object is returned.
        - If 'user_api_key' is present in metadata and is a valid SHA256 hash, it's stored as 'user_api_key_hash'.
    """
    # Initialize with default values
    clean_metadata = StandardLoggingMetadata(
        user_api_key_hash=None,
        user_api_key_alias=None,
        user_api_key_team_id=None,
        user_api_key_org_id=None,
        user_api_key_user_id=None,
        user_api_key_user_email=None,
        user_api_key_team_alias=None,
        spend_logs_metadata=None,
        requester_ip_address=None,
        requester_metadata=None,
        user_api_key_end_user_id=None,
        prompt_management_metadata=None,
        applied_guardrails=None,
        mcp_tool_call_metadata=None,
        vector_store_request_metadata=None,
        usage_object=None,
        requester_custom_headers=None,
        user_api_key_request_route=None,
    )
    if isinstance(metadata, dict):
        # Filter the metadata dictionary to include only the specified keys
        clean_metadata = StandardLoggingMetadata(
            **{  # type: ignore
                key: metadata[key]
                for key in StandardLoggingMetadata.__annotations__.keys()
                if key in metadata
            }
        )

        if metadata.get("user_api_key") is not None:
            if is_valid_sha256_hash(str(metadata.get("user_api_key"))):
                clean_metadata["user_api_key_hash"] = metadata.get(
                    "user_api_key"
                )  # this is the hash
    return clean_metadata


def scrub_sensitive_keys_in_metadata(litellm_params: Optional[dict]):
    if litellm_params is None:
        litellm_params = {}

    metadata = litellm_params.get("metadata", {}) or {}

    ## check user_api_key_metadata for sensitive logging keys
    cleaned_user_api_key_metadata = {}
    if "user_api_key_metadata" in metadata and isinstance(
        metadata["user_api_key_metadata"], dict
    ):
        for k, v in metadata["user_api_key_metadata"].items():
            if k == "logging":  # prevent logging user logging keys
                cleaned_user_api_key_metadata[k] = (
                    "scrubbed_by_litellm_for_sensitive_keys"
                )
            else:
                cleaned_user_api_key_metadata[k] = v

        metadata["user_api_key_metadata"] = cleaned_user_api_key_metadata
        litellm_params["metadata"] = metadata

    return litellm_params


# integration helper function
def modify_integration(integration_name, integration_params):
    global supabaseClient
    if integration_name == "supabase":
        if "table_name" in integration_params:
            Supabase.supabase_table_name = integration_params["table_name"]


@lru_cache(maxsize=16)
def _get_traceback_str_for_error(error_str: str) -> str:
    """
    function wrapped with lru_cache to limit the number of times `traceback.format_exc()` is called
    """
    return traceback.format_exc()


from decimal import Decimal

# used for unit testing
from typing import Any, Dict, List, Optional, Union


def create_dummy_standard_logging_payload() -> StandardLoggingPayload:
    # First create the nested objects with proper typing
    model_info = StandardLoggingModelInformation(
        model_map_key="gpt-3.5-turbo", model_map_value=None
    )

    metadata = StandardLoggingMetadata(  # type: ignore
        user_api_key_hash=str("test_hash"),
        user_api_key_alias=str("test_alias"),
        user_api_key_team_id=str("test_team"),
        user_api_key_user_id=str("test_user"),
        user_api_key_team_alias=str("test_team_alias"),
        user_api_key_org_id=None,
        spend_logs_metadata=None,
        requester_ip_address=str("127.0.0.1"),
        requester_metadata=None,
        user_api_key_end_user_id=str("test_end_user"),
    )

    hidden_params = StandardLoggingHiddenParams(
        model_id=None,
        cache_key=None,
        api_base=None,
        response_cost=None,
        additional_headers=None,
        litellm_overhead_time_ms=None,
        batch_models=None,
        litellm_model_name=None,
        usage_object=None,
    )

    # Convert numeric values to appropriate types
    response_cost = Decimal("0.1")
    start_time = Decimal("1234567890.0")
    end_time = Decimal("1234567891.0")
    completion_start_time = Decimal("1234567890.5")
    saved_cache_cost = Decimal("0.0")

    # Create messages and response with proper typing
    messages: List[Dict[str, str]] = [{"role": "user", "content": "Hello, world!"}]
    response: Dict[str, List[Dict[str, Dict[str, str]]]] = {
        "choices": [{"message": {"content": "Hi there!"}}]
    }

    # Main payload initialization
    return StandardLoggingPayload(  # type: ignore
        id=str("test_id"),
        call_type=str("completion"),
        stream=bool(False),
        response_cost=response_cost,
        response_cost_failure_debug_info=None,
        status=str("success"),
        total_tokens=int(
            DEFAULT_MOCK_RESPONSE_PROMPT_TOKEN_COUNT
            + DEFAULT_MOCK_RESPONSE_COMPLETION_TOKEN_COUNT
        ),
        prompt_tokens=int(DEFAULT_MOCK_RESPONSE_PROMPT_TOKEN_COUNT),
        completion_tokens=int(DEFAULT_MOCK_RESPONSE_COMPLETION_TOKEN_COUNT),
        startTime=start_time,
        endTime=end_time,
        completionStartTime=completion_start_time,
        model_map_information=model_info,
        model=str("gpt-3.5-turbo"),
        model_id=str("model-123"),
        model_group=str("openai-gpt"),
        custom_llm_provider=str("openai"),
        api_base=str("https://api.openai.com"),
        metadata=metadata,
        cache_hit=bool(False),
        cache_key=None,
        saved_cache_cost=saved_cache_cost,
        request_tags=[],
        end_user=None,
        requester_ip_address=str("127.0.0.1"),
        messages=messages,
        response=response,
        error_str=None,
        model_parameters={"stream": True},
        hidden_params=hidden_params,
    )

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\idna\idnadata.py ===
# This file is automatically generated by tools/idna-data

__version__ = "15.1.0"
scripts = {
    "Greek": (
        0x37000000374,
        0x37500000378,
        0x37A0000037E,
        0x37F00000380,
        0x38400000385,
        0x38600000387,
        0x3880000038B,
        0x38C0000038D,
        0x38E000003A2,
        0x3A3000003E2,
        0x3F000000400,
        0x1D2600001D2B,
        0x1D5D00001D62,
        0x1D6600001D6B,
        0x1DBF00001DC0,
        0x1F0000001F16,
        0x1F1800001F1E,
        0x1F2000001F46,
        0x1F4800001F4E,
        0x1F5000001F58,
        0x1F5900001F5A,
        0x1F5B00001F5C,
        0x1F5D00001F5E,
        0x1F5F00001F7E,
        0x1F8000001FB5,
        0x1FB600001FC5,
        0x1FC600001FD4,
        0x1FD600001FDC,
        0x1FDD00001FF0,
        0x1FF200001FF5,
        0x1FF600001FFF,
        0x212600002127,
        0xAB650000AB66,
        0x101400001018F,
        0x101A0000101A1,
        0x1D2000001D246,
    ),
    "Han": (
        0x2E8000002E9A,
        0x2E9B00002EF4,
        0x2F0000002FD6,
        0x300500003006,
        0x300700003008,
        0x30210000302A,
        0x30380000303C,
        0x340000004DC0,
        0x4E000000A000,
        0xF9000000FA6E,
        0xFA700000FADA,
        0x16FE200016FE4,
        0x16FF000016FF2,
        0x200000002A6E0,
        0x2A7000002B73A,
        0x2B7400002B81E,
        0x2B8200002CEA2,
        0x2CEB00002EBE1,
        0x2EBF00002EE5E,
        0x2F8000002FA1E,
        0x300000003134B,
        0x31350000323B0,
    ),
    "Hebrew": (
        0x591000005C8,
        0x5D0000005EB,
        0x5EF000005F5,
        0xFB1D0000FB37,
        0xFB380000FB3D,
        0xFB3E0000FB3F,
        0xFB400000FB42,
        0xFB430000FB45,
        0xFB460000FB50,
    ),
    "Hiragana": (
        0x304100003097,
        0x309D000030A0,
        0x1B0010001B120,
        0x1B1320001B133,
        0x1B1500001B153,
        0x1F2000001F201,
    ),
    "Katakana": (
        0x30A1000030FB,
        0x30FD00003100,
        0x31F000003200,
        0x32D0000032FF,
        0x330000003358,
        0xFF660000FF70,
        0xFF710000FF9E,
        0x1AFF00001AFF4,
        0x1AFF50001AFFC,
        0x1AFFD0001AFFF,
        0x1B0000001B001,
        0x1B1200001B123,
        0x1B1550001B156,
        0x1B1640001B168,
    ),
}
joining_types = {
    0xAD: 84,
    0x300: 84,
    0x301: 84,
    0x302: 84,
    0x303: 84,
    0x304: 84,
    0x305: 84,
    0x306: 84,
    0x307: 84,
    0x308: 84,
    0x309: 84,
    0x30A: 84,
    0x30B: 84,
    0x30C: 84,
    0x30D: 84,
    0x30E: 84,
    0x30F: 84,
    0x310: 84,
    0x311: 84,
    0x312: 84,
    0x313: 84,
    0x314: 84,
    0x315: 84,
    0x316: 84,
    0x317: 84,
    0x318: 84,
    0x319: 84,
    0x31A: 84,
    0x31B: 84,
    0x31C: 84,
    0x31D: 84,
    0x31E: 84,
    0x31F: 84,
    0x320: 84,
    0x321: 84,
    0x322: 84,
    0x323: 84,
    0x324: 84,
    0x325: 84,
    0x326: 84,
    0x327: 84,
    0x328: 84,
    0x329: 84,
    0x32A: 84,
    0x32B: 84,
    0x32C: 84,
    0x32D: 84,
    0x32E: 84,
    0x32F: 84,
    0x330: 84,
    0x331: 84,
    0x332: 84,
    0x333: 84,
    0x334: 84,
    0x335: 84,
    0x336: 84,
    0x337: 84,
    0x338: 84,
    0x339: 84,
    0x33A: 84,
    0x33B: 84,
    0x33C: 84,
    0x33D: 84,
    0x33E: 84,
    0x33F: 84,
    0x340: 84,
    0x341: 84,
    0x342: 84,
    0x343: 84,
    0x344: 84,
    0x345: 84,
    0x346: 84,
    0x347: 84,
    0x348: 84,
    0x349: 84,
    0x34A: 84,
    0x34B: 84,
    0x34C: 84,
    0x34D: 84,
    0x34E: 84,
    0x34F: 84,
    0x350: 84,
    0x351: 84,
    0x352: 84,
    0x353: 84,
    0x354: 84,
    0x355: 84,
    0x356: 84,
    0x357: 84,
    0x358: 84,
    0x359: 84,
    0x35A: 84,
    0x35B: 84,
    0x35C: 84,
    0x35D: 84,
    0x35E: 84,
    0x35F: 84,
    0x360: 84,
    0x361: 84,
    0x362: 84,
    0x363: 84,
    0x364: 84,
    0x365: 84,
    0x366: 84,
    0x367: 84,
    0x368: 84,
    0x369: 84,
    0x36A: 84,
    0x36B: 84,
    0x36C: 84,
    0x36D: 84,
    0x36E: 84,
    0x36F: 84,
    0x483: 84,
    0x484: 84,
    0x485: 84,
    0x486: 84,
    0x487: 84,
    0x488: 84,
    0x489: 84,
    0x591: 84,
    0x592: 84,
    0x593: 84,
    0x594: 84,
    0x595: 84,
    0x596: 84,
    0x597: 84,
    0x598: 84,
    0x599: 84,
    0x59A: 84,
    0x59B: 84,
    0x59C: 84,
    0x59D: 84,
    0x59E: 84,
    0x59F: 84,
    0x5A0: 84,
    0x5A1: 84,
    0x5A2: 84,
    0x5A3: 84,
    0x5A4: 84,
    0x5A5: 84,
    0x5A6: 84,
    0x5A7: 84,
    0x5A8: 84,
    0x5A9: 84,
    0x5AA: 84,
    0x5AB: 84,
    0x5AC: 84,
    0x5AD: 84,
    0x5AE: 84,
    0x5AF: 84,
    0x5B0: 84,
    0x5B1: 84,
    0x5B2: 84,
    0x5B3: 84,
    0x5B4: 84,
    0x5B5: 84,
    0x5B6: 84,
    0x5B7: 84,
    0x5B8: 84,
    0x5B9: 84,
    0x5BA: 84,
    0x5BB: 84,
    0x5BC: 84,
    0x5BD: 84,
    0x5BF: 84,
    0x5C1: 84,
    0x5C2: 84,
    0x5C4: 84,
    0x5C5: 84,
    0x5C7: 84,
    0x610: 84,
    0x611: 84,
    0x612: 84,
    0x613: 84,
    0x614: 84,
    0x615: 84,
    0x616: 84,
    0x617: 84,
    0x618: 84,
    0x619: 84,
    0x61A: 84,
    0x61C: 84,
    0x620: 68,
    0x622: 82,
    0x623: 82,
    0x624: 82,
    0x625: 82,
    0x626: 68,
    0x627: 82,
    0x628: 68,
    0x629: 82,
    0x62A: 68,
    0x62B: 68,
    0x62C: 68,
    0x62D: 68,
    0x62E: 68,
    0x62F: 82,
    0x630: 82,
    0x631: 82,
    0x632: 82,
    0x633: 68,
    0x634: 68,
    0x635: 68,
    0x636: 68,
    0x637: 68,
    0x638: 68,
    0x639: 68,
    0x63A: 68,
    0x63B: 68,
    0x63C: 68,
    0x63D: 68,
    0x63E: 68,
    0x63F: 68,
    0x640: 67,
    0x641: 68,
    0x642: 68,
    0x643: 68,
    0x644: 68,
    0x645: 68,
    0x646: 68,
    0x647: 68,
    0x648: 82,
    0x649: 68,
    0x64A: 68,
    0x64B: 84,
    0x64C: 84,
    0x64D: 84,
    0x64E: 84,
    0x64F: 84,
    0x650: 84,
    0x651: 84,
    0x652: 84,
    0x653: 84,
    0x654: 84,
    0x655: 84,
    0x656: 84,
    0x657: 84,
    0x658: 84,
    0x659: 84,
    0x65A: 84,
    0x65B: 84,
    0x65C: 84,
    0x65D: 84,
    0x65E: 84,
    0x65F: 84,
    0x66E: 68,
    0x66F: 68,
    0x670: 84,
    0x671: 82,
    0x672: 82,
    0x673: 82,
    0x675: 82,
    0x676: 82,
    0x677: 82,
    0x678: 68,
    0x679: 68,
    0x67A: 68,
    0x67B: 68,
    0x67C: 68,
    0x67D: 68,
    0x67E: 68,
    0x67F: 68,
    0x680: 68,
    0x681: 68,
    0x682: 68,
    0x683: 68,
    0x684: 68,
    0x685: 68,
    0x686: 68,
    0x687: 68,
    0x688: 82,
    0x689: 82,
    0x68A: 82,
    0x68B: 82,
    0x68C: 82,
    0x68D: 82,
    0x68E: 82,
    0x68F: 82,
    0x690: 82,
    0x691: 82,
    0x692: 82,
    0x693: 82,
    0x694: 82,
    0x695: 82,
    0x696: 82,
    0x697: 82,
    0x698: 82,
    0x699: 82,
    0x69A: 68,
    0x69B: 68,
    0x69C: 68,
    0x69D: 68,
    0x69E: 68,
    0x69F: 68,
    0x6A0: 68,
    0x6A1: 68,
    0x6A2: 68,
    0x6A3: 68,
    0x6A4: 68,
    0x6A5: 68,
    0x6A6: 68,
    0x6A7: 68,
    0x6A8: 68,
    0x6A9: 68,
    0x6AA: 68,
    0x6AB: 68,
    0x6AC: 68,
    0x6AD: 68,
    0x6AE: 68,
    0x6AF: 68,
    0x6B0: 68,
    0x6B1: 68,
    0x6B2: 68,
    0x6B3: 68,
    0x6B4: 68,
    0x6B5: 68,
    0x6B6: 68,
    0x6B7: 68,
    0x6B8: 68,
    0x6B9: 68,
    0x6BA: 68,
    0x6BB: 68,
    0x6BC: 68,
    0x6BD: 68,
    0x6BE: 68,
    0x6BF: 68,
    0x6C0: 82,
    0x6C1: 68,
    0x6C2: 68,
    0x6C3: 82,
    0x6C4: 82,
    0x6C5: 82,
    0x6C6: 82,
    0x6C7: 82,
    0x6C8: 82,
    0x6C9: 82,
    0x6CA: 82,
    0x6CB: 82,
    0x6CC: 68,
    0x6CD: 82,
    0x6CE: 68,
    0x6CF: 82,
    0x6D0: 68,
    0x6D1: 68,
    0x6D2: 82,
    0x6D3: 82,
    0x6D5: 82,
    0x6D6: 84,
    0x6D7: 84,
    0x6D8: 84,
    0x6D9: 84,
    0x6DA: 84,
    0x6DB: 84,
    0x6DC: 84,
    0x6DF: 84,
    0x6E0: 84,
    0x6E1: 84,
    0x6E2: 84,
    0x6E3: 84,
    0x6E4: 84,
    0x6E7: 84,
    0x6E8: 84,
    0x6EA: 84,
    0x6EB: 84,
    0x6EC: 84,
    0x6ED: 84,
    0x6EE: 82,
    0x6EF: 82,
    0x6FA: 68,
    0x6FB: 68,
    0x6FC: 68,
    0x6FF: 68,
    0x70F: 84,
    0x710: 82,
    0x711: 84,
    0x712: 68,
    0x713: 68,
    0x714: 68,
    0x715: 82,
    0x716: 82,
    0x717: 82,
    0x718: 82,
    0x719: 82,
    0x71A: 68,
    0x71B: 68,
    0x71C: 68,
    0x71D: 68,
    0x71E: 82,
    0x71F: 68,
    0x720: 68,
    0x721: 68,
    0x722: 68,
    0x723: 68,
    0x724: 68,
    0x725: 68,
    0x726: 68,
    0x727: 68,
    0x728: 82,
    0x729: 68,
    0x72A: 82,
    0x72B: 68,
    0x72C: 82,
    0x72D: 68,
    0x72E: 68,
    0x72F: 82,
    0x730: 84,
    0x731: 84,
    0x732: 84,
    0x733: 84,
    0x734: 84,
    0x735: 84,
    0x736: 84,
    0x737: 84,
    0x738: 84,
    0x739: 84,
    0x73A: 84,
    0x73B: 84,
    0x73C: 84,
    0x73D: 84,
    0x73E: 84,
    0x73F: 84,
    0x740: 84,
    0x741: 84,
    0x742: 84,
    0x743: 84,
    0x744: 84,
    0x745: 84,
    0x746: 84,
    0x747: 84,
    0x748: 84,
    0x749: 84,
    0x74A: 84,
    0x74D: 82,
    0x74E: 68,
    0x74F: 68,
    0x750: 68,
    0x751: 68,
    0x752: 68,
    0x753: 68,
    0x754: 68,
    0x755: 68,
    0x756: 68,
    0x757: 68,
    0x758: 68,
    0x759: 82,
    0x75A: 82,
    0x75B: 82,
    0x75C: 68,
    0x75D: 68,
    0x75E: 68,
    0x75F: 68,
    0x760: 68,
    0x761: 68,
    0x762: 68,
    0x763: 68,
    0x764: 68,
    0x765: 68,
    0x766: 68,
    0x767: 68,
    0x768: 68,
    0x769: 68,
    0x76A: 68,
    0x76B: 82,
    0x76C: 82,
    0x76D: 68,
    0x76E: 68,
    0x76F: 68,
    0x770: 68,
    0x771: 82,
    0x772: 68,
    0x773: 82,
    0x774: 82,
    0x775: 68,
    0x776: 68,
    0x777: 68,
    0x778: 82,
    0x779: 82,
    0x77A: 68,
    0x77B: 68,
    0x77C: 68,
    0x77D: 68,
    0x77E: 68,
    0x77F: 68,
    0x7A6: 84,
    0x7A7: 84,
    0x7A8: 84,
    0x7A9: 84,
    0x7AA: 84,
    0x7AB: 84,
    0x7AC: 84,
    0x7AD: 84,
    0x7AE: 84,
    0x7AF: 84,
    0x7B0: 84,
    0x7CA: 68,
    0x7CB: 68,
    0x7CC: 68,
    0x7CD: 68,
    0x7CE: 68,
    0x7CF: 68,
    0x7D0: 68,
    0x7D1: 68,
    0x7D2: 68,
    0x7D3: 68,
    0x7D4: 68,
    0x7D5: 68,
    0x7D6: 68,
    0x7D7: 68,
    0x7D8: 68,
    0x7D9: 68,
    0x7DA: 68,
    0x7DB: 68,
    0x7DC: 68,
    0x7DD: 68,
    0x7DE: 68,
    0x7DF: 68,
    0x7E0: 68,
    0x7E1: 68,
    0x7E2: 68,
    0x7E3: 68,
    0x7E4: 68,
    0x7E5: 68,
    0x7E6: 68,
    0x7E7: 68,
    0x7E8: 68,
    0x7E9: 68,
    0x7EA: 68,
    0x7EB: 84,
    0x7EC: 84,
    0x7ED: 84,
    0x7EE: 84,
    0x7EF: 84,
    0x7F0: 84,
    0x7F1: 84,
    0x7F2: 84,
    0x7F3: 84,
    0x7FA: 67,
    0x7FD: 84,
    0x816: 84,
    0x817: 84,
    0x818: 84,
    0x819: 84,
    0x81B: 84,
    0x81C: 84,
    0x81D: 84,
    0x81E: 84,
    0x81F: 84,
    0x820: 84,
    0x821: 84,
    0x822: 84,
    0x823: 84,
    0x825: 84,
    0x826: 84,
    0x827: 84,
    0x829: 84,
    0x82A: 84,
    0x82B: 84,
    0x82C: 84,
    0x82D: 84,
    0x840: 82,
    0x841: 68,
    0x842: 68,
    0x843: 68,
    0x844: 68,
    0x845: 68,
    0x846: 82,
    0x847: 82,
    0x848: 68,
    0x849: 82,
    0x84A: 68,
    0x84B: 68,
    0x84C: 68,
    0x84D: 68,
    0x84E: 68,
    0x84F: 68,
    0x850: 68,
    0x851: 68,
    0x852: 68,
    0x853: 68,
    0x854: 82,
    0x855: 68,
    0x856: 82,
    0x857: 82,
    0x858: 82,
    0x859: 84,
    0x85A: 84,
    0x85B: 84,
    0x860: 68,
    0x862: 68,
    0x863: 68,
    0x864: 68,
    0x865: 68,
    0x867: 82,
    0x868: 68,
    0x869: 82,
    0x86A: 82,
    0x870: 82,
    0x871: 82,
    0x872: 82,
    0x873: 82,
    0x874: 82,
    0x875: 82,
    0x876: 82,
    0x877: 82,
    0x878: 82,
    0x879: 82,
    0x87A: 82,
    0x87B: 82,
    0x87C: 82,
    0x87D: 82,
    0x87E: 82,
    0x87F: 82,
    0x880: 82,
    0x881: 82,
    0x882: 82,
    0x883: 67,
    0x884: 67,
    0x885: 67,
    0x886: 68,
    0x889: 68,
    0x88A: 68,
    0x88B: 68,
    0x88C: 68,
    0x88D: 68,
    0x88E: 82,
    0x898: 84,
    0x899: 84,
    0x89A: 84,
    0x89B: 84,
    0x89C: 84,
    0x89D: 84,
    0x89E: 84,
    0x89F: 84,
    0x8A0: 68,
    0x8A1: 68,
    0x8A2: 68,
    0x8A3: 68,
    0x8A4: 68,
    0x8A5: 68,
    0x8A6: 68,
    0x8A7: 68,
    0x8A8: 68,
    0x8A9: 68,
    0x8AA: 82,
    0x8AB: 82,
    0x8AC: 82,
    0x8AE: 82,
    0x8AF: 68,
    0x8B0: 68,
    0x8B1: 82,
    0x8B2: 82,
    0x8B3: 68,
    0x8B4: 68,
    0x8B5: 68,
    0x8B6: 68,
    0x8B7: 68,
    0x8B8: 68,
    0x8B9: 82,
    0x8BA: 68,
    0x8BB: 68,
    0x8BC: 68,
    0x8BD: 68,
    0x8BE: 68,
    0x8BF: 68,
    0x8C0: 68,
    0x8C1: 68,
    0x8C2: 68,
    0x8C3: 68,
    0x8C4: 68,
    0x8C5: 68,
    0x8C6: 68,
    0x8C7: 68,
    0x8C8: 68,
    0x8CA: 84,
    0x8CB: 84,
    0x8CC: 84,
    0x8CD: 84,
    0x8CE: 84,
    0x8CF: 84,
    0x8D0: 84,
    0x8D1: 84,
    0x8D2: 84,
    0x8D3: 84,
    0x8D4: 84,
    0x8D5: 84,
    0x8D6: 84,
    0x8D7: 84,
    0x8D8: 84,
    0x8D9: 84,
    0x8DA: 84,
    0x8DB: 84,
    0x8DC: 84,
    0x8DD: 84,
    0x8DE: 84,
    0x8DF: 84,
    0x8E0: 84,
    0x8E1: 84,
    0x8E3: 84,
    0x8E4: 84,
    0x8E5: 84,
    0x8E6: 84,
    0x8E7: 84,
    0x8E8: 84,
    0x8E9: 84,
    0x8EA: 84,
    0x8EB: 84,
    0x8EC: 84,
    0x8ED: 84,
    0x8EE: 84,
    0x8EF: 84,
    0x8F0: 84,
    0x8F1: 84,
    0x8F2: 84,
    0x8F3: 84,
    0x8F4: 84,
    0x8F5: 84,
    0x8F6: 84,
    0x8F7: 84,
    0x8F8: 84,
    0x8F9: 84,
    0x8FA: 84,
    0x8FB: 84,
    0x8FC: 84,
    0x8FD: 84,
    0x8FE: 84,
    0x8FF: 84,
    0x900: 84,
    0x901: 84,
    0x902: 84,
    0x93A: 84,
    0x93C: 84,
    0x941: 84,
    0x942: 84,
    0x943: 84,
    0x944: 84,
    0x945: 84,
    0x946: 84,
    0x947: 84,
    0x948: 84,
    0x94D: 84,
    0x951: 84,
    0x952: 84,
    0x953: 84,
    0x954: 84,
    0x955: 84,
    0x956: 84,
    0x957: 84,
    0x962: 84,
    0x963: 84,
    0x981: 84,
    0x9BC: 84,
    0x9C1: 84,
    0x9C2: 84,
    0x9C3: 84,
    0x9C4: 84,
    0x9CD: 84,
    0x9E2: 84,
    0x9E3: 84,
    0x9FE: 84,
    0xA01: 84,
    0xA02: 84,
    0xA3C: 84,
    0xA41: 84,
    0xA42: 84,
    0xA47: 84,
    0xA48: 84,
    0xA4B: 84,
    0xA4C: 84,
    0xA4D: 84,
    0xA51: 84,
    0xA70: 84,
    0xA71: 84,
    0xA75: 84,
    0xA81: 84,
    0xA82: 84,
    0xABC: 84,
    0xAC1: 84,
    0xAC2: 84,
    0xAC3: 84,
    0xAC4: 84,
    0xAC5: 84,
    0xAC7: 84,
    0xAC8: 84,
    0xACD: 84,
    0xAE2: 84,
    0xAE3: 84,
    0xAFA: 84,
    0xAFB: 84,
    0xAFC: 84,
    0xAFD: 84,
    0xAFE: 84,
    0xAFF: 84,
    0xB01: 84,
    0xB3C: 84,
    0xB3F: 84,
    0xB41: 84,
    0xB42: 84,
    0xB43: 84,
    0xB44: 84,
    0xB4D: 84,
    0xB55: 84,
    0xB56: 84,
    0xB62: 84,
    0xB63: 84,
    0xB82: 84,
    0xBC0: 84,
    0xBCD: 84,
    0xC00: 84,
    0xC04: 84,
    0xC3C: 84,
    0xC3E: 84,
    0xC3F: 84,
    0xC40: 84,
    0xC46: 84,
    0xC47: 84,
    0xC48: 84,
    0xC4A: 84,
    0xC4B: 84,
    0xC4C: 84,
    0xC4D: 84,
    0xC55: 84,
    0xC56: 84,
    0xC62: 84,
    0xC63: 84,
    0xC81: 84,
    0xCBC: 84,
    0xCBF: 84,
    0xCC6: 84,
    0xCCC: 84,
    0xCCD: 84,
    0xCE2: 84,
    0xCE3: 84,
    0xD00: 84,
    0xD01: 84,
    0xD3B: 84,
    0xD3C: 84,
    0xD41: 84,
    0xD42: 84,
    0xD43: 84,
    0xD44: 84,
    0xD4D: 84,
    0xD62: 84,
    0xD63: 84,
    0xD81: 84,
    0xDCA: 84,
    0xDD2: 84,
    0xDD3: 84,
    0xDD4: 84,
    0xDD6: 84,
    0xE31: 84,
    0xE34: 84,
    0xE35: 84,
    0xE36: 84,
    0xE37: 84,
    0xE38: 84,
    0xE39: 84,
    0xE3A: 84,
    0xE47: 84,
    0xE48: 84,
    0xE49: 84,
    0xE4A: 84,
    0xE4B: 84,
    0xE4C: 84,
    0xE4D: 84,
    0xE4E: 84,
    0xEB1: 84,
    0xEB4: 84,
    0xEB5: 84,
    0xEB6: 84,
    0xEB7: 84,
    0xEB8: 84,
    0xEB9: 84,
    0xEBA: 84,
    0xEBB: 84,
    0xEBC: 84,
    0xEC8: 84,
    0xEC9: 84,
    0xECA: 84,
    0xECB: 84,
    0xECC: 84,
    0xECD: 84,
    0xECE: 84,
    0xF18: 84,
    0xF19: 84,
    0xF35: 84,
    0xF37: 84,
    0xF39: 84,
    0xF71: 84,
    0xF72: 84,
    0xF73: 84,
    0xF74: 84,
    0xF75: 84,
    0xF76: 84,
    0xF77: 84,
    0xF78: 84,
    0xF79: 84,
    0xF7A: 84,
    0xF7B: 84,
    0xF7C: 84,
    0xF7D: 84,
    0xF7E: 84,
    0xF80: 84,
    0xF81: 84,
    0xF82: 84,
    0xF83: 84,
    0xF84: 84,
    0xF86: 84,
    0xF87: 84,
    0xF8D: 84,
    0xF8E: 84,
    0xF8F: 84,
    0xF90: 84,
    0xF91: 84,
    0xF92: 84,
    0xF93: 84,
    0xF94: 84,
    0xF95: 84,
    0xF96: 84,
    0xF97: 84,
    0xF99: 84,
    0xF9A: 84,
    0xF9B: 84,
    0xF9C: 84,
    0xF9D: 84,
    0xF9E: 84,
    0xF9F: 84,
    0xFA0: 84,
    0xFA1: 84,
    0xFA2: 84,
    0xFA3: 84,
    0xFA4: 84,
    0xFA5: 84,
    0xFA6: 84,
    0xFA7: 84,
    0xFA8: 84,
    0xFA9: 84,
    0xFAA: 84,
    0xFAB: 84,
    0xFAC: 84,
    0xFAD: 84,
    0xFAE: 84,
    0xFAF: 84,
    0xFB0: 84,
    0xFB1: 84,
    0xFB2: 84,
    0xFB3: 84,
    0xFB4: 84,
    0xFB5: 84,
    0xFB6: 84,
    0xFB7: 84,
    0xFB8: 84,
    0xFB9: 84,
    0xFBA: 84,
    0xFBB: 84,
    0xFBC: 84,
    0xFC6: 84,
    0x102D: 84,
    0x102E: 84,
    0x102F: 84,
    0x1030: 84,
    0x1032: 84,
    0x1033: 84,
    0x1034: 84,
    0x1035: 84,
    0x1036: 84,
    0x1037: 84,
    0x1039: 84,
    0x103A: 84,
    0x103D: 84,
    0x103E: 84,
    0x1058: 84,
    0x1059: 84,
    0x105E: 84,
    0x105F: 84,
    0x1060: 84,
    0x1071: 84,
    0x1072: 84,
    0x1073: 84,
    0x1074: 84,
    0x1082: 84,
    0x1085: 84,
    0x1086: 84,
    0x108D: 84,
    0x109D: 84,
    0x135D: 84,
    0x135E: 84,
    0x135F: 84,
    0x1712: 84,
    0x1713: 84,
    0x1714: 84,
    0x1732: 84,
    0x1733: 84,
    0x1752: 84,
    0x1753: 84,
    0x1772: 84,
    0x1773: 84,
    0x17B4: 84,
    0x17B5: 84,
    0x17B7: 84,
    0x17B8: 84,
    0x17B9: 84,
    0x17BA: 84,
    0x17BB: 84,
    0x17BC: 84,
    0x17BD: 84,
    0x17C6: 84,
    0x17C9: 84,
    0x17CA: 84,
    0x17CB: 84,
    0x17CC: 84,
    0x17CD: 84,
    0x17CE: 84,
    0x17CF: 84,
    0x17D0: 84,
    0x17D1: 84,
    0x17D2: 84,
    0x17D3: 84,
    0x17DD: 84,
    0x1807: 68,
    0x180A: 67,
    0x180B: 84,
    0x180C: 84,
    0x180D: 84,
    0x180F: 84,
    0x1820: 68,
    0x1821: 68,
    0x1822: 68,
    0x1823: 68,
    0x1824: 68,
    0x1825: 68,
    0x1826: 68,
    0x1827: 68,
    0x1828: 68,
    0x1829: 68,
    0x182A: 68,
    0x182B: 68,
    0x182C: 68,
    0x182D: 68,
    0x182E: 68,
    0x182F: 68,
    0x1830: 68,
    0x1831: 68,
    0x1832: 68,
    0x1833: 68,
    0x1834: 68,
    0x1835: 68,
    0x1836: 68,
    0x1837: 68,
    0x1838: 68,
    0x1839: 68,
    0x183A: 68,
    0x183B: 68,
    0x183C: 68,
    0x183D: 68,
    0x183E: 68,
    0x183F: 68,
    0x1840: 68,
    0x1841: 68,
    0x1842: 68,
    0x1843: 68,
    0x1844: 68,
    0x1845: 68,
    0x1846: 68,
    0x1847: 68,
    0x1848: 68,
    0x1849: 68,
    0x184A: 68,
    0x184B: 68,
    0x184C: 68,
    0x184D: 68,
    0x184E: 68,
    0x184F: 68,
    0x1850: 68,
    0x1851: 68,
    0x1852: 68,
    0x1853: 68,
    0x1854: 68,
    0x1855: 68,
    0x1856: 68,
    0x1857: 68,
    0x1858: 68,
    0x1859: 68,
    0x185A: 68,
    0x185B: 68,
    0x185C: 68,
    0x185D: 68,
    0x185E: 68,
    0x185F: 68,
    0x1860: 68,
    0x1861: 68,
    0x1862: 68,
    0x1863: 68,
    0x1864: 68,
    0x1865: 68,
    0x1866: 68,
    0x1867: 68,
    0x1868: 68,
    0x1869: 68,
    0x186A: 68,
    0x186B: 68,
    0x186C: 68,
    0x186D: 68,
    0x186E: 68,
    0x186F: 68,
    0x1870: 68,
    0x1871: 68,
    0x1872: 68,
    0x1873: 68,
    0x1874: 68,
    0x1875: 68,
    0x1876: 68,
    0x1877: 68,
    0x1878: 68,
    0x1885: 84,
    0x1886: 84,
    0x1887: 68,
    0x1888: 68,
    0x1889: 68,
    0x188A: 68,
    0x188B: 68,
    0x188C: 68,
    0x188D: 68,
    0x188E: 68,
    0x188F: 68,
    0x1890: 68,
    0x1891: 68,
    0x1892: 68,
    0x1893: 68,
    0x1894: 68,
    0x1895: 68,
    0x1896: 68,
    0x1897: 68,
    0x1898: 68,
    0x1899: 68,
    0x189A: 68,
    0x189B: 68,
    0x189C: 68,
    0x189D: 68,
    0x189E: 68,
    0x189F: 68,
    0x18A0: 68,
    0x18A1: 68,
    0x18A2: 68,
    0x18A3: 68,
    0x18A4: 68,
    0x18A5: 68,
    0x18A6: 68,
    0x18A7: 68,
    0x18A8: 68,
    0x18A9: 84,
    0x18AA: 68,
    0x1920: 84,
    0x1921: 84,
    0x1922: 84,
    0x1927: 84,
    0x1928: 84,
    0x1932: 84,
    0x1939: 84,
    0x193A: 84,
    0x193B: 84,
    0x1A17: 84,
    0x1A18: 84,
    0x1A1B: 84,
    0x1A56: 84,
    0x1A58: 84,
    0x1A59: 84,
    0x1A5A: 84,
    0x1A5B: 84,
    0x1A5C: 84,
    0x1A5D: 84,
    0x1A5E: 84,
    0x1A60: 84,
    0x1A62: 84,
    0x1A65: 84,
    0x1A66: 84,
    0x1A67: 84,
    0x1A68: 84,
    0x1A69: 84,
    0x1A6A: 84,
    0x1A6B: 84,
    0x1A6C: 84,
    0x1A73: 84,
    0x1A74: 84,
    0x1A75: 84,
    0x1A76: 84,
    0x1A77: 84,
    0x1A78: 84,
    0x1A79: 84,
    0x1A7A: 84,
    0x1A7B: 84,
    0x1A7C: 84,
    0x1A7F: 84,
    0x1AB0: 84,
    0x1AB1: 84,
    0x1AB2: 84,
    0x1AB3: 84,
    0x1AB4: 84,
    0x1AB5: 84,
    0x1AB6: 84,
    0x1AB7: 84,
    0x1AB8: 84,
    0x1AB9: 84,
    0x1ABA: 84,
    0x1ABB: 84,
    0x1ABC: 84,
    0x1ABD: 84,
    0x1ABE: 84,
    0x1ABF: 84,
    0x1AC0: 84,
    0x1AC1: 84,
    0x1AC2: 84,
    0x1AC3: 84,
    0x1AC4: 84,
    0x1AC5: 84,
    0x1AC6: 84,
    0x1AC7: 84,
    0x1AC8: 84,
    0x1AC9: 84,
    0x1ACA: 84,
    0x1ACB: 84,
    0x1ACC: 84,
    0x1ACD: 84,
    0x1ACE: 84,
    0x1B00: 84,
    0x1B01: 84,
    0x1B02: 84,
    0x1B03: 84,
    0x1B34: 84,
    0x1B36: 84,
    0x1B37: 84,
    0x1B38: 84,
    0x1B39: 84,
    0x1B3A: 84,
    0x1B3C: 84,
    0x1B42: 84,
    0x1B6B: 84,
    0x1B6C: 84,
    0x1B6D: 84,
    0x1B6E: 84,
    0x1B6F: 84,
    0x1B70: 84,
    0x1B71: 84,
    0x1B72: 84,
    0x1B73: 84,
    0x1B80: 84,
    0x1B81: 84,
    0x1BA2: 84,
    0x1BA3: 84,
    0x1BA4: 84,
    0x1BA5: 84,
    0x1BA8: 84,
    0x1BA9: 84,
    0x1BAB: 84,
    0x1BAC: 84,
    0x1BAD: 84,
    0x1BE6: 84,
    0x1BE8: 84,
    0x1BE9: 84,
    0x1BED: 84,
    0x1BEF: 84,
    0x1BF0: 84,
    0x1BF1: 84,
    0x1C2C: 84,
    0x1C2D: 84,
    0x1C2E: 84,
    0x1C2F: 84,
    0x1C30: 84,
    0x1C31: 84,
    0x1C32: 84,
    0x1C33: 84,
    0x1C36: 84,
    0x1C37: 84,
    0x1CD0: 84,
    0x1CD1: 84,
    0x1CD2: 84,
    0x1CD4: 84,
    0x1CD5: 84,
    0x1CD6: 84,
    0x1CD7: 84,
    0x1CD8: 84,
    0x1CD9: 84,
    0x1CDA: 84,
    0x1CDB: 84,
    0x1CDC: 84,
    0x1CDD: 84,
    0x1CDE: 84,
    0x1CDF: 84,
    0x1CE0: 84,
    0x1CE2: 84,
    0x1CE3: 84,
    0x1CE4: 84,
    0x1CE5: 84,
    0x1CE6: 84,
    0x1CE7: 84,
    0x1CE8: 84,
    0x1CED: 84,
    0x1CF4: 84,
    0x1CF8: 84,
    0x1CF9: 84,
    0x1DC0: 84,
    0x1DC1: 84,
    0x1DC2: 84,
    0x1DC3: 84,
    0x1DC4: 84,
    0x1DC5: 84,
    0x1DC6: 84,
    0x1DC7: 84,
    0x1DC8: 84,
    0x1DC9: 84,
    0x1DCA: 84,
    0x1DCB: 84,
    0x1DCC: 84,
    0x1DCD: 84,
    0x1DCE: 84,
    0x1DCF: 84,
    0x1DD0: 84,
    0x1DD1: 84,
    0x1DD2: 84,
    0x1DD3: 84,
    0x1DD4: 84,
    0x1DD5: 84,
    0x1DD6: 84,
    0x1DD7: 84,
    0x1DD8: 84,
    0x1DD9: 84,
    0x1DDA: 84,
    0x1DDB: 84,
    0x1DDC: 84,
    0x1DDD: 84,
    0x1DDE: 84,
    0x1DDF: 84,
    0x1DE0: 84,
    0x1DE1: 84,
    0x1DE2: 84,
    0x1DE3: 84,
    0x1DE4: 84,
    0x1DE5: 84,
    0x1DE6: 84,
    0x1DE7: 84,
    0x1DE8: 84,
    0x1DE9: 84,
    0x1DEA: 84,
    0x1DEB: 84,
    0x1DEC: 84,
    0x1DED: 84,
    0x1DEE: 84,
    0x1DEF: 84,
    0x1DF0: 84,
    0x1DF1: 84,
    0x1DF2: 84,
    0x1DF3: 84,
    0x1DF4: 84,
    0x1DF5: 84,
    0x1DF6: 84,
    0x1DF7: 84,
    0x1DF8: 84,
    0x1DF9: 84,
    0x1DFA: 84,
    0x1DFB: 84,
    0x1DFC: 84,
    0x1DFD: 84,
    0x1DFE: 84,
    0x1DFF: 84,
    0x200B: 84,
    0x200D: 67,
    0x200E: 84,
    0x200F: 84,
    0x202A: 84,
    0x202B: 84,
    0x202C: 84,
    0x202D: 84,
    0x202E: 84,
    0x2060: 84,
    0x2061: 84,
    0x2062: 84,
    0x2063: 84,
    0x2064: 84,
    0x206A: 84,
    0x206B: 84,
    0x206C: 84,
    0x206D: 84,
    0x206E: 84,
    0x206F: 84,
    0x20D0: 84,
    0x20D1: 84,
    0x20D2: 84,
    0x20D3: 84,
    0x20D4: 84,
    0x20D5: 84,
    0x20D6: 84,
    0x20D7: 84,
    0x20D8: 84,
    0x20D9: 84,
    0x20DA: 84,
    0x20DB: 84,
    0x20DC: 84,
    0x20DD: 84,
    0x20DE: 84,
    0x20DF: 84,
    0x20E0: 84,
    0x20E1: 84,
    0x20E2: 84,
    0x20E3: 84,
    0x20E4: 84,
    0x20E5: 84,
    0x20E6: 84,
    0x20E7: 84,
    0x20E8: 84,
    0x20E9: 84,
    0x20EA: 84,
    0x20EB: 84,
    0x20EC: 84,
    0x20ED: 84,
    0x20EE: 84,
    0x20EF: 84,
    0x20F0: 84,
    0x2CEF: 84,
    0x2CF0: 84,
    0x2CF1: 84,
    0x2D7F: 84,
    0x2DE0: 84,
    0x2DE1: 84,
    0x2DE2: 84,
    0x2DE3: 84,
    0x2DE4: 84,
    0x2DE5: 84,
    0x2DE6: 84,
    0x2DE7: 84,
    0x2DE8: 84,
    0x2DE9: 84,
    0x2DEA: 84,
    0x2DEB: 84,
    0x2DEC: 84,
    0x2DED: 84,
    0x2DEE: 84,
    0x2DEF: 84,
    0x2DF0: 84,
    0x2DF1: 84,
    0x2DF2: 84,
    0x2DF3: 84,
    0x2DF4: 84,
    0x2DF5: 84,
    0x2DF6: 84,
    0x2DF7: 84,
    0x2DF8: 84,
    0x2DF9: 84,
    0x2DFA: 84,
    0x2DFB: 84,
    0x2DFC: 84,
    0x2DFD: 84,
    0x2DFE: 84,
    0x2DFF: 84,
    0x302A: 84,
    0x302B: 84,
    0x302C: 84,
    0x302D: 84,
    0x3099: 84,
    0x309A: 84,
    0xA66F: 84,
    0xA670: 84,
    0xA671: 84,
    0xA672: 84,
    0xA674: 84,
    0xA675: 84,
    0xA676: 84,
    0xA677: 84,
    0xA678: 84,
    0xA679: 84,
    0xA67A: 84,
    0xA67B: 84,
    0xA67C: 84,
    0xA67D: 84,
    0xA69E: 84,
    0xA69F: 84,
    0xA6F0: 84,
    0xA6F1: 84,
    0xA802: 84,
    0xA806: 84,
    0xA80B: 84,
    0xA825: 84,
    0xA826: 84,
    0xA82C: 84,
    0xA840: 68,
    0xA841: 68,
    0xA842: 68,
    0xA843: 68,
    0xA844: 68,
    0xA845: 68,
    0xA846: 68,
    0xA847: 68,
    0xA848: 68,
    0xA849: 68,
    0xA84A: 68,
    0xA84B: 68,
    0xA84C: 68,
    0xA84D: 68,
    0xA84E: 68,
    0xA84F: 68,
    0xA850: 68,
    0xA851: 68,
    0xA852: 68,
    0xA853: 68,
    0xA854: 68,
    0xA855: 68,
    0xA856: 68,
    0xA857: 68,
    0xA858: 68,
    0xA859: 68,
    0xA85A: 68,
    0xA85B: 68,
    0xA85C: 68,
    0xA85D: 68,
    0xA85E: 68,
    0xA85F: 68,
    0xA860: 68,
    0xA861: 68,
    0xA862: 68,
    0xA863: 68,
    0xA864: 68,
    0xA865: 68,
    0xA866: 68,
    0xA867: 68,
    0xA868: 68,
    0xA869: 68,
    0xA86A: 68,
    0xA86B: 68,
    0xA86C: 68,
    0xA86D: 68,
    0xA86E: 68,
    0xA86F: 68,
    0xA870: 68,
    0xA871: 68,
    0xA872: 76,
    0xA8C4: 84,
    0xA8C5: 84,
    0xA8E0: 84,
    0xA8E1: 84,
    0xA8E2: 84,
    0xA8E3: 84,
    0xA8E4: 84,
    0xA8E5: 84,
    0xA8E6: 84,
    0xA8E7: 84,
    0xA8E8: 84,
    0xA8E9: 84,
    0xA8EA: 84,
    0xA8EB: 84,
    0xA8EC: 84,
    0xA8ED: 84,
    0xA8EE: 84,
    0xA8EF: 84,
    0xA8F0: 84,
    0xA8F1: 84,
    0xA8FF: 84,
    0xA926: 84,
    0xA927: 84,
    0xA928: 84,
    0xA929: 84,
    0xA92A: 84,
    0xA92B: 84,
    0xA92C: 84,
    0xA92D: 84,
    0xA947: 84,
    0xA948: 84,
    0xA949: 84,
    0xA94A: 84,
    0xA94B: 84,
    0xA94C: 84,
    0xA94D: 84,
    0xA94E: 84,
    0xA94F: 84,
    0xA950: 84,
    0xA951: 84,
    0xA980: 84,
    0xA981: 84,
    0xA982: 84,
    0xA9B3: 84,
    0xA9B6: 84,
    0xA9B7: 84,
    0xA9B8: 84,
    0xA9B9: 84,
    0xA9BC: 84,
    0xA9BD: 84,
    0xA9E5: 84,
    0xAA29: 84,
    0xAA2A: 84,
    0xAA2B: 84,
    0xAA2C: 84,
    0xAA2D: 84,
    0xAA2E: 84,
    0xAA31: 84,
    0xAA32: 84,
    0xAA35: 84,
    0xAA36: 84,
    0xAA43: 84,
    0xAA4C: 84,
    0xAA7C: 84,
    0xAAB0: 84,
    0xAAB2: 84,
    0xAAB3: 84,
    0xAAB4: 84,
    0xAAB7: 84,
    0xAAB8: 84,
    0xAABE: 84,
    0xAABF: 84,
    0xAAC1: 84,
    0xAAEC: 84,
    0xAAED: 84,
    0xAAF6: 84,
    0xABE5: 84,
    0xABE8: 84,
    0xABED: 84,
    0xFB1E: 84,
    0xFE00: 84,
    0xFE01: 84,
    0xFE02: 84,
    0xFE03: 84,
    0xFE04: 84,
    0xFE05: 84,
    0xFE06: 84,
    0xFE07: 84,
    0xFE08: 84,
    0xFE09: 84,
    0xFE0A: 84,
    0xFE0B: 84,
    0xFE0C: 84,
    0xFE0D: 84,
    0xFE0E: 84,
    0xFE0F: 84,
    0xFE20: 84,
    0xFE21: 84,
    0xFE22: 84,
    0xFE23: 84,
    0xFE24: 84,
    0xFE25: 84,
    0xFE26: 84,
    0xFE27: 84,
    0xFE28: 84,
    0xFE29: 84,
    0xFE2A: 84,
    0xFE2B: 84,
    0xFE2C: 84,
    0xFE2D: 84,
    0xFE2E: 84,
    0xFE2F: 84,
    0xFEFF: 84,
    0xFFF9: 84,
    0xFFFA: 84,
    0xFFFB: 84,
    0x101FD: 84,
    0x102E0: 84,
    0x10376: 84,
    0x10377: 84,
    0x10378: 84,
    0x10379: 84,
    0x1037A: 84,
    0x10A01: 84,
    0x10A02: 84,
    0x10A03: 84,
    0x10A05: 84,
    0x10A06: 84,
    0x10A0C: 84,
    0x10A0D: 84,
    0x10A0E: 84,
    0x10A0F: 84,
    0x10A38: 84,
    0x10A39: 84,
    0x10A3A: 84,
    0x10A3F: 84,
    0x10AC0: 68,
    0x10AC1: 68,
    0x10AC2: 68,
    0x10AC3: 68,
    0x10AC4: 68,
    0x10AC5: 82,
    0x10AC7: 82,
    0x10AC9: 82,
    0x10ACA: 82,
    0x10ACD: 76,
    0x10ACE: 82,
    0x10ACF: 82,
    0x10AD0: 82,
    0x10AD1: 82,
    0x10AD2: 82,
    0x10AD3: 68,
    0x10AD4: 68,
    0x10AD5: 68,
    0x10AD6: 68,
    0x10AD7: 76,
    0x10AD8: 68,
    0x10AD9: 68,
    0x10ADA: 68,
    0x10ADB: 68,
    0x10ADC: 68,
    0x10ADD: 82,
    0x10ADE: 68,
    0x10ADF: 68,
    0x10AE0: 68,
    0x10AE1: 82,
    0x10AE4: 82,
    0x10AE5: 84,
    0x10AE6: 84,
    0x10AEB: 68,
    0x10AEC: 68,
    0x10AED: 68,
    0x10AEE: 68,
    0x10AEF: 82,
    0x10B80: 68,
    0x10B81: 82,
    0x10B82: 68,
    0x10B83: 82,
    0x10B84: 82,
    0x10B85: 82,
    0x10B86: 68,
    0x10B87: 68,
    0x10B88: 68,
    0x10B89: 82,
    0x10B8A: 68,
    0x10B8B: 68,
    0x10B8C: 82,
    0x10B8D: 68,
    0x10B8E: 82,
    0x10B8F: 82,
    0x10B90: 68,
    0x10B91: 82,
    0x10BA9: 82,
    0x10BAA: 82,
    0x10BAB: 82,
    0x10BAC: 82,
    0x10BAD: 68,
    0x10BAE: 68,
    0x10D00: 76,
    0x10D01: 68,
    0x10D02: 68,
    0x10D03: 68,
    0x10D04: 68,
    0x10D05: 68,
    0x10D06: 68,
    0x10D07: 68,
    0x10D08: 68,
    0x10D09: 68,
    0x10D0A: 68,
    0x10D0B: 68,
    0x10D0C: 68,
    0x10D0D: 68,
    0x10D0E: 68,
    0x10D0F: 68,
    0x10D10: 68,
    0x10D11: 68,
    0x10D12: 68,
    0x10D13: 68,
    0x10D14: 68,
    0x10D15: 68,
    0x10D16: 68,
    0x10D17: 68,
    0x10D18: 68,
    0x10D19: 68,
    0x10D1A: 68,
    0x10D1B: 68,
    0x10D1C: 68,
    0x10D1D: 68,
    0x10D1E: 68,
    0x10D1F: 68,
    0x10D20: 68,
    0x10D21: 68,
    0x10D22: 82,
    0x10D23: 68,
    0x10D24: 84,
    0x10D25: 84,
    0x10D26: 84,
    0x10D27: 84,
    0x10EAB: 84,
    0x10EAC: 84,
    0x10EFD: 84,
    0x10EFE: 84,
    0x10EFF: 84,
    0x10F30: 68,
    0x10F31: 68,
    0x10F32: 68,
    0x10F33: 82,
    0x10F34: 68,
    0x10F35: 68,
    0x10F36: 68,
    0x10F37: 68,
    0x10F38: 68,
    0x10F39: 68,
    0x10F3A: 68,
    0x10F3B: 68,
    0x10F3C: 68,
    0x10F3D: 68,
    0x10F3E: 68,
    0x10F3F: 68,
    0x10F40: 68,
    0x10F41: 68,
    0x10F42: 68,
    0x10F43: 68,
    0x10F44: 68,
    0x10F46: 84,
    0x10F47: 84,
    0x10F48: 84,
    0x10F49: 84,
    0x10F4A: 84,
    0x10F4B: 84,
    0x10F4C: 84,
    0x10F4D: 84,
    0x10F4E: 84,
    0x10F4F: 84,
    0x10F50: 84,
    0x10F51: 68,
    0x10F52: 68,
    0x10F53: 68,
    0x10F54: 82,
    0x10F70: 68,
    0x10F71: 68,
    0x10F72: 68,
    0x10F73: 68,
    0x10F74: 82,
    0x10F75: 82,
    0x10F76: 68,
    0x10F77: 68,
    0x10F78: 68,
    0x10F79: 68,
    0x10F7A: 68,
    0x10F7B: 68,
    0x10F7C: 68,
    0x10F7D: 68,
    0x10F7E: 68,
    0x10F7F: 68,
    0x10F80: 68,
    0x10F81: 68,
    0x10F82: 84,
    0x10F83: 84,
    0x10F84: 84,
    0x10F85: 84,
    0x10FB0: 68,
    0x10FB2: 68,
    0x10FB3: 68,
    0x10FB4: 82,
    0x10FB5: 82,
    0x10FB6: 82,
    0x10FB8: 68,
    0x10FB9: 82,
    0x10FBA: 82,
    0x10FBB: 68,
    0x10FBC: 68,
    0x10FBD: 82,
    0x10FBE: 68,
    0x10FBF: 68,
    0x10FC1: 68,
    0x10FC2: 82,
    0x10FC3: 82,
    0x10FC4: 68,
    0x10FC9: 82,
    0x10FCA: 68,
    0x10FCB: 76,
    0x11001: 84,
    0x11038: 84,
    0x11039: 84,
    0x1103A: 84,
    0x1103B: 84,
    0x1103C: 84,
    0x1103D: 84,
    0x1103E: 84,
    0x1103F: 84,
    0x11040: 84,
    0x11041: 84,
    0x11042: 84,
    0x11043: 84,
    0x11044: 84,
    0x11045: 84,
    0x11046: 84,
    0x11070: 84,
    0x11073: 84,
    0x11074: 84,
    0x1107F: 84,
    0x11080: 84,
    0x11081: 84,
    0x110B3: 84,
    0x110B4: 84,
    0x110B5: 84,
    0x110B6: 84,
    0x110B9: 84,
    0x110BA: 84,
    0x110C2: 84,
    0x11100: 84,
    0x11101: 84,
    0x11102: 84,
    0x11127: 84,
    0x11128: 84,
    0x11129: 84,
    0x1112A: 84,
    0x1112B: 84,
    0x1112D: 84,
    0x1112E: 84,
    0x1112F: 84,
    0x11130: 84,
    0x11131: 84,
    0x11132: 84,
    0x11133: 84,
    0x11134: 84,
    0x11173: 84,
    0x11180: 84,
    0x11181: 84,
    0x111B6: 84,
    0x111B7: 84,
    0x111B8: 84,
    0x111B9: 84,
    0x111BA: 84,
    0x111BB: 84,
    0x111BC: 84,
    0x111BD: 84,
    0x111BE: 84,
    0x111C9: 84,
    0x111CA: 84,
    0x111CB: 84,
    0x111CC: 84,
    0x111CF: 84,
    0x1122F: 84,
    0x11230: 84,
    0x11231: 84,
    0x11234: 84,
    0x11236: 84,
    0x11237: 84,
    0x1123E: 84,
    0x11241: 84,
    0x112DF: 84,
    0x112E3: 84,
    0x112E4: 84,
    0x112E5: 84,
    0x112E6: 84,
    0x112E7: 84,
    0x112E8: 84,
    0x112E9: 84,
    0x112EA: 84,
    0x11300: 84,
    0x11301: 84,
    0x1133B: 84,
    0x1133C: 84,
    0x11340: 84,
    0x11366: 84,
    0x11367: 84,
    0x11368: 84,
    0x11369: 84,
    0x1136A: 84,
    0x1136B: 84,
    0x1136C: 84,
    0x11370: 84,
    0x11371: 84,
    0x11372: 84,
    0x11373: 84,
    0x11374: 84,
    0x11438: 84,
    0x11439: 84,
    0x1143A: 84,
    0x1143B: 84,
    0x1143C: 84,
    0x1143D: 84,
    0x1143E: 84,
    0x1143F: 84,
    0x11442: 84,
    0x11443: 84,
    0x11444: 84,
    0x11446: 84,
    0x1145E: 84,
    0x114B3: 84,
    0x114B4: 84,
    0x114B5: 84,
    0x114B6: 84,
    0x114B7: 84,
    0x114B8: 84,
    0x114BA: 84,
    0x114BF: 84,
    0x114C0: 84,
    0x114C2: 84,
    0x114C3: 84,
    0x115B2: 84,
    0x115B3: 84,
    0x115B4: 84,
    0x115B5: 84,
    0x115BC: 84,
    0x115BD: 84,
    0x115BF: 84,
    0x115C0: 84,
    0x115DC: 84,
    0x115DD: 84,
    0x11633: 84,
    0x11634: 84,
    0x11635: 84,
    0x11636: 84,
    0x11637: 84,
    0x11638: 84,
    0x11639: 84,
    0x1163A: 84,
    0x1163D: 84,
    0x1163F: 84,
    0x11640: 84,
    0x116AB: 84,
    0x116AD: 84,
    0x116B0: 84,
    0x116B1: 84,
    0x116B2: 84,
    0x116B3: 84,
    0x116B4: 84,
    0x116B5: 84,
    0x116B7: 84,
    0x1171D: 84,
    0x1171E: 84,
    0x1171F: 84,
    0x11722: 84,
    0x11723: 84,
    0x11724: 84,
    0x11725: 84,
    0x11727: 84,
    0x11728: 84,
    0x11729: 84,
    0x1172A: 84,
    0x1172B: 84,
    0x1182F: 84,
    0x11830: 84,
    0x11831: 84,
    0x11832: 84,
    0x11833: 84,
    0x11834: 84,
    0x11835: 84,
    0x11836: 84,
    0x11837: 84,
    0x11839: 84,
    0x1183A: 84,
    0x1193B: 84,
    0x1193C: 84,
    0x1193E: 84,
    0x11943: 84,
    0x119D4: 84,
    0x119D5: 84,
    0x119D6: 84,
    0x119D7: 84,
    0x119DA: 84,
    0x119DB: 84,
    0x119E0: 84,
    0x11A01: 84,
    0x11A02: 84,
    0x11A03: 84,
    0x11A04: 84,
    0x11A05: 84,
    0x11A06: 84,
    0x11A07: 84,
    0x11A08: 84,
    0x11A09: 84,
    0x11A0A: 84,
    0x11A33: 84,
    0x11A34: 84,
    0x11A35: 84,
    0x11A36: 84,
    0x11A37: 84,
    0x11A38: 84,
    0x11A3B: 84,
    0x11A3C: 84,
    0x11A3D: 84,
    0x11A3E: 84,
    0x11A47: 84,
    0x11A51: 84,
    0x11A52: 84,
    0x11A53: 84,
    0x11A54: 84,
    0x11A55: 84,
    0x11A56: 84,
    0x11A59: 84,
    0x11A5A: 84,
    0x11A5B: 84,
    0x11A8A: 84,
    0x11A8B: 84,
    0x11A8C: 84,
    0x11A8D: 84,
    0x11A8E: 84,
    0x11A8F: 84,
    0x11A90: 84,
    0x11A91: 84,
    0x11A92: 84,
    0x11A93: 84,
    0x11A94: 84,
    0x11A95: 84,
    0x11A96: 84,
    0x11A98: 84,
    0x11A99: 84,
    0x11C30: 84,
    0x11C31: 84,
    0x11C32: 84,
    0x11C33: 84,
    0x11C34: 84,
    0x11C35: 84,
    0x11C36: 84,
    0x11C38: 84,
    0x11C39: 84,
    0x11C3A: 84,
    0x11C3B: 84,
    0x11C3C: 84,
    0x11C3D: 84,
    0x11C3F: 84,
    0x11C92: 84,
    0x11C93: 84,
    0x11C94: 84,
    0x11C95: 84,
    0x11C96: 84,
    0x11C97: 84,
    0x11C98: 84,
    0x11C99: 84,
    0x11C9A: 84,
    0x11C9B: 84,
    0x11C9C: 84,
    0x11C9D: 84,
    0x11C9E: 84,
    0x11C9F: 84,
    0x11CA0: 84,
    0x11CA1: 84,
    0x11CA2: 84,
    0x11CA3: 84,
    0x11CA4: 84,
    0x11CA5: 84,
    0x11CA6: 84,
    0x11CA7: 84,
    0x11CAA: 84,
    0x11CAB: 84,
    0x11CAC: 84,
    0x11CAD: 84,
    0x11CAE: 84,
    0x11CAF: 84,
    0x11CB0: 84,
    0x11CB2: 84,
    0x11CB3: 84,
    0x11CB5: 84,
    0x11CB6: 84,
    0x11D31: 84,
    0x11D32: 84,
    0x11D33: 84,
    0x11D34: 84,
    0x11D35: 84,
    0x11D36: 84,
    0x11D3A: 84,
    0x11D3C: 84,
    0x11D3D: 84,
    0x11D3F: 84,
    0x11D40: 84,
    0x11D41: 84,
    0x11D42: 84,
    0x11D43: 84,
    0x11D44: 84,
    0x11D45: 84,
    0x11D47: 84,
    0x11D90: 84,
    0x11D91: 84,
    0x11D95: 84,
    0x11D97: 84,
    0x11EF3: 84,
    0x11EF4: 84,
    0x11F00: 84,
    0x11F01: 84,
    0x11F36: 84,
    0x11F37: 84,
    0x11F38: 84,
    0x11F39: 84,
    0x11F3A: 84,
    0x11F40: 84,
    0x11F42: 84,
    0x13430: 84,
    0x13431: 84,
    0x13432: 84,
    0x13433: 84,
    0x13434: 84,
    0x13435: 84,
    0x13436: 84,
    0x13437: 84,
    0x13438: 84,
    0x13439: 84,
    0x1343A: 84,
    0x1343B: 84,
    0x1343C: 84,
    0x1343D: 84,
    0x1343E: 84,
    0x1343F: 84,
    0x13440: 84,
    0x13447: 84,
    0x13448: 84,
    0x13449: 84,
    0x1344A: 84,
    0x1344B: 84,
    0x1344C: 84,
    0x1344D: 84,
    0x1344E: 84,
    0x1344F: 84,
    0x13450: 84,
    0x13451: 84,
    0x13452: 84,
    0x13453: 84,
    0x13454: 84,
    0x13455: 84,
    0x16AF0: 84,
    0x16AF1: 84,
    0x16AF2: 84,
    0x16AF3: 84,
    0x16AF4: 84,
    0x16B30: 84,
    0x16B31: 84,
    0x16B32: 84,
    0x16B33: 84,
    0x16B34: 84,
    0x16B35: 84,
    0x16B36: 84,
    0x16F4F: 84,
    0x16F8F: 84,
    0x16F90: 84,
    0x16F91: 84,
    0x16F92: 84,
    0x16FE4: 84,
    0x1BC9D: 84,
    0x1BC9E: 84,
    0x1BCA0: 84,
    0x1BCA1: 84,
    0x1BCA2: 84,
    0x1BCA3: 84,
    0x1CF00: 84,
    0x1CF01: 84,
    0x1CF02: 84,
    0x1CF03: 84,
    0x1CF04: 84,
    0x1CF05: 84,
    0x1CF06: 84,
    0x1CF07: 84,
    0x1CF08: 84,
    0x1CF09: 84,
    0x1CF0A: 84,
    0x1CF0B: 84,
    0x1CF0C: 84,
    0x1CF0D: 84,
    0x1CF0E: 84,
    0x1CF0F: 84,
    0x1CF10: 84,
    0x1CF11: 84,
    0x1CF12: 84,
    0x1CF13: 84,
    0x1CF14: 84,
    0x1CF15: 84,
    0x1CF16: 84,
    0x1CF17: 84,
    0x1CF18: 84,
    0x1CF19: 84,
    0x1CF1A: 84,
    0x1CF1B: 84,
    0x1CF1C: 84,
    0x1CF1D: 84,
    0x1CF1E: 84,
    0x1CF1F: 84,
    0x1CF20: 84,
    0x1CF21: 84,
    0x1CF22: 84,
    0x1CF23: 84,
    0x1CF24: 84,
    0x1CF25: 84,
    0x1CF26: 84,
    0x1CF27: 84,
    0x1CF28: 84,
    0x1CF29: 84,
    0x1CF2A: 84,
    0x1CF2B: 84,
    0x1CF2C: 84,
    0x1CF2D: 84,
    0x1CF30: 84,
    0x1CF31: 84,
    0x1CF32: 84,
    0x1CF33: 84,
    0x1CF34: 84,
    0x1CF35: 84,
    0x1CF36: 84,
    0x1CF37: 84,
    0x1CF38: 84,
    0x1CF39: 84,
    0x1CF3A: 84,
    0x1CF3B: 84,
    0x1CF3C: 84,
    0x1CF3D: 84,
    0x1CF3E: 84,
    0x1CF3F: 84,
    0x1CF40: 84,
    0x1CF41: 84,
    0x1CF42: 84,
    0x1CF43: 84,
    0x1CF44: 84,
    0x1CF45: 84,
    0x1CF46: 84,
    0x1D167: 84,
    0x1D168: 84,
    0x1D169: 84,
    0x1D173: 84,
    0x1D174: 84,
    0x1D175: 84,
    0x1D176: 84,
    0x1D177: 84,
    0x1D178: 84,
    0x1D179: 84,
    0x1D17A: 84,
    0x1D17B: 84,
    0x1D17C: 84,
    0x1D17D: 84,
    0x1D17E: 84,
    0x1D17F: 84,
    0x1D180: 84,
    0x1D181: 84,
    0x1D182: 84,
    0x1D185: 84,
    0x1D186: 84,
    0x1D187: 84,
    0x1D188: 84,
    0x1D189: 84,
    0x1D18A: 84,
    0x1D18B: 84,
    0x1D1AA: 84,
    0x1D1AB: 84,
    0x1D1AC: 84,
    0x1D1AD: 84,
    0x1D242: 84,
    0x1D243: 84,
    0x1D244: 84,
    0x1DA00: 84,
    0x1DA01: 84,
    0x1DA02: 84,
    0x1DA03: 84,
    0x1DA04: 84,
    0x1DA05: 84,
    0x1DA06: 84,
    0x1DA07: 84,
    0x1DA08: 84,
    0x1DA09: 84,
    0x1DA0A: 84,
    0x1DA0B: 84,
    0x1DA0C: 84,
    0x1DA0D: 84,
    0x1DA0E: 84,
    0x1DA0F: 84,
    0x1DA10: 84,
    0x1DA11: 84,
    0x1DA12: 84,
    0x1DA13: 84,
    0x1DA14: 84,
    0x1DA15: 84,
    0x1DA16: 84,
    0x1DA17: 84,
    0x1DA18: 84,
    0x1DA19: 84,
    0x1DA1A: 84,
    0x1DA1B: 84,
    0x1DA1C: 84,
    0x1DA1D: 84,
    0x1DA1E: 84,
    0x1DA1F: 84,
    0x1DA20: 84,
    0x1DA21: 84,
    0x1DA22: 84,
    0x1DA23: 84,
    0x1DA24: 84,
    0x1DA25: 84,
    0x1DA26: 84,
    0x1DA27: 84,
    0x1DA28: 84,
    0x1DA29: 84,
    0x1DA2A: 84,
    0x1DA2B: 84,
    0x1DA2C: 84,
    0x1DA2D: 84,
    0x1DA2E: 84,
    0x1DA2F: 84,
    0x1DA30: 84,
    0x1DA31: 84,
    0x1DA32: 84,
    0x1DA33: 84,
    0x1DA34: 84,
    0x1DA35: 84,
    0x1DA36: 84,
    0x1DA3B: 84,
    0x1DA3C: 84,
    0x1DA3D: 84,
    0x1DA3E: 84,
    0x1DA3F: 84,
    0x1DA40: 84,
    0x1DA41: 84,
    0x1DA42: 84,
    0x1DA43: 84,
    0x1DA44: 84,
    0x1DA45: 84,
    0x1DA46: 84,
    0x1DA47: 84,
    0x1DA48: 84,
    0x1DA49: 84,
    0x1DA4A: 84,
    0x1DA4B: 84,
    0x1DA4C: 84,
    0x1DA4D: 84,
    0x1DA4E: 84,
    0x1DA4F: 84,
    0x1DA50: 84,
    0x1DA51: 84,
    0x1DA52: 84,
    0x1DA53: 84,
    0x1DA54: 84,
    0x1DA55: 84,
    0x1DA56: 84,
    0x1DA57: 84,
    0x1DA58: 84,
    0x1DA59: 84,
    0x1DA5A: 84,
    0x1DA5B: 84,
    0x1DA5C: 84,
    0x1DA5D: 84,
    0x1DA5E: 84,
    0x1DA5F: 84,
    0x1DA60: 84,
    0x1DA61: 84,
    0x1DA62: 84,
    0x1DA63: 84,
    0x1DA64: 84,
    0x1DA65: 84,
    0x1DA66: 84,
    0x1DA67: 84,
    0x1DA68: 84,
    0x1DA69: 84,
    0x1DA6A: 84,
    0x1DA6B: 84,
    0x1DA6C: 84,
    0x1DA75: 84,
    0x1DA84: 84,
    0x1DA9B: 84,
    0x1DA9C: 84,
    0x1DA9D: 84,
    0x1DA9E: 84,
    0x1DA9F: 84,
    0x1DAA1: 84,
    0x1DAA2: 84,
    0x1DAA3: 84,
    0x1DAA4: 84,
    0x1DAA5: 84,
    0x1DAA6: 84,
    0x1DAA7: 84,
    0x1DAA8: 84,
    0x1DAA9: 84,
    0x1DAAA: 84,
    0x1DAAB: 84,
    0x1DAAC: 84,
    0x1DAAD: 84,
    0x1DAAE: 84,
    0x1DAAF: 84,
    0x1E000: 84,
    0x1E001: 84,
    0x1E002: 84,
    0x1E003: 84,
    0x1E004: 84,
    0x1E005: 84,
    0x1E006: 84,
    0x1E008: 84,
    0x1E009: 84,
    0x1E00A: 84,
    0x1E00B: 84,
    0x1E00C: 84,
    0x1E00D: 84,
    0x1E00E: 84,
    0x1E00F: 84,
    0x1E010: 84,
    0x1E011: 84,
    0x1E012: 84,
    0x1E013: 84,
    0x1E014: 84,
    0x1E015: 84,
    0x1E016: 84,
    0x1E017: 84,
    0x1E018: 84,
    0x1E01B: 84,
    0x1E01C: 84,
    0x1E01D: 84,
    0x1E01E: 84,
    0x1E01F: 84,
    0x1E020: 84,
    0x1E021: 84,
    0x1E023: 84,
    0x1E024: 84,
    0x1E026: 84,
    0x1E027: 84,
    0x1E028: 84,
    0x1E029: 84,
    0x1E02A: 84,
    0x1E08F: 84,
    0x1E130: 84,
    0x1E131: 84,
    0x1E132: 84,
    0x1E133: 84,
    0x1E134: 84,
    0x1E135: 84,
    0x1E136: 84,
    0x1E2AE: 84,
    0x1E2EC: 84,
    0x1E2ED: 84,
    0x1E2EE: 84,
    0x1E2EF: 84,
    0x1E4EC: 84,
    0x1E4ED: 84,
    0x1E4EE: 84,
    0x1E4EF: 84,
    0x1E8D0: 84,
    0x1E8D1: 84,
    0x1E8D2: 84,
    0x1E8D3: 84,
    0x1E8D4: 84,
    0x1E8D5: 84,
    0x1E8D6: 84,
    0x1E900: 68,
    0x1E901: 68,
    0x1E902: 68,
    0x1E903: 68,
    0x1E904: 68,
    0x1E905: 68,
    0x1E906: 68,
    0x1E907: 68,
    0x1E908: 68,
    0x1E909: 68,
    0x1E90A: 68,
    0x1E90B: 68,
    0x1E90C: 68,
    0x1E90D: 68,
    0x1E90E: 68,
    0x1E90F: 68,
    0x1E910: 68,
    0x1E911: 68,
    0x1E912: 68,
    0x1E913: 68,
    0x1E914: 68,
    0x1E915: 68,
    0x1E916: 68,
    0x1E917: 68,
    0x1E918: 68,
    0x1E919: 68,
    0x1E91A: 68,
    0x1E91B: 68,
    0x1E91C: 68,
    0x1E91D: 68,
    0x1E91E: 68,
    0x1E91F: 68,
    0x1E920: 68,
    0x1E921: 68,
    0x1E922: 68,
    0x1E923: 68,
    0x1E924: 68,
    0x1E925: 68,
    0x1E926: 68,
    0x1E927: 68,
    0x1E928: 68,
    0x1E929: 68,
    0x1E92A: 68,
    0x1E92B: 68,
    0x1E92C: 68,
    0x1E92D: 68,
    0x1E92E: 68,
    0x1E92F: 68,
    0x1E930: 68,
    0x1E931: 68,
    0x1E932: 68,
    0x1E933: 68,
    0x1E934: 68,
    0x1E935: 68,
    0x1E936: 68,
    0x1E937: 68,
    0x1E938: 68,
    0x1E939: 68,
    0x1E93A: 68,
    0x1E93B: 68,
    0x1E93C: 68,
    0x1E93D: 68,
    0x1E93E: 68,
    0x1E93F: 68,
    0x1E940: 68,
    0x1E941: 68,
    0x1E942: 68,
    0x1E943: 68,
    0x1E944: 84,
    0x1E945: 84,
    0x1E946: 84,
    0x1E947: 84,
    0x1E948: 84,
    0x1E949: 84,
    0x1E94A: 84,
    0x1E94B: 84,
    0xE0001: 84,
    0xE0020: 84,
    0xE0021: 84,
    0xE0022: 84,
    0xE0023: 84,
    0xE0024: 84,
    0xE0025: 84,
    0xE0026: 84,
    0xE0027: 84,
    0xE0028: 84,
    0xE0029: 84,
    0xE002A: 84,
    0xE002B: 84,
    0xE002C: 84,
    0xE002D: 84,
    0xE002E: 84,
    0xE002F: 84,
    0xE0030: 84,
    0xE0031: 84,
    0xE0032: 84,
    0xE0033: 84,
    0xE0034: 84,
    0xE0035: 84,
    0xE0036: 84,
    0xE0037: 84,
    0xE0038: 84,
    0xE0039: 84,
    0xE003A: 84,
    0xE003B: 84,
    0xE003C: 84,
    0xE003D: 84,
    0xE003E: 84,
    0xE003F: 84,
    0xE0040: 84,
    0xE0041: 84,
    0xE0042: 84,
    0xE0043: 84,
    0xE0044: 84,
    0xE0045: 84,
    0xE0046: 84,
    0xE0047: 84,
    0xE0048: 84,
    0xE0049: 84,
    0xE004A: 84,
    0xE004B: 84,
    0xE004C: 84,
    0xE004D: 84,
    0xE004E: 84,
    0xE004F: 84,
    0xE0050: 84,
    0xE0051: 84,
    0xE0052: 84,
    0xE0053: 84,
    0xE0054: 84,
    0xE0055: 84,
    0xE0056: 84,
    0xE0057: 84,
    0xE0058: 84,
    0xE0059: 84,
    0xE005A: 84,
    0xE005B: 84,
    0xE005C: 84,
    0xE005D: 84,
    0xE005E: 84,
    0xE005F: 84,
    0xE0060: 84,
    0xE0061: 84,
    0xE0062: 84,
    0xE0063: 84,
    0xE0064: 84,
    0xE0065: 84,
    0xE0066: 84,
    0xE0067: 84,
    0xE0068: 84,
    0xE0069: 84,
    0xE006A: 84,
    0xE006B: 84,
    0xE006C: 84,
    0xE006D: 84,
    0xE006E: 84,
    0xE006F: 84,
    0xE0070: 84,
    0xE0071: 84,
    0xE0072: 84,
    0xE0073: 84,
    0xE0074: 84,
    0xE0075: 84,
    0xE0076: 84,
    0xE0077: 84,
    0xE0078: 84,
    0xE0079: 84,
    0xE007A: 84,
    0xE007B: 84,
    0xE007C: 84,
    0xE007D: 84,
    0xE007E: 84,
    0xE007F: 84,
    0xE0100: 84,
    0xE0101: 84,
    0xE0102: 84,
    0xE0103: 84,
    0xE0104: 84,
    0xE0105: 84,
    0xE0106: 84,
    0xE0107: 84,
    0xE0108: 84,
    0xE0109: 84,
    0xE010A: 84,
    0xE010B: 84,
    0xE010C: 84,
    0xE010D: 84,
    0xE010E: 84,
    0xE010F: 84,
    0xE0110: 84,
    0xE0111: 84,
    0xE0112: 84,
    0xE0113: 84,
    0xE0114: 84,
    0xE0115: 84,
    0xE0116: 84,
    0xE0117: 84,
    0xE0118: 84,
    0xE0119: 84,
    0xE011A: 84,
    0xE011B: 84,
    0xE011C: 84,
    0xE011D: 84,
    0xE011E: 84,
    0xE011F: 84,
    0xE0120: 84,
    0xE0121: 84,
    0xE0122: 84,
    0xE0123: 84,
    0xE0124: 84,
    0xE0125: 84,
    0xE0126: 84,
    0xE0127: 84,
    0xE0128: 84,
    0xE0129: 84,
    0xE012A: 84,
    0xE012B: 84,
    0xE012C: 84,
    0xE012D: 84,
    0xE012E: 84,
    0xE012F: 84,
    0xE0130: 84,
    0xE0131: 84,
    0xE0132: 84,
    0xE0133: 84,
    0xE0134: 84,
    0xE0135: 84,
    0xE0136: 84,
    0xE0137: 84,
    0xE0138: 84,
    0xE0139: 84,
    0xE013A: 84,
    0xE013B: 84,
    0xE013C: 84,
    0xE013D: 84,
    0xE013E: 84,
    0xE013F: 84,
    0xE0140: 84,
    0xE0141: 84,
    0xE0142: 84,
    0xE0143: 84,
    0xE0144: 84,
    0xE0145: 84,
    0xE0146: 84,
    0xE0147: 84,
    0xE0148: 84,
    0xE0149: 84,
    0xE014A: 84,
    0xE014B: 84,
    0xE014C: 84,
    0xE014D: 84,
    0xE014E: 84,
    0xE014F: 84,
    0xE0150: 84,
    0xE0151: 84,
    0xE0152: 84,
    0xE0153: 84,
    0xE0154: 84,
    0xE0155: 84,
    0xE0156: 84,
    0xE0157: 84,
    0xE0158: 84,
    0xE0159: 84,
    0xE015A: 84,
    0xE015B: 84,
    0xE015C: 84,
    0xE015D: 84,
    0xE015E: 84,
    0xE015F: 84,
    0xE0160: 84,
    0xE0161: 84,
    0xE0162: 84,
    0xE0163: 84,
    0xE0164: 84,
    0xE0165: 84,
    0xE0166: 84,
    0xE0167: 84,
    0xE0168: 84,
    0xE0169: 84,
    0xE016A: 84,
    0xE016B: 84,
    0xE016C: 84,
    0xE016D: 84,
    0xE016E: 84,
    0xE016F: 84,
    0xE0170: 84,
    0xE0171: 84,
    0xE0172: 84,
    0xE0173: 84,
    0xE0174: 84,
    0xE0175: 84,
    0xE0176: 84,
    0xE0177: 84,
    0xE0178: 84,
    0xE0179: 84,
    0xE017A: 84,
    0xE017B: 84,
    0xE017C: 84,
    0xE017D: 84,
    0xE017E: 84,
    0xE017F: 84,
    0xE0180: 84,
    0xE0181: 84,
    0xE0182: 84,
    0xE0183: 84,
    0xE0184: 84,
    0xE0185: 84,
    0xE0186: 84,
    0xE0187: 84,
    0xE0188: 84,
    0xE0189: 84,
    0xE018A: 84,
    0xE018B: 84,
    0xE018C: 84,
    0xE018D: 84,
    0xE018E: 84,
    0xE018F: 84,
    0xE0190: 84,
    0xE0191: 84,
    0xE0192: 84,
    0xE0193: 84,
    0xE0194: 84,
    0xE0195: 84,
    0xE0196: 84,
    0xE0197: 84,
    0xE0198: 84,
    0xE0199: 84,
    0xE019A: 84,
    0xE019B: 84,
    0xE019C: 84,
    0xE019D: 84,
    0xE019E: 84,
    0xE019F: 84,
    0xE01A0: 84,
    0xE01A1: 84,
    0xE01A2: 84,
    0xE01A3: 84,
    0xE01A4: 84,
    0xE01A5: 84,
    0xE01A6: 84,
    0xE01A7: 84,
    0xE01A8: 84,
    0xE01A9: 84,
    0xE01AA: 84,
    0xE01AB: 84,
    0xE01AC: 84,
    0xE01AD: 84,
    0xE01AE: 84,
    0xE01AF: 84,
    0xE01B0: 84,
    0xE01B1: 84,
    0xE01B2: 84,
    0xE01B3: 84,
    0xE01B4: 84,
    0xE01B5: 84,
    0xE01B6: 84,
    0xE01B7: 84,
    0xE01B8: 84,
    0xE01B9: 84,
    0xE01BA: 84,
    0xE01BB: 84,
    0xE01BC: 84,
    0xE01BD: 84,
    0xE01BE: 84,
    0xE01BF: 84,
    0xE01C0: 84,
    0xE01C1: 84,
    0xE01C2: 84,
    0xE01C3: 84,
    0xE01C4: 84,
    0xE01C5: 84,
    0xE01C6: 84,
    0xE01C7: 84,
    0xE01C8: 84,
    0xE01C9: 84,
    0xE01CA: 84,
    0xE01CB: 84,
    0xE01CC: 84,
    0xE01CD: 84,
    0xE01CE: 84,
    0xE01CF: 84,
    0xE01D0: 84,
    0xE01D1: 84,
    0xE01D2: 84,
    0xE01D3: 84,
    0xE01D4: 84,
    0xE01D5: 84,
    0xE01D6: 84,
    0xE01D7: 84,
    0xE01D8: 84,
    0xE01D9: 84,
    0xE01DA: 84,
    0xE01DB: 84,
    0xE01DC: 84,
    0xE01DD: 84,
    0xE01DE: 84,
    0xE01DF: 84,
    0xE01E0: 84,
    0xE01E1: 84,
    0xE01E2: 84,
    0xE01E3: 84,
    0xE01E4: 84,
    0xE01E5: 84,
    0xE01E6: 84,
    0xE01E7: 84,
    0xE01E8: 84,
    0xE01E9: 84,
    0xE01EA: 84,
    0xE01EB: 84,
    0xE01EC: 84,
    0xE01ED: 84,
    0xE01EE: 84,
    0xE01EF: 84,
}
codepoint_classes = {
    "PVALID": (
        0x2D0000002E,
        0x300000003A,
        0x610000007B,
        0xDF000000F7,
        0xF800000100,
        0x10100000102,
        0x10300000104,
        0x10500000106,
        0x10700000108,
        0x1090000010A,
        0x10B0000010C,
        0x10D0000010E,
        0x10F00000110,
        0x11100000112,
        0x11300000114,
        0x11500000116,
        0x11700000118,
        0x1190000011A,
        0x11B0000011C,
        0x11D0000011E,
        0x11F00000120,
        0x12100000122,
        0x12300000124,
        0x12500000126,
        0x12700000128,
        0x1290000012A,
        0x12B0000012C,
        0x12D0000012E,
        0x12F00000130,
        0x13100000132,
        0x13500000136,
        0x13700000139,
        0x13A0000013B,
        0x13C0000013D,
        0x13E0000013F,
        0x14200000143,
        0x14400000145,
        0x14600000147,
        0x14800000149,
        0x14B0000014C,
        0x14D0000014E,
        0x14F00000150,
        0x15100000152,
        0x15300000154,
        0x15500000156,
        0x15700000158,
        0x1590000015A,
        0x15B0000015C,
        0x15D0000015E,
        0x15F00000160,
        0x16100000162,
        0x16300000164,
        0x16500000166,
        0x16700000168,
        0x1690000016A,
        0x16B0000016C,
        0x16D0000016E,
        0x16F00000170,
        0x17100000172,
        0x17300000174,
        0x17500000176,
        0x17700000178,
        0x17A0000017B,
        0x17C0000017D,
        0x17E0000017F,
        0x18000000181,
        0x18300000184,
        0x18500000186,
        0x18800000189,
        0x18C0000018E,
        0x19200000193,
        0x19500000196,
        0x1990000019C,
        0x19E0000019F,
        0x1A1000001A2,
        0x1A3000001A4,
        0x1A5000001A6,
        0x1A8000001A9,
        0x1AA000001AC,
        0x1AD000001AE,
        0x1B0000001B1,
        0x1B4000001B5,
        0x1B6000001B7,
        0x1B9000001BC,
        0x1BD000001C4,
        0x1CE000001CF,
        0x1D0000001D1,
        0x1D2000001D3,
        0x1D4000001D5,
        0x1D6000001D7,
        0x1D8000001D9,
        0x1DA000001DB,
        0x1DC000001DE,
        0x1DF000001E0,
        0x1E1000001E2,
        0x1E3000001E4,
        0x1E5000001E6,
        0x1E7000001E8,
        0x1E9000001EA,
        0x1EB000001EC,
        0x1ED000001EE,
        0x1EF000001F1,
        0x1F5000001F6,
        0x1F9000001FA,
        0x1FB000001FC,
        0x1FD000001FE,
        0x1FF00000200,
        0x20100000202,
        0x20300000204,
        0x20500000206,
        0x20700000208,
        0x2090000020A,
        0x20B0000020C,
        0x20D0000020E,
        0x20F00000210,
        0x21100000212,
        0x21300000214,
        0x21500000216,
        0x21700000218,
        0x2190000021A,
        0x21B0000021C,
        0x21D0000021E,
        0x21F00000220,
        0x22100000222,
        0x22300000224,
        0x22500000226,
        0x22700000228,
        0x2290000022A,
        0x22B0000022C,
        0x22D0000022E,
        0x22F00000230,
        0x23100000232,
        0x2330000023A,
        0x23C0000023D,
        0x23F00000241,
        0x24200000243,
        0x24700000248,
        0x2490000024A,
        0x24B0000024C,
        0x24D0000024E,
        0x24F000002B0,
        0x2B9000002C2,
        0x2C6000002D2,
        0x2EC000002ED,
        0x2EE000002EF,
        0x30000000340,
        0x34200000343,
        0x3460000034F,
        0x35000000370,
        0x37100000372,
        0x37300000374,
        0x37700000378,
        0x37B0000037E,
        0x39000000391,
        0x3AC000003CF,
        0x3D7000003D8,
        0x3D9000003DA,
        0x3DB000003DC,
        0x3DD000003DE,
        0x3DF000003E0,
        0x3E1000003E2,
        0x3E3000003E4,
        0x3E5000003E6,
        0x3E7000003E8,
        0x3E9000003EA,
        0x3EB000003EC,
        0x3ED000003EE,
        0x3EF000003F0,
        0x3F3000003F4,
        0x3F8000003F9,
        0x3FB000003FD,
        0x43000000460,
        0x46100000462,
        0x46300000464,
        0x46500000466,
        0x46700000468,
        0x4690000046A,
        0x46B0000046C,
        0x46D0000046E,
        0x46F00000470,
        0x47100000472,
        0x47300000474,
        0x47500000476,
        0x47700000478,
        0x4790000047A,
        0x47B0000047C,
        0x47D0000047E,
        0x47F00000480,
        0x48100000482,
        0x48300000488,
        0x48B0000048C,
        0x48D0000048E,
        0x48F00000490,
        0x49100000492,
        0x49300000494,
        0x49500000496,
        0x49700000498,
        0x4990000049A,
        0x49B0000049C,
        0x49D0000049E,
        0x49F000004A0,
        0x4A1000004A2,
        0x4A3000004A4,
        0x4A5000004A6,
        0x4A7000004A8,
        0x4A9000004AA,
        0x4AB000004AC,
        0x4AD000004AE,
        0x4AF000004B0,
        0x4B1000004B2,
        0x4B3000004B4,
        0x4B5000004B6,
        0x4B7000004B8,
        0x4B9000004BA,
        0x4BB000004BC,
        0x4BD000004BE,
        0x4BF000004C0,
        0x4C2000004C3,
        0x4C4000004C5,
        0x4C6000004C7,
        0x4C8000004C9,
        0x4CA000004CB,
        0x4CC000004CD,
        0x4CE000004D0,
        0x4D1000004D2,
        0x4D3000004D4,
        0x4D5000004D6,
        0x4D7000004D8,
        0x4D9000004DA,
        0x4DB000004DC,
        0x4DD000004DE,
        0x4DF000004E0,
        0x4E1000004E2,
        0x4E3000004E4,
        0x4E5000004E6,
        0x4E7000004E8,
        0x4E9000004EA,
        0x4EB000004EC,
        0x4ED000004EE,
        0x4EF000004F0,
        0x4F1000004F2,
        0x4F3000004F4,
        0x4F5000004F6,
        0x4F7000004F8,
        0x4F9000004FA,
        0x4FB000004FC,
        0x4FD000004FE,
        0x4FF00000500,
        0x50100000502,
        0x50300000504,
        0x50500000506,
        0x50700000508,
        0x5090000050A,
        0x50B0000050C,
        0x50D0000050E,
        0x50F00000510,
        0x51100000512,
        0x51300000514,
        0x51500000516,
        0x51700000518,
        0x5190000051A,
        0x51B0000051C,
        0x51D0000051E,
        0x51F00000520,
        0x52100000522,
        0x52300000524,
        0x52500000526,
        0x52700000528,
        0x5290000052A,
        0x52B0000052C,
        0x52D0000052E,
        0x52F00000530,
        0x5590000055A,
        0x56000000587,
        0x58800000589,
        0x591000005BE,
        0x5BF000005C0,
        0x5C1000005C3,
        0x5C4000005C6,
        0x5C7000005C8,
        0x5D0000005EB,
        0x5EF000005F3,
        0x6100000061B,
        0x62000000640,
        0x64100000660,
        0x66E00000675,
        0x679000006D4,
        0x6D5000006DD,
        0x6DF000006E9,
        0x6EA000006F0,
        0x6FA00000700,
        0x7100000074B,
        0x74D000007B2,
        0x7C0000007F6,
        0x7FD000007FE,
        0x8000000082E,
        0x8400000085C,
        0x8600000086B,
        0x87000000888,
        0x8890000088F,
        0x898000008E2,
        0x8E300000958,
        0x96000000964,
        0x96600000970,
        0x97100000984,
        0x9850000098D,
        0x98F00000991,
        0x993000009A9,
        0x9AA000009B1,
        0x9B2000009B3,
        0x9B6000009BA,
        0x9BC000009C5,
        0x9C7000009C9,
        0x9CB000009CF,
        0x9D7000009D8,
        0x9E0000009E4,
        0x9E6000009F2,
        0x9FC000009FD,
        0x9FE000009FF,
        0xA0100000A04,
        0xA0500000A0B,
        0xA0F00000A11,
        0xA1300000A29,
        0xA2A00000A31,
        0xA3200000A33,
        0xA3500000A36,
        0xA3800000A3A,
        0xA3C00000A3D,
        0xA3E00000A43,
        0xA4700000A49,
        0xA4B00000A4E,
        0xA5100000A52,
        0xA5C00000A5D,
        0xA6600000A76,
        0xA8100000A84,
        0xA8500000A8E,
        0xA8F00000A92,
        0xA9300000AA9,
        0xAAA00000AB1,
        0xAB200000AB4,
        0xAB500000ABA,
        0xABC00000AC6,
        0xAC700000ACA,
        0xACB00000ACE,
        0xAD000000AD1,
        0xAE000000AE4,
        0xAE600000AF0,
        0xAF900000B00,
        0xB0100000B04,
        0xB0500000B0D,
        0xB0F00000B11,
        0xB1300000B29,
        0xB2A00000B31,
        0xB3200000B34,
        0xB3500000B3A,
        0xB3C00000B45,
        0xB4700000B49,
        0xB4B00000B4E,
        0xB5500000B58,
        0xB5F00000B64,
        0xB6600000B70,
        0xB7100000B72,
        0xB8200000B84,
        0xB8500000B8B,
        0xB8E00000B91,
        0xB9200000B96,
        0xB9900000B9B,
        0xB9C00000B9D,
        0xB9E00000BA0,
        0xBA300000BA5,
        0xBA800000BAB,
        0xBAE00000BBA,
        0xBBE00000BC3,
        0xBC600000BC9,
        0xBCA00000BCE,
        0xBD000000BD1,
        0xBD700000BD8,
        0xBE600000BF0,
        0xC0000000C0D,
        0xC0E00000C11,
        0xC1200000C29,
        0xC2A00000C3A,
        0xC3C00000C45,
        0xC4600000C49,
        0xC4A00000C4E,
        0xC5500000C57,
        0xC5800000C5B,
        0xC5D00000C5E,
        0xC6000000C64,
        0xC6600000C70,
        0xC8000000C84,
        0xC8500000C8D,
        0xC8E00000C91,
        0xC9200000CA9,
        0xCAA00000CB4,
        0xCB500000CBA,
        0xCBC00000CC5,
        0xCC600000CC9,
        0xCCA00000CCE,
        0xCD500000CD7,
        0xCDD00000CDF,
        0xCE000000CE4,
        0xCE600000CF0,
        0xCF100000CF4,
        0xD0000000D0D,
        0xD0E00000D11,
        0xD1200000D45,
        0xD4600000D49,
        0xD4A00000D4F,
        0xD5400000D58,
        0xD5F00000D64,
        0xD6600000D70,
        0xD7A00000D80,
        0xD8100000D84,
        0xD8500000D97,
        0xD9A00000DB2,
        0xDB300000DBC,
        0xDBD00000DBE,
        0xDC000000DC7,
        0xDCA00000DCB,
        0xDCF00000DD5,
        0xDD600000DD7,
        0xDD800000DE0,
        0xDE600000DF0,
        0xDF200000DF4,
        0xE0100000E33,
        0xE3400000E3B,
        0xE4000000E4F,
        0xE5000000E5A,
        0xE8100000E83,
        0xE8400000E85,
        0xE8600000E8B,
        0xE8C00000EA4,
        0xEA500000EA6,
        0xEA700000EB3,
        0xEB400000EBE,
        0xEC000000EC5,
        0xEC600000EC7,
        0xEC800000ECF,
        0xED000000EDA,
        0xEDE00000EE0,
        0xF0000000F01,
        0xF0B00000F0C,
        0xF1800000F1A,
        0xF2000000F2A,
        0xF3500000F36,
        0xF3700000F38,
        0xF3900000F3A,
        0xF3E00000F43,
        0xF4400000F48,
        0xF4900000F4D,
        0xF4E00000F52,
        0xF5300000F57,
        0xF5800000F5C,
        0xF5D00000F69,
        0xF6A00000F6D,
        0xF7100000F73,
        0xF7400000F75,
        0xF7A00000F81,
        0xF8200000F85,
        0xF8600000F93,
        0xF9400000F98,
        0xF9900000F9D,
        0xF9E00000FA2,
        0xFA300000FA7,
        0xFA800000FAC,
        0xFAD00000FB9,
        0xFBA00000FBD,
        0xFC600000FC7,
        0x10000000104A,
        0x10500000109E,
        0x10D0000010FB,
        0x10FD00001100,
        0x120000001249,
        0x124A0000124E,
        0x125000001257,
        0x125800001259,
        0x125A0000125E,
        0x126000001289,
        0x128A0000128E,
        0x1290000012B1,
        0x12B2000012B6,
        0x12B8000012BF,
        0x12C0000012C1,
        0x12C2000012C6,
        0x12C8000012D7,
        0x12D800001311,
        0x131200001316,
        0x13180000135B,
        0x135D00001360,
        0x138000001390,
        0x13A0000013F6,
        0x14010000166D,
        0x166F00001680,
        0x16810000169B,
        0x16A0000016EB,
        0x16F1000016F9,
        0x170000001716,
        0x171F00001735,
        0x174000001754,
        0x17600000176D,
        0x176E00001771,
        0x177200001774,
        0x1780000017B4,
        0x17B6000017D4,
        0x17D7000017D8,
        0x17DC000017DE,
        0x17E0000017EA,
        0x18100000181A,
        0x182000001879,
        0x1880000018AB,
        0x18B0000018F6,
        0x19000000191F,
        0x19200000192C,
        0x19300000193C,
        0x19460000196E,
        0x197000001975,
        0x1980000019AC,
        0x19B0000019CA,
        0x19D0000019DA,
        0x1A0000001A1C,
        0x1A2000001A5F,
        0x1A6000001A7D,
        0x1A7F00001A8A,
        0x1A9000001A9A,
        0x1AA700001AA8,
        0x1AB000001ABE,
        0x1ABF00001ACF,
        0x1B0000001B4D,
        0x1B5000001B5A,
        0x1B6B00001B74,
        0x1B8000001BF4,
        0x1C0000001C38,
        0x1C4000001C4A,
        0x1C4D00001C7E,
        0x1CD000001CD3,
        0x1CD400001CFB,
        0x1D0000001D2C,
        0x1D2F00001D30,
        0x1D3B00001D3C,
        0x1D4E00001D4F,
        0x1D6B00001D78,
        0x1D7900001D9B,
        0x1DC000001E00,
        0x1E0100001E02,
        0x1E0300001E04,
        0x1E0500001E06,
        0x1E0700001E08,
        0x1E0900001E0A,
        0x1E0B00001E0C,
        0x1E0D00001E0E,
        0x1E0F00001E10,
        0x1E1100001E12,
        0x1E1300001E14,
        0x1E1500001E16,
        0x1E1700001E18,
        0x1E1900001E1A,
        0x1E1B00001E1C,
        0x1E1D00001E1E,
        0x1E1F00001E20,
        0x1E2100001E22,
        0x1E2300001E24,
        0x1E2500001E26,
        0x1E2700001E28,
        0x1E2900001E2A,
        0x1E2B00001E2C,
        0x1E2D00001E2E,
        0x1E2F00001E30,
        0x1E3100001E32,
        0x1E3300001E34,
        0x1E3500001E36,
        0x1E3700001E38,
        0x1E3900001E3A,
        0x1E3B00001E3C,
        0x1E3D00001E3E,
        0x1E3F00001E40,
        0x1E4100001E42,
        0x1E4300001E44,
        0x1E4500001E46,
        0x1E4700001E48,
        0x1E4900001E4A,
        0x1E4B00001E4C,
        0x1E4D00001E4E,
        0x1E4F00001E50,
        0x1E5100001E52,
        0x1E5300001E54,
        0x1E5500001E56,
        0x1E5700001E58,
        0x1E5900001E5A,
        0x1E5B00001E5C,
        0x1E5D00001E5E,
        0x1E5F00001E60,
        0x1E6100001E62,
        0x1E6300001E64,
        0x1E6500001E66,
        0x1E6700001E68,
        0x1E6900001E6A,
        0x1E6B00001E6C,
        0x1E6D00001E6E,
        0x1E6F00001E70,
        0x1E7100001E72,
        0x1E7300001E74,
        0x1E7500001E76,
        0x1E7700001E78,
        0x1E7900001E7A,
        0x1E7B00001E7C,
        0x1E7D00001E7E,
        0x1E7F00001E80,
        0x1E8100001E82,
        0x1E8300001E84,
        0x1E8500001E86,
        0x1E8700001E88,
        0x1E8900001E8A,
        0x1E8B00001E8C,
        0x1E8D00001E8E,
        0x1E8F00001E90,
        0x1E9100001E92,
        0x1E9300001E94,
        0x1E9500001E9A,
        0x1E9C00001E9E,
        0x1E9F00001EA0,
        0x1EA100001EA2,
        0x1EA300001EA4,
        0x1EA500001EA6,
        0x1EA700001EA8,
        0x1EA900001EAA,
        0x1EAB00001EAC,
        0x1EAD00001EAE,
        0x1EAF00001EB0,
        0x1EB100001EB2,
        0x1EB300001EB4,
        0x1EB500001EB6,
        0x1EB700001EB8,
        0x1EB900001EBA,
        0x1EBB00001EBC,
        0x1EBD00001EBE,
        0x1EBF00001EC0,
        0x1EC100001EC2,
        0x1EC300001EC4,
        0x1EC500001EC6,
        0x1EC700001EC8,
        0x1EC900001ECA,
        0x1ECB00001ECC,
        0x1ECD00001ECE,
        0x1ECF00001ED0,
        0x1ED100001ED2,
        0x1ED300001ED4,
        0x1ED500001ED6,
        0x1ED700001ED8,
        0x1ED900001EDA,
        0x1EDB00001EDC,
        0x1EDD00001EDE,
        0x1EDF00001EE0,
        0x1EE100001EE2,
        0x1EE300001EE4,
        0x1EE500001EE6,
        0x1EE700001EE8,
        0x1EE900001EEA,
        0x1EEB00001EEC,
        0x1EED00001EEE,
        0x1EEF00001EF0,
        0x1EF100001EF2,
        0x1EF300001EF4,
        0x1EF500001EF6,
        0x1EF700001EF8,
        0x1EF900001EFA,
        0x1EFB00001EFC,
        0x1EFD00001EFE,
        0x1EFF00001F08,
        0x1F1000001F16,
        0x1F2000001F28,
        0x1F3000001F38,
        0x1F4000001F46,
        0x1F5000001F58,
        0x1F6000001F68,
        0x1F7000001F71,
        0x1F7200001F73,
        0x1F7400001F75,
        0x1F7600001F77,
        0x1F7800001F79,
        0x1F7A00001F7B,
        0x1F7C00001F7D,
        0x1FB000001FB2,
        0x1FB600001FB7,
        0x1FC600001FC7,
        0x1FD000001FD3,
        0x1FD600001FD8,
        0x1FE000001FE3,
        0x1FE400001FE8,
        0x1FF600001FF7,
        0x214E0000214F,
        0x218400002185,
        0x2C3000002C60,
        0x2C6100002C62,
        0x2C6500002C67,
        0x2C6800002C69,
        0x2C6A00002C6B,
        0x2C6C00002C6D,
        0x2C7100002C72,
        0x2C7300002C75,
        0x2C7600002C7C,
        0x2C8100002C82,
        0x2C8300002C84,
        0x2C8500002C86,
        0x2C8700002C88,
        0x2C8900002C8A,
        0x2C8B00002C8C,
        0x2C8D00002C8E,
        0x2C8F00002C90,
        0x2C9100002C92,
        0x2C9300002C94,
        0x2C9500002C96,
        0x2C9700002C98,
        0x2C9900002C9A,
        0x2C9B00002C9C,
        0x2C9D00002C9E,
        0x2C9F00002CA0,
        0x2CA100002CA2,
        0x2CA300002CA4,
        0x2CA500002CA6,
        0x2CA700002CA8,
        0x2CA900002CAA,
        0x2CAB00002CAC,
        0x2CAD00002CAE,
        0x2CAF00002CB0,
        0x2CB100002CB2,
        0x2CB300002CB4,
        0x2CB500002CB6,
        0x2CB700002CB8,
        0x2CB900002CBA,
        0x2CBB00002CBC,
        0x2CBD00002CBE,
        0x2CBF00002CC0,
        0x2CC100002CC2,
        0x2CC300002CC4,
        0x2CC500002CC6,
        0x2CC700002CC8,
        0x2CC900002CCA,
        0x2CCB00002CCC,
        0x2CCD00002CCE,
        0x2CCF00002CD0,
        0x2CD100002CD2,
        0x2CD300002CD4,
        0x2CD500002CD6,
        0x2CD700002CD8,
        0x2CD900002CDA,
        0x2CDB00002CDC,
        0x2CDD00002CDE,
        0x2CDF00002CE0,
        0x2CE100002CE2,
        0x2CE300002CE5,
        0x2CEC00002CED,
        0x2CEE00002CF2,
        0x2CF300002CF4,
        0x2D0000002D26,
        0x2D2700002D28,
        0x2D2D00002D2E,
        0x2D3000002D68,
        0x2D7F00002D97,
        0x2DA000002DA7,
        0x2DA800002DAF,
        0x2DB000002DB7,
        0x2DB800002DBF,
        0x2DC000002DC7,
        0x2DC800002DCF,
        0x2DD000002DD7,
        0x2DD800002DDF,
        0x2DE000002E00,
        0x2E2F00002E30,
        0x300500003008,
        0x302A0000302E,
        0x303C0000303D,
        0x304100003097,
        0x30990000309B,
        0x309D0000309F,
        0x30A1000030FB,
        0x30FC000030FF,
        0x310500003130,
        0x31A0000031C0,
        0x31F000003200,
        0x340000004DC0,
        0x4E000000A48D,
        0xA4D00000A4FE,
        0xA5000000A60D,
        0xA6100000A62C,
        0xA6410000A642,
        0xA6430000A644,
        0xA6450000A646,
        0xA6470000A648,
        0xA6490000A64A,
        0xA64B0000A64C,
        0xA64D0000A64E,
        0xA64F0000A650,
        0xA6510000A652,
        0xA6530000A654,
        0xA6550000A656,
        0xA6570000A658,
        0xA6590000A65A,
        0xA65B0000A65C,
        0xA65D0000A65E,
        0xA65F0000A660,
        0xA6610000A662,
        0xA6630000A664,
        0xA6650000A666,
        0xA6670000A668,
        0xA6690000A66A,
        0xA66B0000A66C,
        0xA66D0000A670,
        0xA6740000A67E,
        0xA67F0000A680,
        0xA6810000A682,
        0xA6830000A684,
        0xA6850000A686,
        0xA6870000A688,
        0xA6890000A68A,
        0xA68B0000A68C,
        0xA68D0000A68E,
        0xA68F0000A690,
        0xA6910000A692,
        0xA6930000A694,
        0xA6950000A696,
        0xA6970000A698,
        0xA6990000A69A,
        0xA69B0000A69C,
        0xA69E0000A6E6,
        0xA6F00000A6F2,
        0xA7170000A720,
        0xA7230000A724,
        0xA7250000A726,
        0xA7270000A728,
        0xA7290000A72A,
        0xA72B0000A72C,
        0xA72D0000A72E,
        0xA72F0000A732,
        0xA7330000A734,
        0xA7350000A736,
        0xA7370000A738,
        0xA7390000A73A,
        0xA73B0000A73C,
        0xA73D0000A73E,
        0xA73F0000A740,
        0xA7410000A742,
        0xA7430000A744,
        0xA7450000A746,
        0xA7470000A748,
        0xA7490000A74A,
        0xA74B0000A74C,
        0xA74D0000A74E,
        0xA74F0000A750,
        0xA7510000A752,
        0xA7530000A754,
        0xA7550000A756,
        0xA7570000A758,
        0xA7590000A75A,
        0xA75B0000A75C,
        0xA75D0000A75E,
        0xA75F0000A760,
        0xA7610000A762,
        0xA7630000A764,
        0xA7650000A766,
        0xA7670000A768,
        0xA7690000A76A,
        0xA76B0000A76C,
        0xA76D0000A76E,
        0xA76F0000A770,
        0xA7710000A779,
        0xA77A0000A77B,
        0xA77C0000A77D,
        0xA77F0000A780,
        0xA7810000A782,
        0xA7830000A784,
        0xA7850000A786,
        0xA7870000A789,
        0xA78C0000A78D,
        0xA78E0000A790,
        0xA7910000A792,
        0xA7930000A796,
        0xA7970000A798,
        0xA7990000A79A,
        0xA79B0000A79C,
        0xA79D0000A79E,
        0xA79F0000A7A0,
        0xA7A10000A7A2,
        0xA7A30000A7A4,
        0xA7A50000A7A6,
        0xA7A70000A7A8,
        0xA7A90000A7AA,
        0xA7AF0000A7B0,
        0xA7B50000A7B6,
        0xA7B70000A7B8,
        0xA7B90000A7BA,
        0xA7BB0000A7BC,
        0xA7BD0000A7BE,
        0xA7BF0000A7C0,
        0xA7C10000A7C2,
        0xA7C30000A7C4,
        0xA7C80000A7C9,
        0xA7CA0000A7CB,
        0xA7D10000A7D2,
        0xA7D30000A7D4,
        0xA7D50000A7D6,
        0xA7D70000A7D8,
        0xA7D90000A7DA,
        0xA7F60000A7F8,
        0xA7FA0000A828,
        0xA82C0000A82D,
        0xA8400000A874,
        0xA8800000A8C6,
        0xA8D00000A8DA,
        0xA8E00000A8F8,
        0xA8FB0000A8FC,
        0xA8FD0000A92E,
        0xA9300000A954,
        0xA9800000A9C1,
        0xA9CF0000A9DA,
        0xA9E00000A9FF,
        0xAA000000AA37,
        0xAA400000AA4E,
        0xAA500000AA5A,
        0xAA600000AA77,
        0xAA7A0000AAC3,
        0xAADB0000AADE,
        0xAAE00000AAF0,
        0xAAF20000AAF7,
        0xAB010000AB07,
        0xAB090000AB0F,
        0xAB110000AB17,
        0xAB200000AB27,
        0xAB280000AB2F,
        0xAB300000AB5B,
        0xAB600000AB69,
        0xABC00000ABEB,
        0xABEC0000ABEE,
        0xABF00000ABFA,
        0xAC000000D7A4,
        0xFA0E0000FA10,
        0xFA110000FA12,
        0xFA130000FA15,
        0xFA1F0000FA20,
        0xFA210000FA22,
        0xFA230000FA25,
        0xFA270000FA2A,
        0xFB1E0000FB1F,
        0xFE200000FE30,
        0xFE730000FE74,
        0x100000001000C,
        0x1000D00010027,
        0x100280001003B,
        0x1003C0001003E,
        0x1003F0001004E,
        0x100500001005E,
        0x10080000100FB,
        0x101FD000101FE,
        0x102800001029D,
        0x102A0000102D1,
        0x102E0000102E1,
        0x1030000010320,
        0x1032D00010341,
        0x103420001034A,
        0x103500001037B,
        0x103800001039E,
        0x103A0000103C4,
        0x103C8000103D0,
        0x104280001049E,
        0x104A0000104AA,
        0x104D8000104FC,
        0x1050000010528,
        0x1053000010564,
        0x10597000105A2,
        0x105A3000105B2,
        0x105B3000105BA,
        0x105BB000105BD,
        0x1060000010737,
        0x1074000010756,
        0x1076000010768,
        0x1078000010781,
        0x1080000010806,
        0x1080800010809,
        0x1080A00010836,
        0x1083700010839,
        0x1083C0001083D,
        0x1083F00010856,
        0x1086000010877,
        0x108800001089F,
        0x108E0000108F3,
        0x108F4000108F6,
        0x1090000010916,
        0x109200001093A,
        0x10980000109B8,
        0x109BE000109C0,
        0x10A0000010A04,
        0x10A0500010A07,
        0x10A0C00010A14,
        0x10A1500010A18,
        0x10A1900010A36,
        0x10A3800010A3B,
        0x10A3F00010A40,
        0x10A6000010A7D,
        0x10A8000010A9D,
        0x10AC000010AC8,
        0x10AC900010AE7,
        0x10B0000010B36,
        0x10B4000010B56,
        0x10B6000010B73,
        0x10B8000010B92,
        0x10C0000010C49,
        0x10CC000010CF3,
        0x10D0000010D28,
        0x10D3000010D3A,
        0x10E8000010EAA,
        0x10EAB00010EAD,
        0x10EB000010EB2,
        0x10EFD00010F1D,
        0x10F2700010F28,
        0x10F3000010F51,
        0x10F7000010F86,
        0x10FB000010FC5,
        0x10FE000010FF7,
        0x1100000011047,
        0x1106600011076,
        0x1107F000110BB,
        0x110C2000110C3,
        0x110D0000110E9,
        0x110F0000110FA,
        0x1110000011135,
        0x1113600011140,
        0x1114400011148,
        0x1115000011174,
        0x1117600011177,
        0x11180000111C5,
        0x111C9000111CD,
        0x111CE000111DB,
        0x111DC000111DD,
        0x1120000011212,
        0x1121300011238,
        0x1123E00011242,
        0x1128000011287,
        0x1128800011289,
        0x1128A0001128E,
        0x1128F0001129E,
        0x1129F000112A9,
        0x112B0000112EB,
        0x112F0000112FA,
        0x1130000011304,
        0x113050001130D,
        0x1130F00011311,
        0x1131300011329,
        0x1132A00011331,
        0x1133200011334,
        0x113350001133A,
        0x1133B00011345,
        0x1134700011349,
        0x1134B0001134E,
        0x1135000011351,
        0x1135700011358,
        0x1135D00011364,
        0x113660001136D,
        0x1137000011375,
        0x114000001144B,
        0x114500001145A,
        0x1145E00011462,
        0x11480000114C6,
        0x114C7000114C8,
        0x114D0000114DA,
        0x11580000115B6,
        0x115B8000115C1,
        0x115D8000115DE,
        0x1160000011641,
        0x1164400011645,
        0x116500001165A,
        0x11680000116B9,
        0x116C0000116CA,
        0x117000001171B,
        0x1171D0001172C,
        0x117300001173A,
        0x1174000011747,
        0x118000001183B,
        0x118C0000118EA,
        0x118FF00011907,
        0x119090001190A,
        0x1190C00011914,
        0x1191500011917,
        0x1191800011936,
        0x1193700011939,
        0x1193B00011944,
        0x119500001195A,
        0x119A0000119A8,
        0x119AA000119D8,
        0x119DA000119E2,
        0x119E3000119E5,
        0x11A0000011A3F,
        0x11A4700011A48,
        0x11A5000011A9A,
        0x11A9D00011A9E,
        0x11AB000011AF9,
        0x11C0000011C09,
        0x11C0A00011C37,
        0x11C3800011C41,
        0x11C5000011C5A,
        0x11C7200011C90,
        0x11C9200011CA8,
        0x11CA900011CB7,
        0x11D0000011D07,
        0x11D0800011D0A,
        0x11D0B00011D37,
        0x11D3A00011D3B,
        0x11D3C00011D3E,
        0x11D3F00011D48,
        0x11D5000011D5A,
        0x11D6000011D66,
        0x11D6700011D69,
        0x11D6A00011D8F,
        0x11D9000011D92,
        0x11D9300011D99,
        0x11DA000011DAA,
        0x11EE000011EF7,
        0x11F0000011F11,
        0x11F1200011F3B,
        0x11F3E00011F43,
        0x11F5000011F5A,
        0x11FB000011FB1,
        0x120000001239A,
        0x1248000012544,
        0x12F9000012FF1,
        0x1300000013430,
        0x1344000013456,
        0x1440000014647,
        0x1680000016A39,
        0x16A4000016A5F,
        0x16A6000016A6A,
        0x16A7000016ABF,
        0x16AC000016ACA,
        0x16AD000016AEE,
        0x16AF000016AF5,
        0x16B0000016B37,
        0x16B4000016B44,
        0x16B5000016B5A,
        0x16B6300016B78,
        0x16B7D00016B90,
        0x16E6000016E80,
        0x16F0000016F4B,
        0x16F4F00016F88,
        0x16F8F00016FA0,
        0x16FE000016FE2,
        0x16FE300016FE5,
        0x16FF000016FF2,
        0x17000000187F8,
        0x1880000018CD6,
        0x18D0000018D09,
        0x1AFF00001AFF4,
        0x1AFF50001AFFC,
        0x1AFFD0001AFFF,
        0x1B0000001B123,
        0x1B1320001B133,
        0x1B1500001B153,
        0x1B1550001B156,
        0x1B1640001B168,
        0x1B1700001B2FC,
        0x1BC000001BC6B,
        0x1BC700001BC7D,
        0x1BC800001BC89,
        0x1BC900001BC9A,
        0x1BC9D0001BC9F,
        0x1CF000001CF2E,
        0x1CF300001CF47,
        0x1DA000001DA37,
        0x1DA3B0001DA6D,
        0x1DA750001DA76,
        0x1DA840001DA85,
        0x1DA9B0001DAA0,
        0x1DAA10001DAB0,
        0x1DF000001DF1F,
        0x1DF250001DF2B,
        0x1E0000001E007,
        0x1E0080001E019,
        0x1E01B0001E022,
        0x1E0230001E025,
        0x1E0260001E02B,
        0x1E08F0001E090,
        0x1E1000001E12D,
        0x1E1300001E13E,
        0x1E1400001E14A,
        0x1E14E0001E14F,
        0x1E2900001E2AF,
        0x1E2C00001E2FA,
        0x1E4D00001E4FA,
        0x1E7E00001E7E7,
        0x1E7E80001E7EC,
        0x1E7ED0001E7EF,
        0x1E7F00001E7FF,
        0x1E8000001E8C5,
        0x1E8D00001E8D7,
        0x1E9220001E94C,
        0x1E9500001E95A,
        0x200000002A6E0,
        0x2A7000002B73A,
        0x2B7400002B81E,
        0x2B8200002CEA2,
        0x2CEB00002EBE1,
        0x2EBF00002EE5E,
        0x300000003134B,
        0x31350000323B0,
    ),
    "CONTEXTJ": (0x200C0000200E,),
    "CONTEXTO": (
        0xB7000000B8,
        0x37500000376,
        0x5F3000005F5,
        0x6600000066A,
        0x6F0000006FA,
        0x30FB000030FC,
    ),
}