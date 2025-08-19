
# === NexusCore/openenv\Lib\site-packages\numpy\lib\_index_tricks_impl.py ===
import functools
import math
import sys
import warnings

import numpy as np
import numpy._core.numeric as _nx
import numpy.matrixlib as matrixlib
from numpy._core import linspace, overrides
from numpy._core.multiarray import ravel_multi_index, unravel_index
from numpy._core.numeric import ScalarType, array
from numpy._core.numerictypes import issubdtype
from numpy._utils import set_module
from numpy.lib._function_base_impl import diff
from numpy.lib.stride_tricks import as_strided

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'ravel_multi_index', 'unravel_index', 'mgrid', 'ogrid', 'r_', 'c_',
    's_', 'index_exp', 'ix_', 'ndenumerate', 'ndindex', 'fill_diagonal',
    'diag_indices', 'diag_indices_from'
]


def _ix__dispatcher(*args):
    return args


@array_function_dispatch(_ix__dispatcher)
def ix_(*args):
    """
    Construct an open mesh from multiple sequences.

    This function takes N 1-D sequences and returns N outputs with N
    dimensions each, such that the shape is 1 in all but one dimension
    and the dimension with the non-unit shape value cycles through all
    N dimensions.

    Using `ix_` one can quickly construct index arrays that will index
    the cross product. ``a[np.ix_([1,3],[2,5])]`` returns the array
    ``[[a[1,2] a[1,5]], [a[3,2] a[3,5]]]``.

    Parameters
    ----------
    args : 1-D sequences
        Each sequence should be of integer or boolean type.
        Boolean sequences will be interpreted as boolean masks for the
        corresponding dimension (equivalent to passing in
        ``np.nonzero(boolean_sequence)``).

    Returns
    -------
    out : tuple of ndarrays
        N arrays with N dimensions each, with N the number of input
        sequences. Together these arrays form an open mesh.

    See Also
    --------
    ogrid, mgrid, meshgrid

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10).reshape(2, 5)
    >>> a
    array([[0, 1, 2, 3, 4],
           [5, 6, 7, 8, 9]])
    >>> ixgrid = np.ix_([0, 1], [2, 4])
    >>> ixgrid
    (array([[0],
           [1]]), array([[2, 4]]))
    >>> ixgrid[0].shape, ixgrid[1].shape
    ((2, 1), (1, 2))
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    >>> ixgrid = np.ix_([True, True], [2, 4])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])
    >>> ixgrid = np.ix_([True, True], [False, False, True, False, True])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    """
    out = []
    nd = len(args)
    for k, new in enumerate(args):
        if not isinstance(new, _nx.ndarray):
            new = np.asarray(new)
            if new.size == 0:
                # Explicitly type empty arrays to avoid float default
                new = new.astype(_nx.intp)
        if new.ndim != 1:
            raise ValueError("Cross index must be 1 dimensional")
        if issubdtype(new.dtype, _nx.bool):
            new, = new.nonzero()
        new = new.reshape((1,) * k + (new.size,) + (1,) * (nd - k - 1))
        out.append(new)
    return tuple(out)


class nd_grid:
    """
    Construct a multi-dimensional "meshgrid".

    ``grid = nd_grid()`` creates an instance which will return a mesh-grid
    when indexed.  The dimension and number of the output arrays are equal
    to the number of indexing dimensions.  If the step length is not a
    complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then the
    integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    If instantiated with an argument of ``sparse=True``, the mesh-grid is
    open (or not fleshed out) so that only one-dimension of each returned
    argument is greater than 1.

    Parameters
    ----------
    sparse : bool, optional
        Whether the grid is sparse or not. Default is False.

    Notes
    -----
    Two instances of `nd_grid` are made available in the NumPy namespace,
    `mgrid` and `ogrid`, approximately defined as::

        mgrid = nd_grid(sparse=False)
        ogrid = nd_grid(sparse=True)

    Users should use these pre-defined instances instead of using `nd_grid`
    directly.
    """
    __slots__ = ('sparse',)

    def __init__(self, sparse=False):
        self.sparse = sparse

    def __getitem__(self, key):
        try:
            size = []
            # Mimic the behavior of `np.arange` and use a data type
            # which is at least as large as `np.int_`
            num_list = [0]
            for k in range(len(key)):
                step = key[k].step
                start = key[k].start
                stop = key[k].stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = abs(step)
                    size.append(int(step))
                else:
                    size.append(
                        math.ceil((stop - start) / step))
                num_list += [start, stop, step]
            typ = _nx.result_type(*num_list)
            if self.sparse:
                nn = [_nx.arange(_x, dtype=_t)
                      for _x, _t in zip(size, (typ,) * len(size))]
            else:
                nn = _nx.indices(size, typ)
            for k, kk in enumerate(key):
                step = kk.step
                start = kk.start
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = int(abs(step))
                    if step != 1:
                        step = (kk.stop - start) / float(step - 1)
                nn[k] = (nn[k] * step + start)
            if self.sparse:
                slobj = [_nx.newaxis] * len(size)
                for k in range(len(size)):
                    slobj[k] = slice(None, None)
                    nn[k] = nn[k][tuple(slobj)]
                    slobj[k] = _nx.newaxis
                return tuple(nn)  # ogrid -> tuple of arrays
            return nn  # mgrid -> ndarray
        except (IndexError, TypeError):
            step = key.step
            stop = key.stop
            start = key.start
            if start is None:
                start = 0
            if isinstance(step, (_nx.complexfloating, complex)):
                # Prevent the (potential) creation of integer arrays
                step_float = abs(step)
                step = length = int(step_float)
                if step != 1:
                    step = (key.stop - start) / float(step - 1)
                typ = _nx.result_type(start, stop, step_float)
                return _nx.arange(0, length, 1, dtype=typ) * step + start
            else:
                return _nx.arange(start, stop, step)


class MGridClass(nd_grid):
    """
    An instance which returns a dense multi-dimensional "meshgrid".

    An instance which returns a dense (or fleshed out) mesh-grid
    when indexed, so that each returned argument has the same shape.
    The dimensions and number of the output arrays are equal to the
    number of indexing dimensions.  If the step length is not a complex
    number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray
        A single array, containing a set of `ndarray`\\ s all of the same
        dimensions. stacked along the first axis.

    See Also
    --------
    ogrid : like `mgrid` but returns open (not fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> import numpy as np
    >>> np.mgrid[0:5, 0:5]
    array([[[0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1],
            [2, 2, 2, 2, 2],
            [3, 3, 3, 3, 3],
            [4, 4, 4, 4, 4]],
           [[0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4]]])
    >>> np.mgrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])

    >>> np.mgrid[0:4].shape
    (4,)
    >>> np.mgrid[0:4, 0:5].shape
    (2, 4, 5)
    >>> np.mgrid[0:4, 0:5, 0:6].shape
    (3, 4, 5, 6)

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=False)


mgrid = MGridClass()


class OGridClass(nd_grid):
    """
    An instance which returns an open multi-dimensional "meshgrid".

    An instance which returns an open (i.e. not fleshed out) mesh-grid
    when indexed, so that only one dimension of each returned array is
    greater than 1.  The dimension and number of the output arrays are
    equal to the number of indexing dimensions.  If the step length is
    not a complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray or tuple of ndarrays
        If the input is a single slice, returns an array.
        If the input is multiple slices, returns a tuple of arrays, with
        only one dimension not equal to 1.

    See Also
    --------
    mgrid : like `ogrid` but returns dense (or fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> from numpy import ogrid
    >>> ogrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])
    >>> ogrid[0:5, 0:5]
    (array([[0],
            [1],
            [2],
            [3],
            [4]]),
     array([[0, 1, 2, 3, 4]]))

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=True)


ogrid = OGridClass()


class AxisConcatenator:
    """
    Translates slice objects to concatenation along an axis.

    For detailed documentation on usage, see `r_`.
    """
    __slots__ = ('axis', 'matrix', 'ndmin', 'trans1d')

    # allow ma.mr_ to override this
    concatenate = staticmethod(_nx.concatenate)
    makemat = staticmethod(matrixlib.matrix)

    def __init__(self, axis=0, matrix=False, ndmin=1, trans1d=-1):
        self.axis = axis
        self.matrix = matrix
        self.trans1d = trans1d
        self.ndmin = ndmin

    def __getitem__(self, key):
        # handle matrix builder syntax
        if isinstance(key, str):
            frame = sys._getframe().f_back
            mymat = matrixlib.bmat(key, frame.f_globals, frame.f_locals)
            return mymat

        if not isinstance(key, tuple):
            key = (key,)

        # copy attributes, since they can be overridden in the first argument
        trans1d = self.trans1d
        ndmin = self.ndmin
        matrix = self.matrix
        axis = self.axis

        objs = []
        # dtypes or scalars for weak scalar handling in result_type
        result_type_objs = []

        for k, item in enumerate(key):
            scalar = False
            if isinstance(item, slice):
                step = item.step
                start = item.start
                stop = item.stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    size = int(abs(step))
                    newobj = linspace(start, stop, num=size)
                else:
                    newobj = _nx.arange(start, stop, step)
                if ndmin > 1:
                    newobj = array(newobj, copy=None, ndmin=ndmin)
                    if trans1d != -1:
                        newobj = newobj.swapaxes(-1, trans1d)
            elif isinstance(item, str):
                if k != 0:
                    raise ValueError("special directives must be the "
                                     "first entry.")
                if item in ('r', 'c'):
                    matrix = True
                    col = (item == 'c')
                    continue
                if ',' in item:
                    vec = item.split(',')
                    try:
                        axis, ndmin = [int(x) for x in vec[:2]]
                        if len(vec) == 3:
                            trans1d = int(vec[2])
                        continue
                    except Exception as e:
                        raise ValueError(
                            f"unknown special directive {item!r}"
                        ) from e
                try:
                    axis = int(item)
                    continue
                except (ValueError, TypeError) as e:
                    raise ValueError("unknown special directive") from e
            elif type(item) in ScalarType:
                scalar = True
                newobj = item
            else:
                item_ndim = np.ndim(item)
                newobj = array(item, copy=None, subok=True, ndmin=ndmin)
                if trans1d != -1 and item_ndim < ndmin:
                    k2 = ndmin - item_ndim
                    k1 = trans1d
                    if k1 < 0:
                        k1 += k2 + 1
                    defaxes = list(range(ndmin))
                    axes = defaxes[:k1] + defaxes[k2:] + defaxes[k1:k2]
                    newobj = newobj.transpose(axes)

            objs.append(newobj)
            if scalar:
                result_type_objs.append(item)
            else:
                result_type_objs.append(newobj.dtype)

        # Ensure that scalars won't up-cast unless warranted, for 0, drops
        # through to error in concatenate.
        if len(result_type_objs) != 0:
            final_dtype = _nx.result_type(*result_type_objs)
            # concatenate could do cast, but that can be overridden:
            objs = [array(obj, copy=None, subok=True,
                          ndmin=ndmin, dtype=final_dtype) for obj in objs]

        res = self.concatenate(tuple(objs), axis=axis)

        if matrix:
            oldndim = res.ndim
            res = self.makemat(res)
            if oldndim == 1 and col:
                res = res.T
        return res

    def __len__(self):
        return 0

# separate classes are used here instead of just making r_ = concatenator(0),
# etc. because otherwise we couldn't get the doc string to come out right
# in help(r_)


class RClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the first axis.

    This is a simple way to build up arrays quickly. There are two use cases.

    1. If the index expression contains comma separated arrays, then stack
       them along their first axis.
    2. If the index expression contains slice notation or scalars then create
       a 1-D array with a range indicated by the slice notation.

    If slice notation is used, the syntax ``start:stop:step`` is equivalent
    to ``np.arange(start, stop, step)`` inside of the brackets. However, if
    ``step`` is an imaginary number (i.e. 100j) then its integer portion is
    interpreted as a number-of-points desired and the start and stop are
    inclusive. In other words ``start:stop:stepj`` is interpreted as
    ``np.linspace(start, stop, step, endpoint=1)`` inside of the brackets.
    After expansion of slice notation, all comma separated sequences are
    concatenated together.

    Optional character strings placed as the first element of the index
    expression can be used to change the output. The strings 'r' or 'c' result
    in matrix output. If the result is 1-D and 'r' is specified a 1 x N (row)
    matrix is produced. If the result is 1-D and 'c' is specified, then a N x 1
    (column) matrix is produced. If the result is 2-D then both provide the
    same matrix result.

    A string integer specifies which axis to stack multiple comma separated
    arrays along. A string of two comma-separated integers allows indication
    of the minimum number of dimensions to force each entry into as the
    second integer (the axis to concatenate along is still the first integer).

    A string with three comma-separated integers allows specification of the
    axis to concatenate along, the minimum number of dimensions to force the
    entries to, and which axis should contain the start of the arrays which
    are less than the specified number of dimensions. In other words the third
    integer allows you to specify where the 1's should be placed in the shape
    of the arrays that have their shapes upgraded. By default, they are placed
    in the front of the shape tuple. The third argument allows you to specify
    where the start of the array should be instead. Thus, a third argument of
    '0' would place the 1's at the end of the array shape. Negative integers
    specify where in the new shape tuple the last dimension of upgraded arrays
    should be placed, so the default is '-1'.

    Parameters
    ----------
    Not a function, so takes no parameters


    Returns
    -------
    A concatenated ndarray or matrix.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    c_ : Translates slice objects to concatenation along the second axis.

    Examples
    --------
    >>> import numpy as np
    >>> np.r_[np.array([1,2,3]), 0, 0, np.array([4,5,6])]
    array([1, 2, 3, ..., 4, 5, 6])
    >>> np.r_[-1:1:6j, [0]*3, 5, 6]
    array([-1. , -0.6, -0.2,  0.2,  0.6,  1. ,  0. ,  0. ,  0. ,  5. ,  6. ])

    String integers specify the axis to concatenate along or the minimum
    number of dimensions to force entries into.

    >>> a = np.array([[0, 1, 2], [3, 4, 5]])
    >>> np.r_['-1', a, a] # concatenate along last axis
    array([[0, 1, 2, 0, 1, 2],
           [3, 4, 5, 3, 4, 5]])
    >>> np.r_['0,2', [1,2,3], [4,5,6]] # concatenate along first axis, dim>=2
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> np.r_['0,2,0', [1,2,3], [4,5,6]]
    array([[1],
           [2],
           [3],
           [4],
           [5],
           [6]])
    >>> np.r_['1,2,0', [1,2,3], [4,5,6]]
    array([[1, 4],
           [2, 5],
           [3, 6]])

    Using 'r' or 'c' as a first string argument creates a matrix.

    >>> np.r_['r',[1,2,3], [4,5,6]]
    matrix([[1, 2, 3, 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, 0)


r_ = RClass()


class CClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the second axis.

    This is short-hand for ``np.r_['-1,2,0', index expression]``, which is
    useful because of its common occurrence. In particular, arrays will be
    stacked along their last axis after being upgraded to at least 2-D with
    1's post-pended to the shape (column vectors made out of 1-D arrays).

    See Also
    --------
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    r_ : For more detailed documentation.

    Examples
    --------
    >>> import numpy as np
    >>> np.c_[np.array([1,2,3]), np.array([4,5,6])]
    array([[1, 4],
           [2, 5],
           [3, 6]])
    >>> np.c_[np.array([[1,2,3]]), 0, 0, np.array([[4,5,6]])]
    array([[1, 2, 3, ..., 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, -1, ndmin=2, trans1d=0)


c_ = CClass()


@set_module('numpy')
class ndenumerate:
    """
    Multidimensional index iterator.

    Return an iterator yielding pairs of array coordinates and values.

    Parameters
    ----------
    arr : ndarray
      Input array.

    See Also
    --------
    ndindex, flatiter

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> for index, x in np.ndenumerate(a):
    ...     print(index, x)
    (0, 0) 1
    (0, 1) 2
    (1, 0) 3
    (1, 1) 4

    """

    def __init__(self, arr):
        self.iter = np.asarray(arr).flat

    def __next__(self):
        """
        Standard iterator method, returns the index tuple and array value.

        Returns
        -------
        coords : tuple of ints
            The indices of the current iteration.
        val : scalar
            The array element of the current iteration.

        """
        return self.iter.coords, next(self.iter)

    def __iter__(self):
        return self


@set_module('numpy')
class ndindex:
    """
    An N-dimensional iterator object to index arrays.

    Given the shape of an array, an `ndindex` instance iterates over
    the N-dimensional index of the array. At each iteration a tuple
    of indices is returned, the last dimension is iterated over first.

    Parameters
    ----------
    shape : ints, or a single tuple of ints
        The size of each dimension of the array can be passed as
        individual parameters or as the elements of a tuple.

    See Also
    --------
    ndenumerate, flatiter

    Examples
    --------
    >>> import numpy as np

    Dimensions as individual arguments

    >>> for index in np.ndindex(3, 2, 1):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    Same dimensions - but in a tuple ``(3, 2, 1)``

    >>> for index in np.ndindex((3, 2, 1)):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    """

    def __init__(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], tuple):
            shape = shape[0]
        x = as_strided(_nx.zeros(1), shape=shape,
                       strides=_nx.zeros_like(shape))
        self._it = _nx.nditer(x, flags=['multi_index', 'zerosize_ok'],
                              order='C')

    def __iter__(self):
        return self

    def ndincr(self):
        """
        Increment the multi-dimensional index by one.

        This method is for backward compatibility only: do not use.

        .. deprecated:: 1.20.0
            This method has been advised against since numpy 1.8.0, but only
            started emitting DeprecationWarning as of this version.
        """
        # NumPy 1.20.0, 2020-09-08
        warnings.warn(
            "`ndindex.ndincr()` is deprecated, use `next(ndindex)` instead",
            DeprecationWarning, stacklevel=2)
        next(self)

    def __next__(self):
        """
        Standard iterator method, updates the index and returns the index
        tuple.

        Returns
        -------
        val : tuple of ints
            Returns a tuple containing the indices of the current
            iteration.

        """
        next(self._it)
        return self._it.multi_index


# You can do all this with slice() plus a few special objects,
# but there's a lot to remember. This version is simpler because
# it uses the standard array indexing syntax.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-23
#
# Cosmetic changes by T. Oliphant 2001
#
#

class IndexExpression:
    """
    A nicer way to build up index tuples for arrays.

    .. note::
       Use one of the two predefined instances ``index_exp`` or `s_`
       rather than directly using `IndexExpression`.

    For any index combination, including slicing and axis insertion,
    ``a[indices]`` is the same as ``a[np.index_exp[indices]]`` for any
    array `a`. However, ``np.index_exp[indices]`` can be used anywhere
    in Python code and returns a tuple of slice objects that can be
    used in the construction of complex index expressions.

    Parameters
    ----------
    maketuple : bool
        If True, always returns a tuple.

    See Also
    --------
    s_ : Predefined instance without tuple conversion:
       `s_ = IndexExpression(maketuple=False)`.
       The ``index_exp`` is another predefined instance that
       always returns a tuple:
       `index_exp = IndexExpression(maketuple=True)`.

    Notes
    -----
    You can do all this with :class:`slice` plus a few special objects,
    but there's a lot to remember and this version is simpler because
    it uses the standard array indexing syntax.

    Examples
    --------
    >>> import numpy as np
    >>> np.s_[2::2]
    slice(2, None, 2)
    >>> np.index_exp[2::2]
    (slice(2, None, 2),)

    >>> np.array([0, 1, 2, 3, 4])[np.s_[2::2]]
    array([2, 4])

    """
    __slots__ = ('maketuple',)

    def __init__(self, maketuple):
        self.maketuple = maketuple

    def __getitem__(self, item):
        if self.maketuple and not isinstance(item, tuple):
            return (item,)
        else:
            return item


index_exp = IndexExpression(maketuple=True)
s_ = IndexExpression(maketuple=False)

# End contribution from Konrad.


# The following functions complement those in twodim_base, but are
# applicable to N-dimensions.


def _fill_diagonal_dispatcher(a, val, wrap=None):
    return (a,)


@array_function_dispatch(_fill_diagonal_dispatcher)
def fill_diagonal(a, val, wrap=False):
    """Fill the main diagonal of the given array of any dimensionality.

    For an array `a` with ``a.ndim >= 2``, the diagonal is the list of
    values ``a[i, ..., i]`` with indices ``i`` all identical.  This function
    modifies the input array in-place without returning a value.

    Parameters
    ----------
    a : array, at least 2-D.
      Array whose diagonal is to be filled in-place.
    val : scalar or array_like
      Value(s) to write on the diagonal. If `val` is scalar, the value is
      written along the diagonal. If array-like, the flattened `val` is
      written along the diagonal, repeating if necessary to fill all
      diagonal entries.

    wrap : bool
      For tall matrices in NumPy version up to 1.6.2, the
      diagonal "wrapped" after N columns. You can have this behavior
      with this option. This affects only tall matrices.

    See also
    --------
    diag_indices, diag_indices_from

    Notes
    -----
    This functionality can be obtained via `diag_indices`, but internally
    this version uses a much faster implementation that never constructs the
    indices and uses simple slicing.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), int)
    >>> np.fill_diagonal(a, 5)
    >>> a
    array([[5, 0, 0],
           [0, 5, 0],
           [0, 0, 5]])

    The same function can operate on a 4-D array:

    >>> a = np.zeros((3, 3, 3, 3), int)
    >>> np.fill_diagonal(a, 4)

    We only show a few blocks for clarity:

    >>> a[0, 0]
    array([[4, 0, 0],
           [0, 0, 0],
           [0, 0, 0]])
    >>> a[1, 1]
    array([[0, 0, 0],
           [0, 4, 0],
           [0, 0, 0]])
    >>> a[2, 2]
    array([[0, 0, 0],
           [0, 0, 0],
           [0, 0, 4]])

    The wrap option affects only tall matrices:

    >>> # tall matrices no wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [0, 0, 0]])

    >>> # tall matrices wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [4, 0, 0]])

    >>> # wide matrices
    >>> a = np.zeros((3, 5), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0, 0, 0],
           [0, 4, 0, 0, 0],
           [0, 0, 4, 0, 0]])

    The anti-diagonal can be filled by reversing the order of elements
    using either `numpy.flipud` or `numpy.fliplr`.

    >>> a = np.zeros((3, 3), int);
    >>> np.fill_diagonal(np.fliplr(a), [1,2,3])  # Horizontal flip
    >>> a
    array([[0, 0, 1],
           [0, 2, 0],
           [3, 0, 0]])
    >>> np.fill_diagonal(np.flipud(a), [1,2,3])  # Vertical flip
    >>> a
    array([[0, 0, 3],
           [0, 2, 0],
           [1, 0, 0]])

    Note that the order in which the diagonal is filled varies depending
    on the flip function.
    """
    if a.ndim < 2:
        raise ValueError("array must be at least 2-d")
    end = None
    if a.ndim == 2:
        # Explicit, fast formula for the common case.  For 2-d arrays, we
        # accept rectangular ones.
        step = a.shape[1] + 1
        # This is needed to don't have tall matrix have the diagonal wrap.
        if not wrap:
            end = a.shape[1] * a.shape[1]
    else:
        # For more than d=2, the strided formula is only valid for arrays with
        # all dimensions equal, so we check first.
        if not np.all(diff(a.shape) == 0):
            raise ValueError("All dimensions of input must be of equal length")
        step = 1 + (np.cumprod(a.shape[:-1])).sum()

    # Write the value out into the diagonal.
    a.flat[:end:step] = val


@set_module('numpy')
def diag_indices(n, ndim=2):
    """
    Return the indices to access the main diagonal of an array.

    This returns a tuple of indices that can be used to access the main
    diagonal of an array `a` with ``a.ndim >= 2`` dimensions and shape
    (n, n, ..., n). For ``a.ndim = 2`` this is the usual diagonal, for
    ``a.ndim > 2`` this is the set of indices to access ``a[i, i, ..., i]``
    for ``i = [0..n-1]``.

    Parameters
    ----------
    n : int
      The size, along each dimension, of the arrays for which the returned
      indices can be used.

    ndim : int, optional
      The number of dimensions.

    See Also
    --------
    diag_indices_from

    Examples
    --------
    >>> import numpy as np

    Create a set of indices to access the diagonal of a (4, 4) array:

    >>> di = np.diag_indices(4)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))
    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])
    >>> a[di] = 100
    >>> a
    array([[100,   1,   2,   3],
           [  4, 100,   6,   7],
           [  8,   9, 100,  11],
           [ 12,  13,  14, 100]])

    Now, we create indices to manipulate a 3-D array:

    >>> d3 = np.diag_indices(2, 3)
    >>> d3
    (array([0, 1]), array([0, 1]), array([0, 1]))

    And use it to set the diagonal of an array of zeros to 1:

    >>> a = np.zeros((2, 2, 2), dtype=int)
    >>> a[d3] = 1
    >>> a
    array([[[1, 0],
            [0, 0]],
           [[0, 0],
            [0, 1]]])

    """
    idx = np.arange(n)
    return (idx,) * ndim


def _diag_indices_from(arr):
    return (arr,)


@array_function_dispatch(_diag_indices_from)
def diag_indices_from(arr):
    """
    Return the indices to access the main diagonal of an n-dimensional array.

    See `diag_indices` for full details.

    Parameters
    ----------
    arr : array, at least 2-D

    See Also
    --------
    diag_indices

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array.

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Get the indices of the diagonal elements.

    >>> di = np.diag_indices_from(a)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    >>> a[di]
    array([ 0,  5, 10, 15])

    This is simply syntactic sugar for diag_indices.

    >>> np.diag_indices(a.shape[0])
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    """

    if not arr.ndim >= 2:
        raise ValueError("input array must be at least 2-d")
    # For more than d=2, the strided formula is only valid for arrays with
    # all dimensions equal, so we check first.
    if not np.all(diff(arr.shape) == 0):
        raise ValueError("All dimensions of input must be of equal length")

    return diag_indices(arr.shape[0], arr.ndim)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_index_tricks_impl.py ===
import functools
import math
import sys
import warnings

import numpy as np
import numpy._core.numeric as _nx
import numpy.matrixlib as matrixlib
from numpy._core import linspace, overrides
from numpy._core.multiarray import ravel_multi_index, unravel_index
from numpy._core.numeric import ScalarType, array
from numpy._core.numerictypes import issubdtype
from numpy._utils import set_module
from numpy.lib._function_base_impl import diff
from numpy.lib.stride_tricks import as_strided

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'ravel_multi_index', 'unravel_index', 'mgrid', 'ogrid', 'r_', 'c_',
    's_', 'index_exp', 'ix_', 'ndenumerate', 'ndindex', 'fill_diagonal',
    'diag_indices', 'diag_indices_from'
]


def _ix__dispatcher(*args):
    return args


@array_function_dispatch(_ix__dispatcher)
def ix_(*args):
    """
    Construct an open mesh from multiple sequences.

    This function takes N 1-D sequences and returns N outputs with N
    dimensions each, such that the shape is 1 in all but one dimension
    and the dimension with the non-unit shape value cycles through all
    N dimensions.

    Using `ix_` one can quickly construct index arrays that will index
    the cross product. ``a[np.ix_([1,3],[2,5])]`` returns the array
    ``[[a[1,2] a[1,5]], [a[3,2] a[3,5]]]``.

    Parameters
    ----------
    args : 1-D sequences
        Each sequence should be of integer or boolean type.
        Boolean sequences will be interpreted as boolean masks for the
        corresponding dimension (equivalent to passing in
        ``np.nonzero(boolean_sequence)``).

    Returns
    -------
    out : tuple of ndarrays
        N arrays with N dimensions each, with N the number of input
        sequences. Together these arrays form an open mesh.

    See Also
    --------
    ogrid, mgrid, meshgrid

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10).reshape(2, 5)
    >>> a
    array([[0, 1, 2, 3, 4],
           [5, 6, 7, 8, 9]])
    >>> ixgrid = np.ix_([0, 1], [2, 4])
    >>> ixgrid
    (array([[0],
           [1]]), array([[2, 4]]))
    >>> ixgrid[0].shape, ixgrid[1].shape
    ((2, 1), (1, 2))
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    >>> ixgrid = np.ix_([True, True], [2, 4])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])
    >>> ixgrid = np.ix_([True, True], [False, False, True, False, True])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    """
    out = []
    nd = len(args)
    for k, new in enumerate(args):
        if not isinstance(new, _nx.ndarray):
            new = np.asarray(new)
            if new.size == 0:
                # Explicitly type empty arrays to avoid float default
                new = new.astype(_nx.intp)
        if new.ndim != 1:
            raise ValueError("Cross index must be 1 dimensional")
        if issubdtype(new.dtype, _nx.bool):
            new, = new.nonzero()
        new = new.reshape((1,) * k + (new.size,) + (1,) * (nd - k - 1))
        out.append(new)
    return tuple(out)


class nd_grid:
    """
    Construct a multi-dimensional "meshgrid".

    ``grid = nd_grid()`` creates an instance which will return a mesh-grid
    when indexed.  The dimension and number of the output arrays are equal
    to the number of indexing dimensions.  If the step length is not a
    complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then the
    integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    If instantiated with an argument of ``sparse=True``, the mesh-grid is
    open (or not fleshed out) so that only one-dimension of each returned
    argument is greater than 1.

    Parameters
    ----------
    sparse : bool, optional
        Whether the grid is sparse or not. Default is False.

    Notes
    -----
    Two instances of `nd_grid` are made available in the NumPy namespace,
    `mgrid` and `ogrid`, approximately defined as::

        mgrid = nd_grid(sparse=False)
        ogrid = nd_grid(sparse=True)

    Users should use these pre-defined instances instead of using `nd_grid`
    directly.
    """
    __slots__ = ('sparse',)

    def __init__(self, sparse=False):
        self.sparse = sparse

    def __getitem__(self, key):
        try:
            size = []
            # Mimic the behavior of `np.arange` and use a data type
            # which is at least as large as `np.int_`
            num_list = [0]
            for k in range(len(key)):
                step = key[k].step
                start = key[k].start
                stop = key[k].stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = abs(step)
                    size.append(int(step))
                else:
                    size.append(
                        math.ceil((stop - start) / step))
                num_list += [start, stop, step]
            typ = _nx.result_type(*num_list)
            if self.sparse:
                nn = [_nx.arange(_x, dtype=_t)
                      for _x, _t in zip(size, (typ,) * len(size))]
            else:
                nn = _nx.indices(size, typ)
            for k, kk in enumerate(key):
                step = kk.step
                start = kk.start
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = int(abs(step))
                    if step != 1:
                        step = (kk.stop - start) / float(step - 1)
                nn[k] = (nn[k] * step + start)
            if self.sparse:
                slobj = [_nx.newaxis] * len(size)
                for k in range(len(size)):
                    slobj[k] = slice(None, None)
                    nn[k] = nn[k][tuple(slobj)]
                    slobj[k] = _nx.newaxis
                return tuple(nn)  # ogrid -> tuple of arrays
            return nn  # mgrid -> ndarray
        except (IndexError, TypeError):
            step = key.step
            stop = key.stop
            start = key.start
            if start is None:
                start = 0
            if isinstance(step, (_nx.complexfloating, complex)):
                # Prevent the (potential) creation of integer arrays
                step_float = abs(step)
                step = length = int(step_float)
                if step != 1:
                    step = (key.stop - start) / float(step - 1)
                typ = _nx.result_type(start, stop, step_float)
                return _nx.arange(0, length, 1, dtype=typ) * step + start
            else:
                return _nx.arange(start, stop, step)


class MGridClass(nd_grid):
    """
    An instance which returns a dense multi-dimensional "meshgrid".

    An instance which returns a dense (or fleshed out) mesh-grid
    when indexed, so that each returned argument has the same shape.
    The dimensions and number of the output arrays are equal to the
    number of indexing dimensions.  If the step length is not a complex
    number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray
        A single array, containing a set of `ndarray`\\ s all of the same
        dimensions. stacked along the first axis.

    See Also
    --------
    ogrid : like `mgrid` but returns open (not fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> import numpy as np
    >>> np.mgrid[0:5, 0:5]
    array([[[0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1],
            [2, 2, 2, 2, 2],
            [3, 3, 3, 3, 3],
            [4, 4, 4, 4, 4]],
           [[0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4]]])
    >>> np.mgrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])

    >>> np.mgrid[0:4].shape
    (4,)
    >>> np.mgrid[0:4, 0:5].shape
    (2, 4, 5)
    >>> np.mgrid[0:4, 0:5, 0:6].shape
    (3, 4, 5, 6)

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=False)


mgrid = MGridClass()


class OGridClass(nd_grid):
    """
    An instance which returns an open multi-dimensional "meshgrid".

    An instance which returns an open (i.e. not fleshed out) mesh-grid
    when indexed, so that only one dimension of each returned array is
    greater than 1.  The dimension and number of the output arrays are
    equal to the number of indexing dimensions.  If the step length is
    not a complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray or tuple of ndarrays
        If the input is a single slice, returns an array.
        If the input is multiple slices, returns a tuple of arrays, with
        only one dimension not equal to 1.

    See Also
    --------
    mgrid : like `ogrid` but returns dense (or fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> from numpy import ogrid
    >>> ogrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])
    >>> ogrid[0:5, 0:5]
    (array([[0],
            [1],
            [2],
            [3],
            [4]]),
     array([[0, 1, 2, 3, 4]]))

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=True)


ogrid = OGridClass()


class AxisConcatenator:
    """
    Translates slice objects to concatenation along an axis.

    For detailed documentation on usage, see `r_`.
    """
    __slots__ = ('axis', 'matrix', 'ndmin', 'trans1d')

    # allow ma.mr_ to override this
    concatenate = staticmethod(_nx.concatenate)
    makemat = staticmethod(matrixlib.matrix)

    def __init__(self, axis=0, matrix=False, ndmin=1, trans1d=-1):
        self.axis = axis
        self.matrix = matrix
        self.trans1d = trans1d
        self.ndmin = ndmin

    def __getitem__(self, key):
        # handle matrix builder syntax
        if isinstance(key, str):
            frame = sys._getframe().f_back
            mymat = matrixlib.bmat(key, frame.f_globals, frame.f_locals)
            return mymat

        if not isinstance(key, tuple):
            key = (key,)

        # copy attributes, since they can be overridden in the first argument
        trans1d = self.trans1d
        ndmin = self.ndmin
        matrix = self.matrix
        axis = self.axis

        objs = []
        # dtypes or scalars for weak scalar handling in result_type
        result_type_objs = []

        for k, item in enumerate(key):
            scalar = False
            if isinstance(item, slice):
                step = item.step
                start = item.start
                stop = item.stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    size = int(abs(step))
                    newobj = linspace(start, stop, num=size)
                else:
                    newobj = _nx.arange(start, stop, step)
                if ndmin > 1:
                    newobj = array(newobj, copy=None, ndmin=ndmin)
                    if trans1d != -1:
                        newobj = newobj.swapaxes(-1, trans1d)
            elif isinstance(item, str):
                if k != 0:
                    raise ValueError("special directives must be the "
                                     "first entry.")
                if item in ('r', 'c'):
                    matrix = True
                    col = (item == 'c')
                    continue
                if ',' in item:
                    vec = item.split(',')
                    try:
                        axis, ndmin = [int(x) for x in vec[:2]]
                        if len(vec) == 3:
                            trans1d = int(vec[2])
                        continue
                    except Exception as e:
                        raise ValueError(
                            f"unknown special directive {item!r}"
                        ) from e
                try:
                    axis = int(item)
                    continue
                except (ValueError, TypeError) as e:
                    raise ValueError("unknown special directive") from e
            elif type(item) in ScalarType:
                scalar = True
                newobj = item
            else:
                item_ndim = np.ndim(item)
                newobj = array(item, copy=None, subok=True, ndmin=ndmin)
                if trans1d != -1 and item_ndim < ndmin:
                    k2 = ndmin - item_ndim
                    k1 = trans1d
                    if k1 < 0:
                        k1 += k2 + 1
                    defaxes = list(range(ndmin))
                    axes = defaxes[:k1] + defaxes[k2:] + defaxes[k1:k2]
                    newobj = newobj.transpose(axes)

            objs.append(newobj)
            if scalar:
                result_type_objs.append(item)
            else:
                result_type_objs.append(newobj.dtype)

        # Ensure that scalars won't up-cast unless warranted, for 0, drops
        # through to error in concatenate.
        if len(result_type_objs) != 0:
            final_dtype = _nx.result_type(*result_type_objs)
            # concatenate could do cast, but that can be overridden:
            objs = [array(obj, copy=None, subok=True,
                          ndmin=ndmin, dtype=final_dtype) for obj in objs]

        res = self.concatenate(tuple(objs), axis=axis)

        if matrix:
            oldndim = res.ndim
            res = self.makemat(res)
            if oldndim == 1 and col:
                res = res.T
        return res

    def __len__(self):
        return 0

# separate classes are used here instead of just making r_ = concatenator(0),
# etc. because otherwise we couldn't get the doc string to come out right
# in help(r_)


class RClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the first axis.

    This is a simple way to build up arrays quickly. There are two use cases.

    1. If the index expression contains comma separated arrays, then stack
       them along their first axis.
    2. If the index expression contains slice notation or scalars then create
       a 1-D array with a range indicated by the slice notation.

    If slice notation is used, the syntax ``start:stop:step`` is equivalent
    to ``np.arange(start, stop, step)`` inside of the brackets. However, if
    ``step`` is an imaginary number (i.e. 100j) then its integer portion is
    interpreted as a number-of-points desired and the start and stop are
    inclusive. In other words ``start:stop:stepj`` is interpreted as
    ``np.linspace(start, stop, step, endpoint=1)`` inside of the brackets.
    After expansion of slice notation, all comma separated sequences are
    concatenated together.

    Optional character strings placed as the first element of the index
    expression can be used to change the output. The strings 'r' or 'c' result
    in matrix output. If the result is 1-D and 'r' is specified a 1 x N (row)
    matrix is produced. If the result is 1-D and 'c' is specified, then a N x 1
    (column) matrix is produced. If the result is 2-D then both provide the
    same matrix result.

    A string integer specifies which axis to stack multiple comma separated
    arrays along. A string of two comma-separated integers allows indication
    of the minimum number of dimensions to force each entry into as the
    second integer (the axis to concatenate along is still the first integer).

    A string with three comma-separated integers allows specification of the
    axis to concatenate along, the minimum number of dimensions to force the
    entries to, and which axis should contain the start of the arrays which
    are less than the specified number of dimensions. In other words the third
    integer allows you to specify where the 1's should be placed in the shape
    of the arrays that have their shapes upgraded. By default, they are placed
    in the front of the shape tuple. The third argument allows you to specify
    where the start of the array should be instead. Thus, a third argument of
    '0' would place the 1's at the end of the array shape. Negative integers
    specify where in the new shape tuple the last dimension of upgraded arrays
    should be placed, so the default is '-1'.

    Parameters
    ----------
    Not a function, so takes no parameters


    Returns
    -------
    A concatenated ndarray or matrix.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    c_ : Translates slice objects to concatenation along the second axis.

    Examples
    --------
    >>> import numpy as np
    >>> np.r_[np.array([1,2,3]), 0, 0, np.array([4,5,6])]
    array([1, 2, 3, ..., 4, 5, 6])
    >>> np.r_[-1:1:6j, [0]*3, 5, 6]
    array([-1. , -0.6, -0.2,  0.2,  0.6,  1. ,  0. ,  0. ,  0. ,  5. ,  6. ])

    String integers specify the axis to concatenate along or the minimum
    number of dimensions to force entries into.

    >>> a = np.array([[0, 1, 2], [3, 4, 5]])
    >>> np.r_['-1', a, a] # concatenate along last axis
    array([[0, 1, 2, 0, 1, 2],
           [3, 4, 5, 3, 4, 5]])
    >>> np.r_['0,2', [1,2,3], [4,5,6]] # concatenate along first axis, dim>=2
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> np.r_['0,2,0', [1,2,3], [4,5,6]]
    array([[1],
           [2],
           [3],
           [4],
           [5],
           [6]])
    >>> np.r_['1,2,0', [1,2,3], [4,5,6]]
    array([[1, 4],
           [2, 5],
           [3, 6]])

    Using 'r' or 'c' as a first string argument creates a matrix.

    >>> np.r_['r',[1,2,3], [4,5,6]]
    matrix([[1, 2, 3, 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, 0)


r_ = RClass()


class CClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the second axis.

    This is short-hand for ``np.r_['-1,2,0', index expression]``, which is
    useful because of its common occurrence. In particular, arrays will be
    stacked along their last axis after being upgraded to at least 2-D with
    1's post-pended to the shape (column vectors made out of 1-D arrays).

    See Also
    --------
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    r_ : For more detailed documentation.

    Examples
    --------
    >>> import numpy as np
    >>> np.c_[np.array([1,2,3]), np.array([4,5,6])]
    array([[1, 4],
           [2, 5],
           [3, 6]])
    >>> np.c_[np.array([[1,2,3]]), 0, 0, np.array([[4,5,6]])]
    array([[1, 2, 3, ..., 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, -1, ndmin=2, trans1d=0)


c_ = CClass()


@set_module('numpy')
class ndenumerate:
    """
    Multidimensional index iterator.

    Return an iterator yielding pairs of array coordinates and values.

    Parameters
    ----------
    arr : ndarray
      Input array.

    See Also
    --------
    ndindex, flatiter

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> for index, x in np.ndenumerate(a):
    ...     print(index, x)
    (0, 0) 1
    (0, 1) 2
    (1, 0) 3
    (1, 1) 4

    """

    def __init__(self, arr):
        self.iter = np.asarray(arr).flat

    def __next__(self):
        """
        Standard iterator method, returns the index tuple and array value.

        Returns
        -------
        coords : tuple of ints
            The indices of the current iteration.
        val : scalar
            The array element of the current iteration.

        """
        return self.iter.coords, next(self.iter)

    def __iter__(self):
        return self


@set_module('numpy')
class ndindex:
    """
    An N-dimensional iterator object to index arrays.

    Given the shape of an array, an `ndindex` instance iterates over
    the N-dimensional index of the array. At each iteration a tuple
    of indices is returned, the last dimension is iterated over first.

    Parameters
    ----------
    shape : ints, or a single tuple of ints
        The size of each dimension of the array can be passed as
        individual parameters or as the elements of a tuple.

    See Also
    --------
    ndenumerate, flatiter

    Examples
    --------
    >>> import numpy as np

    Dimensions as individual arguments

    >>> for index in np.ndindex(3, 2, 1):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    Same dimensions - but in a tuple ``(3, 2, 1)``

    >>> for index in np.ndindex((3, 2, 1)):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    """

    def __init__(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], tuple):
            shape = shape[0]
        x = as_strided(_nx.zeros(1), shape=shape,
                       strides=_nx.zeros_like(shape))
        self._it = _nx.nditer(x, flags=['multi_index', 'zerosize_ok'],
                              order='C')

    def __iter__(self):
        return self

    def ndincr(self):
        """
        Increment the multi-dimensional index by one.

        This method is for backward compatibility only: do not use.

        .. deprecated:: 1.20.0
            This method has been advised against since numpy 1.8.0, but only
            started emitting DeprecationWarning as of this version.
        """
        # NumPy 1.20.0, 2020-09-08
        warnings.warn(
            "`ndindex.ndincr()` is deprecated, use `next(ndindex)` instead",
            DeprecationWarning, stacklevel=2)
        next(self)

    def __next__(self):
        """
        Standard iterator method, updates the index and returns the index
        tuple.

        Returns
        -------
        val : tuple of ints
            Returns a tuple containing the indices of the current
            iteration.

        """
        next(self._it)
        return self._it.multi_index


# You can do all this with slice() plus a few special objects,
# but there's a lot to remember. This version is simpler because
# it uses the standard array indexing syntax.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-23
#
# Cosmetic changes by T. Oliphant 2001
#
#

class IndexExpression:
    """
    A nicer way to build up index tuples for arrays.

    .. note::
       Use one of the two predefined instances ``index_exp`` or `s_`
       rather than directly using `IndexExpression`.

    For any index combination, including slicing and axis insertion,
    ``a[indices]`` is the same as ``a[np.index_exp[indices]]`` for any
    array `a`. However, ``np.index_exp[indices]`` can be used anywhere
    in Python code and returns a tuple of slice objects that can be
    used in the construction of complex index expressions.

    Parameters
    ----------
    maketuple : bool
        If True, always returns a tuple.

    See Also
    --------
    s_ : Predefined instance without tuple conversion:
       `s_ = IndexExpression(maketuple=False)`.
       The ``index_exp`` is another predefined instance that
       always returns a tuple:
       `index_exp = IndexExpression(maketuple=True)`.

    Notes
    -----
    You can do all this with :class:`slice` plus a few special objects,
    but there's a lot to remember and this version is simpler because
    it uses the standard array indexing syntax.

    Examples
    --------
    >>> import numpy as np
    >>> np.s_[2::2]
    slice(2, None, 2)
    >>> np.index_exp[2::2]
    (slice(2, None, 2),)

    >>> np.array([0, 1, 2, 3, 4])[np.s_[2::2]]
    array([2, 4])

    """
    __slots__ = ('maketuple',)

    def __init__(self, maketuple):
        self.maketuple = maketuple

    def __getitem__(self, item):
        if self.maketuple and not isinstance(item, tuple):
            return (item,)
        else:
            return item


index_exp = IndexExpression(maketuple=True)
s_ = IndexExpression(maketuple=False)

# End contribution from Konrad.


# The following functions complement those in twodim_base, but are
# applicable to N-dimensions.


def _fill_diagonal_dispatcher(a, val, wrap=None):
    return (a,)


@array_function_dispatch(_fill_diagonal_dispatcher)
def fill_diagonal(a, val, wrap=False):
    """Fill the main diagonal of the given array of any dimensionality.

    For an array `a` with ``a.ndim >= 2``, the diagonal is the list of
    values ``a[i, ..., i]`` with indices ``i`` all identical.  This function
    modifies the input array in-place without returning a value.

    Parameters
    ----------
    a : array, at least 2-D.
      Array whose diagonal is to be filled in-place.
    val : scalar or array_like
      Value(s) to write on the diagonal. If `val` is scalar, the value is
      written along the diagonal. If array-like, the flattened `val` is
      written along the diagonal, repeating if necessary to fill all
      diagonal entries.

    wrap : bool
      For tall matrices in NumPy version up to 1.6.2, the
      diagonal "wrapped" after N columns. You can have this behavior
      with this option. This affects only tall matrices.

    See also
    --------
    diag_indices, diag_indices_from

    Notes
    -----
    This functionality can be obtained via `diag_indices`, but internally
    this version uses a much faster implementation that never constructs the
    indices and uses simple slicing.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), int)
    >>> np.fill_diagonal(a, 5)
    >>> a
    array([[5, 0, 0],
           [0, 5, 0],
           [0, 0, 5]])

    The same function can operate on a 4-D array:

    >>> a = np.zeros((3, 3, 3, 3), int)
    >>> np.fill_diagonal(a, 4)

    We only show a few blocks for clarity:

    >>> a[0, 0]
    array([[4, 0, 0],
           [0, 0, 0],
           [0, 0, 0]])
    >>> a[1, 1]
    array([[0, 0, 0],
           [0, 4, 0],
           [0, 0, 0]])
    >>> a[2, 2]
    array([[0, 0, 0],
           [0, 0, 0],
           [0, 0, 4]])

    The wrap option affects only tall matrices:

    >>> # tall matrices no wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [0, 0, 0]])

    >>> # tall matrices wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [4, 0, 0]])

    >>> # wide matrices
    >>> a = np.zeros((3, 5), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0, 0, 0],
           [0, 4, 0, 0, 0],
           [0, 0, 4, 0, 0]])

    The anti-diagonal can be filled by reversing the order of elements
    using either `numpy.flipud` or `numpy.fliplr`.

    >>> a = np.zeros((3, 3), int);
    >>> np.fill_diagonal(np.fliplr(a), [1,2,3])  # Horizontal flip
    >>> a
    array([[0, 0, 1],
           [0, 2, 0],
           [3, 0, 0]])
    >>> np.fill_diagonal(np.flipud(a), [1,2,3])  # Vertical flip
    >>> a
    array([[0, 0, 3],
           [0, 2, 0],
           [1, 0, 0]])

    Note that the order in which the diagonal is filled varies depending
    on the flip function.
    """
    if a.ndim < 2:
        raise ValueError("array must be at least 2-d")
    end = None
    if a.ndim == 2:
        # Explicit, fast formula for the common case.  For 2-d arrays, we
        # accept rectangular ones.
        step = a.shape[1] + 1
        # This is needed to don't have tall matrix have the diagonal wrap.
        if not wrap:
            end = a.shape[1] * a.shape[1]
    else:
        # For more than d=2, the strided formula is only valid for arrays with
        # all dimensions equal, so we check first.
        if not np.all(diff(a.shape) == 0):
            raise ValueError("All dimensions of input must be of equal length")
        step = 1 + (np.cumprod(a.shape[:-1])).sum()

    # Write the value out into the diagonal.
    a.flat[:end:step] = val


@set_module('numpy')
def diag_indices(n, ndim=2):
    """
    Return the indices to access the main diagonal of an array.

    This returns a tuple of indices that can be used to access the main
    diagonal of an array `a` with ``a.ndim >= 2`` dimensions and shape
    (n, n, ..., n). For ``a.ndim = 2`` this is the usual diagonal, for
    ``a.ndim > 2`` this is the set of indices to access ``a[i, i, ..., i]``
    for ``i = [0..n-1]``.

    Parameters
    ----------
    n : int
      The size, along each dimension, of the arrays for which the returned
      indices can be used.

    ndim : int, optional
      The number of dimensions.

    See Also
    --------
    diag_indices_from

    Examples
    --------
    >>> import numpy as np

    Create a set of indices to access the diagonal of a (4, 4) array:

    >>> di = np.diag_indices(4)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))
    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])
    >>> a[di] = 100
    >>> a
    array([[100,   1,   2,   3],
           [  4, 100,   6,   7],
           [  8,   9, 100,  11],
           [ 12,  13,  14, 100]])

    Now, we create indices to manipulate a 3-D array:

    >>> d3 = np.diag_indices(2, 3)
    >>> d3
    (array([0, 1]), array([0, 1]), array([0, 1]))

    And use it to set the diagonal of an array of zeros to 1:

    >>> a = np.zeros((2, 2, 2), dtype=int)
    >>> a[d3] = 1
    >>> a
    array([[[1, 0],
            [0, 0]],
           [[0, 0],
            [0, 1]]])

    """
    idx = np.arange(n)
    return (idx,) * ndim


def _diag_indices_from(arr):
    return (arr,)


@array_function_dispatch(_diag_indices_from)
def diag_indices_from(arr):
    """
    Return the indices to access the main diagonal of an n-dimensional array.

    See `diag_indices` for full details.

    Parameters
    ----------
    arr : array, at least 2-D

    See Also
    --------
    diag_indices

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array.

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Get the indices of the diagonal elements.

    >>> di = np.diag_indices_from(a)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    >>> a[di]
    array([ 0,  5, 10, 15])

    This is simply syntactic sugar for diag_indices.

    >>> np.diag_indices(a.shape[0])
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    """

    if not arr.ndim >= 2:
        raise ValueError("input array must be at least 2-d")
    # For more than d=2, the strided formula is only valid for arrays with
    # all dimensions equal, so we check first.
    if not np.all(diff(arr.shape) == 0):
        raise ValueError("All dimensions of input must be of equal length")

    return diag_indices(arr.shape[0], arr.ndim)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_format.py ===
# doctest
r''' Test the .npy file format.

Set up:

    >>> import sys
    >>> from io import BytesIO
    >>> from numpy.lib import format
    >>>
    >>> scalars = [
    ...     np.uint8,
    ...     np.int8,
    ...     np.uint16,
    ...     np.int16,
    ...     np.uint32,
    ...     np.int32,
    ...     np.uint64,
    ...     np.int64,
    ...     np.float32,
    ...     np.float64,
    ...     np.complex64,
    ...     np.complex128,
    ...     object,
    ... ]
    >>>
    >>> basic_arrays = []
    >>>
    >>> for scalar in scalars:
    ...     for endian in '<>':
    ...         dtype = np.dtype(scalar).newbyteorder(endian)
    ...         basic = np.arange(15).astype(dtype)
    ...         basic_arrays.extend([
    ...             np.array([], dtype=dtype),
    ...             np.array(10, dtype=dtype),
    ...             basic,
    ...             basic.reshape((3,5)),
    ...             basic.reshape((3,5)).T,
    ...             basic.reshape((3,5))[::-1,::2],
    ...         ])
    ...
    >>>
    >>> Pdescr = [
    ...     ('x', 'i4', (2,)),
    ...     ('y', 'f8', (2, 2)),
    ...     ('z', 'u1')]
    >>>
    >>>
    >>> PbufferT = [
    ...     ([3,2], [[6.,4.],[6.,4.]], 8),
    ...     ([4,3], [[7.,5.],[7.,5.]], 9),
    ...     ]
    >>>
    >>>
    >>> Ndescr = [
    ...     ('x', 'i4', (2,)),
    ...     ('Info', [
    ...         ('value', 'c16'),
    ...         ('y2', 'f8'),
    ...         ('Info2', [
    ...             ('name', 'S2'),
    ...             ('value', 'c16', (2,)),
    ...             ('y3', 'f8', (2,)),
    ...             ('z3', 'u4', (2,))]),
    ...         ('name', 'S2'),
    ...         ('z2', 'b1')]),
    ...     ('color', 'S2'),
    ...     ('info', [
    ...         ('Name', 'U8'),
    ...         ('Value', 'c16')]),
    ...     ('y', 'f8', (2, 2)),
    ...     ('z', 'u1')]
    >>>
    >>>
    >>> NbufferT = [
    ...     ([3,2], (6j, 6., ('nn', [6j,4j], [6.,4.], [1,2]), 'NN', True), 'cc', ('NN', 6j), [[6.,4.],[6.,4.]], 8),
    ...     ([4,3], (7j, 7., ('oo', [7j,5j], [7.,5.], [2,1]), 'OO', False), 'dd', ('OO', 7j), [[7.,5.],[7.,5.]], 9),
    ...     ]
    >>>
    >>>
    >>> record_arrays = [
    ...     np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('<')),
    ...     np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('<')),
    ...     np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('>')),
    ...     np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('>')),
    ... ]

Test the magic string writing.

    >>> format.magic(1, 0)
    '\x93NUMPY\x01\x00'
    >>> format.magic(0, 0)
    '\x93NUMPY\x00\x00'
    >>> format.magic(255, 255)
    '\x93NUMPY\xff\xff'
    >>> format.magic(2, 5)
    '\x93NUMPY\x02\x05'

Test the magic string reading.

    >>> format.read_magic(BytesIO(format.magic(1, 0)))
    (1, 0)
    >>> format.read_magic(BytesIO(format.magic(0, 0)))
    (0, 0)
    >>> format.read_magic(BytesIO(format.magic(255, 255)))
    (255, 255)
    >>> format.read_magic(BytesIO(format.magic(2, 5)))
    (2, 5)

Test the header writing.

    >>> for arr in basic_arrays + record_arrays:
    ...     f = BytesIO()
    ...     format.write_array_header_1_0(f, arr)   # XXX: arr is not a dict, items gets called on it
    ...     print(repr(f.getvalue()))
    ...
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<f4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>f4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<f8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>f8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<c8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>c8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (0,)}             \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': ()}               \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (15,)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (3, 5)}           \n"
    "F\x00{'descr': '<c16', 'fortran_order': True, 'shape': (5, 3)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (3, 3)}           \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (0,)}             \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': ()}               \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (15,)}            \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (3, 5)}           \n"
    "F\x00{'descr': '>c16', 'fortran_order': True, 'shape': (5, 3)}            \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (3, 3)}           \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "v\x00{'descr': [('x', '<i4', (2,)), ('y', '<f8', (2, 2)), ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}         \n"
    "\x16\x02{'descr': [('x', '<i4', (2,)),\n           ('Info',\n            [('value', '<c16'),\n             ('y2', '<f8'),\n             ('Info2',\n              [('name', '|S2'),\n               ('value', '<c16', (2,)),\n               ('y3', '<f8', (2,)),\n               ('z3', '<u4', (2,))]),\n             ('name', '|S2'),\n             ('z2', '|b1')]),\n           ('color', '|S2'),\n           ('info', [('Name', '<U8'), ('Value', '<c16')]),\n           ('y', '<f8', (2, 2)),\n           ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}      \n"
    "v\x00{'descr': [('x', '>i4', (2,)), ('y', '>f8', (2, 2)), ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}         \n"
    "\x16\x02{'descr': [('x', '>i4', (2,)),\n           ('Info',\n            [('value', '>c16'),\n             ('y2', '>f8'),\n             ('Info2',\n              [('name', '|S2'),\n               ('value', '>c16', (2,)),\n               ('y3', '>f8', (2,)),\n               ('z3', '>u4', (2,))]),\n             ('name', '|S2'),\n             ('z2', '|b1')]),\n           ('color', '|S2'),\n           ('info', [('Name', '>U8'), ('Value', '>c16')]),\n           ('y', '>f8', (2, 2)),\n           ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}      \n"
'''
import os
import sys
import warnings
from io import BytesIO

import pytest

import numpy as np
from numpy.lib import format
from numpy.testing import (
    IS_64BIT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_array_equal,
    assert_raises,
    assert_raises_regex,
    assert_warns,
)
from numpy.testing._private.utils import requires_memory

# Generate some basic arrays to test with.
scalars = [
    np.uint8,
    np.int8,
    np.uint16,
    np.int16,
    np.uint32,
    np.int32,
    np.uint64,
    np.int64,
    np.float32,
    np.float64,
    np.complex64,
    np.complex128,
    object,
]
basic_arrays = []
for scalar in scalars:
    for endian in '<>':
        dtype = np.dtype(scalar).newbyteorder(endian)
        basic = np.arange(1500).astype(dtype)
        basic_arrays.extend([
            # Empty
            np.array([], dtype=dtype),
            # Rank-0
            np.array(10, dtype=dtype),
            # 1-D
            basic,
            # 2-D C-contiguous
            basic.reshape((30, 50)),
            # 2-D F-contiguous
            basic.reshape((30, 50)).T,
            # 2-D non-contiguous
            basic.reshape((30, 50))[::-1, ::2],
        ])

# More complicated record arrays.
# This is the structure of the table used for plain objects:
#
# +-+-+-+
# |x|y|z|
# +-+-+-+

# Structure of a plain array description:
Pdescr = [
    ('x', 'i4', (2,)),
    ('y', 'f8', (2, 2)),
    ('z', 'u1')]

# A plain list of tuples with values for testing:
PbufferT = [
    # x     y                  z
    ([3, 2], [[6., 4.], [6., 4.]], 8),
    ([4, 3], [[7., 5.], [7., 5.]], 9),
    ]


# This is the structure of the table used for nested objects (DON'T PANIC!):
#
# +-+---------------------------------+-----+----------+-+-+
# |x|Info                             |color|info      |y|z|
# | +-----+--+----------------+----+--+     +----+-----+ | |
# | |value|y2|Info2           |name|z2|     |Name|Value| | |
# | |     |  +----+-----+--+--+    |  |     |    |     | | |
# | |     |  |name|value|y3|z3|    |  |     |    |     | | |
# +-+-----+--+----+-----+--+--+----+--+-----+----+-----+-+-+
#

# The corresponding nested array description:
Ndescr = [
    ('x', 'i4', (2,)),
    ('Info', [
        ('value', 'c16'),
        ('y2', 'f8'),
        ('Info2', [
            ('name', 'S2'),
            ('value', 'c16', (2,)),
            ('y3', 'f8', (2,)),
            ('z3', 'u4', (2,))]),
        ('name', 'S2'),
        ('z2', 'b1')]),
    ('color', 'S2'),
    ('info', [
        ('Name', 'U8'),
        ('Value', 'c16')]),
    ('y', 'f8', (2, 2)),
    ('z', 'u1')]

NbufferT = [
    # x     Info                                                color info        y                  z
    #       value y2 Info2                            name z2         Name Value
    #                name   value    y3       z3
    ([3, 2], (6j, 6., ('nn', [6j, 4j], [6., 4.], [1, 2]), 'NN', True),
     'cc', ('NN', 6j), [[6., 4.], [6., 4.]], 8),
    ([4, 3], (7j, 7., ('oo', [7j, 5j], [7., 5.], [2, 1]), 'OO', False),
     'dd', ('OO', 7j), [[7., 5.], [7., 5.]], 9),
    ]

record_arrays = [
    np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('<')),
    np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('<')),
    np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('>')),
    np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('>')),
    np.zeros(1, dtype=[('c', ('<f8', (5,)), (2,))])
]


# BytesIO that reads a random number of bytes at a time
class BytesIOSRandomSize(BytesIO):
    def read(self, size=None):
        import random
        size = random.randint(1, size)
        return super().read(size)


def roundtrip(arr):
    f = BytesIO()
    format.write_array(f, arr)
    f2 = BytesIO(f.getvalue())
    arr2 = format.read_array(f2, allow_pickle=True)
    return arr2


def roundtrip_randsize(arr):
    f = BytesIO()
    format.write_array(f, arr)
    f2 = BytesIOSRandomSize(f.getvalue())
    arr2 = format.read_array(f2)
    return arr2


def roundtrip_truncated(arr):
    f = BytesIO()
    format.write_array(f, arr)
    # BytesIO is one byte short
    f2 = BytesIO(f.getvalue()[0:-1])
    arr2 = format.read_array(f2)
    return arr2

def assert_equal_(o1, o2):
    assert_(o1 == o2)


def test_roundtrip():
    for arr in basic_arrays + record_arrays:
        arr2 = roundtrip(arr)
        assert_array_equal(arr, arr2)


def test_roundtrip_randsize():
    for arr in basic_arrays + record_arrays:
        if arr.dtype != object:
            arr2 = roundtrip_randsize(arr)
            assert_array_equal(arr, arr2)


def test_roundtrip_truncated():
    for arr in basic_arrays:
        if arr.dtype != object:
            assert_raises(ValueError, roundtrip_truncated, arr)

def test_file_truncated(tmp_path):
    path = tmp_path / "a.npy"
    for arr in basic_arrays:
        if arr.dtype != object:
            with open(path, 'wb') as f:
                format.write_array(f, arr)
            # truncate the file by one byte
            with open(path, 'rb+') as f:
                f.seek(-1, os.SEEK_END)
                f.truncate()
            with open(path, 'rb') as f:
                with pytest.raises(
                    ValueError,
                    match=(
                        r"EOF: reading array header, "
                        r"expected (\d+) bytes got (\d+)"
                    ) if arr.size == 0 else (
                        r"Failed to read all data for array\. "
                        r"Expected \(.*?\) = (\d+) elements, "
                        r"could only read (\d+) elements\. "
                        r"\(file seems not fully written\?\)"
                    )
                ):
                    _ = format.read_array(f)

def test_long_str():
    # check items larger than internal buffer size, gh-4027
    long_str_arr = np.ones(1, dtype=np.dtype((str, format.BUFFER_SIZE + 1)))
    long_str_arr2 = roundtrip(long_str_arr)
    assert_array_equal(long_str_arr, long_str_arr2)


@pytest.mark.skipif(IS_WASM, reason="memmap doesn't work correctly")
@pytest.mark.slow
def test_memmap_roundtrip(tmpdir):
    for i, arr in enumerate(basic_arrays + record_arrays):
        if arr.dtype.hasobject:
            # Skip these since they can't be mmap'ed.
            continue
        # Write it out normally and through mmap.
        nfn = os.path.join(tmpdir, f'normal{i}.npy')
        mfn = os.path.join(tmpdir, f'memmap{i}.npy')
        with open(nfn, 'wb') as fp:
            format.write_array(fp, arr)

        fortran_order = (
            arr.flags.f_contiguous and not arr.flags.c_contiguous)
        ma = format.open_memmap(mfn, mode='w+', dtype=arr.dtype,
                                shape=arr.shape, fortran_order=fortran_order)
        ma[...] = arr
        ma.flush()

        # Check that both of these files' contents are the same.
        with open(nfn, 'rb') as fp:
            normal_bytes = fp.read()
        with open(mfn, 'rb') as fp:
            memmap_bytes = fp.read()
        assert_equal_(normal_bytes, memmap_bytes)

        # Check that reading the file using memmap works.
        ma = format.open_memmap(nfn, mode='r')
        ma.flush()


def test_compressed_roundtrip(tmpdir):
    arr = np.random.rand(200, 200)
    npz_file = os.path.join(tmpdir, 'compressed.npz')
    np.savez_compressed(npz_file, arr=arr)
    with np.load(npz_file) as npz:
        arr1 = npz['arr']
    assert_array_equal(arr, arr1)


# aligned
dt1 = np.dtype('i1, i4, i1', align=True)
# non-aligned, explicit offsets
dt2 = np.dtype({'names': ['a', 'b'], 'formats': ['i4', 'i4'],
                'offsets': [1, 6]})
# nested struct-in-struct
dt3 = np.dtype({'names': ['c', 'd'], 'formats': ['i4', dt2]})
# field with '' name
dt4 = np.dtype({'names': ['a', '', 'b'], 'formats': ['i4'] * 3})
# titles
dt5 = np.dtype({'names': ['a', 'b'], 'formats': ['i4', 'i4'],
                'offsets': [1, 6], 'titles': ['aa', 'bb']})
# empty
dt6 = np.dtype({'names': [], 'formats': [], 'itemsize': 8})

@pytest.mark.parametrize("dt", [dt1, dt2, dt3, dt4, dt5, dt6])
def test_load_padded_dtype(tmpdir, dt):
    arr = np.zeros(3, dt)
    for i in range(3):
        arr[i] = i + 5
    npz_file = os.path.join(tmpdir, 'aligned.npz')
    np.savez(npz_file, arr=arr)
    with np.load(npz_file) as npz:
        arr1 = npz['arr']
    assert_array_equal(arr, arr1)


@pytest.mark.skipif(sys.version_info >= (3, 12), reason="see gh-23988")
@pytest.mark.xfail(IS_WASM, reason="Emscripten NODEFS has a buggy dup")
def test_python2_python3_interoperability():
    fname = 'win64python2.npy'
    path = os.path.join(os.path.dirname(__file__), 'data', fname)
    with pytest.warns(UserWarning, match="Reading.*this warning\\."):
        data = np.load(path)
    assert_array_equal(data, np.ones(2))


def test_pickle_python2_python3():
    # Test that loading object arrays saved on Python 2 works both on
    # Python 2 and Python 3 and vice versa
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    expected = np.array([None, range, '\u512a\u826f',
                         b'\xe4\xb8\x8d\xe8\x89\xaf'],
                        dtype=object)

    for fname in ['py2-np0-objarr.npy', 'py2-objarr.npy', 'py2-objarr.npz',
                  'py3-objarr.npy', 'py3-objarr.npz']:
        path = os.path.join(data_dir, fname)

        for encoding in ['bytes', 'latin1']:
            data_f = np.load(path, allow_pickle=True, encoding=encoding)
            if fname.endswith('.npz'):
                data = data_f['x']
                data_f.close()
            else:
                data = data_f

            if encoding == 'latin1' and fname.startswith('py2'):
                assert_(isinstance(data[3], str))
                assert_array_equal(data[:-1], expected[:-1])
                # mojibake occurs
                assert_array_equal(data[-1].encode(encoding), expected[-1])
            else:
                assert_(isinstance(data[3], bytes))
                assert_array_equal(data, expected)

        if fname.startswith('py2'):
            if fname.endswith('.npz'):
                data = np.load(path, allow_pickle=True)
                assert_raises(UnicodeError, data.__getitem__, 'x')
                data.close()
                data = np.load(path, allow_pickle=True, fix_imports=False,
                               encoding='latin1')
                assert_raises(ImportError, data.__getitem__, 'x')
                data.close()
            else:
                assert_raises(UnicodeError, np.load, path,
                              allow_pickle=True)
                assert_raises(ImportError, np.load, path,
                              allow_pickle=True, fix_imports=False,
                              encoding='latin1')


def test_pickle_disallow(tmpdir):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    path = os.path.join(data_dir, 'py2-objarr.npy')
    assert_raises(ValueError, np.load, path,
                  allow_pickle=False, encoding='latin1')

    path = os.path.join(data_dir, 'py2-objarr.npz')
    with np.load(path, allow_pickle=False, encoding='latin1') as f:
        assert_raises(ValueError, f.__getitem__, 'x')

    path = os.path.join(tmpdir, 'pickle-disabled.npy')
    assert_raises(ValueError, np.save, path, np.array([None], dtype=object),
                  allow_pickle=False)

@pytest.mark.parametrize('dt', [
    np.dtype(np.dtype([('a', np.int8),
                       ('b', np.int16),
                       ('c', np.int32),
                      ], align=True),
             (3,)),
    np.dtype([('x', np.dtype({'names': ['a', 'b'],
                              'formats': ['i1', 'i1'],
                              'offsets': [0, 4],
                              'itemsize': 8,
                             },
                    (3,)),
               (4,),
             )]),
    np.dtype([('x',
                   ('<f8', (5,)),
                   (2,),
               )]),
    np.dtype([('x', np.dtype((
        np.dtype((
            np.dtype({'names': ['a', 'b'],
                      'formats': ['i1', 'i1'],
                      'offsets': [0, 4],
                      'itemsize': 8}),
            (3,)
            )),
        (4,)
        )))
        ]),
    np.dtype([
        ('a', np.dtype((
            np.dtype((
                np.dtype((
                    np.dtype([
                        ('a', int),
                        ('b', np.dtype({'names': ['a', 'b'],
                                        'formats': ['i1', 'i1'],
                                        'offsets': [0, 4],
                                        'itemsize': 8})),
                    ]),
                    (3,),
                )),
                (4,),
            )),
            (5,),
        )))
        ]),
    ])
def test_descr_to_dtype(dt):
    dt1 = format.descr_to_dtype(dt.descr)
    assert_equal_(dt1, dt)
    arr1 = np.zeros(3, dt)
    arr2 = roundtrip(arr1)
    assert_array_equal(arr1, arr2)

def test_version_2_0():
    f = BytesIO()
    # requires more than 2 byte for header
    dt = [(("%d" % i) * 100, float) for i in range(500)]
    d = np.ones(1000, dtype=dt)

    format.write_array(f, d, version=(2, 0))
    with warnings.catch_warnings(record=True) as w:
        warnings.filterwarnings('always', '', UserWarning)
        format.write_array(f, d)
        assert_(w[0].category is UserWarning)

    # check alignment of data portion
    f.seek(0)
    header = f.readline()
    assert_(len(header) % format.ARRAY_ALIGN == 0)

    f.seek(0)
    n = format.read_array(f, max_header_size=200000)
    assert_array_equal(d, n)

    # 1.0 requested but data cannot be saved this way
    assert_raises(ValueError, format.write_array, f, d, (1, 0))


@pytest.mark.skipif(IS_WASM, reason="memmap doesn't work correctly")
def test_version_2_0_memmap(tmpdir):
    # requires more than 2 byte for header
    dt = [(("%d" % i) * 100, float) for i in range(500)]
    d = np.ones(1000, dtype=dt)
    tf1 = os.path.join(tmpdir, 'version2_01.npy')
    tf2 = os.path.join(tmpdir, 'version2_02.npy')

    # 1.0 requested but data cannot be saved this way
    assert_raises(ValueError, format.open_memmap, tf1, mode='w+', dtype=d.dtype,
                            shape=d.shape, version=(1, 0))

    ma = format.open_memmap(tf1, mode='w+', dtype=d.dtype,
                            shape=d.shape, version=(2, 0))
    ma[...] = d
    ma.flush()
    ma = format.open_memmap(tf1, mode='r', max_header_size=200000)
    assert_array_equal(ma, d)

    with warnings.catch_warnings(record=True) as w:
        warnings.filterwarnings('always', '', UserWarning)
        ma = format.open_memmap(tf2, mode='w+', dtype=d.dtype,
                                shape=d.shape, version=None)
        assert_(w[0].category is UserWarning)
        ma[...] = d
        ma.flush()

    ma = format.open_memmap(tf2, mode='r', max_header_size=200000)

    assert_array_equal(ma, d)

@pytest.mark.parametrize("mmap_mode", ["r", None])
def test_huge_header(tmpdir, mmap_mode):
    f = os.path.join(tmpdir, 'large_header.npy')
    arr = np.array(1, dtype="i," * 10000 + "i")

    with pytest.warns(UserWarning, match=".*format 2.0"):
        np.save(f, arr)

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, mmap_mode=mmap_mode)

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, mmap_mode=mmap_mode, max_header_size=20000)

    res = np.load(f, mmap_mode=mmap_mode, allow_pickle=True)
    assert_array_equal(res, arr)

    res = np.load(f, mmap_mode=mmap_mode, max_header_size=180000)
    assert_array_equal(res, arr)

def test_huge_header_npz(tmpdir):
    f = os.path.join(tmpdir, 'large_header.npz')
    arr = np.array(1, dtype="i," * 10000 + "i")

    with pytest.warns(UserWarning, match=".*format 2.0"):
        np.savez(f, arr=arr)

    # Only getting the array from the file actually reads it
    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f)["arr"]

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, max_header_size=20000)["arr"]

    res = np.load(f, allow_pickle=True)["arr"]
    assert_array_equal(res, arr)

    res = np.load(f, max_header_size=180000)["arr"]
    assert_array_equal(res, arr)

def test_write_version():
    f = BytesIO()
    arr = np.arange(1)
    # These should pass.
    format.write_array(f, arr, version=(1, 0))
    format.write_array(f, arr)

    format.write_array(f, arr, version=None)
    format.write_array(f, arr)

    format.write_array(f, arr, version=(2, 0))
    format.write_array(f, arr)

    # These should all fail.
    bad_versions = [
        (1, 1),
        (0, 0),
        (0, 1),
        (2, 2),
        (255, 255),
    ]
    for version in bad_versions:
        with assert_raises_regex(ValueError,
                                 'we only support format version.*'):
            format.write_array(f, arr, version=version)


bad_version_magic = [
    b'\x93NUMPY\x01\x01',
    b'\x93NUMPY\x00\x00',
    b'\x93NUMPY\x00\x01',
    b'\x93NUMPY\x02\x00',
    b'\x93NUMPY\x02\x02',
    b'\x93NUMPY\xff\xff',
]
malformed_magic = [
    b'\x92NUMPY\x01\x00',
    b'\x00NUMPY\x01\x00',
    b'\x93numpy\x01\x00',
    b'\x93MATLB\x01\x00',
    b'\x93NUMPY\x01',
    b'\x93NUMPY',
    b'',
]

def test_read_magic():
    s1 = BytesIO()
    s2 = BytesIO()

    arr = np.ones((3, 6), dtype=float)

    format.write_array(s1, arr, version=(1, 0))
    format.write_array(s2, arr, version=(2, 0))

    s1.seek(0)
    s2.seek(0)

    version1 = format.read_magic(s1)
    version2 = format.read_magic(s2)

    assert_(version1 == (1, 0))
    assert_(version2 == (2, 0))

    assert_(s1.tell() == format.MAGIC_LEN)
    assert_(s2.tell() == format.MAGIC_LEN)

def test_read_magic_bad_magic():
    for magic in malformed_magic:
        f = BytesIO(magic)
        assert_raises(ValueError, format.read_array, f)


def test_read_version_1_0_bad_magic():
    for magic in bad_version_magic + malformed_magic:
        f = BytesIO(magic)
        assert_raises(ValueError, format.read_array, f)


def test_bad_magic_args():
    assert_raises(ValueError, format.magic, -1, 1)
    assert_raises(ValueError, format.magic, 256, 1)
    assert_raises(ValueError, format.magic, 1, -1)
    assert_raises(ValueError, format.magic, 1, 256)


def test_large_header():
    s = BytesIO()
    d = {'shape': (), 'fortran_order': False, 'descr': '<i8'}
    format.write_array_header_1_0(s, d)

    s = BytesIO()
    d['descr'] = [('x' * 256 * 256, '<i8')]
    assert_raises(ValueError, format.write_array_header_1_0, s, d)


def test_read_array_header_1_0():
    s = BytesIO()

    arr = np.ones((3, 6), dtype=float)
    format.write_array(s, arr, version=(1, 0))

    s.seek(format.MAGIC_LEN)
    shape, fortran, dtype = format.read_array_header_1_0(s)

    assert_(s.tell() % format.ARRAY_ALIGN == 0)
    assert_((shape, fortran, dtype) == ((3, 6), False, float))


def test_read_array_header_2_0():
    s = BytesIO()

    arr = np.ones((3, 6), dtype=float)
    format.write_array(s, arr, version=(2, 0))

    s.seek(format.MAGIC_LEN)
    shape, fortran, dtype = format.read_array_header_2_0(s)

    assert_(s.tell() % format.ARRAY_ALIGN == 0)
    assert_((shape, fortran, dtype) == ((3, 6), False, float))


def test_bad_header():
    # header of length less than 2 should fail
    s = BytesIO()
    assert_raises(ValueError, format.read_array_header_1_0, s)
    s = BytesIO(b'1')
    assert_raises(ValueError, format.read_array_header_1_0, s)

    # header shorter than indicated size should fail
    s = BytesIO(b'\x01\x00')
    assert_raises(ValueError, format.read_array_header_1_0, s)

    # headers without the exact keys required should fail
    # d = {"shape": (1, 2),
    #      "descr": "x"}
    s = BytesIO(
        b"\x93NUMPY\x01\x006\x00{'descr': 'x', 'shape': (1, 2), }"
        b"                    \n"
    )
    assert_raises(ValueError, format.read_array_header_1_0, s)

    d = {"shape": (1, 2),
         "fortran_order": False,
         "descr": "x",
         "extrakey": -1}
    s = BytesIO()
    format.write_array_header_1_0(s, d)
    assert_raises(ValueError, format.read_array_header_1_0, s)


def test_large_file_support(tmpdir):
    if (sys.platform == 'win32' or sys.platform == 'cygwin'):
        pytest.skip("Unknown if Windows has sparse filesystems")
    # try creating a large sparse file
    tf_name = os.path.join(tmpdir, 'sparse_file')
    try:
        # seek past end would work too, but linux truncate somewhat
        # increases the chances that we have a sparse filesystem and can
        # avoid actually writing 5GB
        import subprocess as sp
        sp.check_call(["truncate", "-s", "5368709120", tf_name])
    except Exception:
        pytest.skip("Could not create 5GB large file")
    # write a small array to the end
    with open(tf_name, "wb") as f:
        f.seek(5368709120)
        d = np.arange(5)
        np.save(f, d)
    # read it back
    with open(tf_name, "rb") as f:
        f.seek(5368709120)
        r = np.load(f)
    assert_array_equal(r, d)


@pytest.mark.skipif(IS_PYPY, reason="flaky on PyPy")
@pytest.mark.skipif(not IS_64BIT, reason="test requires 64-bit system")
@pytest.mark.slow
@requires_memory(free_bytes=2 * 2**30)
def test_large_archive(tmpdir):
    # Regression test for product of saving arrays with dimensions of array
    # having a product that doesn't fit in int32.  See gh-7598 for details.
    shape = (2**30, 2)
    try:
        a = np.empty(shape, dtype=np.uint8)
    except MemoryError:
        pytest.skip("Could not create large file")

    fname = os.path.join(tmpdir, "large_archive")

    with open(fname, "wb") as f:
        np.savez(f, arr=a)

    del a

    with open(fname, "rb") as f:
        new_a = np.load(f)["arr"]

    assert new_a.shape == shape


def test_empty_npz(tmpdir):
    # Test for gh-9989
    fname = os.path.join(tmpdir, "nothing.npz")
    np.savez(fname)
    with np.load(fname) as nps:
        pass


def test_unicode_field_names(tmpdir):
    # gh-7391
    arr = np.array([
        (1, 3),
        (1, 2),
        (1, 3),
        (1, 2)
    ], dtype=[
        ('int', int),
        ('\N{CJK UNIFIED IDEOGRAPH-6574}\N{CJK UNIFIED IDEOGRAPH-5F62}', int)
    ])
    fname = os.path.join(tmpdir, "unicode.npy")
    with open(fname, 'wb') as f:
        format.write_array(f, arr, version=(3, 0))
    with open(fname, 'rb') as f:
        arr2 = format.read_array(f)
    assert_array_equal(arr, arr2)

    # notifies the user that 3.0 is selected
    with open(fname, 'wb') as f:
        with assert_warns(UserWarning):
            format.write_array(f, arr, version=None)

def test_header_growth_axis():
    for is_fortran_array, dtype_space, expected_header_length in [
        [False, 22, 128], [False, 23, 192], [True, 23, 128], [True, 24, 192]
    ]:
        for size in [10**i for i in range(format.GROWTH_AXIS_MAX_DIGITS)]:
            fp = BytesIO()
            format.write_array_header_1_0(fp, {
                'shape': (2, size) if is_fortran_array else (size, 2),
                'fortran_order': is_fortran_array,
                'descr': np.dtype([(' ' * dtype_space, int)])
            })

            assert len(fp.getvalue()) == expected_header_length

@pytest.mark.parametrize('dt', [
    np.dtype({'names': ['a', 'b'], 'formats':  [float, np.dtype('S3',
                 metadata={'some': 'stuff'})]}),
    np.dtype(int, metadata={'some': 'stuff'}),
    np.dtype([('subarray', (int, (2,)))], metadata={'some': 'stuff'}),
    # recursive: metadata on the field of a dtype
    np.dtype({'names': ['a', 'b'], 'formats': [
        float, np.dtype({'names': ['c'], 'formats': [np.dtype(int, metadata={})]})
    ]}),
    ])
@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
        reason="PyPy bug in error formatting")
def test_metadata_dtype(dt):
    # gh-14142
    arr = np.ones(10, dtype=dt)
    buf = BytesIO()
    with assert_warns(UserWarning):
        np.save(buf, arr)
    buf.seek(0)

    # Loading should work (metadata was stripped):
    arr2 = np.load(buf)
    # BUG: assert_array_equal does not check metadata
    from numpy.lib._utils_impl import drop_metadata
    assert_array_equal(arr, arr2)
    assert drop_metadata(arr.dtype) is not arr.dtype
    assert drop_metadata(arr2.dtype) is arr2.dtype

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_format.py ===
# doctest
r''' Test the .npy file format.

Set up:

    >>> import sys
    >>> from io import BytesIO
    >>> from numpy.lib import format
    >>>
    >>> scalars = [
    ...     np.uint8,
    ...     np.int8,
    ...     np.uint16,
    ...     np.int16,
    ...     np.uint32,
    ...     np.int32,
    ...     np.uint64,
    ...     np.int64,
    ...     np.float32,
    ...     np.float64,
    ...     np.complex64,
    ...     np.complex128,
    ...     object,
    ... ]
    >>>
    >>> basic_arrays = []
    >>>
    >>> for scalar in scalars:
    ...     for endian in '<>':
    ...         dtype = np.dtype(scalar).newbyteorder(endian)
    ...         basic = np.arange(15).astype(dtype)
    ...         basic_arrays.extend([
    ...             np.array([], dtype=dtype),
    ...             np.array(10, dtype=dtype),
    ...             basic,
    ...             basic.reshape((3,5)),
    ...             basic.reshape((3,5)).T,
    ...             basic.reshape((3,5))[::-1,::2],
    ...         ])
    ...
    >>>
    >>> Pdescr = [
    ...     ('x', 'i4', (2,)),
    ...     ('y', 'f8', (2, 2)),
    ...     ('z', 'u1')]
    >>>
    >>>
    >>> PbufferT = [
    ...     ([3,2], [[6.,4.],[6.,4.]], 8),
    ...     ([4,3], [[7.,5.],[7.,5.]], 9),
    ...     ]
    >>>
    >>>
    >>> Ndescr = [
    ...     ('x', 'i4', (2,)),
    ...     ('Info', [
    ...         ('value', 'c16'),
    ...         ('y2', 'f8'),
    ...         ('Info2', [
    ...             ('name', 'S2'),
    ...             ('value', 'c16', (2,)),
    ...             ('y3', 'f8', (2,)),
    ...             ('z3', 'u4', (2,))]),
    ...         ('name', 'S2'),
    ...         ('z2', 'b1')]),
    ...     ('color', 'S2'),
    ...     ('info', [
    ...         ('Name', 'U8'),
    ...         ('Value', 'c16')]),
    ...     ('y', 'f8', (2, 2)),
    ...     ('z', 'u1')]
    >>>
    >>>
    >>> NbufferT = [
    ...     ([3,2], (6j, 6., ('nn', [6j,4j], [6.,4.], [1,2]), 'NN', True), 'cc', ('NN', 6j), [[6.,4.],[6.,4.]], 8),
    ...     ([4,3], (7j, 7., ('oo', [7j,5j], [7.,5.], [2,1]), 'OO', False), 'dd', ('OO', 7j), [[7.,5.],[7.,5.]], 9),
    ...     ]
    >>>
    >>>
    >>> record_arrays = [
    ...     np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('<')),
    ...     np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('<')),
    ...     np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('>')),
    ...     np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('>')),
    ... ]

Test the magic string writing.

    >>> format.magic(1, 0)
    '\x93NUMPY\x01\x00'
    >>> format.magic(0, 0)
    '\x93NUMPY\x00\x00'
    >>> format.magic(255, 255)
    '\x93NUMPY\xff\xff'
    >>> format.magic(2, 5)
    '\x93NUMPY\x02\x05'

Test the magic string reading.

    >>> format.read_magic(BytesIO(format.magic(1, 0)))
    (1, 0)
    >>> format.read_magic(BytesIO(format.magic(0, 0)))
    (0, 0)
    >>> format.read_magic(BytesIO(format.magic(255, 255)))
    (255, 255)
    >>> format.read_magic(BytesIO(format.magic(2, 5)))
    (2, 5)

Test the header writing.

    >>> for arr in basic_arrays + record_arrays:
    ...     f = BytesIO()
    ...     format.write_array_header_1_0(f, arr)   # XXX: arr is not a dict, items gets called on it
    ...     print(repr(f.getvalue()))
    ...
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<f4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>f4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<f8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>f8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<c8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>c8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (0,)}             \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': ()}               \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (15,)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (3, 5)}           \n"
    "F\x00{'descr': '<c16', 'fortran_order': True, 'shape': (5, 3)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (3, 3)}           \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (0,)}             \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': ()}               \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (15,)}            \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (3, 5)}           \n"
    "F\x00{'descr': '>c16', 'fortran_order': True, 'shape': (5, 3)}            \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (3, 3)}           \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "v\x00{'descr': [('x', '<i4', (2,)), ('y', '<f8', (2, 2)), ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}         \n"
    "\x16\x02{'descr': [('x', '<i4', (2,)),\n           ('Info',\n            [('value', '<c16'),\n             ('y2', '<f8'),\n             ('Info2',\n              [('name', '|S2'),\n               ('value', '<c16', (2,)),\n               ('y3', '<f8', (2,)),\n               ('z3', '<u4', (2,))]),\n             ('name', '|S2'),\n             ('z2', '|b1')]),\n           ('color', '|S2'),\n           ('info', [('Name', '<U8'), ('Value', '<c16')]),\n           ('y', '<f8', (2, 2)),\n           ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}      \n"
    "v\x00{'descr': [('x', '>i4', (2,)), ('y', '>f8', (2, 2)), ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}         \n"
    "\x16\x02{'descr': [('x', '>i4', (2,)),\n           ('Info',\n            [('value', '>c16'),\n             ('y2', '>f8'),\n             ('Info2',\n              [('name', '|S2'),\n               ('value', '>c16', (2,)),\n               ('y3', '>f8', (2,)),\n               ('z3', '>u4', (2,))]),\n             ('name', '|S2'),\n             ('z2', '|b1')]),\n           ('color', '|S2'),\n           ('info', [('Name', '>U8'), ('Value', '>c16')]),\n           ('y', '>f8', (2, 2)),\n           ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}      \n"
'''
import os
import sys
import warnings
from io import BytesIO

import pytest

import numpy as np
from numpy.lib import format
from numpy.testing import (
    IS_64BIT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_array_equal,
    assert_raises,
    assert_raises_regex,
    assert_warns,
)
from numpy.testing._private.utils import requires_memory

# Generate some basic arrays to test with.
scalars = [
    np.uint8,
    np.int8,
    np.uint16,
    np.int16,
    np.uint32,
    np.int32,
    np.uint64,
    np.int64,
    np.float32,
    np.float64,
    np.complex64,
    np.complex128,
    object,
]
basic_arrays = []
for scalar in scalars:
    for endian in '<>':
        dtype = np.dtype(scalar).newbyteorder(endian)
        basic = np.arange(1500).astype(dtype)
        basic_arrays.extend([
            # Empty
            np.array([], dtype=dtype),
            # Rank-0
            np.array(10, dtype=dtype),
            # 1-D
            basic,
            # 2-D C-contiguous
            basic.reshape((30, 50)),
            # 2-D F-contiguous
            basic.reshape((30, 50)).T,
            # 2-D non-contiguous
            basic.reshape((30, 50))[::-1, ::2],
        ])

# More complicated record arrays.
# This is the structure of the table used for plain objects:
#
# +-+-+-+
# |x|y|z|
# +-+-+-+

# Structure of a plain array description:
Pdescr = [
    ('x', 'i4', (2,)),
    ('y', 'f8', (2, 2)),
    ('z', 'u1')]

# A plain list of tuples with values for testing:
PbufferT = [
    # x     y                  z
    ([3, 2], [[6., 4.], [6., 4.]], 8),
    ([4, 3], [[7., 5.], [7., 5.]], 9),
    ]


# This is the structure of the table used for nested objects (DON'T PANIC!):
#
# +-+---------------------------------+-----+----------+-+-+
# |x|Info                             |color|info      |y|z|
# | +-----+--+----------------+----+--+     +----+-----+ | |
# | |value|y2|Info2           |name|z2|     |Name|Value| | |
# | |     |  +----+-----+--+--+    |  |     |    |     | | |
# | |     |  |name|value|y3|z3|    |  |     |    |     | | |
# +-+-----+--+----+-----+--+--+----+--+-----+----+-----+-+-+
#

# The corresponding nested array description:
Ndescr = [
    ('x', 'i4', (2,)),
    ('Info', [
        ('value', 'c16'),
        ('y2', 'f8'),
        ('Info2', [
            ('name', 'S2'),
            ('value', 'c16', (2,)),
            ('y3', 'f8', (2,)),
            ('z3', 'u4', (2,))]),
        ('name', 'S2'),
        ('z2', 'b1')]),
    ('color', 'S2'),
    ('info', [
        ('Name', 'U8'),
        ('Value', 'c16')]),
    ('y', 'f8', (2, 2)),
    ('z', 'u1')]

NbufferT = [
    # x     Info                                                color info        y                  z
    #       value y2 Info2                            name z2         Name Value
    #                name   value    y3       z3
    ([3, 2], (6j, 6., ('nn', [6j, 4j], [6., 4.], [1, 2]), 'NN', True),
     'cc', ('NN', 6j), [[6., 4.], [6., 4.]], 8),
    ([4, 3], (7j, 7., ('oo', [7j, 5j], [7., 5.], [2, 1]), 'OO', False),
     'dd', ('OO', 7j), [[7., 5.], [7., 5.]], 9),
    ]

record_arrays = [
    np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('<')),
    np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('<')),
    np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('>')),
    np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('>')),
    np.zeros(1, dtype=[('c', ('<f8', (5,)), (2,))])
]


# BytesIO that reads a random number of bytes at a time
class BytesIOSRandomSize(BytesIO):
    def read(self, size=None):
        import random
        size = random.randint(1, size)
        return super().read(size)


def roundtrip(arr):
    f = BytesIO()
    format.write_array(f, arr)
    f2 = BytesIO(f.getvalue())
    arr2 = format.read_array(f2, allow_pickle=True)
    return arr2


def roundtrip_randsize(arr):
    f = BytesIO()
    format.write_array(f, arr)
    f2 = BytesIOSRandomSize(f.getvalue())
    arr2 = format.read_array(f2)
    return arr2


def roundtrip_truncated(arr):
    f = BytesIO()
    format.write_array(f, arr)
    # BytesIO is one byte short
    f2 = BytesIO(f.getvalue()[0:-1])
    arr2 = format.read_array(f2)
    return arr2

def assert_equal_(o1, o2):
    assert_(o1 == o2)


def test_roundtrip():
    for arr in basic_arrays + record_arrays:
        arr2 = roundtrip(arr)
        assert_array_equal(arr, arr2)


def test_roundtrip_randsize():
    for arr in basic_arrays + record_arrays:
        if arr.dtype != object:
            arr2 = roundtrip_randsize(arr)
            assert_array_equal(arr, arr2)


def test_roundtrip_truncated():
    for arr in basic_arrays:
        if arr.dtype != object:
            assert_raises(ValueError, roundtrip_truncated, arr)

def test_file_truncated(tmp_path):
    path = tmp_path / "a.npy"
    for arr in basic_arrays:
        if arr.dtype != object:
            with open(path, 'wb') as f:
                format.write_array(f, arr)
            # truncate the file by one byte
            with open(path, 'rb+') as f:
                f.seek(-1, os.SEEK_END)
                f.truncate()
            with open(path, 'rb') as f:
                with pytest.raises(
                    ValueError,
                    match=(
                        r"EOF: reading array header, "
                        r"expected (\d+) bytes got (\d+)"
                    ) if arr.size == 0 else (
                        r"Failed to read all data for array\. "
                        r"Expected \(.*?\) = (\d+) elements, "
                        r"could only read (\d+) elements\. "
                        r"\(file seems not fully written\?\)"
                    )
                ):
                    _ = format.read_array(f)

def test_long_str():
    # check items larger than internal buffer size, gh-4027
    long_str_arr = np.ones(1, dtype=np.dtype((str, format.BUFFER_SIZE + 1)))
    long_str_arr2 = roundtrip(long_str_arr)
    assert_array_equal(long_str_arr, long_str_arr2)


@pytest.mark.skipif(IS_WASM, reason="memmap doesn't work correctly")
@pytest.mark.slow
def test_memmap_roundtrip(tmpdir):
    for i, arr in enumerate(basic_arrays + record_arrays):
        if arr.dtype.hasobject:
            # Skip these since they can't be mmap'ed.
            continue
        # Write it out normally and through mmap.
        nfn = os.path.join(tmpdir, f'normal{i}.npy')
        mfn = os.path.join(tmpdir, f'memmap{i}.npy')
        with open(nfn, 'wb') as fp:
            format.write_array(fp, arr)

        fortran_order = (
            arr.flags.f_contiguous and not arr.flags.c_contiguous)
        ma = format.open_memmap(mfn, mode='w+', dtype=arr.dtype,
                                shape=arr.shape, fortran_order=fortran_order)
        ma[...] = arr
        ma.flush()

        # Check that both of these files' contents are the same.
        with open(nfn, 'rb') as fp:
            normal_bytes = fp.read()
        with open(mfn, 'rb') as fp:
            memmap_bytes = fp.read()
        assert_equal_(normal_bytes, memmap_bytes)

        # Check that reading the file using memmap works.
        ma = format.open_memmap(nfn, mode='r')
        ma.flush()


def test_compressed_roundtrip(tmpdir):
    arr = np.random.rand(200, 200)
    npz_file = os.path.join(tmpdir, 'compressed.npz')
    np.savez_compressed(npz_file, arr=arr)
    with np.load(npz_file) as npz:
        arr1 = npz['arr']
    assert_array_equal(arr, arr1)


# aligned
dt1 = np.dtype('i1, i4, i1', align=True)
# non-aligned, explicit offsets
dt2 = np.dtype({'names': ['a', 'b'], 'formats': ['i4', 'i4'],
                'offsets': [1, 6]})
# nested struct-in-struct
dt3 = np.dtype({'names': ['c', 'd'], 'formats': ['i4', dt2]})
# field with '' name
dt4 = np.dtype({'names': ['a', '', 'b'], 'formats': ['i4'] * 3})
# titles
dt5 = np.dtype({'names': ['a', 'b'], 'formats': ['i4', 'i4'],
                'offsets': [1, 6], 'titles': ['aa', 'bb']})
# empty
dt6 = np.dtype({'names': [], 'formats': [], 'itemsize': 8})

@pytest.mark.parametrize("dt", [dt1, dt2, dt3, dt4, dt5, dt6])
def test_load_padded_dtype(tmpdir, dt):
    arr = np.zeros(3, dt)
    for i in range(3):
        arr[i] = i + 5
    npz_file = os.path.join(tmpdir, 'aligned.npz')
    np.savez(npz_file, arr=arr)
    with np.load(npz_file) as npz:
        arr1 = npz['arr']
    assert_array_equal(arr, arr1)


@pytest.mark.skipif(sys.version_info >= (3, 12), reason="see gh-23988")
@pytest.mark.xfail(IS_WASM, reason="Emscripten NODEFS has a buggy dup")
def test_python2_python3_interoperability():
    fname = 'win64python2.npy'
    path = os.path.join(os.path.dirname(__file__), 'data', fname)
    with pytest.warns(UserWarning, match="Reading.*this warning\\."):
        data = np.load(path)
    assert_array_equal(data, np.ones(2))


def test_pickle_python2_python3():
    # Test that loading object arrays saved on Python 2 works both on
    # Python 2 and Python 3 and vice versa
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    expected = np.array([None, range, '\u512a\u826f',
                         b'\xe4\xb8\x8d\xe8\x89\xaf'],
                        dtype=object)

    for fname in ['py2-np0-objarr.npy', 'py2-objarr.npy', 'py2-objarr.npz',
                  'py3-objarr.npy', 'py3-objarr.npz']:
        path = os.path.join(data_dir, fname)

        for encoding in ['bytes', 'latin1']:
            data_f = np.load(path, allow_pickle=True, encoding=encoding)
            if fname.endswith('.npz'):
                data = data_f['x']
                data_f.close()
            else:
                data = data_f

            if encoding == 'latin1' and fname.startswith('py2'):
                assert_(isinstance(data[3], str))
                assert_array_equal(data[:-1], expected[:-1])
                # mojibake occurs
                assert_array_equal(data[-1].encode(encoding), expected[-1])
            else:
                assert_(isinstance(data[3], bytes))
                assert_array_equal(data, expected)

        if fname.startswith('py2'):
            if fname.endswith('.npz'):
                data = np.load(path, allow_pickle=True)
                assert_raises(UnicodeError, data.__getitem__, 'x')
                data.close()
                data = np.load(path, allow_pickle=True, fix_imports=False,
                               encoding='latin1')
                assert_raises(ImportError, data.__getitem__, 'x')
                data.close()
            else:
                assert_raises(UnicodeError, np.load, path,
                              allow_pickle=True)
                assert_raises(ImportError, np.load, path,
                              allow_pickle=True, fix_imports=False,
                              encoding='latin1')


def test_pickle_disallow(tmpdir):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    path = os.path.join(data_dir, 'py2-objarr.npy')
    assert_raises(ValueError, np.load, path,
                  allow_pickle=False, encoding='latin1')

    path = os.path.join(data_dir, 'py2-objarr.npz')
    with np.load(path, allow_pickle=False, encoding='latin1') as f:
        assert_raises(ValueError, f.__getitem__, 'x')

    path = os.path.join(tmpdir, 'pickle-disabled.npy')
    assert_raises(ValueError, np.save, path, np.array([None], dtype=object),
                  allow_pickle=False)

@pytest.mark.parametrize('dt', [
    np.dtype(np.dtype([('a', np.int8),
                       ('b', np.int16),
                       ('c', np.int32),
                      ], align=True),
             (3,)),
    np.dtype([('x', np.dtype({'names': ['a', 'b'],
                              'formats': ['i1', 'i1'],
                              'offsets': [0, 4],
                              'itemsize': 8,
                             },
                    (3,)),
               (4,),
             )]),
    np.dtype([('x',
                   ('<f8', (5,)),
                   (2,),
               )]),
    np.dtype([('x', np.dtype((
        np.dtype((
            np.dtype({'names': ['a', 'b'],
                      'formats': ['i1', 'i1'],
                      'offsets': [0, 4],
                      'itemsize': 8}),
            (3,)
            )),
        (4,)
        )))
        ]),
    np.dtype([
        ('a', np.dtype((
            np.dtype((
                np.dtype((
                    np.dtype([
                        ('a', int),
                        ('b', np.dtype({'names': ['a', 'b'],
                                        'formats': ['i1', 'i1'],
                                        'offsets': [0, 4],
                                        'itemsize': 8})),
                    ]),
                    (3,),
                )),
                (4,),
            )),
            (5,),
        )))
        ]),
    ])
def test_descr_to_dtype(dt):
    dt1 = format.descr_to_dtype(dt.descr)
    assert_equal_(dt1, dt)
    arr1 = np.zeros(3, dt)
    arr2 = roundtrip(arr1)
    assert_array_equal(arr1, arr2)

def test_version_2_0():
    f = BytesIO()
    # requires more than 2 byte for header
    dt = [(("%d" % i) * 100, float) for i in range(500)]
    d = np.ones(1000, dtype=dt)

    format.write_array(f, d, version=(2, 0))
    with warnings.catch_warnings(record=True) as w:
        warnings.filterwarnings('always', '', UserWarning)
        format.write_array(f, d)
        assert_(w[0].category is UserWarning)

    # check alignment of data portion
    f.seek(0)
    header = f.readline()
    assert_(len(header) % format.ARRAY_ALIGN == 0)

    f.seek(0)
    n = format.read_array(f, max_header_size=200000)
    assert_array_equal(d, n)

    # 1.0 requested but data cannot be saved this way
    assert_raises(ValueError, format.write_array, f, d, (1, 0))


@pytest.mark.skipif(IS_WASM, reason="memmap doesn't work correctly")
def test_version_2_0_memmap(tmpdir):
    # requires more than 2 byte for header
    dt = [(("%d" % i) * 100, float) for i in range(500)]
    d = np.ones(1000, dtype=dt)
    tf1 = os.path.join(tmpdir, 'version2_01.npy')
    tf2 = os.path.join(tmpdir, 'version2_02.npy')

    # 1.0 requested but data cannot be saved this way
    assert_raises(ValueError, format.open_memmap, tf1, mode='w+', dtype=d.dtype,
                            shape=d.shape, version=(1, 0))

    ma = format.open_memmap(tf1, mode='w+', dtype=d.dtype,
                            shape=d.shape, version=(2, 0))
    ma[...] = d
    ma.flush()
    ma = format.open_memmap(tf1, mode='r', max_header_size=200000)
    assert_array_equal(ma, d)

    with warnings.catch_warnings(record=True) as w:
        warnings.filterwarnings('always', '', UserWarning)
        ma = format.open_memmap(tf2, mode='w+', dtype=d.dtype,
                                shape=d.shape, version=None)
        assert_(w[0].category is UserWarning)
        ma[...] = d
        ma.flush()

    ma = format.open_memmap(tf2, mode='r', max_header_size=200000)

    assert_array_equal(ma, d)

@pytest.mark.parametrize("mmap_mode", ["r", None])
def test_huge_header(tmpdir, mmap_mode):
    f = os.path.join(tmpdir, 'large_header.npy')
    arr = np.array(1, dtype="i," * 10000 + "i")

    with pytest.warns(UserWarning, match=".*format 2.0"):
        np.save(f, arr)

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, mmap_mode=mmap_mode)

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, mmap_mode=mmap_mode, max_header_size=20000)

    res = np.load(f, mmap_mode=mmap_mode, allow_pickle=True)
    assert_array_equal(res, arr)

    res = np.load(f, mmap_mode=mmap_mode, max_header_size=180000)
    assert_array_equal(res, arr)

def test_huge_header_npz(tmpdir):
    f = os.path.join(tmpdir, 'large_header.npz')
    arr = np.array(1, dtype="i," * 10000 + "i")

    with pytest.warns(UserWarning, match=".*format 2.0"):
        np.savez(f, arr=arr)

    # Only getting the array from the file actually reads it
    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f)["arr"]

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, max_header_size=20000)["arr"]

    res = np.load(f, allow_pickle=True)["arr"]
    assert_array_equal(res, arr)

    res = np.load(f, max_header_size=180000)["arr"]
    assert_array_equal(res, arr)

def test_write_version():
    f = BytesIO()
    arr = np.arange(1)
    # These should pass.
    format.write_array(f, arr, version=(1, 0))
    format.write_array(f, arr)

    format.write_array(f, arr, version=None)
    format.write_array(f, arr)

    format.write_array(f, arr, version=(2, 0))
    format.write_array(f, arr)

    # These should all fail.
    bad_versions = [
        (1, 1),
        (0, 0),
        (0, 1),
        (2, 2),
        (255, 255),
    ]
    for version in bad_versions:
        with assert_raises_regex(ValueError,
                                 'we only support format version.*'):
            format.write_array(f, arr, version=version)


bad_version_magic = [
    b'\x93NUMPY\x01\x01',
    b'\x93NUMPY\x00\x00',
    b'\x93NUMPY\x00\x01',
    b'\x93NUMPY\x02\x00',
    b'\x93NUMPY\x02\x02',
    b'\x93NUMPY\xff\xff',
]
malformed_magic = [
    b'\x92NUMPY\x01\x00',
    b'\x00NUMPY\x01\x00',
    b'\x93numpy\x01\x00',
    b'\x93MATLB\x01\x00',
    b'\x93NUMPY\x01',
    b'\x93NUMPY',
    b'',
]

def test_read_magic():
    s1 = BytesIO()
    s2 = BytesIO()

    arr = np.ones((3, 6), dtype=float)

    format.write_array(s1, arr, version=(1, 0))
    format.write_array(s2, arr, version=(2, 0))

    s1.seek(0)
    s2.seek(0)

    version1 = format.read_magic(s1)
    version2 = format.read_magic(s2)

    assert_(version1 == (1, 0))
    assert_(version2 == (2, 0))

    assert_(s1.tell() == format.MAGIC_LEN)
    assert_(s2.tell() == format.MAGIC_LEN)

def test_read_magic_bad_magic():
    for magic in malformed_magic:
        f = BytesIO(magic)
        assert_raises(ValueError, format.read_array, f)


def test_read_version_1_0_bad_magic():
    for magic in bad_version_magic + malformed_magic:
        f = BytesIO(magic)
        assert_raises(ValueError, format.read_array, f)


def test_bad_magic_args():
    assert_raises(ValueError, format.magic, -1, 1)
    assert_raises(ValueError, format.magic, 256, 1)
    assert_raises(ValueError, format.magic, 1, -1)
    assert_raises(ValueError, format.magic, 1, 256)


def test_large_header():
    s = BytesIO()
    d = {'shape': (), 'fortran_order': False, 'descr': '<i8'}
    format.write_array_header_1_0(s, d)

    s = BytesIO()
    d['descr'] = [('x' * 256 * 256, '<i8')]
    assert_raises(ValueError, format.write_array_header_1_0, s, d)


def test_read_array_header_1_0():
    s = BytesIO()

    arr = np.ones((3, 6), dtype=float)
    format.write_array(s, arr, version=(1, 0))

    s.seek(format.MAGIC_LEN)
    shape, fortran, dtype = format.read_array_header_1_0(s)

    assert_(s.tell() % format.ARRAY_ALIGN == 0)
    assert_((shape, fortran, dtype) == ((3, 6), False, float))


def test_read_array_header_2_0():
    s = BytesIO()

    arr = np.ones((3, 6), dtype=float)
    format.write_array(s, arr, version=(2, 0))

    s.seek(format.MAGIC_LEN)
    shape, fortran, dtype = format.read_array_header_2_0(s)

    assert_(s.tell() % format.ARRAY_ALIGN == 0)
    assert_((shape, fortran, dtype) == ((3, 6), False, float))


def test_bad_header():
    # header of length less than 2 should fail
    s = BytesIO()
    assert_raises(ValueError, format.read_array_header_1_0, s)
    s = BytesIO(b'1')
    assert_raises(ValueError, format.read_array_header_1_0, s)

    # header shorter than indicated size should fail
    s = BytesIO(b'\x01\x00')
    assert_raises(ValueError, format.read_array_header_1_0, s)

    # headers without the exact keys required should fail
    # d = {"shape": (1, 2),
    #      "descr": "x"}
    s = BytesIO(
        b"\x93NUMPY\x01\x006\x00{'descr': 'x', 'shape': (1, 2), }"
        b"                    \n"
    )
    assert_raises(ValueError, format.read_array_header_1_0, s)

    d = {"shape": (1, 2),
         "fortran_order": False,
         "descr": "x",
         "extrakey": -1}
    s = BytesIO()
    format.write_array_header_1_0(s, d)
    assert_raises(ValueError, format.read_array_header_1_0, s)


def test_large_file_support(tmpdir):
    if (sys.platform == 'win32' or sys.platform == 'cygwin'):
        pytest.skip("Unknown if Windows has sparse filesystems")
    # try creating a large sparse file
    tf_name = os.path.join(tmpdir, 'sparse_file')
    try:
        # seek past end would work too, but linux truncate somewhat
        # increases the chances that we have a sparse filesystem and can
        # avoid actually writing 5GB
        import subprocess as sp
        sp.check_call(["truncate", "-s", "5368709120", tf_name])
    except Exception:
        pytest.skip("Could not create 5GB large file")
    # write a small array to the end
    with open(tf_name, "wb") as f:
        f.seek(5368709120)
        d = np.arange(5)
        np.save(f, d)
    # read it back
    with open(tf_name, "rb") as f:
        f.seek(5368709120)
        r = np.load(f)
    assert_array_equal(r, d)


@pytest.mark.skipif(IS_PYPY, reason="flaky on PyPy")
@pytest.mark.skipif(not IS_64BIT, reason="test requires 64-bit system")
@pytest.mark.slow
@requires_memory(free_bytes=2 * 2**30)
def test_large_archive(tmpdir):
    # Regression test for product of saving arrays with dimensions of array
    # having a product that doesn't fit in int32.  See gh-7598 for details.
    shape = (2**30, 2)
    try:
        a = np.empty(shape, dtype=np.uint8)
    except MemoryError:
        pytest.skip("Could not create large file")

    fname = os.path.join(tmpdir, "large_archive")

    with open(fname, "wb") as f:
        np.savez(f, arr=a)

    del a

    with open(fname, "rb") as f:
        new_a = np.load(f)["arr"]

    assert new_a.shape == shape


def test_empty_npz(tmpdir):
    # Test for gh-9989
    fname = os.path.join(tmpdir, "nothing.npz")
    np.savez(fname)
    with np.load(fname) as nps:
        pass


def test_unicode_field_names(tmpdir):
    # gh-7391
    arr = np.array([
        (1, 3),
        (1, 2),
        (1, 3),
        (1, 2)
    ], dtype=[
        ('int', int),
        ('\N{CJK UNIFIED IDEOGRAPH-6574}\N{CJK UNIFIED IDEOGRAPH-5F62}', int)
    ])
    fname = os.path.join(tmpdir, "unicode.npy")
    with open(fname, 'wb') as f:
        format.write_array(f, arr, version=(3, 0))
    with open(fname, 'rb') as f:
        arr2 = format.read_array(f)
    assert_array_equal(arr, arr2)

    # notifies the user that 3.0 is selected
    with open(fname, 'wb') as f:
        with assert_warns(UserWarning):
            format.write_array(f, arr, version=None)

def test_header_growth_axis():
    for is_fortran_array, dtype_space, expected_header_length in [
        [False, 22, 128], [False, 23, 192], [True, 23, 128], [True, 24, 192]
    ]:
        for size in [10**i for i in range(format.GROWTH_AXIS_MAX_DIGITS)]:
            fp = BytesIO()
            format.write_array_header_1_0(fp, {
                'shape': (2, size) if is_fortran_array else (size, 2),
                'fortran_order': is_fortran_array,
                'descr': np.dtype([(' ' * dtype_space, int)])
            })

            assert len(fp.getvalue()) == expected_header_length

@pytest.mark.parametrize('dt', [
    np.dtype({'names': ['a', 'b'], 'formats':  [float, np.dtype('S3',
                 metadata={'some': 'stuff'})]}),
    np.dtype(int, metadata={'some': 'stuff'}),
    np.dtype([('subarray', (int, (2,)))], metadata={'some': 'stuff'}),
    # recursive: metadata on the field of a dtype
    np.dtype({'names': ['a', 'b'], 'formats': [
        float, np.dtype({'names': ['c'], 'formats': [np.dtype(int, metadata={})]})
    ]}),
    ])
@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
        reason="PyPy bug in error formatting")
def test_metadata_dtype(dt):
    # gh-14142
    arr = np.ones(10, dtype=dt)
    buf = BytesIO()
    with assert_warns(UserWarning):
        np.save(buf, arr)
    buf.seek(0)

    # Loading should work (metadata was stripped):
    arr2 = np.load(buf)
    # BUG: assert_array_equal does not check metadata
    from numpy.lib._utils_impl import drop_metadata
    assert_array_equal(arr, arr2)
    assert drop_metadata(arr.dtype) is not arr.dtype
    assert drop_metadata(arr2.dtype) is arr2.dtype

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_recfunctions.py ===

import numpy as np
import numpy.ma as ma
from numpy.lib.recfunctions import (
    append_fields,
    apply_along_fields,
    assign_fields_by_name,
    drop_fields,
    find_duplicates,
    get_fieldstructure,
    join_by,
    merge_arrays,
    recursive_fill_fields,
    rename_fields,
    repack_fields,
    require_fields,
    stack_arrays,
    structured_to_unstructured,
    unstructured_to_structured,
)
from numpy.ma.mrecords import MaskedRecords
from numpy.ma.testutils import assert_equal
from numpy.testing import assert_, assert_raises

get_fieldspec = np.lib.recfunctions._get_fieldspec
get_names = np.lib.recfunctions.get_names
get_names_flat = np.lib.recfunctions.get_names_flat
zip_descr = np.lib.recfunctions._zip_descr
zip_dtype = np.lib.recfunctions._zip_dtype


class TestRecFunctions:
    # Misc tests

    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array([('A', 1.), ('B', 2.)],
                     dtype=[('A', '|S3'), ('B', float)])
        w = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])
        self.data = (w, x, y, z)

    def test_zip_descr(self):
        # Test zip_descr
        (w, x, y, z) = self.data

        # Std array
        test = zip_descr((x, x), flatten=True)
        assert_equal(test,
                     np.dtype([('', int), ('', int)]))
        test = zip_descr((x, x), flatten=False)
        assert_equal(test,
                     np.dtype([('', int), ('', int)]))

        # Std & flexible-dtype
        test = zip_descr((x, z), flatten=True)
        assert_equal(test,
                     np.dtype([('', int), ('A', '|S3'), ('B', float)]))
        test = zip_descr((x, z), flatten=False)
        assert_equal(test,
                     np.dtype([('', int),
                               ('', [('A', '|S3'), ('B', float)])]))

        # Standard & nested dtype
        test = zip_descr((x, w), flatten=True)
        assert_equal(test,
                     np.dtype([('', int),
                               ('a', int),
                               ('ba', float), ('bb', int)]))
        test = zip_descr((x, w), flatten=False)
        assert_equal(test,
                     np.dtype([('', int),
                               ('', [('a', int),
                                     ('b', [('ba', float), ('bb', int)])])]))

    def test_drop_fields(self):
        # Test drop_fields
        a = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])

        # A basic field
        test = drop_fields(a, 'a')
        control = np.array([((2, 3.0),), ((5, 6.0),)],
                           dtype=[('b', [('ba', float), ('bb', int)])])
        assert_equal(test, control)

        # Another basic field (but nesting two fields)
        test = drop_fields(a, 'b')
        control = np.array([(1,), (4,)], dtype=[('a', int)])
        assert_equal(test, control)

        # A nested sub-field
        test = drop_fields(a, ['ba', ])
        control = np.array([(1, (3.0,)), (4, (6.0,))],
                           dtype=[('a', int), ('b', [('bb', int)])])
        assert_equal(test, control)

        # All the nested sub-field from a field: zap that field
        test = drop_fields(a, ['ba', 'bb'])
        control = np.array([(1,), (4,)], dtype=[('a', int)])
        assert_equal(test, control)

        # dropping all fields results in an array with no fields
        test = drop_fields(a, ['a', 'b'])
        control = np.array([(), ()], dtype=[])
        assert_equal(test, control)

    def test_rename_fields(self):
        # Test rename fields
        a = np.array([(1, (2, [3.0, 30.])), (4, (5, [6.0, 60.]))],
                     dtype=[('a', int),
                            ('b', [('ba', float), ('bb', (float, 2))])])
        test = rename_fields(a, {'a': 'A', 'bb': 'BB'})
        newdtype = [('A', int), ('b', [('ba', float), ('BB', (float, 2))])]
        control = a.view(newdtype)
        assert_equal(test.dtype, newdtype)
        assert_equal(test, control)

    def test_get_names(self):
        # Test get_names
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        test = get_names(ndtype)
        assert_equal(test, ('A', 'B'))

        ndtype = np.dtype([('a', int), ('b', [('ba', float), ('bb', int)])])
        test = get_names(ndtype)
        assert_equal(test, ('a', ('b', ('ba', 'bb'))))

        ndtype = np.dtype([('a', int), ('b', [])])
        test = get_names(ndtype)
        assert_equal(test, ('a', ('b', ())))

        ndtype = np.dtype([])
        test = get_names(ndtype)
        assert_equal(test, ())

    def test_get_names_flat(self):
        # Test get_names_flat
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        test = get_names_flat(ndtype)
        assert_equal(test, ('A', 'B'))

        ndtype = np.dtype([('a', int), ('b', [('ba', float), ('bb', int)])])
        test = get_names_flat(ndtype)
        assert_equal(test, ('a', 'b', 'ba', 'bb'))

        ndtype = np.dtype([('a', int), ('b', [])])
        test = get_names_flat(ndtype)
        assert_equal(test, ('a', 'b'))

        ndtype = np.dtype([])
        test = get_names_flat(ndtype)
        assert_equal(test, ())

    def test_get_fieldstructure(self):
        # Test get_fieldstructure

        # No nested fields
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        test = get_fieldstructure(ndtype)
        assert_equal(test, {'A': [], 'B': []})

        # One 1-nested field
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        test = get_fieldstructure(ndtype)
        assert_equal(test, {'A': [], 'B': [], 'BA': ['B', ], 'BB': ['B']})

        # One 2-nested fields
        ndtype = np.dtype([('A', int),
                           ('B', [('BA', int),
                                  ('BB', [('BBA', int), ('BBB', int)])])])
        test = get_fieldstructure(ndtype)
        control = {'A': [], 'B': [], 'BA': ['B'], 'BB': ['B'],
                   'BBA': ['B', 'BB'], 'BBB': ['B', 'BB']}
        assert_equal(test, control)

        # 0 fields
        ndtype = np.dtype([])
        test = get_fieldstructure(ndtype)
        assert_equal(test, {})

    def test_find_duplicates(self):
        # Test find_duplicates
        a = ma.array([(2, (2., 'B')), (1, (2., 'B')), (2, (2., 'B')),
                      (1, (1., 'B')), (2, (2., 'B')), (2, (2., 'C'))],
                     mask=[(0, (0, 0)), (0, (0, 0)), (0, (0, 0)),
                           (0, (0, 0)), (1, (0, 0)), (0, (1, 0))],
                     dtype=[('A', int), ('B', [('BA', float), ('BB', '|S1')])])

        test = find_duplicates(a, ignoremask=False, return_index=True)
        control = [0, 2]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='A', return_index=True)
        control = [0, 1, 2, 3, 5]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='B', return_index=True)
        control = [0, 1, 2, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='BA', return_index=True)
        control = [0, 1, 2, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='BB', return_index=True)
        control = [0, 1, 2, 3, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

    def test_find_duplicates_ignoremask(self):
        # Test the ignoremask option of find_duplicates
        ndtype = [('a', int)]
        a = ma.array([1, 1, 1, 2, 2, 3, 3],
                     mask=[0, 0, 1, 0, 0, 0, 1]).view(ndtype)
        test = find_duplicates(a, ignoremask=True, return_index=True)
        control = [0, 1, 3, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, ignoremask=False, return_index=True)
        control = [0, 1, 2, 3, 4, 6]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

    def test_repack_fields(self):
        dt = np.dtype('u1,f4,i8', align=True)
        a = np.zeros(2, dtype=dt)

        assert_equal(repack_fields(dt), np.dtype('u1,f4,i8'))
        assert_equal(repack_fields(a).itemsize, 13)
        assert_equal(repack_fields(repack_fields(dt), align=True), dt)

        # make sure type is preserved
        dt = np.dtype((np.record, dt))
        assert_(repack_fields(dt).type is np.record)

    def test_structured_to_unstructured(self, tmp_path):
        a = np.zeros(4, dtype=[('a', 'i4'), ('b', 'f4,u2'), ('c', 'f4', 2)])
        out = structured_to_unstructured(a)
        assert_equal(out, np.zeros((4, 5), dtype='f8'))

        b = np.array([(1, 2, 5), (4, 5, 7), (7, 8, 11), (10, 11, 12)],
                     dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
        out = np.mean(structured_to_unstructured(b[['x', 'z']]), axis=-1)
        assert_equal(out, np.array([3.,  5.5,  9., 11.]))
        out = np.mean(structured_to_unstructured(b[['x']]), axis=-1)
        assert_equal(out, np.array([1.,  4. ,  7., 10.]))  # noqa: E203

        c = np.arange(20).reshape((4, 5))
        out = unstructured_to_structured(c, a.dtype)
        want = np.array([( 0, ( 1.,  2), [ 3.,  4.]),
                         ( 5, ( 6.,  7), [ 8.,  9.]),
                         (10, (11., 12), [13., 14.]),
                         (15, (16., 17), [18., 19.])],
                     dtype=[('a', 'i4'),
                            ('b', [('f0', 'f4'), ('f1', 'u2')]),
                            ('c', 'f4', (2,))])
        assert_equal(out, want)

        d = np.array([(1, 2, 5), (4, 5, 7), (7, 8, 11), (10, 11, 12)],
                     dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
        assert_equal(apply_along_fields(np.mean, d),
                     np.array([ 8.0 / 3,  16.0 / 3,  26.0 / 3, 11.]))
        assert_equal(apply_along_fields(np.mean, d[['x', 'z']]),
                     np.array([ 3.,  5.5,  9., 11.]))

        # check that for uniform field dtypes we get a view, not a copy:
        d = np.array([(1, 2, 5), (4, 5, 7), (7, 8, 11), (10, 11, 12)],
                     dtype=[('x', 'i4'), ('y', 'i4'), ('z', 'i4')])
        dd = structured_to_unstructured(d)
        ddd = unstructured_to_structured(dd, d.dtype)
        assert_(np.shares_memory(dd, d))
        assert_(np.shares_memory(ddd, d))

        # check that reversing the order of attributes works
        dd_attrib_rev = structured_to_unstructured(d[['z', 'x']])
        assert_equal(dd_attrib_rev, [[5, 1], [7, 4], [11, 7], [12, 10]])
        assert_(np.shares_memory(dd_attrib_rev, d))

        # including uniform fields with subarrays unpacked
        d = np.array([(1, [2,  3], [[ 4,  5], [ 6,  7]]),
                      (8, [9, 10], [[11, 12], [13, 14]])],
                     dtype=[('x0', 'i4'), ('x1', ('i4', 2)),
                            ('x2', ('i4', (2, 2)))])
        dd = structured_to_unstructured(d)
        ddd = unstructured_to_structured(dd, d.dtype)
        assert_(np.shares_memory(dd, d))
        assert_(np.shares_memory(ddd, d))

        # check that reversing with sub-arrays works as expected
        d_rev = d[::-1]
        dd_rev = structured_to_unstructured(d_rev)
        assert_equal(dd_rev, [[8, 9, 10, 11, 12, 13, 14],
                              [1, 2, 3, 4, 5, 6, 7]])

        # check that sub-arrays keep the order of their values
        d_attrib_rev = d[['x2', 'x1', 'x0']]
        dd_attrib_rev = structured_to_unstructured(d_attrib_rev)
        assert_equal(dd_attrib_rev, [[4, 5, 6, 7, 2, 3, 1],
                                     [11, 12, 13, 14, 9, 10, 8]])

        # with ignored field at the end
        d = np.array([(1, [2,  3], [[4, 5], [6, 7]], 32),
                      (8, [9, 10], [[11, 12], [13, 14]], 64)],
                     dtype=[('x0', 'i4'), ('x1', ('i4', 2)),
                            ('x2', ('i4', (2, 2))), ('ignored', 'u1')])
        dd = structured_to_unstructured(d[['x0', 'x1', 'x2']])
        assert_(np.shares_memory(dd, d))
        assert_equal(dd, [[1, 2, 3, 4, 5, 6, 7],
                          [8, 9, 10, 11, 12, 13, 14]])

        # test that nested fields with identical names don't break anything
        point = np.dtype([('x', int), ('y', int)])
        triangle = np.dtype([('a', point), ('b', point), ('c', point)])
        arr = np.zeros(10, triangle)
        res = structured_to_unstructured(arr, dtype=int)
        assert_equal(res, np.zeros((10, 6), dtype=int))

        # test nested combinations of subarrays and structured arrays, gh-13333
        def subarray(dt, shape):
            return np.dtype((dt, shape))

        def structured(*dts):
            return np.dtype([(f'x{i}', dt) for i, dt in enumerate(dts)])

        def inspect(dt, dtype=None):
            arr = np.zeros((), dt)
            ret = structured_to_unstructured(arr, dtype=dtype)
            backarr = unstructured_to_structured(ret, dt)
            return ret.shape, ret.dtype, backarr.dtype

        dt = structured(subarray(structured(np.int32, np.int32), 3))
        assert_equal(inspect(dt), ((6,), np.int32, dt))

        dt = structured(subarray(subarray(np.int32, 2), 2))
        assert_equal(inspect(dt), ((4,), np.int32, dt))

        dt = structured(np.int32)
        assert_equal(inspect(dt), ((1,), np.int32, dt))

        dt = structured(np.int32, subarray(subarray(np.int32, 2), 2))
        assert_equal(inspect(dt), ((5,), np.int32, dt))

        dt = structured()
        assert_raises(ValueError, structured_to_unstructured, np.zeros(3, dt))

        # these currently don't work, but we may make it work in the future
        assert_raises(NotImplementedError, structured_to_unstructured,
                                           np.zeros(3, dt), dtype=np.int32)
        assert_raises(NotImplementedError, unstructured_to_structured,
                                           np.zeros((3, 0), dtype=np.int32))

        # test supported ndarray subclasses
        d_plain = np.array([(1, 2), (3, 4)], dtype=[('a', 'i4'), ('b', 'i4')])
        dd_expected = structured_to_unstructured(d_plain, copy=True)

        # recarray
        d = d_plain.view(np.recarray)

        dd = structured_to_unstructured(d, copy=False)
        ddd = structured_to_unstructured(d, copy=True)
        assert_(np.shares_memory(d, dd))
        assert_(type(dd) is np.recarray)
        assert_(type(ddd) is np.recarray)
        assert_equal(dd, dd_expected)
        assert_equal(ddd, dd_expected)

        # memmap
        d = np.memmap(tmp_path / 'memmap',
                      mode='w+',
                      dtype=d_plain.dtype,
                      shape=d_plain.shape)
        d[:] = d_plain
        dd = structured_to_unstructured(d, copy=False)
        ddd = structured_to_unstructured(d, copy=True)
        assert_(np.shares_memory(d, dd))
        assert_(type(dd) is np.memmap)
        assert_(type(ddd) is np.memmap)
        assert_equal(dd, dd_expected)
        assert_equal(ddd, dd_expected)

    def test_unstructured_to_structured(self):
        # test if dtype is the args of np.dtype
        a = np.zeros((20, 2))
        test_dtype_args = [('x', float), ('y', float)]
        test_dtype = np.dtype(test_dtype_args)
        field1 = unstructured_to_structured(a, dtype=test_dtype_args)  # now
        field2 = unstructured_to_structured(a, dtype=test_dtype)  # before
        assert_equal(field1, field2)

    def test_field_assignment_by_name(self):
        a = np.ones(2, dtype=[('a', 'i4'), ('b', 'f8'), ('c', 'u1')])
        newdt = [('b', 'f4'), ('c', 'u1')]

        assert_equal(require_fields(a, newdt), np.ones(2, newdt))

        b = np.array([(1, 2), (3, 4)], dtype=newdt)
        assign_fields_by_name(a, b, zero_unassigned=False)
        assert_equal(a, np.array([(1, 1, 2), (1, 3, 4)], dtype=a.dtype))
        assign_fields_by_name(a, b)
        assert_equal(a, np.array([(0, 1, 2), (0, 3, 4)], dtype=a.dtype))

        # test nested fields
        a = np.ones(2, dtype=[('a', [('b', 'f8'), ('c', 'u1')])])
        newdt = [('a', [('c', 'u1')])]
        assert_equal(require_fields(a, newdt), np.ones(2, newdt))
        b = np.array([((2,),), ((3,),)], dtype=newdt)
        assign_fields_by_name(a, b, zero_unassigned=False)
        assert_equal(a, np.array([((1, 2),), ((1, 3),)], dtype=a.dtype))
        assign_fields_by_name(a, b)
        assert_equal(a, np.array([((0, 2),), ((0, 3),)], dtype=a.dtype))

        # test unstructured code path for 0d arrays
        a, b = np.array(3), np.array(0)
        assign_fields_by_name(b, a)
        assert_equal(b[()], 3)


class TestRecursiveFillFields:
    # Test recursive_fill_fields.
    def test_simple_flexible(self):
        # Test recursive_fill_fields on flexible-array
        a = np.array([(1, 10.), (2, 20.)], dtype=[('A', int), ('B', float)])
        b = np.zeros((3,), dtype=a.dtype)
        test = recursive_fill_fields(a, b)
        control = np.array([(1, 10.), (2, 20.), (0, 0.)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)

    def test_masked_flexible(self):
        # Test recursive_fill_fields on masked flexible-array
        a = ma.array([(1, 10.), (2, 20.)], mask=[(0, 1), (1, 0)],
                     dtype=[('A', int), ('B', float)])
        b = ma.zeros((3,), dtype=a.dtype)
        test = recursive_fill_fields(a, b)
        control = ma.array([(1, 10.), (2, 20.), (0, 0.)],
                           mask=[(0, 1), (1, 0), (0, 0)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)


class TestMergeArrays:
    # Test merge_arrays

    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array(
            [('A', 1.), ('B', 2.)], dtype=[('A', '|S3'), ('B', float)])
        w = np.array(
            [(1, (2, 3.0, ())), (4, (5, 6.0, ()))],
            dtype=[('a', int), ('b', [('ba', float), ('bb', int), ('bc', [])])])
        self.data = (w, x, y, z)

    def test_solo(self):
        # Test merge_arrays on a single array.
        (_, x, _, z) = self.data

        test = merge_arrays(x)
        control = np.array([(1,), (2,)], dtype=[('f0', int)])
        assert_equal(test, control)
        test = merge_arrays((x,))
        assert_equal(test, control)

        test = merge_arrays(z, flatten=False)
        assert_equal(test, z)
        test = merge_arrays(z, flatten=True)
        assert_equal(test, z)

    def test_solo_w_flatten(self):
        # Test merge_arrays on a single array w & w/o flattening
        w = self.data[0]
        test = merge_arrays(w, flatten=False)
        assert_equal(test, w)

        test = merge_arrays(w, flatten=True)
        control = np.array([(1, 2, 3.0), (4, 5, 6.0)],
                           dtype=[('a', int), ('ba', float), ('bb', int)])
        assert_equal(test, control)

    def test_standard(self):
        # Test standard & standard
        # Test merge arrays
        (_, x, y, _) = self.data
        test = merge_arrays((x, y), usemask=False)
        control = np.array([(1, 10), (2, 20), (-1, 30)],
                           dtype=[('f0', int), ('f1', int)])
        assert_equal(test, control)

        test = merge_arrays((x, y), usemask=True)
        control = ma.array([(1, 10), (2, 20), (-1, 30)],
                           mask=[(0, 0), (0, 0), (1, 0)],
                           dtype=[('f0', int), ('f1', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_flatten(self):
        # Test standard & flexible
        (_, x, _, z) = self.data
        test = merge_arrays((x, z), flatten=True)
        control = np.array([(1, 'A', 1.), (2, 'B', 2.)],
                           dtype=[('f0', int), ('A', '|S3'), ('B', float)])
        assert_equal(test, control)

        test = merge_arrays((x, z), flatten=False)
        control = np.array([(1, ('A', 1.)), (2, ('B', 2.))],
                           dtype=[('f0', int),
                                  ('f1', [('A', '|S3'), ('B', float)])])
        assert_equal(test, control)

    def test_flatten_wflexible(self):
        # Test flatten standard & nested
        (w, x, _, _) = self.data
        test = merge_arrays((x, w), flatten=True)
        control = np.array([(1, 1, 2, 3.0), (2, 4, 5, 6.0)],
                           dtype=[('f0', int),
                                  ('a', int), ('ba', float), ('bb', int)])
        assert_equal(test, control)

        test = merge_arrays((x, w), flatten=False)
        controldtype = [('f0', int),
                                ('f1', [('a', int),
                                        ('b', [('ba', float), ('bb', int), ('bc', [])])])]
        control = np.array([(1., (1, (2, 3.0, ()))), (2, (4, (5, 6.0, ())))],
                           dtype=controldtype)
        assert_equal(test, control)

    def test_wmasked_arrays(self):
        # Test merge_arrays masked arrays
        (_, x, _, _) = self.data
        mx = ma.array([1, 2, 3], mask=[1, 0, 0])
        test = merge_arrays((x, mx), usemask=True)
        control = ma.array([(1, 1), (2, 2), (-1, 3)],
                           mask=[(0, 1), (0, 0), (1, 0)],
                           dtype=[('f0', int), ('f1', int)])
        assert_equal(test, control)
        test = merge_arrays((x, mx), usemask=True, asrecarray=True)
        assert_equal(test, control)
        assert_(isinstance(test, MaskedRecords))

    def test_w_singlefield(self):
        # Test single field
        test = merge_arrays((np.array([1, 2]).view([('a', int)]),
                             np.array([10., 20., 30.])),)
        control = ma.array([(1, 10.), (2, 20.), (-1, 30.)],
                           mask=[(0, 0), (0, 0), (1, 0)],
                           dtype=[('a', int), ('f1', float)])
        assert_equal(test, control)

    def test_w_shorter_flex(self):
        # Test merge_arrays w/ a shorter flexndarray.
        z = self.data[-1]

        # Fixme, this test looks incomplete and broken
        #test = merge_arrays((z, np.array([10, 20, 30]).view([('C', int)])))
        #control = np.array([('A', 1., 10), ('B', 2., 20), ('-1', -1, 20)],
        #                   dtype=[('A', '|S3'), ('B', float), ('C', int)])
        #assert_equal(test, control)

        merge_arrays((z, np.array([10, 20, 30]).view([('C', int)])))
        np.array([('A', 1., 10), ('B', 2., 20), ('-1', -1, 20)],
                 dtype=[('A', '|S3'), ('B', float), ('C', int)])

    def test_singlerecord(self):
        (_, x, y, z) = self.data
        test = merge_arrays((x[0], y[0], z[0]), usemask=False)
        control = np.array([(1, 10, ('A', 1))],
                           dtype=[('f0', int),
                                  ('f1', int),
                                  ('f2', [('A', '|S3'), ('B', float)])])
        assert_equal(test, control)


class TestAppendFields:
    # Test append_fields

    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array(
            [('A', 1.), ('B', 2.)], dtype=[('A', '|S3'), ('B', float)])
        w = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])
        self.data = (w, x, y, z)

    def test_append_single(self):
        # Test simple case
        (_, x, _, _) = self.data
        test = append_fields(x, 'A', data=[10, 20, 30])
        control = ma.array([(1, 10), (2, 20), (-1, 30)],
                           mask=[(0, 0), (0, 0), (1, 0)],
                           dtype=[('f0', int), ('A', int)],)
        assert_equal(test, control)

    def test_append_double(self):
        # Test simple case
        (_, x, _, _) = self.data
        test = append_fields(x, ('A', 'B'), data=[[10, 20, 30], [100, 200]])
        control = ma.array([(1, 10, 100), (2, 20, 200), (-1, 30, -1)],
                           mask=[(0, 0, 0), (0, 0, 0), (1, 0, 1)],
                           dtype=[('f0', int), ('A', int), ('B', int)],)
        assert_equal(test, control)

    def test_append_on_flex(self):
        # Test append_fields on flexible type arrays
        z = self.data[-1]
        test = append_fields(z, 'C', data=[10, 20, 30])
        control = ma.array([('A', 1., 10), ('B', 2., 20), (-1, -1., 30)],
                           mask=[(0, 0, 0), (0, 0, 0), (1, 1, 0)],
                           dtype=[('A', '|S3'), ('B', float), ('C', int)],)
        assert_equal(test, control)

    def test_append_on_nested(self):
        # Test append_fields on nested fields
        w = self.data[0]
        test = append_fields(w, 'C', data=[10, 20, 30])
        control = ma.array([(1, (2, 3.0), 10),
                            (4, (5, 6.0), 20),
                            (-1, (-1, -1.), 30)],
                           mask=[(
                               0, (0, 0), 0), (0, (0, 0), 0), (1, (1, 1), 0)],
                           dtype=[('a', int),
                                  ('b', [('ba', float), ('bb', int)]),
                                  ('C', int)],)
        assert_equal(test, control)


class TestStackArrays:
    # Test stack_arrays
    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array(
            [('A', 1.), ('B', 2.)], dtype=[('A', '|S3'), ('B', float)])
        w = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])
        self.data = (w, x, y, z)

    def test_solo(self):
        # Test stack_arrays on single arrays
        (_, x, _, _) = self.data
        test = stack_arrays((x,))
        assert_equal(test, x)
        assert_(test is x)

        test = stack_arrays(x)
        assert_equal(test, x)
        assert_(test is x)

    def test_unnamed_fields(self):
        # Tests combinations of arrays w/o named fields
        (_, x, y, _) = self.data

        test = stack_arrays((x, x), usemask=False)
        control = np.array([1, 2, 1, 2])
        assert_equal(test, control)

        test = stack_arrays((x, y), usemask=False)
        control = np.array([1, 2, 10, 20, 30])
        assert_equal(test, control)

        test = stack_arrays((y, x), usemask=False)
        control = np.array([10, 20, 30, 1, 2])
        assert_equal(test, control)

    def test_unnamed_and_named_fields(self):
        # Test combination of arrays w/ & w/o named fields
        (_, x, _, z) = self.data

        test = stack_arrays((x, z))
        control = ma.array([(1, -1, -1), (2, -1, -1),
                            (-1, 'A', 1), (-1, 'B', 2)],
                           mask=[(0, 1, 1), (0, 1, 1),
                                 (1, 0, 0), (1, 0, 0)],
                           dtype=[('f0', int), ('A', '|S3'), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

        test = stack_arrays((z, x))
        control = ma.array([('A', 1, -1), ('B', 2, -1),
                            (-1, -1, 1), (-1, -1, 2), ],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (1, 1, 0), (1, 1, 0)],
                           dtype=[('A', '|S3'), ('B', float), ('f2', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

        test = stack_arrays((z, z, x))
        control = ma.array([('A', 1, -1), ('B', 2, -1),
                            ('A', 1, -1), ('B', 2, -1),
                            (-1, -1, 1), (-1, -1, 2), ],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (0, 0, 1), (0, 0, 1),
                                 (1, 1, 0), (1, 1, 0)],
                           dtype=[('A', '|S3'), ('B', float), ('f2', int)])
        assert_equal(test, control)

    def test_matching_named_fields(self):
        # Test combination of arrays w/ matching field names
        (_, x, _, z) = self.data
        zz = np.array([('a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                      dtype=[('A', '|S3'), ('B', float), ('C', float)])
        test = stack_arrays((z, zz))
        control = ma.array([('A', 1, -1), ('B', 2, -1),
                            (
                                'a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                           dtype=[('A', '|S3'), ('B', float), ('C', float)],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (0, 0, 0), (0, 0, 0), (0, 0, 0)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

        test = stack_arrays((z, zz, x))
        ndtype = [('A', '|S3'), ('B', float), ('C', float), ('f3', int)]
        control = ma.array([('A', 1, -1, -1), ('B', 2, -1, -1),
                            ('a', 10., 100., -1), ('b', 20., 200., -1),
                            ('c', 30., 300., -1),
                            (-1, -1, -1, 1), (-1, -1, -1, 2)],
                           dtype=ndtype,
                           mask=[(0, 0, 1, 1), (0, 0, 1, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1), (0, 0, 0, 1),
                                 (1, 1, 1, 0), (1, 1, 1, 0)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_defaults(self):
        # Test defaults: no exception raised if keys of defaults are not fields.
        (_, _, _, z) = self.data
        zz = np.array([('a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                      dtype=[('A', '|S3'), ('B', float), ('C', float)])
        defaults = {'A': '???', 'B': -999., 'C': -9999., 'D': -99999.}
        test = stack_arrays((z, zz), defaults=defaults)
        control = ma.array([('A', 1, -9999.), ('B', 2, -9999.),
                            (
                                'a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                           dtype=[('A', '|S3'), ('B', float), ('C', float)],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (0, 0, 0), (0, 0, 0), (0, 0, 0)])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

    def test_autoconversion(self):
        # Tests autoconversion
        adtype = [('A', int), ('B', bool), ('C', float)]
        a = ma.array([(1, 2, 3)], mask=[(0, 1, 0)], dtype=adtype)
        bdtype = [('A', int), ('B', float), ('C', float)]
        b = ma.array([(4, 5, 6)], dtype=bdtype)
        control = ma.array([(1, 2, 3), (4, 5, 6)], mask=[(0, 1, 0), (0, 0, 0)],
                           dtype=bdtype)
        test = stack_arrays((a, b), autoconvert=True)
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        with assert_raises(TypeError):
            stack_arrays((a, b), autoconvert=False)

    def test_checktitles(self):
        # Test using titles in the field names
        adtype = [(('a', 'A'), int), (('b', 'B'), bool), (('c', 'C'), float)]
        a = ma.array([(1, 2, 3)], mask=[(0, 1, 0)], dtype=adtype)
        bdtype = [(('a', 'A'), int), (('b', 'B'), bool), (('c', 'C'), float)]
        b = ma.array([(4, 5, 6)], dtype=bdtype)
        test = stack_arrays((a, b))
        control = ma.array([(1, 2, 3), (4, 5, 6)], mask=[(0, 1, 0), (0, 0, 0)],
                           dtype=bdtype)
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_subdtype(self):
        z = np.array([
            ('A', 1), ('B', 2)
        ], dtype=[('A', '|S3'), ('B', float, (1,))])
        zz = np.array([
            ('a', [10.], 100.), ('b', [20.], 200.), ('c', [30.], 300.)
        ], dtype=[('A', '|S3'), ('B', float, (1,)), ('C', float)])

        res = stack_arrays((z, zz))
        expected = ma.array(
            data=[
                (b'A', [1.0], 0),
                (b'B', [2.0], 0),
                (b'a', [10.0], 100.0),
                (b'b', [20.0], 200.0),
                (b'c', [30.0], 300.0)],
            mask=[
                (False, [False], True),
                (False, [False], True),
                (False, [False], False),
                (False, [False], False),
                (False, [False], False)
            ],
            dtype=zz.dtype
        )
        assert_equal(res.dtype, expected.dtype)
        assert_equal(res, expected)
        assert_equal(res.mask, expected.mask)


class TestJoinBy:
    def setup_method(self):
        self.a = np.array(list(zip(np.arange(10), np.arange(50, 60),
                                   np.arange(100, 110))),
                          dtype=[('a', int), ('b', int), ('c', int)])
        self.b = np.array(list(zip(np.arange(5, 15), np.arange(65, 75),
                                   np.arange(100, 110))),
                          dtype=[('a', int), ('b', int), ('d', int)])

    def test_inner_join(self):
        # Basic test of join_by
        a, b = self.a, self.b

        test = join_by('a', a, b, jointype='inner')
        control = np.array([(5, 55, 65, 105, 100), (6, 56, 66, 106, 101),
                            (7, 57, 67, 107, 102), (8, 58, 68, 108, 103),
                            (9, 59, 69, 109, 104)],
                           dtype=[('a', int), ('b1', int), ('b2', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_join(self):
        a, b = self.a, self.b

        # Fixme, this test is broken
        #test = join_by(('a', 'b'), a, b)
        #control = np.array([(5, 55, 105, 100), (6, 56, 106, 101),
        #                    (7, 57, 107, 102), (8, 58, 108, 103),
        #                    (9, 59, 109, 104)],
        #                   dtype=[('a', int), ('b', int),
        #                          ('c', int), ('d', int)])
        #assert_equal(test, control)

        join_by(('a', 'b'), a, b)
        np.array([(5, 55, 105, 100), (6, 56, 106, 101),
                  (7, 57, 107, 102), (8, 58, 108, 103),
                  (9, 59, 109, 104)],
                  dtype=[('a', int), ('b', int),
                         ('c', int), ('d', int)])

    def test_join_subdtype(self):
        # tests the bug in https://stackoverflow.com/q/44769632/102441
        foo = np.array([(1,)],
                       dtype=[('key', int)])
        bar = np.array([(1, np.array([1, 2, 3]))],
                       dtype=[('key', int), ('value', 'uint16', 3)])
        res = join_by('key', foo, bar)
        assert_equal(res, bar.view(ma.MaskedArray))

    def test_outer_join(self):
        a, b = self.a, self.b

        test = join_by(('a', 'b'), a, b, 'outer')
        control = ma.array([(0, 50, 100, -1), (1, 51, 101, -1),
                            (2, 52, 102, -1), (3, 53, 103, -1),
                            (4, 54, 104, -1), (5, 55, 105, -1),
                            (5, 65, -1, 100), (6, 56, 106, -1),
                            (6, 66, -1, 101), (7, 57, 107, -1),
                            (7, 67, -1, 102), (8, 58, 108, -1),
                            (8, 68, -1, 103), (9, 59, 109, -1),
                            (9, 69, -1, 104), (10, 70, -1, 105),
                            (11, 71, -1, 106), (12, 72, -1, 107),
                            (13, 73, -1, 108), (14, 74, -1, 109)],
                           mask=[(0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 1, 0),
                                 (0, 0, 1, 0), (0, 0, 1, 0),
                                 (0, 0, 1, 0), (0, 0, 1, 0)],
                           dtype=[('a', int), ('b', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_leftouter_join(self):
        a, b = self.a, self.b

        test = join_by(('a', 'b'), a, b, 'leftouter')
        control = ma.array([(0, 50, 100, -1), (1, 51, 101, -1),
                            (2, 52, 102, -1), (3, 53, 103, -1),
                            (4, 54, 104, -1), (5, 55, 105, -1),
                            (6, 56, 106, -1), (7, 57, 107, -1),
                            (8, 58, 108, -1), (9, 59, 109, -1)],
                           mask=[(0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1)],
                           dtype=[('a', int), ('b', int), ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_different_field_order(self):
        # gh-8940
        a = np.zeros(3, dtype=[('a', 'i4'), ('b', 'f4'), ('c', 'u1')])
        b = np.ones(3, dtype=[('c', 'u1'), ('b', 'f4'), ('a', 'i4')])
        # this should not give a FutureWarning:
        j = join_by(['c', 'b'], a, b, jointype='inner', usemask=False)
        assert_equal(j.dtype.names, ['b', 'c', 'a1', 'a2'])

    def test_duplicate_keys(self):
        a = np.zeros(3, dtype=[('a', 'i4'), ('b', 'f4'), ('c', 'u1')])
        b = np.ones(3, dtype=[('c', 'u1'), ('b', 'f4'), ('a', 'i4')])
        assert_raises(ValueError, join_by, ['a', 'b', 'b'], a, b)

    def test_same_name_different_dtypes_key(self):
        a_dtype = np.dtype([('key', 'S5'), ('value', '<f4')])
        b_dtype = np.dtype([('key', 'S10'), ('value', '<f4')])
        expected_dtype = np.dtype([
            ('key', 'S10'), ('value1', '<f4'), ('value2', '<f4')])

        a = np.array([('Sarah',  8.0), ('John', 6.0)], dtype=a_dtype)
        b = np.array([('Sarah', 10.0), ('John', 7.0)], dtype=b_dtype)
        res = join_by('key', a, b)

        assert_equal(res.dtype, expected_dtype)

    def test_same_name_different_dtypes(self):
        # gh-9338
        a_dtype = np.dtype([('key', 'S10'), ('value', '<f4')])
        b_dtype = np.dtype([('key', 'S10'), ('value', '<f8')])
        expected_dtype = np.dtype([
            ('key', '|S10'), ('value1', '<f4'), ('value2', '<f8')])

        a = np.array([('Sarah',  8.0), ('John', 6.0)], dtype=a_dtype)
        b = np.array([('Sarah', 10.0), ('John', 7.0)], dtype=b_dtype)
        res = join_by('key', a, b)

        assert_equal(res.dtype, expected_dtype)

    def test_subarray_key(self):
        a_dtype = np.dtype([('pos', int, 3), ('f', '<f4')])
        a = np.array([([1, 1, 1], np.pi), ([1, 2, 3], 0.0)], dtype=a_dtype)

        b_dtype = np.dtype([('pos', int, 3), ('g', '<f4')])
        b = np.array([([1, 1, 1], 3), ([3, 2, 1], 0.0)], dtype=b_dtype)

        expected_dtype = np.dtype([('pos', int, 3), ('f', '<f4'), ('g', '<f4')])
        expected = np.array([([1, 1, 1], np.pi, 3)], dtype=expected_dtype)

        res = join_by('pos', a, b)
        assert_equal(res.dtype, expected_dtype)
        assert_equal(res, expected)

    def test_padded_dtype(self):
        dt = np.dtype('i1,f4', align=True)
        dt.names = ('k', 'v')
        assert_(len(dt.descr), 3)  # padding field is inserted

        a = np.array([(1, 3), (3, 2)], dt)
        b = np.array([(1, 1), (2, 2)], dt)
        res = join_by('k', a, b)

        # no padding fields remain
        expected_dtype = np.dtype([
            ('k', 'i1'), ('v1', 'f4'), ('v2', 'f4')
        ])

        assert_equal(res.dtype, expected_dtype)


class TestJoinBy2:
    @classmethod
    def setup_method(cls):
        cls.a = np.array(list(zip(np.arange(10), np.arange(50, 60),
                                  np.arange(100, 110))),
                         dtype=[('a', int), ('b', int), ('c', int)])
        cls.b = np.array(list(zip(np.arange(10), np.arange(65, 75),
                                  np.arange(100, 110))),
                         dtype=[('a', int), ('b', int), ('d', int)])

    def test_no_r1postfix(self):
        # Basic test of join_by no_r1postfix
        a, b = self.a, self.b

        test = join_by(
            'a', a, b, r1postfix='', r2postfix='2', jointype='inner')
        control = np.array([(0, 50, 65, 100, 100), (1, 51, 66, 101, 101),
                            (2, 52, 67, 102, 102), (3, 53, 68, 103, 103),
                            (4, 54, 69, 104, 104), (5, 55, 70, 105, 105),
                            (6, 56, 71, 106, 106), (7, 57, 72, 107, 107),
                            (8, 58, 73, 108, 108), (9, 59, 74, 109, 109)],
                           dtype=[('a', int), ('b', int), ('b2', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_no_postfix(self):
        assert_raises(ValueError, join_by, 'a', self.a, self.b,
                      r1postfix='', r2postfix='')

    def test_no_r2postfix(self):
        # Basic test of join_by no_r2postfix
        a, b = self.a, self.b

        test = join_by(
            'a', a, b, r1postfix='1', r2postfix='', jointype='inner')
        control = np.array([(0, 50, 65, 100, 100), (1, 51, 66, 101, 101),
                            (2, 52, 67, 102, 102), (3, 53, 68, 103, 103),
                            (4, 54, 69, 104, 104), (5, 55, 70, 105, 105),
                            (6, 56, 71, 106, 106), (7, 57, 72, 107, 107),
                            (8, 58, 73, 108, 108), (9, 59, 74, 109, 109)],
                           dtype=[('a', int), ('b1', int), ('b', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_two_keys_two_vars(self):
        a = np.array(list(zip(np.tile([10, 11], 5), np.repeat(np.arange(5), 2),
                              np.arange(50, 60), np.arange(10, 20))),
                     dtype=[('k', int), ('a', int), ('b', int), ('c', int)])

        b = np.array(list(zip(np.tile([10, 11], 5), np.repeat(np.arange(5), 2),
                              np.arange(65, 75), np.arange(0, 10))),
                     dtype=[('k', int), ('a', int), ('b', int), ('c', int)])

        control = np.array([(10, 0, 50, 65, 10, 0), (11, 0, 51, 66, 11, 1),
                            (10, 1, 52, 67, 12, 2), (11, 1, 53, 68, 13, 3),
                            (10, 2, 54, 69, 14, 4), (11, 2, 55, 70, 15, 5),
                            (10, 3, 56, 71, 16, 6), (11, 3, 57, 72, 17, 7),
                            (10, 4, 58, 73, 18, 8), (11, 4, 59, 74, 19, 9)],
                           dtype=[('k', int), ('a', int), ('b1', int),
                                  ('b2', int), ('c1', int), ('c2', int)])
        test = join_by(
            ['a', 'k'], a, b, r1postfix='1', r2postfix='2', jointype='inner')
        assert_equal(test.dtype, control.dtype)
        assert_equal(test, control)

class TestAppendFieldsObj:
    """
    Test append_fields with arrays containing objects
    """
    # https://github.com/numpy/numpy/issues/2346

    def setup_method(self):
        from datetime import date
        self.data = {'obj': date(2000, 1, 1)}

    def test_append_to_objects(self):
        "Test append_fields when the base array contains objects"
        obj = self.data['obj']
        x = np.array([(obj, 1.), (obj, 2.)],
                      dtype=[('A', object), ('B', float)])
        y = np.array([10, 20], dtype=int)
        test = append_fields(x, 'C', data=y, usemask=False)
        control = np.array([(obj, 1.0, 10), (obj, 2.0, 20)],
                           dtype=[('A', object), ('B', float), ('C', int)])
        assert_equal(test, control)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_recfunctions.py ===

import numpy as np
import numpy.ma as ma
from numpy.lib.recfunctions import (
    append_fields,
    apply_along_fields,
    assign_fields_by_name,
    drop_fields,
    find_duplicates,
    get_fieldstructure,
    join_by,
    merge_arrays,
    recursive_fill_fields,
    rename_fields,
    repack_fields,
    require_fields,
    stack_arrays,
    structured_to_unstructured,
    unstructured_to_structured,
)
from numpy.ma.mrecords import MaskedRecords
from numpy.ma.testutils import assert_equal
from numpy.testing import assert_, assert_raises

get_fieldspec = np.lib.recfunctions._get_fieldspec
get_names = np.lib.recfunctions.get_names
get_names_flat = np.lib.recfunctions.get_names_flat
zip_descr = np.lib.recfunctions._zip_descr
zip_dtype = np.lib.recfunctions._zip_dtype


class TestRecFunctions:
    # Misc tests

    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array([('A', 1.), ('B', 2.)],
                     dtype=[('A', '|S3'), ('B', float)])
        w = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])
        self.data = (w, x, y, z)

    def test_zip_descr(self):
        # Test zip_descr
        (w, x, y, z) = self.data

        # Std array
        test = zip_descr((x, x), flatten=True)
        assert_equal(test,
                     np.dtype([('', int), ('', int)]))
        test = zip_descr((x, x), flatten=False)
        assert_equal(test,
                     np.dtype([('', int), ('', int)]))

        # Std & flexible-dtype
        test = zip_descr((x, z), flatten=True)
        assert_equal(test,
                     np.dtype([('', int), ('A', '|S3'), ('B', float)]))
        test = zip_descr((x, z), flatten=False)
        assert_equal(test,
                     np.dtype([('', int),
                               ('', [('A', '|S3'), ('B', float)])]))

        # Standard & nested dtype
        test = zip_descr((x, w), flatten=True)
        assert_equal(test,
                     np.dtype([('', int),
                               ('a', int),
                               ('ba', float), ('bb', int)]))
        test = zip_descr((x, w), flatten=False)
        assert_equal(test,
                     np.dtype([('', int),
                               ('', [('a', int),
                                     ('b', [('ba', float), ('bb', int)])])]))

    def test_drop_fields(self):
        # Test drop_fields
        a = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])

        # A basic field
        test = drop_fields(a, 'a')
        control = np.array([((2, 3.0),), ((5, 6.0),)],
                           dtype=[('b', [('ba', float), ('bb', int)])])
        assert_equal(test, control)

        # Another basic field (but nesting two fields)
        test = drop_fields(a, 'b')
        control = np.array([(1,), (4,)], dtype=[('a', int)])
        assert_equal(test, control)

        # A nested sub-field
        test = drop_fields(a, ['ba', ])
        control = np.array([(1, (3.0,)), (4, (6.0,))],
                           dtype=[('a', int), ('b', [('bb', int)])])
        assert_equal(test, control)

        # All the nested sub-field from a field: zap that field
        test = drop_fields(a, ['ba', 'bb'])
        control = np.array([(1,), (4,)], dtype=[('a', int)])
        assert_equal(test, control)

        # dropping all fields results in an array with no fields
        test = drop_fields(a, ['a', 'b'])
        control = np.array([(), ()], dtype=[])
        assert_equal(test, control)

    def test_rename_fields(self):
        # Test rename fields
        a = np.array([(1, (2, [3.0, 30.])), (4, (5, [6.0, 60.]))],
                     dtype=[('a', int),
                            ('b', [('ba', float), ('bb', (float, 2))])])
        test = rename_fields(a, {'a': 'A', 'bb': 'BB'})
        newdtype = [('A', int), ('b', [('ba', float), ('BB', (float, 2))])]
        control = a.view(newdtype)
        assert_equal(test.dtype, newdtype)
        assert_equal(test, control)

    def test_get_names(self):
        # Test get_names
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        test = get_names(ndtype)
        assert_equal(test, ('A', 'B'))

        ndtype = np.dtype([('a', int), ('b', [('ba', float), ('bb', int)])])
        test = get_names(ndtype)
        assert_equal(test, ('a', ('b', ('ba', 'bb'))))

        ndtype = np.dtype([('a', int), ('b', [])])
        test = get_names(ndtype)
        assert_equal(test, ('a', ('b', ())))

        ndtype = np.dtype([])
        test = get_names(ndtype)
        assert_equal(test, ())

    def test_get_names_flat(self):
        # Test get_names_flat
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        test = get_names_flat(ndtype)
        assert_equal(test, ('A', 'B'))

        ndtype = np.dtype([('a', int), ('b', [('ba', float), ('bb', int)])])
        test = get_names_flat(ndtype)
        assert_equal(test, ('a', 'b', 'ba', 'bb'))

        ndtype = np.dtype([('a', int), ('b', [])])
        test = get_names_flat(ndtype)
        assert_equal(test, ('a', 'b'))

        ndtype = np.dtype([])
        test = get_names_flat(ndtype)
        assert_equal(test, ())

    def test_get_fieldstructure(self):
        # Test get_fieldstructure

        # No nested fields
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        test = get_fieldstructure(ndtype)
        assert_equal(test, {'A': [], 'B': []})

        # One 1-nested field
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        test = get_fieldstructure(ndtype)
        assert_equal(test, {'A': [], 'B': [], 'BA': ['B', ], 'BB': ['B']})

        # One 2-nested fields
        ndtype = np.dtype([('A', int),
                           ('B', [('BA', int),
                                  ('BB', [('BBA', int), ('BBB', int)])])])
        test = get_fieldstructure(ndtype)
        control = {'A': [], 'B': [], 'BA': ['B'], 'BB': ['B'],
                   'BBA': ['B', 'BB'], 'BBB': ['B', 'BB']}
        assert_equal(test, control)

        # 0 fields
        ndtype = np.dtype([])
        test = get_fieldstructure(ndtype)
        assert_equal(test, {})

    def test_find_duplicates(self):
        # Test find_duplicates
        a = ma.array([(2, (2., 'B')), (1, (2., 'B')), (2, (2., 'B')),
                      (1, (1., 'B')), (2, (2., 'B')), (2, (2., 'C'))],
                     mask=[(0, (0, 0)), (0, (0, 0)), (0, (0, 0)),
                           (0, (0, 0)), (1, (0, 0)), (0, (1, 0))],
                     dtype=[('A', int), ('B', [('BA', float), ('BB', '|S1')])])

        test = find_duplicates(a, ignoremask=False, return_index=True)
        control = [0, 2]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='A', return_index=True)
        control = [0, 1, 2, 3, 5]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='B', return_index=True)
        control = [0, 1, 2, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='BA', return_index=True)
        control = [0, 1, 2, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, key='BB', return_index=True)
        control = [0, 1, 2, 3, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

    def test_find_duplicates_ignoremask(self):
        # Test the ignoremask option of find_duplicates
        ndtype = [('a', int)]
        a = ma.array([1, 1, 1, 2, 2, 3, 3],
                     mask=[0, 0, 1, 0, 0, 0, 1]).view(ndtype)
        test = find_duplicates(a, ignoremask=True, return_index=True)
        control = [0, 1, 3, 4]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

        test = find_duplicates(a, ignoremask=False, return_index=True)
        control = [0, 1, 2, 3, 4, 6]
        assert_equal(sorted(test[-1]), control)
        assert_equal(test[0], a[test[-1]])

    def test_repack_fields(self):
        dt = np.dtype('u1,f4,i8', align=True)
        a = np.zeros(2, dtype=dt)

        assert_equal(repack_fields(dt), np.dtype('u1,f4,i8'))
        assert_equal(repack_fields(a).itemsize, 13)
        assert_equal(repack_fields(repack_fields(dt), align=True), dt)

        # make sure type is preserved
        dt = np.dtype((np.record, dt))
        assert_(repack_fields(dt).type is np.record)

    def test_structured_to_unstructured(self, tmp_path):
        a = np.zeros(4, dtype=[('a', 'i4'), ('b', 'f4,u2'), ('c', 'f4', 2)])
        out = structured_to_unstructured(a)
        assert_equal(out, np.zeros((4, 5), dtype='f8'))

        b = np.array([(1, 2, 5), (4, 5, 7), (7, 8, 11), (10, 11, 12)],
                     dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
        out = np.mean(structured_to_unstructured(b[['x', 'z']]), axis=-1)
        assert_equal(out, np.array([3.,  5.5,  9., 11.]))
        out = np.mean(structured_to_unstructured(b[['x']]), axis=-1)
        assert_equal(out, np.array([1.,  4. ,  7., 10.]))  # noqa: E203

        c = np.arange(20).reshape((4, 5))
        out = unstructured_to_structured(c, a.dtype)
        want = np.array([( 0, ( 1.,  2), [ 3.,  4.]),
                         ( 5, ( 6.,  7), [ 8.,  9.]),
                         (10, (11., 12), [13., 14.]),
                         (15, (16., 17), [18., 19.])],
                     dtype=[('a', 'i4'),
                            ('b', [('f0', 'f4'), ('f1', 'u2')]),
                            ('c', 'f4', (2,))])
        assert_equal(out, want)

        d = np.array([(1, 2, 5), (4, 5, 7), (7, 8, 11), (10, 11, 12)],
                     dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
        assert_equal(apply_along_fields(np.mean, d),
                     np.array([ 8.0 / 3,  16.0 / 3,  26.0 / 3, 11.]))
        assert_equal(apply_along_fields(np.mean, d[['x', 'z']]),
                     np.array([ 3.,  5.5,  9., 11.]))

        # check that for uniform field dtypes we get a view, not a copy:
        d = np.array([(1, 2, 5), (4, 5, 7), (7, 8, 11), (10, 11, 12)],
                     dtype=[('x', 'i4'), ('y', 'i4'), ('z', 'i4')])
        dd = structured_to_unstructured(d)
        ddd = unstructured_to_structured(dd, d.dtype)
        assert_(np.shares_memory(dd, d))
        assert_(np.shares_memory(ddd, d))

        # check that reversing the order of attributes works
        dd_attrib_rev = structured_to_unstructured(d[['z', 'x']])
        assert_equal(dd_attrib_rev, [[5, 1], [7, 4], [11, 7], [12, 10]])
        assert_(np.shares_memory(dd_attrib_rev, d))

        # including uniform fields with subarrays unpacked
        d = np.array([(1, [2,  3], [[ 4,  5], [ 6,  7]]),
                      (8, [9, 10], [[11, 12], [13, 14]])],
                     dtype=[('x0', 'i4'), ('x1', ('i4', 2)),
                            ('x2', ('i4', (2, 2)))])
        dd = structured_to_unstructured(d)
        ddd = unstructured_to_structured(dd, d.dtype)
        assert_(np.shares_memory(dd, d))
        assert_(np.shares_memory(ddd, d))

        # check that reversing with sub-arrays works as expected
        d_rev = d[::-1]
        dd_rev = structured_to_unstructured(d_rev)
        assert_equal(dd_rev, [[8, 9, 10, 11, 12, 13, 14],
                              [1, 2, 3, 4, 5, 6, 7]])

        # check that sub-arrays keep the order of their values
        d_attrib_rev = d[['x2', 'x1', 'x0']]
        dd_attrib_rev = structured_to_unstructured(d_attrib_rev)
        assert_equal(dd_attrib_rev, [[4, 5, 6, 7, 2, 3, 1],
                                     [11, 12, 13, 14, 9, 10, 8]])

        # with ignored field at the end
        d = np.array([(1, [2,  3], [[4, 5], [6, 7]], 32),
                      (8, [9, 10], [[11, 12], [13, 14]], 64)],
                     dtype=[('x0', 'i4'), ('x1', ('i4', 2)),
                            ('x2', ('i4', (2, 2))), ('ignored', 'u1')])
        dd = structured_to_unstructured(d[['x0', 'x1', 'x2']])
        assert_(np.shares_memory(dd, d))
        assert_equal(dd, [[1, 2, 3, 4, 5, 6, 7],
                          [8, 9, 10, 11, 12, 13, 14]])

        # test that nested fields with identical names don't break anything
        point = np.dtype([('x', int), ('y', int)])
        triangle = np.dtype([('a', point), ('b', point), ('c', point)])
        arr = np.zeros(10, triangle)
        res = structured_to_unstructured(arr, dtype=int)
        assert_equal(res, np.zeros((10, 6), dtype=int))

        # test nested combinations of subarrays and structured arrays, gh-13333
        def subarray(dt, shape):
            return np.dtype((dt, shape))

        def structured(*dts):
            return np.dtype([(f'x{i}', dt) for i, dt in enumerate(dts)])

        def inspect(dt, dtype=None):
            arr = np.zeros((), dt)
            ret = structured_to_unstructured(arr, dtype=dtype)
            backarr = unstructured_to_structured(ret, dt)
            return ret.shape, ret.dtype, backarr.dtype

        dt = structured(subarray(structured(np.int32, np.int32), 3))
        assert_equal(inspect(dt), ((6,), np.int32, dt))

        dt = structured(subarray(subarray(np.int32, 2), 2))
        assert_equal(inspect(dt), ((4,), np.int32, dt))

        dt = structured(np.int32)
        assert_equal(inspect(dt), ((1,), np.int32, dt))

        dt = structured(np.int32, subarray(subarray(np.int32, 2), 2))
        assert_equal(inspect(dt), ((5,), np.int32, dt))

        dt = structured()
        assert_raises(ValueError, structured_to_unstructured, np.zeros(3, dt))

        # these currently don't work, but we may make it work in the future
        assert_raises(NotImplementedError, structured_to_unstructured,
                                           np.zeros(3, dt), dtype=np.int32)
        assert_raises(NotImplementedError, unstructured_to_structured,
                                           np.zeros((3, 0), dtype=np.int32))

        # test supported ndarray subclasses
        d_plain = np.array([(1, 2), (3, 4)], dtype=[('a', 'i4'), ('b', 'i4')])
        dd_expected = structured_to_unstructured(d_plain, copy=True)

        # recarray
        d = d_plain.view(np.recarray)

        dd = structured_to_unstructured(d, copy=False)
        ddd = structured_to_unstructured(d, copy=True)
        assert_(np.shares_memory(d, dd))
        assert_(type(dd) is np.recarray)
        assert_(type(ddd) is np.recarray)
        assert_equal(dd, dd_expected)
        assert_equal(ddd, dd_expected)

        # memmap
        d = np.memmap(tmp_path / 'memmap',
                      mode='w+',
                      dtype=d_plain.dtype,
                      shape=d_plain.shape)
        d[:] = d_plain
        dd = structured_to_unstructured(d, copy=False)
        ddd = structured_to_unstructured(d, copy=True)
        assert_(np.shares_memory(d, dd))
        assert_(type(dd) is np.memmap)
        assert_(type(ddd) is np.memmap)
        assert_equal(dd, dd_expected)
        assert_equal(ddd, dd_expected)

    def test_unstructured_to_structured(self):
        # test if dtype is the args of np.dtype
        a = np.zeros((20, 2))
        test_dtype_args = [('x', float), ('y', float)]
        test_dtype = np.dtype(test_dtype_args)
        field1 = unstructured_to_structured(a, dtype=test_dtype_args)  # now
        field2 = unstructured_to_structured(a, dtype=test_dtype)  # before
        assert_equal(field1, field2)

    def test_field_assignment_by_name(self):
        a = np.ones(2, dtype=[('a', 'i4'), ('b', 'f8'), ('c', 'u1')])
        newdt = [('b', 'f4'), ('c', 'u1')]

        assert_equal(require_fields(a, newdt), np.ones(2, newdt))

        b = np.array([(1, 2), (3, 4)], dtype=newdt)
        assign_fields_by_name(a, b, zero_unassigned=False)
        assert_equal(a, np.array([(1, 1, 2), (1, 3, 4)], dtype=a.dtype))
        assign_fields_by_name(a, b)
        assert_equal(a, np.array([(0, 1, 2), (0, 3, 4)], dtype=a.dtype))

        # test nested fields
        a = np.ones(2, dtype=[('a', [('b', 'f8'), ('c', 'u1')])])
        newdt = [('a', [('c', 'u1')])]
        assert_equal(require_fields(a, newdt), np.ones(2, newdt))
        b = np.array([((2,),), ((3,),)], dtype=newdt)
        assign_fields_by_name(a, b, zero_unassigned=False)
        assert_equal(a, np.array([((1, 2),), ((1, 3),)], dtype=a.dtype))
        assign_fields_by_name(a, b)
        assert_equal(a, np.array([((0, 2),), ((0, 3),)], dtype=a.dtype))

        # test unstructured code path for 0d arrays
        a, b = np.array(3), np.array(0)
        assign_fields_by_name(b, a)
        assert_equal(b[()], 3)


class TestRecursiveFillFields:
    # Test recursive_fill_fields.
    def test_simple_flexible(self):
        # Test recursive_fill_fields on flexible-array
        a = np.array([(1, 10.), (2, 20.)], dtype=[('A', int), ('B', float)])
        b = np.zeros((3,), dtype=a.dtype)
        test = recursive_fill_fields(a, b)
        control = np.array([(1, 10.), (2, 20.), (0, 0.)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)

    def test_masked_flexible(self):
        # Test recursive_fill_fields on masked flexible-array
        a = ma.array([(1, 10.), (2, 20.)], mask=[(0, 1), (1, 0)],
                     dtype=[('A', int), ('B', float)])
        b = ma.zeros((3,), dtype=a.dtype)
        test = recursive_fill_fields(a, b)
        control = ma.array([(1, 10.), (2, 20.), (0, 0.)],
                           mask=[(0, 1), (1, 0), (0, 0)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)


class TestMergeArrays:
    # Test merge_arrays

    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array(
            [('A', 1.), ('B', 2.)], dtype=[('A', '|S3'), ('B', float)])
        w = np.array(
            [(1, (2, 3.0, ())), (4, (5, 6.0, ()))],
            dtype=[('a', int), ('b', [('ba', float), ('bb', int), ('bc', [])])])
        self.data = (w, x, y, z)

    def test_solo(self):
        # Test merge_arrays on a single array.
        (_, x, _, z) = self.data

        test = merge_arrays(x)
        control = np.array([(1,), (2,)], dtype=[('f0', int)])
        assert_equal(test, control)
        test = merge_arrays((x,))
        assert_equal(test, control)

        test = merge_arrays(z, flatten=False)
        assert_equal(test, z)
        test = merge_arrays(z, flatten=True)
        assert_equal(test, z)

    def test_solo_w_flatten(self):
        # Test merge_arrays on a single array w & w/o flattening
        w = self.data[0]
        test = merge_arrays(w, flatten=False)
        assert_equal(test, w)

        test = merge_arrays(w, flatten=True)
        control = np.array([(1, 2, 3.0), (4, 5, 6.0)],
                           dtype=[('a', int), ('ba', float), ('bb', int)])
        assert_equal(test, control)

    def test_standard(self):
        # Test standard & standard
        # Test merge arrays
        (_, x, y, _) = self.data
        test = merge_arrays((x, y), usemask=False)
        control = np.array([(1, 10), (2, 20), (-1, 30)],
                           dtype=[('f0', int), ('f1', int)])
        assert_equal(test, control)

        test = merge_arrays((x, y), usemask=True)
        control = ma.array([(1, 10), (2, 20), (-1, 30)],
                           mask=[(0, 0), (0, 0), (1, 0)],
                           dtype=[('f0', int), ('f1', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_flatten(self):
        # Test standard & flexible
        (_, x, _, z) = self.data
        test = merge_arrays((x, z), flatten=True)
        control = np.array([(1, 'A', 1.), (2, 'B', 2.)],
                           dtype=[('f0', int), ('A', '|S3'), ('B', float)])
        assert_equal(test, control)

        test = merge_arrays((x, z), flatten=False)
        control = np.array([(1, ('A', 1.)), (2, ('B', 2.))],
                           dtype=[('f0', int),
                                  ('f1', [('A', '|S3'), ('B', float)])])
        assert_equal(test, control)

    def test_flatten_wflexible(self):
        # Test flatten standard & nested
        (w, x, _, _) = self.data
        test = merge_arrays((x, w), flatten=True)
        control = np.array([(1, 1, 2, 3.0), (2, 4, 5, 6.0)],
                           dtype=[('f0', int),
                                  ('a', int), ('ba', float), ('bb', int)])
        assert_equal(test, control)

        test = merge_arrays((x, w), flatten=False)
        controldtype = [('f0', int),
                                ('f1', [('a', int),
                                        ('b', [('ba', float), ('bb', int), ('bc', [])])])]
        control = np.array([(1., (1, (2, 3.0, ()))), (2, (4, (5, 6.0, ())))],
                           dtype=controldtype)
        assert_equal(test, control)

    def test_wmasked_arrays(self):
        # Test merge_arrays masked arrays
        (_, x, _, _) = self.data
        mx = ma.array([1, 2, 3], mask=[1, 0, 0])
        test = merge_arrays((x, mx), usemask=True)
        control = ma.array([(1, 1), (2, 2), (-1, 3)],
                           mask=[(0, 1), (0, 0), (1, 0)],
                           dtype=[('f0', int), ('f1', int)])
        assert_equal(test, control)
        test = merge_arrays((x, mx), usemask=True, asrecarray=True)
        assert_equal(test, control)
        assert_(isinstance(test, MaskedRecords))

    def test_w_singlefield(self):
        # Test single field
        test = merge_arrays((np.array([1, 2]).view([('a', int)]),
                             np.array([10., 20., 30.])),)
        control = ma.array([(1, 10.), (2, 20.), (-1, 30.)],
                           mask=[(0, 0), (0, 0), (1, 0)],
                           dtype=[('a', int), ('f1', float)])
        assert_equal(test, control)

    def test_w_shorter_flex(self):
        # Test merge_arrays w/ a shorter flexndarray.
        z = self.data[-1]

        # Fixme, this test looks incomplete and broken
        #test = merge_arrays((z, np.array([10, 20, 30]).view([('C', int)])))
        #control = np.array([('A', 1., 10), ('B', 2., 20), ('-1', -1, 20)],
        #                   dtype=[('A', '|S3'), ('B', float), ('C', int)])
        #assert_equal(test, control)

        merge_arrays((z, np.array([10, 20, 30]).view([('C', int)])))
        np.array([('A', 1., 10), ('B', 2., 20), ('-1', -1, 20)],
                 dtype=[('A', '|S3'), ('B', float), ('C', int)])

    def test_singlerecord(self):
        (_, x, y, z) = self.data
        test = merge_arrays((x[0], y[0], z[0]), usemask=False)
        control = np.array([(1, 10, ('A', 1))],
                           dtype=[('f0', int),
                                  ('f1', int),
                                  ('f2', [('A', '|S3'), ('B', float)])])
        assert_equal(test, control)


class TestAppendFields:
    # Test append_fields

    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array(
            [('A', 1.), ('B', 2.)], dtype=[('A', '|S3'), ('B', float)])
        w = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])
        self.data = (w, x, y, z)

    def test_append_single(self):
        # Test simple case
        (_, x, _, _) = self.data
        test = append_fields(x, 'A', data=[10, 20, 30])
        control = ma.array([(1, 10), (2, 20), (-1, 30)],
                           mask=[(0, 0), (0, 0), (1, 0)],
                           dtype=[('f0', int), ('A', int)],)
        assert_equal(test, control)

    def test_append_double(self):
        # Test simple case
        (_, x, _, _) = self.data
        test = append_fields(x, ('A', 'B'), data=[[10, 20, 30], [100, 200]])
        control = ma.array([(1, 10, 100), (2, 20, 200), (-1, 30, -1)],
                           mask=[(0, 0, 0), (0, 0, 0), (1, 0, 1)],
                           dtype=[('f0', int), ('A', int), ('B', int)],)
        assert_equal(test, control)

    def test_append_on_flex(self):
        # Test append_fields on flexible type arrays
        z = self.data[-1]
        test = append_fields(z, 'C', data=[10, 20, 30])
        control = ma.array([('A', 1., 10), ('B', 2., 20), (-1, -1., 30)],
                           mask=[(0, 0, 0), (0, 0, 0), (1, 1, 0)],
                           dtype=[('A', '|S3'), ('B', float), ('C', int)],)
        assert_equal(test, control)

    def test_append_on_nested(self):
        # Test append_fields on nested fields
        w = self.data[0]
        test = append_fields(w, 'C', data=[10, 20, 30])
        control = ma.array([(1, (2, 3.0), 10),
                            (4, (5, 6.0), 20),
                            (-1, (-1, -1.), 30)],
                           mask=[(
                               0, (0, 0), 0), (0, (0, 0), 0), (1, (1, 1), 0)],
                           dtype=[('a', int),
                                  ('b', [('ba', float), ('bb', int)]),
                                  ('C', int)],)
        assert_equal(test, control)


class TestStackArrays:
    # Test stack_arrays
    def setup_method(self):
        x = np.array([1, 2, ])
        y = np.array([10, 20, 30])
        z = np.array(
            [('A', 1.), ('B', 2.)], dtype=[('A', '|S3'), ('B', float)])
        w = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
                     dtype=[('a', int), ('b', [('ba', float), ('bb', int)])])
        self.data = (w, x, y, z)

    def test_solo(self):
        # Test stack_arrays on single arrays
        (_, x, _, _) = self.data
        test = stack_arrays((x,))
        assert_equal(test, x)
        assert_(test is x)

        test = stack_arrays(x)
        assert_equal(test, x)
        assert_(test is x)

    def test_unnamed_fields(self):
        # Tests combinations of arrays w/o named fields
        (_, x, y, _) = self.data

        test = stack_arrays((x, x), usemask=False)
        control = np.array([1, 2, 1, 2])
        assert_equal(test, control)

        test = stack_arrays((x, y), usemask=False)
        control = np.array([1, 2, 10, 20, 30])
        assert_equal(test, control)

        test = stack_arrays((y, x), usemask=False)
        control = np.array([10, 20, 30, 1, 2])
        assert_equal(test, control)

    def test_unnamed_and_named_fields(self):
        # Test combination of arrays w/ & w/o named fields
        (_, x, _, z) = self.data

        test = stack_arrays((x, z))
        control = ma.array([(1, -1, -1), (2, -1, -1),
                            (-1, 'A', 1), (-1, 'B', 2)],
                           mask=[(0, 1, 1), (0, 1, 1),
                                 (1, 0, 0), (1, 0, 0)],
                           dtype=[('f0', int), ('A', '|S3'), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

        test = stack_arrays((z, x))
        control = ma.array([('A', 1, -1), ('B', 2, -1),
                            (-1, -1, 1), (-1, -1, 2), ],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (1, 1, 0), (1, 1, 0)],
                           dtype=[('A', '|S3'), ('B', float), ('f2', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

        test = stack_arrays((z, z, x))
        control = ma.array([('A', 1, -1), ('B', 2, -1),
                            ('A', 1, -1), ('B', 2, -1),
                            (-1, -1, 1), (-1, -1, 2), ],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (0, 0, 1), (0, 0, 1),
                                 (1, 1, 0), (1, 1, 0)],
                           dtype=[('A', '|S3'), ('B', float), ('f2', int)])
        assert_equal(test, control)

    def test_matching_named_fields(self):
        # Test combination of arrays w/ matching field names
        (_, x, _, z) = self.data
        zz = np.array([('a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                      dtype=[('A', '|S3'), ('B', float), ('C', float)])
        test = stack_arrays((z, zz))
        control = ma.array([('A', 1, -1), ('B', 2, -1),
                            (
                                'a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                           dtype=[('A', '|S3'), ('B', float), ('C', float)],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (0, 0, 0), (0, 0, 0), (0, 0, 0)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

        test = stack_arrays((z, zz, x))
        ndtype = [('A', '|S3'), ('B', float), ('C', float), ('f3', int)]
        control = ma.array([('A', 1, -1, -1), ('B', 2, -1, -1),
                            ('a', 10., 100., -1), ('b', 20., 200., -1),
                            ('c', 30., 300., -1),
                            (-1, -1, -1, 1), (-1, -1, -1, 2)],
                           dtype=ndtype,
                           mask=[(0, 0, 1, 1), (0, 0, 1, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1), (0, 0, 0, 1),
                                 (1, 1, 1, 0), (1, 1, 1, 0)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_defaults(self):
        # Test defaults: no exception raised if keys of defaults are not fields.
        (_, _, _, z) = self.data
        zz = np.array([('a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                      dtype=[('A', '|S3'), ('B', float), ('C', float)])
        defaults = {'A': '???', 'B': -999., 'C': -9999., 'D': -99999.}
        test = stack_arrays((z, zz), defaults=defaults)
        control = ma.array([('A', 1, -9999.), ('B', 2, -9999.),
                            (
                                'a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
                           dtype=[('A', '|S3'), ('B', float), ('C', float)],
                           mask=[(0, 0, 1), (0, 0, 1),
                                 (0, 0, 0), (0, 0, 0), (0, 0, 0)])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

    def test_autoconversion(self):
        # Tests autoconversion
        adtype = [('A', int), ('B', bool), ('C', float)]
        a = ma.array([(1, 2, 3)], mask=[(0, 1, 0)], dtype=adtype)
        bdtype = [('A', int), ('B', float), ('C', float)]
        b = ma.array([(4, 5, 6)], dtype=bdtype)
        control = ma.array([(1, 2, 3), (4, 5, 6)], mask=[(0, 1, 0), (0, 0, 0)],
                           dtype=bdtype)
        test = stack_arrays((a, b), autoconvert=True)
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        with assert_raises(TypeError):
            stack_arrays((a, b), autoconvert=False)

    def test_checktitles(self):
        # Test using titles in the field names
        adtype = [(('a', 'A'), int), (('b', 'B'), bool), (('c', 'C'), float)]
        a = ma.array([(1, 2, 3)], mask=[(0, 1, 0)], dtype=adtype)
        bdtype = [(('a', 'A'), int), (('b', 'B'), bool), (('c', 'C'), float)]
        b = ma.array([(4, 5, 6)], dtype=bdtype)
        test = stack_arrays((a, b))
        control = ma.array([(1, 2, 3), (4, 5, 6)], mask=[(0, 1, 0), (0, 0, 0)],
                           dtype=bdtype)
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_subdtype(self):
        z = np.array([
            ('A', 1), ('B', 2)
        ], dtype=[('A', '|S3'), ('B', float, (1,))])
        zz = np.array([
            ('a', [10.], 100.), ('b', [20.], 200.), ('c', [30.], 300.)
        ], dtype=[('A', '|S3'), ('B', float, (1,)), ('C', float)])

        res = stack_arrays((z, zz))
        expected = ma.array(
            data=[
                (b'A', [1.0], 0),
                (b'B', [2.0], 0),
                (b'a', [10.0], 100.0),
                (b'b', [20.0], 200.0),
                (b'c', [30.0], 300.0)],
            mask=[
                (False, [False], True),
                (False, [False], True),
                (False, [False], False),
                (False, [False], False),
                (False, [False], False)
            ],
            dtype=zz.dtype
        )
        assert_equal(res.dtype, expected.dtype)
        assert_equal(res, expected)
        assert_equal(res.mask, expected.mask)


class TestJoinBy:
    def setup_method(self):
        self.a = np.array(list(zip(np.arange(10), np.arange(50, 60),
                                   np.arange(100, 110))),
                          dtype=[('a', int), ('b', int), ('c', int)])
        self.b = np.array(list(zip(np.arange(5, 15), np.arange(65, 75),
                                   np.arange(100, 110))),
                          dtype=[('a', int), ('b', int), ('d', int)])

    def test_inner_join(self):
        # Basic test of join_by
        a, b = self.a, self.b

        test = join_by('a', a, b, jointype='inner')
        control = np.array([(5, 55, 65, 105, 100), (6, 56, 66, 106, 101),
                            (7, 57, 67, 107, 102), (8, 58, 68, 108, 103),
                            (9, 59, 69, 109, 104)],
                           dtype=[('a', int), ('b1', int), ('b2', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_join(self):
        a, b = self.a, self.b

        # Fixme, this test is broken
        #test = join_by(('a', 'b'), a, b)
        #control = np.array([(5, 55, 105, 100), (6, 56, 106, 101),
        #                    (7, 57, 107, 102), (8, 58, 108, 103),
        #                    (9, 59, 109, 104)],
        #                   dtype=[('a', int), ('b', int),
        #                          ('c', int), ('d', int)])
        #assert_equal(test, control)

        join_by(('a', 'b'), a, b)
        np.array([(5, 55, 105, 100), (6, 56, 106, 101),
                  (7, 57, 107, 102), (8, 58, 108, 103),
                  (9, 59, 109, 104)],
                  dtype=[('a', int), ('b', int),
                         ('c', int), ('d', int)])

    def test_join_subdtype(self):
        # tests the bug in https://stackoverflow.com/q/44769632/102441
        foo = np.array([(1,)],
                       dtype=[('key', int)])
        bar = np.array([(1, np.array([1, 2, 3]))],
                       dtype=[('key', int), ('value', 'uint16', 3)])
        res = join_by('key', foo, bar)
        assert_equal(res, bar.view(ma.MaskedArray))

    def test_outer_join(self):
        a, b = self.a, self.b

        test = join_by(('a', 'b'), a, b, 'outer')
        control = ma.array([(0, 50, 100, -1), (1, 51, 101, -1),
                            (2, 52, 102, -1), (3, 53, 103, -1),
                            (4, 54, 104, -1), (5, 55, 105, -1),
                            (5, 65, -1, 100), (6, 56, 106, -1),
                            (6, 66, -1, 101), (7, 57, 107, -1),
                            (7, 67, -1, 102), (8, 58, 108, -1),
                            (8, 68, -1, 103), (9, 59, 109, -1),
                            (9, 69, -1, 104), (10, 70, -1, 105),
                            (11, 71, -1, 106), (12, 72, -1, 107),
                            (13, 73, -1, 108), (14, 74, -1, 109)],
                           mask=[(0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 0, 1),
                                 (0, 0, 1, 0), (0, 0, 1, 0),
                                 (0, 0, 1, 0), (0, 0, 1, 0),
                                 (0, 0, 1, 0), (0, 0, 1, 0)],
                           dtype=[('a', int), ('b', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_leftouter_join(self):
        a, b = self.a, self.b

        test = join_by(('a', 'b'), a, b, 'leftouter')
        control = ma.array([(0, 50, 100, -1), (1, 51, 101, -1),
                            (2, 52, 102, -1), (3, 53, 103, -1),
                            (4, 54, 104, -1), (5, 55, 105, -1),
                            (6, 56, 106, -1), (7, 57, 107, -1),
                            (8, 58, 108, -1), (9, 59, 109, -1)],
                           mask=[(0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1),
                                 (0, 0, 0, 1), (0, 0, 0, 1)],
                           dtype=[('a', int), ('b', int), ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_different_field_order(self):
        # gh-8940
        a = np.zeros(3, dtype=[('a', 'i4'), ('b', 'f4'), ('c', 'u1')])
        b = np.ones(3, dtype=[('c', 'u1'), ('b', 'f4'), ('a', 'i4')])
        # this should not give a FutureWarning:
        j = join_by(['c', 'b'], a, b, jointype='inner', usemask=False)
        assert_equal(j.dtype.names, ['b', 'c', 'a1', 'a2'])

    def test_duplicate_keys(self):
        a = np.zeros(3, dtype=[('a', 'i4'), ('b', 'f4'), ('c', 'u1')])
        b = np.ones(3, dtype=[('c', 'u1'), ('b', 'f4'), ('a', 'i4')])
        assert_raises(ValueError, join_by, ['a', 'b', 'b'], a, b)

    def test_same_name_different_dtypes_key(self):
        a_dtype = np.dtype([('key', 'S5'), ('value', '<f4')])
        b_dtype = np.dtype([('key', 'S10'), ('value', '<f4')])
        expected_dtype = np.dtype([
            ('key', 'S10'), ('value1', '<f4'), ('value2', '<f4')])

        a = np.array([('Sarah',  8.0), ('John', 6.0)], dtype=a_dtype)
        b = np.array([('Sarah', 10.0), ('John', 7.0)], dtype=b_dtype)
        res = join_by('key', a, b)

        assert_equal(res.dtype, expected_dtype)

    def test_same_name_different_dtypes(self):
        # gh-9338
        a_dtype = np.dtype([('key', 'S10'), ('value', '<f4')])
        b_dtype = np.dtype([('key', 'S10'), ('value', '<f8')])
        expected_dtype = np.dtype([
            ('key', '|S10'), ('value1', '<f4'), ('value2', '<f8')])

        a = np.array([('Sarah',  8.0), ('John', 6.0)], dtype=a_dtype)
        b = np.array([('Sarah', 10.0), ('John', 7.0)], dtype=b_dtype)
        res = join_by('key', a, b)

        assert_equal(res.dtype, expected_dtype)

    def test_subarray_key(self):
        a_dtype = np.dtype([('pos', int, 3), ('f', '<f4')])
        a = np.array([([1, 1, 1], np.pi), ([1, 2, 3], 0.0)], dtype=a_dtype)

        b_dtype = np.dtype([('pos', int, 3), ('g', '<f4')])
        b = np.array([([1, 1, 1], 3), ([3, 2, 1], 0.0)], dtype=b_dtype)

        expected_dtype = np.dtype([('pos', int, 3), ('f', '<f4'), ('g', '<f4')])
        expected = np.array([([1, 1, 1], np.pi, 3)], dtype=expected_dtype)

        res = join_by('pos', a, b)
        assert_equal(res.dtype, expected_dtype)
        assert_equal(res, expected)

    def test_padded_dtype(self):
        dt = np.dtype('i1,f4', align=True)
        dt.names = ('k', 'v')
        assert_(len(dt.descr), 3)  # padding field is inserted

        a = np.array([(1, 3), (3, 2)], dt)
        b = np.array([(1, 1), (2, 2)], dt)
        res = join_by('k', a, b)

        # no padding fields remain
        expected_dtype = np.dtype([
            ('k', 'i1'), ('v1', 'f4'), ('v2', 'f4')
        ])

        assert_equal(res.dtype, expected_dtype)


class TestJoinBy2:
    @classmethod
    def setup_method(cls):
        cls.a = np.array(list(zip(np.arange(10), np.arange(50, 60),
                                  np.arange(100, 110))),
                         dtype=[('a', int), ('b', int), ('c', int)])
        cls.b = np.array(list(zip(np.arange(10), np.arange(65, 75),
                                  np.arange(100, 110))),
                         dtype=[('a', int), ('b', int), ('d', int)])

    def test_no_r1postfix(self):
        # Basic test of join_by no_r1postfix
        a, b = self.a, self.b

        test = join_by(
            'a', a, b, r1postfix='', r2postfix='2', jointype='inner')
        control = np.array([(0, 50, 65, 100, 100), (1, 51, 66, 101, 101),
                            (2, 52, 67, 102, 102), (3, 53, 68, 103, 103),
                            (4, 54, 69, 104, 104), (5, 55, 70, 105, 105),
                            (6, 56, 71, 106, 106), (7, 57, 72, 107, 107),
                            (8, 58, 73, 108, 108), (9, 59, 74, 109, 109)],
                           dtype=[('a', int), ('b', int), ('b2', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_no_postfix(self):
        assert_raises(ValueError, join_by, 'a', self.a, self.b,
                      r1postfix='', r2postfix='')

    def test_no_r2postfix(self):
        # Basic test of join_by no_r2postfix
        a, b = self.a, self.b

        test = join_by(
            'a', a, b, r1postfix='1', r2postfix='', jointype='inner')
        control = np.array([(0, 50, 65, 100, 100), (1, 51, 66, 101, 101),
                            (2, 52, 67, 102, 102), (3, 53, 68, 103, 103),
                            (4, 54, 69, 104, 104), (5, 55, 70, 105, 105),
                            (6, 56, 71, 106, 106), (7, 57, 72, 107, 107),
                            (8, 58, 73, 108, 108), (9, 59, 74, 109, 109)],
                           dtype=[('a', int), ('b1', int), ('b', int),
                                  ('c', int), ('d', int)])
        assert_equal(test, control)

    def test_two_keys_two_vars(self):
        a = np.array(list(zip(np.tile([10, 11], 5), np.repeat(np.arange(5), 2),
                              np.arange(50, 60), np.arange(10, 20))),
                     dtype=[('k', int), ('a', int), ('b', int), ('c', int)])

        b = np.array(list(zip(np.tile([10, 11], 5), np.repeat(np.arange(5), 2),
                              np.arange(65, 75), np.arange(0, 10))),
                     dtype=[('k', int), ('a', int), ('b', int), ('c', int)])

        control = np.array([(10, 0, 50, 65, 10, 0), (11, 0, 51, 66, 11, 1),
                            (10, 1, 52, 67, 12, 2), (11, 1, 53, 68, 13, 3),
                            (10, 2, 54, 69, 14, 4), (11, 2, 55, 70, 15, 5),
                            (10, 3, 56, 71, 16, 6), (11, 3, 57, 72, 17, 7),
                            (10, 4, 58, 73, 18, 8), (11, 4, 59, 74, 19, 9)],
                           dtype=[('k', int), ('a', int), ('b1', int),
                                  ('b2', int), ('c1', int), ('c2', int)])
        test = join_by(
            ['a', 'k'], a, b, r1postfix='1', r2postfix='2', jointype='inner')
        assert_equal(test.dtype, control.dtype)
        assert_equal(test, control)

class TestAppendFieldsObj:
    """
    Test append_fields with arrays containing objects
    """
    # https://github.com/numpy/numpy/issues/2346

    def setup_method(self):
        from datetime import date
        self.data = {'obj': date(2000, 1, 1)}

    def test_append_to_objects(self):
        "Test append_fields when the base array contains objects"
        obj = self.data['obj']
        x = np.array([(obj, 1.), (obj, 2.)],
                      dtype=[('A', object), ('B', float)])
        y = np.array([10, 20], dtype=int)
        test = append_fields(x, 'C', data=y, usemask=False)
        control = np.array([(obj, 1.0, 10), (obj, 2.0, 20)],
                           dtype=[('A', object), ('B', float), ('C', int)])
        assert_equal(test, control)

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\_assistants.py ===
from __future__ import annotations

import asyncio
from types import TracebackType
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Callable, Iterable, Iterator, cast
from typing_extensions import Awaitable, AsyncIterable, AsyncIterator, assert_never

import httpx

from ..._utils import is_dict, is_list, consume_sync_iterator, consume_async_iterator
from ..._compat import model_dump
from ..._models import construct_type
from ..._streaming import Stream, AsyncStream
from ...types.beta import AssistantStreamEvent
from ...types.beta.threads import (
    Run,
    Text,
    Message,
    ImageFile,
    TextDelta,
    MessageDelta,
    MessageContent,
    MessageContentDelta,
)
from ...types.beta.threads.runs import RunStep, ToolCall, RunStepDelta, ToolCallDelta


class AssistantEventHandler:
    text_deltas: Iterable[str]
    """Iterator over just the text deltas in the stream.

    This corresponds to the `thread.message.delta` event
    in the API.

    ```py
    for text in stream.text_deltas:
        print(text, end="", flush=True)
    print()
    ```
    """

    def __init__(self) -> None:
        self._current_event: AssistantStreamEvent | None = None
        self._current_message_content_index: int | None = None
        self._current_message_content: MessageContent | None = None
        self._current_tool_call_index: int | None = None
        self._current_tool_call: ToolCall | None = None
        self.__current_run_step_id: str | None = None
        self.__current_run: Run | None = None
        self.__run_step_snapshots: dict[str, RunStep] = {}
        self.__message_snapshots: dict[str, Message] = {}
        self.__current_message_snapshot: Message | None = None

        self.text_deltas = self.__text_deltas__()
        self._iterator = self.__stream__()
        self.__stream: Stream[AssistantStreamEvent] | None = None

    def _init(self, stream: Stream[AssistantStreamEvent]) -> None:
        if self.__stream:
            raise RuntimeError(
                "A single event handler cannot be shared between multiple streams; You will need to construct a new event handler instance"
            )

        self.__stream = stream

    def __next__(self) -> AssistantStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[AssistantStreamEvent]:
        for item in self._iterator:
            yield item

    @property
    def current_event(self) -> AssistantStreamEvent | None:
        return self._current_event

    @property
    def current_run(self) -> Run | None:
        return self.__current_run

    @property
    def current_run_step_snapshot(self) -> RunStep | None:
        if not self.__current_run_step_id:
            return None

        return self.__run_step_snapshots[self.__current_run_step_id]

    @property
    def current_message_snapshot(self) -> Message | None:
        return self.__current_message_snapshot

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called when the context manager exits.
        """
        if self.__stream:
            self.__stream.close()

    def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        consume_sync_iterator(self)

    def get_final_run(self) -> Run:
        """Wait for the stream to finish and returns the completed Run object"""
        self.until_done()

        if not self.__current_run:
            raise RuntimeError("No final run object found")

        return self.__current_run

    def get_final_run_steps(self) -> list[RunStep]:
        """Wait for the stream to finish and returns the steps taken in this run"""
        self.until_done()

        if not self.__run_step_snapshots:
            raise RuntimeError("No run steps found")

        return [step for step in self.__run_step_snapshots.values()]

    def get_final_messages(self) -> list[Message]:
        """Wait for the stream to finish and returns the messages emitted in this run"""
        self.until_done()

        if not self.__message_snapshots:
            raise RuntimeError("No messages found")

        return [message for message in self.__message_snapshots.values()]

    def __text_deltas__(self) -> Iterator[str]:
        for event in self:
            if event.event != "thread.message.delta":
                continue

            for content_delta in event.data.delta.content or []:
                if content_delta.type == "text" and content_delta.text and content_delta.text.value:
                    yield content_delta.text.value

    # event handlers

    def on_end(self) -> None:
        """Fires when the stream has finished.

        This happens if the stream is read to completion
        or if an exception occurs during iteration.
        """

    def on_event(self, event: AssistantStreamEvent) -> None:
        """Callback that is fired for every Server-Sent-Event"""

    def on_run_step_created(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is created"""

    def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        """Callback that is fired whenever a run step delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the run step. For example, a tool calls event may
        look like this:

        # delta
        tool_calls=[
            RunStepDeltaToolCallsCodeInterpreter(
                index=0,
                type='code_interpreter',
                id=None,
                code_interpreter=CodeInterpreter(input=' sympy', outputs=None)
            )
        ]
        # snapshot
        tool_calls=[
            CodeToolCall(
                id='call_wKayJlcYV12NiadiZuJXxcfx',
                code_interpreter=CodeInterpreter(input='from sympy', outputs=[]),
                type='code_interpreter',
                index=0
            )
        ],
        """

    def on_run_step_done(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is completed"""

    def on_tool_call_created(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call is created"""

    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    def on_tool_call_done(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    def on_exception(self, exception: Exception) -> None:
        """Fired whenever an exception happens during streaming"""

    def on_timeout(self) -> None:
        """Fires if the request times out"""

    def on_message_created(self, message: Message) -> None:
        """Callback that is fired when a message is created"""

    def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        """Callback that is fired whenever a message delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the message. For example, a text content event may
        look like this:

        # delta
        MessageDeltaText(
            index=0,
            type='text',
            text=Text(
                value=' Jane'
            ),
        )
        # snapshot
        MessageContentText(
            index=0,
            type='text',
            text=Text(
                value='Certainly, Jane'
            ),
        )
        """

    def on_message_done(self, message: Message) -> None:
        """Callback that is fired when a message is completed"""

    def on_text_created(self, text: Text) -> None:
        """Callback that is fired when a text content block is created"""

    def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        """Callback that is fired whenever a text content delta is returned
        by the API.

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the text. For example:

        on_text_delta(TextDelta(value="The"), Text(value="The")),
        on_text_delta(TextDelta(value=" solution"), Text(value="The solution")),
        on_text_delta(TextDelta(value=" to"), Text(value="The solution to")),
        on_text_delta(TextDelta(value=" the"), Text(value="The solution to the")),
        on_text_delta(TextDelta(value=" equation"), Text(value="The solution to the equation")),
        """

    def on_text_done(self, text: Text) -> None:
        """Callback that is fired when a text content block is finished"""

    def on_image_file_done(self, image_file: ImageFile) -> None:
        """Callback that is fired when an image file block is finished"""

    def _emit_sse_event(self, event: AssistantStreamEvent) -> None:
        self._current_event = event
        self.on_event(event)

        self.__current_message_snapshot, new_content = accumulate_event(
            event=event,
            current_message_snapshot=self.__current_message_snapshot,
        )
        if self.__current_message_snapshot is not None:
            self.__message_snapshots[self.__current_message_snapshot.id] = self.__current_message_snapshot

        accumulate_run_step(
            event=event,
            run_step_snapshots=self.__run_step_snapshots,
        )

        for content_delta in new_content:
            assert self.__current_message_snapshot is not None

            block = self.__current_message_snapshot.content[content_delta.index]
            if block.type == "text":
                self.on_text_created(block.text)

        if (
            event.event == "thread.run.completed"
            or event.event == "thread.run.cancelled"
            or event.event == "thread.run.expired"
            or event.event == "thread.run.failed"
            or event.event == "thread.run.requires_action"
            or event.event == "thread.run.incomplete"
        ):
            self.__current_run = event.data
            if self._current_tool_call:
                self.on_tool_call_done(self._current_tool_call)
        elif (
            event.event == "thread.run.created"
            or event.event == "thread.run.in_progress"
            or event.event == "thread.run.cancelling"
            or event.event == "thread.run.queued"
        ):
            self.__current_run = event.data
        elif event.event == "thread.message.created":
            self.on_message_created(event.data)
        elif event.event == "thread.message.delta":
            snapshot = self.__current_message_snapshot
            assert snapshot is not None

            message_delta = event.data.delta
            if message_delta.content is not None:
                for content_delta in message_delta.content:
                    if content_delta.type == "text" and content_delta.text:
                        snapshot_content = snapshot.content[content_delta.index]
                        assert snapshot_content.type == "text"
                        self.on_text_delta(content_delta.text, snapshot_content.text)

                    # If the delta is for a new message content:
                    # - emit on_text_done/on_image_file_done for the previous message content
                    # - emit on_text_created/on_image_created for the new message content
                    if content_delta.index != self._current_message_content_index:
                        if self._current_message_content is not None:
                            if self._current_message_content.type == "text":
                                self.on_text_done(self._current_message_content.text)
                            elif self._current_message_content.type == "image_file":
                                self.on_image_file_done(self._current_message_content.image_file)

                        self._current_message_content_index = content_delta.index
                        self._current_message_content = snapshot.content[content_delta.index]

                    # Update the current_message_content (delta event is correctly emitted already)
                    self._current_message_content = snapshot.content[content_delta.index]

            self.on_message_delta(event.data.delta, snapshot)
        elif event.event == "thread.message.completed" or event.event == "thread.message.incomplete":
            self.__current_message_snapshot = event.data
            self.__message_snapshots[event.data.id] = event.data

            if self._current_message_content_index is not None:
                content = event.data.content[self._current_message_content_index]
                if content.type == "text":
                    self.on_text_done(content.text)
                elif content.type == "image_file":
                    self.on_image_file_done(content.image_file)

            self.on_message_done(event.data)
        elif event.event == "thread.run.step.created":
            self.__current_run_step_id = event.data.id
            self.on_run_step_created(event.data)
        elif event.event == "thread.run.step.in_progress":
            self.__current_run_step_id = event.data.id
        elif event.event == "thread.run.step.delta":
            step_snapshot = self.__run_step_snapshots[event.data.id]

            run_step_delta = event.data.delta
            if (
                run_step_delta.step_details
                and run_step_delta.step_details.type == "tool_calls"
                and run_step_delta.step_details.tool_calls is not None
            ):
                assert step_snapshot.step_details.type == "tool_calls"
                for tool_call_delta in run_step_delta.step_details.tool_calls:
                    if tool_call_delta.index == self._current_tool_call_index:
                        self.on_tool_call_delta(
                            tool_call_delta,
                            step_snapshot.step_details.tool_calls[tool_call_delta.index],
                        )

                    # If the delta is for a new tool call:
                    # - emit on_tool_call_done for the previous tool_call
                    # - emit on_tool_call_created for the new tool_call
                    if tool_call_delta.index != self._current_tool_call_index:
                        if self._current_tool_call is not None:
                            self.on_tool_call_done(self._current_tool_call)

                        self._current_tool_call_index = tool_call_delta.index
                        self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]
                        self.on_tool_call_created(self._current_tool_call)

                    # Update the current_tool_call (delta event is correctly emitted already)
                    self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]

            self.on_run_step_delta(
                event.data.delta,
                step_snapshot,
            )
        elif (
            event.event == "thread.run.step.completed"
            or event.event == "thread.run.step.cancelled"
            or event.event == "thread.run.step.expired"
            or event.event == "thread.run.step.failed"
        ):
            if self._current_tool_call:
                self.on_tool_call_done(self._current_tool_call)

            self.on_run_step_done(event.data)
            self.__current_run_step_id = None
        elif event.event == "thread.created" or event.event == "thread.message.in_progress" or event.event == "error":
            # currently no special handling
            ...
        else:
            # we only want to error at build-time
            if TYPE_CHECKING:  # type: ignore[unreachable]
                assert_never(event)

        self._current_event = None

    def __stream__(self) -> Iterator[AssistantStreamEvent]:
        stream = self.__stream
        if not stream:
            raise RuntimeError("Stream has not been started yet")

        try:
            for event in stream:
                self._emit_sse_event(event)

                yield event
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            self.on_timeout()
            self.on_exception(exc)
            raise
        except Exception as exc:
            self.on_exception(exc)
            raise
        finally:
            self.on_end()


AssistantEventHandlerT = TypeVar("AssistantEventHandlerT", bound=AssistantEventHandler)


class AssistantStreamManager(Generic[AssistantEventHandlerT]):
    """Wrapper over AssistantStreamEventHandler that is returned by `.stream()`
    so that a context manager can be used.

    ```py
    with client.threads.create_and_run_stream(...) as stream:
        for event in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[AssistantStreamEvent]],
        *,
        event_handler: AssistantEventHandlerT,
    ) -> None:
        self.__stream: Stream[AssistantStreamEvent] | None = None
        self.__event_handler = event_handler
        self.__api_request = api_request

    def __enter__(self) -> AssistantEventHandlerT:
        self.__stream = self.__api_request()
        self.__event_handler._init(self.__stream)
        return self.__event_handler

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncAssistantEventHandler:
    text_deltas: AsyncIterable[str]
    """Iterator over just the text deltas in the stream.

    This corresponds to the `thread.message.delta` event
    in the API.

    ```py
    async for text in stream.text_deltas:
        print(text, end="", flush=True)
    print()
    ```
    """

    def __init__(self) -> None:
        self._current_event: AssistantStreamEvent | None = None
        self._current_message_content_index: int | None = None
        self._current_message_content: MessageContent | None = None
        self._current_tool_call_index: int | None = None
        self._current_tool_call: ToolCall | None = None
        self.__current_run_step_id: str | None = None
        self.__current_run: Run | None = None
        self.__run_step_snapshots: dict[str, RunStep] = {}
        self.__message_snapshots: dict[str, Message] = {}
        self.__current_message_snapshot: Message | None = None

        self.text_deltas = self.__text_deltas__()
        self._iterator = self.__stream__()
        self.__stream: AsyncStream[AssistantStreamEvent] | None = None

    def _init(self, stream: AsyncStream[AssistantStreamEvent]) -> None:
        if self.__stream:
            raise RuntimeError(
                "A single event handler cannot be shared between multiple streams; You will need to construct a new event handler instance"
            )

        self.__stream = stream

    async def __anext__(self) -> AssistantStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[AssistantStreamEvent]:
        async for item in self._iterator:
            yield item

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called when the context manager exits.
        """
        if self.__stream:
            await self.__stream.close()

    @property
    def current_event(self) -> AssistantStreamEvent | None:
        return self._current_event

    @property
    def current_run(self) -> Run | None:
        return self.__current_run

    @property
    def current_run_step_snapshot(self) -> RunStep | None:
        if not self.__current_run_step_id:
            return None

        return self.__run_step_snapshots[self.__current_run_step_id]

    @property
    def current_message_snapshot(self) -> Message | None:
        return self.__current_message_snapshot

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    async def get_final_run(self) -> Run:
        """Wait for the stream to finish and returns the completed Run object"""
        await self.until_done()

        if not self.__current_run:
            raise RuntimeError("No final run object found")

        return self.__current_run

    async def get_final_run_steps(self) -> list[RunStep]:
        """Wait for the stream to finish and returns the steps taken in this run"""
        await self.until_done()

        if not self.__run_step_snapshots:
            raise RuntimeError("No run steps found")

        return [step for step in self.__run_step_snapshots.values()]

    async def get_final_messages(self) -> list[Message]:
        """Wait for the stream to finish and returns the messages emitted in this run"""
        await self.until_done()

        if not self.__message_snapshots:
            raise RuntimeError("No messages found")

        return [message for message in self.__message_snapshots.values()]

    async def __text_deltas__(self) -> AsyncIterator[str]:
        async for event in self:
            if event.event != "thread.message.delta":
                continue

            for content_delta in event.data.delta.content or []:
                if content_delta.type == "text" and content_delta.text and content_delta.text.value:
                    yield content_delta.text.value

    # event handlers

    async def on_end(self) -> None:
        """Fires when the stream has finished.

        This happens if the stream is read to completion
        or if an exception occurs during iteration.
        """

    async def on_event(self, event: AssistantStreamEvent) -> None:
        """Callback that is fired for every Server-Sent-Event"""

    async def on_run_step_created(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is created"""

    async def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        """Callback that is fired whenever a run step delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the run step. For example, a tool calls event may
        look like this:

        # delta
        tool_calls=[
            RunStepDeltaToolCallsCodeInterpreter(
                index=0,
                type='code_interpreter',
                id=None,
                code_interpreter=CodeInterpreter(input=' sympy', outputs=None)
            )
        ]
        # snapshot
        tool_calls=[
            CodeToolCall(
                id='call_wKayJlcYV12NiadiZuJXxcfx',
                code_interpreter=CodeInterpreter(input='from sympy', outputs=[]),
                type='code_interpreter',
                index=0
            )
        ],
        """

    async def on_run_step_done(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is completed"""

    async def on_tool_call_created(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call is created"""

    async def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    async def on_tool_call_done(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    async def on_exception(self, exception: Exception) -> None:
        """Fired whenever an exception happens during streaming"""

    async def on_timeout(self) -> None:
        """Fires if the request times out"""

    async def on_message_created(self, message: Message) -> None:
        """Callback that is fired when a message is created"""

    async def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        """Callback that is fired whenever a message delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the message. For example, a text content event may
        look like this:

        # delta
        MessageDeltaText(
            index=0,
            type='text',
            text=Text(
                value=' Jane'
            ),
        )
        # snapshot
        MessageContentText(
            index=0,
            type='text',
            text=Text(
                value='Certainly, Jane'
            ),
        )
        """

    async def on_message_done(self, message: Message) -> None:
        """Callback that is fired when a message is completed"""

    async def on_text_created(self, text: Text) -> None:
        """Callback that is fired when a text content block is created"""

    async def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        """Callback that is fired whenever a text content delta is returned
        by the API.

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the text. For example:

        on_text_delta(TextDelta(value="The"), Text(value="The")),
        on_text_delta(TextDelta(value=" solution"), Text(value="The solution")),
        on_text_delta(TextDelta(value=" to"), Text(value="The solution to")),
        on_text_delta(TextDelta(value=" the"), Text(value="The solution to the")),
        on_text_delta(TextDelta(value=" equation"), Text(value="The solution to the equivalent")),
        """

    async def on_text_done(self, text: Text) -> None:
        """Callback that is fired when a text content block is finished"""

    async def on_image_file_done(self, image_file: ImageFile) -> None:
        """Callback that is fired when an image file block is finished"""

    async def _emit_sse_event(self, event: AssistantStreamEvent) -> None:
        self._current_event = event
        await self.on_event(event)

        self.__current_message_snapshot, new_content = accumulate_event(
            event=event,
            current_message_snapshot=self.__current_message_snapshot,
        )
        if self.__current_message_snapshot is not None:
            self.__message_snapshots[self.__current_message_snapshot.id] = self.__current_message_snapshot

        accumulate_run_step(
            event=event,
            run_step_snapshots=self.__run_step_snapshots,
        )

        for content_delta in new_content:
            assert self.__current_message_snapshot is not None

            block = self.__current_message_snapshot.content[content_delta.index]
            if block.type == "text":
                await self.on_text_created(block.text)

        if (
            event.event == "thread.run.completed"
            or event.event == "thread.run.cancelled"
            or event.event == "thread.run.expired"
            or event.event == "thread.run.failed"
            or event.event == "thread.run.requires_action"
            or event.event == "thread.run.incomplete"
        ):
            self.__current_run = event.data
            if self._current_tool_call:
                await self.on_tool_call_done(self._current_tool_call)
        elif (
            event.event == "thread.run.created"
            or event.event == "thread.run.in_progress"
            or event.event == "thread.run.cancelling"
            or event.event == "thread.run.queued"
        ):
            self.__current_run = event.data
        elif event.event == "thread.message.created":
            await self.on_message_created(event.data)
        elif event.event == "thread.message.delta":
            snapshot = self.__current_message_snapshot
            assert snapshot is not None

            message_delta = event.data.delta
            if message_delta.content is not None:
                for content_delta in message_delta.content:
                    if content_delta.type == "text" and content_delta.text:
                        snapshot_content = snapshot.content[content_delta.index]
                        assert snapshot_content.type == "text"
                        await self.on_text_delta(content_delta.text, snapshot_content.text)

                    # If the delta is for a new message content:
                    # - emit on_text_done/on_image_file_done for the previous message content
                    # - emit on_text_created/on_image_created for the new message content
                    if content_delta.index != self._current_message_content_index:
                        if self._current_message_content is not None:
                            if self._current_message_content.type == "text":
                                await self.on_text_done(self._current_message_content.text)
                            elif self._current_message_content.type == "image_file":
                                await self.on_image_file_done(self._current_message_content.image_file)

                        self._current_message_content_index = content_delta.index
                        self._current_message_content = snapshot.content[content_delta.index]

                    # Update the current_message_content (delta event is correctly emitted already)
                    self._current_message_content = snapshot.content[content_delta.index]

            await self.on_message_delta(event.data.delta, snapshot)
        elif event.event == "thread.message.completed" or event.event == "thread.message.incomplete":
            self.__current_message_snapshot = event.data
            self.__message_snapshots[event.data.id] = event.data

            if self._current_message_content_index is not None:
                content = event.data.content[self._current_message_content_index]
                if content.type == "text":
                    await self.on_text_done(content.text)
                elif content.type == "image_file":
                    await self.on_image_file_done(content.image_file)

            await self.on_message_done(event.data)
        elif event.event == "thread.run.step.created":
            self.__current_run_step_id = event.data.id
            await self.on_run_step_created(event.data)
        elif event.event == "thread.run.step.in_progress":
            self.__current_run_step_id = event.data.id
        elif event.event == "thread.run.step.delta":
            step_snapshot = self.__run_step_snapshots[event.data.id]

            run_step_delta = event.data.delta
            if (
                run_step_delta.step_details
                and run_step_delta.step_details.type == "tool_calls"
                and run_step_delta.step_details.tool_calls is not None
            ):
                assert step_snapshot.step_details.type == "tool_calls"
                for tool_call_delta in run_step_delta.step_details.tool_calls:
                    if tool_call_delta.index == self._current_tool_call_index:
                        await self.on_tool_call_delta(
                            tool_call_delta,
                            step_snapshot.step_details.tool_calls[tool_call_delta.index],
                        )

                    # If the delta is for a new tool call:
                    # - emit on_tool_call_done for the previous tool_call
                    # - emit on_tool_call_created for the new tool_call
                    if tool_call_delta.index != self._current_tool_call_index:
                        if self._current_tool_call is not None:
                            await self.on_tool_call_done(self._current_tool_call)

                        self._current_tool_call_index = tool_call_delta.index
                        self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]
                        await self.on_tool_call_created(self._current_tool_call)

                    # Update the current_tool_call (delta event is correctly emitted already)
                    self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]

            await self.on_run_step_delta(
                event.data.delta,
                step_snapshot,
            )
        elif (
            event.event == "thread.run.step.completed"
            or event.event == "thread.run.step.cancelled"
            or event.event == "thread.run.step.expired"
            or event.event == "thread.run.step.failed"
        ):
            if self._current_tool_call:
                await self.on_tool_call_done(self._current_tool_call)

            await self.on_run_step_done(event.data)
            self.__current_run_step_id = None
        elif event.event == "thread.created" or event.event == "thread.message.in_progress" or event.event == "error":
            # currently no special handling
            ...
        else:
            # we only want to error at build-time
            if TYPE_CHECKING:  # type: ignore[unreachable]
                assert_never(event)

        self._current_event = None

    async def __stream__(self) -> AsyncIterator[AssistantStreamEvent]:
        stream = self.__stream
        if not stream:
            raise RuntimeError("Stream has not been started yet")

        try:
            async for event in stream:
                await self._emit_sse_event(event)

                yield event
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            await self.on_timeout()
            await self.on_exception(exc)
            raise
        except Exception as exc:
            await self.on_exception(exc)
            raise
        finally:
            await self.on_end()


AsyncAssistantEventHandlerT = TypeVar("AsyncAssistantEventHandlerT", bound=AsyncAssistantEventHandler)


class AsyncAssistantStreamManager(Generic[AsyncAssistantEventHandlerT]):
    """Wrapper over AsyncAssistantStreamEventHandler that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.threads.create_and_run_stream(...) as stream:
        async for event in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[AssistantStreamEvent]],
        *,
        event_handler: AsyncAssistantEventHandlerT,
    ) -> None:
        self.__stream: AsyncStream[AssistantStreamEvent] | None = None
        self.__event_handler = event_handler
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncAssistantEventHandlerT:
        self.__stream = await self.__api_request
        self.__event_handler._init(self.__stream)
        return self.__event_handler

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def accumulate_run_step(
    *,
    event: AssistantStreamEvent,
    run_step_snapshots: dict[str, RunStep],
) -> None:
    if event.event == "thread.run.step.created":
        run_step_snapshots[event.data.id] = event.data
        return

    if event.event == "thread.run.step.delta":
        data = event.data
        snapshot = run_step_snapshots[data.id]

        if data.delta:
            merged = accumulate_delta(
                cast(
                    "dict[object, object]",
                    model_dump(snapshot, exclude_unset=True, warnings=False),
                ),
                cast(
                    "dict[object, object]",
                    model_dump(data.delta, exclude_unset=True, warnings=False),
                ),
            )
            run_step_snapshots[snapshot.id] = cast(RunStep, construct_type(type_=RunStep, value=merged))

    return None


def accumulate_event(
    *,
    event: AssistantStreamEvent,
    current_message_snapshot: Message | None,
) -> tuple[Message | None, list[MessageContentDelta]]:
    """Returns a tuple of message snapshot and newly created text message deltas"""
    if event.event == "thread.message.created":
        return event.data, []

    new_content: list[MessageContentDelta] = []

    if event.event != "thread.message.delta":
        return current_message_snapshot, []

    if not current_message_snapshot:
        raise RuntimeError("Encountered a message delta with no previous snapshot")

    data = event.data
    if data.delta.content:
        for content_delta in data.delta.content:
            try:
                block = current_message_snapshot.content[content_delta.index]
            except IndexError:
                current_message_snapshot.content.insert(
                    content_delta.index,
                    cast(
                        MessageContent,
                        construct_type(
                            # mypy doesn't allow Content for some reason
                            type_=cast(Any, MessageContent),
                            value=model_dump(content_delta, exclude_unset=True, warnings=False),
                        ),
                    ),
                )
                new_content.append(content_delta)
            else:
                merged = accumulate_delta(
                    cast(
                        "dict[object, object]",
                        model_dump(block, exclude_unset=True, warnings=False),
                    ),
                    cast(
                        "dict[object, object]",
                        model_dump(content_delta, exclude_unset=True, warnings=False),
                    ),
                )
                current_message_snapshot.content[content_delta.index] = cast(
                    MessageContent,
                    construct_type(
                        # mypy doesn't allow Content for some reason
                        type_=cast(Any, MessageContent),
                        value=merged,
                    ),
                )

    return current_message_snapshot, new_content


def accumulate_delta(acc: dict[object, object], delta: dict[object, object]) -> dict[object, object]:
    for key, delta_value in delta.items():
        if key not in acc:
            acc[key] = delta_value
            continue

        acc_value = acc[key]
        if acc_value is None:
            acc[key] = delta_value
            continue

        # the `index` property is used in arrays of objects so it should
        # not be accumulated like other values e.g.
        # [{'foo': 'bar', 'index': 0}]
        #
        # the same applies to `type` properties as they're used for
        # discriminated unions
        if key == "index" or key == "type":
            acc[key] = delta_value
            continue

        if isinstance(acc_value, str) and isinstance(delta_value, str):
            acc_value += delta_value
        elif isinstance(acc_value, (int, float)) and isinstance(delta_value, (int, float)):
            acc_value += delta_value
        elif is_dict(acc_value) and is_dict(delta_value):
            acc_value = accumulate_delta(acc_value, delta_value)
        elif is_list(acc_value) and is_list(delta_value):
            # for lists of non-dictionary items we'll only ever get new entries
            # in the array, existing entries will never be changed
            if all(isinstance(x, (str, int, float)) for x in acc_value):
                acc_value.extend(delta_value)
                continue

            for delta_entry in delta_value:
                if not is_dict(delta_entry):
                    raise TypeError(f"Unexpected list delta entry is not a dictionary: {delta_entry}")

                try:
                    index = delta_entry["index"]
                except KeyError as exc:
                    raise RuntimeError(f"Expected list delta entry to have an `index` key; {delta_entry}") from exc

                if not isinstance(index, int):
                    raise TypeError(f"Unexpected, list delta entry `index` value is not an integer; {index}")

                try:
                    acc_entry = acc_value[index]
                except IndexError:
                    acc_value.insert(index, delta_entry)
                else:
                    if not is_dict(acc_entry):
                        raise TypeError("not handled yet")

                    acc_value[index] = accumulate_delta(acc_entry, delta_entry)

        acc[key] = acc_value

    return acc

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\openai\lib\streaming\_assistants.py ===
from __future__ import annotations

import asyncio
from types import TracebackType
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Callable, Iterable, Iterator, cast
from typing_extensions import Awaitable, AsyncIterable, AsyncIterator, assert_never

import httpx

from ..._utils import is_dict, is_list, consume_sync_iterator, consume_async_iterator
from ..._compat import model_dump
from ..._models import construct_type
from ..._streaming import Stream, AsyncStream
from ...types.beta import AssistantStreamEvent
from ...types.beta.threads import (
    Run,
    Text,
    Message,
    ImageFile,
    TextDelta,
    MessageDelta,
    MessageContent,
    MessageContentDelta,
)
from ...types.beta.threads.runs import RunStep, ToolCall, RunStepDelta, ToolCallDelta


class AssistantEventHandler:
    text_deltas: Iterable[str]
    """Iterator over just the text deltas in the stream.

    This corresponds to the `thread.message.delta` event
    in the API.

    ```py
    for text in stream.text_deltas:
        print(text, end="", flush=True)
    print()
    ```
    """

    def __init__(self) -> None:
        self._current_event: AssistantStreamEvent | None = None
        self._current_message_content_index: int | None = None
        self._current_message_content: MessageContent | None = None
        self._current_tool_call_index: int | None = None
        self._current_tool_call: ToolCall | None = None
        self.__current_run_step_id: str | None = None
        self.__current_run: Run | None = None
        self.__run_step_snapshots: dict[str, RunStep] = {}
        self.__message_snapshots: dict[str, Message] = {}
        self.__current_message_snapshot: Message | None = None

        self.text_deltas = self.__text_deltas__()
        self._iterator = self.__stream__()
        self.__stream: Stream[AssistantStreamEvent] | None = None

    def _init(self, stream: Stream[AssistantStreamEvent]) -> None:
        if self.__stream:
            raise RuntimeError(
                "A single event handler cannot be shared between multiple streams; You will need to construct a new event handler instance"
            )

        self.__stream = stream

    def __next__(self) -> AssistantStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[AssistantStreamEvent]:
        for item in self._iterator:
            yield item

    @property
    def current_event(self) -> AssistantStreamEvent | None:
        return self._current_event

    @property
    def current_run(self) -> Run | None:
        return self.__current_run

    @property
    def current_run_step_snapshot(self) -> RunStep | None:
        if not self.__current_run_step_id:
            return None

        return self.__run_step_snapshots[self.__current_run_step_id]

    @property
    def current_message_snapshot(self) -> Message | None:
        return self.__current_message_snapshot

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called when the context manager exits.
        """
        if self.__stream:
            self.__stream.close()

    def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        consume_sync_iterator(self)

    def get_final_run(self) -> Run:
        """Wait for the stream to finish and returns the completed Run object"""
        self.until_done()

        if not self.__current_run:
            raise RuntimeError("No final run object found")

        return self.__current_run

    def get_final_run_steps(self) -> list[RunStep]:
        """Wait for the stream to finish and returns the steps taken in this run"""
        self.until_done()

        if not self.__run_step_snapshots:
            raise RuntimeError("No run steps found")

        return [step for step in self.__run_step_snapshots.values()]

    def get_final_messages(self) -> list[Message]:
        """Wait for the stream to finish and returns the messages emitted in this run"""
        self.until_done()

        if not self.__message_snapshots:
            raise RuntimeError("No messages found")

        return [message for message in self.__message_snapshots.values()]

    def __text_deltas__(self) -> Iterator[str]:
        for event in self:
            if event.event != "thread.message.delta":
                continue

            for content_delta in event.data.delta.content or []:
                if content_delta.type == "text" and content_delta.text and content_delta.text.value:
                    yield content_delta.text.value

    # event handlers

    def on_end(self) -> None:
        """Fires when the stream has finished.

        This happens if the stream is read to completion
        or if an exception occurs during iteration.
        """

    def on_event(self, event: AssistantStreamEvent) -> None:
        """Callback that is fired for every Server-Sent-Event"""

    def on_run_step_created(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is created"""

    def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        """Callback that is fired whenever a run step delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the run step. For example, a tool calls event may
        look like this:

        # delta
        tool_calls=[
            RunStepDeltaToolCallsCodeInterpreter(
                index=0,
                type='code_interpreter',
                id=None,
                code_interpreter=CodeInterpreter(input=' sympy', outputs=None)
            )
        ]
        # snapshot
        tool_calls=[
            CodeToolCall(
                id='call_wKayJlcYV12NiadiZuJXxcfx',
                code_interpreter=CodeInterpreter(input='from sympy', outputs=[]),
                type='code_interpreter',
                index=0
            )
        ],
        """

    def on_run_step_done(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is completed"""

    def on_tool_call_created(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call is created"""

    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    def on_tool_call_done(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    def on_exception(self, exception: Exception) -> None:
        """Fired whenever an exception happens during streaming"""

    def on_timeout(self) -> None:
        """Fires if the request times out"""

    def on_message_created(self, message: Message) -> None:
        """Callback that is fired when a message is created"""

    def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        """Callback that is fired whenever a message delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the message. For example, a text content event may
        look like this:

        # delta
        MessageDeltaText(
            index=0,
            type='text',
            text=Text(
                value=' Jane'
            ),
        )
        # snapshot
        MessageContentText(
            index=0,
            type='text',
            text=Text(
                value='Certainly, Jane'
            ),
        )
        """

    def on_message_done(self, message: Message) -> None:
        """Callback that is fired when a message is completed"""

    def on_text_created(self, text: Text) -> None:
        """Callback that is fired when a text content block is created"""

    def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        """Callback that is fired whenever a text content delta is returned
        by the API.

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the text. For example:

        on_text_delta(TextDelta(value="The"), Text(value="The")),
        on_text_delta(TextDelta(value=" solution"), Text(value="The solution")),
        on_text_delta(TextDelta(value=" to"), Text(value="The solution to")),
        on_text_delta(TextDelta(value=" the"), Text(value="The solution to the")),
        on_text_delta(TextDelta(value=" equation"), Text(value="The solution to the equation")),
        """

    def on_text_done(self, text: Text) -> None:
        """Callback that is fired when a text content block is finished"""

    def on_image_file_done(self, image_file: ImageFile) -> None:
        """Callback that is fired when an image file block is finished"""

    def _emit_sse_event(self, event: AssistantStreamEvent) -> None:
        self._current_event = event
        self.on_event(event)

        self.__current_message_snapshot, new_content = accumulate_event(
            event=event,
            current_message_snapshot=self.__current_message_snapshot,
        )
        if self.__current_message_snapshot is not None:
            self.__message_snapshots[self.__current_message_snapshot.id] = self.__current_message_snapshot

        accumulate_run_step(
            event=event,
            run_step_snapshots=self.__run_step_snapshots,
        )

        for content_delta in new_content:
            assert self.__current_message_snapshot is not None

            block = self.__current_message_snapshot.content[content_delta.index]
            if block.type == "text":
                self.on_text_created(block.text)

        if (
            event.event == "thread.run.completed"
            or event.event == "thread.run.cancelled"
            or event.event == "thread.run.expired"
            or event.event == "thread.run.failed"
            or event.event == "thread.run.requires_action"
            or event.event == "thread.run.incomplete"
        ):
            self.__current_run = event.data
            if self._current_tool_call:
                self.on_tool_call_done(self._current_tool_call)
        elif (
            event.event == "thread.run.created"
            or event.event == "thread.run.in_progress"
            or event.event == "thread.run.cancelling"
            or event.event == "thread.run.queued"
        ):
            self.__current_run = event.data
        elif event.event == "thread.message.created":
            self.on_message_created(event.data)
        elif event.event == "thread.message.delta":
            snapshot = self.__current_message_snapshot
            assert snapshot is not None

            message_delta = event.data.delta
            if message_delta.content is not None:
                for content_delta in message_delta.content:
                    if content_delta.type == "text" and content_delta.text:
                        snapshot_content = snapshot.content[content_delta.index]
                        assert snapshot_content.type == "text"
                        self.on_text_delta(content_delta.text, snapshot_content.text)

                    # If the delta is for a new message content:
                    # - emit on_text_done/on_image_file_done for the previous message content
                    # - emit on_text_created/on_image_created for the new message content
                    if content_delta.index != self._current_message_content_index:
                        if self._current_message_content is not None:
                            if self._current_message_content.type == "text":
                                self.on_text_done(self._current_message_content.text)
                            elif self._current_message_content.type == "image_file":
                                self.on_image_file_done(self._current_message_content.image_file)

                        self._current_message_content_index = content_delta.index
                        self._current_message_content = snapshot.content[content_delta.index]

                    # Update the current_message_content (delta event is correctly emitted already)
                    self._current_message_content = snapshot.content[content_delta.index]

            self.on_message_delta(event.data.delta, snapshot)
        elif event.event == "thread.message.completed" or event.event == "thread.message.incomplete":
            self.__current_message_snapshot = event.data
            self.__message_snapshots[event.data.id] = event.data

            if self._current_message_content_index is not None:
                content = event.data.content[self._current_message_content_index]
                if content.type == "text":
                    self.on_text_done(content.text)
                elif content.type == "image_file":
                    self.on_image_file_done(content.image_file)

            self.on_message_done(event.data)
        elif event.event == "thread.run.step.created":
            self.__current_run_step_id = event.data.id
            self.on_run_step_created(event.data)
        elif event.event == "thread.run.step.in_progress":
            self.__current_run_step_id = event.data.id
        elif event.event == "thread.run.step.delta":
            step_snapshot = self.__run_step_snapshots[event.data.id]

            run_step_delta = event.data.delta
            if (
                run_step_delta.step_details
                and run_step_delta.step_details.type == "tool_calls"
                and run_step_delta.step_details.tool_calls is not None
            ):
                assert step_snapshot.step_details.type == "tool_calls"
                for tool_call_delta in run_step_delta.step_details.tool_calls:
                    if tool_call_delta.index == self._current_tool_call_index:
                        self.on_tool_call_delta(
                            tool_call_delta,
                            step_snapshot.step_details.tool_calls[tool_call_delta.index],
                        )

                    # If the delta is for a new tool call:
                    # - emit on_tool_call_done for the previous tool_call
                    # - emit on_tool_call_created for the new tool_call
                    if tool_call_delta.index != self._current_tool_call_index:
                        if self._current_tool_call is not None:
                            self.on_tool_call_done(self._current_tool_call)

                        self._current_tool_call_index = tool_call_delta.index
                        self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]
                        self.on_tool_call_created(self._current_tool_call)

                    # Update the current_tool_call (delta event is correctly emitted already)
                    self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]

            self.on_run_step_delta(
                event.data.delta,
                step_snapshot,
            )
        elif (
            event.event == "thread.run.step.completed"
            or event.event == "thread.run.step.cancelled"
            or event.event == "thread.run.step.expired"
            or event.event == "thread.run.step.failed"
        ):
            if self._current_tool_call:
                self.on_tool_call_done(self._current_tool_call)

            self.on_run_step_done(event.data)
            self.__current_run_step_id = None
        elif event.event == "thread.created" or event.event == "thread.message.in_progress" or event.event == "error":
            # currently no special handling
            ...
        else:
            # we only want to error at build-time
            if TYPE_CHECKING:  # type: ignore[unreachable]
                assert_never(event)

        self._current_event = None

    def __stream__(self) -> Iterator[AssistantStreamEvent]:
        stream = self.__stream
        if not stream:
            raise RuntimeError("Stream has not been started yet")

        try:
            for event in stream:
                self._emit_sse_event(event)

                yield event
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            self.on_timeout()
            self.on_exception(exc)
            raise
        except Exception as exc:
            self.on_exception(exc)
            raise
        finally:
            self.on_end()


AssistantEventHandlerT = TypeVar("AssistantEventHandlerT", bound=AssistantEventHandler)


class AssistantStreamManager(Generic[AssistantEventHandlerT]):
    """Wrapper over AssistantStreamEventHandler that is returned by `.stream()`
    so that a context manager can be used.

    ```py
    with client.threads.create_and_run_stream(...) as stream:
        for event in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[AssistantStreamEvent]],
        *,
        event_handler: AssistantEventHandlerT,
    ) -> None:
        self.__stream: Stream[AssistantStreamEvent] | None = None
        self.__event_handler = event_handler
        self.__api_request = api_request

    def __enter__(self) -> AssistantEventHandlerT:
        self.__stream = self.__api_request()
        self.__event_handler._init(self.__stream)
        return self.__event_handler

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncAssistantEventHandler:
    text_deltas: AsyncIterable[str]
    """Iterator over just the text deltas in the stream.

    This corresponds to the `thread.message.delta` event
    in the API.

    ```py
    async for text in stream.text_deltas:
        print(text, end="", flush=True)
    print()
    ```
    """

    def __init__(self) -> None:
        self._current_event: AssistantStreamEvent | None = None
        self._current_message_content_index: int | None = None
        self._current_message_content: MessageContent | None = None
        self._current_tool_call_index: int | None = None
        self._current_tool_call: ToolCall | None = None
        self.__current_run_step_id: str | None = None
        self.__current_run: Run | None = None
        self.__run_step_snapshots: dict[str, RunStep] = {}
        self.__message_snapshots: dict[str, Message] = {}
        self.__current_message_snapshot: Message | None = None

        self.text_deltas = self.__text_deltas__()
        self._iterator = self.__stream__()
        self.__stream: AsyncStream[AssistantStreamEvent] | None = None

    def _init(self, stream: AsyncStream[AssistantStreamEvent]) -> None:
        if self.__stream:
            raise RuntimeError(
                "A single event handler cannot be shared between multiple streams; You will need to construct a new event handler instance"
            )

        self.__stream = stream

    async def __anext__(self) -> AssistantStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[AssistantStreamEvent]:
        async for item in self._iterator:
            yield item

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called when the context manager exits.
        """
        if self.__stream:
            await self.__stream.close()

    @property
    def current_event(self) -> AssistantStreamEvent | None:
        return self._current_event

    @property
    def current_run(self) -> Run | None:
        return self.__current_run

    @property
    def current_run_step_snapshot(self) -> RunStep | None:
        if not self.__current_run_step_id:
            return None

        return self.__run_step_snapshots[self.__current_run_step_id]

    @property
    def current_message_snapshot(self) -> Message | None:
        return self.__current_message_snapshot

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    async def get_final_run(self) -> Run:
        """Wait for the stream to finish and returns the completed Run object"""
        await self.until_done()

        if not self.__current_run:
            raise RuntimeError("No final run object found")

        return self.__current_run

    async def get_final_run_steps(self) -> list[RunStep]:
        """Wait for the stream to finish and returns the steps taken in this run"""
        await self.until_done()

        if not self.__run_step_snapshots:
            raise RuntimeError("No run steps found")

        return [step for step in self.__run_step_snapshots.values()]

    async def get_final_messages(self) -> list[Message]:
        """Wait for the stream to finish and returns the messages emitted in this run"""
        await self.until_done()

        if not self.__message_snapshots:
            raise RuntimeError("No messages found")

        return [message for message in self.__message_snapshots.values()]

    async def __text_deltas__(self) -> AsyncIterator[str]:
        async for event in self:
            if event.event != "thread.message.delta":
                continue

            for content_delta in event.data.delta.content or []:
                if content_delta.type == "text" and content_delta.text and content_delta.text.value:
                    yield content_delta.text.value

    # event handlers

    async def on_end(self) -> None:
        """Fires when the stream has finished.

        This happens if the stream is read to completion
        or if an exception occurs during iteration.
        """

    async def on_event(self, event: AssistantStreamEvent) -> None:
        """Callback that is fired for every Server-Sent-Event"""

    async def on_run_step_created(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is created"""

    async def on_run_step_delta(self, delta: RunStepDelta, snapshot: RunStep) -> None:
        """Callback that is fired whenever a run step delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the run step. For example, a tool calls event may
        look like this:

        # delta
        tool_calls=[
            RunStepDeltaToolCallsCodeInterpreter(
                index=0,
                type='code_interpreter',
                id=None,
                code_interpreter=CodeInterpreter(input=' sympy', outputs=None)
            )
        ]
        # snapshot
        tool_calls=[
            CodeToolCall(
                id='call_wKayJlcYV12NiadiZuJXxcfx',
                code_interpreter=CodeInterpreter(input='from sympy', outputs=[]),
                type='code_interpreter',
                index=0
            )
        ],
        """

    async def on_run_step_done(self, run_step: RunStep) -> None:
        """Callback that is fired when a run step is completed"""

    async def on_tool_call_created(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call is created"""

    async def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    async def on_tool_call_done(self, tool_call: ToolCall) -> None:
        """Callback that is fired when a tool call delta is encountered"""

    async def on_exception(self, exception: Exception) -> None:
        """Fired whenever an exception happens during streaming"""

    async def on_timeout(self) -> None:
        """Fires if the request times out"""

    async def on_message_created(self, message: Message) -> None:
        """Callback that is fired when a message is created"""

    async def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        """Callback that is fired whenever a message delta is returned from the API

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the message. For example, a text content event may
        look like this:

        # delta
        MessageDeltaText(
            index=0,
            type='text',
            text=Text(
                value=' Jane'
            ),
        )
        # snapshot
        MessageContentText(
            index=0,
            type='text',
            text=Text(
                value='Certainly, Jane'
            ),
        )
        """

    async def on_message_done(self, message: Message) -> None:
        """Callback that is fired when a message is completed"""

    async def on_text_created(self, text: Text) -> None:
        """Callback that is fired when a text content block is created"""

    async def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        """Callback that is fired whenever a text content delta is returned
        by the API.

        The first argument is just the delta as sent by the API and the second argument
        is the accumulated snapshot of the text. For example:

        on_text_delta(TextDelta(value="The"), Text(value="The")),
        on_text_delta(TextDelta(value=" solution"), Text(value="The solution")),
        on_text_delta(TextDelta(value=" to"), Text(value="The solution to")),
        on_text_delta(TextDelta(value=" the"), Text(value="The solution to the")),
        on_text_delta(TextDelta(value=" equation"), Text(value="The solution to the equivalent")),
        """

    async def on_text_done(self, text: Text) -> None:
        """Callback that is fired when a text content block is finished"""

    async def on_image_file_done(self, image_file: ImageFile) -> None:
        """Callback that is fired when an image file block is finished"""

    async def _emit_sse_event(self, event: AssistantStreamEvent) -> None:
        self._current_event = event
        await self.on_event(event)

        self.__current_message_snapshot, new_content = accumulate_event(
            event=event,
            current_message_snapshot=self.__current_message_snapshot,
        )
        if self.__current_message_snapshot is not None:
            self.__message_snapshots[self.__current_message_snapshot.id] = self.__current_message_snapshot

        accumulate_run_step(
            event=event,
            run_step_snapshots=self.__run_step_snapshots,
        )

        for content_delta in new_content:
            assert self.__current_message_snapshot is not None

            block = self.__current_message_snapshot.content[content_delta.index]
            if block.type == "text":
                await self.on_text_created(block.text)

        if (
            event.event == "thread.run.completed"
            or event.event == "thread.run.cancelled"
            or event.event == "thread.run.expired"
            or event.event == "thread.run.failed"
            or event.event == "thread.run.requires_action"
            or event.event == "thread.run.incomplete"
        ):
            self.__current_run = event.data
            if self._current_tool_call:
                await self.on_tool_call_done(self._current_tool_call)
        elif (
            event.event == "thread.run.created"
            or event.event == "thread.run.in_progress"
            or event.event == "thread.run.cancelling"
            or event.event == "thread.run.queued"
        ):
            self.__current_run = event.data
        elif event.event == "thread.message.created":
            await self.on_message_created(event.data)
        elif event.event == "thread.message.delta":
            snapshot = self.__current_message_snapshot
            assert snapshot is not None

            message_delta = event.data.delta
            if message_delta.content is not None:
                for content_delta in message_delta.content:
                    if content_delta.type == "text" and content_delta.text:
                        snapshot_content = snapshot.content[content_delta.index]
                        assert snapshot_content.type == "text"
                        await self.on_text_delta(content_delta.text, snapshot_content.text)

                    # If the delta is for a new message content:
                    # - emit on_text_done/on_image_file_done for the previous message content
                    # - emit on_text_created/on_image_created for the new message content
                    if content_delta.index != self._current_message_content_index:
                        if self._current_message_content is not None:
                            if self._current_message_content.type == "text":
                                await self.on_text_done(self._current_message_content.text)
                            elif self._current_message_content.type == "image_file":
                                await self.on_image_file_done(self._current_message_content.image_file)

                        self._current_message_content_index = content_delta.index
                        self._current_message_content = snapshot.content[content_delta.index]

                    # Update the current_message_content (delta event is correctly emitted already)
                    self._current_message_content = snapshot.content[content_delta.index]

            await self.on_message_delta(event.data.delta, snapshot)
        elif event.event == "thread.message.completed" or event.event == "thread.message.incomplete":
            self.__current_message_snapshot = event.data
            self.__message_snapshots[event.data.id] = event.data

            if self._current_message_content_index is not None:
                content = event.data.content[self._current_message_content_index]
                if content.type == "text":
                    await self.on_text_done(content.text)
                elif content.type == "image_file":
                    await self.on_image_file_done(content.image_file)

            await self.on_message_done(event.data)
        elif event.event == "thread.run.step.created":
            self.__current_run_step_id = event.data.id
            await self.on_run_step_created(event.data)
        elif event.event == "thread.run.step.in_progress":
            self.__current_run_step_id = event.data.id
        elif event.event == "thread.run.step.delta":
            step_snapshot = self.__run_step_snapshots[event.data.id]

            run_step_delta = event.data.delta
            if (
                run_step_delta.step_details
                and run_step_delta.step_details.type == "tool_calls"
                and run_step_delta.step_details.tool_calls is not None
            ):
                assert step_snapshot.step_details.type == "tool_calls"
                for tool_call_delta in run_step_delta.step_details.tool_calls:
                    if tool_call_delta.index == self._current_tool_call_index:
                        await self.on_tool_call_delta(
                            tool_call_delta,
                            step_snapshot.step_details.tool_calls[tool_call_delta.index],
                        )

                    # If the delta is for a new tool call:
                    # - emit on_tool_call_done for the previous tool_call
                    # - emit on_tool_call_created for the new tool_call
                    if tool_call_delta.index != self._current_tool_call_index:
                        if self._current_tool_call is not None:
                            await self.on_tool_call_done(self._current_tool_call)

                        self._current_tool_call_index = tool_call_delta.index
                        self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]
                        await self.on_tool_call_created(self._current_tool_call)

                    # Update the current_tool_call (delta event is correctly emitted already)
                    self._current_tool_call = step_snapshot.step_details.tool_calls[tool_call_delta.index]

            await self.on_run_step_delta(
                event.data.delta,
                step_snapshot,
            )
        elif (
            event.event == "thread.run.step.completed"
            or event.event == "thread.run.step.cancelled"
            or event.event == "thread.run.step.expired"
            or event.event == "thread.run.step.failed"
        ):
            if self._current_tool_call:
                await self.on_tool_call_done(self._current_tool_call)

            await self.on_run_step_done(event.data)
            self.__current_run_step_id = None
        elif event.event == "thread.created" or event.event == "thread.message.in_progress" or event.event == "error":
            # currently no special handling
            ...
        else:
            # we only want to error at build-time
            if TYPE_CHECKING:  # type: ignore[unreachable]
                assert_never(event)

        self._current_event = None

    async def __stream__(self) -> AsyncIterator[AssistantStreamEvent]:
        stream = self.__stream
        if not stream:
            raise RuntimeError("Stream has not been started yet")

        try:
            async for event in stream:
                await self._emit_sse_event(event)

                yield event
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            await self.on_timeout()
            await self.on_exception(exc)
            raise
        except Exception as exc:
            await self.on_exception(exc)
            raise
        finally:
            await self.on_end()


AsyncAssistantEventHandlerT = TypeVar("AsyncAssistantEventHandlerT", bound=AsyncAssistantEventHandler)


class AsyncAssistantStreamManager(Generic[AsyncAssistantEventHandlerT]):
    """Wrapper over AsyncAssistantStreamEventHandler that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.threads.create_and_run_stream(...) as stream:
        async for event in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[AssistantStreamEvent]],
        *,
        event_handler: AsyncAssistantEventHandlerT,
    ) -> None:
        self.__stream: AsyncStream[AssistantStreamEvent] | None = None
        self.__event_handler = event_handler
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncAssistantEventHandlerT:
        self.__stream = await self.__api_request
        self.__event_handler._init(self.__stream)
        return self.__event_handler

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def accumulate_run_step(
    *,
    event: AssistantStreamEvent,
    run_step_snapshots: dict[str, RunStep],
) -> None:
    if event.event == "thread.run.step.created":
        run_step_snapshots[event.data.id] = event.data
        return

    if event.event == "thread.run.step.delta":
        data = event.data
        snapshot = run_step_snapshots[data.id]

        if data.delta:
            merged = accumulate_delta(
                cast(
                    "dict[object, object]",
                    model_dump(snapshot, exclude_unset=True, warnings=False),
                ),
                cast(
                    "dict[object, object]",
                    model_dump(data.delta, exclude_unset=True, warnings=False),
                ),
            )
            run_step_snapshots[snapshot.id] = cast(RunStep, construct_type(type_=RunStep, value=merged))

    return None


def accumulate_event(
    *,
    event: AssistantStreamEvent,
    current_message_snapshot: Message | None,
) -> tuple[Message | None, list[MessageContentDelta]]:
    """Returns a tuple of message snapshot and newly created text message deltas"""
    if event.event == "thread.message.created":
        return event.data, []

    new_content: list[MessageContentDelta] = []

    if event.event != "thread.message.delta":
        return current_message_snapshot, []

    if not current_message_snapshot:
        raise RuntimeError("Encountered a message delta with no previous snapshot")

    data = event.data
    if data.delta.content:
        for content_delta in data.delta.content:
            try:
                block = current_message_snapshot.content[content_delta.index]
            except IndexError:
                current_message_snapshot.content.insert(
                    content_delta.index,
                    cast(
                        MessageContent,
                        construct_type(
                            # mypy doesn't allow Content for some reason
                            type_=cast(Any, MessageContent),
                            value=model_dump(content_delta, exclude_unset=True, warnings=False),
                        ),
                    ),
                )
                new_content.append(content_delta)
            else:
                merged = accumulate_delta(
                    cast(
                        "dict[object, object]",
                        model_dump(block, exclude_unset=True, warnings=False),
                    ),
                    cast(
                        "dict[object, object]",
                        model_dump(content_delta, exclude_unset=True, warnings=False),
                    ),
                )
                current_message_snapshot.content[content_delta.index] = cast(
                    MessageContent,
                    construct_type(
                        # mypy doesn't allow Content for some reason
                        type_=cast(Any, MessageContent),
                        value=merged,
                    ),
                )

    return current_message_snapshot, new_content


def accumulate_delta(acc: dict[object, object], delta: dict[object, object]) -> dict[object, object]:
    for key, delta_value in delta.items():
        if key not in acc:
            acc[key] = delta_value
            continue

        acc_value = acc[key]
        if acc_value is None:
            acc[key] = delta_value
            continue

        # the `index` property is used in arrays of objects so it should
        # not be accumulated like other values e.g.
        # [{'foo': 'bar', 'index': 0}]
        #
        # the same applies to `type` properties as they're used for
        # discriminated unions
        if key == "index" or key == "type":
            acc[key] = delta_value
            continue

        if isinstance(acc_value, str) and isinstance(delta_value, str):
            acc_value += delta_value
        elif isinstance(acc_value, (int, float)) and isinstance(delta_value, (int, float)):
            acc_value += delta_value
        elif is_dict(acc_value) and is_dict(delta_value):
            acc_value = accumulate_delta(acc_value, delta_value)
        elif is_list(acc_value) and is_list(delta_value):
            # for lists of non-dictionary items we'll only ever get new entries
            # in the array, existing entries will never be changed
            if all(isinstance(x, (str, int, float)) for x in acc_value):
                acc_value.extend(delta_value)
                continue

            for delta_entry in delta_value:
                if not is_dict(delta_entry):
                    raise TypeError(f"Unexpected list delta entry is not a dictionary: {delta_entry}")

                try:
                    index = delta_entry["index"]
                except KeyError as exc:
                    raise RuntimeError(f"Expected list delta entry to have an `index` key; {delta_entry}") from exc

                if not isinstance(index, int):
                    raise TypeError(f"Unexpected, list delta entry `index` value is not an integer; {index}")

                try:
                    acc_entry = acc_value[index]
                except IndexError:
                    acc_value.insert(index, delta_entry)
                else:
                    if not is_dict(acc_entry):
                        raise TypeError("not handled yet")

                    acc_value[index] = accumulate_delta(acc_entry, delta_entry)

        acc[key] = acc_value

    return acc

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_format_impl.py ===
"""
Binary serialization

NPY format
==========

A simple format for saving numpy arrays to disk with the full
information about them.

The ``.npy`` format is the standard binary file format in NumPy for
persisting a *single* arbitrary NumPy array on disk. The format stores all
of the shape and dtype information necessary to reconstruct the array
correctly even on another machine with a different architecture.
The format is designed to be as simple as possible while achieving
its limited goals.

The ``.npz`` format is the standard format for persisting *multiple* NumPy
arrays on disk. A ``.npz`` file is a zip file containing multiple ``.npy``
files, one for each array.

Capabilities
------------

- Can represent all NumPy arrays including nested record arrays and
  object arrays.

- Represents the data in its native binary form.

- Supports Fortran-contiguous arrays directly.

- Stores all of the necessary information to reconstruct the array
  including shape and dtype on a machine of a different
  architecture.  Both little-endian and big-endian arrays are
  supported, and a file with little-endian numbers will yield
  a little-endian array on any machine reading the file. The
  types are described in terms of their actual sizes. For example,
  if a machine with a 64-bit C "long int" writes out an array with
  "long ints", a reading machine with 32-bit C "long ints" will yield
  an array with 64-bit integers.

- Is straightforward to reverse engineer. Datasets often live longer than
  the programs that created them. A competent developer should be
  able to create a solution in their preferred programming language to
  read most ``.npy`` files that they have been given without much
  documentation.

- Allows memory-mapping of the data. See `open_memmap`.

- Can be read from a filelike stream object instead of an actual file.

- Stores object arrays, i.e. arrays containing elements that are arbitrary
  Python objects. Files with object arrays are not to be mmapable, but
  can be read and written to disk.

Limitations
-----------

- Arbitrary subclasses of numpy.ndarray are not completely preserved.
  Subclasses will be accepted for writing, but only the array data will
  be written out. A regular numpy.ndarray object will be created
  upon reading the file.

.. warning::

  Due to limitations in the interpretation of structured dtypes, dtypes
  with fields with empty names will have the names replaced by 'f0', 'f1',
  etc. Such arrays will not round-trip through the format entirely
  accurately. The data is intact; only the field names will differ. We are
  working on a fix for this. This fix will not require a change in the
  file format. The arrays with such structures can still be saved and
  restored, and the correct dtype may be restored by using the
  ``loadedarray.view(correct_dtype)`` method.

File extensions
---------------

We recommend using the ``.npy`` and ``.npz`` extensions for files saved
in this format. This is by no means a requirement; applications may wish
to use these file formats but use an extension specific to the
application. In the absence of an obvious alternative, however,
we suggest using ``.npy`` and ``.npz``.

Version numbering
-----------------

The version numbering of these formats is independent of NumPy version
numbering. If the format is upgraded, the code in `numpy.io` will still
be able to read and write Version 1.0 files.

Format Version 1.0
------------------

The first 6 bytes are a magic string: exactly ``\\x93NUMPY``.

The next 1 byte is an unsigned byte: the major version number of the file
format, e.g. ``\\x01``.

The next 1 byte is an unsigned byte: the minor version number of the file
format, e.g. ``\\x00``. Note: the version of the file format is not tied
to the version of the numpy package.

The next 2 bytes form a little-endian unsigned short int: the length of
the header data HEADER_LEN.

The next HEADER_LEN bytes form the header data describing the array's
format. It is an ASCII string which contains a Python literal expression
of a dictionary. It is terminated by a newline (``\\n``) and padded with
spaces (``\\x20``) to make the total of
``len(magic string) + 2 + len(length) + HEADER_LEN`` be evenly divisible
by 64 for alignment purposes.

The dictionary contains three keys:

    "descr" : dtype.descr
      An object that can be passed as an argument to the `numpy.dtype`
      constructor to create the array's dtype.
    "fortran_order" : bool
      Whether the array data is Fortran-contiguous or not. Since
      Fortran-contiguous arrays are a common form of non-C-contiguity,
      we allow them to be written directly to disk for efficiency.
    "shape" : tuple of int
      The shape of the array.

For repeatability and readability, the dictionary keys are sorted in
alphabetic order. This is for convenience only. A writer SHOULD implement
this if possible. A reader MUST NOT depend on this.

Following the header comes the array data. If the dtype contains Python
objects (i.e. ``dtype.hasobject is True``), then the data is a Python
pickle of the array. Otherwise the data is the contiguous (either C-
or Fortran-, depending on ``fortran_order``) bytes of the array.
Consumers can figure out the number of bytes by multiplying the number
of elements given by the shape (noting that ``shape=()`` means there is
1 element) by ``dtype.itemsize``.

Format Version 2.0
------------------

The version 1.0 format only allowed the array header to have a total size of
65535 bytes.  This can be exceeded by structured arrays with a large number of
columns.  The version 2.0 format extends the header size to 4 GiB.
`numpy.save` will automatically save in 2.0 format if the data requires it,
else it will always use the more compatible 1.0 format.

The description of the fourth element of the header therefore has become:
"The next 4 bytes form a little-endian unsigned int: the length of the header
data HEADER_LEN."

Format Version 3.0
------------------

This version replaces the ASCII string (which in practice was latin1) with
a utf8-encoded string, so supports structured types with any unicode field
names.

Notes
-----
The ``.npy`` format, including motivation for creating it and a comparison of
alternatives, is described in the
:doc:`"npy-format" NEP <neps:nep-0001-npy-format>`, however details have
evolved with time and this document is more current.

"""
import io
import os
import pickle
import warnings

import numpy
from numpy._utils import set_module
from numpy.lib._utils_impl import drop_metadata

__all__ = []

drop_metadata.__module__ = "numpy.lib.format"

EXPECTED_KEYS = {'descr', 'fortran_order', 'shape'}
MAGIC_PREFIX = b'\x93NUMPY'
MAGIC_LEN = len(MAGIC_PREFIX) + 2
ARRAY_ALIGN = 64  # plausible values are powers of 2 between 16 and 4096
BUFFER_SIZE = 2**18  # size of buffer for reading npz files in bytes
# allow growth within the address space of a 64 bit machine along one axis
GROWTH_AXIS_MAX_DIGITS = 21  # = len(str(8*2**64-1)) hypothetical int1 dtype

# difference between version 1.0 and 2.0 is a 4 byte (I) header length
# instead of 2 bytes (H) allowing storage of large structured arrays
_header_size_info = {
    (1, 0): ('<H', 'latin1'),
    (2, 0): ('<I', 'latin1'),
    (3, 0): ('<I', 'utf8'),
}

# Python's literal_eval is not actually safe for large inputs, since parsing
# may become slow or even cause interpreter crashes.
# This is an arbitrary, low limit which should make it safe in practice.
_MAX_HEADER_SIZE = 10000


def _check_version(version):
    if version not in [(1, 0), (2, 0), (3, 0), None]:
        msg = "we only support format version (1,0), (2,0), and (3,0), not %s"
        raise ValueError(msg % (version,))


@set_module("numpy.lib.format")
def magic(major, minor):
    """ Return the magic string for the given file format version.

    Parameters
    ----------
    major : int in [0, 255]
    minor : int in [0, 255]

    Returns
    -------
    magic : str

    Raises
    ------
    ValueError if the version cannot be formatted.
    """
    if major < 0 or major > 255:
        raise ValueError("major version must be 0 <= major < 256")
    if minor < 0 or minor > 255:
        raise ValueError("minor version must be 0 <= minor < 256")
    return MAGIC_PREFIX + bytes([major, minor])


@set_module("numpy.lib.format")
def read_magic(fp):
    """ Read the magic string to get the version of the file format.

    Parameters
    ----------
    fp : filelike object

    Returns
    -------
    major : int
    minor : int
    """
    magic_str = _read_bytes(fp, MAGIC_LEN, "magic string")
    if magic_str[:-2] != MAGIC_PREFIX:
        msg = "the magic string is not correct; expected %r, got %r"
        raise ValueError(msg % (MAGIC_PREFIX, magic_str[:-2]))
    major, minor = magic_str[-2:]
    return major, minor


@set_module("numpy.lib.format")
def dtype_to_descr(dtype):
    """
    Get a serializable descriptor from the dtype.

    The .descr attribute of a dtype object cannot be round-tripped through
    the dtype() constructor. Simple types, like dtype('float32'), have
    a descr which looks like a record array with one field with '' as
    a name. The dtype() constructor interprets this as a request to give
    a default name.  Instead, we construct descriptor that can be passed to
    dtype().

    Parameters
    ----------
    dtype : dtype
        The dtype of the array that will be written to disk.

    Returns
    -------
    descr : object
        An object that can be passed to `numpy.dtype()` in order to
        replicate the input dtype.

    """
    # NOTE: that drop_metadata may not return the right dtype e.g. for user
    #       dtypes.  In that case our code below would fail the same, though.
    new_dtype = drop_metadata(dtype)
    if new_dtype is not dtype:
        warnings.warn("metadata on a dtype is not saved to an npy/npz. "
                      "Use another format (such as pickle) to store it.",
                      UserWarning, stacklevel=2)
    dtype = new_dtype

    if dtype.names is not None:
        # This is a record array. The .descr is fine.  XXX: parts of the
        # record array with an empty name, like padding bytes, still get
        # fiddled with. This needs to be fixed in the C implementation of
        # dtype().
        return dtype.descr
    elif not type(dtype)._legacy:
        # this must be a user-defined dtype since numpy does not yet expose any
        # non-legacy dtypes in the public API
        #
        # non-legacy dtypes don't yet have __array_interface__
        # support. Instead, as a hack, we use pickle to save the array, and lie
        # that the dtype is object. When the array is loaded, the descriptor is
        # unpickled with the array and the object dtype in the header is
        # discarded.
        #
        # a future NEP should define a way to serialize user-defined
        # descriptors and ideally work out the possible security implications
        warnings.warn("Custom dtypes are saved as python objects using the "
                      "pickle protocol. Loading this file requires "
                      "allow_pickle=True to be set.",
                      UserWarning, stacklevel=2)
        return "|O"
    else:
        return dtype.str


@set_module("numpy.lib.format")
def descr_to_dtype(descr):
    """
    Returns a dtype based off the given description.

    This is essentially the reverse of `~lib.format.dtype_to_descr`. It will
    remove the valueless padding fields created by, i.e. simple fields like
    dtype('float32'), and then convert the description to its corresponding
    dtype.

    Parameters
    ----------
    descr : object
        The object retrieved by dtype.descr. Can be passed to
        `numpy.dtype` in order to replicate the input dtype.

    Returns
    -------
    dtype : dtype
        The dtype constructed by the description.

    """
    if isinstance(descr, str):
        # No padding removal needed
        return numpy.dtype(descr)
    elif isinstance(descr, tuple):
        # subtype, will always have a shape descr[1]
        dt = descr_to_dtype(descr[0])
        return numpy.dtype((dt, descr[1]))

    titles = []
    names = []
    formats = []
    offsets = []
    offset = 0
    for field in descr:
        if len(field) == 2:
            name, descr_str = field
            dt = descr_to_dtype(descr_str)
        else:
            name, descr_str, shape = field
            dt = numpy.dtype((descr_to_dtype(descr_str), shape))

        # Ignore padding bytes, which will be void bytes with '' as name
        # Once support for blank names is removed, only "if name == ''" needed)
        is_pad = (name == '' and dt.type is numpy.void and dt.names is None)
        if not is_pad:
            title, name = name if isinstance(name, tuple) else (None, name)
            titles.append(title)
            names.append(name)
            formats.append(dt)
            offsets.append(offset)
        offset += dt.itemsize

    return numpy.dtype({'names': names, 'formats': formats, 'titles': titles,
                        'offsets': offsets, 'itemsize': offset})


@set_module("numpy.lib.format")
def header_data_from_array_1_0(array):
    """ Get the dictionary of header metadata from a numpy.ndarray.

    Parameters
    ----------
    array : numpy.ndarray

    Returns
    -------
    d : dict
        This has the appropriate entries for writing its string representation
        to the header of the file.
    """
    d = {'shape': array.shape}
    if array.flags.c_contiguous:
        d['fortran_order'] = False
    elif array.flags.f_contiguous:
        d['fortran_order'] = True
    else:
        # Totally non-contiguous data. We will have to make it C-contiguous
        # before writing. Note that we need to test for C_CONTIGUOUS first
        # because a 1-D array is both C_CONTIGUOUS and F_CONTIGUOUS.
        d['fortran_order'] = False

    d['descr'] = dtype_to_descr(array.dtype)
    return d


def _wrap_header(header, version):
    """
    Takes a stringified header, and attaches the prefix and padding to it
    """
    import struct
    assert version is not None
    fmt, encoding = _header_size_info[version]
    header = header.encode(encoding)
    hlen = len(header) + 1
    padlen = ARRAY_ALIGN - ((MAGIC_LEN + struct.calcsize(fmt) + hlen) % ARRAY_ALIGN)
    try:
        header_prefix = magic(*version) + struct.pack(fmt, hlen + padlen)
    except struct.error:
        msg = f"Header length {hlen} too big for version={version}"
        raise ValueError(msg) from None

    # Pad the header with spaces and a final newline such that the magic
    # string, the header-length short and the header are aligned on a
    # ARRAY_ALIGN byte boundary.  This supports memory mapping of dtypes
    # aligned up to ARRAY_ALIGN on systems like Linux where mmap()
    # offset must be page-aligned (i.e. the beginning of the file).
    return header_prefix + header + b' ' * padlen + b'\n'


def _wrap_header_guess_version(header):
    """
    Like `_wrap_header`, but chooses an appropriate version given the contents
    """
    try:
        return _wrap_header(header, (1, 0))
    except ValueError:
        pass

    try:
        ret = _wrap_header(header, (2, 0))
    except UnicodeEncodeError:
        pass
    else:
        warnings.warn("Stored array in format 2.0. It can only be"
                      "read by NumPy >= 1.9", UserWarning, stacklevel=2)
        return ret

    header = _wrap_header(header, (3, 0))
    warnings.warn("Stored array in format 3.0. It can only be "
                  "read by NumPy >= 1.17", UserWarning, stacklevel=2)
    return header


def _write_array_header(fp, d, version=None):
    """ Write the header for an array and returns the version used

    Parameters
    ----------
    fp : filelike object
    d : dict
        This has the appropriate entries for writing its string representation
        to the header of the file.
    version : tuple or None
        None means use oldest that works. Providing an explicit version will
        raise a ValueError if the format does not allow saving this data.
        Default: None
    """
    header = ["{"]
    for key, value in sorted(d.items()):
        # Need to use repr here, since we eval these when reading
        header.append(f"'{key}': {repr(value)}, ")
    header.append("}")
    header = "".join(header)

    # Add some spare space so that the array header can be modified in-place
    # when changing the array size, e.g. when growing it by appending data at
    # the end.
    shape = d['shape']
    header += " " * ((GROWTH_AXIS_MAX_DIGITS - len(repr(
        shape[-1 if d['fortran_order'] else 0]
    ))) if len(shape) > 0 else 0)

    if version is None:
        header = _wrap_header_guess_version(header)
    else:
        header = _wrap_header(header, version)
    fp.write(header)


@set_module("numpy.lib.format")
def write_array_header_1_0(fp, d):
    """ Write the header for an array using the 1.0 format.

    Parameters
    ----------
    fp : filelike object
    d : dict
        This has the appropriate entries for writing its string
        representation to the header of the file.
    """
    _write_array_header(fp, d, (1, 0))


@set_module("numpy.lib.format")
def write_array_header_2_0(fp, d):
    """ Write the header for an array using the 2.0 format.
        The 2.0 format allows storing very large structured arrays.

    Parameters
    ----------
    fp : filelike object
    d : dict
        This has the appropriate entries for writing its string
        representation to the header of the file.
    """
    _write_array_header(fp, d, (2, 0))


@set_module("numpy.lib.format")
def read_array_header_1_0(fp, max_header_size=_MAX_HEADER_SIZE):
    """
    Read an array header from a filelike object using the 1.0 file format
    version.

    This will leave the file object located just after the header.

    Parameters
    ----------
    fp : filelike object
        A file object or something with a `.read()` method like a file.

    Returns
    -------
    shape : tuple of int
        The shape of the array.
    fortran_order : bool
        The array data will be written out directly if it is either
        C-contiguous or Fortran-contiguous. Otherwise, it will be made
        contiguous before writing it out.
    dtype : dtype
        The dtype of the file's data.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.

    Raises
    ------
    ValueError
        If the data is invalid.

    """
    return _read_array_header(
            fp, version=(1, 0), max_header_size=max_header_size)


@set_module("numpy.lib.format")
def read_array_header_2_0(fp, max_header_size=_MAX_HEADER_SIZE):
    """
    Read an array header from a filelike object using the 2.0 file format
    version.

    This will leave the file object located just after the header.

    Parameters
    ----------
    fp : filelike object
        A file object or something with a `.read()` method like a file.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.

    Returns
    -------
    shape : tuple of int
        The shape of the array.
    fortran_order : bool
        The array data will be written out directly if it is either
        C-contiguous or Fortran-contiguous. Otherwise, it will be made
        contiguous before writing it out.
    dtype : dtype
        The dtype of the file's data.

    Raises
    ------
    ValueError
        If the data is invalid.

    """
    return _read_array_header(
            fp, version=(2, 0), max_header_size=max_header_size)


def _filter_header(s):
    """Clean up 'L' in npz header ints.

    Cleans up the 'L' in strings representing integers. Needed to allow npz
    headers produced in Python2 to be read in Python3.

    Parameters
    ----------
    s : string
        Npy file header.

    Returns
    -------
    header : str
        Cleaned up header.

    """
    import tokenize
    from io import StringIO

    tokens = []
    last_token_was_number = False
    for token in tokenize.generate_tokens(StringIO(s).readline):
        token_type = token[0]
        token_string = token[1]
        if (last_token_was_number and
                token_type == tokenize.NAME and
                token_string == "L"):
            continue
        else:
            tokens.append(token)
        last_token_was_number = (token_type == tokenize.NUMBER)
    return tokenize.untokenize(tokens)


def _read_array_header(fp, version, max_header_size=_MAX_HEADER_SIZE):
    """
    see read_array_header_1_0
    """
    # Read an unsigned, little-endian short int which has the length of the
    # header.
    import ast
    import struct
    hinfo = _header_size_info.get(version)
    if hinfo is None:
        raise ValueError(f"Invalid version {version!r}")
    hlength_type, encoding = hinfo

    hlength_str = _read_bytes(fp, struct.calcsize(hlength_type), "array header length")
    header_length = struct.unpack(hlength_type, hlength_str)[0]
    header = _read_bytes(fp, header_length, "array header")
    header = header.decode(encoding)
    if len(header) > max_header_size:
        raise ValueError(
            f"Header info length ({len(header)}) is large and may not be safe "
            "to load securely.\n"
            "To allow loading, adjust `max_header_size` or fully trust "
            "the `.npy` file using `allow_pickle=True`.\n"
            "For safety against large resource use or crashes, sandboxing "
            "may be necessary.")

    # The header is a pretty-printed string representation of a literal
    # Python dictionary with trailing newlines padded to a ARRAY_ALIGN byte
    # boundary. The keys are strings.
    #   "shape" : tuple of int
    #   "fortran_order" : bool
    #   "descr" : dtype.descr
    # Versions (2, 0) and (1, 0) could have been created by a Python 2
    # implementation before header filtering was implemented.
    #
    # For performance reasons, we try without _filter_header first though
    try:
        d = ast.literal_eval(header)
    except SyntaxError as e:
        if version <= (2, 0):
            header = _filter_header(header)
            try:
                d = ast.literal_eval(header)
            except SyntaxError as e2:
                msg = "Cannot parse header: {!r}"
                raise ValueError(msg.format(header)) from e2
            else:
                warnings.warn(
                    "Reading `.npy` or `.npz` file required additional "
                    "header parsing as it was created on Python 2. Save the "
                    "file again to speed up loading and avoid this warning.",
                    UserWarning, stacklevel=4)
        else:
            msg = "Cannot parse header: {!r}"
            raise ValueError(msg.format(header)) from e
    if not isinstance(d, dict):
        msg = "Header is not a dictionary: {!r}"
        raise ValueError(msg.format(d))

    if EXPECTED_KEYS != d.keys():
        keys = sorted(d.keys())
        msg = "Header does not contain the correct keys: {!r}"
        raise ValueError(msg.format(keys))

    # Sanity-check the values.
    if (not isinstance(d['shape'], tuple) or
            not all(isinstance(x, int) for x in d['shape'])):
        msg = "shape is not valid: {!r}"
        raise ValueError(msg.format(d['shape']))
    if not isinstance(d['fortran_order'], bool):
        msg = "fortran_order is not a valid bool: {!r}"
        raise ValueError(msg.format(d['fortran_order']))
    try:
        dtype = descr_to_dtype(d['descr'])
    except TypeError as e:
        msg = "descr is not a valid dtype descriptor: {!r}"
        raise ValueError(msg.format(d['descr'])) from e

    return d['shape'], d['fortran_order'], dtype


@set_module("numpy.lib.format")
def write_array(fp, array, version=None, allow_pickle=True, pickle_kwargs=None):
    """
    Write an array to an NPY file, including a header.

    If the array is neither C-contiguous nor Fortran-contiguous AND the
    file_like object is not a real file object, this function will have to
    copy data in memory.

    Parameters
    ----------
    fp : file_like object
        An open, writable file object, or similar object with a
        ``.write()`` method.
    array : ndarray
        The array to write to disk.
    version : (int, int) or None, optional
        The version number of the format. None means use the oldest
        supported version that is able to store the data.  Default: None
    allow_pickle : bool, optional
        Whether to allow writing pickled data. Default: True
    pickle_kwargs : dict, optional
        Additional keyword arguments to pass to pickle.dump, excluding
        'protocol'. These are only useful when pickling objects in object
        arrays to Python 2 compatible format.

    Raises
    ------
    ValueError
        If the array cannot be persisted. This includes the case of
        allow_pickle=False and array being an object array.
    Various other errors
        If the array contains Python objects as part of its dtype, the
        process of pickling them may raise various errors if the objects
        are not picklable.

    """
    _check_version(version)
    _write_array_header(fp, header_data_from_array_1_0(array), version)

    if array.itemsize == 0:
        buffersize = 0
    else:
        # Set buffer size to 16 MiB to hide the Python loop overhead.
        buffersize = max(16 * 1024 ** 2 // array.itemsize, 1)

    dtype_class = type(array.dtype)

    if array.dtype.hasobject or not dtype_class._legacy:
        # We contain Python objects so we cannot write out the data
        # directly.  Instead, we will pickle it out
        if not allow_pickle:
            if array.dtype.hasobject:
                raise ValueError("Object arrays cannot be saved when "
                                 "allow_pickle=False")
            if not dtype_class._legacy:
                raise ValueError("User-defined dtypes cannot be saved "
                                 "when allow_pickle=False")
        if pickle_kwargs is None:
            pickle_kwargs = {}
        pickle.dump(array, fp, protocol=4, **pickle_kwargs)
    elif array.flags.f_contiguous and not array.flags.c_contiguous:
        if isfileobj(fp):
            array.T.tofile(fp)
        else:
            for chunk in numpy.nditer(
                    array, flags=['external_loop', 'buffered', 'zerosize_ok'],
                    buffersize=buffersize, order='F'):
                fp.write(chunk.tobytes('C'))
    elif isfileobj(fp):
        array.tofile(fp)
    else:
        for chunk in numpy.nditer(
                array, flags=['external_loop', 'buffered', 'zerosize_ok'],
                buffersize=buffersize, order='C'):
            fp.write(chunk.tobytes('C'))


@set_module("numpy.lib.format")
def read_array(fp, allow_pickle=False, pickle_kwargs=None, *,
               max_header_size=_MAX_HEADER_SIZE):
    """
    Read an array from an NPY file.

    Parameters
    ----------
    fp : file_like object
        If this is not a real file object, then this may take extra memory
        and time.
    allow_pickle : bool, optional
        Whether to allow writing pickled data. Default: False
    pickle_kwargs : dict
        Additional keyword arguments to pass to pickle.load. These are only
        useful when loading object arrays saved on Python 2.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.
        This option is ignored when `allow_pickle` is passed.  In that case
        the file is by definition trusted and the limit is unnecessary.

    Returns
    -------
    array : ndarray
        The array from the data on disk.

    Raises
    ------
    ValueError
        If the data is invalid, or allow_pickle=False and the file contains
        an object array.

    """
    if allow_pickle:
        # Effectively ignore max_header_size, since `allow_pickle` indicates
        # that the input is fully trusted.
        max_header_size = 2**64

    version = read_magic(fp)
    _check_version(version)
    shape, fortran_order, dtype = _read_array_header(
            fp, version, max_header_size=max_header_size)
    if len(shape) == 0:
        count = 1
    else:
        count = numpy.multiply.reduce(shape, dtype=numpy.int64)

    # Now read the actual data.
    if dtype.hasobject:
        # The array contained Python objects. We need to unpickle the data.
        if not allow_pickle:
            raise ValueError("Object arrays cannot be loaded when "
                             "allow_pickle=False")
        if pickle_kwargs is None:
            pickle_kwargs = {}
        try:
            array = pickle.load(fp, **pickle_kwargs)
        except UnicodeError as err:
            # Friendlier error message
            raise UnicodeError("Unpickling a python object failed: %r\n"
                               "You may need to pass the encoding= option "
                               "to numpy.load" % (err,)) from err
    else:
        if isfileobj(fp):
            # We can use the fast fromfile() function.
            array = numpy.fromfile(fp, dtype=dtype, count=count)
        else:
            # This is not a real file. We have to read it the
            # memory-intensive way.
            # crc32 module fails on reads greater than 2 ** 32 bytes,
            # breaking large reads from gzip streams. Chunk reads to
            # BUFFER_SIZE bytes to avoid issue and reduce memory overhead
            # of the read. In non-chunked case count < max_read_count, so
            # only one read is performed.

            # Use np.ndarray instead of np.empty since the latter does
            # not correctly instantiate zero-width string dtypes; see
            # https://github.com/numpy/numpy/pull/6430
            array = numpy.ndarray(count, dtype=dtype)

            if dtype.itemsize > 0:
                # If dtype.itemsize == 0 then there's nothing more to read
                max_read_count = BUFFER_SIZE // min(BUFFER_SIZE, dtype.itemsize)

                for i in range(0, count, max_read_count):
                    read_count = min(max_read_count, count - i)
                    read_size = int(read_count * dtype.itemsize)
                    data = _read_bytes(fp, read_size, "array data")
                    array[i:i + read_count] = numpy.frombuffer(data, dtype=dtype,
                                                             count=read_count)

        if array.size != count:
            raise ValueError(
                "Failed to read all data for array. "
                f"Expected {shape} = {count} elements, "
                f"could only read {array.size} elements. "
                "(file seems not fully written?)"
            )

        if fortran_order:
            array.shape = shape[::-1]
            array = array.transpose()
        else:
            array.shape = shape

    return array


@set_module("numpy.lib.format")
def open_memmap(filename, mode='r+', dtype=None, shape=None,
                fortran_order=False, version=None, *,
                max_header_size=_MAX_HEADER_SIZE):
    """
    Open a .npy file as a memory-mapped array.

    This may be used to read an existing file or create a new one.

    Parameters
    ----------
    filename : str or path-like
        The name of the file on disk.  This may *not* be a file-like
        object.
    mode : str, optional
        The mode in which to open the file; the default is 'r+'.  In
        addition to the standard file modes, 'c' is also accepted to mean
        "copy on write."  See `memmap` for the available mode strings.
    dtype : data-type, optional
        The data type of the array if we are creating a new file in "write"
        mode, if not, `dtype` is ignored.  The default value is None, which
        results in a data-type of `float64`.
    shape : tuple of int
        The shape of the array if we are creating a new file in "write"
        mode, in which case this parameter is required.  Otherwise, this
        parameter is ignored and is thus optional.
    fortran_order : bool, optional
        Whether the array should be Fortran-contiguous (True) or
        C-contiguous (False, the default) if we are creating a new file in
        "write" mode.
    version : tuple of int (major, minor) or None
        If the mode is a "write" mode, then this is the version of the file
        format used to create the file.  None means use the oldest
        supported version that is able to store the data.  Default: None
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.

    Returns
    -------
    marray : memmap
        The memory-mapped array.

    Raises
    ------
    ValueError
        If the data or the mode is invalid.
    OSError
        If the file is not found or cannot be opened correctly.

    See Also
    --------
    numpy.memmap

    """
    if isfileobj(filename):
        raise ValueError("Filename must be a string or a path-like object."
                         "  Memmap cannot use existing file handles.")

    if 'w' in mode:
        # We are creating the file, not reading it.
        # Check if we ought to create the file.
        _check_version(version)
        # Ensure that the given dtype is an authentic dtype object rather
        # than just something that can be interpreted as a dtype object.
        dtype = numpy.dtype(dtype)
        if dtype.hasobject:
            msg = "Array can't be memory-mapped: Python objects in dtype."
            raise ValueError(msg)
        d = {
            "descr": dtype_to_descr(dtype),
            "fortran_order": fortran_order,
            "shape": shape,
        }
        # If we got here, then it should be safe to create the file.
        with open(os.fspath(filename), mode + 'b') as fp:
            _write_array_header(fp, d, version)
            offset = fp.tell()
    else:
        # Read the header of the file first.
        with open(os.fspath(filename), 'rb') as fp:
            version = read_magic(fp)
            _check_version(version)

            shape, fortran_order, dtype = _read_array_header(
                    fp, version, max_header_size=max_header_size)
            if dtype.hasobject:
                msg = "Array can't be memory-mapped: Python objects in dtype."
                raise ValueError(msg)
            offset = fp.tell()

    if fortran_order:
        order = 'F'
    else:
        order = 'C'

    # We need to change a write-only mode to a read-write mode since we've
    # already written data to the file.
    if mode == 'w+':
        mode = 'r+'

    marray = numpy.memmap(filename, dtype=dtype, shape=shape, order=order,
        mode=mode, offset=offset)

    return marray


def _read_bytes(fp, size, error_template="ran out of data"):
    """
    Read from file-like object until size bytes are read.
    Raises ValueError if not EOF is encountered before size bytes are read.
    Non-blocking objects only supported if they derive from io objects.

    Required as e.g. ZipExtFile in python 2.6 can return less data than
    requested.
    """
    data = b""
    while True:
        # io files (default in python3) return None or raise on
        # would-block, python2 file will truncate, probably nothing can be
        # done about that.  note that regular files can't be non-blocking
        try:
            r = fp.read(size - len(data))
            data += r
            if len(r) == 0 or len(data) == size:
                break
        except BlockingIOError:
            pass
    if len(data) != size:
        msg = "EOF: reading %s, expected %d bytes got %d"
        raise ValueError(msg % (error_template, size, len(data)))
    else:
        return data


@set_module("numpy.lib.format")
def isfileobj(f):
    if not isinstance(f, (io.FileIO, io.BufferedReader, io.BufferedWriter)):
        return False
    try:
        # BufferedReader/Writer may raise OSError when
        # fetching `fileno()` (e.g. when wrapping BytesIO).
        f.fileno()
        return True
    except OSError:
        return False

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_format_impl.py ===
"""
Binary serialization

NPY format
==========

A simple format for saving numpy arrays to disk with the full
information about them.

The ``.npy`` format is the standard binary file format in NumPy for
persisting a *single* arbitrary NumPy array on disk. The format stores all
of the shape and dtype information necessary to reconstruct the array
correctly even on another machine with a different architecture.
The format is designed to be as simple as possible while achieving
its limited goals.

The ``.npz`` format is the standard format for persisting *multiple* NumPy
arrays on disk. A ``.npz`` file is a zip file containing multiple ``.npy``
files, one for each array.

Capabilities
------------

- Can represent all NumPy arrays including nested record arrays and
  object arrays.

- Represents the data in its native binary form.

- Supports Fortran-contiguous arrays directly.

- Stores all of the necessary information to reconstruct the array
  including shape and dtype on a machine of a different
  architecture.  Both little-endian and big-endian arrays are
  supported, and a file with little-endian numbers will yield
  a little-endian array on any machine reading the file. The
  types are described in terms of their actual sizes. For example,
  if a machine with a 64-bit C "long int" writes out an array with
  "long ints", a reading machine with 32-bit C "long ints" will yield
  an array with 64-bit integers.

- Is straightforward to reverse engineer. Datasets often live longer than
  the programs that created them. A competent developer should be
  able to create a solution in their preferred programming language to
  read most ``.npy`` files that they have been given without much
  documentation.

- Allows memory-mapping of the data. See `open_memmap`.

- Can be read from a filelike stream object instead of an actual file.

- Stores object arrays, i.e. arrays containing elements that are arbitrary
  Python objects. Files with object arrays are not to be mmapable, but
  can be read and written to disk.

Limitations
-----------

- Arbitrary subclasses of numpy.ndarray are not completely preserved.
  Subclasses will be accepted for writing, but only the array data will
  be written out. A regular numpy.ndarray object will be created
  upon reading the file.

.. warning::

  Due to limitations in the interpretation of structured dtypes, dtypes
  with fields with empty names will have the names replaced by 'f0', 'f1',
  etc. Such arrays will not round-trip through the format entirely
  accurately. The data is intact; only the field names will differ. We are
  working on a fix for this. This fix will not require a change in the
  file format. The arrays with such structures can still be saved and
  restored, and the correct dtype may be restored by using the
  ``loadedarray.view(correct_dtype)`` method.

File extensions
---------------

We recommend using the ``.npy`` and ``.npz`` extensions for files saved
in this format. This is by no means a requirement; applications may wish
to use these file formats but use an extension specific to the
application. In the absence of an obvious alternative, however,
we suggest using ``.npy`` and ``.npz``.

Version numbering
-----------------

The version numbering of these formats is independent of NumPy version
numbering. If the format is upgraded, the code in `numpy.io` will still
be able to read and write Version 1.0 files.

Format Version 1.0
------------------

The first 6 bytes are a magic string: exactly ``\\x93NUMPY``.

The next 1 byte is an unsigned byte: the major version number of the file
format, e.g. ``\\x01``.

The next 1 byte is an unsigned byte: the minor version number of the file
format, e.g. ``\\x00``. Note: the version of the file format is not tied
to the version of the numpy package.

The next 2 bytes form a little-endian unsigned short int: the length of
the header data HEADER_LEN.

The next HEADER_LEN bytes form the header data describing the array's
format. It is an ASCII string which contains a Python literal expression
of a dictionary. It is terminated by a newline (``\\n``) and padded with
spaces (``\\x20``) to make the total of
``len(magic string) + 2 + len(length) + HEADER_LEN`` be evenly divisible
by 64 for alignment purposes.

The dictionary contains three keys:

    "descr" : dtype.descr
      An object that can be passed as an argument to the `numpy.dtype`
      constructor to create the array's dtype.
    "fortran_order" : bool
      Whether the array data is Fortran-contiguous or not. Since
      Fortran-contiguous arrays are a common form of non-C-contiguity,
      we allow them to be written directly to disk for efficiency.
    "shape" : tuple of int
      The shape of the array.

For repeatability and readability, the dictionary keys are sorted in
alphabetic order. This is for convenience only. A writer SHOULD implement
this if possible. A reader MUST NOT depend on this.

Following the header comes the array data. If the dtype contains Python
objects (i.e. ``dtype.hasobject is True``), then the data is a Python
pickle of the array. Otherwise the data is the contiguous (either C-
or Fortran-, depending on ``fortran_order``) bytes of the array.
Consumers can figure out the number of bytes by multiplying the number
of elements given by the shape (noting that ``shape=()`` means there is
1 element) by ``dtype.itemsize``.

Format Version 2.0
------------------

The version 1.0 format only allowed the array header to have a total size of
65535 bytes.  This can be exceeded by structured arrays with a large number of
columns.  The version 2.0 format extends the header size to 4 GiB.
`numpy.save` will automatically save in 2.0 format if the data requires it,
else it will always use the more compatible 1.0 format.

The description of the fourth element of the header therefore has become:
"The next 4 bytes form a little-endian unsigned int: the length of the header
data HEADER_LEN."

Format Version 3.0
------------------

This version replaces the ASCII string (which in practice was latin1) with
a utf8-encoded string, so supports structured types with any unicode field
names.

Notes
-----
The ``.npy`` format, including motivation for creating it and a comparison of
alternatives, is described in the
:doc:`"npy-format" NEP <neps:nep-0001-npy-format>`, however details have
evolved with time and this document is more current.

"""
import io
import os
import pickle
import warnings

import numpy
from numpy._utils import set_module
from numpy.lib._utils_impl import drop_metadata

__all__ = []

drop_metadata.__module__ = "numpy.lib.format"

EXPECTED_KEYS = {'descr', 'fortran_order', 'shape'}
MAGIC_PREFIX = b'\x93NUMPY'
MAGIC_LEN = len(MAGIC_PREFIX) + 2
ARRAY_ALIGN = 64  # plausible values are powers of 2 between 16 and 4096
BUFFER_SIZE = 2**18  # size of buffer for reading npz files in bytes
# allow growth within the address space of a 64 bit machine along one axis
GROWTH_AXIS_MAX_DIGITS = 21  # = len(str(8*2**64-1)) hypothetical int1 dtype

# difference between version 1.0 and 2.0 is a 4 byte (I) header length
# instead of 2 bytes (H) allowing storage of large structured arrays
_header_size_info = {
    (1, 0): ('<H', 'latin1'),
    (2, 0): ('<I', 'latin1'),
    (3, 0): ('<I', 'utf8'),
}

# Python's literal_eval is not actually safe for large inputs, since parsing
# may become slow or even cause interpreter crashes.
# This is an arbitrary, low limit which should make it safe in practice.
_MAX_HEADER_SIZE = 10000


def _check_version(version):
    if version not in [(1, 0), (2, 0), (3, 0), None]:
        msg = "we only support format version (1,0), (2,0), and (3,0), not %s"
        raise ValueError(msg % (version,))


@set_module("numpy.lib.format")
def magic(major, minor):
    """ Return the magic string for the given file format version.

    Parameters
    ----------
    major : int in [0, 255]
    minor : int in [0, 255]

    Returns
    -------
    magic : str

    Raises
    ------
    ValueError if the version cannot be formatted.
    """
    if major < 0 or major > 255:
        raise ValueError("major version must be 0 <= major < 256")
    if minor < 0 or minor > 255:
        raise ValueError("minor version must be 0 <= minor < 256")
    return MAGIC_PREFIX + bytes([major, minor])


@set_module("numpy.lib.format")
def read_magic(fp):
    """ Read the magic string to get the version of the file format.

    Parameters
    ----------
    fp : filelike object

    Returns
    -------
    major : int
    minor : int
    """
    magic_str = _read_bytes(fp, MAGIC_LEN, "magic string")
    if magic_str[:-2] != MAGIC_PREFIX:
        msg = "the magic string is not correct; expected %r, got %r"
        raise ValueError(msg % (MAGIC_PREFIX, magic_str[:-2]))
    major, minor = magic_str[-2:]
    return major, minor


@set_module("numpy.lib.format")
def dtype_to_descr(dtype):
    """
    Get a serializable descriptor from the dtype.

    The .descr attribute of a dtype object cannot be round-tripped through
    the dtype() constructor. Simple types, like dtype('float32'), have
    a descr which looks like a record array with one field with '' as
    a name. The dtype() constructor interprets this as a request to give
    a default name.  Instead, we construct descriptor that can be passed to
    dtype().

    Parameters
    ----------
    dtype : dtype
        The dtype of the array that will be written to disk.

    Returns
    -------
    descr : object
        An object that can be passed to `numpy.dtype()` in order to
        replicate the input dtype.

    """
    # NOTE: that drop_metadata may not return the right dtype e.g. for user
    #       dtypes.  In that case our code below would fail the same, though.
    new_dtype = drop_metadata(dtype)
    if new_dtype is not dtype:
        warnings.warn("metadata on a dtype is not saved to an npy/npz. "
                      "Use another format (such as pickle) to store it.",
                      UserWarning, stacklevel=2)
    dtype = new_dtype

    if dtype.names is not None:
        # This is a record array. The .descr is fine.  XXX: parts of the
        # record array with an empty name, like padding bytes, still get
        # fiddled with. This needs to be fixed in the C implementation of
        # dtype().
        return dtype.descr
    elif not type(dtype)._legacy:
        # this must be a user-defined dtype since numpy does not yet expose any
        # non-legacy dtypes in the public API
        #
        # non-legacy dtypes don't yet have __array_interface__
        # support. Instead, as a hack, we use pickle to save the array, and lie
        # that the dtype is object. When the array is loaded, the descriptor is
        # unpickled with the array and the object dtype in the header is
        # discarded.
        #
        # a future NEP should define a way to serialize user-defined
        # descriptors and ideally work out the possible security implications
        warnings.warn("Custom dtypes are saved as python objects using the "
                      "pickle protocol. Loading this file requires "
                      "allow_pickle=True to be set.",
                      UserWarning, stacklevel=2)
        return "|O"
    else:
        return dtype.str


@set_module("numpy.lib.format")
def descr_to_dtype(descr):
    """
    Returns a dtype based off the given description.

    This is essentially the reverse of `~lib.format.dtype_to_descr`. It will
    remove the valueless padding fields created by, i.e. simple fields like
    dtype('float32'), and then convert the description to its corresponding
    dtype.

    Parameters
    ----------
    descr : object
        The object retrieved by dtype.descr. Can be passed to
        `numpy.dtype` in order to replicate the input dtype.

    Returns
    -------
    dtype : dtype
        The dtype constructed by the description.

    """
    if isinstance(descr, str):
        # No padding removal needed
        return numpy.dtype(descr)
    elif isinstance(descr, tuple):
        # subtype, will always have a shape descr[1]
        dt = descr_to_dtype(descr[0])
        return numpy.dtype((dt, descr[1]))

    titles = []
    names = []
    formats = []
    offsets = []
    offset = 0
    for field in descr:
        if len(field) == 2:
            name, descr_str = field
            dt = descr_to_dtype(descr_str)
        else:
            name, descr_str, shape = field
            dt = numpy.dtype((descr_to_dtype(descr_str), shape))

        # Ignore padding bytes, which will be void bytes with '' as name
        # Once support for blank names is removed, only "if name == ''" needed)
        is_pad = (name == '' and dt.type is numpy.void and dt.names is None)
        if not is_pad:
            title, name = name if isinstance(name, tuple) else (None, name)
            titles.append(title)
            names.append(name)
            formats.append(dt)
            offsets.append(offset)
        offset += dt.itemsize

    return numpy.dtype({'names': names, 'formats': formats, 'titles': titles,
                        'offsets': offsets, 'itemsize': offset})


@set_module("numpy.lib.format")
def header_data_from_array_1_0(array):
    """ Get the dictionary of header metadata from a numpy.ndarray.

    Parameters
    ----------
    array : numpy.ndarray

    Returns
    -------
    d : dict
        This has the appropriate entries for writing its string representation
        to the header of the file.
    """
    d = {'shape': array.shape}
    if array.flags.c_contiguous:
        d['fortran_order'] = False
    elif array.flags.f_contiguous:
        d['fortran_order'] = True
    else:
        # Totally non-contiguous data. We will have to make it C-contiguous
        # before writing. Note that we need to test for C_CONTIGUOUS first
        # because a 1-D array is both C_CONTIGUOUS and F_CONTIGUOUS.
        d['fortran_order'] = False

    d['descr'] = dtype_to_descr(array.dtype)
    return d


def _wrap_header(header, version):
    """
    Takes a stringified header, and attaches the prefix and padding to it
    """
    import struct
    assert version is not None
    fmt, encoding = _header_size_info[version]
    header = header.encode(encoding)
    hlen = len(header) + 1
    padlen = ARRAY_ALIGN - ((MAGIC_LEN + struct.calcsize(fmt) + hlen) % ARRAY_ALIGN)
    try:
        header_prefix = magic(*version) + struct.pack(fmt, hlen + padlen)
    except struct.error:
        msg = f"Header length {hlen} too big for version={version}"
        raise ValueError(msg) from None

    # Pad the header with spaces and a final newline such that the magic
    # string, the header-length short and the header are aligned on a
    # ARRAY_ALIGN byte boundary.  This supports memory mapping of dtypes
    # aligned up to ARRAY_ALIGN on systems like Linux where mmap()
    # offset must be page-aligned (i.e. the beginning of the file).
    return header_prefix + header + b' ' * padlen + b'\n'


def _wrap_header_guess_version(header):
    """
    Like `_wrap_header`, but chooses an appropriate version given the contents
    """
    try:
        return _wrap_header(header, (1, 0))
    except ValueError:
        pass

    try:
        ret = _wrap_header(header, (2, 0))
    except UnicodeEncodeError:
        pass
    else:
        warnings.warn("Stored array in format 2.0. It can only be"
                      "read by NumPy >= 1.9", UserWarning, stacklevel=2)
        return ret

    header = _wrap_header(header, (3, 0))
    warnings.warn("Stored array in format 3.0. It can only be "
                  "read by NumPy >= 1.17", UserWarning, stacklevel=2)
    return header


def _write_array_header(fp, d, version=None):
    """ Write the header for an array and returns the version used

    Parameters
    ----------
    fp : filelike object
    d : dict
        This has the appropriate entries for writing its string representation
        to the header of the file.
    version : tuple or None
        None means use oldest that works. Providing an explicit version will
        raise a ValueError if the format does not allow saving this data.
        Default: None
    """
    header = ["{"]
    for key, value in sorted(d.items()):
        # Need to use repr here, since we eval these when reading
        header.append(f"'{key}': {repr(value)}, ")
    header.append("}")
    header = "".join(header)

    # Add some spare space so that the array header can be modified in-place
    # when changing the array size, e.g. when growing it by appending data at
    # the end.
    shape = d['shape']
    header += " " * ((GROWTH_AXIS_MAX_DIGITS - len(repr(
        shape[-1 if d['fortran_order'] else 0]
    ))) if len(shape) > 0 else 0)

    if version is None:
        header = _wrap_header_guess_version(header)
    else:
        header = _wrap_header(header, version)
    fp.write(header)


@set_module("numpy.lib.format")
def write_array_header_1_0(fp, d):
    """ Write the header for an array using the 1.0 format.

    Parameters
    ----------
    fp : filelike object
    d : dict
        This has the appropriate entries for writing its string
        representation to the header of the file.
    """
    _write_array_header(fp, d, (1, 0))


@set_module("numpy.lib.format")
def write_array_header_2_0(fp, d):
    """ Write the header for an array using the 2.0 format.
        The 2.0 format allows storing very large structured arrays.

    Parameters
    ----------
    fp : filelike object
    d : dict
        This has the appropriate entries for writing its string
        representation to the header of the file.
    """
    _write_array_header(fp, d, (2, 0))


@set_module("numpy.lib.format")
def read_array_header_1_0(fp, max_header_size=_MAX_HEADER_SIZE):
    """
    Read an array header from a filelike object using the 1.0 file format
    version.

    This will leave the file object located just after the header.

    Parameters
    ----------
    fp : filelike object
        A file object or something with a `.read()` method like a file.

    Returns
    -------
    shape : tuple of int
        The shape of the array.
    fortran_order : bool
        The array data will be written out directly if it is either
        C-contiguous or Fortran-contiguous. Otherwise, it will be made
        contiguous before writing it out.
    dtype : dtype
        The dtype of the file's data.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.

    Raises
    ------
    ValueError
        If the data is invalid.

    """
    return _read_array_header(
            fp, version=(1, 0), max_header_size=max_header_size)


@set_module("numpy.lib.format")
def read_array_header_2_0(fp, max_header_size=_MAX_HEADER_SIZE):
    """
    Read an array header from a filelike object using the 2.0 file format
    version.

    This will leave the file object located just after the header.

    Parameters
    ----------
    fp : filelike object
        A file object or something with a `.read()` method like a file.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.

    Returns
    -------
    shape : tuple of int
        The shape of the array.
    fortran_order : bool
        The array data will be written out directly if it is either
        C-contiguous or Fortran-contiguous. Otherwise, it will be made
        contiguous before writing it out.
    dtype : dtype
        The dtype of the file's data.

    Raises
    ------
    ValueError
        If the data is invalid.

    """
    return _read_array_header(
            fp, version=(2, 0), max_header_size=max_header_size)


def _filter_header(s):
    """Clean up 'L' in npz header ints.

    Cleans up the 'L' in strings representing integers. Needed to allow npz
    headers produced in Python2 to be read in Python3.

    Parameters
    ----------
    s : string
        Npy file header.

    Returns
    -------
    header : str
        Cleaned up header.

    """
    import tokenize
    from io import StringIO

    tokens = []
    last_token_was_number = False
    for token in tokenize.generate_tokens(StringIO(s).readline):
        token_type = token[0]
        token_string = token[1]
        if (last_token_was_number and
                token_type == tokenize.NAME and
                token_string == "L"):
            continue
        else:
            tokens.append(token)
        last_token_was_number = (token_type == tokenize.NUMBER)
    return tokenize.untokenize(tokens)


def _read_array_header(fp, version, max_header_size=_MAX_HEADER_SIZE):
    """
    see read_array_header_1_0
    """
    # Read an unsigned, little-endian short int which has the length of the
    # header.
    import ast
    import struct
    hinfo = _header_size_info.get(version)
    if hinfo is None:
        raise ValueError(f"Invalid version {version!r}")
    hlength_type, encoding = hinfo

    hlength_str = _read_bytes(fp, struct.calcsize(hlength_type), "array header length")
    header_length = struct.unpack(hlength_type, hlength_str)[0]
    header = _read_bytes(fp, header_length, "array header")
    header = header.decode(encoding)
    if len(header) > max_header_size:
        raise ValueError(
            f"Header info length ({len(header)}) is large and may not be safe "
            "to load securely.\n"
            "To allow loading, adjust `max_header_size` or fully trust "
            "the `.npy` file using `allow_pickle=True`.\n"
            "For safety against large resource use or crashes, sandboxing "
            "may be necessary.")

    # The header is a pretty-printed string representation of a literal
    # Python dictionary with trailing newlines padded to a ARRAY_ALIGN byte
    # boundary. The keys are strings.
    #   "shape" : tuple of int
    #   "fortran_order" : bool
    #   "descr" : dtype.descr
    # Versions (2, 0) and (1, 0) could have been created by a Python 2
    # implementation before header filtering was implemented.
    #
    # For performance reasons, we try without _filter_header first though
    try:
        d = ast.literal_eval(header)
    except SyntaxError as e:
        if version <= (2, 0):
            header = _filter_header(header)
            try:
                d = ast.literal_eval(header)
            except SyntaxError as e2:
                msg = "Cannot parse header: {!r}"
                raise ValueError(msg.format(header)) from e2
            else:
                warnings.warn(
                    "Reading `.npy` or `.npz` file required additional "
                    "header parsing as it was created on Python 2. Save the "
                    "file again to speed up loading and avoid this warning.",
                    UserWarning, stacklevel=4)
        else:
            msg = "Cannot parse header: {!r}"
            raise ValueError(msg.format(header)) from e
    if not isinstance(d, dict):
        msg = "Header is not a dictionary: {!r}"
        raise ValueError(msg.format(d))

    if EXPECTED_KEYS != d.keys():
        keys = sorted(d.keys())
        msg = "Header does not contain the correct keys: {!r}"
        raise ValueError(msg.format(keys))

    # Sanity-check the values.
    if (not isinstance(d['shape'], tuple) or
            not all(isinstance(x, int) for x in d['shape'])):
        msg = "shape is not valid: {!r}"
        raise ValueError(msg.format(d['shape']))
    if not isinstance(d['fortran_order'], bool):
        msg = "fortran_order is not a valid bool: {!r}"
        raise ValueError(msg.format(d['fortran_order']))
    try:
        dtype = descr_to_dtype(d['descr'])
    except TypeError as e:
        msg = "descr is not a valid dtype descriptor: {!r}"
        raise ValueError(msg.format(d['descr'])) from e

    return d['shape'], d['fortran_order'], dtype


@set_module("numpy.lib.format")
def write_array(fp, array, version=None, allow_pickle=True, pickle_kwargs=None):
    """
    Write an array to an NPY file, including a header.

    If the array is neither C-contiguous nor Fortran-contiguous AND the
    file_like object is not a real file object, this function will have to
    copy data in memory.

    Parameters
    ----------
    fp : file_like object
        An open, writable file object, or similar object with a
        ``.write()`` method.
    array : ndarray
        The array to write to disk.
    version : (int, int) or None, optional
        The version number of the format. None means use the oldest
        supported version that is able to store the data.  Default: None
    allow_pickle : bool, optional
        Whether to allow writing pickled data. Default: True
    pickle_kwargs : dict, optional
        Additional keyword arguments to pass to pickle.dump, excluding
        'protocol'. These are only useful when pickling objects in object
        arrays to Python 2 compatible format.

    Raises
    ------
    ValueError
        If the array cannot be persisted. This includes the case of
        allow_pickle=False and array being an object array.
    Various other errors
        If the array contains Python objects as part of its dtype, the
        process of pickling them may raise various errors if the objects
        are not picklable.

    """
    _check_version(version)
    _write_array_header(fp, header_data_from_array_1_0(array), version)

    if array.itemsize == 0:
        buffersize = 0
    else:
        # Set buffer size to 16 MiB to hide the Python loop overhead.
        buffersize = max(16 * 1024 ** 2 // array.itemsize, 1)

    dtype_class = type(array.dtype)

    if array.dtype.hasobject or not dtype_class._legacy:
        # We contain Python objects so we cannot write out the data
        # directly.  Instead, we will pickle it out
        if not allow_pickle:
            if array.dtype.hasobject:
                raise ValueError("Object arrays cannot be saved when "
                                 "allow_pickle=False")
            if not dtype_class._legacy:
                raise ValueError("User-defined dtypes cannot be saved "
                                 "when allow_pickle=False")
        if pickle_kwargs is None:
            pickle_kwargs = {}
        pickle.dump(array, fp, protocol=4, **pickle_kwargs)
    elif array.flags.f_contiguous and not array.flags.c_contiguous:
        if isfileobj(fp):
            array.T.tofile(fp)
        else:
            for chunk in numpy.nditer(
                    array, flags=['external_loop', 'buffered', 'zerosize_ok'],
                    buffersize=buffersize, order='F'):
                fp.write(chunk.tobytes('C'))
    elif isfileobj(fp):
        array.tofile(fp)
    else:
        for chunk in numpy.nditer(
                array, flags=['external_loop', 'buffered', 'zerosize_ok'],
                buffersize=buffersize, order='C'):
            fp.write(chunk.tobytes('C'))


@set_module("numpy.lib.format")
def read_array(fp, allow_pickle=False, pickle_kwargs=None, *,
               max_header_size=_MAX_HEADER_SIZE):
    """
    Read an array from an NPY file.

    Parameters
    ----------
    fp : file_like object
        If this is not a real file object, then this may take extra memory
        and time.
    allow_pickle : bool, optional
        Whether to allow writing pickled data. Default: False
    pickle_kwargs : dict
        Additional keyword arguments to pass to pickle.load. These are only
        useful when loading object arrays saved on Python 2.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.
        This option is ignored when `allow_pickle` is passed.  In that case
        the file is by definition trusted and the limit is unnecessary.

    Returns
    -------
    array : ndarray
        The array from the data on disk.

    Raises
    ------
    ValueError
        If the data is invalid, or allow_pickle=False and the file contains
        an object array.

    """
    if allow_pickle:
        # Effectively ignore max_header_size, since `allow_pickle` indicates
        # that the input is fully trusted.
        max_header_size = 2**64

    version = read_magic(fp)
    _check_version(version)
    shape, fortran_order, dtype = _read_array_header(
            fp, version, max_header_size=max_header_size)
    if len(shape) == 0:
        count = 1
    else:
        count = numpy.multiply.reduce(shape, dtype=numpy.int64)

    # Now read the actual data.
    if dtype.hasobject:
        # The array contained Python objects. We need to unpickle the data.
        if not allow_pickle:
            raise ValueError("Object arrays cannot be loaded when "
                             "allow_pickle=False")
        if pickle_kwargs is None:
            pickle_kwargs = {}
        try:
            array = pickle.load(fp, **pickle_kwargs)
        except UnicodeError as err:
            # Friendlier error message
            raise UnicodeError("Unpickling a python object failed: %r\n"
                               "You may need to pass the encoding= option "
                               "to numpy.load" % (err,)) from err
    else:
        if isfileobj(fp):
            # We can use the fast fromfile() function.
            array = numpy.fromfile(fp, dtype=dtype, count=count)
        else:
            # This is not a real file. We have to read it the
            # memory-intensive way.
            # crc32 module fails on reads greater than 2 ** 32 bytes,
            # breaking large reads from gzip streams. Chunk reads to
            # BUFFER_SIZE bytes to avoid issue and reduce memory overhead
            # of the read. In non-chunked case count < max_read_count, so
            # only one read is performed.

            # Use np.ndarray instead of np.empty since the latter does
            # not correctly instantiate zero-width string dtypes; see
            # https://github.com/numpy/numpy/pull/6430
            array = numpy.ndarray(count, dtype=dtype)

            if dtype.itemsize > 0:
                # If dtype.itemsize == 0 then there's nothing more to read
                max_read_count = BUFFER_SIZE // min(BUFFER_SIZE, dtype.itemsize)

                for i in range(0, count, max_read_count):
                    read_count = min(max_read_count, count - i)
                    read_size = int(read_count * dtype.itemsize)
                    data = _read_bytes(fp, read_size, "array data")
                    array[i:i + read_count] = numpy.frombuffer(data, dtype=dtype,
                                                             count=read_count)

        if array.size != count:
            raise ValueError(
                "Failed to read all data for array. "
                f"Expected {shape} = {count} elements, "
                f"could only read {array.size} elements. "
                "(file seems not fully written?)"
            )

        if fortran_order:
            array.shape = shape[::-1]
            array = array.transpose()
        else:
            array.shape = shape

    return array


@set_module("numpy.lib.format")
def open_memmap(filename, mode='r+', dtype=None, shape=None,
                fortran_order=False, version=None, *,
                max_header_size=_MAX_HEADER_SIZE):
    """
    Open a .npy file as a memory-mapped array.

    This may be used to read an existing file or create a new one.

    Parameters
    ----------
    filename : str or path-like
        The name of the file on disk.  This may *not* be a file-like
        object.
    mode : str, optional
        The mode in which to open the file; the default is 'r+'.  In
        addition to the standard file modes, 'c' is also accepted to mean
        "copy on write."  See `memmap` for the available mode strings.
    dtype : data-type, optional
        The data type of the array if we are creating a new file in "write"
        mode, if not, `dtype` is ignored.  The default value is None, which
        results in a data-type of `float64`.
    shape : tuple of int
        The shape of the array if we are creating a new file in "write"
        mode, in which case this parameter is required.  Otherwise, this
        parameter is ignored and is thus optional.
    fortran_order : bool, optional
        Whether the array should be Fortran-contiguous (True) or
        C-contiguous (False, the default) if we are creating a new file in
        "write" mode.
    version : tuple of int (major, minor) or None
        If the mode is a "write" mode, then this is the version of the file
        format used to create the file.  None means use the oldest
        supported version that is able to store the data.  Default: None
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.

    Returns
    -------
    marray : memmap
        The memory-mapped array.

    Raises
    ------
    ValueError
        If the data or the mode is invalid.
    OSError
        If the file is not found or cannot be opened correctly.

    See Also
    --------
    numpy.memmap

    """
    if isfileobj(filename):
        raise ValueError("Filename must be a string or a path-like object."
                         "  Memmap cannot use existing file handles.")

    if 'w' in mode:
        # We are creating the file, not reading it.
        # Check if we ought to create the file.
        _check_version(version)
        # Ensure that the given dtype is an authentic dtype object rather
        # than just something that can be interpreted as a dtype object.
        dtype = numpy.dtype(dtype)
        if dtype.hasobject:
            msg = "Array can't be memory-mapped: Python objects in dtype."
            raise ValueError(msg)
        d = {
            "descr": dtype_to_descr(dtype),
            "fortran_order": fortran_order,
            "shape": shape,
        }
        # If we got here, then it should be safe to create the file.
        with open(os.fspath(filename), mode + 'b') as fp:
            _write_array_header(fp, d, version)
            offset = fp.tell()
    else:
        # Read the header of the file first.
        with open(os.fspath(filename), 'rb') as fp:
            version = read_magic(fp)
            _check_version(version)

            shape, fortran_order, dtype = _read_array_header(
                    fp, version, max_header_size=max_header_size)
            if dtype.hasobject:
                msg = "Array can't be memory-mapped: Python objects in dtype."
                raise ValueError(msg)
            offset = fp.tell()

    if fortran_order:
        order = 'F'
    else:
        order = 'C'

    # We need to change a write-only mode to a read-write mode since we've
    # already written data to the file.
    if mode == 'w+':
        mode = 'r+'

    marray = numpy.memmap(filename, dtype=dtype, shape=shape, order=order,
        mode=mode, offset=offset)

    return marray


def _read_bytes(fp, size, error_template="ran out of data"):
    """
    Read from file-like object until size bytes are read.
    Raises ValueError if not EOF is encountered before size bytes are read.
    Non-blocking objects only supported if they derive from io objects.

    Required as e.g. ZipExtFile in python 2.6 can return less data than
    requested.
    """
    data = b""
    while True:
        # io files (default in python3) return None or raise on
        # would-block, python2 file will truncate, probably nothing can be
        # done about that.  note that regular files can't be non-blocking
        try:
            r = fp.read(size - len(data))
            data += r
            if len(r) == 0 or len(data) == size:
                break
        except BlockingIOError:
            pass
    if len(data) != size:
        msg = "EOF: reading %s, expected %d bytes got %d"
        raise ValueError(msg % (error_template, size, len(data)))
    else:
        return data


@set_module("numpy.lib.format")
def isfileobj(f):
    if not isinstance(f, (io.FileIO, io.BufferedReader, io.BufferedWriter)):
        return False
    try:
        # BufferedReader/Writer may raise OSError when
        # fetching `fileno()` (e.g. when wrapping BytesIO).
        f.fileno()
        return True
    except OSError:
        return False